import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'tools/historical/run.py'
spec=importlib.util.spec_from_file_location('historical_run', SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ReadonlyROM(unittest.TestCase):
    def test_real_module1_pin_and_layout(self):
        p=mod.prepare('module1')
        self.assertEqual((p['records'],p['known_missing'],p['source_pin_verified']), (64,[],True))

    def test_fp_missing_source_is_hold(self):
        with self.assertRaises(mod.GateError):mod.prepare('fp_simulation')

    def test_fp_251_sparse_with_known_holes(self):
        expected=mod.slot_addresses('3300','3777')-mod.known_holes()
        self.assertEqual(len(expected),251)
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'fp.k41'
            src.write_bytes(('KYIV41-OCT1\n'+''.join(f'{x:04o} 00000000000000\n' for x in sorted(expected))).encode())
            result=mod.prepare('fp_simulation',src)
            self.assertEqual((result['records'],len(result['known_missing']),result['source_pin_verified']),(251,69,False))
            out=Path(tmp)/'output'
            mod.prepare('fp_simulation',src,output=out)
            self.assertEqual(mod.parse_k41((out/'words.k41').read_bytes()),mod.parse_k41(src.read_bytes()))
            with self.assertRaises(mod.GateError):mod.prepare('fp_simulation',src,output=out)
            with self.assertRaises(mod.GateError):mod.prepare('fp_simulation',src,expected_sha='0'*64)

    def test_unknown_slot_not_silently_filled(self):
        s=json.loads((mod.MANIFESTS/'fp_simulation.json').read_text())
        good={a:'0'*14 for a in mod.slot_addresses('3300','3777')-mod.known_holes()}
        for changed in ({**good,0o3574:'0'*14},{k:v for k,v in good.items() if k!=0o3300}):
            with self.assertRaises(mod.GateError):mod.validate_spec(s,changed)

    def test_collisions_and_bad_records_rejected(self):
        for raw in [b'KYIV41-OCT1\n3300 00000000000000\n3300 00000000000000\n',
                    b'KYIV41-OCT1\n3300 40000000000000\n',
                    b'KYIV41-OCT1\n3300 00000000000008\n']:
            with self.assertRaises(mod.GateError):mod.parse_k41(raw)
        with self.assertRaises(mod.GateError):mod.validate_spec({'schema':'KYIV_H114_ROMSET_V1','id':'module1','slots':[['3300','3377'],['3370','3477']]}, {})

    def test_cli(self):
        x=subprocess.run([sys.executable,str(SCRIPT),'validate','module1'],capture_output=True,text=True,check=True)
        self.assertIn('PASS_H114_SOURCE_LAYOUT_NOT_NATIVE',x.stdout)
        bad=subprocess.run([sys.executable,str(SCRIPT),'validate','fp_simulation'],capture_output=True,text=True)
        self.assertEqual(bad.returncode,2)
        self.assertIn('HOLD_H114_ROMSET',bad.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
