import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.schemas.execute import ExecuteRequest, ExecuteResponse, ExecuteData, ClassificationData, HintData
from app.db.session import get_db
from app.db.models import CodeSubmission, ExecutionResult, ErrorRecord, HintSequence
from app.execution.service import execute_code
from app.cognitive.engine import classify, get_reflection_question

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_handler(request: ExecuteRequest, db: AsyncSession = Depends(get_db)) -> ExecuteResponse:
    # Write CodeSubmission
    try:
        submission = CodeSubmission(
            code_text=request.code,
            session_id=request.session_id,
            prediction=request.prediction
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
    exec_result = await loop.run_in_executor(None, execute_code, request.code)
    
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
    hints = None
    hint_auto_unlocked = False
    
    if not exec_result.success:
        classification_result = classify(exec_result.traceback)
        if classification_result is not None and execution_result_id is not None:
            # Count prior errors in same session+concept
            from sqlalchemy import select, func as sql_func
            stmt = select(sql_func.count(ErrorRecord.id)).join(ExecutionResult).join(CodeSubmission).where(
                CodeSubmission.session_id == request.session_id,
                ErrorRecord.concept_category == classification_result.concept_category
            )
            result = await db.execute(stmt)
            prior_count = result.scalar() or 0
            
            # Current failure count includes this error
            current_failure_count = prior_count + 1
            failed_attempts = current_failure_count
            hint_auto_unlocked = current_failure_count >= 2
            
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
            
            # Get reflection question
            reflection_question = get_reflection_question(classification_result.concept_category)
            
            # Get hints
            from sqlalchemy import select
            stmt = select(HintSequence).where(
                HintSequence.concept_category == classification_result.concept_category
            ).order_by(HintSequence.tier)
            result = await db.execute(stmt)
            hint_rows = result.scalars().all()
            
            hints = [
                HintData(
                    tier=h.tier,
                    tier_name=h.tier_name,
                    hint_text=h.hint_text,
                    unlocked=False
                )
                for h in hint_rows
            ]
    
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
        hints=hints,
        hint_auto_unlocked=hint_auto_unlocked
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
