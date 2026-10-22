#!/usr/bin/env python3
"""D15/A2 actual CLI vs standalone parity, legacy compatibility and safety.

All fixtures private; baseline legacy CLI is built from git-pinned sources.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile
import re

BASE = '68fa06f247f3b3a70ba37a72283469b6cec6b137'
ROOT = Path(__file__).resolve().parents[1]
SIGN = 1 << 40
MASK = (1 << 41) - 1


def git(*args):
    p = subprocess.run(['git', *args], cwd=ROOT, text=True,
                       capture_output=True, timeout=30)
    if p.returncode: raise RuntimeError('GIT_FAILED: ' + p.stderr[-300:])
    return p.stdout.strip()


def need(ok, why, process=None):
    if not ok:
        detail = '' if process is None else (
            f' rc={process.returncode} stdout={process.stdout[-700:]!r}'
            f' stderr={process.stderr[-700:]!r}')
        raise AssertionError(why + detail)


def command(op, a1=0, a2=0, a3=0):
    return op << 36 | a1 << 24 | a2 << 12 | a3


def image(pairs):
    return ('KYIV41-OCT1\n'+''.join(f'{a:04o} {w:014o}\n' for a,w in pairs)).encode('ascii')


def invoke(exe, args, timeout):
    return subprocess.run([str(exe), *map(str,args)],cwd=ROOT, text=True,
                          capture_output=True,encoding='utf-8',errors='replace',
                          timeout=timeout)


def summary(r):
    # The real disassembler can print additional internal diagnostics;
    # only the bounded public HOST contract is compared across executables.
    out = []
    for line in r.stdout.splitlines():
        if line.startswith(('D15A1-LOAD ', 'D15A1-RUN ', 'D15A1-WATCH ',
                            'D15A2-LOAD ', 'D15A2-RUN ', 'D15A2-WATCH ')):
            out.append(re.sub(r'^D15A[12]-','D15AX-',line))
    errors=[]
    for line in r.stderr.splitlines():
        if line.startswith(('D15A1-ERROR ','D15A2-ERROR ')):
            errors.append(re.sub(r'^D15A[12]-','D15AX-',line))
    return r.returncode, out, errors


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--a1-exe',type=Path)
    ap.add_argument('--cli-exe',type=Path)
    ap.add_argument('--cxx',default='g++')
    ap.add_argument('--timeout',type=int,default=20)
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    need(command(0o33)==0o33<<36,'COMMAND_ENCODING')
    need(len(image([(0o500, MASK)]).splitlines()[1].split()[1])==14,
         'IMAGE_WORD_WIDTH')
    need(summary(type('Fake',(),dict(returncode=0,stdout='D15A2-RUN STATUS=LIMIT\n',stderr=''))()) ==
         (0,['D15AX-RUN STATUS=LIMIT'],[]),'SUMMARY_NORMALIZATION')
    if args.self_test:
        print('D15A2-SELFTEST PASS RAW41=1 SUMMARY=1 OP33=1')
        return
    need(0 < args.timeout <= 120,'INVALID_TIMEOUT')
    need(git('rev-parse','HEAD') == BASE,'PINNED_HEAD_MISMATCH')
    need(git('branch','--show-current') == 'main','NOT_MAIN')
    need(git('rev-parse','--show-prefix') == '','NOT_REPO_ROOT')
    need(all(x is not None for x in (args.a1_exe,args.cli_exe)), 'MISSING_EXECUTABLE')
    a1=args.a1_exe.resolve();cli=args.cli_exe.resolve()
    need(a1.is_file() and cli.is_file(), 'MISSING_EXECUTABLE')
    count=0
    with tempfile.TemporaryDirectory(prefix='d15a2_',dir=ROOT/'tempkyiv') as temp:
        folder=Path(temp)/'private image folder with spaces';folder.mkdir()
        def check_case(label,data,tail,success=True):
            nonlocal count
            file=folder/(f'case{count:02d}.k41')
            file.write_bytes(data)
            before=file.read_bytes()
            ra=invoke(a1,[file,*tail],args.timeout)
            rb=invoke(cli,['image',file,*tail],args.timeout)
            need(summary(ra)==summary(rb),'PARITY_'+label,rb)
            need(file.read_bytes()==before,'SOURCE_MUTATED_'+label)
            need(ra.returncode == (0 if success else 2),'RETURN_CODE_'+label,ra)
            if success:
                need(any('-RUN ' in s for s in summary(ra)[1]),'RUN_SUMMARY_MISSING',ra)
            else:
                need(any('ERROR' in s for s in summary(ra)[2]),'ERROR_MISSING',ra)
            count+=1
            print(f'D15A2-CASE {count:02d} {label}: PASS',flush=True)

        good=image([(1,3),(2,4),(4,SIGN),
                    (0o500,command(0o1,1,2,3)),(0o501,command(0o33))])
        check_case('stop-add-signed-zero',good,['0500','10','--watch','0003','--watch','0004'])
        check_case('bounded-add',good,['0500','1','--watch','0003'])
        check_case('repeated-watch',good,['0500','3','--watch','0001','--watch','0001'])
        check_case('zero-opcode-limit',image([(0o500,0)]),['0500','3'])
        check_case('conditional-loop',image([(1,5),(2,5),
                         (0o500,command(0o16,1,2,0o500))]),['0500','4'])
        check_case('sign-distinction',image([(1,0),(2,SIGN),
                         (0o500,command(0o16,1,2,0o502)),
                         (0o501,command(0o33)),(0o502,command(0o33))]),['0500','4'])
        check_case('maximal-word',image([(1,MASK),(0o500,command(0o33))]),
                   ['0500','2','--watch','0001'])
        check_case('comments-spaces',b'# comment\nKYIV41-OCT1 #header\n 0500 33000000000000\n',
                   ['0500','2'])
        check_case('rom-opt-in',image([(0o3010,command(0o33))]),
                   ['3010','2','--allow-rom'])
        check_case('rom-denied',image([(0o3010,command(0o33))]),['3010','2'],False)
        check_case('duplicate',image([(0o500,0),(0o500,1)]),['0500','2'],False)
        check_case('bad-header',b'KYIV41-OCT2\n0500 33000000000000\n',['0500','2'],False)
        check_case('overwide',image([(0o500,1<<41)]),['0500','2'],False)
        check_case('forbidden-gap',image([(0o2000,0)]),['0500','2'],False)
        check_case('zero-cell',image([(0,0)]),['0500','2'],False)
        check_case('limit-wraparound',good,['0500','18446744073709551617'],False)
        check_case('nondigit-limit',good,['0500','2x'],False)
        check_case('missing-watch',good,['0500','2','--watch'],False)
        check_case('invalid-watch',good,['0500','2','--watch','2000'],False)
        check_case('bad-start',good,['2000','2'],False)
        check_case('empty-image',b'KYIV41-OCT1\n',['0500','2'],False)
        check_case('bad-fields',b'KYIV41-OCT1\n0500 33000000000000 extra\n',
                   ['0500','2'],False)

        # Fail closed on suffixes excluded by the D15/A2 HOST-mode contract.
        newimg=folder/'suffix.k41';newimg.write_bytes(good)
        for flag in [['--block-overflow-stop'],
                     ['--experimental-drum',str(folder/'none.kdr'),'experiment', '2','8','1']]:
            got=invoke(cli,['image',newimg,'0500','2',*flag],args.timeout)
            need(got.returncode==2 and 'D15A2-ERROR IMAGE_SUFFIX_UNSUPPORTED' in got.stderr,
                 'UNSUPPORTED_SUFFIX_NOT_REJECTED',got)
            count+=1
            print(f'D15A2-CASE {count:02d} excluded-suffix: PASS',flush=True)

        # Build a pristine legacy production CLI from the *pinned Git tree*.
        # Comparing actual stdout and stderr preserves existing CLI behavior.
        oldsrc=Path(temp)/'legacy_asm_disasm.cpp'
        # Keep the original UTF-8 bytes (including Ukrainian comments and
        # line endings) rather than decoding via Windows locale settings.
        original_cli = subprocess.run(
            ['git', 'show', BASE+':src/asm_disasm.cpp'],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30)
        need(original_cli.returncode == 0, 'PINNED_CLI_FETCH_FAILED')
        oldsrc.write_bytes(original_cli.stdout)
        oldexe=Path(temp)/'legacy_kyivemu.exe'
        build=subprocess.run([args.cxx,'-std=c++17','-O0','-Wall','-Wextra',
                              '-pedantic','-Iinc','src/main.cpp',str(oldsrc),
                              '-o',str(oldexe)],cwd=ROOT,capture_output=True,
                              text=True,encoding='utf-8',errors='replace',timeout=120)
        need(build.returncode==0,'LEGACY_BUILD_FAILED',build)
        stop=command(0o33)
        variants=[['expression',f'(320,{stop})','0500'],
                  ['expression',f'(320,{stop})','0500','--block-overflow-stop']]
        for v in variants:
            o=invoke(oldexe,v,args.timeout)
            n=invoke(cli,v,args.timeout)
            need(o.returncode==n.returncode and o.stdout==n.stdout and
                 o.stderr==n.stderr, 'LEGACY_CLI_REGRESSION',n)
            count+=1
            print(f'D15A2-CASE {count:02d} legacy-expression: PASS',flush=True)

    need(count==26,'CASE_COUNT_MISMATCH')
    print('D15A2-CLI PASS CASES=26/26 SHARED_PARSER=1 BOUNDED=1 '
          'A1_A2_PARITY=22/22 LEGACY_PARITY=2/2 SUFFIX_REJECTED=2/2 '
          'CPU_MUTATION=0 HISTORICAL_CORPUS=PENDING ROM_BASELINE=OPEN HARDWARE_ORACLE=0')

if __name__=='__main__':
    main()
