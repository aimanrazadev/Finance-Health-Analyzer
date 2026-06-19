from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn

from app.db.database import Base, SessionLocal, engine


FRIEND_UNIQUE_INDEXES = {
    "friends": {
        "uq_friends_user_normalized_name": (
            "CREATE UNIQUE INDEX uq_friends_user_normalized_name "
            "ON friends (user_id, normalized_name)"
        ),
    },
    "friend_transaction_links": {
        "uq_friend_links_user_transaction": (
            "CREATE UNIQUE INDEX uq_friend_links_user_transaction "
            "ON friend_transaction_links (user_id, transaction_id)"
        ),
    },
    "friend_merchant_learning": {
        "uq_friend_learning_user_friend_merchant": (
            "CREATE UNIQUE INDEX uq_friend_learning_user_friend_merchant "
            "ON friend_merchant_learning (user_id, friend_id, normalized_merchant)"
        ),
    },
}


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

    _repair_friend_data_before_constraints()
    _ensure_friend_unique_indexes()


def _repair_friend_data_before_constraints() -> None:
    """Merge old duplicate friend rows before adding uniqueness indexes."""
    db = SessionLocal()
    try:
        from app.services.friend_service import sync_friends_category_transactions

        sync_friends_category_transactions(db)
        db.commit()
    finally:
        db.close()

    with engine.begin() as connection:
        _merge_duplicate_friend_rows(connection)
        connection.execute(
            text(
                "DELETE link_duplicate FROM friend_transaction_links link_duplicate "
                "JOIN friend_transaction_links link_primary "
                "ON link_duplicate.user_id = link_primary.user_id "
                "AND link_duplicate.transaction_id = link_primary.transaction_id "
                "AND link_duplicate.id > link_primary.id"
            )
        )
        connection.execute(
            text(
                "DELETE learning_duplicate FROM friend_merchant_learning learning_duplicate "
                "JOIN friend_merchant_learning learning_primary "
                "ON learning_duplicate.user_id = learning_primary.user_id "
                "AND learning_duplicate.friend_id = learning_primary.friend_id "
                "AND learning_duplicate.normalized_merchant = learning_primary.normalized_merchant "
                "AND learning_duplicate.id > learning_primary.id "
                "WHERE learning_duplicate.normalized_merchant IS NOT NULL"
            )
        )


def _merge_duplicate_friend_rows(connection) -> None:
    """Merge duplicate friend rows directly in SQL before unique indexes exist."""
    duplicate_groups = connection.execute(
        text(
            "SELECT user_id, normalized_name, MIN(id) AS primary_id "
            "FROM friends "
            "WHERE normalized_name IS NOT NULL "
            "AND normalized_name NOT LIKE '%__merged_%' "
            "GROUP BY user_id, normalized_name "
            "HAVING COUNT(*) > 1"
        )
    ).mappings().all()

    for group in duplicate_groups:
        duplicate_ids = [
            row["id"]
            for row in connection.execute(
                text(
                    "SELECT id FROM friends "
                    "WHERE user_id = :user_id "
                    "AND normalized_name = :normalized_name "
                    "AND id <> :primary_id"
                ),
                {
                    "user_id": group["user_id"],
                    "normalized_name": group["normalized_name"],
                    "primary_id": group["primary_id"],
                },
            ).mappings().all()
        ]

        if not duplicate_ids:
            continue

        for duplicate_id in duplicate_ids:
            params = {
                "user_id": group["user_id"],
                "primary_id": group["primary_id"],
                "duplicate_id": duplicate_id,
            }
            connection.execute(
                text(
                    "UPDATE transactions "
                    "SET friend_id = :primary_id, is_friend_transaction = 1 "
                    "WHERE user_id = :user_id AND friend_id = :duplicate_id"
                ),
                params,
            )
            connection.execute(
                text(
                    "UPDATE friend_transaction_links "
                    "SET friend_id = :primary_id "
                    "WHERE user_id = :user_id AND friend_id = :duplicate_id"
                ),
                params,
            )
            connection.execute(
                text(
                    "UPDATE friend_merchant_learning "
                    "SET friend_id = :primary_id "
                    "WHERE user_id = :user_id AND friend_id = :duplicate_id"
                ),
                params,
            )
            connection.execute(
                text(
                    "UPDATE friends "
                    "SET is_active = 0, normalized_name = CONCAT(normalized_name, '__merged_', id) "
                    "WHERE id = :duplicate_id"
                ),
                params,
            )

        connection.execute(
            text("UPDATE friends SET is_active = 1 WHERE id = :primary_id"),
            {"primary_id": group["primary_id"]},
        )


def _ensure_friend_unique_indexes() -> None:
    """Create DB-level safeguards that prevent duplicate friend records."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name, indexes in FRIEND_UNIQUE_INDEXES.items():
            if table_name not in existing_tables:
                continue

            existing_index_names = {
                index["name"]
                for index in inspector.get_indexes(table_name)
            }
            for index_name, ddl in indexes.items():
                if index_name in existing_index_names:
                    continue
                connection.execute(text(ddl))
