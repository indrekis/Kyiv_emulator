#!/usr/bin/env python3
"""H113: offline evidence-based integration gate; no production emulator modifications."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
BUNDLE = HERE / 'bundle' / 'KYIV_H112_H1_WINDOWS_HTML_NEWLINE_FIX_V1.zip'
MANIFEST = HERE / 'MANIFEST_H113.json'
PASS = 'PASS_H113_PORTABLE_RK4_OFFLINE_CI_RELEASE_REVIEW'
HOLD = 'HOLD_H113_PORTABLE_RK4_OFFLINE_CI_RELEASE_REVIEW'

def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def verify_bundle() -> dict:
    meta = json.loads(MANIFEST.read_bytes())
    assert meta['schema'] == 'KYIV_H113_BUNDLE_PIN_V1'
    assert BUNDLE.stat().st_size == meta['bundle_bytes'], 'H112_H1_SIZE_MISMATCH'
    assert digest(BUNDLE) == meta['bundle_sha256'], 'H112_H1_SHA256_MISMATCH'
    with zipfile.ZipFile(BUNDLE) as z:
        names = z.namelist()
        assert len(names) == len(set(names)), 'DUPLICATE_ARCHIVE_MEMBERS'
        for name in names:
            p = PurePosixPath(name)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in name, 'UNSAFE_ARCHIVE_MEMBER'
            assert not (z.getinfo(name).external_attr >> 16 & 0o170000 == 0o120000), 'SYMLINK_MEMBER'
        assert z.testzip() is None, 'BUNDLE_CRC_FAILURE'
        assert 'PACKAGE_SHA256SUMS.txt' in names
    return meta

def run_command(args: list[str], cwd: Path, out: Path, label: str) -> None:
    proc = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
    log = (f'$ python {" ".join(args)}\nRETURN_CODE={proc.returncode}\n'
           f'--- STDOUT ---\n{proc.stdout}\n--- STDERR ---\n{proc.stderr}\n')
    (out / (label + '.txt')).write_bytes(log.encode('utf-8'))
    print('H113_STEP=' + label + (':PASS' if proc.returncode == 0 else ':HOLD'), flush=True)
    if proc.returncode:
        raise RuntimeError(f'{label}: EXIT_{proc.returncode}; see {label}.txt')

def pack_out(out: Path):
    dest = out.with_suffix('.zip')
    assert not dest.exists(), f'OUTPUT_ZIP_EXISTS: {dest}'
    partial = out.with_suffix('.tmpzip')
    try:
        with zipfile.ZipFile(partial, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in sorted(out.rglob('*')):
                if p.is_file(): z.write(p, p.relative_to(out).as_posix())
        with zipfile.ZipFile(partial) as z:
            assert z.testzip() is None, 'EVIDENCE_ZIP_CRC'
        partial.replace(dest)
    finally:
        partial.unlink(missing_ok=True)
    print('H113_EVIDENCE_ZIP=' + str(dest), flush=True)

def offline(out: Path) -> dict:
    meta = verify_bundle()
    with tempfile.TemporaryDirectory(prefix='kyiv_h113_') as temp:
        source = Path(temp)
        with zipfile.ZipFile(BUNDLE) as z: z.extractall(source)
        run_command(['test_h112_h1.py'], source, out, 'H112_H1_5_TESTS')
        run_command(['test_h112.py'], source, out, 'H112_13_TESTS')
        run_command(['h112_audit.py', '--out', str(out/'H112_AUDIT')], source, out, 'H112_AUDIT')
        run_command(['h112_report.py', '--out', str(out/'DEMO_H112.html')], source, out, 'H112_HTML')
        a = (out/'DEMO_H112.html').read_bytes()
        b = (source/'DEMO_H112.html').read_bytes()
        assert a == b, 'H112_HTML_NONEXACT_BYTES'
        assert hashlib.sha256(a).hexdigest() == meta['html_sha256'], 'H112_HTML_SHA256_MISMATCH'
        result = json.loads((out/'H112_AUDIT'/'RESULT_H112.json').read_bytes())
        assert result['status'] == 'PASS_H112_OFFLINE_EVIDENCE_AUDIT', 'BAD_AUDIT_STATUS'
        assert result['native_scenarios_reexamined'] == 29, 'BAD_SCENARIO_COUNT'
        assert result['trajectory_points_reexamined'] == 3408, 'BAD_POINT_COUNT'
    return {'status':PASS, 'type':'OFFLINE_EVIDENCE_REAUDIT_NOT_NEW_NATIVE_EXECUTION',
            'h112_h1_sha256':meta['bundle_sha256'], 'h112_html_sha256':meta['html_sha256'],
            'scenarios':29, 'trajectory_points':3408, 'html_bytes':len(a),
            'scope':'reconstructed functional n=2 RK4; not historic ROM or authentic printer'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True,help='new evidence directory (must not exist)')
    args=parser.parse_args()
    out = args.out.resolve()
    if out.exists() or out.with_suffix('.zip').exists() or out.with_suffix('.tmpzip').exists():
        parser.error('OUT_ALREADY_EXISTS; choose new --out to preserve previous evidence')
    out.mkdir(parents=True)
    code=0
    try:
        result=offline(out)
    except Exception as exc:
        code=1
        result={'status':HOLD,'error':repr(exc),'type':'OFFLINE_EVIDENCE_REAUDIT_NOT_NEW_NATIVE_EXECUTION'}
    (out/'RESULT_H113.json').write_bytes((json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
    print('H113_STATUS='+result['status'],flush=True)
    try: pack_out(out)
    except Exception as exc:
        print('H113_PACKAGING_ERROR='+repr(exc),file=sys.stderr)
        code=1
    sys.exit(code)

if __name__ == '__main__': main()
