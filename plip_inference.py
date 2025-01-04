import logging
from pathlib import Path
import os
from plip.structure.preparation import PDBComplex
from plip.exchange.report import StructureReport
from plip.basic import config
from plip.exchange.webservices import fetch_pdb

logger = logging.getLogger(__name__)

class PLIPInference:
    def __init__(self, task_id: str, plip_config: dict):
        self.task_id = task_id
        self.output_dir = f"storage/{task_id}"
        self.config = plip_config

    def run_inference(self, pdb_file: str) -> dict:
        """Run PLIP analysis and return results"""
        try:
            # Configure PLIP settings
            self._setup_plip_config()

            # Initialize complex
            complex = PDBComplex()
            complex.output_path = self.output_dir

            # Load structure
            if pdb_file.startswith('pdb:'):
                pdb_id = pdb_file[4:]
                pdb_string, _ = fetch_pdb(pdb_id)
                complex.load_pdb(pdb_string, as_string=True)
            else:
                complex.load_pdb(pdb_file)

            # Process results
            results = {}
            txt_reports = {}

            for ligand in complex.ligands:
                complex.characterize_complex(ligand)
                binding_site = ':'.join([ligand.hetid, ligand.chain, str(ligand.position)])

                report = StructureReport(complex)

                if config.XML:
                    results[binding_site] = report.write_xml(as_string=False)
                if config.TXT:
                    txt_reports[binding_site] = report.write_txt(as_string=False)

            return {
                'status': 'completed',
                'results': results if results else None,
                'txt_reports': txt_reports if txt_reports else None,
                'output_dir': self.output_dir
            }

        except Exception as e:
            logger.exception("Inference error")
            return {
                'status': 'failed',
                'error': str(e)
            }

    def _setup_plip_config(self):
        """Configure PLIP settings"""
        config.VERBOSE = self.config.get('verbose', False)
        config.MODEL = self.config.get('model', 1)
        config.NOHYDRO = self.config.get('nohydro', False)
        config.PEPTIDES = self.config.get('peptides', [])
        config.OUTPATH = self.output_dir
        config.XML = 'xml' in self.config.get('output_format', ['xml'])
        config.TXT = 'txt' in self.config.get('output_format', [])
        config.PYMOL = 'pymol' in self.config.get('output_format', [])
