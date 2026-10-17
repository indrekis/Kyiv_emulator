#!/usr/bin/env python3
"""ISA-06 D8-H6 document-integrity check, NOT a historical sign/CPU oracle.

This validates scoped after-reset claims and preserves downstream uncertainty.
Use --verify-source PATH to authenticate original user-supplied spread images.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
PFX = 'ISA_06_D8_H6_'


def read_tsv(name, columns):
    file = DOCS / (PFX + name + '.tsv')
    with file.open(encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t')
        assert reader.fieldnames == columns, f'{file.name}: wrong header {reader.fieldnames!r}'
        data = list(reader)
    assert data, f'{file.name}: empty'
    for i, row in enumerate(data, 2):
        assert None not in row, f'{file.name}:{i}: overflow columns'
        assert all(v is not None and v.strip() for v in row.values()), f'{file.name}:{i}: empty field'
    return data


def assert_unique(data, key, table):
    vals = [item[key] for item in data]
    assert len(set(vals)) == len(vals), f'{table}: duplicate {key}'


def check(source_dir=None, show=False):
    evidence = read_tsv('RESET_AND_GATE_EVIDENCE',
                        ['id', 'printed_page', 'location', 'basis', 'claim', 'grade', 'boundary'])
    phases = read_tsv('RESET_PHASE_TRACE',
                      ['phase_id', 'event', 'relative_order', 'supported_state_or_event',
                       'grade', 'source', 'non_conclusion'])
    gates = read_tsv('F71_GATE_LABEL_REVIEW',
                     ['node_id', 'visible_pulse_or_input', 'visible_group_or_control',
                      'evidence_scope', 'conclusion', 'unresolved'])
    cases = read_tsv('OPCODE01_GATE_BOUNDARIES',
                     ['case_id', 'sign1', 'sign2', 'I1_selected', 'I2_selected',
                      'minus_Ch1', 'minus_Ch2', 'TZn1Sm_after_reset', 'TZn2Sm_after_reset',
                      'C16_admitted', 'C17_admitted', 'C18_admitted',
                      'TZn2Sm_at_IVA3', 'historical_01_zero_sign'])
    opendelta = read_tsv('OPEN_DELTA',
                         ['parent_id', 'topic', 'disposition', 'new_evidence_or_limit', 'next_requirement'])
    manifest = read_tsv('SOURCE_MANIFEST', ['name', 'sha256', 'bytes', 'scope'])

    for data, key, name in [(evidence,'id','evidence'),(phases,'phase_id','phases'),
                            (gates,'node_id','gates'),(cases,'case_id','cases'),
                            (opendelta,'parent_id','open'),(manifest,'name','manifest')]:
        assert_unique(data,key,name)
    assert len(evidence) == 20
    assert len(phases) == 8
    assert len(gates) == 6
    assert len(cases) == 6
    assert len(opendelta) == 12
    assert len(manifest) == 4
    assert [p['phase_id'] for p in phases] == [f'P{n:02}' for n in range(8)]
    assert all(x['historical_01_zero_sign'] == 'OPEN' and x['TZn2Sm_at_IVA3'] == 'OPEN' for x in cases)
    for x in cases:
        assert x['TZn1Sm_after_reset'] == x['TZn2Sm_after_reset'] == '0'
        assert x['C16_admitted'] == x['C17_admitted'] == x['C18_admitted'] == 'OPEN'
        assert x['I1_selected'] == ('minus' if x['sign1'] == '-' else 'plus')
        assert x['I2_selected'] == ('minus' if x['sign2'] == '-' else 'plus')
        assert x['minus_Ch1'] == ('1' if x['sign1'] == '-' else '0')
        assert x['minus_Ch2'] == ('1' if x['sign2'] == '-' else '0')

    # Cross-validate upstream independently with already committed H5, not merely H6's new data.
    h5file = DOCS / 'ISA_06_D8_H5_OPCODE01_TRANSFER_MATRIX.tsv'
    with h5file.open(encoding='utf-8', newline='') as f:
        h5 = {r['case_id']:r for r in csv.DictReader(f,delimiter='\t')}
    assert set(h5) == {r['case_id'] for r in cases}
    for row in cases:
        old=h5[row['case_id']]
        for k in ('sign1','sign2','I1_selected','I2_selected','minus_Ch1','minus_Ch2'):
            assert row[k] == old[k], f'{row["case_id"]}: H5 conflict in {k}'
        assert all(old[k]=='OPEN' for k in ('g16','g18','C17','trigger_sign'))

    ga={r['node_id']:r for r in gates}
    assert set(ga) == {'F71.C16','F71.C17','F71.C18','F71.P_CORR','F71.TZ1SM','F71.TZ2SM'}
    assert ga['F71.C16']['visible_pulse_or_input'] == '-Ч1'
    assert ga['F71.C18']['visible_pulse_or_input'] == '-Ч2'
    assert ga['F71.C17']['visible_pulse_or_input'] == 'И1'
    assert all('U0' in ga[k]['visible_pulse_or_input'] or 'У0' in ga[k]['visible_pulse_or_input']
               for k in ('F71.TZ1SM','F71.TZ2SM'))
    # The exact published aliases are purposefully only label transcriptions,
    # not executable operation-control truth values.
    assert all(ga[k]['evidence_scope'] == 'label-only'
               for k in ('F71.C16','F71.C17','F71.C18'))
    assert 'after' in phases[1]['relative_order'] or 'reset' in phases[1]['relative_order']
    assert 'TZn1Sm=0' in phases[1]['supported_state_or_event']
    assert 'TZn2Sm=0' in phases[1]['supported_state_or_event']
    assert evidence[0]['id'] == 'H6-001'
    assert any(x['id']=='H6-006' and x['grade']=='DERIVED_SCOPED' for x in evidence)
    assert any(x['id']=='H6-018' and x['grade']=='OPEN' for x in evidence)
    assert all(row['disposition'] in {'OPEN','PARTIALLY_CLOSED'} for row in opendelta)
    assert next(x for x in opendelta if x['parent_id']=='H4-O07')['disposition']=='PARTIALLY_CLOSED'
    assert all(x['parent_id'] in {f'H4-O{i:02}' for i in range(1,13)} for x in opendelta)

    # Reject any accidental resurrection of H2's retracted E022 edge.
    override_path=DOCS/'ISA_06_D8_H2_EDGE_OVERRIDES.tsv'
    with override_path.open(encoding='utf-8',newline='') as f:
        overrides=list(csv.DictReader(f,delimiter='\t'))
    assert any(r['h1_edge_id']=='E022' and r['disposition']=='RETRACT_AS_DIRECTED_EDGE'
               for r in overrides), 'H2 E022 retraction missing'
    assert len({r['name'] for r in manifest})==4
    assert set(r['name'] for r in manifest)=={'kiev0051.png','kiev0052.png','kiev0072.png','kiev0073.png'}
    for r in manifest:
        assert len(r['sha256'])==64 and all(ch in '0123456789abcdef' for ch in r['sha256'])
        assert int(r['bytes'])>100000
        if source_dir is not None:
            file=source_dir / r['name']
            assert file.is_file(), f'missing scan: {file}'
            assert file.stat().st_size == int(r['bytes']), f'scan bytes mismatch {file}'
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            assert digest == r['sha256'], f'scan sha256 mismatch {file}'
    print('ISA-06 D8-H6: RESET-CONDITION QUALIFIED ONLY; F71 opcode-01 gate admission and signed-zero oracle OPEN')
    print(f'RESET-CHECK PASS evidence={len(evidence)} phases={len(phases)} gates={len(gates)} '
          f'cases={len(cases)} open_delta={len(opendelta)} sources={len(manifest)} '
          'initial_TZn1Sm=0 initial_TZn2Sm=0 H2_E022=RETRACTED')
    if source_dir is not None:
        print(f'SOURCE-HASH PASS scans={len(manifest)}')
    if show:
        print('case                            I1       I2       after_reset   C16 C17 C18 at_IVA3 historical_sign')
        for r in cases:
            print(f'{r["case_id"]:<31} {r["I1_selected"]:<8} {r["I2_selected"]:<8} '
                  f'({r["TZn1Sm_after_reset"]},{r["TZn2Sm_after_reset"]})           '
                  f'{r["C16_admitted"]:4} {r["C17_admitted"]:4} {r["C18_admitted"]:4} '
                  f'{r["TZn2Sm_at_IVA3"]:7} {r["historical_01_zero_sign"]}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='validate only (never historical sign proof)')
    parser.add_argument('--show-boundaries',action='store_true')
    parser.add_argument('--verify-source',type=Path,metavar='SCAN_DIR')
    args=parser.parse_args()
    try:
        check(args.verify_source,args.show_boundaries)
    except (AssertionError, KeyError, FileNotFoundError, ValueError) as exc:
        print('RESET-CHECK FAIL:',exc,file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
