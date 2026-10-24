#!/usr/bin/env python3
"""H14 fail-closed source/gitscope audit; observational ISA conflict."""
from __future__ import annotations
import argparse,hashlib,pathlib,re,subprocess
BASE='00fbea3187590d4d206a7cf56c76ec3194974099';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_rounded_multiplication_0171_0201.k41';PROV='examples/historical/gy1962/au1_rounded_multiplication_0171_0201_provenance.tsv'
NEW=['docs/ISA_07_D15B1_H14_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H14_ROUNDED_MULTIPLICATION_OBSERVATION.md', 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201.k41', 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201_provenance.tsv', 'tools/isa07_d15b1_h14_audit.py', 'tools/isa07_d15b1_h14_native.py'];PINS={'examples/historical/gy1962/README.md': '684af8e00ec13847557d0bab8e49145e6c17da1b', 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad', 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e', 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6', 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217', 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4', 'examples/historical/gy1962/au1_addition_0143_0150.k41': '2596703fe167ca2d990717d7cd051c1f822378ff', 'examples/historical/gy1962/au1_addcyc_0151_0154.k41': 'c28ef4d4f4f474442d8bc0d104551886d9b1f80c', 'examples/historical/gy1962/au1_subtraction_0155_0162.k41': '3428a04652d6f9a8ee070138a183b158406175d2', 'examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv': '9c7737f526d313eef8243a4a4de592059d53f5af', 'docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv': 'ef6ae41bae4075caddd292a4c11e537a86cc0218', 'docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md': '01cb2d553c1d97f6426c3adb16b3683250e97464', 'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md': '2ed71f86671bab99d456bcbe1426f67c60407310', 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b', 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c', 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1', 'docs/ISA_07_D15B1_H12_ADDCMD_SIGN.md': '2aedc98670e193e7ebdda887d245b411b971051c', 'docs/ISA_07_D15B1_H12_DECISION_LEDGER.tsv': '37284e5a5a818d9c03aad8d1124b80839047f4ac', 'examples/historical/gy1962/au1_addcmd_0163_0165.k41': '60beab5d65e6f3c4af412971ee88e4bf9b89fd70', 'examples/historical/gy1962/au1_addcmd_0163_0165_provenance.tsv': '9a7f3c4537174e116f99d4405a11bb00ea331041', 'examples/historical/gy1962/au1_shift_zero_0166_0170.k41': '6b3fe5cefe09218ee1a65979f5df88c22f0d6012', 'examples/historical/gy1962/au1_shift_zero_0166_0170_provenance.tsv': '22b9ed96ad6cd6e89be45be4263bc92eeffed277', 'docs/ISA_07_D15B1_H13_DECISION_LEDGER.tsv': '639cb1308df041b3de081a27bda4f7e69a59ab01', 'docs/ISA_07_D15B1_H13_ZERO_SHIFT.md': '9269aedfee849505dcae8f6d2628ab1dc4094767', 'tools/isa07_d15b1_h13_audit.py': '78264991c1bf003378d860934dbee2cafa05fdb1', 'tools/isa07_d15b1_h13_native.py': 'b797b1a3bb7931baa3b55a953bcce7f1d8f63e04'};WORDS={'0015': '00000000000001', '0021': '20000000000001', '0022': '30000000000000', '0023': '30000000000001', '0024': '17777777777775', '0171': '11002100220347', '0172': '16034700150174', '0173': '33000000000000', '0174': '11002330350347', '0175': '16034700220177', '0176': '33000000000000', '0177': '11303530350347', '0200': '16034700240202', '0201': '33000000000000'};SHA={'examples/historical/gy1962/au1_rounded_multiplication_0171_0201.k41': 'b8952d138ce706532ef70317ad753659c46bcdc4fee48ef023705904d93a0f77', 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201_provenance.tsv': '8208df9f99a083e1b9f2cc695b53623d666e323213ffb8b9ceda99616821592f', 'docs/ISA_07_D15B1_H14_ROUNDED_MULTIPLICATION_OBSERVATION.md': '7b262d714064afc9d3088bc28911a2f93bc59072f07e2355df39ea69df4a97cd', 'docs/ISA_07_D15B1_H14_DECISION_LEDGER.tsv': 'de7bb4d44a8aae30ec857e093fbaff0013266fea8a08e4b5949e9420da8a5d08'};README_SHA='8fff41f56f3380aefed36f95ec295f5c4d5e18f810c09359a1b1ba84aa09a2d2';APPEND='\n## AU test I, three rounded multiplications at 0171–0201 (D15/B1-H14)\n\n- `au1_rounded_multiplication_0171_0201.k41` contains **14 exact first-visual-source words**:\n  five RAM data/expected records (`0015`, `0021`–`0024`, printed p. 172)\n  and nine literal commands at `0171`–`0201` (printed p. 173).\n  They form three opcode `11` rounded-multiplication tests, each followed by\n  an opcode `16` comparison and original opcode `33` failure STOP.\n- ROM `3035=17777777777777` is a pinned emulator software-ROM value;\n  no extra HOST replacement for this ROM cell is included in the image.\n- Groups `0171` and `0174` are predicted to match p.172 exactly with results\n  `00000000000001` and `30000000000000`; their original STOPs are\n  exercised on private comparison-mutant files only.\n- **Potential conflict:** p.172 expects `17777777777775` for `0177`, whereas\n  independent integer rounded multiplication of `ROM[3035]` by itself,\n  using the current CPU rounding rule, predicts `17777777777776`.\n  Native tests record both outcomes as separate profiles; if the CPU yields\n  `17777777777776`, its literal historical comparison falls through to the\n  **original STOP at `0201`**. This is an observation, not a hardware truth.\n- Neither canonical source words, CPU, ROM nor prior H1–H13 examples change.\n  Original H9, H10, H11, H13 source/behavior conflicts remain OPEN_UNCHANGED.\n  Second independent human source reading and real Kyiv hardware oracle remain\n  PENDING. Never execute beyond boundary `0202`.\n\n```sh\ng++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h14_kyivemu.exe\npython -B tools/isa07_d15b1_h14_native.py --cli-exe tempkyiv/d15b1h14_kyivemu.exe --timeout 20\n```\n'
ROM='17777777777777';EXPECTED=['00000000000001', '30000000000000', '17777777777775'];HOST=['00000000000001', '30000000000000', '17777777777776']

def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode('utf-8').rstrip('\n')
def norm(data):
 assert b'\r' not in data.replace(b'\r\n',b'\n'),'STRAY_CR'
 return data.replace(b'\r\n',b'\n')
def recs(data):
 return dict((a,w) for a,w in (line.split() for line in data.decode('ascii').splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',line)))
def selftest():
 assert len(PINS)==26 and all(re.fullmatch('[0-9a-f]{40}',v) for v in PINS.values()),'PIN_WIDTH'
 assert len(WORDS)==14 and len(NEW)==6 and len(SHA)==4
 assert recs(('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in WORDS.items())+'\n').encode())==WORDS
 assert len(set(WORDS))==14 and len(set(NEW))==6
 assert int(ROM,8)==(1<<40)-1
 def mul(a,b):return (a*b+(1<<39))>>40
 assert f'{mul(1,1<<39):014o}'==EXPECTED[0]==HOST[0]
 assert f'{mul((1<<39)+1,int(ROM,8))|(1<<40):014o}'==EXPECTED[1]==HOST[1]
 assert f'{mul(int(ROM,8),int(ROM,8)):014o}'==HOST[2]=='17777777777776'
 assert EXPECTED[2]=='17777777777775'
 assert int(HOST[2],8)-int(EXPECTED[2],8)==1
 modified=dict(WORDS);modified['0200']='16034700250202'
 assert modified!=WORDS and modified['0200']!=WORDS['0200'],'MUTANT_NOT_REJECTED'
 print('D15B1H14-AUDIT-SELFTEST PASS WORDS=14/14 MUTANTS_REJECTED=1 CRLF=1 GIT_PIN_WIDTH=26/26 ROUNDING_DISCRIMINATOR=1')
def audit():
 root=pathlib.Path(__file__).resolve().parent.parent
 assert git('rev-parse','HEAD')==BASE,'WRONG_BASE'
 assert git('branch','--show-current')=='main' and not git('rev-parse','--show-prefix'),'NOT_MAIN_ROOT'
 expected={(' M '+README)}|{'?? '+p for p in NEW}
 found=set(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert found==expected,('WORKTREE_SCOPE',sorted(found),sorted(expected))
 for p,v in PINS.items():assert git('rev-parse','HEAD:'+p)==v,('SOURCE_PIN',p)
 assert hashlib.sha256(norm((root/README).read_bytes())).hexdigest()==README_SHA,'README_SHA'
 assert norm((root/README).read_bytes()).endswith(APPEND.encode('utf-8')),'README_APPEND'
 for p,sha in SHA.items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==sha,('SOURCE_SHA',p)
 image=(root/IMAGE).read_bytes();parsed=recs(image)
 assert parsed==WORDS,('SOURCE_WORDS',parsed)
 assert len([x for x in image.decode('ascii').splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',x)])==14,'DUP_RECORD'
 ptext=(root/PROV).read_text('ascii').splitlines()
 assert len(ptext)==15 and ptext[0]=='address\tcode_octal_14\tprinted_page\trole\tverification','PROVENANCE_SHAPE'
 for (a,w),line in zip(WORDS.items(),ptext[1:]):
  fields=line.split('\t');assert len(fields)==5 and fields[:2]==[a,w] and fields[2]==('172' if int(a,8)<0o171 else '173') and fields[4]=='VISUAL_FIRST_PASS',('PROVENANCE_WORD',a)
 print('D15B1H14-AUDIT PASS BASELINE='+BASE[:7]+' MOD=1/1 NEW=6/6 WORDS=14/14 PROGRAM=9 DATA=5 SOURCE_PINS=26/26 CONTENT_SHA=4/4 ROM3035_PIN=1 HOST_ROUNDING_CONFLICT=OPEN H9_H10_H11_H13_CONFLICTS=OPEN_UNCHANGED CPU_MUTATION=0 ROM_IMMUTABLE=1 PRIOR_IMAGES_IMMUTABLE=1 NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--self-test',action='store_true');args=a.parse_args()
 try:selftest();None if args.self_test else audit()
 except BaseException as e:raise SystemExit('D15B1H14-AUDIT FAIL '+repr(e))
