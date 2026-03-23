from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, ReflectionResponse, MetacognitiveMetric, SessionSnapshot
from datetime import date


async def get_concept_stats(session_id, db: AsyncSession) -> list[dict]:
    """
    Get concept statistics for the last 10 submissions.

    Metric definitions:
      - error_count: number of ErrorRecord rows for this concept in the window
      - attempts: total CodeSubmission rows in the session window (shared denominator,
        not scoped to error rows — avoids the tautology where attempts == errors)
      - mastery (frontend): 100 - (error_count / attempts * 100)
        A concept with 2 errors out of 10 total submissions = 80% mastery
      - success_streak: consecutive successful executions from most recent backward
    Returns: [{concept, error_count, attempts, success_streak}]
    """
    # Step 1: Get last 10 CodeSubmission IDs for session_id
    stmt = select(CodeSubmission.id).where(
        CodeSubmission.session_id == session_id
    ).order_by(desc(CodeSubmission.timestamp)).limit(10)
    result = await db.execute(stmt)
    submission_ids = [row[0] for row in result.fetchall()]
    
    if not submission_ids:
        return []
    
    # Total submissions in window — used as the shared attempts denominator for all
    # concepts so that mastery = 1 - (error_count / total_submissions), not 0% always.
    total_submissions = len(submission_ids)

    # Step 2-5: Join ExecutionResult → ErrorRecord, group by concept
    stmt = select(
        ErrorRecord.concept_category,
        func.count(ErrorRecord.id).label('error_count'),
    ).select_from(ExecutionResult).join(
        ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id
    ).where(
        ExecutionResult.submission_id.in_(submission_ids)
    ).group_by(ErrorRecord.concept_category)
    
    result = await db.execute(stmt)
    concept_data = result.fetchall()
    
    # Step 6: Compute success_streak per concept.
    # Fetch the full ordered submission window once (all submissions, all outcomes)
    # and walk it from most-recent backward. A streak for a concept breaks on the
    # first submission that has an ErrorRecord for that concept — unrelated failures
    # from other concepts do NOT break the streak, but they also do NOT extend it.
    # This matches the learner's actual experience: if they fix NameError but then
    # hit a TypeError, their NameError streak is unaffected.
    full_timeline_stmt = select(
        CodeSubmission.id,
        CodeSubmission.timestamp,
        ExecutionResult.success_flag,
        ErrorRecord.concept_category,
    ).select_from(
        CodeSubmission
    ).join(
        ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id
    ).outerjoin(
        ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id
    ).where(
        CodeSubmission.session_id == session_id,
        CodeSubmission.id.in_(submission_ids)
    ).order_by(desc(CodeSubmission.timestamp))

    full_result = await db.execute(full_timeline_stmt)
    full_timeline = full_result.fetchall()

    concept_stats = []
    for concept, error_count in concept_data:
        streak = 0
        for row in full_timeline:
            row_concept = row.concept_category
            row_success = row.success_flag
            if row_concept == concept:
                # This submission is directly relevant to this concept.
                if row_success:
                    # Successful run that had this concept's error previously
                    # — counts toward the streak.
                    streak += 1
                else:
                    # This concept failed on this submission — streak ends.
                    break
            elif row_concept is None and row_success:
                # Fully successful submission (no error record at all) — counts
                # toward every concept's streak.
                streak += 1
            # Failures from OTHER concepts do not break or extend this streak.

        concept_stats.append({
            'concept': concept,
            'error_count': error_count,
            'attempts': total_submissions,
            'success_streak': streak,
        })
    
    return concept_stats


async def get_weakness_profile(session_id, db: AsyncSession) -> list[dict]:
    """
    Get weakness profile: concepts with error_count >= 3, sorted by error_count desc.
    Returns: [{concept, error_count, attempts, success_streak}]
    """
    # Step 1: Call get_concept_stats
    stats = await get_concept_stats(session_id, db)
    
    # Step 2: Filter where error_count >= 3
    weak_concepts = [s for s in stats if s['error_count'] >= 3]
    
    # Step 3: Sort descending by error_count
    weak_concepts.sort(key=lambda x: x['error_count'], reverse=True)
    
    return weak_concepts


async def get_hint_dependency_ratio(session_id, db: AsyncSession) -> list[dict]:
    """
    Get hint dependency ratio per concept.
    Returns: [{concept, hints_used, attempts, ratio}]
    """
    # Step 1: Get last 10 CodeSubmission IDs
    stmt = select(CodeSubmission.id).where(
        CodeSubmission.session_id == session_id
    ).order_by(desc(CodeSubmission.timestamp)).limit(10)
    result = await db.execute(stmt)
    submission_ids = [row[0] for row in result.fetchall()]
    
    if not submission_ids:
        return []
    
    # Step 2-3: Get attempts per concept from ErrorRecord (distinct submissions)
    stmt = select(
        ErrorRecord.concept_category,
        func.count(func.distinct(ExecutionResult.submission_id)).label('attempts')
    ).select_from(ExecutionResult).join(
        ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id
    ).where(
        ExecutionResult.submission_id.in_(submission_ids)
    ).group_by(ErrorRecord.concept_category)
    
    result = await db.execute(stmt)
    concept_attempts = {row[0]: row[1] for row in result.fetchall()}
    
    # Step 4: Get hints_used per concept (distinct submissions with hints)
    stmt = select(
        ErrorRecord.concept_category,
        func.count(func.distinct(CodeSubmission.id)).label('hints_used')
    ).select_from(CodeSubmission).join(
        ReflectionResponse, CodeSubmission.id == ReflectionResponse.submission_id
    ).join(
        ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id
    ).join(
        ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id
    ).where(
        CodeSubmission.id.in_(submission_ids),
        ReflectionResponse.hint_unlocked == True
    ).group_by(ErrorRecord.concept_category)
    
    result = await db.execute(stmt)
    concept_hints = {row[0]: row[1] for row in result.fetchall()}
    
    # Step 5: Compute ratio
    ratios = []
    for concept, attempts in concept_attempts.items():
        hints_used = concept_hints.get(concept, 0)
        ratio = hints_used / attempts if attempts > 0 else 0.0
        ratios.append({
            'concept': concept,
            'hints_used': hints_used,
            'attempts': attempts,
            'ratio': ratio
        })
    
    return ratios


async def get_session_summary(session_id, db: AsyncSession) -> dict:
    """
    Get session summary statistics.
    Returns: {submissions_count, errors_count, concepts_learned, hints_used, prediction_accuracy}
    """
    # Step 1: submissions_count
    stmt = select(func.count(CodeSubmission.id)).where(
        CodeSubmission.session_id == session_id
    )
    result = await db.execute(stmt)
    submissions_count = result.scalar() or 0
    
    # Step 2: errors_count
    stmt = select(func.count(ErrorRecord.id)).select_from(
        CodeSubmission
    ).join(
        ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id
    ).join(
        ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id
    ).where(
        CodeSubmission.session_id == session_id
    )
    result = await db.execute(stmt)
    errors_count = result.scalar() or 0
    
    # Step 3: concepts_learned — single query.
    # A concept is "learned" if the most recent submission in the session
    # that touches that concept is a success (no ErrorRecord for it).
    # We find, per concept, the timestamp of its last error, then count
    # how many of those concepts have at least one successful submission
    # after that timestamp — all in one query using a lateral-style subquery.
    from sqlalchemy import literal_column
    last_error_subq = (
        select(
            ErrorRecord.concept_category,
            func.max(CodeSubmission.timestamp).label("last_error_time"),
        )
        .select_from(CodeSubmission)
        .join(ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id)
        .join(ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id)
        .where(CodeSubmission.session_id == session_id)
        .group_by(ErrorRecord.concept_category)
        .subquery()
    )
    success_after_subq = (
        select(last_error_subq.c.concept_category)
        .select_from(last_error_subq)
        .join(
            CodeSubmission,
            CodeSubmission.timestamp > last_error_subq.c.last_error_time,
        )
        .join(ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id)
        .where(
            CodeSubmission.session_id == session_id,
            ExecutionResult.success_flag.is_(True),
        )
        .distinct()
        .subquery()
    )
    concepts_learned_result = await db.execute(
        select(func.count()).select_from(success_after_subq)
    )
    concepts_learned = concepts_learned_result.scalar() or 0

    # Step 4: hints_used — count HintEvent rows for this session
    from app.db.models import HintEvent
    stmt = select(func.count(HintEvent.id)).where(
        HintEvent.session_id == session_id
    )
    result = await db.execute(stmt)
    hints_used = result.scalar() or 0
    
    # Step 5: prediction_accuracy
    stmt = select(MetacognitiveMetric.accuracy_score).where(
        MetacognitiveMetric.session_id == session_id
    )
    result = await db.execute(stmt)
    prediction_accuracy = result.scalar() or 0.0
    
    return {
        'submissions_count': submissions_count,
        'errors_count': errors_count,
        'concepts_learned': concepts_learned,
        'hints_used': hints_used,
        'prediction_accuracy': prediction_accuracy
    }


async def upsert_session_snapshot(session_id, summary: dict, db: AsyncSession) -> None:
    """Persist or update a SessionSnapshot row for today's date bucket.

    Uses INSERT … ON CONFLICT DO UPDATE (PostgreSQL) or a manual
    select-then-insert/update (SQLite / other dialects) so same-day calls
    update counters rather than inserting duplicates.
    """
    import logging

    bucket = date.today().isoformat()  # YYYY-MM-DD
    try:
        dialect = db.bind.dialect.name if db.bind else "unknown"
    except Exception:
        dialect = "unknown"

    try:
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(SessionSnapshot).values(
                session_id=session_id,
                date_bucket=bucket,
                submissions_count=summary['submissions_count'],
                errors_count=summary['errors_count'],
                concepts_learned=summary['concepts_learned'],
                hints_used=summary['hints_used'],
                prediction_accuracy=summary['prediction_accuracy'],
            ).on_conflict_do_update(
                constraint='uq_snapshot_session_date',
                set_={
                    'submissions_count': summary['submissions_count'],
                    'errors_count': summary['errors_count'],
                    'concepts_learned': summary['concepts_learned'],
                    'hints_used': summary['hints_used'],
                    'prediction_accuracy': summary['prediction_accuracy'],
                },
            )
            await db.execute(stmt)
        else:
            # SQLite / other: manual upsert
            existing = (await db.execute(
                select(SessionSnapshot).where(
                    SessionSnapshot.session_id == session_id,
                    SessionSnapshot.date_bucket == bucket,
                )
            )).scalar_one_or_none()
            if existing:
                existing.submissions_count = summary['submissions_count']
                existing.errors_count = summary['errors_count']
                existing.concepts_learned = summary['concepts_learned']
                existing.hints_used = summary['hints_used']
                existing.prediction_accuracy = summary['prediction_accuracy']
            else:
                db.add(SessionSnapshot(
                    session_id=session_id,
                    date_bucket=bucket,
                    submissions_count=summary['submissions_count'],
                    errors_count=summary['errors_count'],
                    concepts_learned=summary['concepts_learned'],
                    hints_used=summary['hints_used'],
                    prediction_accuracy=summary['prediction_accuracy'],
                ))
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logging.getLogger(__name__).warning("Failed to upsert SessionSnapshot: %s", exc)
