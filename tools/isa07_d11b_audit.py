#!/usr/bin/env python3
"""D11-B: pinned exact IO21-only substitution, read-only repository audit."""
from pathlib import Path
import hashlib
import subprocess
import sys

BASE='707cdf7ef72467e305056c0ff22d6582d16c8f76'
CPU_SHA='e6d00248705668156c29b376b3dd1b26ed40e275'
PINS={
 'inc/kyiv.h':'ff4aa592f12b07d32b4961b49cb97b15289d38e0',
 'inc/kyiv_decimal_input_plan.h':'a38b137291c7e218bf9d81c5eebfcc6ac9d3b6a3',
 'inc/kyiv_decimal_trunc.h':'e6ab074335a2337de3a5b0eadd3bf46adf0b09fe',
 'inc/kyiv_decimal_ascii.h':'e92fda12785ea2ed79a215461003a13eb85fb076',
}
NEW=(
 'inc/kyiv_binary_input_plan.h',
 'docs/ISA_07_D11B_IO21_ATOMIC_RAW_WORD_INPUT.md',
 'tests/isa/isa07_d11b_input_plan_probe.cpp',
 'tests/isa/isa07_d11b_io21_cpu_probe.cpp',
 'tools/isa07_d11b_input_plan_sandbox.py',
 'tools/isa07_d11b_io21_cpu_sandbox.py',
 'tools/isa07_d11b_regression_gate.py',
 'tools/isa07_d11b_audit.py',
)
# Replaced at package build time: exact LF-normalized content digests.
NEW_SHA={'inc/kyiv_binary_input_plan.h': '44713ffcf6098cf1602979ccc2c41891d1519af018f9fd44ff2312e5b099faa1', 'docs/ISA_07_D11B_IO21_ATOMIC_RAW_WORD_INPUT.md': 'dcee927f0f025f63de316511b63bcd7a6e3a02d29559a6e6e5d989ce9df98a30', 'tests/isa/isa07_d11b_input_plan_probe.cpp': '5c987c892869ead0b75e7173685a703058a22bc24ab687cb4ecd24803e9cf5c9', 'tests/isa/isa07_d11b_io21_cpu_probe.cpp': 'c9c6d7178d87e73b8a5bb96087230276f3c87acbfd0f50e919cb1ce76baf480d', 'tools/isa07_d11b_input_plan_sandbox.py': '18f9c13ec7225f86c88e0502512e1a79fe81fbbb04eb3de9c63ac33621660617', 'tools/isa07_d11b_io21_cpu_sandbox.py': '918425051f50ec7cf5c89678112be24b2be2388dcb06d30a80994476e347f699', 'tools/isa07_d11b_regression_gate.py': '9cfdcd575ddb9733d280a112af3acbf9c36506e5e8116b41ce124c3e809322ce'}

def git(*args):
    return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().strip()

def req(value,message):
    if not value:raise RuntimeError(message)

def canonical_bytes(content,label):
    req(b'\r' not in content.replace(b'\r\n',b''),'bare CR '+label)
    return content.replace(b'\r\n',b'\n')

def canonical(path):
    return canonical_bytes(Path(path).read_bytes(),path)

def main():
    try:
        req(git('rev-parse','--show-prefix')=='','not repository root')
        req(git('rev-parse','HEAD')==BASE,'wrong committed D11-A HEAD')
        req(git('rev-parse','HEAD:src/main.cpp')==CPU_SHA,'CPU blob drift')
        for p,sha in PINS.items():
            req(git('rev-parse','HEAD:'+p)==sha,'baseline pin mismatch '+p)
        req(set(git('diff','--name-only','HEAD','--').splitlines())=={'src/main.cpp'},
            'unexpected tracked changes')
        req(not git('diff','--cached','--name-only','--'),'staged source changes not allowed')
        for p in NEW:
            req(Path(p).is_file(),'missing new file '+p)
            req(not git('ls-files','--',p),'new file unexpectedly tracked '+p)
            contents=canonical(p)
            if p in NEW_SHA:
                req(hashlib.sha256(contents).hexdigest()==NEW_SHA[p],
                    'new content hash mismatch '+p)
        baseline=canonical_bytes(subprocess.check_output(
            ['git','show','HEAD:src/main.cpp']), 'HEAD:src/main.cpp')
        original=ORIGINAL_BLOCK.encode('utf-8')
        replacement=REPLACEMENT_BLOCK.encode('utf-8')
        req(baseline.count(original)==1,'original IO21 block not unique')
        include=b'#include "kyiv_decimal_input_plan.h"\n'
        req(baseline.count(include)==1,'include anchor absent or repeated')
        expected=baseline.replace(include,include+b'#include "kyiv_binary_input_plan.h"\n',1)
        expected=expected.replace(original,replacement,1)
        req(canonical('src/main.cpp')==expected,'CPU delta exceeds exact IO21 block/include')
        doc=canonical(NEW[1]).decode('utf-8')
        for marker in ('SOURCE_STRICT','HOST_POLICY','GY62','p.58','41-bit',
                       'atomic','D11-A','IO20','IO22','OPEN'):
            req(marker.casefold() in doc.casefold(),'document missing '+marker)
        probe=canonical(NEW[3]).decode('utf-8')
        for marker in ('execute_opcode()', '02000','pc1','h1','guard','unchanged','second'):
            req(marker in probe,'CPU probe contract missing '+marker)
        req(len(NEW)==8 and len(NEW_SHA)==7, 'scope count error')
        print('D11B-AUDIT PASS BASELINE=707cdf7 CPU_BLOB_PIN=1 PINS=4/4 '
              'IO21_ONLY=1 INCLUDE_ONLY=1 NEW_FILES=8/8 CONTENT_SHA=7/7 '
              'OTHER_IO_UNCHANGED=1 EOL_PORTABLE=1 HOST_POLICY=1 HARDWARE_ORACLE=0')
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as e:
        print('D11B-AUDIT FAIL:',e,file=sys.stderr)
        return 1

# ORIGINAL/REPLACEMENT are sealed into the delivered package by builder.
ORIGINAL_BLOCK='case IO_operations_t::opcode_read_perfo_binary:{\n            std::ifstream punch_cards;\n            std::ifstream heads;\n            std::string head;\n            std::string line;\n\n            punch_cards.open("../punched_tape.txt");\n            heads.open("../heads.txt");\n\n            std::getline(heads, head);\n            std::getline(heads, head);\n            // int num = std::stoi(head);\n            size_t num = h;\n            int counter = 0;\n            int com_counter = 0;\n            bool flag = false;\n\n            while(punch_cards){\n                std::getline(punch_cards, line);\n                int pos = 0;\n                if(counter == num){\n                    if(com_counter <= addr3_shifted.source_2 - addr3_shifted.source_1){\n                        kmem.write_memory(addr3_shifted.source_1 + com_counter, std::stol(line, 0, 8));\n                        com_counter++;\n                    }else{\n                        flag = true;\n                        break;\n                    }\n                }else if(counter > num){\n                    if(com_counter <= addr3_shifted.source_2 - addr3_shifted.source_1){\n                        kmem.write_memory(addr3_shifted.source_1 + com_counter, std::stol(line, 0, 8));\n                        com_counter ++;\n                    }else{\n                        flag = true;\n                        break;\n                    }\n\n                }\n                if(flag){\n                    break;\n                }\n                ++counter;\n            }\n            h += com_counter;\n            ++C_reg;\n            K_reg = kmem.read_memory(C_reg);\n        }\n            break;\n'
REPLACEMENT_BLOCK='case IO_operations_t::opcode_read_perfo_binary:{\n            // D11-B: strict raw 41-bit OCTAL text is HOST_POLICY, not the\n            // encoding of real perforated tape. Validate the entire command\n            // before writing a single destination cell or changing C/K/h.\n            if (addr3_shifted.source_1 > addr3_shifted.source_2)\n                throw std::runtime_error("IO21: INVALID_INTERVAL");\n            // Physical Kyiv RAM: 0000..1777 octal. Cell zero discards writes.\n            if (addr3_shifted.source_2 >= 02000ULL)\n                throw std::runtime_error("IO21: INVALID_RAM_ADDRESS");\n            const std::size_t count = static_cast<std::size_t>(\n                addr3_shifted.source_2 - addr3_shifted.source_1 + 1);\n            std::ifstream punch_cards("../punched_tape.txt",\n                                    std::ios::in | std::ios::binary);\n            const auto staged = kyiv_binary_input_plan::collect(\n                punch_cards, static_cast<std::size_t>(h), count);\n            if (staged.state != kyiv_binary_input_plan::status::exact)\n                throw std::runtime_error(std::string("IO21: ") +\n                    kyiv_binary_input_plan::status_text(staged.state));\n            for (std::size_t i = 0; i < staged.words.size(); ++i)\n                kmem.write_memory(addr3_shifted.source_1 + i, staged.words[i]);\n            h += staged.words.size(); // host physical-line cursor policy\n            // GY62 printed p.58: C+1 -> C and memory[C] -> K.\n            ++C_reg;\n            K_reg = kmem.read_memory(C_reg);\n        }\n            break;\n'
if __name__=='__main__':sys.exit(main())
