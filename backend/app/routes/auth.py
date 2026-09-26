from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    try:
        user = auth_service.register(payload.name, str(payload.email), payload.password)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return AuthResponse(user=user, access_token=auth_service.issue_token(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    user = auth_service.authenticate(str(payload.email), payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return AuthResponse(user=user, access_token=auth_service.issue_token(user))
