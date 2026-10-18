#!/usr/bin/env python3
"""D11-B: functional unaffected-opcode gates; archived SHA auditors stay archived.

This gate recompiles actual src/main.cpp (not mock CPU) for all C++ probes.
All generated logs and executables stay under tempkyiv/.
"""
import argparse
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE='707cdf7ef72467e305056c0ff22d6582d16c8f76'

def module(path,tag):
    spec=importlib.util.spec_from_file_location(tag,path)
    if spec is None or spec.loader is None:raise RuntimeError('missing module '+str(path))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run(command,cwd,timeout):
    proc=subprocess.run(command,cwd=cwd,text=True,capture_output=True,
                        encoding='utf-8',errors='replace',timeout=timeout)
    if proc.returncode:
        raise RuntimeError('FAILED '+str(command)+'\n'+(proc.stdout+proc.stderr)[-1400:])
    return proc.stdout+'\n'+proc.stderr

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--timeout',type=float,default=20)
    ap.add_argument('--long-timeout',type=int,default=900)
    a=ap.parse_args()
    if not 5<=a.timeout<=60 or not 60<=a.long_timeout<=3600:ap.error('timeouts')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=BASE:
        raise RuntimeError('wrong D11-A HEAD')
    if subprocess.check_output(['git','rev-parse','--show-prefix'],cwd=ROOT,text=True).strip():
        raise RuntimeError('run from root')
    previous=module(ROOT/'tools/isa07_d10f3_regression_gate.py','old_regressions')
    root=ROOT/'tempkyiv'/'isa07_d11b_regressions'
    root.mkdir(parents=True,exist_ok=True)
    def compile_probe(name,source):
        exe=root/(name+'.exe')
        log=run(['g++','-std=c++17','-O0','-Wall','-Wextra','-pedantic',
                 '-Iinc','src/main.cpp','tests/isa/'+source,'-o',str(exe)],ROOT,180)
        (root/(name+'.build.log')).write_text(log,encoding='utf-8')
        return exe
    total=0
    for name,src,runner,expected in previous.IO_CASES:
        exe=compile_probe(name,src)
        n=int(expected.split('/')[1])
        output=run([sys.executable,str(ROOT/'tools'/runner),'--exe',str(exe),
                    '--timeout',str(a.timeout)],ROOT,max(180,int(n*a.timeout+60)))
        (root/(name+'.run.log')).write_text(output,encoding='utf-8')
        if expected not in output or len(re.findall(r'D(?:8B|9A|9B)-CODE-[^\n]*result=PASS\s*$',output,re.M))!=n:
            raise RuntimeError(name+' regression mismatch '+output[-1200:])
        total+=1
        print('D11B '+name+' FUNCTIONAL '+expected,flush=True)
    # D10-A's old 21-missing expected success and is now OBSOLETE.
    # The other five modes are source-compatible octal raw words.
    exe=compile_probe('D10A_IO21','isa07_d10a_io20_21_sequential_probe.cpp')
    prior=module(ROOT/'tools/isa07_d10a_io20_21_sequential_sandbox.py','old_d10a')
    names=tuple(k for k in prior.CASES if k.startswith('21-') and k!='21-missing')
    if len(names)!=5:raise RuntimeError('D10A expected exactly 5 still-qualified positives')
    log=io.StringIO()
    with contextlib.redirect_stdout(log):
        passed=sum(prior.one(exe,k,ROOT/'tempkyiv',a.timeout) for k in names)
    (root/'D10A_IO21.run.log').write_text(log.getvalue(),encoding='utf-8')
    if passed!=5:raise RuntimeError('D10A IO21 positives fail '+log.getvalue()[-1200:])
    print('D11B IO21 D10A_POSITIVE PASS=5/5 MISSING_OLD_POLICY=EXCLUDED',flush=True)
    total+=1
    # IO20 current functional runner (the archived exact/nonexact rejection
    # expectations were already updated by D10-F3).
    exe=compile_probe('IO20_F3','isa07_d10e3_io20_cpu_probe.cpp')
    output=run([sys.executable,str(ROOT/'tools/isa07_d10f3_io20_cpu_sandbox.py'),
                '--exe',str(exe),'--timeout',str(a.timeout)],ROOT,900)
    (root/'IO20_F3.run.log').write_text(output,encoding='utf-8')
    if 'ISA-07 D10-F3 CPU PASS=50/50' not in output:raise RuntimeError('IO20 50/50 absent '+output[-1200:])
    print('D11B IO20 F3 FUNCTIONAL PASS=50/50',flush=True)
    total+=1
    strict=policy=0
    for name in previous.ISA06:
        exe=compile_probe(name,name+'.cpp')
        timeout=a.long_timeout if 'd8_p8_' in name or 'd8_p10_' in name else max(60,a.timeout)
        output=run([str(exe)],ROOT,timeout)
        (root/(name+'.run.log')).write_text(output,encoding='utf-8')
        match=re.findall(r'^ISA-06 [^\n]+',output,re.M)
        if len(match)!=1:raise RuntimeError(name+' missing summary '+output[-700:])
        s=re.search(r'\bSTRICT=(\d+)/(\d+)',match[0]);p=re.search(r'\bPOLICY=(\d+)/(\d+)',match[0])
        if not s:raise RuntimeError(name+' no strict counter')
        sc,st=map(int,s.groups());pc,pt=map(int,p.groups()) if p else (0,0)
        if sc!=st or pc!=pt:raise RuntimeError(name+' failing ISA06 '+match[0])
        strict+=st;policy+=pt;total+=1
        print(f'D11B ISA06 {name} STRICT={sc}/{st} POLICY={pc}/{pt}',flush=True)
    if strict!=89 or policy!=40 or total!=22:
        raise RuntimeError(f'wrong totals groups={total} strict={strict} policy={policy}')
    run(['git','diff','--check'],ROOT,20)
    run(['git','diff','--cached','--check'],ROOT,20)
    print('D11B REGRESSION PASS=22/22 IO22_25=25/25 D10A_IO21=5/5 '
          'IO20=50/50 ISA06_STRICT=89/89 ISA06_POLICY=40/40 '
          'HISTORICAL_AUDITORS=ARCHIVED HARDWARE_ORACLE=0',flush=True)
    print('D11B REGRESSION_LOG_DIR=tempkyiv/isa07_d11b_regressions',flush=True)
    return 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print('D11B REGRESSION FAIL',str(e),file=sys.stderr,flush=True)
        sys.exit(1)
