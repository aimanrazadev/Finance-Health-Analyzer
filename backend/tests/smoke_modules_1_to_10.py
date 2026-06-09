from io import BytesIO
from pathlib import Path
import sys
from uuid import uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def assert_success(response, label):
    if response.status_code >= 400:
        raise AssertionError(f"{label} failed: {response.status_code} {response.text}")
    return response.json() if response.content else None


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def run_smoke_test():
    email = f"smoke-{uuid4().hex[:10]}@example.com"
    password = "SmokeTest123"

    register = client.post(
        "/auth/register",
        json={"name": "Smoke Test", "email": email, "password": password},
    )
    auth = assert_success(register, "register")
    headers = auth_headers(auth["access_token"])

    assert_success(client.get("/auth/me", headers=headers), "current user")

    categories = assert_success(client.get("/categories/"), "categories")
    food = next(item for item in categories if item["name"] == "Food")
    salary = next(item for item in categories if item["name"] == "Salary")

    transactions = [
        {
            "amount": 8000,
            "category_id": salary["id"],
            "description": "Salary credit",
            "merchant": "Employer",
            "transaction_type": "income",
            "date": "2026-06-01T09:00:00",
        },
        {
            "amount": 250,
            "category_id": None,
            "description": "McDonalds dinner",
            "merchant": "McDonalds",
            "transaction_type": "expense",
            "date": "2026-06-05T20:00:00",
        },
        {
            "amount": 180,
            "category_id": None,
            "description": "Uber ride",
            "merchant": "Uber",
            "transaction_type": "expense",
            "date": "2026-06-07T11:00:00",
        },
        {
            "amount": 60,
            "category_id": None,
            "description": "Netflix monthly payment",
            "merchant": "Netflix",
            "transaction_type": "expense",
            "date": "2026-06-08T12:00:00",
        },
    ]

    for index, payload in enumerate(transactions, start=1):
        assert_success(client.post("/transactions/", json=payload, headers=headers), f"transaction {index}")

    transaction_list = assert_success(client.get("/transactions/", headers=headers), "transaction list")
    assert len(transaction_list) >= 4

    dashboard = assert_success(
        client.get("/dashboard/summary?month=6&year=2026", headers=headers),
        "dashboard summary",
    )
    assert dashboard["total_income"] >= 8000
    assert dashboard["transaction_count"] >= 4

    charts = assert_success(
        client.get("/dashboard/charts?month=6&year=2026", headers=headers),
        "dashboard charts",
    )
    assert "category_breakdown" in charts

    budget = assert_success(
        client.post(
            "/budgets/",
            json={
                "category_id": food["id"],
                "monthly_limit": 1000,
                "month": 6,
                "year": 2026,
                "alert_threshold": 80,
            },
            headers=headers,
        ),
        "create budget",
    )
    assert budget["status"] in {"under_budget", "alert", "over_budget"}

    budgets = assert_success(
        client.get("/budgets/?month=6&year=2026", headers=headers),
        "budget list",
    )
    assert len(budgets) >= 1

    csv_bytes = b"date,description,amount,merchant\n2026-06-10,Amazon order,-120,Amazon\n2026-06-11,Bonus,500,Employer\n"
    preview = client.post(
        "/upload/preview",
        headers=headers,
        files={"file": ("statement.csv", BytesIO(csv_bytes), "text/csv")},
    )
    preview_data = assert_success(preview, "upload preview")
    assert preview_data["valid_rows"] == 2

    confirm = assert_success(
        client.post(
            "/upload/confirm",
            json={
                "file_name": preview_data["file_name"],
                "file_size": preview_data["file_size"],
                "rows": preview_data["rows"],
            },
            headers=headers,
        ),
        "upload confirm",
    )
    assert confirm["saved_transactions"] == 2

    history = assert_success(client.get("/upload/history", headers=headers), "upload history")
    assert len(history) >= 1

    insights = assert_success(
        client.get("/ai/insights?month=6&year=2026&regenerate=true", headers=headers),
        "ai insights",
    )
    assert len(insights["insights"]) >= 1

    print("Smoke test passed for modules 1-10.")


if __name__ == "__main__":
    run_smoke_test()
