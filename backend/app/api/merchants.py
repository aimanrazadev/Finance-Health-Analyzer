from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.models import Merchant, User
from app.schemas.schemas import (
    MerchantDirectoryDetailResponse,
    MerchantMergeRequest,
    MerchantRenameRequest,
    MerchantResponse,
)
from app.services.merchant_service import (
    merge_merchants,
    merchant_detail,
    rename_merchant,
    serialize_merchant,
    sync_merchants_from_transactions,
)

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=list[MerchantResponse])
def get_merchants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchants = sync_merchants_from_transactions(db, current_user.id)
    return [serialize_merchant(merchant) for merchant in merchants]


@router.get("/{merchant_id}", response_model=MerchantDirectoryDetailResponse)
def get_merchant_detail(
    merchant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = merchant_detail(db, current_user.id, merchant_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    return detail


@router.put("/{merchant_id}/rename", response_model=MerchantResponse)
def rename_merchant_endpoint(
    merchant_id: int,
    payload: MerchantRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchant = rename_merchant(db, current_user.id, merchant_id, payload.canonical_name)
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    return serialize_merchant(merchant)


@router.post("/{merchant_id}/merge", response_model=MerchantResponse)
def merge_merchant_endpoint(
    merchant_id: int,
    payload: MerchantMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchant = merge_merchants(db, current_user.id, merchant_id, payload.source_merchant_id)
    if not merchant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not merge merchants")
    return serialize_merchant(merchant)


@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_merchant(
    merchant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id, Merchant.user_id == current_user.id).first()
    if not merchant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found")
    db.delete(merchant)
    db.commit()
