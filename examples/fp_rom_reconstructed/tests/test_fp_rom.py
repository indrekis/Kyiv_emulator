from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import unittest
import zipfile

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fp_b20_demo',HERE/'run.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FunctionalROM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prov=json.loads((HERE/'PROVENANCE.json').read_bytes())
        cls.patch=json.loads((HERE/'PATCHES.json').read_bytes())
        cls.data=(HERE/'inputs/FP_FUNCTIONAL_1962_RECONSTRUCTED.k41').read_bytes()
        cls.rows=mod.strict_rom(cls.data)
    def test_rom_format(self):
        self.assertEqual(len(self.rows),257)
        self.assertNotIn(0o3574,self.rows)
        self.assertEqual(mod.sha(self.data),self.prov['functional_image_sha256'])
    def test_changes(self):
        self.assertEqual(len(self.patch['patches']),12)
        self.assertEqual(sum(v['original_word_octal'] is None for v in self.patch['patches']),6)
        self.assertEqual(sum(v['original_word_octal'] is not None for v in self.patch['patches']),6)
    def test_all_changes_in_rom(self):
        for v in self.patch['patches']:
            self.assertEqual(self.rows[int(v['address_octal'],8)],int(v['functional_word_octal'],8))
    def test_reject_duplicate(self):
        with self.assertRaises(mod.GateHold): mod.strict_rom(self.data+self.data.splitlines()[1]+b'\n')
    def test_reject_wrong_word(self):
        a=self.data.replace(b'3706 05002300213502',b'3706 05002300213503')
        self.assertNotEqual(mod.sha(a),self.prov['functional_image_sha256'])
    def test_reject_3574(self):
        with self.assertRaises(mod.GateHold):mod.strict_rom(self.data+b'3574 00000000000000\n')
    def test_evidence(self):
        evidence=(HERE/'evidence/H115_B19_FP_SIGNED_OVERFLOW_NATIVE_EVIDENCE_V1.zip').read_bytes()
        self.assertEqual(mod.sha(evidence),self.prov['b19_evidence_sha256'])
        files=mod.archived(evidence)
        self.assertEqual(json.loads(files['RESULT.json'])['status'],mod.B19_PASS)
    def test_no_host_patches(self):
        for name in ('native_rk4.cpp','native_regression.cpp'):
            txt=(HERE/name).read_text()
            self.assertEqual(txt.count('cpu.kmem.write_rom('),1)
            self.assertEqual(txt.count('cpu.C_reg='),1)
    def test_b19_evidence_contents(self):
        files=mod.archived((HERE/'evidence/H115_B19_FP_SIGNED_OVERFLOW_NATIVE_EVIDENCE_V1.zip').read_bytes())
        self.assertEqual(len(files['RK4/NATIVE_CHECKPOINTS.tsv'].splitlines()),43)
        self.assertEqual(len(files['REGRESSION/NATIVE_RESULTS.tsv'].splitlines()),52)
    def test_negative_zero_is_not_zero_filled(self):
        self.assertNotIn(0o3574,self.rows)
        self.assertNotIn(0o3574,[int(x['address_octal'],8) for x in self.patch['patches']])
    def test_b16_program_pinned(self):
        p=HERE/'reference/RK4_ORIGINAL_B16.k41'
        self.assertEqual(mod.sha(p.read_bytes()),self.prov['b16_original_rk4_image_sha256'])
    def test_native_rk4_loader_pinned(self):
        self.assertEqual(mod.sha((HERE/'native_rk4.cpp').read_bytes()),self.prov['native_rk4_image_loader_source_sha256'])
    def test_native_regression_loader_pinned(self):
        self.assertEqual(mod.sha((HERE/'native_regression.cpp').read_bytes()),self.prov['native_regression_image_loader_source_sha256'])
    def test_every_patch_word_41_bit(self):
        for row in self.patch['patches']:
            self.assertLess(int(row['functional_word_octal'],8),1<<41)
    def test_pinned_image_name(self):
        self.assertEqual((HERE/'inputs/FP_FUNCTIONAL_1962_RECONSTRUCTED.k41').name,'FP_FUNCTIONAL_1962_RECONSTRUCTED.k41')

if __name__=='__main__':unittest.main()
