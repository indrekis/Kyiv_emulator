#!/usr/bin/env python3
"""D10-E2 read-only baseline/source and scope auditor (run in repo root)."""
from pathlib import Path
import hashlib
import subprocess
import sys

BASE='2d0aaf48ab848b6789f85dca355d05e8c0e0f03f'
BLOBS={
  'src/main.cpp':'bc9331b178333d2e3ef32789972bc16bc70c39ea',
  'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
  'inc/kyiv_decimal_exact.h':'6a09319f3eef53236c87647d4e4d155ce9addd75',
  'inc/kyiv_decimal_ascii.h':'93e47fd34b5133964fb5a9addab3430dd25f71ae',
}
NEW={
 'inc/kyiv_decimal_input_plan.h',
 'tests/isa/isa07_d10e2_input_plan_probe.cpp',
 'tools/isa07_d10e2_input_plan_sandbox.py',
 'tools/isa07_d10e2_audit.py',
 'docs/ISA_07_D10E1_PREFLIGHT_AND_E2_PLANNER.md',
}

def git(*args):
    p=subprocess.run(['git',*args],capture_output=True,text=True)
    if p.returncode:raise RuntimeError(f'git {args}: {p.stderr.strip()}')
    return p.stdout.strip()

def main():
    root=Path(__file__).resolve().parents[1]
    if Path.cwd().resolve()!=root:
        print('D10E2-AUDIT FAIL: run at repository root');return 1
    errs=[]
    try:
        head=git('rev-parse','HEAD')
        if head!=BASE:errs.append('wrong HEAD: '+head)
        for name,expected in BLOBS.items():
            obj=git('rev-parse',f'HEAD:{name}')
            if obj!=expected:errs.append('git blob mismatch '+name)
            file_obj=git('hash-object',name)
            if file_obj!=expected:errs.append('worktree mutation '+name)
        modified=set(filter(None,git('diff','--name-only').splitlines()))
        staged=set(filter(None,git('diff','--cached','--name-only').splitlines()))
        if modified-NEW:errs.append('unrelated tracked changes '+str(sorted(modified-NEW)))
        if staged-NEW:errs.append('unrelated staged changes '+str(sorted(staged-NEW)))
        for file in NEW:
            if not (root/file).is_file():errs.append('missing new file '+file)
    except Exception as exc:
        errs.append(str(exc))
    for e in errs:print('D10E2-AUDIT FAIL:',e)
    if not errs:print('D10E2-AUDIT PASS BASELINE=2d0aaf4 BLOBS=4/4 CPU_MUTATION=0 D10C_D10D_MUTATION=0 NEW_FILES=5/5')
    return int(bool(errs))

if __name__=='__main__':sys.exit(main())
