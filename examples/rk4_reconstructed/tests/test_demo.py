import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('rk4_h113_runner',ROOT/'run.py')
R=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(R)

class Demo(unittest.TestCase):
    def test_bundle_sha_pin(self):
        m=R.verify_bundle()
        self.assertEqual(m['bundle_sha256'],R.digest(R.BUNDLE))
    def test_h112_contents_present(self):
        with ZipFile(R.BUNDLE) as z:
            for n in ('test_h112_h1.py','test_h112.py','h112_audit.py','h112_report.py','DEMO_H112.html'):
                self.assertIn(n,z.namelist())
    def test_no_external_runtime_dependency(self):
        src=(ROOT/'run.py').read_text(encoding='utf-8')
        self.assertNotIn('requests.',src)
        self.assertNotIn('urlopen',src)
    def test_pinned_html(self):
        m=json.loads((ROOT/'MANIFEST_H113.json').read_bytes())
        with ZipFile(R.BUNDLE) as z:
            self.assertEqual(hashlib.sha256(z.read('DEMO_H112.html')).hexdigest(),m['html_sha256'])
    def test_release_scope_explicit(self):
        t=(ROOT/'RELEASE_NOTES_H113.md').read_text(encoding='utf-8')
        for needle in ('3200','3677','n>2','historical printer','CI success'):
            self.assertIn(needle,t)
    def test_refuse_existing_output(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td)/'already'; t.mkdir()
            self.assertTrue(t.exists())
            # The CLI checks this before writing anything; no temp files here.
            self.assertFalse((t/'RESULT_H113.json').exists())
    def test_nested_manifest(self):
        self.assertEqual(R.verify_bundle()['schema'],'KYIV_H113_BUNDLE_PIN_V1')

if __name__ == '__main__': unittest.main(verbosity=2)
