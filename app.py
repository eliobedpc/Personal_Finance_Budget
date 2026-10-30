from datetime import date, datetime
from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
import requests

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

DEFAULT_CATEGORIES = ["Housing", "Food", "Transport", "Entertainment", "Utilities", "Other"]
EXCHANGE_API_URL = "https://api.frankfurter.dev/v2/rates"
SPREADSHEET_COLUMNS = ["Date", "Description", "Type", "Category", "Amount"]
XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

FINANCIAL_TIPS = {
    "education": {
        "message": (
            "Keep learning how your money works. A peer-reviewed meta-analysis found "
            "positive relationships between financial knowledge, desirable financial "
            "behavior, and financial well-being."
        ),
        "source": "Hwang & Park (2023), Journal of Consumer Affairs",
        "url": "https://doi.org/10.1111/joca.12497",
    },
    "emergency": {
        "message": (
            "You have money remaining this month. Consider assigning part of it to "
            "liquid emergency savings; research links financial literacy with holding "
            "at least three months of liquid savings across income levels."
        ),
        "source": "Journal of Accounting and Public Policy (2023)",
        "url": "https://doi.org/10.1016/j.jaccpubpol.2022.107000",
    },
    "goal": {
        "message": (
            "Give your savings a specific dollar goal. A randomized study found that "
            "highlighting a specific monetary goal was more effective than general "
            "personalization alone for encouraging savings."
        ),
        "source": "Journal of Economic Behavior & Organization (2024)",
        "url": "https://doi.org/10.1016/j.jebo.2024.04.005",
    },
    "review": {
        "message": (
            "Your spending is close to or above the budget you set. Review the largest "
            "categories and make a clear plan for the rest of the month; financial "
            "knowledge is positively associated with desirable financial behavior."
        ),
        "source": "Hwang & Park (2023), Journal of Consumer Affairs",
        "url": "https://doi.org/10.1111/joca.12497",
    },
}


def to_number(value, field_name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")
    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return number


def normalize_date(value):
    """Return an ISO date string or an empty string."""
    if value is None or str(value).strip() == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        raise ValueError("Transaction date must use YYYY-MM-DD format.")


def select_financial_tips(summary):
    tips = []
    if summary["income"] == 0 and summary["expenses"] == 0:
        return [FINANCIAL_TIPS["education"]]
    if summary["remaining"] < 0:
        tips.extend([FINANCIAL_TIPS["review"], FINANCIAL_TIPS["education"]])
    elif summary["budget_used_percent"] is not None and summary["budget_used_percent"] >= 80:
        tips.extend([FINANCIAL_TIPS["review"], FINANCIAL_TIPS["goal"]])
    elif summary["remaining"] > 0:
        tips.extend([FINANCIAL_TIPS["emergency"], FINANCIAL_TIPS["goal"]])
    else:
        tips.append(FINANCIAL_TIPS["education"])
    if FINANCIAL_TIPS["education"] not in tips:
        tips.append(FINANCIAL_TIPS["education"])
    return tips


def calculate_summary(transactions, budget):
    total_income = 0.0
    total_expenses = 0.0
    categories = {category: 0.0 for category in DEFAULT_CATEGORIES}

    for transaction in transactions:
        transaction_type = str(transaction.get("type", "")).lower()
        amount = to_number(transaction.get("amount"), "Transaction amount")
        if amount == 0:
            raise ValueError("Transaction amount must be greater than zero.")

        if transaction_type == "income":
            total_income += amount
        elif transaction_type == "expense":
            total_expenses += amount
            category = str(transaction.get("category", "Other")).strip() or "Other"
            if category not in categories:
                categories[category] = 0.0
            categories[category] += amount
        else:
            raise ValueError("Transaction type must be income or expense.")

    remaining = total_income - total_expenses
    budget_used_percent = (total_expenses / budget) * 100 if budget > 0 else None
    income_spent_percent = (total_expenses / total_income) * 100 if total_income > 0 else None

    if budget <= 0:
        budget_status = "not_set"
        budget_message = "No budget set"
        budget_difference = None
    else:
        difference = budget - total_expenses
        budget_difference = round(abs(difference), 2)
        if difference >= 0:
            budget_status = "under"
            budget_message = f"${difference:,.2f} left in budget"
        else:
            budget_status = "over"
            budget_message = f"${abs(difference):,.2f} over budget"

    summary = {
        "income": round(total_income, 2),
        "expenses": round(total_expenses, 2),
        "remaining": round(remaining, 2),
        "budget_used_percent": round(budget_used_percent, 1) if budget_used_percent is not None else None,
        "income_spent_percent": round(income_spent_percent, 1) if income_spent_percent is not None else None,
        "budget_status": budget_status,
        "budget_message": budget_message,
        "budget_difference": budget_difference,
        "categories": {category: round(total, 2) for category, total in categories.items()},
    }
    summary["tips"] = select_financial_tips(summary)
    return summary


def validate_request(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid request data.")
    transactions = data.get("transactions", [])
    if not isinstance(transactions, list):
        raise ValueError("Transactions must be a list.")

    budget = to_number(data.get("budget", 0), "Budget")
    savings_goal = to_number(data.get("savings_goal", 0), "Savings goal")
    savings_saved = to_number(data.get("savings_saved", 0), "Current savings")

    for transaction in transactions:
        if not isinstance(transaction, dict):
            raise ValueError("Each transaction must be an object.")
        description = str(transaction.get("description", "")).strip()
        if not description:
            raise ValueError("Each transaction needs a description.")
        if len(description) > 60:
            raise ValueError("Transaction descriptions must be 60 characters or fewer.")
        normalize_date(transaction.get("date", ""))
        if str(transaction.get("type", "")).lower() == "expense":
            category = str(transaction.get("category", "")).strip()
            if not category:
                raise ValueError("Expense transactions need a category.")
            if len(category) > 30:
                raise ValueError("Categories must be 30 characters or fewer.")

    return transactions, budget, savings_goal, savings_saved


def read_spreadsheet(file):
    try:
        workbook = load_workbook(file, read_only=True, data_only=True)
    except Exception:
        raise ValueError("That file could not be opened. Please upload an Excel .xlsx file.")

    sheet = workbook["Transactions"] if "Transactions" in workbook.sheetnames else workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows, None) or ()
    columns = {str(name).strip().lower(): index for index, name in enumerate(header) if name is not None}

    required = ["description", "type", "amount"]
    missing = [name.title() for name in required if name not in columns]
    if missing:
        raise ValueError(f"The spreadsheet is missing these columns: {', '.join(missing)}.")

    def cell(row, name):
        index = columns.get(name.lower())
        return row[index] if index is not None and index < len(row) else None

    transactions = []
    for row_number, row in enumerate(rows, start=2):
        if all(value is None or str(value).strip() == "" for value in row):
            continue
        description = str(cell(row, "Description") or "").strip()
        transaction_type = str(cell(row, "Type") or "").strip().lower()
        category = str(cell(row, "Category") or "Other").strip() or "Other"
        amount = cell(row, "Amount")
        transaction_date = normalize_date(cell(row, "Date")) if "date" in columns else ""

        if not description:
            raise ValueError(f"Row {row_number}: Description is required.")
        if transaction_type not in ("income", "expense"):
            raise ValueError(f"Row {row_number}: Type must be Income or Expense.")
        amount = to_number(amount, f"Row {row_number} amount")
        if amount == 0:
            raise ValueError(f"Row {row_number} amount must be greater than zero.")

        transactions.append({
            "date": transaction_date,
            "description": description,
            "type": transaction_type,
            "category": category,
            "amount": f"{amount:.2f}",
        })

    budget = 0.0
    savings_goal = 0.0
    savings_saved = 0.0
    if "Summary" in workbook.sheetnames:
        for label, value, *_ in workbook["Summary"].iter_rows(min_col=1, max_col=2, values_only=True):
            key = str(label or "").strip().lower()
            if key == "monthly budget":
                budget = to_number(value or 0, "Budget")
            elif key == "savings goal":
                savings_goal = to_number(value or 0, "Savings goal")
            elif key == "current savings":
                savings_saved = to_number(value or 0, "Current savings")

    workbook.close()
    if not transactions:
        raise ValueError("No transactions were found in the spreadsheet.")
    return transactions, budget, savings_goal, savings_saved


def build_spreadsheet(transactions, budget, savings_goal=0, savings_saved=0):
    summary = calculate_summary(transactions, budget)
    workbook = Workbook()
    money = '"$"#,##0.00'
    bold = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="E8EEE9")

    sheet = workbook.active
    sheet.title = "Transactions"
    sheet.append(SPREADSHEET_COLUMNS)
    for transaction in transactions:
        sheet.append([
            normalize_date(transaction.get("date", "")),
            str(transaction.get("description", "")).strip(),
            str(transaction.get("type", "")).title(),
            transaction.get("category", "Other") if transaction.get("type") == "expense" else "",
            float(transaction.get("amount")),
        ])
    for cell in sheet[1]:
        cell.font = bold
        cell.fill = header_fill
    for row in sheet.iter_rows(min_row=2, min_col=5, max_col=5):
        row[0].number_format = money
    for column, width in zip("ABCDE", (14, 40, 12, 18, 14)):
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"

    totals = workbook.create_sheet("Summary")
    totals.append(["Item", "Value"])
    totals.append(["Total income", summary["income"]])
    totals.append(["Total expenses", summary["expenses"]])
    totals.append(["Money remaining", summary["remaining"]])
    totals.append(["Monthly budget", round(budget, 2)])
    totals.append(["Budget status", summary["budget_message"]])
    totals.append(["Budget used (%)", summary["budget_used_percent"]])
    totals.append(["Income spent (%)", summary["income_spent_percent"]])
    totals.append(["Savings goal", round(savings_goal, 2)])
    totals.append(["Current savings", round(savings_saved, 2)])
    totals.append([])
    totals.append(["Expense category", "Total"])
    for category, total in summary["categories"].items():
        if total:
            totals.append([category, total])

    for cell in totals[1]:
        cell.font = bold
        cell.fill = header_fill
    for cell in totals[11]:
        cell.font = bold
        cell.fill = header_fill
    for row in totals.iter_rows(min_row=2, min_col=2, max_col=2):
        label = str(totals.cell(row=row[0].row, column=1).value or "").lower()
        if "percent" not in label and "(%)" not in label and isinstance(row[0].value, (int, float)):
            row[0].number_format = money
    totals.column_dimensions["A"].width = 24
    totals.column_dimensions["B"].width = 24

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/summary", methods=["POST"])
def api_summary():
    try:
        transactions, budget, _, _ = validate_request(request.get_json(silent=True))
        return jsonify(calculate_summary(transactions, budget))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/import", methods=["POST"])
def api_import():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Choose an Excel .xlsx file first."}), 400
    if not file.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Only Excel .xlsx files are supported."}), 400
    try:
        transactions, budget, savings_goal, savings_saved = read_spreadsheet(file.stream)
        return jsonify({
            "transactions": transactions,
            "budget": f"{budget:.2f}",
            "savings_goal": f"{savings_goal:.2f}",
            "savings_saved": f"{savings_saved:.2f}",
        })
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/export", methods=["POST"])
def api_export():
    try:
        transactions, budget, savings_goal, savings_saved = validate_request(request.get_json(silent=True))
        output = build_spreadsheet(transactions, budget, savings_goal, savings_saved)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return send_file(
        output,
        as_attachment=True,
        download_name=f"budget_{date.today().isoformat()}.xlsx",
        mimetype=XLSX_MIMETYPE,
    )


@app.route("/api/exchange-rates")
def exchange_rates():
    try:
        response = requests.get(
            EXCHANGE_API_URL,
            params={"base": "usd", "quotes": "eur,gbp,mxn,cad,jpy"},
            timeout=5,
        )
        response.raise_for_status()
        api_data = response.json()
        rates = {}
        rate_date = None
        for item in api_data:
            quote = item.get("quote")
            rate = item.get("rate")
            if quote and rate is not None:
                rates[quote.upper()] = rate
            if rate_date is None:
                rate_date = item.get("date")
        return jsonify({"base": "USD", "date": rate_date, "rates": rates, "source": "Frankfurter"})
    except requests.RequestException:
        return jsonify({"error": "Exchange-rate service is temporarily unavailable."}), 503


@app.route("/api/convert", methods=["POST"])
def convert_currency():
    data = request.get_json(silent=True) or {}
    try:
        amount = to_number(data.get("amount"), "Amount")
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    from_currency = str(data.get("from", "USD")).upper().strip()
    to_currency = str(data.get("to", "EUR")).upper().strip()
    allowed = {"USD", "EUR", "GBP", "MXN", "CAD", "JPY"}
    if from_currency not in allowed or to_currency not in allowed:
        return jsonify({"error": "Unsupported currency selection."}), 400
    if from_currency == to_currency:
        return jsonify({"amount": amount, "converted": amount, "rate": 1.0, "from": from_currency, "to": to_currency})

    try:
        response = requests.get(
            EXCHANGE_API_URL,
            params={"base": from_currency.lower(), "quotes": to_currency.lower()},
            timeout=5,
        )
        response.raise_for_status()
        api_data = response.json()
        if not api_data:
            raise ValueError("No conversion rate was returned.")
        rate = float(api_data[0]["rate"])
        converted = amount * rate
        return jsonify({
            "amount": round(amount, 2),
            "converted": round(converted, 2),
            "rate": rate,
            "from": from_currency,
            "to": to_currency,
            "date": api_data[0].get("date"),
        })
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return jsonify({"error": "Currency conversion is temporarily unavailable."}), 503


if __name__ == "__main__":
    app.run(debug=True)
