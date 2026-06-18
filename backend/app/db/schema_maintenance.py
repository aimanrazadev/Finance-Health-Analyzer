from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn

from app.db.database import Base, engine


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
            connection.execute(text("UPDATE transactions SET is_needs_review = 0 WHERE is_needs_review IS NULL"))
            connection.execute(text("UPDATE transactions SET is_friend_transaction = 0 WHERE is_friend_transaction IS NULL"))
            connection.execute(text("UPDATE transactions SET review_status = 'approved' WHERE review_status IS NULL"))
        if "friends" in existing_tables:
            connection.execute(text("UPDATE friends SET is_active = 1 WHERE is_active IS NULL"))
        if "friend_merchant_learning" in existing_tables:
            friend_learning_columns = {
                column["name"]
                for column in inspector.get_columns("friend_merchant_learning")
            }
            if "raw_transaction_text" in friend_learning_columns:
                # Older local schemas created this as required, but the current
                # friend learning model stores the reusable text in merchant_pattern.
                connection.execute(
                    text(
                        "ALTER TABLE friend_merchant_learning "
                        "MODIFY COLUMN raw_transaction_text TEXT NULL"
                    )
                )
            if "normalized_text" in friend_learning_columns:
                # Kept only for compatibility with old local databases.
                connection.execute(
                    text(
                        "ALTER TABLE friend_merchant_learning "
                        "MODIFY COLUMN normalized_text VARCHAR(150) NULL"
                    )
                )
