#!/usr/bin/env python3
"""Read-only exact-source audit for P2; compares FULL files to pure pinned edits."""
import argparse
import hashlib
import importlib.util
import pathlib
import subprocess

BASE='eeef38e8ceccc17effb0f9aa4b09bd10ecf2f8c4'
PINS={
 'inc/kyiv.h':'1b8b87a5539af31dc773db7a9633b24e971febd5',
 'src/main.cpp':'145cbf8725405b52c12c3c75fa8f3141f2671dc1',
 'inc/kyiv_drum_transaction_v1.h':'1aab83a4735280df0cf4331191c5521dcc5ddcb4',
 'inc/kyiv_drum_host_address_v1.h':'74b75b9c4fd86d73b43eb108bbdce312dc9619d3',
 'inc/kyiv_drum_logical_media.h':'910911f7181bfb455e334b1f66fd00ee94ef1e97',
 'inc/kyiv_drum_group_transfer.h':'91be71be4abc45f8dfb7ca771dd0122c7e5e7a7b',
 'inc/kyiv_drum_persistence.h':'6827b4636405a5407c87055a4f35b575e71211c3',
 'inc/kyiv_drum_prepare_decode.h':'3706e2a4e9c1a5afe6bf584658d62b59eb0f6e5b',
}
TRACKED={'inc/kyiv.h','src/main.cpp'}
NEW={'docs/ISA_07_D14C2H2_P2_DECISION_LEDGER.tsv',
     'docs/ISA_07_D14C2H2_P2_REAL_CPU_INTEGRATION.md',
     'tests/isa/isa07_d14c2h2p2_cpu_probe.cpp',
     'tools/isa07_d14c2h2p2_audit.py',
     'tools/isa07_d14c2h2p2_cpu_sandbox.py'}
CONTENT_SHA={
 'docs/ISA_07_D14C2H2_P2_DECISION_LEDGER.tsv': '037f69f818df781858752dad870123f13a6e4a26055af7ff02a66a8b941051ca',
 'docs/ISA_07_D14C2H2_P2_REAL_CPU_INTEGRATION.md': '0b702977d0452206ffee3f0e1d6cc80372f4c4c23b7ab0ba3890606b1848b094',
 'tests/isa/isa07_d14c2h2p2_cpu_probe.cpp': 'ff0b75ea02de342d70212f1e3e7aec7c2f16f2fb17cacfa28b0611dfbd45ac8a',
 'tools/isa07_d14c2h2p2_cpu_sandbox.py': '9c86bea3e70000622b21142a2d13fa566abcd807f35bc42776d19847753b7122',
}

def run(*args):
    return subprocess.check_output(args,stderr=subprocess.STDOUT).decode('utf8').strip()


def normalize(data):
    if b'\r' in data.replace(b'\r\n',b''): raise RuntimeError('BARE_CR_REJECTED')
    return data.replace(b'\r\n',b'\n')


def sha(data): return hashlib.sha256(data).hexdigest()


def get_transform(package):
    name=package/'apply_d14c2h2p2.py'
    if not name.is_file():raise RuntimeError('PACKAGE_APPLIER_MISSING')
    spec=importlib.util.spec_from_file_location('d14c2h2p2_apply',name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(root,package):
    if run('git','rev-parse','HEAD')!=BASE:raise RuntimeError('BASELINE_MISMATCH')
    if run('git','diff','--cached','--name-only'):raise RuntimeError('STAGED_MUTATION')
    if set(run('git','diff','--name-only').splitlines())!=TRACKED:
        raise RuntimeError('TRACKED_SCOPE_VIOLATION')
    actual_new=set(x for x in run('git','ls-files','--others','--exclude-standard').splitlines() if x)
    if actual_new!=NEW:raise RuntimeError('UNTRACKED_SCOPE_VIOLATION '+str(actual_new^NEW))
    for path, expected in PINS.items():
        if run('git','rev-parse','HEAD:'+path)!=expected:
            raise RuntimeError('PIN_ERROR '+path)
        if path not in TRACKED and run('git','diff','--name-only','--',path):
            raise RuntimeError('DEPENDENCY_MUTATED '+path)
    applier=get_transform(package)
    for path in TRACKED:
        baseline=subprocess.check_output(['git','show','HEAD:'+path])
        expected=applier.TRANSFORMS[path](normalize(baseline).decode('utf8')).encode('utf8')
        actual=normalize((root/path).read_bytes())
        if actual!=expected:raise RuntimeError('TRACKED_CONTENT_MISMATCH '+path)
    for path in NEW:
        if not (root/path).is_file():raise RuntimeError('MISSING '+path)
        if b'\r' in (root/path).read_bytes().replace(b'\r\n',b''):
            raise RuntimeError('BARE_CR '+path)
    for path,digest in CONTENT_SHA.items():
        if sha(normalize((root/path).read_bytes()))!=digest:
            raise RuntimeError('CONTENT_SHA '+path)
    if run('git','diff','--check'):raise RuntimeError('WHITESPACE')
    print('D14C2H2P2-AUDIT PASS BASELINE=eeef38e PINS=8/8 '
          'TRACKED=2/2 NEW_FILES=5/5 CONTENT_SHA=4/4 '
          'SOURCE_MATCH_EXACT=2/2 LEGACY_UNMODIFIED=1 '
          'CPU_MUTATION=EXPLICIT REAL_CPU_GATE=PENDING '
          'TRACK_MAPPING=OPEN HARDWARE_ORACLE=0')


def self_test(package):
    assert sha(b'mutate')!=sha(b'baseline')
    try:normalize(b'a\rb')
    except RuntimeError:pass
    else:raise RuntimeError('BARE_CR_ACCEPTED')
    assert normalize(b'a\r\nb\r\n')==b'a\nb\n'
    module=get_transform(package)
    assert module.BASE==BASE and set(module.TRANSFORMS)==TRACKED
    assert set(module.NEW)==NEW
    print('D14C2H2P2-AUDIT-SELFTEST PASS SCOPE=2+5 PINS=8/8 '
          'BARE_CR_REJECTED=1 EOL=2/2 PACKAGE=1')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--package',required=True)
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    try:
        package=pathlib.Path(a.package).resolve()
        if a.self_test:self_test(package)
        else:audit(pathlib.Path.cwd(),package)
    except (RuntimeError,OSError,subprocess.CalledProcessError,AssertionError) as e:
        print('D14C2H2P2-AUDIT FAIL '+str(e))
        raise SystemExit(1)
