from app import calculate_summary


def show_test(name, transactions, budget):
    result = calculate_summary(transactions, budget)
    print(f"\n{name}")
    print("-" * len(name))
    print(result)


if __name__ == "__main__":
    show_test(
        "No budget set",
        [
            {"description": "Pay", "type": "income", "amount": 3000},
            {"description": "Vet", "type": "expense", "amount": 125, "category": "Pets"},
        ],
        0,
    )

    show_test(
        "Over budget by $200",
        [
            {"description": "Pay", "type": "income", "amount": 1500},
            {"description": "Expenses", "type": "expense", "amount": 1200, "category": "Other"},
        ],
        1000,
    )
