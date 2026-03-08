from pydantic import BaseModel, EmailStr, Field


class DesignerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    whatsapp: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=250)


class ViewerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr


class ProjectCreate(BaseModel):
    designer_id: int
    title: str = Field(min_length=2, max_length=180)
    description: str | None = None
    category: str = Field(min_length=2, max_length=80)
