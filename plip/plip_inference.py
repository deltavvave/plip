from pathlib import Path
from typing import List
import contextlib
import os

from plip.structure.preparation import PDBComplex
from plip.exchange.report import StructureReport
from plip.basic import config
from plip.exchange.webservices import fetch_pdb

class PLIPInference:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.output_dir = Path(f"storage/{task_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run(self, pdb_file: str, output_format: List[str] = ["xml", "txt"]):
        try:
            error_file = Path(self.output_dir) / "debug.log"
            with open(error_file, "w") as f:
                f.write(f"Input pdb_file: {pdb_file}\n")
                f.write(f"Output dir: {self.output_dir}\n")
                if os.path.exists(pdb_file):
                    f.write(f"File exists: {pdb_file}\n")
                    with open(pdb_file, 'r') as pf:
                        content = pf.read()
                    f.write(f"File readable: yes, size: {len(content)} bytes\n")
                else:
                    f.write(f"File does not exist: {pdb_file}\n")

            self._setup_plip_config(output_format)

            with open(os.devnull, 'w') as devnull:
                with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                    complex = PDBComplex()
                    complex.output_path = str(self.output_dir)

                    if pdb_file.startswith('pdb:'):
                        pdb_id = pdb_file[4:]
                        pdb_string, _ = fetch_pdb(pdb_id)
                        # Save fetched content to a temporary file
                        temp_pdb = Path(self.output_dir) / "input.pdb"
                        temp_pdb.write_text(pdb_string)
                        complex.load_pdb(str(temp_pdb))
                    else:
                        complex.load_pdb(pdb_file)

                    for ligand in complex.ligands:
                        try:
                            complex.characterize_complex(ligand)
                            report = StructureReport(complex)
                            if config.XML:
                                report.write_xml(as_string=False)
                            if config.TXT:
                                report.write_txt(as_string=False)
                        except Exception as ligand_error:
                            error_file = Path(self.output_dir) / "error.log"
                            with open(error_file, "w") as f:
                                f.write(f"Error processing ligand: {str(ligand_error)}")
                            raise

        except Exception as e:
            error_file = Path(self.output_dir) / "error.log"
            with open(error_file, "w") as f:
                f.write(f"Error in PLIP analysis: {str(e)}")
            raise

    def _setup_plip_config(self, output_format: List[str]):
        config.VERBOSE = False
        config.XML = "xml" in output_format
        config.TXT = "txt" in output_format
        config.OUTPATH = str(self.output_dir)
