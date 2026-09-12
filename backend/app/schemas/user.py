from datetime import datetime
from pydantic import BaseModel,EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password:str
    full_name:str
    role:str

class UserLogin(BaseModel):
    email:EmailStr
    password:str

class UserResponse(BaseModel):
    id:int
    email:EmailStr
    full_name:str
    role:str
    is_active:bool
    created_at:datetime
    model_config={
        "from_attributes":True
    }
