from sqlalchemy import select, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, ReflectionResponse, MetacognitiveMetric


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
    
    # Step 6: Compute success_streak per concept from last 10 submissions
    # For each concept, count consecutive successful submissions from most recent backward
    concept_stats = []
    for concept, error_count in concept_data:
        # Get all submissions in last 10 ordered by timestamp descending (most recent first)
        # Include both error submissions for this concept and all successful submissions
        stmt = select(
            CodeSubmission.timestamp,
            ExecutionResult.success_flag
        ).select_from(
            CodeSubmission
        ).join(
            ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id
        ).outerjoin(
            ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id
        ).where(
            CodeSubmission.session_id == session_id,
            CodeSubmission.id.in_(submission_ids)
        ).where(
            (ErrorRecord.concept_category == concept) |
            (ExecutionResult.success_flag == True)
        ).order_by(desc(CodeSubmission.timestamp))
        
        result = await db.execute(stmt)
        timeline = result.fetchall()
        
        # Count consecutive successes from most recent backward
        success_streak = 0
        for _, success_flag in timeline:
            if success_flag:
                success_streak += 1
            else:
                break
        
        concept_stats.append({
            'concept': concept,
            'error_count': error_count,
            'attempts': total_submissions,
            'success_streak': success_streak
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
    
    # Step 3: concepts_learned (concepts with successful outcomes after their last error)
    # Get all concepts with their last error timestamp
    stmt = select(
        ErrorRecord.concept_category,
        func.max(CodeSubmission.timestamp).label('last_error_time')
    ).select_from(
        CodeSubmission
    ).join(
        ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id
    ).join(
        ErrorRecord, ExecutionResult.id == ErrorRecord.execution_result_id
    ).where(
        CodeSubmission.session_id == session_id
    ).group_by(ErrorRecord.concept_category)
    
    result = await db.execute(stmt)
    concept_last_errors = result.fetchall()
    
    # For each concept, check if most recent submission after last error is successful
    # This uses a conservative heuristic: assume learner works on most recent error context
    concepts_learned = 0
    for concept, last_error_time in concept_last_errors:
        # Get the most recent submission after this concept's last error
        stmt = select(
            ExecutionResult.success_flag
        ).select_from(
            CodeSubmission
        ).join(
            ExecutionResult, CodeSubmission.id == ExecutionResult.submission_id
        ).where(
            CodeSubmission.session_id == session_id,
            CodeSubmission.timestamp > last_error_time
        ).order_by(desc(CodeSubmission.timestamp)).limit(1)
        
        result = await db.execute(stmt)
        most_recent_success = result.scalar()
        
        # Concept is learned if most recent attempt after error was successful
        if most_recent_success is True:
            concepts_learned += 1
    
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
