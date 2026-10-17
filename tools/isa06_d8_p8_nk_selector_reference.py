#!/usr/bin/env python3
"""Reference-only NK3000-3002 source selection — NOT connected to Kyiv_t.
GY62 1962 printed pp. 8, 120-121, 161. Synthetic inputs are POLICY.
"""
import argparse
import itertools
MASK=(1<<41)-1
SIGN=1<<40
SELECTABLE=(0o3000,0o3001,0o3002)


def resolve(addr, *, cabinet, panel, select_panel):
    if addr not in SELECTABLE:
        raise ValueError('Only NK3000..3002 are documented console-selectable')
    if set(cabinet)!=set(SELECTABLE) or set(panel)!=set(SELECTABLE) or set(select_panel)!=set(SELECTABLE):
        raise ValueError('Expected three independently specified address/source pairs')
    raw=panel[addr] if select_panel[addr] else cabinet[addr]
    if not isinstance(raw,int) or not 0<=raw<=MASK:
        raise ValueError('Not a complete unsigned 41-bit machine word')
    return raw


def check():
    # Distinct symbolic values, including both signed zeros; no historical panel settings implied.
    panel={0o3000:0,0o3001:SIGN,0o3002:0o12345}
    cabinet={0o3000:SIGN,0o3001:0,0o3002:MASK}
    total=0
    for bits in itertools.product((False,True),repeat=3):
        choice=dict(zip(SELECTABLE,bits))
        observed={addr:resolve(addr,cabinet=cabinet,panel=panel,select_panel=choice) for addr in SELECTABLE}
        assert observed=={a:(panel[a] if choice[a] else cabinet[a]) for a in SELECTABLE}
        assert observed[0o3000] in (0,SIGN)
        assert (observed[0o3000]&SIGN)!=0 if not choice[0o3000] else observed[0o3000]==0
        total+=1
    for invalid in (-1,1<<41):
        try: resolve(0o3001,cabinet=cabinet,panel={**panel,0o3001:invalid},select_panel={a:True for a in SELECTABLE})
        except ValueError: pass
        else: raise AssertionError('Invalid NK word not rejected')
    for bad_address in (0o3003,0o3007):
        try: resolve(bad_address,cabinet=cabinet,panel=panel,select_panel={a:True for a in SELECTABLE})
        except ValueError: pass
        else: raise AssertionError('Undocumented console selector accepted')
    print('NK-REFERENCE PASS selectable=3 configurations=8 invalid_codes=2 undocumented_selectors=2 signed_zero_distinct=1 emulator_integration=NONE')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.parse_args()
    check()
