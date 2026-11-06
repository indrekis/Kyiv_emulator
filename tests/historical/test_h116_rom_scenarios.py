#!/usr/bin/env python3
"""H116-C2a standalone offline tests; no emulator executable required."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[2]/'tools/historical/rom_scenarios_v1.py'
if not SCRIPT.is_file():
    # Candidate package: the test resides under payload/tests/historical.
    SCRIPT=Path(__file__).resolve().parents[2]/'tools/historical/rom_scenarios_v1.py'
loader=importlib.util.spec_from_file_location('h116_rom_scenarios_unit',SCRIPT)
S=importlib.util.module_from_spec(loader);loader.loader.exec_module(S)
FIXTURES=Path(__file__).resolve().parents[2]/'examples/rom_scenarios'

class CatalogStub:
    def parse_k41(self,path,sha):
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('SHA')
        records={}
        for line in raw.decode('ascii').splitlines()[1:]:
            a,w=line.split(); records[int(a,8)]=w
        return records
    def validate_set(self,repo,name):
        if name not in ('math_module1','fp_functional'):
            raise ValueError('WRONG_SET')
        return {'set':name}, {0o3300:'01000000000003'}

class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'examples/rom_scenarios/inputs').mkdir(parents=True)
        (self.root/'tempkyiv').mkdir()
        shutil.copyfile(FIXTURES/'inputs/romset_smoke_stop.k41',self.root/'examples/rom_scenarios/inputs/romset_smoke_stop.k41')
        self.manifest=json.loads((FIXTURES/'romset_smoke.json').read_text())
        self.path=self.root/'examples/rom_scenarios/romset_smoke.json'
        self.write()
        self.catalog_patch=patch.object(S,'catalog_module',return_value=CatalogStub())
        self.catalog_patch.start()
        self.addCleanup(self.catalog_patch.stop)
    def write(self):self.path.write_text(json.dumps(self.manifest),encoding='utf-8')
    def expect_hold(self,code):
        with self.assertRaises(S.ScenarioError) as e:S.check(self.root,'romset_smoke')
        self.assertIn(code,str(e.exception))
    def sample(self):
        return subprocess.CompletedProcess([],0,'D15A2-RUN STATUS=CPU_STOP STEPS=1 C=0002 K=33000000000000 A=0000 P=0000 LOOP=0000 T=0\nD15A2-WATCH ADDR=3300 RAW=01000000000003\n','')
    def test_staged_program_before_install(self):
        # Mirrors preflight: the new RAM image is in tempkyiv/payload, not in examples/.
        staged=self.root/'tempkyiv'/'pending_payload'
        (staged/'examples/rom_scenarios/inputs').mkdir(parents=True)
        original=self.root/'examples/rom_scenarios/inputs/romset_smoke_stop.k41'
        shutil.copyfile(original,staged/'examples/rom_scenarios/inputs/romset_smoke_stop.k41')
        original.unlink()
        with self.assertRaisesRegex(S.ScenarioError,'PROGRAM_MISSING_OR_UNSAFE'):
            S.check(self.root,'romset_smoke')
        spec,_=S.check(self.root,'romset_smoke',program_staging_root=staged)
        self.assertEqual(spec['id'],'romset_smoke')
    def test_staged_program_wrong_sha_rejected(self):
        staged=self.root/'tempkyiv'/'pending_payload'
        (staged/'examples/rom_scenarios/inputs').mkdir(parents=True)
        (staged/'examples/rom_scenarios/inputs/romset_smoke_stop.k41').write_bytes(b'KYIV41-OCT1\n0001 33000000000000\n# drift\n')
        (self.root/'examples/rom_scenarios/inputs/romset_smoke_stop.k41').unlink()
        with self.assertRaisesRegex(S.ScenarioError,'PROGRAM_SHA_DRIFT'):
            S.check(self.root,'romset_smoke',program_staging_root=staged)
    def test_staged_program_outside_tempkyiv_rejected(self):
        outside=self.root/'examples'
        with self.assertRaisesRegex(S.ScenarioError,'STAGED_PROGRAM_ROOT_UNSAFE'):
            S.check(self.root,'romset_smoke',program_staging_root=outside)
    def test_installed_program_has_precedence(self):
        staged=self.root/'tempkyiv'/'pending_payload'
        (staged/'examples/rom_scenarios/inputs').mkdir(parents=True)
        (staged/'examples/rom_scenarios/inputs/romset_smoke_stop.k41').write_bytes(b'wrong')
        spec,_=S.check(self.root,'romset_smoke',program_staging_root=staged)
        self.assertEqual(spec['id'],'romset_smoke')
    def test_valid_smoke(self):
        spec,_=S.check(self.root,'romset_smoke')
        self.assertEqual(S.evaluate(spec,self.sample())['steps'],1)
    def test_manifest_wrong_sha(self):
        self.manifest['program']['sha256']='0'*64;self.write();self.expect_hold('PROGRAM_SHA_DRIFT')
    def test_path_escape(self):
        self.manifest['program']['path']='examples/../mem/ROM.txt';self.write();self.expect_hold('UNSAFE_PROGRAM_PATH')
    def test_duplicate_json_keys(self):
        self.path.write_text(self.path.read_text()[:-1]+',"id":"romset_smoke"}',encoding='utf-8')
        self.expect_hold('DUPLICATE_JSON_KEY')
    def test_unknown_schema(self):
        self.manifest['schema']='UNKNOWN';self.write();self.expect_hold('SCENARIO_SCHEMA_OR_ID')
    def test_bad_entry(self):
        self.manifest['entry']='0002';self.write();self.expect_hold('ENTRY_MISSING')
    def test_bad_mode(self):
        self.manifest['mode']='arbitrary';self.write();self.expect_hold('MODE_INVALID')
    def test_invalid_limit(self):
        self.manifest['max_steps']=100001;self.write();self.expect_hold('STEP_LIMIT')
    def test_bad_watch_address(self):
        self.manifest['watches']={'2000':'00000000000000'};self.write();self.expect_hold('WATCH_ADDRESS')
    def test_bad_watch_width(self):
        self.manifest['watches']={'3300':'77777777777777'};self.write();self.expect_hold('WATCH_WORD')
    def test_unexpected_end_pointer(self):
        self.manifest['end_pointer']='0001';self.write();self.expect_hold('IMAGE_END_POINTER_FORBIDDEN')
    def test_dispatch_count_in_image(self):
        self.manifest['expect']['dispatches']=1;self.write();self.expect_hold('IMAGE_DISPATCHES')
    def test_image_status_mismatch(self):
        self.manifest['expect']['status']='LIMIT';self.write();self.expect_hold('EXPECT_STATUS')
    def test_executable_return_failure(self):
        spec,_=S.check(self.root,'romset_smoke')
        x=self.sample();x.returncode=5
        with self.assertRaisesRegex(S.ScenarioError,'CPU_RETURN_CODE'):S.evaluate(spec,x)
    def test_native_step_mismatch(self):
        spec,_=S.check(self.root,'romset_smoke')
        x=self.sample();x.stdout=x.stdout.replace('STEPS=1','STEPS=2')
        with self.assertRaisesRegex(S.ScenarioError,'STEPS_MISMATCH'):S.evaluate(spec,x)
    def test_native_watch_mismatch(self):
        spec,_=S.check(self.root,'romset_smoke')
        x=self.sample();x.stdout=x.stdout.replace('01000000000003','01000000000002')
        with self.assertRaisesRegex(S.ScenarioError,'WATCH_VALUE_MISMATCH'):S.evaluate(spec,x)
    def test_native_missing_watch(self):
        spec,_=S.check(self.root,'romset_smoke')
        x=self.sample();x.stdout=x.stdout.split('D15A2-WATCH')[0]
        with self.assertRaisesRegex(S.ScenarioError,'WATCH_SET_MISMATCH'):S.evaluate(spec,x)
    def test_native_status_limit(self):
        spec,_=S.check(self.root,'romset_smoke')
        x=self.sample();x.stdout=x.stdout.replace('CPU_STOP','LIMIT')
        with self.assertRaisesRegex(S.ScenarioError,'RESULT_STATUS_MISMATCH'):S.evaluate(spec,x)
    def test_wrong_scenario_directory(self):
        with self.assertRaisesRegex(S.ScenarioError,'DIRECTORY_OUTSIDE_ALLOWED_AREA'):
            S.check(self.root,'romset_smoke',Path('/tmp'))
    def test_existing_output_fails_before_execution(self):
        out=self.root/'tempkyiv'/'existing';out.mkdir()
        fake=self.root/'binary.exe';fake.write_bytes(b'dummy')
        with self.assertRaisesRegex(S.ScenarioError,'OUTPUT_NOT_NEW_UNDER_TEMPKYIV'):
            S.execute(self.root,'romset_smoke',fake,out)
    def test_program_not_ram(self):
        new=b'KYIV41-OCT1\n3300 33000000000000\n'
        p=self.root/'examples/rom_scenarios/inputs/romset_smoke_stop.k41';p.write_bytes(new)
        self.manifest['program']['sha256']=hashlib.sha256(new).hexdigest();self.write()
        self.expect_hold('NOT_RAM_PROGRAM')
    def test_fp_end_required(self):
        self.manifest['mode']='fp-image';self.manifest['expect']['status']='END_POINTER';self.manifest['expect']['dispatches']=1;self.write()
        self.expect_hold('FP_END_POINTER_MISSING')

if __name__=='__main__':unittest.main(verbosity=2)
