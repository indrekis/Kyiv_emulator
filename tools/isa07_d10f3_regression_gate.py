#!/usr/bin/env python3
"""ISA-07 D10-F3: unchanged-opcode functional regression gate.

No repo file mutations. Runs actual Kyiv_t binaries; preserves historic auditors.
This script is a host test harness, not a historical device oracle.
"""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

BASE = '98964fd96dfc8dbea692accd1ffb00d5d8719abb'
IO_CASES = (
    ('D8B', 'isa07_d8b_absolute_output_probe.cpp', 'isa07_d8b_output_interval_sandbox.py', 'PASS=10/10'),
    ('D9A', 'isa07_d9a_io24_branch_probe.cpp', 'isa07_d9a_io24_branch_sandbox.py', 'PASS=7/7'),
    ('D9B', 'isa07_d9b_io25_sequential_probe.cpp', 'isa07_d9b_io25_sequential_sandbox.py', 'PASS=8/8'),
)
IO21_PROBE = 'isa07_d10a_io20_21_sequential_probe.cpp'
IO21_RUNNER = 'isa07_d10a_io20_21_sequential_sandbox.py'
ISA06 = (
    'isa06_d1_logic_probe',
    'isa06_d2_logic_sequence_probe',
    'isa06_d3_historical_shift_probe',
    'isa06_d4_historical_ram_window_probe',
    'isa06_d5_historical_ram_iterations_probe',
    'isa06_d6_zero_sum_probe',
    'isa06_d7_zero_sign_flow_probe',
    'isa06_d8_p1_signed_zero_policy_probe',
    'isa06_d8_p2_historical_ram_policy_probe',
    'isa06_d8_p3_natural_phase_walk_probe',
    'isa06_d8_p4_multi_pattern_probe',
    'isa06_d8_p5_terminal_dispatch_probe',
    'isa06_d8_p6_natural_terminal_reach_probe',
    'isa06_d8_p7_documented_entry_probe',
    'isa06_d8_p8_full_entry_78_cycles_probe',
    'isa06_d8_p9_nk_memory_integration_probe',
    'isa06_d8_p10_natural_nk_dispatch_probe',
)

class GateFailure(Exception):
    pass


def run(cmd, cwd, timeout, input_text=None):
    try:
        return subprocess.run(cmd, cwd=cwd, input=input_text, capture_output=True,
                              text=True, encoding='utf-8', errors='replace',
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise GateFailure(f'TIMEOUT={timeout}s COMMAND={cmd!r}') from exc
    except OSError as exc:
        raise GateFailure(f'EXECUTION_ERROR={exc} COMMAND={cmd!r}') from exc


def require(condition, message):
    if not condition:
        raise GateFailure(message)


def log_tail(content, max_lines=15):
    return '\n'.join(content.splitlines()[-max_lines:])


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--repo', type=Path, default=Path.cwd())
    cli.add_argument('--compiler', default='g++')
    cli.add_argument('--timeout', type=int, default=20, help='normal CPU-test timeout seconds')
    cli.add_argument('--long-timeout', type=int, default=900, help='ISA-06 long run timeout seconds')
    cli.add_argument('--build-timeout', type=int, default=180)
    args = cli.parse_args()
    require(5 <= args.timeout <= 600 and 60 <= args.long_timeout <= 3600,
            'TIMEOUT_ARGUMENT_OUT_OF_RANGE')
    require(30 <= args.build_timeout <= 1200, 'BUILD_TIMEOUT_OUT_OF_RANGE')
    root = args.repo.resolve()
    require((root/'src/main.cpp').is_file() and (root/'inc/kyiv.h').is_file(),
            'NOT_KYIV_REPOSITORY_ROOT')
    head = run(['git','rev-parse','HEAD'], root, 15)
    require(head.returncode == 0 and head.stdout.strip() == BASE,
            'UNEXPECTED_HEAD: required ' + BASE + ' got ' + head.stdout.strip())
    prefix = run(['git','rev-parse','--show-prefix'], root, 15)
    require(prefix.returncode == 0 and not prefix.stdout.strip(),
            'RUN_FROM_REPOSITORY_ROOT')
    out = root/'tempkyiv'/'isa07_d10f3_regressions'
    out.mkdir(parents=True, exist_ok=True)
    result = {'base': BASE, 'utc': datetime.now(timezone.utc).isoformat(),
              'io': [], 'io21': {}, 'isa06': [], 'gates_passed': 0}
    print('D10F3 PREFLIGHT PASS BASELINE=98964fd ROOT=1 MUTATION=0', flush=True)

    def compile_probe(label, source):
        require((root/'tests'/'isa'/source).is_file(), 'MISSING_PROBE=' + source)
        exe = out/(label+'.exe')
        cmd = [args.compiler, '-std=c++17', '-O0', '-Wall', '-Wextra', '-pedantic',
               '-Iinc', 'src/main.cpp', 'tests/isa/'+source, '-o', str(exe)]
        process = run(cmd, root, args.build_timeout)
        (out/(label+'.build.log')).write_text(process.stdout+'\n'+process.stderr,
                                            encoding='utf-8')
        require(process.returncode == 0 and exe.is_file(),
                'BUILD_FAIL ' + label + '\n' + log_tail(process.stderr))
        return exe

    def run_script(label, script, exe, count):
        cmd = [sys.executable, str(root/'tools'/script),
               '--exe', str(exe), '--timeout', str(args.timeout)]
        process = run(cmd, root, max(150, args.timeout * (count+2)))
        output = process.stdout+'\n'+process.stderr
        (out/(label+'.run.log')).write_text(output, encoding='utf-8')
        require(process.returncode == 0 and count == len(re.findall(r'(?m)^D(?:8B|9A|9B)-CODE-[^\n]*result=PASS\s*$', output)),
                'IO_GATE_FAIL ' + label + '\n' + log_tail(output))
        return output

    for label, source, script, expected in IO_CASES:
        exe = compile_probe(label, source)
        n = int(expected.split('/')[1])
        output = run_script(label, script, exe, n)
        require(expected in output, 'WRONG_IO_SUMMARY=' + label + '\n' + log_tail(output))
        result['io'].append({'gate': label, 'cases': n, 'pass': True})
        result['gates_passed'] += 1
        print('D10F3 ' + label + ' FUNCTIONAL PASS=' + str(n) + '/' + str(n), flush=True)

    # D10-A's six original IO20 expectations are obsolete. Reuse only its
    # verified IO21 runner + probe in six actual two-step executions.
    exe = compile_probe('IO21', IO21_PROBE)
    spec = importlib.util.spec_from_file_location('d10a_io21_only', root/'tools'/IO21_RUNNER)
    require(spec is not None and spec.loader is not None, 'IO21_RUNNER_IMPORT_ERROR')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    modes = tuple(m for m in mod.CASES if m.startswith('21-'))
    require(len(modes) == 6, f'IO21_EXPECTED_SIX_GOT_{len(modes)}')
    io21_log = io.StringIO()
    io21_passed = 0
    with contextlib.redirect_stdout(io21_log):
        for mode in modes:
            io21_passed += int(mod.one(exe, mode, root/'tempkyiv', args.timeout))
    contents = io21_log.getvalue()
    (out/'IO21.run.log').write_text(contents, encoding='utf-8')
    require(io21_passed == 6 and contents.count('D10A-CODE-PASS mode=21-') == 6,
            'IO21_ONLY_FAIL\n' + log_tail(contents))
    result['io21'] = {'cases': 6, 'pass': True, 'excluded': 'obsolete IO20'}
    result['gates_passed'] += 1
    print('D10F3 IO21 TWO_STEP PASS=6/6 D10A_OLD_IO20=EXCLUDED', flush=True)

    strict_passed = strict_total = policy_passed = policy_total = 0
    for base in ISA06:
        exe = compile_probe(base, base+'.cpp')
        timeout = args.long_timeout if ('d8_p8_' in base or 'd8_p10_' in base) else max(60, args.timeout)
        process = run([str(exe)], root, timeout)
        output = process.stdout+'\n'+process.stderr
        (out/(base+'.run.log')).write_text(output, encoding='utf-8')
        require(process.returncode == 0, 'ISA06_NONZERO '+base+'\n'+log_tail(output))
        summaries = [line for line in output.splitlines() if line.startswith('ISA-06 ')]
        require(len(summaries) == 1, 'ISA06_MISSING_OR_MULTIPLE_SUMMARY '+base+'\n'+log_tail(output))
        summary = summaries[0]
        strict = re.search(r'\bSTRICT=(\d+)/(\d+)\b', summary)
        policy = re.search(r'\bPOLICY=(\d+)/(\d+)\b', summary)
        require(strict is not None, 'ISA06_STRICT_COUNT_MISSING '+base+' '+summary)
        a,b = map(int, strict.groups())
        c,d = (tuple(map(int, policy.groups())) if policy is not None else (0,0))
        mismatch = re.search(r'\bDOC-MISMATCH=(\d+)\b', summary)
        policyfail = re.search(r'\bPOLICY-FAIL=(\d+)\b', summary)
        require(a == b and c == d and (mismatch is None or mismatch.group(1) == '0')
                and (policyfail is None or policyfail.group(1) == '0'),
                'ISA06_COUNTER_FAIL '+base+' '+summary)
        strict_passed += a; strict_total += b
        policy_passed += c; policy_total += d
        result['isa06'].append({'probe':base,'strict':f'{a}/{b}', 'policy':f'{c}/{d}','pass':True})
        result['gates_passed'] += 1
        print(f'D10F3 ISA06 PASS {base} STRICT={a}/{b} POLICY={c}/{d}',flush=True)

    # Prior full accepted gate; prevent accidental omission of an ISA-06 probe.
    require(strict_total == 89 and policy_total == 40,
            f'ISA06_AGGREGATE_CHANGED STRICT={strict_passed}/{strict_total} POLICY={policy_passed}/{policy_total}')
    print(f'ISA-06 REGRESSION STRICT={strict_passed}/{strict_total} POLICY={policy_passed}/{policy_total}',flush=True)
    for command in (('git','diff','--check'),('git','diff','--cached','--check')):
        checked = run(command, root, 30)
        require(checked.returncode == 0, 'DIFF_CHECK_FAILED '+' '.join(command)+'\n'+checked.stdout+checked.stderr)
    current_head = run(['git','rev-parse','HEAD'], root, 15)
    require(current_head.returncode == 0 and current_head.stdout.strip() == BASE, 'HEAD_CHANGED_DURING_TEST')
    result['strict'] = f'{strict_passed}/{strict_total}'
    result['policy'] = f'{policy_passed}/{policy_total}'
    result['status'] = 'PASS'
    (out/'SUMMARY.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'D10F3 REGRESSION PASS=21/21 IO22_25=25/25 IO21=6/6 '
          f'ISA06_STRICT={strict_passed}/{strict_total} ISA06_POLICY={policy_passed}/{policy_total} '
          f'HEAD=98964fd DIFF_CHECK=PASS CPU_MAIN_UNCOMMITTED=1',flush=True)
    print('D10F3 LOG_DIR=tempkyiv/isa07_d10f3_regressions',flush=True)
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (GateFailure, Exception) as error:
        print('D10F3 REGRESSION FAIL ' + str(error), file=sys.stderr,flush=True)
        sys.exit(1)
