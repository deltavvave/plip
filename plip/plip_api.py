from fastapi import FastAPI, HTTPException, Path as FastAPIPath
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
import sys
from pathlib import Path
import io
from zipfile import ZipFile
from pydantic import BaseModel

from .plip_task import process_task, get_task_status, list_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Disable other verbose loggers
logging.getLogger("plip").setLevel(logging.WARNING)
logging.getLogger("openbabel").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Request model for inference endpoint
class InferenceRequest(BaseModel):
    pdb_id: Optional[str] = None
    file_content: Optional[str] = None
    output_format: List[str] = ["xml", "txt"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.get('/ping')
def ping():
    """Health check endpoint"""
    return JSONResponse(status_code=200, content={'message': 'pong'})

@app.post('/inference')
async def inference(request: InferenceRequest):
    """Start PLIP analysis and return task ID"""
    try:
        # Validate input
        if not request.file_content and not request.pdb_id:
            raise HTTPException(
                status_code=400,
                detail="Either file_content or pdb_id must be provided"
            )

        logger.info("Received inference request")

        # Pass the entire request model to process_task
        task_id = await process_task(request.dict())
        logger.info(f"Created task: {task_id}")

        return JSONResponse(
            status_code=202,
            content={'task_id': task_id}
        )

    except Exception as e:
        logger.error(f"Error submitting inference task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/task_status/{task_id}')
async def check_task_status(task_id: str):
    """Get status of a specific task"""
    status = await get_task_status(task_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    return status

@app.get('/tasks')
def get_tasks():
    """List all tasks"""
    return JSONResponse(status_code=200, content=list_tasks())

@app.get('/download/{task_id}')
async def download_results(task_id: str = FastAPIPath(...)):
    """Download task results as zip file"""
    status = await get_task_status(task_id)
    if status == "not_found":
        return JSONResponse(
            content={"error": "Task not found"},
            status_code=404
        )

    if status != "completed":
        return JSONResponse(
            content={"error": "Task not completed"},
            status_code=400
        )

    task_dir = Path("/src/storage") / task_id
    if not task_dir.exists():
        logger.error(f"Output directory {task_dir} does not exist for task {task_id}")
        return JSONResponse(
            content={"error": "Results not found"},
            status_code=404
        )

    memory_file = io.BytesIO()
    with ZipFile(memory_file, 'w') as zf:
        for file_path in task_dir.glob('*'):
            zf.write(file_path, file_path.name)

    memory_file.seek(0)

    return StreamingResponse(
        memory_file,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=plip_results_{task_id}.zip"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
