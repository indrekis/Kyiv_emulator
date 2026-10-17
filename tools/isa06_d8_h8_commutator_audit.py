#!/usr/bin/env python3
"""ISA-06 D8-H8 documentary commutator boundary audit, not hardware simulation."""
import argparse
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs'
PREFIX = 'ISA_06_D8_H8_'

def read_tsv(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))

def read(name):
    return read_tsv(DOC / (PREFIX + name + '.tsv'))

def check(predicate, why):
    if not predicate:
        raise AssertionError(why)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--show-interfaces', action='store_true')
    parser.add_argument('--verify-source', type=Path)
    args = parser.parse_args()
    evidence, interfaces, cases, delta, sources = (
        read('CONTROL_EVIDENCE'), read('COMMUTATOR_INTERFACES'),
        read('OPCODE01_BOUNDARIES'), read('OPEN_DELTA'), read('SOURCE_MANIFEST')
    )
    check(len(evidence) == 20, 'evidence row count')
    check({x['id'] for x in evidence} == {f'H8-{i:03d}' for i in range(1, 21)}, 'evidence IDs')
    check({x['grade'] for x in evidence} <= {'DOC', 'FIGURE_LABEL', 'NEGATIVE_SCOPE'}, 'incorrect grades')
    check(len(interfaces) == 6, 'interface count')
    check({x['interface_id'] for x in interfaces} == {
        'RK.operation_bits', 'COMM.individual', 'COMM.group',
        'F71.C16', 'F71.C17', 'F71.C18'
    }, 'interface IDs')
    for x in interfaces:
        check(x['opcode01_enable'] == 'OPEN', f"unsupported hardware value: {x['interface_id']}")
    check('five' in interfaces[0]['observed_interface'], 'five-bit opcode control untraced')
    check(any(x['id'] == 'H8-005' and x['grade'] == 'DOC' and 'combined' in x['supported_claim'] for x in evidence), 'missing grouped control potentials')
    check(any(x['id'] == 'H8-018' and x['grade'] == 'NEGATIVE_SCOPE' for x in evidence), 'missing source-limited finding')
    check(len(cases) == 6, 'six-case size')
    check(len({x['case_id'] for x in cases}) == 6, 'duplicate cases')
    h7_path = DOC / 'ISA_06_D8_H7_OPCODE01_BOUNDARIES.tsv'
    check(h7_path.is_file(), 'H7 case matrix missing')
    prior = {x['case_id']: x for x in read_tsv(h7_path)}
    check(set(prior) == {x['case_id'] for x in cases}, 'changed case IDs')
    for x in cases:
        before = prior[x['case_id']]
        for k in ['sign1', 'sign2', 'I1_pulse', 'I2_pulse',
                  'TZn1Sm_after_reset', 'TZn2Sm_after_reset',
                  'C16_admission', 'C17_admission', 'C18_admission',
                  'TZn2Sm_at_IVA3', 'historical_01_zero_sign']:
            check(x[k] == before[k], f"altered historical boundary {x['case_id']}/{k}")
        check(x['decoder_interface'] == 'INDIVIDUAL_AND_GROUP_POTENTIALS_ONLY', 'wrong decoder certainty')
        check(x['TZn1Sm_after_reset'] == x['TZn2Sm_after_reset'] == '0', 'reset-state regression')
        for k in ['C16_admission', 'C17_admission', 'C18_admission',
                  'TZn2Sm_at_IVA3', 'historical_01_zero_sign']:
            check(x[k] == 'OPEN', f'unsupported sign or gate oracle: {k}')
    check(len(delta) == 12, '12 blockers are required')
    check({x['parent_id'] for x in delta} == {f'H4-O{i:02d}' for i in range(1,13)}, 'blocker IDs')
    check(any(x['parent_id'] == 'H4-O03' and x['disposition'] == 'PARTIALLY_RESOLVED' for x in delta), 'C17 qualification lost')
    override_path = DOC / 'ISA_06_D8_H2_EDGE_OVERRIDES.tsv'
    check(override_path.exists() and 'E022' in override_path.read_text(encoding='utf8'), 'E022 retraction missing')
    check(len(sources) == 7 and len({x['name'] for x in sources}) == 7, 'scan count')
    for x in sources:
        check(len(x['sha256']) == 64 and int(x['bytes']) > 0, 'bad scan hash')
        if args.verify_source is not None:
            path = args.verify_source / x['name']
            check(path.is_file(), f'missing original scan: {path}')
            data = path.read_bytes()
            check(len(data) == int(x['bytes']) and hashlib.sha256(data).hexdigest() == x['sha256'], f'altered scan: {path}')
    # Note: no truth-table outputs are generated. The only check is ledger and inherited-boundary consistency.
    print('ISA-06 D8-H8: OPERATION COMMUTATOR ARCHITECTURE QUALIFIED; F71 ELECTRICAL DECODER MAP AND SIGNED-ZERO ORACLE OPEN')
    print(f'COMMUTATOR-CHECK PASS evidence={len(evidence)} interfaces={len(interfaces)} cases={len(cases)} open_delta={len(delta)} sources={len(sources)} five_opcode_triggers=DOC individual_and_group_potentials=DOC H2_E022=RETRACTED')
    if args.show_interfaces:
        for x in interfaces:
            print(f"{x['interface_id']}: source={x['printed_page']} known={x['known']} missing={x['missing_link']} opcode01_enable={x['opcode01_enable']}")
    if args.verify_source is not None:
        print(f'SOURCE-SHA256 PASS originals={len(sources)}')

if __name__ == '__main__':
    main()
