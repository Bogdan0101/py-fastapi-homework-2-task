from typing import Optional, List

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import date, timedelta
from src.database.models import MovieStatusEnum


class Country(BaseModel):
    id: int
    code: str
    name: str | None = None


class Genre(BaseModel):
    id: int
    name: str


class Actor(BaseModel):
    id: int
    name: str


class Language(BaseModel):
    id: int
    name: str


class MovieBase(BaseModel):
    name: str = Field(..., max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    model_config = ConfigDict(from_attributes=True)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return v
        if v > date.today() + timedelta(days=365):
            raise ValueError("Date cannot be more than one year in the future.")
        return v


class MovieList(MovieBase):
    id: int


class MovieListResponseSchema(BaseModel):
    movies: List[MovieList]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class MovieDetail(MovieList):
    status: MovieStatusEnum
    budget: float
    revenue: float
    country: Country
    genres: List[Genre]
    actors: List[Actor]
    languages: List[Language]


class MovieCreate(MovieBase):
    status: MovieStatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]


class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return v
        if v > date.today() + timedelta(days=365):
            raise ValueError("Date cannot be more than one year in the future.")
        return v
