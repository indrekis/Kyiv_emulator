#!/usr/bin/env python3
"""D12-B read-only audit: full baseline Git blob pins, only IO24 CPU delta."""
from __future__ import annotations
from pathlib import Path
import hashlib
import subprocess
import sys

BASE='afc4ad9279c75ecb2a0af7583ec6625847640dca'
PINS={
    'src/main.cpp':'80de2590770966cc80cb812d5cc6e3c0afa6e8ea',
    'inc/kyiv.h':'1b8b87a5539af31dc773db7a9633b24e971febd5',
    'inc/kyiv_binary_input_plan.h':'a73fd6fe097ad46078bd1626c760a3f7c7d3a890',
    'docs/ISA_07_D12A_IO24_HOST_CHARACTERIZATION.md':'b39aa6c038d5f9ba1004a796befcc3d54f2487d3',
    'tools/isa07_d11b_regression_gate.py':'2e6a79a53e837e15388dc0e7fcb6526c78e26780',
}
NEW=(
    'docs/ISA_07_D12B_IO24_ATOMIC_DECIMAL_HOST_INPUT.md',
    'docs/ISA_07_D12B_IO24_DECISION_LEDGER.tsv',
    'inc/kyiv_drum_input_plan.h',
    'tests/isa/isa07_d12b_input_plan_probe.cpp',
    'tests/isa/isa07_d12b_io24_cpu_probe.cpp',
    'tools/isa07_d12b_input_plan_sandbox.py',
    'tools/isa07_d12b_io24_cpu_sandbox.py',
    'tools/isa07_d12b_regression_gate.py',
    'tools/isa07_d12b_audit.py',
)
CONTENT_SHA={'docs/ISA_07_D12B_IO24_ATOMIC_DECIMAL_HOST_INPUT.md': 'f15f766d20e47552422602d8d9bc7c1f48e5d8fd8c2cb74221f262a2465c9ab8', 'docs/ISA_07_D12B_IO24_DECISION_LEDGER.tsv': '89bb09ab64a5d8419314e896bb8de9f9f1c381bf136d820b4099499d53d85dd8', 'inc/kyiv_drum_input_plan.h': '1f02822897ec16debb66dec65e03c86de3e155159f2d6f591ea68c1ef1774841', 'tests/isa/isa07_d12b_input_plan_probe.cpp': '45a75317d37970c048507e73ae5301a69b24ede3d12dc4ba5e195625c4de22c1', 'tests/isa/isa07_d12b_io24_cpu_probe.cpp': '76ec63c44a68b9ef49372e35b38a675f611b01f99ba92252c1a5ee4acb4da26f', 'tools/isa07_d12b_input_plan_sandbox.py': '94d9bf775200753d7f3c275e17429774dbb4e5c832c610bd605ff55999013ecf', 'tools/isa07_d12b_io24_cpu_sandbox.py': '43516da54ca88cd59ce4016e8639f1a8b42badf9426c40e320629f204d59b38c', 'tools/isa07_d12b_regression_gate.py': '990eb39bbde7a9921826021ab69bfbf9d17e4fe90e4e66eb70e72bed140e4d78'} # Pinned LF-normalized bytes of all non-auditor new files.
START='        case IO_operations_t::opcode_read_magnetic_drum:{'
END='        case IO_operations_t::opcode_write_perfo_binary:{'
INCLUDE='#include "kyiv_binary_input_plan.h"\n'
INCLUDE_NEW='#include "kyiv_binary_input_plan.h"\n#include "kyiv_drum_input_plan.h"\n'
NEW_IO24='''        case IO_operations_t::opcode_read_magnetic_drum:{
            // D12-B: decimal host text is NOT historical drum encoding.
            // Check the entire input before any memory/control-state change.
            if (addr3_shifted.source_1 > addr3_shifted.source_2)
                throw std::runtime_error("IO24: INVALID_INTERVAL");
            if (addr3_shifted.source_2 >= 02000ULL)
                throw std::runtime_error("IO24: INVALID_RAM_ADDRESS");
            if (drum_num_read < 0)
                throw std::runtime_error("IO24: INVALID_TRACK");
            if (drum_zone_read < 0)
                throw std::runtime_error("IO24: INVALID_ZONE");
            const std::size_t count = static_cast<std::size_t>(
                addr3_shifted.source_2 - addr3_shifted.source_1 + 1);
            std::ifstream magnetic_drum("../../mem/drum_in.txt",
                                        std::ios::in | std::ios::binary);
            const auto staged = kyiv_drum_input_plan::collect(
                magnetic_drum, static_cast<std::size_t>(drum_num_read),
                static_cast<std::size_t>(drum_zone_read), count);
            if (staged.state != kyiv_drum_input_plan::status::exact)
                throw std::runtime_error(std::string("IO24: ") +
                    kyiv_drum_input_plan::status_text(staged.state));
            for (std::size_t i = 0; i < staged.words.size(); ++i)
                kmem.write_memory(addr3_shifted.source_1 + i, staged.words[i]);
            // GY62 p.15: branch to a3; prefetch K is emulator convention.
            C_reg = addr3_shifted.destination;
            K_reg = kmem.read_memory(C_reg);
        }
            break;

'''

def require(cond,msg):
    if not cond: raise RuntimeError(msg)

def normalize(data:bytes)->bytes:
    require(b'\r' not in data.replace(b'\r\n',b''),'BARE_CR_NOT_ALLOWED')
    return data.replace(b'\r\n',b'\n')

def expected(base:bytes)->bytes:
    text=normalize(base).decode('utf-8')
    require(text.count(INCLUDE)==1,'INCLUDE_ANCHOR_MISMATCH')
    require(text.count(START)==1 and text.count(END)==1,'IO24_BOUNDARY_MISMATCH')
    start=text.index(START);end=text.index(END)
    require(start<end,'IO24_BOUNDARY_ORDER')
    old=text[start:end]
    require(old.count('std::stoi(num)')==2 and
            old.count('C_reg = addr3_shifted.destination;')==1 and
            'num_counter' in old,'IO24_OLD_HANDLER_NOT_QUALIFIED')
    text=text[:start]+NEW_IO24+text[end:]
    text=text.replace(INCLUDE,INCLUDE_NEW,1)
    return text.encode('utf-8')

def git(*args):
    return subprocess.check_output(['git',*args],stderr=subprocess.PIPE)

def main():
    try:
        require(git('rev-parse','--show-prefix').strip()==b'','RUN_FROM_REPO_ROOT')
        require(git('rev-parse','HEAD').strip().decode()==BASE,'UNEXPECTED_HEAD')
        require(not git('diff','--cached','--name-only').strip(),'STAGED_CHANGES')
        require(git('diff','--name-only').decode().splitlines()==['src/main.cpp'],
                'TRACKED_SCOPE_NOT_IO24_ONLY')
        untracked=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
        require(untracked==set(NEW),'NEW_FILES_SCOPE_MISMATCH '+repr(untracked^set(NEW)))
        for path,sha in PINS.items():
            require(git('rev-parse',f'HEAD:{path}').decode().strip()==sha,'PIN_MISMATCH '+path)
            base=git('show',f'HEAD:{path}')
            check=Path(path).read_bytes()
            desired=expected(base) if path=='src/main.cpp' else normalize(base)
            require(normalize(check)==desired,'CONTENT_NOT_EXACT '+path)
        for path,sha in CONTENT_SHA.items():
            require(hashlib.sha256(normalize(Path(path).read_bytes())).hexdigest()==sha,
                    'NEW_FILE_SHA_MISMATCH '+path)
        require(len(NEW)==9 and len(CONTENT_SHA)==8,'NEW_FILE_COVERAGE')
        subprocess.run(['git','diff','--check'],check=True)
        print('D12B-AUDIT PASS BASELINE=afc4ad9 PINS=5/5 IO24_ONLY=1 '
              'INCLUDE_ONLY=1 NEW_FILES=9/9 CONTENT_SHA=8/8 '
              'OTHER_IO_ARITHMETIC_UNCHANGED=1 EOL_PORTABLE=1 '
              'HOST_POLICY=1 HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (OSError,UnicodeError,ValueError,RuntimeError,subprocess.CalledProcessError) as e:
        print('D12B-AUDIT FAIL',e,file=sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
