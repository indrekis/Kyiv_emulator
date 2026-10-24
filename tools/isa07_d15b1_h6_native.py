#!/usr/bin/env python3
"""D15/B1-H6 historical three additions: real CLI in two CWDs, positive and private STOP tests."""
from __future__ import annotations
import argparse,hashlib,os,pathlib,re,subprocess,tempfile

IMG='examples/historical/gy1962/au1_addition_0116_0126.k41'
IMG_SHA='cc09f0928483df9fd32e0fb66dcb0b94fe5181c53d3e4238e133a9500f786cca'
DATA={'0002': '12525252525252', '0003': '25252525252525', '0004': '05252525252525', '0005': '32525252525252', '0006': '07573675736745', '0007': '17367573675712'}
GROUPS=[
    # start, after ADD, after equality branch, expected word at 0347, check constant, historical STOP address
    ('0116','0117','0121','17367573675712','0007','0120'),
    ('0121','0122','0124','25252525252525','0003','0123'),
    ('0124','0125','0127','05252525252525','0004','0126'),
]
RUN=re.compile(r'D15A2-RUN STATUS=([A-Z_]+) STEPS=(\d+) C=([0-7]{4})')
WATCH=re.compile(r'D15A2-WATCH ADDR=([0-7]{4}) RAW=([0-7]{14})')
MASK=(1<<40)-1; SIGN=(1<<40)

def value(v):
    w=int(v,8)
    return -(w&MASK) if w&SIGN else w&MASK

def oracle():
    assert value(DATA['0006'])+value(DATA['0006'])==value(DATA['0007'])
    assert value(DATA['0004'])+value(DATA['0005'])==value(DATA['0003'])
    assert value(DATA['0002'])+value(DATA['0003'])==value(DATA['0004'])
    assert len(GROUPS)==3 and len(DATA)==6
    assert [g[0] for g in GROUPS]==['0116','0121','0124']
    for a,b in DATA.items():
        assert len(a)==4 and len(b)==14 and set(a+b)<=set('01234567')
    print('D15B1H6-RUNNER-SELFTEST PASS GROUPS=3/3 INPUTS=6/6 ARITH_ORACLE=3/3 SIGN_BIT=1')

def run(exe,image,cwd,start,n,timeout):
    v=[str(exe),'image',str(image),start,str(n),'--watch','0347']
    for a in DATA:v+=['--watch',a]
    p=subprocess.run(v,cwd=cwd,capture_output=True,text=True,
                     timeout=timeout,encoding='utf-8',errors='replace')
    m=RUN.search(p.stdout)
    return p,m.groups() if m else None,dict(WATCH.findall(p.stdout))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--cli-exe');ap.add_argument('--timeout',type=float,default=20)
    ap.add_argument('--self-test',action='store_true');x=ap.parse_args()
    oracle()
    if x.self_test:return
    assert x.cli_exe,'MISSING_CLI_EXE'
    root=pathlib.Path(__file__).resolve().parent.parent
    image=(root/IMG)
    assert hashlib.sha256(image.read_bytes()).hexdigest()==IMG_SHA,'IMAGE_SHA_MUTATION'
    exe=pathlib.Path(x.cli_exe).resolve();assert exe.is_file(),('MISSING_EXE',exe)
    assert (root/'tempkyiv').is_dir(),'MISSING_TEMPKYIV'
    case=0; negatives=0
    with tempfile.TemporaryDirectory(prefix='d15b1h6_cwd_') as td:
      temp=pathlib.Path(td)
      for start,after1,after2,result,check,stop in GROUPS:
        for cwd_name,cwd in [('EXTERNAL',temp),('TEMPKYIV',root/'tempkyiv')]:
          for budget,counter in [(1,after1),(2,after2)]:
            p,run_tuple,w=run(exe,image,cwd,start,budget,x.timeout)
            good=(p.returncode==0 and run_tuple==('LIMIT',str(budget),counter)
                  and w.get('0347')==result and
                  all(w.get(a)==v for a,v in DATA.items()))
            case+=1
            print(f'D15B1H6-CASE {case:02d} PROFILE=HISTORICAL START={start} STEPS={budget} CWD={cwd_name} RC={p.returncode} RUN={run_tuple} RESULT={w.get("0347")} ORACLE={result} '+('PASS' if good else 'MISMATCH'),flush=True)
            if not good:
              print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
              raise AssertionError('HISTORICAL_RESULT_MISMATCH')
          # Private synthetic negative branch witness; only expected constant mutated.
          lines=image.read_text().splitlines(keepends=True)
          target=check+' '+DATA[check]
          assert sum(z.strip()==target for z in lines)==1,('PRIVATE_ANCHOR',check)
          changed=''.join((check+' 00000000000000\n') if z.strip()==target else z for z in lines)
          private=temp/f'fail_{start}_{cwd_name}.k41';private.write_text(changed)
          p,run_tuple,w=run(exe,private,cwd,start,3,x.timeout)
          next_after_stop=format(int(stop,8)+1,'04o')
          good=(p.returncode==0 and run_tuple==('CPU_STOP','3',next_after_stop)
                and w.get('0347')==result)
          case+=1;negatives+=1
          print(f'D15B1H6-CASE {case:02d} PROFILE=PRIVATE_STOP START={start} STEPS=3 CWD={cwd_name} RC={p.returncode} RUN={run_tuple} EXPECTED=CPU_STOP,3,{next_after_stop} '+('PASS' if good else 'MISMATCH'),flush=True)
          if not good:
            print('STDOUT:\n'+p.stdout[-3000:]+'\nSTDERR:\n'+p.stderr,flush=True)
            raise AssertionError('STOP_FALLBACK_MISMATCH')
    assert case==18 and negatives==6
    assert hashlib.sha256(image.read_bytes()).hexdigest()==IMG_SHA,'IMAGE_POST_MUTATION'
    print('D15B1H6-NATIVE PASS CASES=18/18 POSITIVE=12/12 PRIVATE_STOP=6/6 GROUPS=3/3 CWD_PARITY=9/9 HISTORICAL_EXPECTATION_MATCH=1 CANONICAL_SOURCE_IMMUTABLE=1 CPU_MUTATION=0 HARDWARE_ORACLE=0')

if __name__=='__main__':
    try:main()
    except BaseException as e:raise SystemExit('D15B1H6-NATIVE FAIL '+repr(e))
