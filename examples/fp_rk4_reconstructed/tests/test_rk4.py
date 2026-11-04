from __future__ import annotations
import sys
import unittest
from pathlib import Path
from fractions import Fraction
from zipfile import ZipFile
from tempfile import TemporaryDirectory

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import oracle
import run as demo

class RK4Tests(unittest.TestCase):
    def test_provenance(self):
        self.assertEqual(demo.verify_inputs()['status'], 'PASS_H115_B16_R1_BOUNDED_SUM_RK4_NOT_HISTORICAL')
    def test_saved_accepted_evidence(self):
        s=demo.audit_saved_evidence()
        self.assertEqual(s['native_steps'],1637)
        self.assertEqual(s['dispatcher_checkpoints'],54)
    def test_historical_source_does_not_get_invented(self):
        src=(HERE/'native.cpp').read_text()
        self.assertNotIn('cpu.kmem.write_rom(03574',src)
        self.assertIn('HOLD_UNPRINTED_ROM_3574',src)
    def test_oracle_rk4_polynomial(self):
        h=Fraction(1,4)
        r=1-h+h*h/2-h**3/6+h**4/24
        self.assertEqual(r,Fraction(1595,2048))
        self.assertEqual(r*r,Fraction(2544025,4194304))
    def test_oracle_two_steps(self):
        it=oracle.math_iterations()
        self.assertEqual([x['y_after'] for x in it],['1595/2048','2544025/4194304'])
    def test_fp_image_47_words(self):
        w=oracle.parse_image((HERE/'inputs/RK4_IMAGE.k41').read_bytes())
        self.assertEqual(w,oracle.expected_image())
        self.assertEqual(len(w),47)
        self.assertEqual(f'{w[0o252]:014o}','01011001060127')
    def test_full_independent_oracle(self):
        expected,stages=oracle.simulation()
        self.assertEqual(len(expected),54)
        self.assertEqual(len(stages),50)
        self.assertEqual(expected[-1]['pointer'],'0273')
    def test_original_overflow_negative_control(self):
        self.assertEqual(oracle.static()['status'],'PASS_B16_STATIC_NOT_NATIVE')
    def test_reject_bad_image_header(self):
        with self.assertRaises(oracle.Hold):oracle.parse_image(b'KYIV41-FAKE\n0100 00000000000000\n')
    def test_reject_duplicated_image_word(self):
        raw=(HERE/'inputs/RK4_IMAGE.k41').read_bytes()
        with self.assertRaises(oracle.Hold):oracle.parse_image(raw+raw.splitlines()[1]+b'\n')
    def test_reject_checkpoint_tampering(self):
        with ZipFile(HERE/'evidence/H115_B16_R1_FP_RK4_BOUNDED_SUM_EVIDENCE_V1.zip') as z:
            f={name:z.read(name) for name in z.namelist()}
        f['NATIVE_CHECKPOINTS.tsv']=f['NATIVE_CHECKPOINTS.tsv'].replace(b'WORD_MATCH',b'WORD_FAKE',1)
        self.assertEqual(oracle.judge(f,0)['status'],'HOLD_H115_B16_R1')
    def test_reject_trace_truncation(self):
        with ZipFile(HERE/'evidence/H115_B16_R1_FP_RK4_BOUNDED_SUM_EVIDENCE_V1.zip') as z:
            f={name:z.read(name) for name in z.namelist()}
        f['NATIVE_TRACE.tsv']=b'\n'.join(f['NATIVE_TRACE.tsv'].splitlines()[:5])+b'\n'
        with self.assertRaises(oracle.Hold):oracle.judge(f,0)
    def test_reject_nonzero_cpu_return(self):
        with ZipFile(HERE/'evidence/H115_B16_R1_FP_RK4_BOUNDED_SUM_EVIDENCE_V1.zip') as z:
            f={name:z.read(name) for name in z.namelist()}
        self.assertEqual(oracle.judge(f,4)['status'],'HOLD_H115_B16_R1')
    def test_reject_missing_evidence(self):
        with ZipFile(HERE/'evidence/H115_B16_R1_FP_RK4_BOUNDED_SUM_EVIDENCE_V1.zip') as z:
            f={name:z.read(name) for name in z.namelist()}
        f.pop('NATIVE_CHECKPOINTS.tsv')
        self.assertEqual(oracle.judge(f,0)['status'],'HOLD_H115_B16_R1')

if __name__=='__main__':unittest.main()
