from __future__ import annotations
import importlib.util
import json
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile
import unittest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fp_euler_demo', HERE/'run.py')
euler=importlib.util.module_from_spec(spec)
spec.loader.exec_module(euler)

class EulerExampleTests(unittest.TestCase):
    def test_source_pins(self):
        p=euler.verify_inputs()
        self.assertEqual(p['schema'],'KYIV_H115_B17_FP_EULER_EXAMPLE_V1')
    def test_original_cpu_run_reaudited(self):
        r=euler.saved_evidence()
        self.assertEqual(r['steps'],619)
        self.assertEqual(r['checkpoint_matches'],24)
        self.assertEqual(r['status'],euler.PASS)
    def test_trajectory(self):
        result=euler.calculate_steps()
        self.assertEqual([x['y_after'] for x in result],['3/4','9/16','27/64','81/256'])
        self.assertEqual([x['t_after'] for x in result],['1/4','1/2','3/4','1'])
        self.assertEqual([x['difference'] for x in result],['5/8','3/8','1/8','-1/8'])
    def test_final_fp_word(self):
        self.assertEqual(euler.encode_fp(Fraction(81,256)), '12100000000077')
    def test_image_immutable(self):
        words=euler.parse_image((HERE/'inputs/EULER_IMAGE.k41').read_bytes())
        self.assertEqual(len(words),13)
        self.assertEqual(f'{words[0o230]:014o}','11010001010104')
        self.assertEqual(f'{words[0o234]:014o}','31010502350236')
        self.assertEqual(f'{words[0o235]:014o}','31000002300230')
    def test_all_checkpoints(self):
        c=euler.expected_checkpoints()
        self.assertEqual(len(c),24)
        self.assertEqual(c[0]['pointer'],'0230')
        self.assertEqual(c[-1]['pointer'],'0236')
        self.assertEqual(c[-1]['y'],euler.encode_fp(Fraction(81,256)))
    def test_reject_image_wrong_magic(self):
        with self.assertRaises(euler.AuditError):
            euler.parse_image(b'KYIV41-OCT2\n0230 11010001010104\n')
    def test_reject_duplicate_image(self):
        raw=(HERE/'inputs/EULER_IMAGE.k41').read_bytes()
        with self.assertRaises(euler.AuditError):
            euler.parse_image(raw+raw.splitlines()[1]+b'\n')
    def test_reject_scratch_overlap(self):
        with self.assertRaises(euler.AuditError):
            euler.parse_image(b'KYIV41-OCT1\n0001 00000000000001\n')
    def test_reject_evidence_corruption(self):
        path=HERE/'evidence/H115_B15_FP_EULER_ODE_EVIDENCE_V1.zip'
        with ZipFile(path) as z:
            files={n:z.read(n) for n in z.namelist()}
        bad=files.copy()
        bad['NATIVE_SESSIONS.tsv']=bad['NATIVE_SESSIONS.tsv'].replace(b'\t24\t',b'\t23\t')
        with self.assertRaises(euler.AuditError):
            euler.check_evidence(bad)
    def test_reject_truncated_trace(self):
        path=HERE/'evidence/H115_B15_FP_EULER_ODE_EVIDENCE_V1.zip'
        with ZipFile(path) as z:
            files={n:z.read(n) for n in z.namelist()}
        bad=files.copy()
        bad['NATIVE_TRACE.tsv']=b'\n'.join(bad['NATIVE_TRACE.tsv'].splitlines()[:5])+b'\n'
        with self.assertRaises(euler.AuditError):
            euler.check_evidence(bad)
    def test_reject_non_dyadic(self):
        with self.assertRaises(euler.AuditError):
            euler.encode_fp(Fraction(1,3))
    def test_no_missing_historic_word(self):
        src=(HERE/'native.cpp').read_text(encoding='utf-8')
        self.assertNotIn('cpu.kmem.write_rom(03574',src)
        self.assertIn('HOLD_UNPRINTED_ROM_3574',src)
        self.assertIn('cpu.C_reg=03300',src)
        self.assertIn('HOLD_RAW_USER_INSTRUCTION_FETCH',src)

if __name__=='__main__':unittest.main()
