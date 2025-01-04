from fastapi import FastAPI, UploadFile, Form, HTTPException, Path as FastAPIPath, File, BackgroundTask
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
import logging
import asyncio
from pathlib import Path
import shutil
import os
import uuid
from pydantic import BaseModel
import sys
from plip_config import PLIPConfig
from plip_task import process_task, get_task_status, list_tasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    return JSONResponse(status_code=200, content={'message': 'pong'})

@app.post('/inference')
async def inference(config_data: PLIPConfig):
    try:
        task_id = str(uuid.uuid4())
        config_data.task_id = task_id

        # Validate input
        if not config_data.file_content and not config_data.pdb_id:
            raise HTTPException(
                status_code=400,
                detail="Either file_content or pdb_id must be provided"
            )

        # Handle PDB input
        if config_data.file_content:
            temp_pdb = f"storage/{task_id}/input.pdb"
            os.makedirs(os.path.dirname(temp_pdb), exist_ok=True)
            with open(temp_pdb, 'w') as f:
                f.write(config_data.file_content.strip())
            pdb_input = temp_pdb
        else:
            pdb_input = f"pdb:{config_data.pdb_id}"

        # Start task processing
        await process_task(
            task_id=task_id,
            pdb_file=pdb_input,
            plip_config=config_data.to_plip_config()
        )

        return JSONResponse(
            status_code=202,
            content={'task_id': task_id}
        )

    except Exception as e:
        logger.exception("Error processing request")
        return JSONResponse(
            status_code=500,
            content={'error': str(e)}
        )

@app.get('/task_status/{task_id}')
async def check_task_status(task_id: str):
    status = await get_task_status(task_id)
    if status['status'] == 'not_found':
        raise HTTPException(status_code=404, detail="Task not found")
    return status

@app.get('/tasks')
def get_tasks():
    return JSONResponse(status_code=200, content=list_tasks())

@app.get('/download/{task_id}')
async def download_results(task_id: str):
    status = await get_task_status(task_id)
    if status['status'] == 'not_found':
        raise HTTPException(status_code=404, detail="Task not found")
    if status['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Task not completed")

    task_dir = f"storage/{task_id}"
    if not os.path.exists(task_dir):
        raise HTTPException(status_code=404, detail="Results not found")

    zip_path = f"storage/{task_id}.zip"
    shutil.make_archive(zip_path[:-4], 'zip', task_dir)

    return FileResponse(
        zip_path,
        media_type='application/zip',
        filename=f'plip_results_{task_id}.zip',
        background=BackgroundTask(lambda: os.remove(zip_path))
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
