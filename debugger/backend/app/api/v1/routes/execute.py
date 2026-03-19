import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.api.v1.schemas.execute import ExecuteRequest, ExecuteResponse, ExecuteData, ClassificationData, ContextualHint
from app.db.session import get_db
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, HintSequence, MetacognitiveMetric, HintEvent
from app.execution.service import execute_code
from app.cognitive.engine import classify, get_reflection_question, generate_contextual_hint
from app.intelligence.prediction import compare_predictions, compute_accuracy
from app.api.v1.deps.auth_guard import get_current_user_id, require_session_owner

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.post("/execute", response_model=ExecuteResponse)
@limiter.limit("30/minute")
async def execute_handler(
    request: Request,
    request_body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    caller_id: str = Depends(get_current_user_id),
) -> ExecuteResponse:
    require_session_owner(request_body.session_id, caller_id)
    # Initialize all response-level variables up front to prevent unbound locals
    prediction_match: Optional[bool] = None
    metacognitive_accuracy: Optional[float] = None
    failed_attempts: Optional[int] = None
    
    # Write CodeSubmission
    try:
        submission = CodeSubmission(
            code_text=request_body.code,
            session_id=request_body.session_id,
            prediction=request_body.prediction
        )
        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        submission_id = submission.id
    except Exception as e:
        logger.error(f"Failed to write CodeSubmission: {e}")
        return ExecuteResponse(
            status="error",
            message="Internal error",
            code="INTERNAL_ERROR"
        )
    
    # Run code in executor
    loop = asyncio.get_running_loop()
    exec_result = await loop.run_in_executor(None, execute_code, request_body.code)
    
    # Write ExecutionResult
    execution_result_id = None
    try:
        execution_result = ExecutionResult(
            submission_id=submission_id,
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,
            traceback=exec_result.traceback,
            execution_time=exec_result.execution_time,
            success_flag=exec_result.success,
            timed_out=exec_result.timed_out,
            exit_code=exec_result.exit_code
        )
        db.add(execution_result)
        await db.commit()
        await db.refresh(execution_result)
        execution_result_id = execution_result.id
    except Exception as e:
        logger.warning(f"Failed to write ExecutionResult: {e}")
    
    # Prediction comparison and metacognitive metric upsert
    if request_body.prediction is not None:
        try:
            normalized_prediction = request_body.prediction.strip() if request_body.prediction else ""
            actual_output_for_comparison = exec_result.stdout if exec_result.success else (exec_result.traceback or exec_result.stderr)
            prediction_match = compare_predictions(normalized_prediction, actual_output_for_comparison)
            
            stmt = select(MetacognitiveMetric).where(
                MetacognitiveMetric.session_id == request_body.session_id
            ).with_for_update()
            result = await db.execute(stmt)
            metric = result.scalar_one_or_none()
            
            if metric:
                metric.total_predictions += 1
                if prediction_match:
                    metric.correct_predictions += 1
                metric.accuracy_score = compute_accuracy(metric.correct_predictions, metric.total_predictions)
                metric.last_updated = func.now()
            else:
                metric = MetacognitiveMetric(
                    session_id=request_body.session_id,
                    total_predictions=1,
                    correct_predictions=1 if prediction_match else 0,
                    accuracy_score=1.0 if prediction_match else 0.0
                )
                db.add(metric)
            
            try:
                await db.commit()
            except Exception as commit_error:
                await db.rollback()
                from sqlalchemy.exc import IntegrityError
                if isinstance(commit_error, IntegrityError):
                    stmt = select(MetacognitiveMetric).where(
                        MetacognitiveMetric.session_id == request_body.session_id
                    ).with_for_update()
                    result = await db.execute(stmt)
                    metric = result.scalar_one_or_none()
                    if metric:
                        metric.total_predictions += 1
                        if prediction_match:
                            metric.correct_predictions += 1
                        metric.accuracy_score = compute_accuracy(metric.correct_predictions, metric.total_predictions)
                        metric.last_updated = func.now()
                        await db.commit()
                    else:
                        logger.warning(f"Failed to upsert MetacognitiveMetric after rollback: {commit_error}")
                        raise
                else:
                    raise
            
            try:
                await db.refresh(metric)
                metacognitive_accuracy = metric.accuracy_score
            except Exception as refresh_error:
                stmt = select(MetacognitiveMetric).where(MetacognitiveMetric.session_id == request_body.session_id)
                result = await db.execute(stmt)
                metric = result.scalar_one_or_none()
                if metric:
                    metacognitive_accuracy = metric.accuracy_score
                else:
                    logger.warning(f"Failed to fetch MetacognitiveMetric after commit: {refresh_error}")
        except Exception as e:
            await db.rollback()
            logger.warning(f"Failed to process prediction comparison: {e}")
    
    # Handle terminal error states
    if exec_result.timed_out:
        return ExecuteResponse(
            status="error",
            message="Execution timeout",
            code="EXEC_TIMEOUT"
        )
    
    if exec_result.exit_code == 137:
        return ExecuteResponse(
            status="error",
            message="Resource limit exceeded",
            code="EXEC_RESOURCE_LIMIT"
        )
    
    if exec_result.exit_code == -1:
        return ExecuteResponse(
            status="error",
            message="Execution failed",
            code="EXEC_FAILED"
        )
    
    # Classification
    classification_result = None
    reflection_question = None
    contextual_hint = None

    # Trigger Phase 2 features on error OR wrong prediction
    should_provide_assistance = not exec_result.success or (prediction_match is not None and not prediction_match)

    if should_provide_assistance and not exec_result.success:
        classification_result = classify(exec_result.traceback)
        if classification_result is not None and execution_result_id is not None:
            stmt = select(func.count(ErrorRecord.id)).join(ExecutionResult).join(CodeSubmission).where(
                CodeSubmission.session_id == request_body.session_id,
                ErrorRecord.concept_category == classification_result.concept_category
            )
            result = await db.execute(stmt)
            prior_count = result.scalar() or 0
            failed_attempts = prior_count + 1
            
            try:
                error_record = ErrorRecord(
                    execution_result_id=execution_result_id,
                    exception_type=classification_result.exception_type,
                    concept_category=classification_result.concept_category,
                    cognitive_skill=classification_result.cognitive_skill,
                    failed_attempts=failed_attempts
                )
                db.add(error_record)
                await db.commit()
            except Exception as e:
                logger.warning(f"Failed to write ErrorRecord: {e}")
            
            reflection_question = get_reflection_question(classification_result.concept_category)
            
            # Select initial hint tier based on failed_attempts: tier 1 for first 2 attempts,
            # tier 2 for attempts 3-4, tier 3 for 5+
            initial_tier = 1 if failed_attempts <= 2 else (2 if failed_attempts <= 4 else 3)
            hint_stmt = select(HintSequence).where(
                HintSequence.concept_category == classification_result.concept_category,
                HintSequence.tier == initial_tier
            )
            hint_row = (await db.execute(hint_stmt)).scalar_one_or_none()
            
            hint_result = generate_contextual_hint(exec_result.traceback, request_body.code)
            if hint_result:
                # Override hint text with tiered DB hint if available
                if hint_row:
                    hint_result.hint_text = hint_row.hint_text
                    hint_result.explanation = f"Hint tier {initial_tier} — attempt {failed_attempts}"
                contextual_hint = ContextualHint(
                    hint_text=hint_result.hint_text,
                    affected_line=hint_result.affected_line,
                    explanation=hint_result.explanation
                )
                try:
                    db.add(HintEvent(
                        submission_id=submission_id,
                        session_id=request_body.session_id,
                        hint_text=hint_result.hint_text,
                        affected_line=hint_result.affected_line,
                    ))
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.warning(f"Failed to persist HintEvent: {e}")
            
    # When code succeeds but prediction was wrong, surface a metacognitive prompt
    if exec_result.success and prediction_match is not None and not prediction_match:
        reflection_question = "Your code ran correctly but your prediction didn't match — what assumption did you make that turned out to be wrong?"

    # Build response
    status = "success" if exec_result.success else "error"
    classification_data = None
    if classification_result:
        classification_data = ClassificationData(
            exception_type=classification_result.exception_type,
            concept_category=classification_result.concept_category,
            cognitive_skill=classification_result.cognitive_skill
        )
    
    data = ExecuteData(
        submission_id=submission_id,
        success=exec_result.success,
        stdout=exec_result.stdout,
        stderr=exec_result.stderr,
        traceback=exec_result.traceback,
        execution_time=exec_result.execution_time,
        classification=classification_data,
        reflection_question=reflection_question,
        contextual_hint=contextual_hint,
        prediction_match=prediction_match,
        metacognitive_accuracy=metacognitive_accuracy,
        failed_attempts=failed_attempts,
    )
    
    message = ""
    if not exec_result.success:
        if classification_result:
            message = f"{classification_result.exception_type} detected"
        else:
            message = "Unclassified error"
    
    return ExecuteResponse(
        status=status,
        data=data,
        message=message
    )
