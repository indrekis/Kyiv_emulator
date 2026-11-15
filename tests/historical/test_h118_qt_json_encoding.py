"""Regression: Python pipe JSON must decode as UTF-8 even with Windows cp1251 stdout."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module(relpath, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def emulate_cp1251_stdout(callback):
    wire = io.BytesIO()
    stream = io.TextIOWrapper(wire, encoding='cp1251', errors='strict', newline='\n')
    with contextlib.redirect_stdout(stream):
        rc = callback()
        stream.flush()
    return rc, wire.getvalue()


class QtJSONEncodingTests(unittest.TestCase):
    def test_operator_list_non_ascii_uses_utf8_safe_wire(self):
        m = module('tools/historical/qt_h118_operator_v1.py', 'test_op_encoding')
        response = {'status': 'PASS_H118_OPERATOR_LIST', 'items': [
            {'id':'au_h117_two_epochs', 'description':'АУ: дві епохи → 0360',
             'origin':'RECONSTRUCTED_ASSUMPTION'}]}
        with patch.object(m, 'list_items', return_value=response):
            rc, raw = emulate_cp1251_stdout(lambda: m.main(['--repo', str(ROOT), 'list']))
        self.assertEqual(rc, 0)
        self.assertTrue(raw.isascii(), 'Machine JSON must be ASCII/UTF-8 wire-safe')
        self.assertEqual(json.loads(raw.decode('utf-8')), response)
        self.assertIn(b'\\u0410', raw)

    def test_operator_prepare_non_ascii_uses_utf8_safe_wire(self):
        m = module('tools/historical/qt_h118_operator_v1.py', 'test_op_prepare_encoding')
        response = {'status': 'PASS_H118_OPERATOR_PREPARED_NOT_EXECUTED',
                    'id': 'au_h117_two_epochs',
                    'description':'Функціональна реконструкція — 0360 → 0042'}
        with patch.object(m, 'prepare', return_value=response):
            rc, raw = emulate_cp1251_stdout(lambda: m.main(
                ['--repo', str(ROOT), 'prepare', 'au_h117_two_epochs',
                 '--out', str(ROOT/'tempkyiv'/'not_created')]))
        self.assertEqual(rc, 0)
        self.assertTrue(raw.isascii())
        self.assertEqual(json.loads(raw.decode('utf-8')), response)

    def test_rom_catalog_non_ascii_uses_utf8_safe_wire(self):
        m = module('tools/historical/qt_rom_browser_v1.py', 'test_rom_encoding')
        response = {'status':'PASS_H116_H1_CATALOG_VALIDATED', 'sets':[],
                    'scenarios':[{'description':'Математична ПЗП №1 — демонстрація'}]}
        with patch.object(m, 'list_items', return_value=response):
            rc, raw = emulate_cp1251_stdout(lambda: m.main(['--repo', str(ROOT), 'list']))
        self.assertEqual(rc, 0)
        self.assertTrue(raw.isascii())
        self.assertEqual(json.loads(raw.decode('utf-8')), response)

    @unittest.skipUnless((ROOT/'examples/operator_scenarios/au_h117_two_epochs.json').is_file(),
                         'Integration test requires staged H118-P2-B scenario')
    def test_real_c2b_list_cp1251_pipe(self):
        self._real('tools/historical/qt_h118_operator_v1.py', 'PASS_H118_OPERATOR_LIST',
                   'au_h117_two_epochs')

    @unittest.skipUnless((ROOT/'examples/rom_scenarios/fp_euler.json').is_file(),
                         'Integration test requires repository')
    def test_real_c2a_list_cp1251_pipe(self):
        self._real('tools/historical/qt_rom_browser_v1.py',
                   'PASS_H116_H1_CATALOG_VALIDATED', 'fp_euler')

    def _real(self, script, status, scenario_id):
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'cp1251:strict'
        r = subprocess.run([sys.executable, '-B', str(ROOT/script), '--repo', str(ROOT), 'list'],
                           cwd=ROOT, env=env, capture_output=True, timeout=35)
        self.assertEqual(r.returncode, 0, r.stderr.decode('utf-8', errors='replace')[:900])
        self.assertTrue(r.stdout.isascii(), 'Windows cp1251 pipe produced non-UTF8 bytes')
        data = json.loads(r.stdout.decode('utf-8'))
        self.assertEqual(data['status'], status)
        self.assertIn(scenario_id,
                      [item['id'] for item in data['items' if 'items' in data else 'scenarios']])

if __name__=='__main__': unittest.main()
