#!/usr/bin/env python3
"""D10-G4: source-qualified manual signal matrix + independent arithmetic checks.

Neither the manually read rows of DPS64 Table 5 nor these mathematical models
constitute an electrical timing trace or an oracle for opcode 20 low bits.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import json

# Manually inspected DPS64 pp.124-125, zero-based PDF spread 62.
# Signal spellings are descriptive; not a recovered netlist or control encoding.
# Each value '—' is a dash in the table, not a disabled physical gate.
SIGNALS = (
    ('ПЧ1', '—', '—', 'CLEAR_PRINT', 'p.124, table 5'),
    ('ПЧ2', '—', '—', 'CLEAR_PRINT', 'p.124, table 5'),
    ('У<0>Р1', 'ИВА1', 'ИВА1', 'CLEAR_PRINT', 'p.124, table 5'),
    ('У<0>Р2', 'ИВА1; НИ1∧П_s', 'ИВА1', 'READING_QUALIFIED', 'p.124, table 5'),
    ('У<0>См', 'ИВА1', 'same-as-20 (ditto)', 'CLEAR_PRINT', 'p.124, table 5'),
    ('+Ч2,+Ч3', 'ИКЛ', 'ИКЛ', 'CLEAR_PRINT', 'p.125, table 5'),
    ('У<1>Р1', 'ИК', 'ИК', 'CLEAR_PRINT', 'p.125, table 5'),
    ('УЭ', 'ИК; НИ3∧П_s∧ИК', 'ИК', 'READING_QUALIFIED', 'p.125, table 5'),
    ('ИКОп', 'ИСдв∧<1>Т40Р1', 'same-as-20 (ditto)', 'READING_QUALIFIED', 'p.125, table 5'),
)
TSV_FIELDS = ('signal','opcode20_numeric','opcode21_commands','confidence','source')


def signal_tsv():
    rows=['\t'.join(TSV_FIELDS)]
    for row in SIGNALS:
        rows.append('\t'.join(row))
    return '\n'.join(rows)+'\n'


def digits_ok(token):
    return (isinstance(token,str) and len(token)==10 and token.isascii() and
            all(c in '0123456789' for c in token))


def bcd_total(token):
    if not digits_ok(token):
        raise ValueError('ten ASCII digits required')
    terms = []
    for s,char in enumerate(token,1):
        digit=int(char)
        for bit in (8,4,2,1):
            terms.append(Fraction(bit, 10**s) if (digit&bit) else Fraction(0))
    assert len(terms)==40
    return sum(terms, Fraction(0))


def shifted_model(token, precision=45, terminal_shift=True, rounding='nearest'):
    """Counterfactual fixed-point model: no physical gate/timing assertion."""
    if not digits_ok(token) or not isinstance(precision,int) or not 40<=precision<=88:
        raise ValueError('bad input/precision')
    if rounding not in ('nearest','floor'):
        raise ValueError('bad rounding')
    acc=0; shifts=0; adds=0
    for s,char in enumerate(token,1):
        denom=10**s
        numerator=8*(1<<precision)
        reg=(numerator+(denom//2 if rounding=='nearest' else 0))//denom
        for idx,bit in enumerate((8,4,2,1)):
            if int(char)&bit:
                acc+=reg; adds+=1
            if idx!=3 or terminal_shift:
                reg >>= 1; shifts+=1
    magnitude=acc>>(precision-40)
    return {'output':magnitude, 'adds':adds, 'shifts':shifts,
            'delta_ulps':magnitude-(int(token)*(1<<40)//10**10)}


def diagnostic(token):
    if not digits_ok(token): raise ValueError('ten ASCII digits required')
    truth=Fraction(int(token),10**10)
    assert bcd_total(token)==truth
    a=shifted_model(token,45,False,'nearest')
    b=shifted_model(token,45,True,'nearest')
    assert a['output']==b['output']
    return {'digits':token,'source_fraction':str(truth),
            'ideal_truncated_40':int(truth*(1<<40)),
            'P45_nearest_shift_delta_ulps':a['delta_ulps'],
            'shift30_equals_shift40':a['output']==b['output'],
            'pulse_count_not_determined':True,
            'historical_io20_word_oracle':False}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--digits',default='6250000000')
    ap.add_argument('--signals',action='store_true')
    args=ap.parse_args()
    try: obj=diagnostic(args.digits)
    except ValueError as err: ap.error(str(err))
    print('D10G4-REFERENCE TABLE5=VISUAL_TRANSCRIPTION SOURCE_WEIGHT=EXACT '
          'E_s_SOURCE=OPEN CLOCK_TRACE=OPEN HARDWARE_ORACLE=0 CPU_MUTATION=0')
    if args.signals: obj['signals']=list(SIGNALS)
    print(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
