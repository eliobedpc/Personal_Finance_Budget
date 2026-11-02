# Personal Finance & Budget Dashboard + Data Science Midterm

This package preserves the original Flask budget application and expands it to satisfy the Lesson 7 midterm rubric for Lessons 05–07.

## Existing application features
- Income/expense tracking, custom categories, dates and editing
- Budget status, progress, savings goal
- Currency converter and exchange-rate API
- Browser persistence and research-backed tips
- Excel import/export
- Financial dashboard visualizations

## Data-science requirements covered
- New public dataset: South German Credit (UCI ID 522)
- Data acquisition documented and reproducible
- Cleaning: duplicates, missing values, invalid values
- Preprocessing: feature engineering, scaling, one-hot encoding
- EDA: `info()`, `describe()`, mean, median, std, correlation, class balance
- Visualizations: histogram, boxplot, heatmap, countplot, feature-importance bar chart
- ML models: Logistic Regression and Random Forest
- Evaluation: accuracy, precision, recall, F1
- Saved models, results JSON, charts, and auto-generated report

## Setup — macOS
```bash
cd personal_finance_midterm
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 data_analysis.py
python3 app.py
```

## Setup — Windows Command Prompt
```bat
cd personal_finance_midterm
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py data_analysis.py
py app.py
```

Open `http://127.0.0.1:5000/` for the budget dashboard and `http://127.0.0.1:5000/analysis` for the midterm analysis.

The first `data_analysis.py` run downloads the UCI dataset, then creates local raw/cleaned CSV files, two trained models, five charts, `analysis_results.json`, and `report/MIDTERM_REPORT.md`.

## Deployment
Build command: `pip install -r requirements.txt`
Start command: `gunicorn app:app`

## Dataset citation
South German Credit [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5X89F
Dataset page: https://archive.ics.uci.edu/dataset/522/south+german+credit

## Interpretation note
This is an educational ML exercise. The historical credit dataset should not be used to make real lending decisions.
