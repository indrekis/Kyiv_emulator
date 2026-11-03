"""H115-B8 overlay negative and reproducibility tests; no CPU execution."""
import importlib.util
from pathlib import Path
import unittest
import json

ROOT=Path(__file__).resolve().parents[2]
M=ROOT/'tools/historical/materialize_fp_errata_candidate.py'
spec=importlib.util.spec_from_file_location('fp_overlay',M)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SOURCE=ROOT/'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41'
OVERLAY=ROOT/'examples/historical/gy1962/rom_sets/fp_simulation_1962_errata_candidate.json'

class SourceErratum(unittest.TestCase):
    def setUp(self):
        self.source=SOURCE.read_bytes()
        self.overlay=OVERLAY.read_bytes()
    def test_exact_source_sha(self):
        self.assertEqual(mod.sha(self.source),mod.PIN)
    def test_three_replacements_no_other_words(self):
        generated,report=mod.materialize(self.source,self.overlay)
        orig=mod.checked_source(self.source)
        after={p.split()[0]:p.split()[1] for p in generated.decode().splitlines()[1:]}
        self.assertEqual(set(after),set(orig))
        self.assertEqual([a for a in orig if after[a]!=orig[a]],['3467','3470','3474'])
        self.assertEqual(report['unknowns_filled'],0)
        self.assertEqual(report['hardware_oracle'],'NO')
        self.assertEqual(report['records'],251)
        self.assertNotEqual(generated,self.source)
    def test_deterministic(self):
        self.assertEqual(mod.materialize(self.source,self.overlay),mod.materialize(self.source,self.overlay))
    def test_tampered_source_rejected(self):
        b=self.source.replace(b'3467 15002036070021',b'3467 15002036050021')
        with self.assertRaisesRegex(ValueError,'SHA256_DRIFT'):
            mod.materialize(b,self.overlay)
    def test_extra_edit_rejected(self):
        j=json.loads(self.overlay);j['substitutions'].append({'address':'3500','printed':'0'*14,'candidate':'1'*14})
        with self.assertRaisesRegex(ValueError,'OVERLAY_COUNT'):
            mod.materialize(self.source,json.dumps(j).encode())
    def test_unauthorized_candidate_rejected(self):
        j=json.loads(self.overlay);j['substitutions'][0]['candidate']='15002036060021'
        with self.assertRaisesRegex(ValueError,'OVERLAY_UNREVIEWED_CHANGE'):
            mod.materialize(self.source,json.dumps(j).encode())
    def test_missing_change_rejected(self):
        j=json.loads(self.overlay);j['substitutions']=j['substitutions'][:2]
        with self.assertRaisesRegex(ValueError,'OVERLAY_COUNT'):
            mod.materialize(self.source,json.dumps(j).encode())
    def test_source_still_identical(self):
        before=mod.sha(self.source)
        mod.materialize(self.source,self.overlay)
        self.assertEqual(mod.sha(SOURCE.read_bytes()),before)

if __name__=='__main__':unittest.main()
