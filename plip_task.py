import asyncio
import logging
from pathlib import Path
import os
from plip_inference import PLIPInference

logger = logging.getLogger(__name__)

# Task status storage
tasks = {}

async def process_task(task_id: str, pdb_file: str, plip_config: dict):
    """Handle task processing"""
    try:
        # Initialize task
        tasks[task_id] = {'task_id': task_id, 'status': 'running'}

        # Ensure output directory exists
        output_dir = f"storage/{task_id}"
        os.makedirs(output_dir, exist_ok=True)

        # Run inference in thread pool
        loop = asyncio.get_event_loop()
        inference_engine = PLIPInference(task_id, plip_config)

        result = await loop.run_in_executor(
            None,
            inference_engine.run_inference,
            pdb_file
        )

        # Update task status with results
        tasks[task_id].update(result)

    except Exception as e:
        logger.exception(f"Task processing error for {task_id}")
        tasks[task_id].update({
            'status': 'failed',
            'error': str(e)
        })

async def get_task_status(task_id: str) -> dict:
    """Get current task status"""
    return tasks.get(task_id, {'task_id': task_id, 'status': 'not_found'})

def list_tasks() -> list:
    """Get list of all tasks"""
    return list(tasks.keys())
