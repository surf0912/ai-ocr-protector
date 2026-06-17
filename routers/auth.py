from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from deps import get_supabase, get_current_user
from supabase import Client

router = APIRouter()

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    username: str

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
def signup(body: SignUpRequest, sb: Client = Depends(get_supabase)):
    res = sb.auth.sign_up({
        "email": body.email,
        "password": body.password,
        "options": {"data": {"username": body.username}},
    })
    if res.user is None:
        raise HTTPException(400, "Signup failed")
    return {"message": "Check your email to confirm signup"}

@router.post("/signin")
def signin(body: SignInRequest, sb: Client = Depends(get_supabase)):
    res = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
    if res.session is None:
        raise HTTPException(401, "Invalid credentials")
    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
        "user": {"id": res.user.id, "email": res.user.email},
    }

@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user
