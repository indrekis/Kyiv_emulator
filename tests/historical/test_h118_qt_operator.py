"""H118 offline validation and negative tests; native Qt acceptance is separate."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/historical/qt_h118_operator_v1.py'


def module():
    spec = importlib.util.spec_from_file_location('h118_qt_operator_tested', SOURCE)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class H118QtOperatorTests(unittest.TestCase):
    def test_component_validation_delegates_to_existing_c2b(self):
        s = SOURCE.read_text(encoding='utf-8')
        self.assertIn('op.validate(repo, scenario_id)', s)
        self.assertIn('cat.prepare(repo, scenario[\'rom_set\'], out / \'rom\')', s)
        self.assertNotIn('execute_opcode(', s)

    def test_reject_existing_output_without_modifying_it(self):
        candidate = module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'tempkyiv').mkdir()
            out = root / 'tempkyiv/occupied'
            out.mkdir()
            (out / 'SENTINEL').write_text('still here', encoding='ascii')
            prog = root / 'original.k41'
            prog.write_text('KYIV41-OCT1\n0001 33000000000000\n', encoding='ascii')
            class Op:
                def validate(self, repo, id):
                    return ({'program': {'sha256': candidate.sha(prog.read_bytes())},
                             'rom_set': 'test'}, prog, {})
            with patch.object(candidate, 'components', return_value=(Op(), object())):
                with self.assertRaisesRegex(candidate.Hold, 'OUTPUT_NOT_NEW'):
                    candidate.prepare(root, 'example', out)
            self.assertEqual((out / 'SENTINEL').read_text(), 'still here')

    def test_reject_outside_temp(self):
        candidate = module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'tempkyiv').mkdir()
            prog = root / 'program.k41'
            prog.write_text('KYIV41-OCT1\n0001 33000000000000\n', encoding='ascii')
            class Op:
                def validate(self, repo, id):
                    return ({'program': {'sha256': candidate.sha(prog.read_bytes())},
                             'rom_set': 'test'}, prog, {})
            with patch.object(candidate, 'components', return_value=(Op(), object())):
                with self.assertRaisesRegex(candidate.Hold, 'OUTPUT_NOT_NEW'):
                    candidate.prepare(root, 'test', root / 'unsafe')
            self.assertFalse((root / 'unsafe').exists())

    def test_success_preserves_program_and_exact_action_plan(self):
        candidate = module()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'tempkyiv').mkdir()
            prog = root / 'program.k41'
            prog.write_text('KYIV41-OCT1\n0001 33000000000000\n', encoding='ascii')
            actions = [{'op':'step','count':1,'origin':'HOST_TEST','expect':{
                'executed':1,'path':['0001'],'state':{'STEPS':1}}}]
            class Op:
                def validate(self, repo, id):
                    return ({'id':'example','description':'test demo','origin':'HOST_TEST',
                         'entry':'0001','max_steps':3,'program':{'sha256':candidate.sha(prog.read_bytes())},
                         'rom_set':'test','actions':actions},prog,{})
            class Cat:
                def prepare(self, repo, set_id, out):
                    out.mkdir()
                    (out / 'replaceable.k41').write_text('KYIV41-OCT1\n3300 33000000000000\n',encoding='ascii')
            out = root / 'tempkyiv/first'
            with patch.object(candidate, 'components', return_value=(Op(),Cat())):
                result = candidate.prepare(root, 'example', out)
            self.assertEqual(result['status'],'PASS_H118_OPERATOR_PREPARED_NOT_EXECUTED')
            self.assertEqual(result['actions'],actions)
            self.assertEqual((out / 'program.k41').read_bytes(),prog.read_bytes())
            self.assertEqual(json.loads((out / 'RESULT.json').read_text())['id'],'example')
            self.assertTrue((out / 'rom/replaceable.k41').exists())

    def test_gui_hooks_and_dispatch_counter_present(self):
        front = (ROOT / 'gui/qt6/qt_main.cpp').read_text(encoding='utf-8')
        backend = (ROOT / 'gui/qt6/kyiv_gui_backend.cpp').read_text(encoding='utf-8')
        bridge = (ROOT / 'tools/historical/qt_rom_browser_v1.py').read_text(encoding='utf-8')
        for token in ('startOperatorReplay()', 'checkOperatorResponse(', 'startOracleAudit()',
                      'PASS_H118_C2A_GUI_NATIVE_ORACLE_NOT_HARDWARE',
                      'PASS_H118_C2B_GUI_PERSISTENT_HOST_NOT_HARDWARE'):
            self.assertIn(token,front)
        self.assertIn("response['oracle']",bridge)
        self.assertIn('fp_dispatches',backend)
        self.assertIn('saved_fp_dispatches',backend)
        self.assertIn('DISPATCHES=',backend)


if __name__=='__main__':unittest.main()
