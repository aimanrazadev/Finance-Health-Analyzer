from sqlalchemy.orm import Session

from app.models.models import Transaction
from app.utils.merchant_extractor import extract_transaction_merchant, is_noisy_payment_merchant


def clean_existing_transaction_merchants(db: Session) -> int:
    """Backfill old rows where merchant accidentally stored UPI/PCI/payment rail text."""
    updated_count = 0
    rows = db.query(Transaction).all()
    for transaction in rows:
        cleaned_merchant = extract_transaction_merchant(transaction.description, transaction.merchant)
        if not cleaned_merchant:
            continue

        should_replace_merchant = (
            not transaction.merchant
            or is_noisy_payment_merchant(transaction.merchant)
            or "/" in str(transaction.merchant)
            or "|" in str(transaction.merchant)
        )

        changed = False
        if transaction.extracted_merchant != cleaned_merchant:
            transaction.extracted_merchant = cleaned_merchant
            changed = True
        if should_replace_merchant and transaction.merchant != cleaned_merchant:
            transaction.merchant = cleaned_merchant
            changed = True

        if changed:
            updated_count += 1

    if updated_count:
        db.commit()
    return updated_count
