#!/usr/bin/env python3
"""Source-only tests for the 2026 H115-B23 user-program example."""
from __future__ import annotations
import importlib.util
import json
from fractions import Fraction as F
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('h115_b23_oracle',HERE/'oracle.py')
assert spec and spec.loader
oracle=importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)

class FPUserProgramTests(unittest.TestCase):
    def test_exact_image(self):
        self.assertEqual((HERE/'inputs/AFFINE_RECURRENCE.k41').read_bytes(),oracle.render_image())

    def test_distinct_new_program(self):
        self.assertEqual(len(oracle.CODE),7)
        self.assertEqual(oracle.CODE[0],(0o1,0o100,0o101,0o102))
        self.assertEqual(oracle.CODE[1],(0o11,0o102,0o101,0o100))
        self.assertEqual(oracle.CODE[2],(0o1,0o103,0o104,0o103))
        self.assertEqual(oracle.CODE[3],(0o2,0o105,0o103,0o106))

    def test_machine_branch_exit(self):
        self.assertEqual(oracle.CODE[4],(0o31,0o106,0o305,0o306))
        self.assertEqual(oracle.CODE[5],(0o31,0,0o300,0o300))
        self.assertEqual(oracle.CODE[6],(0o33,0,0,0))

    def test_14_unique_ram_words(self):
        image=oracle.image_words()
        self.assertEqual(len(image),14)
        self.assertTrue(all(0<a<0o2000 for a in image))
        self.assertEqual(len(set(image)),14)

    def test_true_four_step_iteration(self):
        it=oracle.itinerary()
        self.assertEqual([F(i['x']) for i in it],
                         [F(3,8),F(7,16),F(15,32),F(31,64)])
        self.assertEqual([i['stop'] for i in it],[False,False,False,True])

    def test_exact_mantissas(self):
        for i in oracle.itinerary():
            for key in ('x','tmp','t','d'):
                self.assertEqual(f'{oracle.exact_fp_word(F(i[key])):014o}',i[key+'_word'])

    def test_oracle_file(self):
        self.assertEqual(json.loads((HERE/'inputs/INDEPENDENT_ORACLE.json').read_text('utf-8')),
                         oracle.expected_json())

    def test_variants_only_change_threshold(self):
        default=oracle.image_words()
        for n in range(1,5):
            v=oracle.image_words(F(2*n-1,8))
            self.assertEqual({k:v[k] for k in v if k!=0o105},
                             {k:default[k] for k in default if k!=0o105})
            self.assertEqual(v[0o105],oracle.exact_fp_word(F(2*n-1,8)))

    def test_difference_negative_at_exit(self):
        for n in range(1,5):
            th=F(2*n-1,8)
            self.assertEqual(th-F(n,4),F(-1,8))
            if n>1:self.assertEqual(th-F(n-1,4),F(1,8))

    def test_negative_number_sign(self):
        self.assertEqual(f'{oracle.exact_fp_word(F(-1,8)):014o}','30000000000076')

    def test_unchanged_constants(self):
        self.assertEqual(oracle.image_words()[0o101],oracle.exact_fp_word(F(1,2)))
        self.assertEqual(oracle.image_words()[0o104],oracle.exact_fp_word(F(1,4)))

    def test_sentinel_is_not_automatically_executed(self):
        self.assertEqual(oracle.CODE[6][0],0o33)
        self.assertEqual(oracle.expected_json()['end_pointer'],'0306')

if __name__=='__main__':unittest.main()
