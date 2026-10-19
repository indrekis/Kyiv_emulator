#!/usr/bin/env python3
"""D13-B: genuine CPU functional regression, preserving archived old policy tests."""
from __future__ import annotations
import contextlib
import importlib.util
import io
import re
import subprocess
import sys
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[1]
BASE='506cfec97bfbedc6da6e9a0717ca4eb525edb067'

def require(ok,reason):
    if not ok:raise RuntimeError(reason)

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    require(spec and spec.loader,'MISSING_MODULE '+str(path))
    obj=importlib.util.module_from_spec(spec)
    # @dataclass resolves its defining module via sys.modules during import.
    # module_from_spec() alone does not register the module.
    require(name not in sys.modules,'MODULE_NAME_COLLISION '+name)
    sys.modules[name]=obj
    try:
        spec.loader.exec_module(obj)
    except BaseException:
        sys.modules.pop(name,None)
        raise
    return obj

def run(args,timeout=180):
    proc=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,
                        encoding='utf-8',errors='replace',timeout=timeout)
    require(proc.returncode==0,'RUN_FAILED '+repr(args)+' '+(proc.stdout+proc.stderr)[-1400:])
    return proc.stdout+'\n'+proc.stderr

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--timeout',type=float,default=20)
    p.add_argument('--long-timeout',type=int,default=900)
    a=p.parse_args()
    require(5<=a.timeout<=60 and 60<=a.long_timeout<=3600,'BAD_TIMEOUTS')
    require(run(['git','rev-parse','HEAD'],20).strip()==BASE,'BASE_CHANGED')
    require(run(['git','rev-parse','--show-prefix'],20).strip()=='','RUN_FROM_ROOT')
    old=load(ROOT/'tools/isa07_d11b_regression_gate.py','d13b_old_d11b_gate')
    prev=load(ROOT/'tools/isa07_d10f3_regression_gate.py','d13b_prev_d10f3_gate')
    require(old.BASE=='707cdf7ef72467e305056c0ff22d6582d16c8f76','D11B_ARCHIVE_CHANGED')
    require(len(prev.ISA06)==17,'ISA06_CORPUS_CHANGED')
    out=ROOT/'tempkyiv'/'isa07_d13b_regressions'
    out.mkdir(parents=True,exist_ok=True)
    def compile_probe(label,source):
        exe=out/(label+'.exe')
        log=run(['g++','-std=c++17','-O0','-Wall','-Wextra','-pedantic',
                 '-Iinc','src/main.cpp','tests/isa/'+source,'-o',str(exe)])
        (out/(label+'.build.log')).write_text(log,encoding='utf-8')
        return exe
    total=0
    # D8-B: all ten output 22/23 fixtures still current.
    d8=load(ROOT/'tools/isa07_d8b_output_interval_sandbox.py','d13b_d8b')
    exe=compile_probe('D8B','isa07_d8b_absolute_output_probe.cpp')
    log=io.StringIO()
    with contextlib.redirect_stdout(log):
        passed=sum(bool(d8.run_case(exe,op,kind,ROOT/'tempkyiv',a.timeout))
                   for op in d8.MODES for kind in d8.EXPECTED)
    (out/'D8B.run.log').write_text(log.getvalue(),encoding='utf-8')
    require(passed==10,'D8B_MISMATCH '+log.getvalue()[-1300:])
    total+=1;print('D13B D8B FUNCTIONAL PASS=10/10',flush=True)

    # D9-A: SHORT, EMPTY, MISSING now deliberately fail CLOSED.
    d9a=load(ROOT/'tools/isa07_d9a_io24_branch_sandbox.py','d13b_d9a')
    expected_a=('full','track1','single','altjump')
    exe=compile_probe('D9A_POSITIVE','isa07_d9a_io24_branch_probe.cpp')
    log=io.StringIO()
    with contextlib.redirect_stdout(log):
        passed=sum(bool(d9a.case(exe,m,ROOT/'tempkyiv',a.timeout)) for m in expected_a)
    (out/'D9A_POSITIVE.run.log').write_text(log.getvalue(),encoding='utf-8')
    require(passed==len(expected_a)==4,'D9A_POSITIVE_MISMATCH '+log.getvalue()[-1300:])
    total+=1;print('D13B D9A POSITIVE PASS=4/4 OLD_SHORT_EMPTY_MISSING=ARCHIVED',flush=True)

    # D9-B: 25->24 remains functional for valid inputs; old read-missing policy obsolete.
    d9b=load(ROOT/'tools/isa07_d9b_io25_sequential_sandbox.py','d13b_d9b')
    expected_b=tuple(m for m in d9b.CASES if m!='read-missing')
    require(len(expected_b)==7,'D9B_CASE_COUNT_DRIFT')
    exe=compile_probe('D9B_VALID','isa07_d9b_io25_sequential_probe.cpp')
    log=io.StringIO()
    with contextlib.redirect_stdout(log):
        passed=sum(bool(d9b.case(exe,m,ROOT/'tempkyiv',a.timeout)) for m in expected_b)
    (out/'D9B_VALID.run.log').write_text(log.getvalue(),encoding='utf-8')
    require(passed==7,'D9B_VALID_MISMATCH '+log.getvalue()[-1300:])
    total+=1;print('D13B D9B VALID PASS=7/7 OLD_READ_MISSING=ARCHIVED',flush=True)

    d10a=load(ROOT/'tools/isa07_d10a_io20_21_sequential_sandbox.py','d13b_d10a')
    positive=tuple(m for m in d10a.CASES if m.startswith('21-') and m!='21-missing')
    require(len(positive)==5,'D10A_CASE_COUNT_DRIFT')
    exe=compile_probe('IO21','isa07_d10a_io20_21_sequential_probe.cpp')
    log=io.StringIO()
    with contextlib.redirect_stdout(log):
        passed=sum(bool(d10a.one(exe,m,ROOT/'tempkyiv',a.timeout)) for m in positive)
    (out/'IO21.run.log').write_text(log.getvalue(),encoding='utf-8')
    require(passed==5,'IO21_MISMATCH '+log.getvalue()[-1300:])
    total+=1;print('D13B IO21 POSITIVE PASS=5/5',flush=True)

    exe=compile_probe('IO20','isa07_d10e3_io20_cpu_probe.cpp')
    text=run([sys.executable,str(ROOT/'tools/isa07_d10f3_io20_cpu_sandbox.py'),
              '--exe',str(exe),'--timeout',str(a.timeout)],900)
    (out/'IO20.run.log').write_text(text,encoding='utf-8')
    require('ISA-07 D10-F3 CPU PASS=50/50' in text,'IO20_MISMATCH '+text[-1300:])
    total+=1;print('D13B IO20 PASS=50/50',flush=True)

    # Historical D13-A *successful* output expectations still current.
    # The seven D13-A observations superseded by D13-B remain archived.
    d13a=load(ROOT/'tools/isa07_d13a_io23_host_sandbox.py','d13b_d13a')
    legacy_ok={
        'range','single','offset','legacy','fromzero','overwrite',
        'negative','max-positive','max-negative','drum-params',
        'modified-addresses','alternate-branch','io25-setup',
    }
    chosen=tuple(c for c in d13a.CASES if c.mode in legacy_ok)
    require(len(chosen)==len(legacy_ok)==13,'D13A_VALID_CASE_DRIFT')
    exe=compile_probe('D13A_POSITIVE','isa07_d13a_io23_host_observation_probe.cpp')
    log=io.StringIO()
    with contextlib.redirect_stdout(log):
        passed=sum(bool(d13a.one(exe,c,a.timeout,ROOT/'tempkyiv')) for c in chosen)
    (out/'D13A_POSITIVE.run.log').write_text(log.getvalue(),encoding='utf-8')
    require(passed==13,'D13A_POSITIVE_MISMATCH '+log.getvalue()[-1300:])
    total+=1;print('D13B D13A POSITIVE PASS=13/13 OLD_IO23_POLICY=ARCHIVED',flush=True)

    strict=policy=0
    for name in prev.ISA06:
        exe=compile_probe(name,name+'.cpp')
        timeout=a.long_timeout if 'd8_p8_' in name or 'd8_p10_' in name else max(60,a.timeout)
        text=run([str(exe)],timeout)
        (out/(name+'.run.log')).write_text(text,encoding='utf-8')
        summaries=[x for x in text.splitlines() if x.startswith('ISA-06 ')]
        require(len(summaries)==1,'ISA06_MISSING_SUMMARY '+name)
        match=re.search(r'\bSTRICT=(\d+)/(\d+)',summaries[0]);
        require(match is not None,'ISA06_MISSING_STRICT '+name)
        x,y=map(int,match.groups())
        p=re.search(r'\bPOLICY=(\d+)/(\d+)',summaries[0]);u,v=map(int,p.groups()) if p else (0,0)
        require(x==y and u==v,'ISA06_COUNTER_MISMATCH '+name+' '+summaries[0])
        strict+=y;policy+=v;total+=1
        print(f'D13B ISA06 {name} STRICT={x}/{y} POLICY={u}/{v}',flush=True)
    require(strict==89 and policy==40 and total==23,'REGRESSION_TOTALS_CHANGED')
    run(['git','diff','--check'],20)
    run(['git','diff','--cached','--check'],20)
    print('D13B REGRESSION PASS=23/23 D13A=13/13 D8B=10/10 D9A_POSITIVE=4/4 '
          'D9B_VALID=7/7 IO21=5/5 IO20=50/50 '
          'ISA06_STRICT=89/89 ISA06_POLICY=40/40 '
          'OBSOLETE_IO24_POLICY=EXCLUDED HARDWARE_ORACLE=0',flush=True)
    print('D13B REGRESSION_LOG_DIR=tempkyiv/isa07_d13b_regressions',flush=True)
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('D13B REGRESSION FAIL',str(exc),file=sys.stderr)
        raise SystemExit(1)
