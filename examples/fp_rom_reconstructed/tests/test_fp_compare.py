"""H115-B21 read-only provenance regression tests (requires repo checkout)."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('b21_compare',HERE/'compare.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CompareRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.report=mod.compare(ROOT)

    def test_pass(self):self.assertEqual(cls_report:=self.report['status'],mod.PASS)
    def test_lengths(self):
        self.assertEqual((self.report['original_records'],self.report['functional_records']),(251,257))
    def test_reverse_exact(self):self.assertTrue(self.report['reverse_patch_exact_source_bytes'])
    def test_changes_count(self):self.assertEqual(len(self.report['changes']),12)
    def test_synthetic(self):
        self.assertEqual(sum(x['type']=='SYNTHETIC_UNPRINTED' for x in self.report['changes']),6)
    def test_replacements(self):
        self.assertEqual(sum(x['type']=='REPLACEMENT' for x in self.report['changes']),6)
    def test_b19_branch(self):
        x=next(i for i in self.report['changes'] if i['address_octal']=='3367')
        self.assertEqual((x['original_word_octal'],x['functional_word_octal']),
                         ('01304200210021','31002137103712'))
    def test_unknown(self):self.assertEqual(self.report['unknown_3574'],'ABSENT_NOT_GUESSED')
    def test_b20_evidence(self):
        self.assertEqual((self.report['native_cpu_sessions_B20'],self.report['rk4_checkpoints_B20']),(52,42))
    def test_hardware_is_unclaimed(self):
        self.assertEqual(self.report['historical_hardware_identity'],'NOT_CLAIMED')
    def test_no_evidence_forgery(self):
        with self.assertRaisesRegex(ValueError,'B20_EVIDENCE_SHA_DRIFT'):
            mod.verified_evidence(b'fabricated')
    def test_no_unregistered_word(self):
        self.assertEqual({int(x['address_octal'],8) for x in self.report['changes']},
                         {0o3367,0o3455,0o3467,0o3470,0o3474,0o3476,0o3706,0o3707,0o3710,0o3711,0o3712,0o3713})

if __name__=='__main__':unittest.main()
