from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ConceptOut(BaseModel):
    id: str
    name: str
    summary: str
    difficulty_tier: int

    model_config = ConfigDict(from_attributes=True)


class LearningObjectiveOut(BaseModel):
    id: str
    statement: str
    bloom_taxonomy_level: str

    model_config = ConfigDict(from_attributes=True)


class TopicOut(BaseModel):
    id: str
    title: str
    order_index: int
    concepts: List[ConceptOut] = []
    learning_objectives: List[LearningObjectiveOut] = []

    model_config = ConfigDict(from_attributes=True)


class SectionOut(BaseModel):
    id: str
    section_number: str
    title: str
    topics: List[TopicOut] = []

    model_config = ConfigDict(from_attributes=True)


class ChapterOut(BaseModel):
    id: str
    chapter_number: int
    title: str
    description: Optional[str] = None
    sections: List[SectionOut] = []

    model_config = ConfigDict(from_attributes=True)


class BookOut(BaseModel):
    id: str
    title: str
    publisher: str
    edition: str
    chapters: List[ChapterOut] = []

    model_config = ConfigDict(from_attributes=True)


class SubjectOut(BaseModel):
    id: str
    name: str
    grade_level: int
    icon: str
    books: List[BookOut] = []

    model_config = ConfigDict(from_attributes=True)
