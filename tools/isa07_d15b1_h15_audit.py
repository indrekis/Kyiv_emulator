#!/usr/bin/env python3
"""D15/B1-H15 immutable historical image and exact Git-scope auditor."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess
BASE='90c8340b3c957707ea6586bdeaff352d492ccbb4';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204.k41';PROV='examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204_provenance.tsv'
NEW=['docs/ISA_07_D15B1_H15_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H15_NEGATIVE_ROUNDED_MULTIPLY.md', 'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204.k41', 'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204_provenance.tsv', 'tools/isa07_d15b1_h15_audit.py', 'tools/isa07_d15b1_h15_native.py'];PINS={'examples/historical/gy1962/README.md': '6253d886f19115561fda9df7ee39a95de9e0d8b9', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4', 'examples/historical/gy1962/au1_addition_0143_0150.k41': '2596703fe167ca2d990717d7cd051c1f822378ff', 'examples/historical/gy1962/au1_addcyc_0151_0154.k41': 'c28ef4d4f4f474442d8bc0d104551886d9b1f80c', 'examples/historical/gy1962/au1_subtraction_0155_0162.k41': '3428a04652d6f9a8ee070138a183b158406175d2', 'examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv': '9c7737f526d313eef8243a4a4de592059d53f5af', 'docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv': 'ef6ae41bae4075caddd292a4c11e537a86cc0218', 'docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md': '01cb2d553c1d97f6426c3adb16b3683250e97464', 'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md': '2ed71f86671bab99d456bcbe1426f67c60407310', 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1', 'docs/ISA_07_D15B1_H12_ADDCMD_SIGN.md': '2aedc98670e193e7ebdda887d245b411b971051c', 'docs/ISA_07_D15B1_H12_DECISION_LEDGER.tsv': '37284e5a5a818d9c03aad8d1124b80839047f4ac', 'examples/historical/gy1962/au1_addcmd_0163_0165.k41': '60beab5d65e6f3c4af412971ee88e4bf9b89fd70', 'examples/historical/gy1962/au1_addcmd_0163_0165_provenance.tsv': '9a7f3c4537174e116f99d4405a11bb00ea331041', 'examples/historical/gy1962/au1_shift_zero_0166_0170.k41': '6b3fe5cefe09218ee1a65979f5df88c22f0d6012', 'examples/historical/gy1962/au1_shift_zero_0166_0170_provenance.tsv': '22b9ed96ad6cd6e89be45be4263bc92eeffed277', 'docs/ISA_07_D15B1_H13_DECISION_LEDGER.tsv': '639cb1308df041b3de081a27bda4f7e69a59ab01', 'docs/ISA_07_D15B1_H13_ZERO_SHIFT.md': '9269aedfee849505dcae8f6d2628ab1dc4094767', 'tools/isa07_d15b1_h13_audit.py': '78264991c1bf003378d860934dbee2cafa05fdb1', 'tools/isa07_d15b1_h13_native.py': 'b797b1a3bb7931baa3b55a953bcce7f1d8f63e04', 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201.k41': 'a599eff8e18fa86c3d57687992d1fcd87d481f74', 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201_provenance.tsv': 'df4ad2f5a52064885f14b7774d9743091047d818', 'docs/ISA_07_D15B1_H14_DECISION_LEDGER.tsv': '82790ccbf2836e22b9054e11aa44c93ef99c2adf', 'docs/ISA_07_D15B1_H14_ROUNDED_MULTIPLICATION_OBSERVATION.md': 'c557df023d05265d05f0ddc2ecc5f3839136458d', 'tools/isa07_d15b1_h14_audit.py': '00f2683622a364429631569bf4574cfacee69fe4', 'tools/isa07_d15b1_h14_native.py': 'f8cff402120bf6137cf5d80cef128fafc4a087bf'};WORDS={'0004': '05252525252525', '0005': '32525252525252', '0025': '23434343434343', '0202': '11000400050347', '0203': '16034700250205', '0204': '33000000000000'};SHA={'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204.k41': 'b33ffdba7d8a47e28a6d5c69d82fd4386d599651c03e4823228264173c9e0fd5', 'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204_provenance.tsv': '1bfd35c3b65f5248cc61da99ce21327d5a47be35e34cbf5228066964f4d2296f', 'docs/ISA_07_D15B1_H15_NEGATIVE_ROUNDED_MULTIPLY.md': '6cf320836bb8569c084bb1b7e36a35dbfea0d25768c7bc5898d7b137d5dafa4e', 'docs/ISA_07_D15B1_H15_DECISION_LEDGER.tsv': '189a5d87f300efbc9d82b87771fb7561cecbb844c016dba0cfe9fb3854522f2f'};README_SHA='101add34912610a6f8ab5a3c26004bd5e8a0cf05dea00e7ee38df8751dbe33fb';APPEND='\n## AU test I, negative rounded multiplication at 0202–0204 (D15/B1-H15)\n\n- `au1_rounded_multiply_negative_0202_0204.k41` contains six verbatim\n  first-visual-source words: RAM operands `0004`, `0005`, expected code\n  `0025` (GY1962 printed p. 172), and instructions `0202`, `0203`,\n  `0204` (printed p. 173). These are *octal* addresses and raw 41-bit words.\n- Original opcode `11`: `0004 × 0005 → 0347`. Sign is negative, and\n  the independent sign-magnitude rounded prediction matches source\n  `0025=23434343434343` exactly. Opcode `16` jumps to `0205` on equality.\n  **Never execute the command at `0205`** in this H15 stage.\n- Historical failure STOP `0204` is verified on a private copy with\n  retargeted JE source operand `0025→0004`; neither source multiplication\n  nor the STOP is modified; private images must not be committed.\n- Two separate working-directory runs check exact input cells, all 41\n  result bits, control-flow and STOP: six native cases total. This is\n  software qualification, not physical machine evidence.\n- CPU, ROM, H1–H14 canonical images and prior issues H9/H10/H11/H13/H14\n  remain unchanged. A second independent human transcription and a\n  real-hardware oracle remain pending.\n\n```sh\ng++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h15_kyivemu.exe\npython -B tools/isa07_d15b1_h15_native.py --cli-exe tempkyiv/d15b1h15_kyivemu.exe --timeout 20\n```\n';EXPECTED='23434343434343'

def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode('utf-8').rstrip('\n')
def norm(b):
 assert b'\r' not in b.replace(b'\r\n',b'\n'),'STRAY_CR'
 return b.replace(b'\r\n',b'\n')
def recs(data):
 x=[line.split() for line in data.decode('ascii').splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',line)]
 assert len(x)==len(WORDS),'DUPLICATE_OR_MISSING_WORDS'
 return dict(x)
def selftest():
 assert len(PINS)==32 and all(re.fullmatch('[0-9a-f]{40}',v) for v in PINS.values()),'GIT_PIN_WIDTH'
 assert len(WORDS)==6 and len(NEW)==6 and len(SHA)==4,'SHAPE'
 assert recs(('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in WORDS.items())+'\n').encode())==WORDS
 assert WORDS['0202']=='11000400050347' and WORDS['0203']=='16034700250205'
 assert WORDS['0204']=='33000000000000' and WORDS['0025']==EXPECTED
 m=(1<<40)-1; a=int(WORDS['0004'],8);b=int(WORDS['0005'],8)
 assert a<m and b>(1<<40) and f'{((a&m)*(b&m)+(1<<39))>>40|(1<<40):014o}'==EXPECTED
 mutant=dict(WORDS);mutant['0202']='11000400040347'
 assert mutant!=WORDS and mutant['0202']!=WORDS['0202'],'MUTANT_REJECTED'
 print('D15B1H15-AUDIT-SELFTEST PASS WORDS=6/6 MUTANTS_REJECTED=1 CRLF=1 GIT_PIN_WIDTH=32/32 NEGATIVE_ROUNDED_PRODUCT=1')
def audit():
 root=pathlib.Path(__file__).resolve().parent.parent
 assert git('rev-parse','HEAD')==BASE,'WRONG_BASE'
 assert git('branch','--show-current')=='main' and not git('rev-parse','--show-prefix'),'NOT_MAIN_ROOT'
 want={' M '+README}|{'?? '+p for p in NEW}
 got=set(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert got==want,('WORKTREE_SCOPE',sorted(got),sorted(want))
 for p,s in PINS.items():assert git('rev-parse','HEAD:'+p)==s,('SOURCE_PIN',p)
 r=norm((root/README).read_bytes())
 assert hashlib.sha256(r).hexdigest()==README_SHA and r.endswith(APPEND.encode()),'README_APPEND_SHA'
 for p,s in SHA.items(): assert hashlib.sha256((root/p).read_bytes()).hexdigest()==s,('CONTENT_SHA',p)
 assert recs((root/IMAGE).read_bytes())==WORDS,'HISTORICAL_WORDS'
 rows=(root/PROV).read_text('ascii').splitlines()
 assert len(rows)==7 and rows[0]=='address\tcode_octal_14\tprinted_page\trole\tverification','PROVENANCE_SHAPE'
 for (a,w),row in zip(WORDS.items(),rows[1:]):
  v=row.split('\t');assert len(v)==5 and v[:2]==[a,w] and v[2]==('172' if int(a,8)<0o202 else '173') and v[4]=='VISUAL_FIRST_PASS',('PROVENANCE',a)
 print('D15B1H15-AUDIT PASS BASELINE='+BASE[:7]+' MOD=1/1 NEW=6/6 WORDS=6/6 PROGRAM=3 DATA=3 SOURCE_PINS=32/32 CONTENT_SHA=4/4 NEGATIVE_ROUNDED_PRODUCT=1 BOUNDARY_0205_NOT_EXECUTED=1 H9_H10_H11_H13_H14_CONFLICTS=OPEN_UNCHANGED CPU_MUTATION=0 ROM_IMMUTABLE=1 PRIOR_IMAGES_IMMUTABLE=1 NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');args=p.parse_args()
 try:selftest();None if args.self_test else audit()
 except BaseException as e:raise SystemExit('D15B1H15-AUDIT FAIL '+repr(e))
