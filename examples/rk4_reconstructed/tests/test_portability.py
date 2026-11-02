import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT.parents[1]/'.github/workflows/kyiv-rk4-evidence.yml'

class Portability(unittest.TestCase):
    def test_ci_checks_both_operating_systems(self):
        src=WORKFLOW.read_text(encoding='utf8')
        self.assertIn('ubuntu-latest',src)
        self.assertIn('windows-latest',src)
        self.assertIn('actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd',src)
        self.assertIn('run.py --out',src)
        self.assertIn('permissions:',src)
        self.assertNotIn('h112_replay.py',src)
    def test_cli_refuses_existing_directory_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'existing'
            path.mkdir()
            sentinel=path/'sentinel';sentinel.write_bytes(b'USER_DATA')
            proc=subprocess.run([sys.executable,str(ROOT/'run.py'),'--out',str(path)],capture_output=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertEqual(sentinel.read_bytes(),b'USER_DATA')
    def test_clean_scope(self):
        self.assertFalse((ROOT/'ROADMAP.md').exists())
        self.assertFalse((ROOT/'mem/ROM.txt').exists())

if __name__=='__main__':unittest.main()
