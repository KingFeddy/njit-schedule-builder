from __future__ import annotations
from pydantic import BaseModel
from .schedule import SectionResponse


class CourseResponse(BaseModel):
    course_code: str
    title: str | None
    credits: int


class CourseDetailResponse(BaseModel):
    course_code: str
    title: str | None
    credits: int
    prerequisites: list[str]
    sections: list[SectionResponse]


class ProfessorResponse(BaseModel):
    rmp_score: float | None
    rmp_difficulty: float | None
    rmp_would_take_again: float | None
    rmp_num_ratings: int | None
    rmp_tags: list[str]
    department: str | None
