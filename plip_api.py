from fastapi import FastAPI, UploadFile, Form, HTTPException, Path as FastAPIPath, File
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
import logging
import asyncio
from pathlib import Path
import tempfile
import os
import uuid
from pydantic import BaseModel
import sys
from plip_task import process_pdb_and_run_plip, tasks
# Add PLIP to path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

from plip.structure.preparation import PDBComplex
from plip.exchange.report import StructureReport
from plip.basic import config
from plip.exchange.webservices import fetch_pdb

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PLIPConfig(BaseModel):
    pdb_id: Optional[str] = None
    file_content: Optional[str] = None
    output_format: Optional[List[str]] = ["xml", "txt"]  # Changed default to include both
    model: Optional[int] = 1
    verbose: Optional[bool] = False
    peptides: Optional[List[str]] = []
    nohydro: Optional[bool] = False
    outpath: Optional[str] = None
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

@app.post('/analyze')
async def analyze_structure(config_data: PLIPConfig):
    try:
        task_id = str(uuid.uuid4())
        tasks[task_id] = {'task_id': task_id, 'status': 'queued'}
        
        # Create temp directory for outputs if not specified
        if config_data.outpath:
            output_dir = config_data.outpath
        else:
            output_dir = tempfile.mkdtemp()
            config_data.outpath = output_dir  # Update the config with the temp dir
        
        # Save PDB content if provided
        pdb_input = None
        if config_data.file_content:
            temp_pdb = os.path.join(output_dir, f"{task_id}.pdb")
            with open(temp_pdb, 'w') as f:
                f.write(config_data.file_content.strip())
            pdb_input = temp_pdb
        elif config_data.pdb_id:
            pdb_input = f"pdb:{config_data.pdb_id}"
            
        # Create configuration dictionary
        plip_config = config_data.dict()
        
        # Run analysis immediately instead of creating a task
        await process_pdb_and_run_plip(
            task_id=task_id,
            pdb_file=pdb_input,
            output_dir=output_dir,
            plip_config=plip_config
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
async def get_task_status(task_id: str):
    """Get the status of a PLIP analysis task"""
    #print(f"[API] Checking status for task {task_id}")
    #print(f"[API] Tasks dictionary content: {tasks}")
    
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_status = tasks[task_id]
    #print(f"[API] Returning full status: {task_status}")
    return task_status

@app.get('/tasks')
def list_tasks():
    return JSONResponse(status_code=200, content=list(tasks.keys()))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
