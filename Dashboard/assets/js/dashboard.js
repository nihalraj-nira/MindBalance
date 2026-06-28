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

    // ---------- MOCK PROFILES (per-day tracking) ----------
    const profiles = {
        'alex': {
            name: 'Alex',
            days: [
                { screenT: 9.5,  sleepT: 5.0,  sleepQ: 4, stressL: 7, studyH: 2.0, late: 1, platform: 'TikTok',    risk: 72 },
                { screenT: 10.0, sleepT: 4.5,  sleepQ: 3, stressL: 8, studyH: 1.5, late: 2, platform: 'TikTok',    risk: 81 },
                { screenT: 11.5, sleepT: 4.0,  sleepQ: 3, stressL: 9, studyH: 1.0, late: 2, platform: 'Instagram', risk: 88 },
                { screenT: 9.0,  sleepT: 5.5,  sleepQ: 4, stressL: 7, studyH: 2.5, late: 1, platform: 'TikTok',    risk: 68 },
                { screenT: 12.5, sleepT: 4.0,  sleepQ: 2, stressL: 9, studyH: 0.5, late: 2, platform: 'TikTok',    risk: 92 },
                { screenT: 13.0, sleepT: 3.75, sleepQ: 2, stressL: 10,studyH: 0.5, late: 2, platform: 'Instagram', risk: 94 },
                { screenT: 12.0, sleepT: 4.5,  sleepQ: 3, stressL: 9, studyH: 1.0, late: 2, platform: 'TikTok',    risk: 91 }
            ]
        },
        'sarah': {
            name: 'Sarah',
            days: [
                { screenT: 3.5, sleepT: 7.5,  sleepQ: 8, stressL: 3, studyH: 5.0, late: 0, platform: 'WhatsApp', risk: 25 },
                { screenT: 3.0, sleepT: 8.0,  sleepQ: 9, stressL: 2, studyH: 5.5, late: 0, platform: 'WhatsApp', risk: 21 },
                { screenT: 2.5, sleepT: 7.75, sleepQ: 8, stressL: 3, studyH: 5.0, late: 0, platform: 'WhatsApp', risk: 22 },
                { screenT: 4.0, sleepT: 7.0,  sleepQ: 7, stressL: 4, studyH: 4.5, late: 0, platform: 'WhatsApp', risk: 28 },
                { screenT: 3.5, sleepT: 7.5,  sleepQ: 8, stressL: 3, studyH: 5.0, late: 0, platform: 'WhatsApp', risk: 26 },
                { screenT: 3.0, sleepT: 8.0,  sleepQ: 9, stressL: 2, studyH: 6.0, late: 0, platform: 'WhatsApp', risk: 20 },
                { screenT: 3.5, sleepT: 7.5,  sleepQ: 8, stressL: 3, studyH: 5.0, late: 0, platform: 'WhatsApp', risk: 23 }
            ]
        },
        'jordan': {
            name: 'Jordan',
            days: [
                { screenT: 5.5, sleepT: 6.5, sleepQ: 6, stressL: 5, studyH: 3.5, late: 1, platform: 'Instagram', risk: 52 },
                { screenT: 6.0, sleepT: 6.0, sleepQ: 5, stressL: 6, studyH: 3.0, late: 1, platform: 'Instagram', risk: 58 },
                { screenT: 7.0, sleepT: 5.5, sleepQ: 4, stressL: 7, studyH: 2.5, late: 1, platform: 'Instagram', risk: 66 },
                { screenT: 6.5, sleepT: 6.0, sleepQ: 5, stressL: 6, studyH: 3.0, late: 1, platform: 'Instagram', risk: 59 },
                { screenT: 6.0, sleepT: 6.25,sleepQ: 5, stressL: 6, studyH: 3.5, late: 1, platform: 'Instagram', risk: 55 },
                { screenT: 7.5, sleepT: 5.5, sleepQ: 4, stressL: 7, studyH: 2.0, late: 2, platform: 'Instagram', risk: 70 },
                { screenT: 6.5, sleepT: 6.0, sleepQ: 5, stressL: 6, studyH: 3.0, late: 1, platform: 'Instagram', risk: 60 }
            ]
        }
    };

    let currentProfile = null;
    let selectedDay = 6; // default to Sunday (today)
    let weeklyChartInstance = null;

    function loadDay(dayIndex) {
        if (!currentProfile) return;
        selectedDay = dayIndex;
        const d = currentProfile.days[dayIndex];

        // Update sliders to this day's data
        screen.value = d.screenT;
        sleep.value = d.sleepT;
        sleepq.value = d.sleepQ;
        stress.value = d.stressL;
        study.value = d.studyH;
        platform.value = d.platform;

        // Update late-night pills
        document.querySelectorAll('#latenight .toggle-pill').forEach(x => {
            x.classList.remove('active');
            if (parseInt(x.dataset.val) === d.late) x.classList.add('active');
        });
        lateNight = d.late;

        // Fire input events to update slider labels
        ['screen', 'sleep', 'sleepq', 'stress', 'study'].forEach(id => {
            $(id).dispatchEvent(new Event('input'));
        });

        // Update day detail card
        $('dd-screen').textContent = d.screenT.toFixed(1) + ' h';
        $('dd-sleep').textContent = d.sleepT.toFixed(1) + ' h';
        $('dd-stress').textContent = d.stressL + ' / 10';
        $('dd-study').textContent = d.studyH.toFixed(1) + ' h';
        const riskEl = $('dd-risk');
        riskEl.textContent = d.risk + ' / 100';
        if (d.risk >= 70) riskEl.style.color = '#D97D6B';
        else if (d.risk >= 45) riskEl.style.color = '#E0A458';
        else riskEl.style.color = '#8FB89C';

        // Highlight active day button
        document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`.day-btn[data-day="${dayIndex}"]`).classList.add('active');

        // Update chart highlight
        updateWeeklyChart(currentProfile.days.map(x => x.risk), currentProfile.days.map(x => x.screenT), dayIndex);

        runPrediction();
    }

    // Day selector click handler
    document.querySelectorAll('.day-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            loadDay(parseInt(e.target.dataset.day));
        });
    });

    // Profile dropdown handler
    $('profileSelector').addEventListener('change', (e) => {
        const pId = e.target.value;
        if (pId === 'none' || !profiles[pId]) {
            $('weeklyReportPanel').style.display = 'none';
            currentProfile = null;
            return;
        }

        currentProfile = profiles[pId];
        $('weeklyProfileName').textContent = `Tracking data for ${currentProfile.name}'s weekly habits.`;
        $('weeklyReportPanel').style.display = 'block';
        loadDay(6); // Load Sunday (today) by default
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
    function updateWeeklyChart(historyData, screenData, activeDay) {
        const ctx = document.getElementById('weeklyChart');
        if (!ctx) return;
        
        if (weeklyChartInstance) {
            weeklyChartInstance.destroy();
        }

        const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

        // Build colors: selected day is brighter, others are dimmed
        const barColors = historyData.map((score, i) => {
            const isActive = (i === activeDay);
            if (score >= 70) return isActive ? 'rgba(217, 125, 107, 1)' : 'rgba(217, 125, 107, 0.4)';
            if (score >= 45) return isActive ? 'rgba(224, 164, 88, 1)'  : 'rgba(224, 164, 88, 0.4)';
            return isActive ? 'rgba(143, 184, 156, 1)' : 'rgba(143, 184, 156, 0.4)';
        });

        const barBorders = historyData.map((score, i) => {
            if (i !== activeDay) return 'transparent';
            if (score >= 70) return '#D97D6B';
            if (score >= 45) return '#E0A458';
            return '#8FB89C';
        });

        // Threshold plugin — draws a dashed "danger zone" line at 70
        const thresholdPlugin = {
            id: 'thresholdLine',
            afterDraw(chart) {
                const yScale = chart.scales.y;
                const ctx2 = chart.ctx;
                const yPos = yScale.getPixelForValue(70);
                ctx2.save();
                ctx2.strokeStyle = 'rgba(217, 125, 107, 0.5)';
                ctx2.lineWidth = 2;
                ctx2.setLineDash([6, 4]);
                ctx2.beginPath();
                ctx2.moveTo(chart.chartArea.left, yPos);
                ctx2.lineTo(chart.chartArea.right, yPos);
                ctx2.stroke();
                // Label
                ctx2.fillStyle = 'rgba(217, 125, 107, 0.7)';
                ctx2.font = '11px Inter, sans-serif';
                ctx2.fillText('High Risk Threshold', chart.chartArea.right - 120, yPos - 6);
                ctx2.restore();
            }
        };
        
        weeklyChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Screen Time (h)',
                        data: screenData,
                        type: 'line',
                        borderColor: '#6398FF',
                        backgroundColor: 'rgba(99, 152, 255, 0.1)',
                        pointBackgroundColor: screenData.map((_, i) => i === activeDay ? '#fff' : '#6398FF'),
                        pointRadius: screenData.map((_, i) => i === activeDay ? 6 : 3),
                        pointBorderWidth: screenData.map((_, i) => i === activeDay ? 3 : 0),
                        pointBorderColor: '#6398FF',
                        borderWidth: 2.5,
                        tension: 0.35,
                        fill: true,
                        yAxisID: 'y-screen'
                    },
                    {
                        label: 'Risk Score',
                        data: historyData,
                        backgroundColor: barColors,
                        borderColor: barBorders,
                        borderWidth: 2,
                        borderRadius: 6,
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
                        title: { display: true, text: 'Risk Score (0-100)', color: '#8A92A3', font: { size: 11 } },
                        ticks: { color: '#8A92A3' }
                    },
                    'y-screen': {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 16,
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Screen Time (h)', color: '#6398FF', font: { size: 11 } },
                        ticks: { color: '#6398FF' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: labels.map((_, i) => i === activeDay ? '#fff' : '#8A92A3'),
                            font: {
                                weight: labels.map((_, i) => i === activeDay ? 'bold' : 'normal')
                            }
                        }
                    }
                },
                plugins: {
                    legend: { 
                        display: true,
                        labels: { color: '#8A92A3', usePointStyle: true, pointStyle: 'circle' }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(30,35,50,0.95)',
                        titleColor: '#fff',
                        bodyColor: '#ccc',
                        borderColor: 'rgba(99,152,255,0.3)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                }
            },
            plugins: [thresholdPlugin]
        });
    }

    // ---------- SYNC DEVICE DATA ----------
    $('syncBtn').addEventListener('click', () => {
        const btn = $('syncBtn');
        const icon = $('syncIcon');
        const text = $('syncText');

        btn.classList.add('syncing');
        btn.classList.remove('synced');
        text.textContent = 'Syncing...';
        btn.disabled = true;

        // Simulate device data coming in (realistic random values)
        setTimeout(() => {
            const syncedScreen = (4 + Math.random() * 6).toFixed(1);
            const syncedSleep = (5 + Math.random() * 4).toFixed(2).replace(/0$/, '');
            const syncedSleepQ = Math.floor(3 + Math.random() * 7);
            const syncedStress = Math.floor(2 + Math.random() * 7);
            const syncedStudy = (1 + Math.random() * 5).toFixed(1);

            screen.value = syncedScreen;
            sleep.value = syncedSleep;
            sleepq.value = syncedSleepQ;
            stress.value = syncedStress;
            study.value = syncedStudy;

            // Fire input events to update labels
            ['screen', 'sleep', 'sleepq', 'stress', 'study'].forEach(id => {
                $(id).dispatchEvent(new Event('input'));
            });

            btn.classList.remove('syncing');
            btn.classList.add('synced');
            icon.innerHTML = '&#10003;';
            text.textContent = 'Synced!';

            runPrediction();

            // Reset button after 3 seconds
            setTimeout(() => {
                btn.classList.remove('synced');
                icon.innerHTML = '&#8635;';
                text.textContent = 'Sync Device Data';
                btn.disabled = false;
            }, 3000);
        }, 2000);
    });

    // ---------- EXPORT CLINICAL REPORT ----------
    $('exportBtn').addEventListener('click', () => {
        const score = lastScore || '—';
        const profileName = currentProfile ? currentProfile.name : 'Anonymous';
        const today = new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });

        let riskLevel = 'Low Risk';
        let riskColor = '#8FB89C';
        if (score >= 70) { riskLevel = 'High Risk'; riskColor = '#D97D6B'; }
        else if (score >= 45) { riskLevel = 'Moderate Risk'; riskColor = '#E0A458'; }

        // Build the top 3 risk factors from contributions
        let factorsHTML = '';
        if (lastInputs) {
            const factors = [
                { name: 'Screen Time', val: lastInputs.screenT.toFixed(1) + ' h/day', impact: Math.abs(lastInputs.screenT - 5) },
                { name: 'Sleep Duration', val: lastInputs.sleepT.toFixed(1) + ' h/night', impact: Math.abs(7.5 - lastInputs.sleepT) },
                { name: 'Stress Level', val: lastInputs.stressL + '/10', impact: lastInputs.stressL / 2 },
                { name: 'Study Hours', val: lastInputs.studyH.toFixed(1) + ' h/day', impact: Math.abs(4 - lastInputs.studyH) / 2 },
                { name: 'Sleep Quality', val: lastInputs.sleepQ + '/10', impact: Math.abs(7 - lastInputs.sleepQ) / 2 }
            ].sort((a, b) => b.impact - a.impact).slice(0, 3);

            factorsHTML = factors.map((f, i) => `
                <tr>
                    <td style="padding:8px 12px; border-bottom:1px solid #eee;">${i + 1}</td>
                    <td style="padding:8px 12px; border-bottom:1px solid #eee;">${f.name}</td>
                    <td style="padding:8px 12px; border-bottom:1px solid #eee;">${f.val}</td>
                </tr>
            `).join('');
        }

        const reportHTML = `
            <html>
            <head>
                <title>MindBalance Clinical Report — ${profileName}</title>
                <style>
                    body { font-family: 'Inter', Arial, sans-serif; padding: 40px; color: #222; max-width: 700px; margin: auto; }
                    h1 { font-size: 22px; margin-bottom: 4px; }
                    .subtitle { color: #888; font-size: 13px; margin-bottom: 30px; }
                    .score-box { text-align: center; padding: 24px; border: 2px solid ${riskColor}; border-radius: 12px; margin-bottom: 24px; }
                    .score-num { font-size: 48px; font-weight: 700; color: ${riskColor}; }
                    .score-label { font-size: 14px; color: #666; margin-top: 4px; }
                    table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
                    th { text-align: left; padding: 8px 12px; background: #f5f5f5; font-size: 13px; }
                    .section-title { font-size: 16px; font-weight: 600; margin: 24px 0 12px; border-bottom: 2px solid #eee; padding-bottom: 6px; }
                    .rec { padding: 10px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; line-height: 1.5; }
                    .footer { margin-top: 40px; font-size: 11px; color: #aaa; text-align: center; border-top: 1px solid #eee; padding-top: 16px; }
                </style>
            </head>
            <body>
                <h1>MindBalance Clinical Summary Report</h1>
                <div class="subtitle">Patient: <strong>${profileName}</strong> | Date: ${today} | Generated by MindBalance AI Platform</div>

                <div class="score-box">
                    <div class="score-num">${score}</div>
                    <div class="score-label">${riskLevel} (0 = Healthy, 100 = Critical)</div>
                </div>

                <div class="section-title">Top Risk Factors</div>
                <table>
                    <tr><th>#</th><th>Factor</th><th>Value</th></tr>
                    ${factorsHTML || '<tr><td colspan="3" style="padding:8px 12px;">Run a prediction first</td></tr>'}
                </table>

                <div class="section-title">Recommendations</div>
                <div class="rec"><strong>1. Sleep Optimization:</strong> Aim for 7–8 hours of uninterrupted sleep. Set a consistent sleep schedule and avoid screens 30 minutes before bedtime.</div>
                <div class="rec"><strong>2. Screen Time Management:</strong> Reduce recreational screen time by 60–90 minutes. Use app-limit features on your device to enforce boundaries.</div>
                <div class="rec"><strong>3. Stress Reduction:</strong> Incorporate a 10-minute mindfulness or breathing exercise into your daily routine, ideally before study sessions.</div>

                <div class="section-title">Counselor Notes</div>
                <p style="font-size:13px; color:#666; line-height:1.6;">
                    This report was generated by the MindBalance AI-driven digital wellness platform. The risk score is computed using a
                    Gradient Boosting Regressor trained on 12,000+ student behavioral records (IEEE DataPort). Factor importance is
                    derived from SHAP (SHapley Additive exPlanations) values. This summary is intended to supplement, not replace,
                    clinical assessment.
                </p>

                <div class="footer">
                    MindBalance &mdash; AI-Driven Digital Wellness Platform | Confidential Student Health Record
                </div>
            </body>
            </html>
        `;

        const printWindow = window.open('', '_blank');
        printWindow.document.write(reportHTML);
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => printWindow.print(), 500);
    });

    // ---------- INIT ----------
    initForecastChart();
    runPrediction();
    renderChart();

})();
