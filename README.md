# Personal Finance & Budget Dashboard

Group midterm project built with Python, Flask, HTML, CSS, JavaScript, a public exchange-rate API, and Excel import/export.

## Project structure

```text
personal_finance_midterm/
├── app.py
├── requirements.txt
├── test_calculations.py
├── templates/
│   └── dashboard.html
└── static/
    ├── dashboard.js
    └── styles.css
```

## Final features

- Add income and expense transactions.
- Add a date to each transaction.
- Edit or remove existing transactions.
- Use default or custom expense categories such as `Pets`.
- Automatically save dashboard data in the browser with `localStorage`.
- Restore saved data after refreshing or reopening the page in the same browser.
- Clear saved browser data from the dashboard.
- Set or clear a monthly expense budget.
- Show clear budget status:
  - `No budget set`
  - `$300.00 left in budget`
  - `$200.00 over budget`
- Display budget usage with a progress bar.
- Python/Flask calculates total income, total expenses, remaining money, budget usage, income spent, and spending by category.
- Dynamic spending-by-category chart with readable percentage labels, including very small categories (`<0.1%`).
- Cash-flow visualization for income, expenses, and remaining money.
- Income-allocation donut showing spent vs. remaining income.
- Savings-goal feature with current savings and progress bar.
- Research-backed financial-tip ticker based on dashboard results.
- Current reference exchange rates through the Frankfurter public API.
- Interactive money converter for USD, EUR, GBP, MXN, CAD, and JPY.
- Custom app validation/error messages instead of browser validation popups.
- Excel `.xlsx` import and export.

## Excel import format

The preferred columns are:

```text
Date | Description | Type | Category | Amount
```

Older spreadsheets without `Date` still work. `Type` should be `Income` or `Expense`. Custom categories are preserved. Files exported by the project also save the monthly budget, savings goal, and current savings on the Summary sheet and can be imported again.

## Research-backed tip sources

The dashboard uses short educational summaries based on peer-reviewed research. These are general educational tips, not individualized financial or investment advice.

1. Hwang, H., & Park, H. I. (2023). *The relationships of financial literacy with both financial behavior and financial well-being: Meta-analyses based on the selective literature review.* Journal of Consumer Affairs, 57(1), 222-244. https://doi.org/10.1111/joca.12497
2. *The smart money is in cash? Financial literacy and liquid savings among U.S. families.* Journal of Accounting and Public Policy, 42(2), 107000 (2023). https://doi.org/10.1016/j.jaccpubpol.2022.107000
3. *Personalizing or reminding? How to better incentivize savings among underbanked individuals.* Journal of Economic Behavior & Organization, 222, 25-63 (2024). https://doi.org/10.1016/j.jebo.2024.04.005

## Run on macOS

```bash
cd ~/Downloads/personal_finance_midterm
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Run on Windows Command Prompt

```bat
cd %USERPROFILE%\Downloads\personal_finance_midterm
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Suggested test checklist

1. Start with no budget and confirm the card says `No budget set`.
2. Set a $1,000 budget and add $1,200 in expenses; confirm `$200.00 over budget`.
3. Add a custom category such as `Pets`; confirm it appears in the category chart.
4. Add a very small category; confirm its label does not show `0.0%`.
5. Edit an existing transaction and verify totals update.
6. Add dates and verify they appear in the transaction table.
7. Refresh the browser and confirm data is restored.
8. Set a savings goal and current savings; verify the progress bar.
9. Test the money converter.
10. Export to Excel and import that file again; verify Date, custom categories, budget, and savings values return.
11. Trigger a validation error and confirm the dashboard shows its own message instead of the browser default popup.

## Suggested presentation flow

1. Enter or import income and expenses.
2. Flask validates the data and Python calculates the financial totals.
3. JavaScript receives the JSON summary and updates the dashboard.
4. The dashboard shows budget status, cash flow, category spending, and income allocation.
5. Users can edit transactions, create custom categories, and track savings goals.
6. The tip ticker provides research-backed educational guidance based on the current totals.
7. The public API supplies exchange rates and supports the interactive money converter.
8. Data persists in the browser and can also be exported/imported through Excel.

## Suggested team contribution summary

- **Lizeth:** requirements, layout planning, and presentation leadership.
- **Kevin:** test scenarios, expected results, testing, and verification.
- **Stefan:** dashboard webpage, JavaScript interactions, Excel import/export workflow, and front-end integration.
- **Eli:** Flask/Python calculations, validation, public API integration, financial visualizations, budget-status improvements, persistence, editing/dates, custom categories, savings-goal feature, money converter, research-backed tips, troubleshooting, and final integration.
