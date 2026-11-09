"""H116-H1 isolated bridge orchestration tests, no production CPU or repo writes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

BRIDGE = Path(__file__).resolve().parents[2] / 'tools/historical/qt_rom_browser_v1.py'
SPEC = importlib.util.spec_from_file_location('h116_qt_browser', BRIDGE)
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)

CATALOG = '''
from pathlib import Path
import json,re,hashlib
class CatalogError(ValueError):pass
def id_ok(s): return bool(re.fullmatch('[a-z][a-z0-9_]{1,47}',str(s)))
def read_json(p): return json.loads(Path(p).read_text())
def validate_set(repo,sid):
 s=read_json(Path(repo)/'examples/rom_catalog/sets'/(sid+'.json'))
 if s['id']!=sid:raise CatalogError('SET_ID_DRIFT')
 return ({'modules':[{'provenance':s['provenance']}], 'unknown_slots_words':s['unknown'],'words':1}, {0o3300:'00000000000001'})
def prepare(repo,sid,out):
 report,_=validate_set(repo,sid)
 out=Path(out)
 if out.exists() or not out.resolve().is_relative_to((Path(repo)/'tempkyiv').resolve()): raise CatalogError('OUT_UNSAFE')
 out.mkdir(parents=True)
 (out/'replaceable.k41').write_bytes(b'KYIV41-OCT1\\n3300 00000000000001\\n')
 return report
'''
SCENARIOS = '''
from pathlib import Path
import json,hashlib,re
class ScenarioError(ValueError):pass
def valid_id(s):return bool(re.fullmatch('[a-z][a-z0-9_]{1,47}',str(s)))
def existing_in_repo(repo,rel):
 if not isinstance(rel,str) or not rel.startswith('examples/') or '..' in rel:raise ScenarioError('PROGRAM_PATH')
 return Path(repo)/rel
def check(repo, sid):
 j=json.loads((Path(repo)/'examples/rom_scenarios'/(sid+'.json')).read_text())
 path=existing_in_repo(repo,j['program']['path'])
 if hashlib.sha256(path.read_bytes()).hexdigest()!=j['program']['sha256']:raise ScenarioError('PROGRAM_SHA_DRIFT')
 return j,{}
'''
class Cases(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.repo=Path(self.t.name)
        for d in ('tools/historical','examples/rom_catalog/sets','examples/rom_scenarios',
                  'examples/programs','tempkyiv'):(self.repo/d).mkdir(parents=True)
        (self.repo/'tools/historical/rom_catalog_v1.py').write_text(CATALOG)
        (self.repo/'tools/historical/rom_scenarios_v1.py').write_text(SCENARIOS)
        self.mkset('alpha','SYNTHETIC_TEST')
        self.mkprogram('demo','alpha')
    def mkset(self,name,origin):
        p=self.repo/'examples/rom_catalog/sets'/(name+'.json')
        p.write_text(json.dumps({'id':name,'description':'Test '+name,'provenance':origin,'unknown':5}))
    def mkprogram(self,name,rom):
        raw=b'KYIV41-OCT1\n0001 33000000000000\n'
        rel='examples/programs/'+name+'.k41'
        (self.repo/rel).write_bytes(raw)
        (self.repo/'examples/rom_scenarios'/(name+'.json')).write_text(json.dumps({
            'id':name,'description':'Test scenario '+name,'origin':'HOST_TEST','rom_set':rom,
            'program':{'path':rel,'sha256':hashlib.sha256(raw).hexdigest()},
            'entry':'0001','mode':'image','end_pointer':None}))
    def test_list(self):
        r=bridge.list_items(self.repo)
        self.assertEqual(r['sets'][0]['id'],'alpha')
        self.assertEqual(r['scenarios'][0]['id'],'demo')
        self.assertIsNone(r['scenarios'][0]['end_pointer'])
    def test_fp_mode_end_pointer_passed_to_gui(self):
        spec_path=self.repo/'examples/rom_scenarios/demo.json'
        spec=json.loads(spec_path.read_text())
        spec['mode']='fp-image'
        spec['end_pointer']='0002'
        spec_path.write_text(json.dumps(spec))
        result=bridge.list_items(self.repo)
        self.assertEqual(result['scenarios'][0]['mode'],'fp-image')
        self.assertEqual(result['scenarios'][0]['end_pointer'],'0002')

    def test_prepare(self):
        out=self.repo/'tempkyiv'/'new'
        r=bridge.prepare(self.repo,'alpha',out,'demo')
        self.assertEqual(r['scenario_id'],'demo')
        self.assertEqual(hashlib.sha256((out/'replaceable.k41').read_bytes()).hexdigest(),r['sha256'])
        self.assertEqual(hashlib.sha256((out/'program.k41').read_bytes()).hexdigest(),r['program_sha256'])
        self.assertEqual(r['entry'],'0001')
    def test_prepare_no_scenario(self):
        r=bridge.prepare(self.repo,'alpha',self.repo/'tempkyiv'/'new',None)
        self.assertNotIn('program_path',r)
    def test_new_set_without_code(self):
        self.mkset('another','SOURCE_TRANSCRIPTION')
        self.mkprogram('another_demo','another')
        r=bridge.list_items(self.repo)
        self.assertEqual([x['id'] for x in r['sets']],['alpha','another'])
        self.assertEqual(len(r['scenarios']),2)
    def test_bad_set(self):
        with self.assertRaises(Exception):bridge.prepare(self.repo,'missing',self.repo/'tempkyiv'/'new',None)
    def test_mismatched_scenario_set(self):
        self.mkset('other','SYNTHETIC_TEST')
        with self.assertRaisesRegex(bridge.BrowserError,'SCENARIO_SET_MISMATCH'):
            bridge.prepare(self.repo,'other',self.repo/'tempkyiv'/'new','demo')
        self.assertFalse((self.repo/'tempkyiv'/'new').exists())
    def test_drifted_program(self):
        (self.repo/'examples/programs/demo.k41').write_text('changed')
        with self.assertRaisesRegex(Exception,'SHA_DRIFT'):
            bridge.prepare(self.repo,'alpha',self.repo/'tempkyiv'/'new','demo')
        self.assertFalse((self.repo/'tempkyiv'/'new').exists())
    def test_duplicate_output(self):
        dest=self.repo/'tempkyiv'/'new';dest.mkdir()
        with self.assertRaisesRegex(Exception,'OUT_UNSAFE'):
            bridge.prepare(self.repo,'alpha',dest,None)
    def test_unsafe_output(self):
        with self.assertRaisesRegex(Exception,'OUT_UNSAFE'):
            bridge.prepare(self.repo,'alpha',self.repo/'examples'/'bad',None)
    def test_invalid_id(self):
        with self.assertRaisesRegex(Exception,'INVALID_SET_ID'):
            bridge.prepare(self.repo,'../../bad',self.repo/'tempkyiv'/'new',None)
    def test_symlink_set_rejected(self):
        p=self.repo/'examples/rom_catalog/sets'/'link.json'
        try:p.symlink_to(self.repo/'examples/rom_catalog/sets'/'alpha.json')
        except (OSError,NotImplementedError):self.skipTest('Symlinks disabled')
        with self.assertRaisesRegex(bridge.BrowserError,'SET_CATALOG_UNSAFE'):
            bridge.list_items(self.repo)
    def test_symlink_scenario_rejected(self):
        p=self.repo/'examples/rom_scenarios'/'link.json'
        try:p.symlink_to(self.repo/'examples/rom_scenarios'/'demo.json')
        except (OSError,NotImplementedError):self.skipTest('Symlinks disabled')
        with self.assertRaisesRegex(bridge.BrowserError,'SCENARIO_FILE_UNSAFE'):
            bridge.list_items(self.repo)
    def test_bad_scenario_blocks_catalog(self):
        (self.repo/'examples/programs/demo.k41').unlink()
        with self.assertRaises(Exception):bridge.list_items(self.repo)

if __name__=='__main__':unittest.main()
