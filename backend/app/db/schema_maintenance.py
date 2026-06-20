from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn

from app.db.database import Base, engine


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
            connection.execute(text("UPDATE transactions SET is_friend_transaction = 0 WHERE is_friend_transaction IS NULL"))
            connection.execute(text("UPDATE transactions SET is_needs_review = 0 WHERE is_needs_review IS NULL"))
            connection.execute(text("UPDATE transactions SET review_status = 'approved' WHERE review_status IS NULL"))

        _ensure_unique_indexes(connection, inspector, existing_tables)
