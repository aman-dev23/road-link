"""Pydantic schemas for auth endpoints."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=40)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str
    expires_in: int  # seconds until access token expires


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class WSTicketResponse(BaseModel):
    ticket: str
    expires_in: int = 30
