#!/usr/bin/env python3
"""Independent read-only exact-source D13-B audit; never adjusts source."""
from pathlib import Path
import hashlib
import subprocess
import sys

BASE='506cfec97bfbedc6da6e9a0717ca4eb525edb067'
PINS={'src/main.cpp': '006bce2fb2420aef19f8480fdc8ac3481057928f', 'inc/kyiv.h': '1b8b87a5539af31dc773db7a9633b24e971febd5', 'docs/ISA_07_D13A_IO23_HOST_CHARACTERIZATION.md': 'aae02b0626a37fdeafc8a894c57c3082495e2832', 'tests/isa/isa07_d13a_io23_host_observation_probe.cpp': '682b5acdf3e2ef21ceb3b0662a1418cc208726c8', 'tools/isa07_d12b_regression_gate.py': 'f15114755c6fe286be4b46529a0187d98a13fde7'}
NEW=('docs/ISA_07_D13B_IO23_ATOMIC_HOST_OUTPUT.md', 'docs/ISA_07_D13B_IO23_DECISION_LEDGER.tsv', 'inc/kyiv_drum_output_plan.h', 'tests/isa/isa07_d13b_output_plan_probe.cpp', 'tests/isa/isa07_d13b_io23_cpu_probe.cpp', 'tools/isa07_d13b_output_plan_sandbox.py', 'tools/isa07_d13b_io23_cpu_sandbox.py', 'tools/isa07_d13b_regression_gate.py', 'tools/isa07_d13b_audit.py')
CONTENT_SHA={'docs/ISA_07_D13B_IO23_ATOMIC_HOST_OUTPUT.md': '6c154a35a9821b9d98b5ee1029ddc8bb7b791c60dcb7acf1ec5b37ee552998dc', 'docs/ISA_07_D13B_IO23_DECISION_LEDGER.tsv': 'd02a48315040e3c6cd0d46e2d5295f25ccbe53d23ca46cb4d37044bb50c3bca2', 'inc/kyiv_drum_output_plan.h': '2e42b1cdeec9108baeaefeea1f2c011b06b137d333ea17d0808b562abce2663e', 'tests/isa/isa07_d13b_output_plan_probe.cpp': 'e9a2e9e73be6d5bbf68cef77cf48db245ec58158b66f358617212040dc376950', 'tests/isa/isa07_d13b_io23_cpu_probe.cpp': '7779037a565178eb7fb0e4fe864528cff8278f9c71caf6f2444acee1e59a99e6', 'tools/isa07_d13b_output_plan_sandbox.py': 'eaa819b1eb0b0ac4d59210eb6998b8d509d44c1d5f75d2fb801c637a18326172', 'tools/isa07_d13b_io23_cpu_sandbox.py': '5d7e1b0edc9b08066e418776d240bfba4eabb976601085f0f1d5a59652b5a1d9', 'tools/isa07_d13b_regression_gate.py': '36363366febadc3a9f16888f4dd1c027b106ba5c198fc06e7bcfe27d115e7f72'}
OLD_IO23='        case IO_operations_t::opcode_write_magnetic_drum:{\n            std::ofstream myfile;\n            myfile.open("../magnetic_drum.txt");\n            if (myfile.is_open())\n            {\n                for(uint64_t i = addr3_shifted.source_1; i <= addr3_shifted.source_2; i++){\n                    myfile << word_to_number(kmem.read_memory(i));\n                    myfile << \' \';\n                }\n                myfile.close();\n            }else {\n                std::cout << "Unable to open file";\n            }\n            C_reg = addr3_shifted.destination;\n            K_reg = kmem.read_memory(C_reg);\n        }\n            break;\n\n'
NEW_IO23='        case IO_operations_t::opcode_write_magnetic_drum:{\n            // D13-B: checked decimal HOST_POLICY, not historical drum encoding.\n            // Stage the complete payload before touching the destination file.\n            if (addr3_shifted.source_1 > addr3_shifted.source_2)\n                throw std::runtime_error("IO23: INVALID_INTERVAL");\n            if (addr3_shifted.source_2 >= 02000ULL)\n                throw std::runtime_error("IO23: INVALID_RAM_ADDRESS");\n            std::vector<std::uint64_t> words;\n            words.reserve(static_cast<std::size_t>(\n                addr3_shifted.source_2 - addr3_shifted.source_1 + 1));\n            for (addr_t i = addr3_shifted.source_1;\n                 i <= addr3_shifted.source_2; ++i)\n                words.push_back(kmem.read_memory(i));\n            const auto staged = kyiv_drum_output_plan::prepare(words);\n            if (staged.state != kyiv_drum_output_plan::status::exact)\n                throw std::runtime_error(std::string("IO23: ") +\n                    kyiv_drum_output_plan::status_text(staged.state));\n            const auto written = kyiv_drum_output_plan::commit(\n                "../magnetic_drum.txt", staged.bytes);\n            if (written != kyiv_drum_output_plan::status::exact)\n                throw std::runtime_error(std::string("IO23: ") +\n                    kyiv_drum_output_plan::status_text(written));\n            // GY62 p.15: branch a3; K prefetch is emulator convention.\n            C_reg = addr3_shifted.destination;\n            K_reg = kmem.read_memory(C_reg);\n        }\n            break;\n\n'
INCLUDE='#include "kyiv_drum_input_plan.h"\n'
NEW_INCLUDE='#include "kyiv_drum_input_plan.h"\n#include "kyiv_drum_output_plan.h"\n'

def require(value, why):
    if not value: raise RuntimeError(why)

def normalize(raw):
    require(b'\r' not in raw.replace(b'\r\n',b''), 'BARE_CR')
    return raw.replace(b'\r\n',b'\n')

def expected(base):
    data=normalize(base).decode('utf-8')
    require(data.count(INCLUDE)==1, 'INCLUDE_ANCHOR')
    require(data.count(OLD_IO23)==1, 'OLD_HANDLER_ANCHOR')
    require(data.count(NEW_IO23)==0, 'NEW_HANDLER_ALREADY_PRESENT')
    return data.replace(INCLUDE,NEW_INCLUDE,1).replace(OLD_IO23,NEW_IO23,1).encode('utf-8')

def git(*argv):
    return subprocess.check_output(['git',*argv],stderr=subprocess.PIPE)

def main():
    try:
        require(git('rev-parse','--show-prefix').strip()==b'', 'NOT_REPOSITORY_ROOT')
        require(git('rev-parse','HEAD').decode().strip()==BASE, 'WRONG_BASELINE')
        require(not git('diff','--cached','--name-only').strip(), 'STAGED_MUTATION')
        require(git('diff','--name-only').decode().splitlines()==['src/main.cpp'], 'TRACKED_SCOPE')
        actual=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
        require(actual==set(NEW), 'UNTRACKED_SCOPE '+repr(actual^set(NEW)))
        for p,blob in PINS.items():
            require(git('rev-parse','HEAD:'+p).decode().strip()==blob,'PIN_MISMATCH '+p)
            data=git('show','HEAD:'+p)
            wanted=expected(data) if p=='src/main.cpp' else normalize(data)
            require(normalize(Path(p).read_bytes())==wanted,'CONTENT_SCOPE '+p)
        for p,sha in CONTENT_SHA.items():
            require(hashlib.sha256(normalize(Path(p).read_bytes())).hexdigest()==sha,
                    'NEW_CONTENT_SHA '+p)
        require(len(NEW)==9 and len(CONTENT_SHA)==8, 'NEW_COVERAGE')
        subprocess.run(['git','diff','--check'],check=True)
        subprocess.run(['git','diff','--cached','--check'],check=True)
        print('D13B-AUDIT PASS BASELINE=506cfec PINS=5/5 IO23_ONLY=1 '
              'INCLUDE_ONLY=1 NEW_FILES=9/9 CONTENT_SHA=8/8 '
              'OTHER_IO_ARITHMETIC_UNCHANGED=1 EOL_PORTABLE=1 '
              'HOST_POLICY=1 HARDWARE_ORACLE=0 PDF_HASH_CHECKS=0')
        return 0
    except (RuntimeError,ValueError,UnicodeError,OSError,subprocess.CalledProcessError) as exc:
        print('D13B-AUDIT FAIL',str(exc),file=sys.stderr)
        return 1
if __name__=='__main__':raise SystemExit(main())
