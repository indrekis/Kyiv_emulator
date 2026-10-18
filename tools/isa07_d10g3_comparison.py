#!/usr/bin/env python3
"""Deterministic comparisons: hypothetical microstep vs ideal final truncation."""
import csv
import io
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('microsteps',Path(__file__).with_name('isa07_d10g3_microsteps.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CASES=(('zero','0000000000'),('tiny','0000000001'),
 ('one-tenth','1000000000'),('three-tenths','3000000000'),
 ('five-eighths','6250000000'),('one-quarter','2500000000'),
 ('one-half','5000000000'),('max','9999999999'),
 ('random-like','1234567890'),('reverse-like','9876543210'),
 ('high-bits','8888888888'),('low-bits','1111111111'),
 ('exact-small','0009765625'),('exact-large','9990234375'))

def comparison_tsv():
    output=io.StringIO(newline='')
    w=csv.writer(output,delimiter='\t',lineterminator='\n')
    w.writerow(['id','digits','ideal_octal','popcount',
                'P40_floor_delta','P45_floor_delta','P45_nearest_delta',
                'P48_nearest_delta','shift_pulses_30_40','literal_unscaled_ratio'])
    for label,token in CASES:
        p40=m.microstep_model(token,40,'floor')
        p45f=m.microstep_model(token,45,'floor')
        p45n=m.microstep_model(token,45,'nearest')
        p48n=m.microstep_model(token,48,'nearest')
        w.writerow([label,token,f"{p40['ideal_output']:014o}",p40['conditional_adds'],
                   p40['delta_ulps'],p45f['delta_ulps'],p45n['delta_ulps'],
                   p48n['delta_ulps'],'30_or_40','1/8_when_nonzero'])
    return output.getvalue()

if __name__=='__main__':print(comparison_tsv(),end='')
