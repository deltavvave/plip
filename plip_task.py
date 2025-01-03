import sys
import os
import subprocess
import tempfile
from pathlib import Path
import logging
import asyncio

# Add PLIP to path
current_dir = Path(__file__).parent.absolute()
project_root = os.path.dirname(current_dir)
sys.path.extend([current_dir, project_root])

from plip.structure.preparation import PDBComplex
from plip.exchange.report import StructureReport
from plip.basic import config
from plip.exchange.webservices import fetch_pdb

logger = logging.getLogger(__name__)

# Initialize tasks dictionary as a global variable
tasks = {}

async def process_pdb_and_run_plip(task_id: str, pdb_file: str, output_dir: str, plip_config: dict):
    """Process PDB file and run PLIP analysis asynchronously"""
    try:

        
        # Initialize task status if it doesn't exist
        if task_id not in tasks:
            tasks[task_id] = {'task_id': task_id}
        
        tasks[task_id]['status'] = 'running'


        # Run the actual analysis in a separate thread to not block
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _run_plip_analysis(
            task_id, pdb_file, output_dir, plip_config
        ))

    except Exception as e:

        logger.exception(f"Error in PLIP analysis for task {task_id}")
        if task_id not in tasks:
            tasks[task_id] = {'task_id': task_id}
        tasks[task_id].update({
            'status': 'failed',
            'error': str(e)
        })

def _run_plip_analysis(task_id: str, pdb_file: str, output_dir: str, plip_config: dict):
    """Run the actual PLIP analysis"""
    try:
        # Configure PLIP settings
        config.VERBOSE = plip_config.get('verbose', False)
        config.MODEL = plip_config.get('model', 1)
        config.NOHYDRO = plip_config.get('nohydro', False)
        config.PEPTIDES = plip_config.get('peptides', [])
        config.OUTPATH = output_dir or plip_config.get('outpath')
        config.XML = 'xml' in plip_config.get('output_format', ['xml'])
        config.TXT = 'txt' in plip_config.get('output_format', [])

        config.PYMOL = 'pymol' in plip_config.get('output_format', [])


        complex = PDBComplex()
        complex.output_path = output_dir

        # Load structure

        if pdb_file.startswith('pdb:'):
            pdb_id = pdb_file[4:]

            pdb_string, _ = fetch_pdb(pdb_id)
            complex.load_pdb(pdb_string, as_string=True)
        else:

            complex.load_pdb(pdb_file)

       
        results = {}
        txt_reports = {}
        

        for i, ligand in enumerate(complex.ligands):
        
            complex.characterize_complex(ligand)
            binding_site = ':'.join([ligand.hetid, ligand.chain, str(ligand.position)])
     
            
            # Generate reports
            report = StructureReport(complex)

            if config.XML:
              
                results[binding_site] = report.write_xml(as_string=False)
            if config.TXT:
    
                txt_report = report.write_txt(as_string=False)
                txt_reports[binding_site] = txt_report


        # Update task status with results
        tasks[task_id] = {
            'task_id': task_id,
            'status': 'completed',
            'results': results if results else None,
            'txt_reports': txt_reports if txt_reports else None,
            'output_dir': output_dir
        }
   
        return tasks[task_id]

    except Exception as e:
  
        tasks[task_id] = {
            'task_id': task_id,
            'status': 'failed',
            'error': str(e)
        }
        raise

