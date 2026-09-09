from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.curriculum import Subject, Book, Chapter, Section, Topic, Concept
from app.schemas.curriculum import SubjectOut, ChapterOut, TopicOut, ConceptOut

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


@router.get("/subjects", response_model=List[SubjectOut])
async def get_subjects(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Subject)
        .options(
            selectinload(Subject.books)
            .selectinload(Book.chapters)
            .selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.concepts),
            selectinload(Subject.books)
            .selectinload(Book.chapters)
            .selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.learning_objectives),
        )
    )
    result = await db.execute(stmt)
    subjects = result.scalars().all()
    return subjects


@router.get("/chapters/{chapter_id}", response_model=ChapterOut)
async def get_chapter_details(chapter_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(
            selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.concepts),
            selectinload(Chapter.sections)
            .selectinload(Section.topics)
            .selectinload(Topic.learning_objectives),
        )
    )
    result = await db.execute(stmt)
    chapter = result.scalars().first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.get("/topics/{topic_id}", response_model=TopicOut)
async def get_topic_details(topic_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Topic)
        .where(Topic.id == topic_id)
        .options(
            selectinload(Topic.concepts),
            selectinload(Topic.learning_objectives),
        )
    )
    result = await db.execute(stmt)
    topic = result.scalars().first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic
