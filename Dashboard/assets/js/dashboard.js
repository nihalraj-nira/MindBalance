(function () {
    // ---------- ELEMENTS ----------
    const $ = id => document.getElementById(id);
    const screen = $('screen'), sleep = $('sleep'), sleepq = $('sleepq'),
        stress = $('stress'), study = $('study'), platform = $('platform');
    const simsleep = $('simsleep'), simscreen = $('simscreen');
    let lateNight = 1;

    // ---------- LIVE LABEL BINDING ----------
    function fmt(v, unit) { return parseFloat(v).toFixed(unit === 'h' ? 1 : 0) + (unit === 'h' ? ' h' : ''); }

    screen.addEventListener('input', () => $('v-screen').textContent = parseFloat(screen.value).toFixed(1) + ' h');
    sleep.addEventListener('input', () => $('v-sleep').textContent = parseFloat(sleep.value).toFixed(2).replace(/0$/, '') + ' h');
    sleepq.addEventListener('input', () => $('v-sleepq').textContent = sleepq.value + ' / 10');
    stress.addEventListener('input', () => $('v-stress').textContent = stress.value + ' / 10');
    study.addEventListener('input', () => $('v-study').textContent = parseFloat(study.value).toFixed(1) + ' h');
    simsleep.addEventListener('input', () => { $('v-simsleep').textContent = parseFloat(simsleep.value).toFixed(2).replace(/0$/, '') + ' h'; runWhatIf(); });
    simscreen.addEventListener('input', () => { $('v-simscreen').textContent = parseFloat(simscreen.value).toFixed(1) + ' h'; runWhatIf(); });

    document.querySelectorAll('#latenight .toggle-pill').forEach(p => {
        p.addEventListener('click', () => {
            document.querySelectorAll('#latenight .toggle-pill').forEach(x => x.classList.remove('active'));
            p.classList.add('active');
            lateNight = parseInt(p.dataset.val);
        });
    });

    // ---------- MOCK PROFILES ----------
    const profiles = {
        'alex': {
            name: 'Alex',
            screenT: 12.0, sleepT: 4.5, sleepQ: 3, stressL: 9, studyH: 1.0, late: 2, platform: 'TikTok',
            history: [88, 89, 90, 85, 92, 94, 91], // High risk scores over 7 days
            screenHistory: [9.5, 10.0, 11.5, 9.0, 12.5, 13.0, 12.0]
        },
        'sarah': {
            name: 'Sarah',
            screenT: 3.5, sleepT: 7.5, sleepQ: 8, stressL: 3, studyH: 5.0, late: 0, platform: 'WhatsApp',
            history: [25, 24, 22, 28, 26, 25, 23], // Low risk scores
            screenHistory: [3.5, 3.0, 2.5, 4.0, 3.5, 3.0, 3.5]
        },
        'jordan': {
            name: 'Jordan',
            screenT: 6.5, sleepT: 6.0, sleepQ: 5, stressL: 6, studyH: 3.0, late: 1, platform: 'Instagram',
            history: [55, 58, 62, 59, 61, 65, 60], // Moderate risk
            screenHistory: [5.5, 6.0, 7.0, 6.5, 6.0, 7.5, 6.5]
        }
    };

    let currentProfile = null;
    let weeklyChartInstance = null;

    $('profileSelector').addEventListener('change', (e) => {
        const pId = e.target.value;
        if (pId === 'none' || !profiles[pId]) {
            $('weeklyReportPanel').style.display = 'none';
            return;
        }
        
        currentProfile = profiles[pId];
        
        // Update sliders
        screen.value = currentProfile.screenT;
        sleep.value = currentProfile.sleepT;
        sleepq.value = currentProfile.sleepQ;
        stress.value = currentProfile.stressL;
        study.value = currentProfile.studyH;
        platform.value = currentProfile.platform;
        
        // Update late night pills
        document.querySelectorAll('#latenight .toggle-pill').forEach(x => {
            x.classList.remove('active');
            if(parseInt(x.dataset.val) === currentProfile.late) x.classList.add('active');
        });
        lateNight = currentProfile.late;
        
        // Dispatch input events to update labels
        ['screen', 'sleep', 'sleepq', 'stress', 'study'].forEach(id => {
            $(id).dispatchEvent(new Event('input'));
        });
        
        $('weeklyReportPanel').style.display = 'block';
        updateWeeklyChart(currentProfile.history, currentProfile.screenHistory);
        runPrediction();
    });

    // ---------- "MODEL" (lightweight client-side stand-in for the trained RF model) ----------
    // Coefficients approximate plausible directionality from EDA; Person C's exported
    // model/SHAP values should replace this function 1:1 via the same interface.
    function computeRisk(inputs) {
        const { screenT, sleepT, sleepQ, stressL, studyH, late } = inputs;

        const baseline = 42;

        const contributions = [
            { factor: 'Screen time', value: clampContrib((screenT - 5.0) * 4.2) },
            { factor: 'Sleep duration', value: clampContrib((7.2 - sleepT) * 5.4) },
            { factor: 'Sleep quality', value: clampContrib((5.5 - sleepQ) * 2.1) },
            { factor: 'Stress level', value: clampContrib((stressL - 5.0) * 3.4) },
            { factor: 'Study hours', value: clampContrib((studyH - 4.0) * -1.6) },
            { factor: 'Late-night usage', value: clampContrib(late * 5.5) },
        ];

        let score = baseline + contributions.reduce((s, c) => s + c.value, 0);
        score = Math.max(2, Math.min(98, score));

        return { score: Math.round(score), contributions, baseline };
    }
    function clampContrib(v) { return Math.max(-22, Math.min(22, v)); }

    function deriveIndices(inputs, riskScore) {
        const recovery = Math.max(2, Math.min(98, Math.round(
            (inputs.sleepT / 9) * 55 + (inputs.sleepQ / 10) * 45 - (inputs.late * 4)
        )));
        const balance = Math.max(2, Math.min(98, Math.round(
            100 - (inputs.screenT / 14) * 40 - (inputs.stressL / 10) * 30 + (inputs.studyH / 10) * 15
        )));
        const load = Math.max(2, Math.min(98, Math.round(
            (inputs.stressL / 10) * 60 + (inputs.screenT / 14) * 25 + inputs.late * 5
        )));
        const density = Math.max(2, Math.min(98, Math.round(
            (inputs.stressL / 10) * 50 + (100 - recovery) * 0.3
        )));
        return { recovery, balance, load, density };
    }

    // ---------- RENDER: GAUGE ----------
    function renderGauge(score) {
        const circumference = 427; // 2*pi*68
        const offset = circumference - (circumference * (score / 100));
        const arc = $('gaugeArc');
        arc.style.strokeDashoffset = offset;
        let color = '#8FB89C';
        if (score >= 70) color = '#D97D6B';
        else if (score >= 45) color = '#E0A458';
        arc.style.stroke = color;
        $('riskScore').textContent = score;
        $('riskScore').style.color = color;
    }

    function renderBand(score) {
        const band = $('riskBand');
        let label, color, bg;
        if (score >= 70) { label = 'High Risk'; color = '#D97D6B'; bg = 'rgba(217,125,107,.14)'; }
        else if (score >= 45) { label = 'Moderate Risk'; color = '#E0A458'; bg = 'rgba(224,164,88,.14)'; }
        else { label = 'Low Risk'; color = '#8FB89C'; bg = 'rgba(143,184,156,.14)'; }
        band.style.background = bg;
        band.style.color = color;
        band.innerHTML = `<span class="band-dot" style="background:${color};"></span> ${label}`;
    }

    function renderHeadline(score, inputs) {
        let headline, sub;
        if (score >= 70) {
            headline = `Several overlapping pressures are pushing this profile into the high-risk band.`;
            sub = `Sleep debt and stress are compounding with screen time late into the night — the model flags this pattern as the strongest predictor of academic and mental health decline in the training cohort.`;
        } else if (score >= 45) {
            headline = `This profile sits in a moderate-risk band — a few adjustable habits are driving most of the score.`;
            sub = `No single factor is extreme, but the combination of screen time and sleep quality is enough to erode recovery capacity over time.`;
        } else {
            headline = `This profile reflects a well-balanced digital lifestyle.`;
            sub = `Sleep, stress, and screen time are in a healthy range relative to the training cohort. Small variations are normal — keep monitoring late-night usage.`;
        }
        $('riskHeadline').textContent = headline;
        $('riskSub').textContent = sub;
    }

    // ---------- RENDER: MINI INDICES ----------
    function renderIndices(idx) {
        $('mn-recovery').textContent = idx.recovery;
        $('mn-balance').textContent = idx.balance;
        $('mn-load').textContent = idx.load;
        $('mn-density').textContent = idx.density;
        $('mn-recovery-bar').style.width = idx.recovery + '%';
        $('mn-balance-bar').style.width = idx.balance + '%';
        $('mn-load-bar').style.width = idx.load + '%';
        $('mn-density-bar').style.width = idx.density + '%';
    }

    // ---------- RENDER: LEDGER ----------
    function renderLedger(contributions) {
        const max = Math.max(...contributions.map(c => Math.abs(c.value)), 1);
        const rows = contributions
            .slice()
            .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
            .map(c => {
                const pct = (Math.abs(c.value) / max) * 46; // max 46% of track width per side
                const isPos = c.value >= 0;
                const left = isPos ? 50 : (50 - pct);
                const width = pct;
                return `
        <div class="ledger-row">
          <div class="ledger-factor">${c.factor}</div>
          <div class="ledger-track">
            <div class="ledger-bar ${isPos ? 'pos' : 'neg'}" style="left:${left}%; width:${width}%;"></div>
          </div>
          <div class="ledger-val ${isPos ? 'pos' : 'neg'}">${isPos ? '+' : ''}${c.value.toFixed(1)}</div>
        </div>`;
            }).join('');
        $('ledgerRows').innerHTML = rows;
    }

    // ---------- RENDER: RECOMMENDATIONS ----------
    function renderRecommendations(inputs, score) {
        const recos = [];
        if (inputs.sleepT < 6.5) {
            recos.push({ urgent: true, tag: 'Sleep', title: 'Extend sleep toward 7.5–8 h', body: 'The model identifies sleep duration as one of the largest drivers of risk in this profile. Even a 45–60 minute increase shows a measurable effect in the cohort data.' });
        }
        if (inputs.late >= 1) {
            recos.push({ urgent: inputs.late === 2, tag: 'Late-night use', title: 'Set a screen cutoff before midnight', body: 'Late-night usage compounds sleep debt more than total screen time alone. A consistent cutoff is the single highest-leverage change available here.' });
        }
        if (inputs.screenT > 6) {
            recos.push({ urgent: false, tag: 'Screen time', title: 'Trim 60–90 minutes of discretionary use', body: 'Reducing screen time without touching study hours preserved the Lifestyle Balance index in similar cohort profiles.' });
        }
        if (inputs.stressL >= 6) {
            recos.push({ urgent: false, tag: 'Stress', title: 'Introduce a short wind-down routine', body: 'Elevated stress is amplifying the impact of poor sleep quality. A 10-minute wind-down before bed is associated with improved next-day recovery scores.' });
        }
        if (inputs.studyH < 2) {
            recos.push({ urgent: false, tag: 'Study habits', title: 'Anchor a fixed daily study block', body: 'Structured study time correlates with lower psychosocial load even when screen time stays constant.' });
        }
        if (recos.length === 0) {
            recos.push({ urgent: false, tag: 'Maintain', title: 'Keep current habits steady', body: 'This profile is within a healthy range across all tracked indices. Recheck weekly to catch drift early.' });
        }
        $('recoList').innerHTML = recos.slice(0, 4).map(r => `
      <div class="reco-item ${r.urgent ? 'urgent' : ''}">
        <div class="reco-tag">${r.tag}</div>
        <div class="reco-body">
          <h4>${r.title}</h4>
          <p>${r.body}</p>
        </div>
      </div>
    `).join('');
    }

    // ---------- CURRENT STATE ----------
    let lastInputs = null;
    let lastScore = null;
    let currentTraj = null;
    let forecastChartInstance = null;

    function getCurrentInputs() {
        return {
            screenT: parseFloat(screen.value),
            sleepT: parseFloat(sleep.value),
            sleepQ: parseFloat(sleepq.value),
            stressL: parseFloat(stress.value),
            studyH: parseFloat(study.value),
            late: lateNight,
            platform: platform.value
        };
    }

    function mapInputsToApi(inputs) {
        return {
            "Age": 20, 
            "Gender": "Male", 
            "Academic_Level": "Undergraduate", 
            "Governorate": "Cairo", 
            "Relationship_Status": "Single", 
            "Avg_Daily_Usage_Hours": inputs.screenT,
            "Sleep_Hours_Per_Night": inputs.sleepT,
            "Most_Used_Platform": inputs.platform.includes('Twitter') ? 'Twitter' : inputs.platform,
            "Mental_Health_Score": inputs.sleepQ, 
            "Conflicts_Over_Social_Media": Math.round(inputs.stressL / 2), 
            "Affects_Academic_Performance": inputs.studyH < 2 ? "Yes" : "No"
        };
    }

    async function runPrediction() {
        const inputs = getCurrentInputs();
        
        try {
            const payload = mapInputsToApi(inputs);
            const res = await fetch("http://127.0.0.1:5000/predict", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            // Map API response back to UI format
            const score = Math.round(data.predicted_score * 10);
            
            // Scale indices to 0-100 gauge (approximate)
            const idx = {
                recovery: Math.min(100, Math.round(data.engineered_scores.Recovery_Capacity * 1.5)), 
                balance: Math.min(100, Math.round(data.engineered_scores.Lifestyle_Balance * 25)),
                load: Math.min(100, Math.round(data.engineered_scores.Psychosocial_Load * 2)),
                density: Math.min(100, Math.round(data.engineered_scores.Stress_Density * 30))
            };
            
            // Format SHAP contributions for ledger
            const contributions = data.top_features.map(f => ({
                factor: f.feature.replace(/_/g, " "),
                value: (f.shap_value * 15) // Scale for visual ledger
            }));

            renderGauge(score);
            renderBand(score);
            
            // Replace headline with API's natural language explanation
            $('riskHeadline').textContent = data.natural_language_explanation || "Run a prediction to see your digital wellness outlook.";
            $('riskSub').textContent = "This prediction is generated live by the Gradient Boosting model.";
            
            renderIndices(idx);
            renderLedger(contributions);
            
            // Render API recommendations
            let htmlRecos = '';
            data.recommendations.slice(0, 4).forEach(r => {
                htmlRecos += `
                  <div class="reco-item ${r.priority === 'high' ? 'urgent' : ''}">
                    <div class="reco-tag">${r.area}</div>
                    <div class="reco-body">
                      <h4>AI Recommendation</h4>
                      <p>${r.message}</p>
                    </div>
                  </div>`;
            });
            $('recoList').innerHTML = htmlRecos;

            // Render Digital Twins
            if (data.digital_twins && data.digital_twins.message) {
                const dtEl = $('dt-message');
                if (dtEl) {
                    dtEl.innerHTML = `<strong>KNN Analysis Complete:</strong> ${data.digital_twins.message}`;
                }
            }

            if (data.current_trajectory) {
                currentTraj = data.current_trajectory;
                updateForecastChart(currentTraj, null);
            }

            lastInputs = inputs;
            lastScore = score;
            runWhatIf();
            
        } catch (e) {
            console.error("API error, falling back to local model", e);
            const { score, contributions } = computeRisk(inputs);
            const idx = deriveIndices(inputs, score);
            renderGauge(score);
            renderBand(score);
            renderHeadline(score, inputs);
            renderIndices(idx);
            renderLedger(contributions);
            renderRecommendations(inputs, score);
            lastInputs = inputs;
            lastScore = score;
            runWhatIf();
        }
    }

    // ---------- WHAT-IF ----------
    async function runWhatIf() {
        if (!lastInputs) { return; }
        
        const simInputs = Object.assign({}, lastInputs, {
            sleepT: parseFloat(simsleep.value),
            screenT: parseFloat(simscreen.value)
        });
        
        try {
            const payload = {
                current: mapInputsToApi(lastInputs),
                adjusted: mapInputsToApi(simInputs)
            };
            
            const res = await fetch("http://127.0.0.1:5000/whatif", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            const base = Math.round(data.current.predicted_score * 10);
            const sim = Math.round(data.adjusted.predicted_score * 10);

            $('sim-from').textContent = base;
            $('sim-to').textContent = sim;
            $('sim-to').className = 'dc-to ' + (sim < base ? 'better' : (sim > base ? 'worse' : ''));

            const delta = sim - base;
            const deltaEl = $('sim-delta');
            if (delta < 0) {
                deltaEl.textContent = `▼ ${Math.abs(delta)} pts`;
                deltaEl.style.color = '#8FB89C';
            } else if (delta > 0) {
                deltaEl.textContent = `▲ ${delta} pts`;
                deltaEl.style.color = '#D97D6B';
            } else {
                deltaEl.textContent = `No change`;
                deltaEl.style.color = '#8A92A3';
            }
            
            if (data.adjusted.adjusted_trajectory && currentTraj) {
                updateForecastChart(currentTraj, data.adjusted.adjusted_trajectory);
            }
        } catch (e) {
            console.error("API error in whatif", e);
            const base = computeRisk(lastInputs).score;
            const sim = computeRisk(simInputs).score;
            $('sim-from').textContent = base;
            $('sim-to').textContent = sim;
            $('sim-to').className = 'dc-to ' + (sim < base ? 'better' : (sim > base ? 'worse' : ''));
            const delta = sim - base;
            const deltaEl = $('sim-delta');
            if (delta < 0) { deltaEl.textContent = `▼ ${Math.abs(delta)} pts`; deltaEl.style.color = '#8FB89C'; } 
            else if (delta > 0) { deltaEl.textContent = `▲ ${delta} pts`; deltaEl.style.color = '#D97D6B'; } 
            else { deltaEl.textContent = `No change`; deltaEl.style.color = '#8A92A3'; }
        }
    }

    $('runBtn').addEventListener('click', runPrediction);

    // ---------- COHORT CHART (simple SVG bar comparison) ----------
    function renderChart() {
        const wrap = $('chartWrap');
        const w = wrap.clientWidth || 1100;
        const h = 220;
        const data = [
            { label: 'Low risk\ncohort', screen: 3.2, sleep: 7.6, stress: 3.4 },
            { label: 'Moderate risk\ncohort', screen: 5.6, sleep: 6.4, stress: 5.8 },
            { label: 'High risk\ncohort', screen: 8.4, sleep: 5.1, stress: 7.9 },
            { label: 'This profile', screen: lastInputs ? lastInputs.screenT : 5.5, sleep: lastInputs ? lastInputs.sleepT : 6.5, stress: lastInputs ? lastInputs.stressL : 6 },
        ];
        const groupW = w / data.length;
        const barW = 26;
        const maxVal = 14;
        const baseY = h - 36;

        function barX(gi, bi) { return gi * groupW + groupW / 2 - (barW * 1.5) + bi * (barW + 6); }
        function barH(v, scaleMax) { return (v / scaleMax) * (h - 80); }

        const metrics = [
            { key: 'screen', color: '#D97D6B', scaleMax: 14 },
            { key: 'sleep', color: '#8FB89C', scaleMax: 10 },
            { key: 'stress', color: '#E0A458', scaleMax: 10 },
        ];

        let bars = '';
        data.forEach((d, gi) => {
            metrics.forEach((m, bi) => {
                const val = d[m.key];
                const bh = barH(val, m.scaleMax);
                const x = barX(gi, bi);
                const y = baseY - bh;
                const isProfile = d.label === 'This profile';
                bars += `<rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="2" fill="${m.color}" opacity="${isProfile ? 1 : 0.55}" stroke="${isProfile ? '#fff' : 'none'}" stroke-width="${isProfile ? 1 : 0}" stroke-opacity="0.4"/>`;
                bars += `<text x="${x + barW / 2}" y="${y - 6}" font-size="10" text-anchor="middle">${val.toFixed(1)}</text>`;
            });
            bars += `<text x="${gi * groupW + groupW / 2}" y="${h - 12}" font-size="11" text-anchor="middle" fill="#8A92A3">${d.label.split('\n')[0]}</text>`;
            bars += `<text x="${gi * groupW + groupW / 2}" y="${h + 2}" font-size="11" text-anchor="middle" fill="#8A92A3">${d.label.split('\n')[1] || ''}</text>`;
        });

        const legend = metrics.map((m, i) => `<rect x="${i * 150}" y="0" width="9" height="9" rx="2" fill="${m.color}"/><text x="${i * 150 + 14}" y="8" font-size="10" fill="#8A92A3">${m.key === 'screen' ? 'Screen time (h)' : m.key === 'sleep' ? 'Sleep (h)' : 'Stress (/10)'}</text>`).join('');

        wrap.innerHTML = `
      <svg width="100%" height="${h + 40}" viewBox="0 0 ${w} ${h + 40}" preserveAspectRatio="xMidYMid meet">
        <g transform="translate(8,4)">${legend}</g>
        <line x1="0" y1="${baseY}" x2="${w}" y2="${baseY}" stroke="#323B49" stroke-width="1"/>
        ${bars}
      </svg>
    `;
    }

    window.addEventListener('resize', renderChart);

    // ---------- CHAT WIDGET LOGIC ----------
    const chatToggle = $('chatToggle');
    const chatWidget = $('chatWidget');
    const chatClose = $('chatClose');
    const chatHistory = $('chatHistory');

    chatToggle.addEventListener('click', () => {
        chatWidget.classList.toggle('hidden');
    });

    chatClose.addEventListener('click', () => {
        chatWidget.classList.add('hidden');
    });

    async function sendChatMessage(text) {
        if (!text) return;

        // Append user message
        const userMsg = document.createElement('div');
        userMsg.className = 'chat-msg user';
        userMsg.textContent = text;
        chatHistory.appendChild(userMsg);

        chatHistory.scrollTop = chatHistory.scrollHeight;

        // Add a small delay for realism
        setTimeout(async () => {
            try {
                // Build Context
                const context = {
                    predicted_score: lastScore,
                    sleep_hours: lastInputs ? parseFloat(lastInputs.Sleep_Hours_Per_Night) : 7.0,
                    screen_time: lastInputs ? parseFloat(lastInputs.Avg_Daily_Usage_Hours) : 4.0
                };

                const res = await fetch("http://127.0.0.1:5000/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: text, context: context })
                });

                if (res.ok) {
                    const data = await res.json();
                    const aiMsg = document.createElement('div');
                    aiMsg.className = 'chat-msg ai';
                    aiMsg.textContent = data.reply || "I didn't quite catch that.";
                    chatHistory.appendChild(aiMsg);
                }
            } catch (e) {
                const aiMsg = document.createElement('div');
                aiMsg.className = 'chat-msg ai';
                aiMsg.textContent = "Oops! Cannot connect to the AI server. Did you start the Python API?";
                chatHistory.appendChild(aiMsg);
            }
            
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }, 300);
    }

    document.querySelectorAll('.chat-predefined-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            sendChatMessage(e.target.textContent);
        });
    });

    // ---------- FORECAST CHART ----------
    function initForecastChart() {
        const ctx = document.getElementById('forecastChart');
        if (!ctx) return;
        
        const labels = Array.from({length: 13}, (_, i) => `Week ${i}`);
        
        forecastChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Current Path',
                        data: [],
                        borderColor: '#E74C3C',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Adjusted Path (What-If)',
                        data: [],
                        borderColor: '#2ECC71',
                        borderWidth: 3,
                        borderDash: [5, 5],
                        tension: 0.4,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 10,
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#8A92A3' } }
                }
            }
        });
    }

    function updateForecastChart(current, adjusted) {
        if (!forecastChartInstance) return;
        if (current) forecastChartInstance.data.datasets[0].data = current;
        if (adjusted) {
            forecastChartInstance.data.datasets[1].data = adjusted;
        } else {
            forecastChartInstance.data.datasets[1].data = [];
        }
        forecastChartInstance.update();
    }

    // ---------- WEEKLY REPORT CHART ----------
    function updateWeeklyChart(historyData, screenData) {
        const ctx = document.getElementById('weeklyChart');
        if (!ctx) return;
        
        if (weeklyChartInstance) {
            weeklyChartInstance.destroy();
        }

        const labels = ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Today'];
        
        weeklyChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Screen Time (Hours)',
                        data: screenData,
                        type: 'line',
                        borderColor: '#3498db',
                        backgroundColor: '#3498db',
                        borderWidth: 3,
                        tension: 0.3,
                        yAxisID: 'y-screen'
                    },
                    {
                        label: 'Risk Score',
                        data: historyData,
                        backgroundColor: historyData.map(score => {
                            if(score >= 70) return 'rgba(217, 125, 107, 0.8)'; // High risk - Red
                            if(score >= 45) return 'rgba(224, 164, 88, 0.8)';  // Mod risk - Yellow
                            return 'rgba(143, 184, 156, 0.8)';                 // Low risk - Green
                        }),
                        borderRadius: 4,
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        title: { display: true, text: 'Risk Score (0-100)', color: '#8A92A3' }
                    },
                    'y-screen': {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 16,
                        grid: { drawOnChartArea: false }, // only draw grid lines for one axis
                        title: { display: true, text: 'Screen Time (h)', color: '#3498db' }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { 
                        display: true,
                        labels: { color: '#8A92A3' }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    }

    // ---------- INIT ----------
    initForecastChart();
    runPrediction();
    renderChart();

})();
