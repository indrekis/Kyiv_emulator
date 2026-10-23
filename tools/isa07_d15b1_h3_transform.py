#!/usr/bin/env python3
"""D15/B1-H3 exact, LF-canonical, source-preserving opcode 17 transformation."""
from pathlib import Path
import re

CPU = 'src/main.cpp'
README = 'README.md'
DOC = 'documentation/documentation.txt'
REG = 'docs/isa_opcode_registry.csv'
D1_DOC = 'docs/ISA_06_D1_LOGIC_AUDIT.md'
D2_DOC = 'docs/ISA_06_D2_LOGIC_SEQUENCE.md'
EXAMPLE = 'examples/historical/gy1962/README.md'
D1_TEST = 'tests/isa/isa06_d1_logic_probe.cpp'
D2_TEST = 'tests/isa/isa06_d2_logic_sequence_probe.cpp'
MODIFIED = (CPU, README, DOC, REG, D1_DOC, D2_DOC, EXAMPLE, D1_TEST, D2_TEST)


def replace_exact(src: str, old: str, new: str, count=1) -> str:
    assert src.count(old) == count, ('ANCHOR_COUNT', repr(old[:120]), src.count(old), count)
    return src.replace(old, new)


def transform_text(path: str, s: str) -> str:
    if path == CPU:
        old = '            kmem.write_memory(addr3_shifted.destination, kmem.read_memory(addr3_shifted.source_1) ^ kmem.read_memory(addr3_shifted.source_2));'
        new = '''            // Octal 17: bitwise equivalence (XNOR), confirmed by the
            // GY1962 AU test (pp. 172-173) and DPS1964 table (p. 18).
            // GY1962 p. 11 instead describes XOR; see D15/B1-H2 ledger.
            // A host word is 64 bits, so discard all bits above bit 40.
            const word_t mask41 = (word_t{1} << 41) - 1;
            const word_t source_1 = kmem.read_memory(addr3_shifted.source_1);
            const word_t source_2 = kmem.read_memory(addr3_shifted.source_2);
            kmem.write_memory(addr3_shifted.destination,
                              (~(source_1 ^ source_2)) & mask41);'''
        s=replace_exact(s,old,new)
        assert s.count('case logic_operations_t::opcode_log_xor:{')==1
    elif path == README:
        old = [l for l in s.split('\n') if re.match(r'^\|\s+17\s+\|',l)]
        assert len(old)==1 and 'xor' in old[0].lower() and 'nonequivalence' in old[0].lower(), 'README_17_ROW'
        new = '|              17              | xor (legacy mnemonic) | bitwise equivalence (XNOR) | ~(k1 ^ k2) & ((1ULL << 41) - 1) => k3; sign bit included; C+1=>C | |'
        s=replace_exact(s,old[0],new)
        s+='''\n## Opcode 17 semantics (D15/B1-H3)\n\nOpcode `17` executes **bitwise equivalence (XNOR)** over all 41 bits,
including the sign bit: `(~(a ^ b)) & ((1ULL << 41) - 1)`. The legacy
assembler mnemonic `xor` remains accepted for compatibility, but is a
misleading historical mnemonic, **not** XOR execution. Glushkov and
Yushchenko (1962), printed p. 11, give an incompatible XOR definition;
their own logic diagnostic (pp. 172-173) and Dashevskii et al. (1964),
printed p. 18, support XNOR. See `docs/ISA_07_D15B1_H2_OPCODE17_SOURCE_ADJUDICATION.md`
and `docs/ISA_07_D15B1_H3_OPCODE17_CORRECTION.md`.\n
The unaltered historical machine image is in
`examples/historical/gy1962/au1_logic.k41`. Its earlier XOR-era run
(`CPU_STOP`, 19 steps, `C=0076`) is retained as a historical observation,
not a current PASS criterion.\n'''
    elif path == DOC:
        s=replace_exact(s,'17 - digital logical operation nonequivalence',
         '17 - bitwise equivalence (XNOR) of all 41 bits, including sign; (~(a ^ b)) & ((1ULL << 41) - 1)')
        s=replace_exact(s,'35 - normalization',
         'Note: opcode 17 was called inequivalence/XOR in GY1962 p. 11, but GY1962 diagnostic pp. 172-173 and DPS1964 p. 18 establish XNOR. The assembler mnemonic xor remains a legacy alias.\n35 - normalization')
    elif path == REG:
        s=replace_exact(s,'17,нерівнозначність,xor,вабо,логічні,',
         '17,нерівнозначність (опис ГЮ1962),xor,вабо,логічні,"D15/B1-H3: виконується XNOR (рівнозначність) у 41 біті; xor — застаріла мнемоніка; джерела 1962 с. 172-173 і 1964 с. 18; суперечність із описом 1962 с. 11"')
    elif path == D1_DOC:
        s=replace_exact(s,'# ISA-06 D1 — logical instructions: documentary audit and CPU characterization',
        '''# ISA-06 D1 — logical instructions: documentary audit and CPU characterization

> **Current opcode 17 correction (D15/B1-H3):** Execution is 41-bit **XNOR**
> (`~(a ^ b) & MASK41`), not XOR. The 1962 pp. 172-173 diagnostic and
> 1964 p. 18 truth table agree; the 1962 p. 11 XOR table is contrary
> evidence retained in `docs/ISA_07_D15B1_H2_OPCODE17_SOURCE_ADJUDICATION.md`.
> Historical D1 38/38 results below characterize the *former* XOR implementation.
> The D1 regression values have been updated for the corrected semantics.
''')
        s=replace_exact(s,'| `17` | non-equivalence | bitwise XOR of full 41-bit codes at I, II |',
                        '| `17` | equivalence (1964 p. 18; 1962 test pp. 172-173) | bitwise XNOR of full 41-bit codes at I, II, sign included; result masked to 41 bits |')
        s=replace_exact(s,'truth tables for logical OR, AND, XOR, and `13` shift',
                        'truth tables for logical OR, AND, **XNOR**, and `13` shift')
    elif path == D2_DOC:
        s=replace_exact(s,'# ISA-06 D2 — logical instruction sequencing and self-modifying RAM',
        '''# ISA-06 D2 — logical instruction sequencing and self-modifying RAM

> **D15/B1-H3 correction:** opcode 17 now performs masked 41-bit **XNOR**.
> The historic D2 run characterized the then-current XOR implementation;
> its assertions for opcode 17 were updated in H3 without changing the
> instruction-fetch or self-modifying-code contract. See H2 source ledger.
''')
        s=replace_exact(s,'source fields for OR/AND/XOR (including the sign bit).',
                        'source fields for OR/AND/XNOR (including the sign bit).')
    elif path == EXAMPLE:
        start='**Current observed result:** `CPU_STOP STEPS=19 C=0076`'
        stop='\nFor independent reproduction of the bounded observations and two work directories:'
        assert s.count(start)==1 and s.count(stop)==1, 'EXAMPLE_NOTE_ANCHORS'
        i=s.index(start); j=s.index(stop)
        s=s[:i]+'''**Original H1 observation on the XOR-era CPU (preserved evidence):**
`CPU_STOP STEPS=19 C=0076`, after running the historical STOP at address `0075`.
This documents a discrepancy, not a successful historical diagnostic.

**Current D15/B1-H3 correction:** opcode `17` now executes 41-bit **XNOR**.
The unchanged image is expected to reach `LIMIT STEPS=22 C=0107` with a
22-instruction budget when the updated CPU passes native qualification.
Do **not** execute `0107` as part of this bounded qualification: that command
uses the operator-settable NK cell `3000`. The original 1962 p. 11 XOR
truth table remains contrary primary evidence; DPS1964 printed p. 18 and the
1962 AU test pp. 172-173 support XNOR. This software behavior is not a
physical-hardware oracle. Independent second visual transcription is pending.
'''+s[j:]
        s=replace_exact(s,'python tools/isa07_d15b1_h1_native.py --cli-exe tempkyiv/kyivemu.exe --timeout 20',
                        'python tools/isa07_d15b1_h2_opcode17_probe.py --cli-exe tempkyiv/kyivemu.exe --expect xnor --timeout 20')
    elif path == D1_TEST:
        assert s.count('"17_xor_')==7, ('D1_OLD_CASE_COUNT',s.count('"17_xor_'))
        s=s.replace('"17_xor_','"17_xnor_')
        s=replace_exact(s,'{{2, SIGN | 074}, {3, SIGN | 012}}, 4, 066}',
                          '{{2, SIGN | 074}, {3, SIGN | 012}}, 4, (MASK41 ^ 066)}',count=2)
        s=replace_exact(s,'{{2, SIGN}, {3, 0}}, 4, SIGN}',
                          '{{2, SIGN}, {3, 0}}, 4, (MASK41 ^ SIGN)}')
        s=replace_exact(s,'{{2, SIGN}, {3, SIGN}}, 4, 0}',
                          '{{2, SIGN}, {3, SIGN}}, 4, MASK41}')
        s=replace_exact(s,'{{2, SIGN | 012}}, 2, 0}',
                          '{{2, SIGN | 012}}, 2, MASK41}')
        s=replace_exact(s,'// Characterization only: NO CPU modifications; no historical assertion from OBS.',
                          '// H3 regression: opcode 17 is 41-bit XNOR (DPS1964 p.18); OBS remain unqualified.')
    elif path == D2_TEST:
        s=replace_exact(s,'{{2, SIGN | 025}}, 2, 0);',
                          '{{2, SIGN | 025}}, 2, MASK41);')
        s=replace_exact(s,'src2_pc ^ (SIGN | 05)',
                          '(~(src2_pc ^ (SIGN | 05))) & MASK41')
        s=replace_exact(s,'''single("17_overwrite_current_instruction", 017, 2, 3, PC, 0,
           {{2, replacement}, {3, 0}}, PC, replacement);''',
         '''single("17_overwrite_current_instruction", 017, 2, 3, PC, 0,
           {{2, replacement}, {3, 0}}, PC, (MASK41 ^ replacement));''')
        s=replace_exact(s,'m.kmem.read_memory(7) == 037 && regs(m, 0);',
                          'm.kmem.read_memory(7) == (MASK41 ^ 037) && regs(m, 0);')
        s=replace_exact(s,'// No emulator changes, no claim of electrical-level timing qualification.',
                          '// H3: opcode 17 expected as masked XNOR; no electrical-level timing claim.')
    else:
        raise AssertionError(('UNSUPPORTED_MODIFIED_PATH',path))
    return s


def transform_bytes(path: str, original: bytes) -> bytes:
    assert path in MODIFIED, ('WRONG_MOD_PATH',path)
    count_crlf=original.count(b'\r\n')
    assert count_crlf == 0 or count_crlf == original.count(b'\n'), ('MIXED_LINE_ENDINGS',path)
    normalized = original.replace(b'\r\n', b'\n')
    assert b'\r' not in normalized, ('LONE_CR',path)
    out=transform_text(path,normalized.decode('utf-8')).encode('utf-8')
    assert out != normalized,('NO_CHANGE',path)
    return out.replace(b'\n',b'\r\n') if count_crlf else out
