#!/usr/bin/env python3
"""D9-B two-step IO25 -> IO23/24 sandbox; no hardware-device timing oracle."""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
# mode: expected RAM, expected output tokens (if output), input fixture (if read),
#       expected setup parameters r/z/w/wz, second-step PC
CASES={
  'write-basic': ('5/7/9/11', ('5','7','9'), None, (6,7,2,4), '120'),
  'write-single':('5/7/9/11', ('7',), None, (6,7,2,4), '120'),
  'write-offset':('5/7/9/11', ('7','9','11'), None, (6,7,2,4), '120'),
  'write-alt':  ('5/7/9/11', ('5','7','9'), None, (6,7,3,5), '130'),
  'read-basic': ('5/7/9/0', None, '5 7 9\n', (0,0,8,9), '120'),
  'read-single':('0/7/0/0', None, '7\n', (0,0,8,9), '120'),
  'read-trackzone':('7/9/11/0',None,'0 0 0\n5 7 9 11\n',(1,2,8,9),'120'),
  'read-missing':('0/0/0/0',None,None,(0,0,8,9),'120'),
}
OBS=re.compile(
    r'^D9B-OBS mode=(\S+) pc0=(\S+) pc1=(\S+) pc2=(\S+) '
    r'k1_match=(\d) k2_match=(\d) params=(\S+) params_post=(\S+) '
    r'memory_pre=(\d) memory=(\S+) running=(\d)/(\d) steps=(\d+)$',re.M)

def case(exe,mode,parent,timeout):
    expected_ram, expected_output, tape, params, pc2 = CASES[mode]
    with tempfile.TemporaryDirectory(prefix='isa07_d9b_',dir=parent) as t:
        root=Path(t)
        (root/'a'/'b').mkdir(parents=True)
        (root/'mem').mkdir()
        if tape is not None:
            # Host fixtures are ASCII text records, not an emulated drum encoding.
            (root/'mem'/'drum_in.txt').write_text(tape,encoding='ascii')
        try:
            p=subprocess.run([str(exe),mode],cwd=root/'a'/'b',capture_output=True,
                             text=True,encoding='utf-8',errors='replace',timeout=timeout)
            status=f'EXIT_{p.returncode}'
            output=p.stdout+'\n'+p.stderr
        except subprocess.TimeoutExpired:
            status='TIMEOUT';output=''
        records=OBS.findall(output)
        ob=records[0] if len(records)==1 else None
        exp_params='/'.join(str(x) for x in params)
        ok=(status=='EXIT_0' and ob is not None and
            ob==(mode,'100','101',pc2,'1','1',exp_params,exp_params,
                 '1',expected_ram,'1','1','2'))
        out_file=root/'a'/'magnetic_drum.txt'
        wrong_file=root/'a'/'punc_cards_out.txt'
        if expected_output is not None:
            good_out=out_file.is_file() and tuple(out_file.read_text(encoding='ascii').split())==expected_output
        else:
            good_out=not out_file.exists()
        ok=ok and good_out and not wrong_file.exists()
        files=[p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()]
        allowed={'a/magnetic_drum.txt'} if expected_output is not None else set()
        if tape is not None:allowed.add('mem/drum_in.txt')
        ok=ok and set(files)==allowed
        classification=('HOST_POLICY' if mode=='read-missing'
                        else 'SOURCE_STRICT_NEXT_PC_HOST_ADAPTER')
        print(f'D9B-CODE-{"PASS" if ok else "FAIL"} mode={mode} process={status} '
              f'pc1={ob[2] if ob else "N/A"} pc2={ob[3] if ob else "N/A"} '
              f'K_PREFETCH={int(bool(ob) and ob[4:6]==("1","1"))} '
              f'params={ob[6] if ob else "N/A"} '
              f'ram={ob[9] if ob else "N/A"} '
              f'output={"/".join(expected_output) if expected_output is not None else "NONE"} '
              f'class={classification} result={"PASS" if ok else "FAIL"}')
        if not ok:
            print('  OUTPUT_TAIL=',repr(output.splitlines()[-10:]))
            print('  CREATED_FILES=',repr(sorted(files)))
            if out_file.is_file():print('  DRUM_OUT=',repr(out_file.read_text(encoding='ascii')[:120]))
        return ok

def main():
    p=argparse.ArgumentParser();p.add_argument('--exe',required=True)
    p.add_argument('--timeout',type=float,default=5)
    args=p.parse_args()
    exe=Path(args.exe).resolve();parent=ROOT/'tempkyiv'
    if not exe.is_file() or not parent.is_dir():p.error('exe and tempkyiv required')
    if not 0.2<=args.timeout<=60:p.error('timeout must be 0.2..60 s')
    passed=sum(bool(case(exe,mode,parent,args.timeout)) for mode in CASES)
    print(f'ISA-07 D9B SANDBOX PASS={passed}/{len(CASES)} TWO_STEPS={len(CASES)} '
          'IO25_NEXT_PC=DOCUMENTED K_PREFETCH=EMULATOR_CONVENTION '
          'IO23_24_SECOND_STEP=EXECUTED DRUM_SETUP=UNCHANGED '
          'HOST_MISSING=POLICY IO20_21_PC=OPEN DEVICE_ORACLES=0')
    return 0 if passed==len(CASES) else 1

if __name__=='__main__':sys.exit(main())
