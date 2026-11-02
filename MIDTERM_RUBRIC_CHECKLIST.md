# Midterm Rubric Checklist

## 1.1 Select a Dataset
- [x] New dataset not used in class: **South German Credit**
- [x] Public repository: UCI Machine Learning Repository
- [x] Source/DOI documented in README and `data/README.md`

## 2.1 Acquire, Clean, and Preprocess
- [x] Acquisition code using `ucimlrepo.fetch_ucirepo(id=522)`
- [x] Saves local CSV copy for reproducibility
- [x] Checks/removes duplicates
- [x] Checks/fills missing numeric and categorical values
- [x] Removes invalid duration/amount/age rows
- [x] Preprocessing technique 1: feature engineering (`amount_per_month`, `age_group`)
- [x] Preprocessing technique 2: `StandardScaler`
- [x] Preprocessing technique 3: `OneHotEncoder`

## 2.2 EDA and Visualization
- [x] `info()`
- [x] `describe()`
- [x] Mean
- [x] Median
- [x] Standard deviation
- [x] Correlation analysis
- [x] Class imbalance analysis
- [x] Histogram
- [x] Boxplot
- [x] Correlation heatmap
- [x] Class-balance bar/count chart
- [x] Feature-importance bar chart

## 2.3 Machine Learning
- [x] Algorithm 1: Logistic Regression
- [x] Algorithm 2: Random Forest
- [x] Stratified train/test split
- [x] Accuracy
- [x] Precision
- [x] Recall
- [x] F1 score
- [x] Confusion matrix saved in JSON results
- [x] Classification report generated
- [x] Trained models saved with joblib

## 3. Deliverables
- [x] Well-commented Python analysis script
- [x] Original Flask budget application retained
- [x] Web `/analysis` page for data-science results
- [x] Dataset access instructions
- [x] Saved charts
- [x] Saved models
- [x] Auto-generated final report
- [x] README with Mac/Windows instructions
- [x] `.gitignore` for Git/GitHub

## Run Order

```bash
pip install -r requirements.txt
python data_analysis.py
python app.py
```

Then open:
- Budget app: `http://127.0.0.1:5000/`
- Data science: `http://127.0.0.1:5000/analysis`
