# Student Digital Well‑Being Analytics

## Overview

This repository contains code and resources to analyze the relationship between social media usage, sleep, mental well‑being, and academic performance.

### Directory Structure
```
├─ data/
│   ├─ raw/            # Original CSV files (provided)
│   └─ processed/      # Cleaned dataset ready for analysis
├─ analysis/           # Python notebooks and scripts for ETL and modeling
├─ dashboard/          # Interactive web dashboard
└─ docs/               # Documentation and report templates
```

### Setup
```bash
# Create a virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows PowerShell
pip install -r analysis/requirements.txt
```

### Quick Start
1. Run the ETL script to generate `data/processed/processed_data.csv`.
2. Open `analysis/explore.ipynb` for exploratory analysis.
3. Open `dashboard/index.html` in a browser to view the dashboard.
