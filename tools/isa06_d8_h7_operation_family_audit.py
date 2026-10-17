#!/usr/bin/env python3
"""ISA-06 D8-H7: validate source attribution and admitted-unknown boundaries only.

No model of historical hardware or CPU is built here.
"""
import argparse
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs'
PREFIX = 'ISA_06_D8_H7_'

def read(name):
    with (DOC / (PREFIX + name + '.tsv')).open(newline='', encoding='utf-8') as fp:
        return list(csv.DictReader(fp, delimiter='\t'))

def verify(cond, message):
    if not cond:
        raise AssertionError(message)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--show-gates', action='store_true')
    ap.add_argument('--verify-source', type=Path, default=None)
    args = ap.parse_args()
    evidence = read('OPERATION_FAMILY_EVIDENCE')
    gates = read('F71_GATE_FAMILY')
    cases = read('OPCODE01_BOUNDARIES')
    delta = read('OPEN_DELTA')
    scans = read('SOURCE_MANIFEST')
    verify(len(evidence) == 20 and len({r['id'] for r in evidence}) == len(evidence), 'bad evidence IDs')
    verify(len(gates) == 3 and {r['node_id'] for r in gates} == {'F71.C16', 'F71.C17', 'F71.C18'}, 'bad gate set')
    verify(len(cases) == 6 and len({r['case_id'] for r in cases}) == 6, 'bad six-case matrix')
    verify(len(delta) == 12 and {r['parent_id'] for r in delta} == {f'H4-O{n:02d}' for n in range(1,13)}, 'bad open ledger')
    verify(len(scans) == 6 and len({r['name'] for r in scans}) == 6, 'bad source manifest')
    for r in gates:
        verify(r['opcode01_enable'] == 'OPEN' and r['accepted_event'] == 'OPEN', 'unproved gate enable')
    by = {r['node_id']:r for r in gates}
    verify(by['F71.C17']['path_evidence'] == 'DOC_LOGICAL_PATH' and 'logical addition' in by['F71.C17']['prose_family'], 'C17 logical evidence missing')
    verify(by['F71.C16']['path_evidence'] == by['F71.C18']['path_evidence'] == 'TEXT_SUPPORT_PATH', 'arithmetic path evidence missing')
    for r in cases:
        verify(r['I1_pulse'] == ('+Ч1' if r['sign1'] == '+' else '−Ч1'), 'I1 transfer mismatch')
        verify(r['I2_pulse'] == ('+Ч2' if r['sign2'] == '+' else '−Ч2'), 'I2 transfer mismatch')
        verify(r['TZn1Sm_after_reset'] == r['TZn2Sm_after_reset'] == '0', 'reset regression')
        for k in ['C16_admission','C17_admission','C18_admission','TZn2Sm_at_IVA3','historical_01_zero_sign']:
            verify(r[k] == 'OPEN', f'unjustified historical oracle: {k}')
    verify(any(r['id'] == 'H7-007' and r['status'] == 'DOC_SCOPED' for r in evidence), 'missing logical-addition explicit evidence')
    verify(any(r['id'] == 'H7-016' and r['status'] == 'TENSION_OPEN' for r in evidence), 'missing C16/18 textual/figure tension')
    verify(any(r['parent_id'] == 'H4-O03' and r['disposition'] == 'PARTIALLY_RESOLVED' for r in delta), 'C17 delta not qualified')
    overrides = DOC / 'ISA_06_D8_H2_EDGE_OVERRIDES.tsv'
    verify(overrides.exists() and 'E022' in overrides.read_text(encoding='utf-8'), 'H2 E022 override lost')
    for r in scans:
        verify(len(r['sha256']) == 64 and int(r['bytes']) > 0 and r['printed_pages'], 'bad source fingerprint')
        if args.verify_source:
            p = args.verify_source / r['name']
            verify(p.is_file(), f'missing original scan {p}')
            raw = p.read_bytes()
            verify(len(raw) == int(r['bytes']) and hashlib.sha256(raw).hexdigest() == r['sha256'], f'fingerprint mismatch {p}')
    # Validate that new case names and inherited H6 case order/transfer data agree.
    h6_path = DOC / 'ISA_06_D8_H6_OPCODE01_GATE_BOUNDARIES.tsv'
    verify(h6_path.is_file(), 'H6 case matrix missing')
    with h6_path.open(newline='',encoding='utf-8') as fp:
        h6 = {r['case_id']:r for r in csv.DictReader(fp,delimiter='\t')}
    verify(set(h6) == {r['case_id'] for r in cases}, 'H6/H7 cases differ')
    for r in cases:
        parent = h6[r['case_id']]
        verify((r['sign1'],r['sign2']) == (parent['sign1'],parent['sign2']), 'source sign regression')
        verify(parent['TZn1Sm_after_reset'] == parent['TZn2Sm_after_reset'] == '0', 'H6 reset missing')
    print('ISA-06 D8-H7: DOCUMENTED C17 LOGICAL PATH ONLY; opcode01 F71 gate admission and signed-zero sign OPEN')
    print(f'FAMILY-CHECK PASS evidence={len(evidence)} gates={len(gates)} cases={len(cases)} open_delta={len(delta)} sources={len(scans)} C17_logical_p147=DOC H2_E022=RETRACTED')
    if args.show_gates:
        for r in gates:
            print(f"{r['node_id']}: pulse={r['visible_pulse']}, family={r['prose_family']}, opcode01_enable={r['opcode01_enable']}, accepted={r['accepted_event']}")
    if args.verify_source:
        print(f'SOURCE-SHA256 PASS originals={len(scans)}')

if __name__ == '__main__':
    main()
