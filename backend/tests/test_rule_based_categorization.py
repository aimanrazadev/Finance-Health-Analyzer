from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.categorization import predict_category_name


SAMPLE_TRANSACTIONS = [
    ("McDonalds dinner", "", "Food"),
    ("KFC airport meal", "", "Food"),
    ("Albaik DMM branch", "", "Food"),
    ("Starbucks coffee", "", "Food"),
    ("Pizza delivery", "", "Food"),
    ("Grocery supermarket", "", "Food"),
    ("Restaurant lunch", "", "Food"),
    ("Bakery purchase", "", "Food"),
    ("Cafe latte", "", "Food"),
    ("Food delivery Zomato", "", "Food"),
    ("Uber trip", "", "Travel"),
    ("Careem ride", "", "Travel"),
    ("Metro card recharge", "", "Travel"),
    ("Fuel station", "", "Travel"),
    ("Petrol payment", "", "Travel"),
    ("Taxi fare", "", "Travel"),
    ("Parking fee", "", "Travel"),
    ("Bus ticket", "", "Travel"),
    ("Train pass", "", "Travel"),
    ("Transport card", "", "Travel"),
    ("Amazon order", "", "Shopping"),
    ("Noon electronics", "", "Shopping"),
    ("Zara clothes", "", "Shopping"),
    ("Mall retail purchase", "", "Shopping"),
    ("Fashion store", "", "Shopping"),
    ("Shopping center", "", "Shopping"),
    ("Shein checkout", "", "Shopping"),
    ("Boutique purchase", "", "Shopping"),
    ("Amazon Books", "", "Shopping"),
    ("Retail store", "", "Shopping"),
    ("Electricity bill", "", "Bills"),
    ("Water utility", "", "Bills"),
    ("Internet bill", "", "Bills"),
    ("STC mobile payment", "", "Bills"),
    ("Phone bill", "", "Bills"),
    ("Wifi subscription bill", "", "Bills"),
    ("Utility payment", "", "Bills"),
    ("Electric service", "", "Bills"),
    ("Mobile recharge", "", "Bills"),
    ("Home water bill", "", "Bills"),
    ("Netflix monthly payment", "", "Subscriptions"),
    ("Spotify premium", "", "Subscriptions"),
    ("YouTube subscription", "", "Subscriptions"),
    ("Apple Music", "", "Subscriptions"),
    ("Prime subscription", "", "Subscriptions"),
    ("Monthly subscription fee", "", "Subscriptions"),
    ("Salary credit", "", "Salary"),
    ("Payroll deposit", "", "Salary"),
    ("Performance bonus", "", "Salary"),
    ("Unknown merchant transfer", "", "Other"),
]


def test_50_sample_transactions_are_categorized_correctly():
    assert len(SAMPLE_TRANSACTIONS) == 50

    failures = []
    for description, merchant, expected in SAMPLE_TRANSACTIONS:
        actual = predict_category_name(description, merchant)
        if actual != expected:
            failures.append((description, expected, actual))

    assert not failures, failures


if __name__ == "__main__":
    test_50_sample_transactions_are_categorized_correctly()
    print("50 sample transactions categorized correctly.")
