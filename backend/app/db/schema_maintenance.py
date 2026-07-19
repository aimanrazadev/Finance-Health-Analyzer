from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn

from app.db.session import Base, engine


UNIQUE_INDEXES = {
    "friends": [
        ("uq_friends_user_normalized_name", "user_id, normalized_name"),
    ],
    "friend_transaction_links": [
        ("uq_friend_transaction_link", "friend_id, transaction_id"),
    ],
    "friend_merchant_learning": [
        ("uq_friend_learning_user_merchant", "user_id, normalized_merchant"),
    ],
}

MONEY_COLUMNS = {
    "transactions": {
        "amount": "DECIMAL(14,2) NOT NULL",
        "withdrawal_amount": "DECIMAL(14,2) NULL",
        "deposit_amount": "DECIMAL(14,2) NULL",
        "balance": "DECIMAL(14,2) NULL",
    },
    "uploaded_files": {
        "opening_balance": "DECIMAL(14,2) NULL",
        "closing_balance": "DECIMAL(14,2) NULL",
    },
    "friends": {"total_amount": "DECIMAL(14,2) NULL DEFAULT 0.00"},
    "subscriptions": {"amount": "DECIMAL(14,2) NOT NULL DEFAULT 0.00"},
}


def _ensure_unique_indexes(connection, inspector, existing_tables: set[str]) -> None:
    """Best-effort constraints for local MySQL schemas.

    Existing dirty duplicate records can make ALTER TABLE fail. We keep startup
    safe and still protect clean databases; the friend service also merges
    duplicates at runtime.
    """
    for table_name, indexes in UNIQUE_INDEXES.items():
        if table_name not in existing_tables:
            continue
        existing_index_names = {index["name"] for index in inspector.get_indexes(table_name)}
        for index_name, columns in indexes:
            if index_name in existing_index_names:
                continue
            try:
                connection.execute(text(f"ALTER TABLE {table_name} ADD UNIQUE INDEX {index_name} ({columns})"))
            except Exception:
                # Do not block app startup if an older database has duplicates.
                pass


def ensure_database_schema():
    """Create missing tables and add missing columns for local development.

    SQLAlchemy create_all creates new tables, but it does not alter existing
    tables. This keeps the local MySQL schema aligned while the project is still
    using create_all instead of Alembic migrations.
    """
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        # Import profiles were removed from the product. Drop the legacy table
        # after the model has been removed so existing deployments are cleaned up.
        if "import_profiles" in existing_tables:
            connection.execute(text("DROP TABLE import_profiles"))
            existing_tables.remove("import_profiles")

        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue

            existing_columns = {
                column["name"]
                for column in inspector.get_columns(table.name)
            }

            for column in table.columns:
                if column.name in existing_columns or column.primary_key:
                    continue

                column_ddl = str(CreateColumn(column).compile(dialect=engine.dialect))
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column_ddl}"))

        if "transactions" in existing_tables:
            connection.execute(text("""
                UPDATE transactions
                SET transaction_type = CASE
                    WHEN deposit_amount IS NOT NULL AND deposit_amount > 0 THEN 'income'
                    ELSE 'expense'
                END
                WHERE transaction_type NOT IN ('income', 'expense')
            """))
            connection.execute(text("UPDATE transactions SET is_friend_transaction = 0 WHERE is_friend_transaction IS NULL"))
            connection.execute(text("UPDATE transactions SET is_needs_review = 0 WHERE is_needs_review IS NULL"))
            connection.execute(text("UPDATE transactions SET review_status = 'approved' WHERE review_status IS NULL"))

        # Monetary values must retain paise exactly. FLOAT is approximate and
        # also allowed older schemas to obscure the intended two-decimal
        # contract, so normalize every persisted money column to DECIMAL.
        for table_name, column_definitions in MONEY_COLUMNS.items():
            if table_name not in existing_tables:
                continue
            existing_column_names = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_definition in column_definitions.items():
                if column_name in existing_column_names:
                    connection.execute(text(
                        f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} {column_definition}"
                    ))

        _ensure_unique_indexes(connection, inspector, existing_tables)
