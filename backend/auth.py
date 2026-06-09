"""
Authentication API routes
- POST /auth/register - Register a new user
- POST /auth/login - Login and get tokens
- POST /auth/logout - Logout (invalidate token)
- GET /auth/me - Get current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import UserRegister, UserLogin, TokenResponse, UserResponse, MessageResponse
from models import User
from utils import hash_password, verify_password, create_access_token, create_refresh_token, get_user_id_from_token
from database import get_db
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["authentication"])

# Security scheme for Bearer token
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from token
    
    Args:
        credentials: HTTP Bearer credentials (token)
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    user_id = get_user_id_from_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


# ==================== Authentication Endpoints ====================

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    Args:
        user_data: User registration data (name, email, password)
        db: Database session
        
    Returns:
        TokenResponse with access token, refresh token, and user info
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email {user_data.email} already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password
    )
    
    # Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate tokens
    token_data = {"user_id": new_user.id, "email": new_user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT tokens
    
    Args:
        login_data: User login data (email, password)
        db: Database session
        
    Returns:
        TokenResponse with access token, refresh token, and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate tokens
    token_data = {"user_id": user.id, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    
    Args:
        current_user: Current user from token
        
    Returns:
        UserResponse with user details
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user (revoke token on frontend)
    
    Note: Token invalidation is handled on the frontend by removing the stored token.
    For additional security, maintain a token blacklist in production.
    
    Args:
        current_user: Current user from token
        
    Returns:
        Success message
    """
    return MessageResponse(message="Logged out successfully. Please remove token from storage.")


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh access token using existing authentication
    
    Args:
        current_user: Current user from token
        
    Returns:
        TokenResponse with new access token
    """
    token_data = {"user_id": current_user.id, "email": current_user.email}
    new_access_token = create_access_token(token_data)
    
    return TokenResponse(
        access_token=new_access_token,
        user=UserResponse.model_validate(current_user)
    )
