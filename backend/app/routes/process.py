from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
import asyncio
import uuid

from app.models.schemas import ProcessRequest, ProcessResponse
from app.pipeline.orchestrator import PipelineOrchestrator


router = APIRouter()

processing_tasks: dict = {}


@router.post("/", response_model=ProcessResponse)
async def process_facebook_url(request: ProcessRequest):
    orchestrator = PipelineOrchestrator()
    result = await orchestrator.process(request.url)
    return result


@router.post("/async", response_model=dict)
async def process_facebook_url_async(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
):
    task_id = str(uuid.uuid4())
    processing_tasks[task_id] = {
        "status": "processing",
        "result": None,
        "error": None,
    }

    async def run_pipeline():
        try:
            orchestrator = PipelineOrchestrator()
            result = await orchestrator.process(request.url)
            processing_tasks[task_id]["status"] = "completed"
            processing_tasks[task_id]["result"] = result.model_dump()
        except Exception as e:
            processing_tasks[task_id]["status"] = "failed"
            processing_tasks[task_id]["error"] = str(e)

    asyncio.create_task(run_pipeline())

    return {"task_id": task_id, "status": "processing"}


@router.get("/status/{task_id}")
async def get_processing_status(task_id: str):
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = processing_tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "result": task["result"],
        "error": task["error"],
    }
