import csv
import io
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query
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
from app.api.v1.deps.auth_guard import get_current_user_id, require_session_owner

router = APIRouter()

_CSV_CHUNK = 100  # rows flushed per yield in streaming CSV


@router.get("/export/session/{session_id}", response_model=SessionExportResponse)
async def export_session(
    session_id: UUID,
    format: Literal["json", "csv"] = "json",
    limit: int = Query(default=500, ge=1, le=2000, description="Max rows per section (JSON only)"),
    offset: int = Query(default=0, ge=0, description="Row offset (JSON only)"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    require_session_owner(session_id, user_id)

    if format == "json":
        # Paginated JSON — each section respects limit/offset independently.
        subs_result = await db.execute(
            select(CodeSubmission)
            .where(CodeSubmission.session_id == session_id)
            .order_by(CodeSubmission.timestamp)
            .offset(offset).limit(limit)
        )
        submissions = subs_result.scalars().all()

        errors_result = await db.execute(
            select(ErrorRecord, ExecutionResult.submission_id)
            .join(ExecutionResult, ErrorRecord.execution_result_id == ExecutionResult.id)
            .join(CodeSubmission, ExecutionResult.submission_id == CodeSubmission.id)
            .where(CodeSubmission.session_id == session_id)
            .offset(offset).limit(limit)
        )
        error_rows = errors_result.fetchall()

        reflections_result = await db.execute(
            select(ReflectionResponse)
            .join(CodeSubmission, ReflectionResponse.submission_id == CodeSubmission.id)
            .where(CodeSubmission.session_id == session_id)
            .offset(offset).limit(limit)
        )
        reflections = reflections_result.scalars().all()

        hints_result = await db.execute(
            select(HintEvent)
            .where(HintEvent.session_id == session_id)
            .order_by(HintEvent.created_at)
            .offset(offset).limit(limit)
        )
        hint_events = hints_result.scalars().all()

        return SessionExportResponse(
            session_id=session_id,
            submissions=[
                SubmissionExportItem(
                    submission_id=s.id, timestamp=s.timestamp.isoformat(),
                    code_text=s.code_text, prediction=s.prediction,
                ) for s in submissions
            ],
            errors=[
                ErrorExportItem(
                    submission_id=sub_id, exception_type=err.exception_type,
                    concept_category=err.concept_category, cognitive_skill=err.cognitive_skill,
                ) for err, sub_id in error_rows
            ],
            reflections=[
                ReflectionExportItem(
                    submission_id=r.submission_id, response_text=r.response_text,
                    hint_unlocked=r.hint_unlocked, created_at=r.created_at.isoformat(),
                ) for r in reflections
            ],
            predictions=[
                PredictionExportItem(
                    submission_id=s.id, timestamp=s.timestamp.isoformat(), prediction=s.prediction,
                ) for s in submissions if s.prediction is not None
            ],
            hints=[
                HintEventExportItem(
                    submission_id=h.submission_id, hint_text=h.hint_text,
                    affected_line=h.affected_line, created_at=h.created_at.isoformat(),
                ) for h in hint_events
            ],
        )

    # CSV: stream row-by-row using yield_per so the full dataset is never
    # held in memory. Each section is flushed every _CSV_CHUNK rows.
    async def _csv_stream():
        buf = io.StringIO()

        # --- Submissions ---
        writer = csv.DictWriter(buf, fieldnames=["submission_id", "timestamp", "code_text", "prediction"])
        writer.writeheader()
        n = 0
        async for row in await db.stream(
            select(CodeSubmission)
            .where(CodeSubmission.session_id == session_id)
            .order_by(CodeSubmission.timestamp)
            .execution_options(yield_per=_CSV_CHUNK)
        ):
            s = row[0]
            writer.writerow({"submission_id": str(s.id), "timestamp": s.timestamp.isoformat(),
                              "code_text": s.code_text, "prediction": s.prediction or ""})
            n += 1
            if n % _CSV_CHUNK == 0:
                yield buf.getvalue(); buf.seek(0); buf.truncate()
        yield buf.getvalue(); buf.seek(0); buf.truncate()

        # --- Errors ---
        buf.write("\n")
        writer = csv.DictWriter(buf, fieldnames=["submission_id", "exception_type", "concept_category", "cognitive_skill"])
        writer.writeheader()
        n = 0
        async for row in await db.stream(
            select(ErrorRecord, ExecutionResult.submission_id)
            .join(ExecutionResult, ErrorRecord.execution_result_id == ExecutionResult.id)
            .join(CodeSubmission, ExecutionResult.submission_id == CodeSubmission.id)
            .where(CodeSubmission.session_id == session_id)
            .execution_options(yield_per=_CSV_CHUNK)
        ):
            err, sub_id = row[0], row[1]
            writer.writerow({"submission_id": str(sub_id), "exception_type": err.exception_type,
                              "concept_category": err.concept_category, "cognitive_skill": err.cognitive_skill or ""})
            n += 1
            if n % _CSV_CHUNK == 0:
                yield buf.getvalue(); buf.seek(0); buf.truncate()
        yield buf.getvalue(); buf.seek(0); buf.truncate()

        # --- Reflections ---
        buf.write("\n")
        writer = csv.DictWriter(buf, fieldnames=["submission_id", "response_text", "hint_unlocked", "created_at"])
        writer.writeheader()
        n = 0
        async for row in await db.stream(
            select(ReflectionResponse)
            .join(CodeSubmission, ReflectionResponse.submission_id == CodeSubmission.id)
            .where(CodeSubmission.session_id == session_id)
            .execution_options(yield_per=_CSV_CHUNK)
        ):
            r = row[0]
            writer.writerow({"submission_id": str(r.submission_id), "response_text": r.response_text,
                              "hint_unlocked": r.hint_unlocked, "created_at": r.created_at.isoformat()})
            n += 1
            if n % _CSV_CHUNK == 0:
                yield buf.getvalue(); buf.seek(0); buf.truncate()
        yield buf.getvalue(); buf.seek(0); buf.truncate()

        # --- Hint events ---
        buf.write("\n")
        writer = csv.DictWriter(buf, fieldnames=["submission_id", "hint_text", "affected_line", "created_at"])
        writer.writeheader()
        n = 0
        async for row in await db.stream(
            select(HintEvent)
            .where(HintEvent.session_id == session_id)
            .order_by(HintEvent.created_at)
            .execution_options(yield_per=_CSV_CHUNK)
        ):
            h = row[0]
            writer.writerow({"submission_id": str(h.submission_id), "hint_text": h.hint_text,
                              "affected_line": h.affected_line or "", "created_at": h.created_at.isoformat()})
            n += 1
            if n % _CSV_CHUNK == 0:
                yield buf.getvalue(); buf.seek(0); buf.truncate()
        yield buf.getvalue()

    return StreamingResponse(
        _csv_stream(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"},
    )
