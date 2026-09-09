from pydantic import BaseModel
from typing import Optional


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str
    student_id: Optional[str] = None
    display_name: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None
    student_id: Optional[str] = None
