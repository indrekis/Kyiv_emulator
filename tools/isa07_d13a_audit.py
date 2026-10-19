#!/usr/bin/env python3
"""D13-A: read-only audit of five new characterization files, immutable CPU."""
from __future__ import annotations
import hashlib
from pathlib import Path
import re
import subprocess
import sys

BASE = 'f7c2b405a49fc6956628ed4e94bd3380e9726a43'
PINS = {
    'src/main.cpp': '006bce2fb2420aef19f8480fdc8ac3481057928f',
    'inc/kyiv.h': '1b8b87a5539af31dc773db7a9633b24e971febd5',
    'docs/ISA_07_D12B_IO24_DECISION_LEDGER.tsv': 'bd52e9a708f5c18480fe12e805e34e8a080e7c87',
    'tests/isa/isa07_d8b_absolute_output_probe.cpp': '756ccb35ee1ee2774474ebc59c9a736049f1cda3',
    'tools/isa07_d12b_regression_gate.py': 'f15114755c6fe286be4b46529a0187d98a13fde7',
}
NEW = (
    'docs/ISA_07_D13A_IO23_HOST_CHARACTERIZATION.md',
    'docs/ISA_07_D13A_IO23_RISK_LEDGER.tsv',
    'tests/isa/isa07_d13a_io23_host_observation_probe.cpp',
    'tools/isa07_d13a_io23_host_sandbox.py',
    'tools/isa07_d13a_audit.py',
)
CONTENT_SHA = {'docs/ISA_07_D13A_IO23_HOST_CHARACTERIZATION.md': 'b0021e8a62d409d7df8b05aee73a1e3fce06cb9154882f939b89124fc702b85f', 'docs/ISA_07_D13A_IO23_RISK_LEDGER.tsv': 'f6ea6c9ca6344b280374c7d8d0c91da24f3d8c8b16621196bb0736f1d118e5fb', 'tests/isa/isa07_d13a_io23_host_observation_probe.cpp': 'f86d1883134cd6acda09b9879fc465b0f39f9818629c0712ff70e140d023770e', 'tools/isa07_d13a_io23_host_sandbox.py': '1e4e3492aa58b955b3e5be105aa6c04d997c321af8fc48b108bbce23fa37cdde'}

def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)

def normalized(data: bytes) -> bytes:
    require(b'\r' not in data.replace(b'\r\n', b''), 'BARE_CR_NOT_ALLOWED')
    return data.replace(b'\r\n', b'\n')

def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], stderr=subprocess.PIPE)

def main() -> int:
    try:
        require(git('rev-parse', '--show-prefix').strip() == b'', 'NOT_REPOSITORY_ROOT')
        require(git('rev-parse', 'HEAD').decode().strip() == BASE, 'UNEXPECTED_HEAD')
        require(not git('diff', '--name-only').strip(), 'TRACKED_MUTATION')
        require(not git('diff', '--cached', '--name-only').strip(), 'STAGED_MUTATION')
        untracked = set(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
        require(untracked == set(NEW), 'NEW_FILES_SCOPE_MISMATCH ' + repr(untracked ^ set(NEW)))
        for path, sha in PINS.items():
            require(git('rev-parse', 'HEAD:' + path).decode().strip() == sha,
                    'BASE_BLOB_MISMATCH ' + path)
            require(normalized(Path(path).read_bytes()) == normalized(git('show', 'HEAD:' + path)),
                    'WORKTREE_PIN_MISMATCH ' + path)
        for path, sha in CONTENT_SHA.items():
            require(hashlib.sha256(normalized(Path(path).read_bytes())).hexdigest() == sha,
                    'NEW_FILE_SHA_MISMATCH ' + path)
        probe = normalized(Path('tests/isa/isa07_d13a_io23_host_observation_probe.cpp').read_bytes())
        runner = normalized(Path('tools/isa07_d13a_io23_host_sandbox.py').read_bytes())
        require(probe.count(b'execute_opcode()') == 3, 'REAL_CPU_STEP_COUNT')
        require(len(re.findall(rb'^    Case\(', runner, re.M)) == 20, 'CASE_MATRIX_NOT_20')
        source = normalized(git('show', 'HEAD:src/main.cpp')).decode()
        a = source.index('case IO_operations_t::opcode_write_magnetic_drum:{')
        b = source.index('case IO_operations_t::opcode_init_magnetic_drum:', a)
        handler = source[a:b]
        require('myfile.open("../magnetic_drum.txt")' in handler and
                'word_to_number(kmem.read_memory(i))' in handler and
                'C_reg = addr3_shifted.destination' in handler and
                'drum_num_write' not in handler and 'drum_zone_write' not in handler,
                'UNEXPECTED_IO23_HANDLER')
        require('std::ofstream myfile' in handler and 'Unable to open file' in handler,
                'IO23_HOST_ERROR_NOT_QUALIFIED')
        subprocess.run(['git', 'diff', '--check'], check=True)
        require(len(NEW) == 5 and len(CONTENT_SHA) == 4, 'FILE_COVERAGE')
        print('D13A-AUDIT PASS BASELINE=f7c2b40 PINS=5/5 NEW_FILES=5/5 '
              'CONTENT_SHA=4/4 CASE_MATRIX=20/20 CPU_MUTATION=0 '
              'IO23_OUTPUT_OBSERVATION=1 EOL_PORTABLE=1 '
              'SHARED_DRUM_MODEL=DEFERRED HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (OSError, RuntimeError, ValueError, UnicodeError, subprocess.CalledProcessError) as err:
        print('D13A-AUDIT FAIL', err, file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
