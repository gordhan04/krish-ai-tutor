import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.user import User, Student
from app.models.curriculum import (
    Subject,
    Book,
    Chapter,
    Section,
    Topic,
    Concept,
    LearningObjective,
    ContentChunk,
)
from app.models.assessment import Question, QuestionOption, QuestionRubric
from app.models.learning import ConceptMastery, Misconception
from app.models.gamification import StudentXP, Streak, DailyMission
from app.api.v1 import (
    auth,
    curriculum,
    tutor,
    assessment,
    student as student_api,
    parent as parent_api,
    voice as voice_api,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("krish_ai_tutor")


async def seed_initial_curriculum_data():
    """Seeds Krish's student profile and NCERT Class 8 Science Chapter 11."""
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        res = await db.execute(select(User).where(User.email == "krish@school.edu"))
        if res.scalars().first():
            logger.info("Database already seeded. Skipping.")
            return

        logger.info("Seeding initial database with Krish (Class 8) and Science Chapter 11...")

        # 1. Parent User
        parent_user = User(
            email="parent@school.edu",
            hashed_password=get_password_hash("parent123"),
            role="parent",
        )
        db.add(parent_user)
        await db.flush()

        # 2. Create Student User & Profile (linked to parent)
        user = User(
            email="krish@school.edu",
            hashed_password=get_password_hash("krish123"),
            role="student",
        )
        db.add(user)
        await db.flush()

        student = Student(
            user_id=user.id,
            parent_id=parent_user.id,
            display_name="Krish",
            grade_level=8,
        )
        db.add(student)
        await db.flush()

        # 3. Gamification Records
        xp = StudentXP(student_id=student.id, total_xp=150, current_level=2)
        streak = Streak(
            student_id=student.id,
            current_streak=3,
            longest_streak=5,
            planned_days_target=16,
            days_completed_count=3,
            grace_days_available=2,
        )
        mission = DailyMission(
            student_id=student.id,
            title="Master Chemical Effects of Electric Current",
            subject_name="Science",
            chapter_name="Chemical Effects of Electric Current",
            target_concepts_count=2,
            completed_concepts_count=0,
            target_questions_count=5,
            completed_questions_count=0,
            target_weak_remedies_count=1,
            completed_weak_remedies_count=0,
            estimated_minutes=12,
            is_completed=False,
            xp_reward=100,
        )
        db.add_all([xp, streak, mission])

        # 4. Subject: Science (Class 8)
        subject = Subject(
            name="Science",
            grade_level=8,
            icon="atom",
        )
        db.add(subject)
        await db.flush()

        # 5. Book: NCERT Science Class 8
        book = Book(
            subject_id=subject.id,
            title="NCERT Science Class 8",
            publisher="NCERT",
            edition="2024-25 Edition",
        )
        db.add(book)
        await db.flush()

        # 6. Chapter 11: Chemical Effects of Electric Current
        chapter = Chapter(
            book_id=book.id,
            chapter_number=11,
            title="Chemical Effects of Electric Current",
            description="Explore how electricity conducts through liquids, electrolysis, and the process of electroplating.",
        )
        db.add(chapter)
        await db.flush()

        # 7. Section 11.1: Do Liquids Conduct Electricity?
        section = Section(
            chapter_id=chapter.id,
            section_number="11.1",
            title="Do Liquids Conduct Electricity?",
        )
        db.add(section)
        await db.flush()

        # 8. Topic: Conductors and Insulators in Liquids
        topic = Topic(
            section_id=section.id,
            title="Conductors and Insulators in Liquids",
            order_index=1,
        )
        db.add(topic)
        await db.flush()

        # 9. Concept: Electrolytes & Liquid Conductivity
        concept = Concept(
            topic_id=topic.id,
            name="Electrolytes & Ionic Conductivity",
            summary="Pure distilled water is an insulator. Solutions of salts, acids, or bases dissociate into ions which conduct electricity.",
            difficulty_tier=2,
        )
        db.add(concept)
        await db.flush()

        # 10. Learning Objective
        obj = LearningObjective(
            topic_id=topic.id,
            concept_id=concept.id,
            statement="Distinguish between poor conducting and good conducting liquids using the concept of dissolved ions.",
            bloom_taxonomy_level="Understanding",
        )
        db.add(obj)

        # 11. Content Chunks (Grounded Textbook Data)
        chunk1 = ContentChunk(
            book_id=book.id,
            chapter_id=chapter.id,
            topic_id=topic.id,
            concept_id=concept.id,
            page_number=140,
            content_type="explanation",
            chunk_text=(
                "Most liquids that conduct electricity are solutions of acids, bases and salts. "
                "When electric current flows through a conducting solution, it causes chemical reactions. "
                "Water that we get from sources such as taps, hand pumps, wells and ponds is not pure. "
                "It contains several mineral salts dissolved in it. A small amount of mineral salts is naturally present in it. "
                "This water is thus a good conductor of electricity. On the other hand, distilled water is free of salts and is a poor conductor."
            ),
        )
        chunk2 = ContentChunk(
            book_id=book.id,
            chapter_id=chapter.id,
            topic_id=topic.id,
            concept_id=concept.id,
            page_number=141,
            content_type="experiment",
            chunk_text=(
                "Activity 11.2: Take about two teaspoonfuls of distilled water in a clean and dry plastic bottle cap. "
                "Use the tester to check whether distilled water conducts electricity. What do you find? Distilled water does not conduct electricity. "
                "Now dissolve a pinch of common salt in distilled water. Again test with the tester. What do you conclude now? "
                "When common salt is dissolved in distilled water, we obtain salt solution. This is a conductor of electricity."
            ),
        )
        db.add_all([chunk1, chunk2])

        # 12. Questions for Concept 1 (Calibrated across Bloom Levels 1-5)
        # Level 1: Recall (MCQ)
        q1_l1 = Question(
            topic_id=topic.id,
            concept_id=concept.id,
            question_type="mcq",
            cognitive_level=1,
            prompt="Which of the following liquids is a poor conductor of electricity?",
            explanation="Distilled water contains no dissolved mineral salts or ions, making it an electrical insulator.",
            source_page=140,
        )
        db.add(q1_l1)
        await db.flush()
        db.add_all([
            QuestionOption(question_id=q1_l1.id, option_key="A", option_text="Pure distilled water", is_correct=True, feedback="Spot on! Distilled water is free of dissolved salts and is a poor conductor."),
            QuestionOption(question_id=q1_l1.id, option_key="B", option_text="Tap water", is_correct=False, feedback="Tap water contains natural minerals and conducts electricity."),
            QuestionOption(question_id=q1_l1.id, option_key="C", option_text="Lemon juice", is_correct=False, feedback="Lemon juice contains citric acid which conducts electricity."),
            QuestionOption(question_id=q1_l1.id, option_key="D", option_text="Vinegar", is_correct=False, feedback="Vinegar contains acetic acid which acts as an electrolyte."),
        ])

        # Level 2: Understanding (MCQ) - Original q1
        q1 = Question(
            topic_id=topic.id,
            concept_id=concept.id,
            question_type="mcq",
            cognitive_level=2,
            prompt="Why does tap water conduct electricity, whereas pure distilled water does not?",
            explanation="Tap water contains dissolved mineral salts that break into free ions capable of carrying electric current. Distilled water lacks these ions.",
            source_page=140,
        )
        db.add(q1)
        await db.flush()

        opt1 = QuestionOption(
            question_id=q1.id,
            option_key="A",
            option_text="Tap water has dissolved mineral salts providing free ions, while distilled water has no dissolved salts.",
            is_correct=True,
            feedback="Spot on! Dissolved salts form the charged ions that complete the electric circuit.",
        )
        opt2 = QuestionOption(
            question_id=q1.id,
            option_key="B",
            option_text="Distilled water is too hot for electricity to flow through it.",
            is_correct=False,
            feedback="Temperature isn't the primary reason; it's the absence of dissolved mineral ions.",
        )
        opt3 = QuestionOption(
            question_id=q1.id,
            option_key="C",
            option_text="Tap water contains copper metal wires dissolved in it.",
            is_correct=False,
            feedback="Tap water doesn't have metal wires; it has microscopic mineral salts.",
        )
        opt4 = QuestionOption(
            question_id=q1.id,
            option_key="D",
            option_text="Neither tap water nor distilled water conducts electricity.",
            is_correct=False,
            feedback="Recall Activity 11.2: tap water easily conducts and lights up the tester.",
        )
        db.add_all([opt1, opt2, opt3, opt4])

        # Level 3: Application (MCQ)
        q1_l3 = Question(
            topic_id=topic.id,
            concept_id=concept.id,
            question_type="mcq",
            cognitive_level=3,
            prompt="A student sets up an electric tester with a magnetic compass. Which of these liquids will cause the compass needle to deflect, proving conduction?",
            explanation="Lemon juice has citric acid that dissociates into ions, carrying electric current and creating a magnetic field that deflects the compass needle.",
            source_page=141,
        )
        db.add(q1_l3)
        await db.flush()
        db.add_all([
            QuestionOption(question_id=q1_l3.id, option_key="A", option_text="Lemon juice", is_correct=True, feedback="Correct! Acidic solutions conduct and cause magnetic deflection."),
            QuestionOption(question_id=q1_l3.id, option_key="B", option_text="Distilled water", is_correct=False, feedback="Distilled water has no ions, so no current flows to deflect the compass needle."),
            QuestionOption(question_id=q1_l3.id, option_key="C", option_text="Sugar dissolved in pure water", is_correct=False, feedback="Sugar dissolved in water does not produce ions and does not conduct."),
            QuestionOption(question_id=q1_l3.id, option_key="D", option_text="Vegetable oil", is_correct=False, feedback="Oils do not contain ions and are electrical insulators."),
        ])

        # Level 4: Reasoning (Subjective Rubric)
        q2 = Question(
            topic_id=topic.id,
            concept_id=concept.id,
            question_type="rubric_explanation",
            cognitive_level=4,
            prompt="Explain in your own words: How does adding common salt to distilled water change its electrical conductivity?",
            explanation="Adding salt (NaCl) introduces sodium and chloride ions into distilled water. These mobile ions allow electric current to pass through the solution.",
            source_page=141,
        )
        db.add(q2)
        await db.flush()

        rubric2 = QuestionRubric(
            question_id=q2.id,
            expected_concepts=["dissolved ions", "salt dissociation", "mobile charge carriers", "current conduction"],
            required_points=["Salt dissolves to form ions", "Free ions conduct electric charge through liquid"],
            misconception_traps={
                "electrons": "Electrons flow freely through liquid water molecules",
                "pure water": "Pure water naturally conducts electricity like copper",
            },
            max_score=1.0,
        )
        db.add(rubric2)

        # Level 5: Challenge (Advanced Synthesis MCQ)
        q1_l5 = Question(
            topic_id=topic.id,
            concept_id=concept.id,
            question_type="mcq",
            cognitive_level=5,
            prompt="A student sets up two beakers: Beaker A contains pure distilled water with submerged electrodes; Beaker B contains pure distilled water with table sugar dissolved. When connected to a battery, neither tester conducts. What chemical addition to Beaker A will cause immediate current conduction, and why?",
            explanation="Adding dilute acid or mineral salt introduces mobile ions that conduct current. Sugar molecules in Beaker B do not ionize into charged particles.",
            source_page=142,
        )
        db.add(q1_l5)
        await db.flush()
        db.add_all([
            QuestionOption(question_id=q1_l5.id, option_key="A", option_text="Adding a few drops of dilute sulphuric acid or common salt to introduce mobile ions", is_correct=True, feedback="Spot on! Acids, bases, and salts dissociate into free ions that conduct electricity."),
            QuestionOption(question_id=q1_l5.id, option_key="B", option_text="Adding more distilled water to dilute the covalent bonds", is_correct=False, feedback="Adding more water adds no ions."),
            QuestionOption(question_id=q1_l5.id, option_key="C", option_text="Heating the water to 100°C to release free copper electrons", is_correct=False, feedback="Thermal boiling does not produce free electrons."),
            QuestionOption(question_id=q1_l5.id, option_key="D", option_text="Adding glucose powder to create organic charge carriers", is_correct=False, feedback="Glucose is a covalent molecule that does not dissociate into ions."),
        ])

        # 13. Concept 2: Electroplating Principles & Applications
        concept2 = Concept(
            topic_id=topic.id,
            name="Electroplating Principles & Applications",
            summary="Electroplating is the process of depositing a layer of any desired metal on another material by passing electric current through an electrolyte solution.",
            difficulty_tier=3,
        )
        db.add(concept2)
        await db.flush()

        # Questions for Concept 2 across Bloom levels 1-5
        c2_q1 = Question(
            topic_id=topic.id,
            concept_id=concept2.id,
            question_type="mcq",
            cognitive_level=1,
            prompt="In an electroplating circuit, to which battery terminal should the object to be electroplated be connected?",
            explanation="The object must be connected to the negative terminal (cathode) so positively charged metal ions are attracted to it and deposit.",
            source_page=144,
        )
        db.add(c2_q1)
        await db.flush()
        db.add_all([
            QuestionOption(question_id=c2_q1.id, option_key="A", option_text="Negative terminal (Cathode)", is_correct=True, feedback="Correct! Positive metal ions in solution are attracted to the negative electrode."),
            QuestionOption(question_id=c2_q1.id, option_key="B", option_text="Positive terminal (Anode)", is_correct=False, feedback="Incorrect; connecting to the positive terminal would cause the object to dissolve."),
            QuestionOption(question_id=c2_q1.id, option_key="C", option_text="Either terminal; polarity does not matter", is_correct=False, feedback="DC polarity is critical in electroplating."),
            QuestionOption(question_id=c2_q1.id, option_key="D", option_text="Directly to AC supply", is_correct=False, feedback="AC oscillates polarity and prevents uniform deposition."),
        ])

        c2_q2 = Question(
            topic_id=topic.id,
            concept_id=concept2.id,
            question_type="mcq",
            cognitive_level=2,
            prompt="During copper plating of an iron key in copper sulphate solution, what happens to the copper plate at the positive terminal?",
            explanation="Copper atoms from the positive plate lose electrons and dissolve into the solution as copper ions, keeping the electrolyte concentration constant.",
            source_page=145,
        )
        db.add(c2_q2)
        await db.flush()
        db.add_all([
            QuestionOption(question_id=c2_q2.id, option_key="A", option_text="It gradually dissolves into the solution to replace copper ions deposited on the key.", is_correct=True, feedback="Spot on! The copper anode dissolves at the same rate that copper deposits at the cathode."),
            QuestionOption(question_id=c2_q2.id, option_key="B", option_text="It gains iron atoms from the key.", is_correct=False, feedback="Iron stays on the key; only copper ions migrate."),
            QuestionOption(question_id=c2_q2.id, option_key="C", option_text="It becomes coated with white sulphate salt.", is_correct=False, feedback="Sulphate ions remain in solution; copper dissolves."),
            QuestionOption(question_id=c2_q2.id, option_key="D", option_text="It undergoes no chemical reaction.", is_correct=False, feedback="The copper anode is oxidized and consumed."),
        ])

        c2_q3 = Question(
            topic_id=topic.id,
            concept_id=concept2.id,
            question_type="mcq",
            cognitive_level=3,
            prompt="Why are bicycle handlebars and car rims electroplated with chromium rather than made of pure chromium?",
            explanation="Chromium is corrosion-resistant and shiny, but very expensive. Electroplating a thin layer over cheap iron gives strength and rust protection economically.",
            source_page=146,
        )
        db.add(c2_q3)
        await db.flush()
        db.add_all([
            QuestionOption(question_id=c2_q3.id, option_key="A", option_text="Chromium is expensive; plating a thin layer over cheap iron provides corrosion resistance economically.", is_correct=True, feedback="Exactly! Plating combines the strength of iron with the beauty and rust-resistance of chromium."),
            QuestionOption(question_id=c2_q3.id, option_key="B", option_text="Solid chromium is too soft to support weight.", is_correct=False, feedback="Chromium is extremely hard."),
            QuestionOption(question_id=c2_q3.id, option_key="C", option_text="Chromium only resists rust when in contact with iron.", is_correct=False, feedback="Chromium resists rust independently."),
            QuestionOption(question_id=c2_q3.id, option_key="D", option_text="Chromium is an insulator unless plated.", is_correct=False, feedback="Chromium is a good electrical conductor."),
        ])

        c2_q4 = Question(
            topic_id=topic.id,
            concept_id=concept2.id,
            question_type="rubric_explanation",
            cognitive_level=4,
            prompt="Explain why the blue color of copper sulphate solution does not fade during copper electroplating.",
            explanation="For every copper ion deposited on the negative cathode, an equivalent copper atom from the positive copper anode dissolves into the solution, keeping the concentration constant.",
            source_page=145,
        )
        db.add(c2_q4)
        await db.flush()
        db.add(QuestionRubric(
            question_id=c2_q4.id,
            expected_concepts=["copper ions", "cathode deposition", "anode dissolution", "equilibrium", "copper sulphate concentration"],
            required_points=["Copper deposits onto cathode", "Copper anode dissolves into solution at equal rate"],
            misconception_traps={"electrons": "Electrons carry copper through the liquid"},
            max_score=1.0,
        ))

        c2_q5 = Question(
            topic_id=topic.id,
            concept_id=concept2.id,
            question_type="rubric_explanation",
            cognitive_level=5,
            prompt="Explain the environmental hazards of electroplating factories and how industrial waste solutions must be managed according to pollution control guidelines.",
            explanation="Electroplating effluents contain toxic heavy metal ions and strong acids. They must undergo chemical neutralization and heavy metal precipitation in effluent treatment plants before discharge.",
            source_page=146,
        )
        db.add(c2_q5)
        await db.flush()
        db.add(QuestionRubric(
            question_id=c2_q5.id,
            expected_concepts=["toxic heavy metals", "acidic effluents", "water contamination", "effluent treatment plants"],
            required_points=["Electroplating waste contains toxic metals and acids", "Must be treated and neutralized in dedicated treatment plants"],
            misconception_traps={"safe": "Electroplating solutions are non-toxic and can be dumped in drains"},
            max_score=1.0,
        ))

        # 14. Initial Concept Mastery
        mastery = ConceptMastery(
            student_id=student.id,
            concept_id=concept.id,
            mastery_score=0.35,
            total_attempts=2,
            correct_attempts=1,
            evidence_count=2,
            recent_accuracy=0.50,
            historical_accuracy=0.50,
        )
        db.add(mastery)

        await db.commit()
        logger.info("Database seeding completed successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist (or handled via migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_initial_curriculum_data()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Adaptive, curriculum-grounded AI Tutor for Krish (Class 8).",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(curriculum.router, prefix=settings.API_V1_STR)
app.include_router(tutor.router, prefix=settings.API_V1_STR)
app.include_router(assessment.router, prefix=settings.API_V1_STR)
app.include_router(student_api.router, prefix=settings.API_V1_STR)
app.include_router(parent_api.router, prefix=settings.API_V1_STR)
app.include_router(voice_api.router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
