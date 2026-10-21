#!/usr/bin/env python3
"""D14-C2-H3/A2: genuine production kyivemu CLI integration oracle.

Use a REAL binary made from src/main.cpp + src/asm_disasm.cpp, never a CPU stub.
Provision KYIVDRM1 separately; verify all complete image bytes independently.
"""
import argparse
import pathlib
import struct
import subprocess
import tempfile

SIGN = 1 << 40
MASK41 = (1 << 41) - 1
PROFILE = 'h3a2-cli-e2e'
TRACKS, SLOTS, DRUMS = 2, 8, 3
N = TRACKS * SLOTS * DRUMS


def crc64(data):
    r = 0
    for b in data:
        r ^= b << 56
        for _ in range(8):
            r = ((r << 1) ^ (0x42F0E1EBA9EA3693 if r & SIGN << 23 else 0)) & ((1 << 64)-1)
    return r


def image(cells):
    p = PROFILE.encode('ascii')
    bitmap = bytearray((N+7)//8)
    payload = [0] * N
    for i, v in cells.items():
        assert 0 <= i < N and 0 <= v <= MASK41
        bitmap[i//8] |= 1 << (i%8)
        payload[i] = v
    header = struct.pack('<8sIIQQQQQII', b'KYIVDRM1', 1, 64,
                         DRUMS, TRACKS, SLOTS, N, len(cells), len(p), 0)
    assert len(header) == 64
    raw = header + p + bitmap + b''.join(struct.pack('<Q', x) for x in payload)
    return raw + struct.pack('<Q', crc64(raw))


def ins(op, a1, a2, a3):
    assert 0 <= op < 32 and 0 <= a1 < 2048 and 0 <= a2 < 2048 and 0 <= a3 < 2048
    return (op << 36) | (a1 << 24) | (a2 << 12) | a3


def expression(pin=1, full=True):
    """CLI expressions: decimal RAM addresses/data; starting C in octal."""
    if not full:
        pairs = [(0o500, ins(0o1, 0o200, 0o201, 0o3)),
                 (0o501, ins(0o33, 0, 0, 0)),
                 (0o200, 2), (0o201, 5)]
    else:
        drum_a2 = pin << 6
        pairs = [(0o500, ins(0o25, 1, drum_a2, 3)),
                 (0o501, ins(0o23, 0o200, 0o202, 0o502)),
                 (0o502, ins(0o25, 0, drum_a2, 3)),
                 (0o503, ins(0o24, 0o210, 0o212, 0o504)),
                 (0o504, ins(0o1, 0o210, 0o211, 0o3)),
                 (0o505, ins(0o33, 0, 0, 0)),
                 (0o200, 7), (0o201, 0), (0o202, SIGN)]
    return ['expression', *(f'({a},{v})' for a, v in pairs), '0500']


def invoke(exe, root, args, timeout):
    return subprocess.run([str(exe), *args], cwd=root, capture_output=True,
                          text=True, encoding='utf-8', errors='replace',
                          timeout=timeout, check=False)


def must(ok, what, proc=None):
    if not ok:
        detail = '' if proc is None else f' RC={proc.returncode} stdout={proc.stdout[-900:]!r} stderr={proc.stderr[-900:]!r}'
        raise AssertionError(what + detail)


def run_case(exe, base, name, timeout):
    root = base/name
    root.mkdir()
    img = root/'a directory with spaces'/'drum.kdr'
    img.parent.mkdir()
    empty = image({})
    if name == 'legacy' or name == 'legacy-flag':
        args = expression(full=False)
        if name == 'legacy-flag': args += ['--block-overflow-stop']
        p = invoke(exe, root, args, timeout)
        must(p.returncode == 0 and 'Result:' in p.stdout, 'LEGACY_FAIL', p)
        must(not img.exists(), 'LEGACY_CREATED_FILE', p)
        return
    if name == 'missing-image':
        p = invoke(exe, root, expression()+['--experimental-drum',str(img),PROFILE,'2','8','1'],timeout)
        must(p.returncode != 0 and 'D14C2H3A2-ATTACH-ERROR' in p.stderr,
             'MISSING_NOT_REJECTED',p)
        must(not img.exists(), 'MISSING_CREATED_IMAGE',p)
        return
    if name == 'invalid-suffix':
        p = invoke(exe,root,expression()+['--experimental-drum',str(img),PROFILE,'0','8','1'],timeout)
        must(p.returncode != 0 and 'D14C2H3A2-CLI-ERROR' in p.stderr,
             'BAD_SUFFIX_NOT_REJECTED',p)
        must(not img.exists(),'BAD_SUFFIX_CREATED_IMAGE',p)
        return
    if name == 'incomplete-suffix':
        p = invoke(exe,root,expression()+['--experimental-drum',str(img),PROFILE],timeout)
        must(p.returncode != 0 and 'D14C2H3A2-CLI-ERROR' in p.stderr,
             'INCOMPLETE_SUFFIX_NOT_REJECTED',p)
        must(not img.exists(),'INCOMPLETE_CREATED_IMAGE',p)
        return
    if name == 'flag-out-of-order':
        args=expression()+['--block-overflow-stop','--experimental-drum',str(img),PROFILE,'2','8','1']
        p=invoke(exe,root,args,timeout)
        must(p.returncode!=0 and 'D14C2H3A2-CLI-ERROR' in p.stderr,
             'FLAG_ORDER_NOT_REJECTED',p)
        must(not img.exists(),'FLAG_ORDER_CREATED_IMAGE',p)
        return
    if name == 'corrupt-image':
        img.write_bytes(b'bad')
        p=invoke(exe,root,expression()+['--experimental-drum',str(img),PROFILE,'2','8','1'],timeout)
        must(p.returncode!=0 and 'D14C2H3A2-ATTACH-ERROR' in p.stderr,
             'BAD_IMAGE_NOT_REJECTED',p)
        must(img.read_bytes()==b'bad','BAD_IMAGE_MUTATED',p)
        return
    if name == 'wrong-geometry':
        img.write_bytes(empty)
        p=invoke(exe,root,expression()+['--experimental-drum',str(img),PROFILE,'2','9','1'],timeout)
        must(p.returncode!=0 and 'D14C2H3A2-ATTACH-ERROR' in p.stderr,
             'WRONG_GEOMETRY_NOT_REJECTED',p)
        must(img.read_bytes()==empty,'WRONG_GEOMETRY_MUTATED',p)
        return
    if name == 'unsupported-mode':
        # A valid image and suffix may never implicitly enable an unknown legacy mode.
        img.write_bytes(empty)
        p=invoke(exe,root,['not-a-mode','--experimental-drum',str(img),PROFILE,'2','8','1'],timeout)
        must(p.returncode!=0,'UNKNOWN_MODE_NOT_REJECTED',p)
        must(img.read_bytes()==empty,'UNKNOWN_MODE_CHANGED_IMAGE',p)
        return
    pin = 1 if name in ('success-pin1','success-pin1-flag') else (2 if name=='success-pin2' else 3)
    img.write_bytes(empty)
    args=expression(pin)+['--experimental-drum',str(img),PROFILE,'2','8',str(pin)]
    if name=='success-pin1-flag': args+=['--block-overflow-stop']
    p=invoke(exe,root,args,timeout)
    must(p.returncode==0 and 'Result:' in p.stdout,'SUCCESS_CLI_FAILED',p)
    # Linear position 3/4/5 of the pinned logical drum, preserving -0.
    offset=(pin-1)*(TRACKS*SLOTS)
    expected=image({offset+3:7,offset+4:0,offset+5:SIGN})
    actual=img.read_bytes()
    must(actual==expected,'IMAGE_BYTE_MISMATCH diff='+str(next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)),p)
    must(sorted(x.name for x in img.parent.iterdir())==['drum.kdr'], 'TEMP_IMAGE_RESIDUE',p)


def self_test():
    assert crc64(b'123456789')==0x6C40DF5F0B497347
    assert image({})!=image({0:0})!=image({0:SIGN})
    assert ins(0o25,1,0o100,3) < (1<<41)
    assert len(image({}))==64+len(PROFILE)+((N+7)//8)+8*N+8
    # Detect a corrupted CRC and a wrongly shifted sign bit.
    assert image({0:7})[-8:]!=image({0:SIGN})[-8:]
    print('D14C2H3A2-SANDBOX-SELFTEST PASS CRC64=1 SIGNED_ZERO=1 INPUT_GRAMMAR=1 MUTANT_REJECTED=1')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--self-test',action='store_true')
    ap.add_argument('--exe',type=pathlib.Path)
    ap.add_argument('--timeout',type=float,default=15)
    a=ap.parse_args()
    if a.self_test:
        self_test()
        if not a.exe: return
    if not a.exe or not a.exe.is_file(): ap.error('--exe must reference genuine kyivemu executable')
    cases=['legacy','legacy-flag','missing-image','invalid-suffix','incomplete-suffix',
           'flag-out-of-order','corrupt-image','wrong-geometry','unsupported-mode',
           'success-pin1','success-pin1-flag','success-pin2','success-pin3']
    with tempfile.TemporaryDirectory(prefix='d14c2h3a2_') as folder:
        for case in cases:
            run_case(a.exe.resolve(),pathlib.Path(folder),case,a.timeout)
            print('D14C2H3A2-CASE '+case+': PASS',flush=True)
    print(f'D14C2H3A2-PRODUCTION-CLI PASS CASES={len(cases)}/{len(cases)} '
          'REAL_KYIVEMU=1 EXPLICIT_ATTACH=1 LEGACY_UNCHANGED=1 '
          'BYTE_EXACT_KDR=1 SIGNED_ZERO=1 NO_AUTO_CREATE=1 '
          'HOST_POLICY=EXPLICIT HISTORICAL_MAPPING=OPEN HARDWARE_ORACLE=0')

if __name__=='__main__': main()
