#!/usr/bin/env python3
"""Shared MSYS2 launcher contract, including scrubbed Python->Bash environment."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('kyiv_mingw64_shared',
    ROOT/'tools/historical/msys2_mingw64_v1.py')
assert SPEC and SPEC.loader
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

class LauncherTests(unittest.TestCase):
    def test_exact_msys2_family(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            exe=base/'mingw64/bin/python.exe';exe.parent.mkdir(parents=True)
            exe.write_bytes(b'fixture')
            bash=base/'usr/bin/bash.exe';bash.parent.mkdir(parents=True)
            bash.write_bytes(b'fixture')
            self.assertEqual(m.msys2_bash_from_python(exe),str(bash.resolve()))
            bad=base/'ucrt64/bin/python.exe';bad.parent.mkdir(parents=True)
            bad.write_bytes(b'fixture')
            with self.assertRaisesRegex(RuntimeError,'QT_MSYS2_PYTHON_NOT_MINGW64'):
                m.msys2_bash_from_python(bad)

    def test_bash_bootstrap_is_self_contained(self):
        content=m.qt_mingw_bootstrap()
        self.assertIn('export MSYSTEM=MINGW64',content)
        self.assertIn('export MINGW_PREFIX=/mingw64',content)
        self.assertIn('export PATH=/mingw64/bin:/usr/bin:/bin',content)
        self.assertIn('source gui/qt6/run.sh --smoke-only',content)
        self.assertNotIn('source gui/qt6/run.sh',m.qt_mingw_bootstrap(run_gui=False))
        with self.assertRaisesRegex(RuntimeError,'QT_MINGW_PREFIX_INVALID'):
            m.qt_mingw_bootstrap('/mingw64/../ucrt64')

    @unittest.skipUnless(sys.platform=='win32','MSYS2 MINGW64 Windows only')
    def test_real_mingw64_child_environment(self):
        argv=[m.msys2_bash_from_python(),'--noprofile','--norc','-c',m.qt_mingw_bootstrap(run_gui=False)]
        env=dict(os.environ)
        env.pop('MSYSTEM',None)
        env.pop('MINGW_PREFIX',None)
        # The child must initialize the correct environment itself.
        p=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,
                         encoding='utf-8',errors='replace',timeout=20)
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertIn('H118_MINGW64_ENV_PASS|MSYSTEM=MINGW64|MINGW_PREFIX=/mingw64|QT=',p.stdout)

if __name__=='__main__':unittest.main()
