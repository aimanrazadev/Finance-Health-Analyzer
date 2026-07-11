from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import ImportProfile, User
from app.schemas.schemas import ImportProfileCreate, ImportProfileResponse
from app.services.import_profile_service import serialize_import_profile

router = APIRouter(prefix="/import-profiles", tags=["import profiles"])


@router.get("", response_model=list[ImportProfileResponse])
def get_import_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profiles = (
        db.query(ImportProfile)
        .filter(ImportProfile.user_id == current_user.id, ImportProfile.file_type == "pdf")
        .order_by(ImportProfile.last_used_at.desc(), ImportProfile.created_at.desc())
        .all()
    )
    return [serialize_import_profile(profile) for profile in profiles]


@router.post("", response_model=ImportProfileResponse, status_code=status.HTTP_201_CREATED)
def create_import_profile(
    payload: ImportProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import json

    profile = ImportProfile(
        user_id=current_user.id,
        profile_name=payload.profile_name,
        bank_name=payload.bank_name,
        file_type="pdf",
        header_signature=payload.header_signature,
        column_mapping=json.dumps(payload.column_mapping, ensure_ascii=True),
        preferences=json.dumps(payload.preferences, ensure_ascii=True),
        confidence_score=payload.confidence_score,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return serialize_import_profile(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_import_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(ImportProfile).filter(ImportProfile.id == profile_id, ImportProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import profile not found")
    db.delete(profile)
    db.commit()
