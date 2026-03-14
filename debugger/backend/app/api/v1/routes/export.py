import csv
import io
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, ReflectionResponse, HintEvent
from app.api.v1.schemas.export import (
    SessionExportResponse,
    SubmissionExportItem,
    ErrorExportItem,
    ReflectionExportItem,
    PredictionExportItem,
    HintEventExportItem,
)
from app.api.v1.deps.auth_guard import get_current_user_id

router = APIRouter()


@router.get("/export/session/{session_id}", response_model=SessionExportResponse)
async def export_session(
    session_id: UUID,
    format: Literal["json", "csv"] = "json",
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_user_id),
):
    # Submissions
    stmt = select(CodeSubmission).where(CodeSubmission.session_id == session_id).order_by(CodeSubmission.timestamp)
    result = await db.execute(stmt)
    submissions = result.scalars().all()

    # Errors via join
    stmt = (
        select(ErrorRecord, ExecutionResult.submission_id)
        .join(ExecutionResult, ErrorRecord.execution_result_id == ExecutionResult.id)
        .join(CodeSubmission, ExecutionResult.submission_id == CodeSubmission.id)
        .where(CodeSubmission.session_id == session_id)
    )
    result = await db.execute(stmt)
    error_rows = result.fetchall()

    # Reflections via join
    stmt = (
        select(ReflectionResponse)
        .join(CodeSubmission, ReflectionResponse.submission_id == CodeSubmission.id)
        .where(CodeSubmission.session_id == session_id)
    )
    result = await db.execute(stmt)
    reflections = result.scalars().all()

    # Predictions: submissions that have a non-null prediction field
    prediction_items = [
        PredictionExportItem(
            submission_id=s.id,
            timestamp=s.timestamp.isoformat(),
            prediction=s.prediction,
        )
        for s in submissions
        if s.prediction is not None
    ]

    # Hint events persisted at execution time
    stmt = (
        select(HintEvent)
        .where(HintEvent.session_id == session_id)
        .order_by(HintEvent.created_at)
    )
    result = await db.execute(stmt)
    hint_events = result.scalars().all()

    submission_items = [
        SubmissionExportItem(
            submission_id=s.id,
            timestamp=s.timestamp.isoformat(),
            code_text=s.code_text,
            prediction=s.prediction,
        )
        for s in submissions
    ]

    error_items = [
        ErrorExportItem(
            submission_id=sub_id,
            exception_type=err.exception_type,
            concept_category=err.concept_category,
            cognitive_skill=err.cognitive_skill,
        )
        for err, sub_id in error_rows
    ]

    reflection_items = [
        ReflectionExportItem(
            submission_id=r.submission_id,
            response_text=r.response_text,
            hint_unlocked=r.hint_unlocked,
            created_at=r.created_at.isoformat(),
        )
        for r in reflections
    ]

    hint_event_items = [
        HintEventExportItem(
            submission_id=h.submission_id,
            hint_text=h.hint_text,
            affected_line=h.affected_line,
            created_at=h.created_at.isoformat(),
        )
        for h in hint_events
    ]

    if format == "json":
        return SessionExportResponse(
            session_id=session_id,
            submissions=submission_items,
            errors=error_items,
            reflections=reflection_items,
            predictions=prediction_items,
            hints=hint_event_items,
        )

    # CSV: blank-line-separated sections
    output = io.StringIO()

    writer = csv.DictWriter(output, fieldnames=["submission_id", "timestamp", "code_text", "prediction"])
    writer.writeheader()
    for item in submission_items:
        writer.writerow({"submission_id": str(item.submission_id), "timestamp": item.timestamp, "code_text": item.code_text, "prediction": item.prediction or ""})

    output.write("\n")
    writer = csv.DictWriter(output, fieldnames=["submission_id", "exception_type", "concept_category", "cognitive_skill"])
    writer.writeheader()
    for item in error_items:
        writer.writerow({"submission_id": str(item.submission_id), "exception_type": item.exception_type, "concept_category": item.concept_category, "cognitive_skill": item.cognitive_skill or ""})

    output.write("\n")
    writer = csv.DictWriter(output, fieldnames=["submission_id", "response_text", "hint_unlocked", "created_at"])
    writer.writeheader()
    for item in reflection_items:
        writer.writerow({"submission_id": str(item.submission_id), "response_text": item.response_text, "hint_unlocked": item.hint_unlocked, "created_at": item.created_at})

    output.write("\n")
    writer = csv.DictWriter(output, fieldnames=["submission_id", "timestamp", "prediction"])
    writer.writeheader()
    for item in prediction_items:
        writer.writerow({"submission_id": str(item.submission_id), "timestamp": item.timestamp, "prediction": item.prediction or ""})

    output.write("\n")
    writer = csv.DictWriter(output, fieldnames=["submission_id", "hint_text", "affected_line", "created_at"])
    writer.writeheader()
    for item in hint_event_items:
        writer.writerow({"submission_id": str(item.submission_id), "hint_text": item.hint_text, "affected_line": item.affected_line or "", "created_at": item.created_at})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"},
    )
