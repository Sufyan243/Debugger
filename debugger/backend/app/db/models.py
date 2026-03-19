import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, Boolean, Integer, DateTime, ForeignKey, func, text
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CodeSubmission(Base):
    __tablename__ = "code_submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    code_text: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    prediction: Mapped[Optional[str]] = mapped_column(Text)


class ExecutionResult(Base):
    __tablename__ = "execution_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("code_submissions.id", ondelete="CASCADE"), nullable=False)
    stdout: Mapped[Optional[str]] = mapped_column(Text)
    stderr: Mapped[Optional[str]] = mapped_column(Text)
    traceback: Mapped[Optional[str]] = mapped_column(Text)
    execution_time: Mapped[Optional[float]] = mapped_column(Float)
    success_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer)


class ErrorRecord(Base):
    __tablename__ = "error_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    execution_result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("execution_results.id", ondelete="CASCADE"), nullable=False)
    exception_type: Mapped[str] = mapped_column(String(100), nullable=False)
    concept_category: Mapped[str] = mapped_column(String(200), nullable=False)
    cognitive_skill: Mapped[Optional[str]] = mapped_column(String(200))
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ConceptCategory(Base):
    __tablename__ = "concept_categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    cognitive_skill: Mapped[Optional[str]] = mapped_column(String(200))


class HintSequence(Base):
    __tablename__ = "hint_sequences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    concept_category: Mapped[str] = mapped_column(String(200), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    tier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    hint_text: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (sa.UniqueConstraint('concept_category', 'tier', name='uq_concept_tier'),)


class ReflectionResponse(Base):
    __tablename__ = "reflection_responses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("code_submissions.id", ondelete="CASCADE"), nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    hint_unlocked: Mapped[bool] = mapped_column(Boolean, default=True)


class SolutionRequest(Base):
    __tablename__ = "solution_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("code_submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    solution_revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class MetacognitiveMetric(Base):
    __tablename__ = "metacognitive_metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_predictions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    correct_predictions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SessionOwnership(Base):
    """
    Maps a session_id to a server-issued owner_token.
    The owner_token is generated server-side on session registration and returned
    to the client once. All subsequent session-scoped requests must present it
    via X-Session-Token to prove ownership.
    """
    __tablename__ = "session_ownership"

    session_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    owner_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HintEvent(Base):
    __tablename__ = "hint_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("code_submissions.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    hint_text: Mapped[str] = mapped_column(Text, nullable=False)
    affected_line: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessionSnapshot(Base):
    __tablename__ = "session_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    date_bucket: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    submissions_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    concepts_learned: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    prediction_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        sa.UniqueConstraint('session_id', 'date_bucket', name='uq_snapshot_session_date'),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, server_default="email")
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint('provider', 'provider_id', name='uq_users_provider_id'),
    )


class AnonSession(Base):
    __tablename__ = "anon_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    merged_into: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
