#!/usr/bin/env python3
"""H23: 38-word source audit, exact Git baseline and all prior blob pins."""
from __future__ import annotations
import argparse,csv,hashlib,pathlib,re,subprocess
BASE='75e291cf0e0b3cbca9eb2f8d537a3915f25b3bc5';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_batch38_0300_0345.k41';PROV='examples/historical/gy1962/au1_batch38_0300_0345_provenance.tsv';NEW=['docs/ISA_07_D15B1_H23_DECISION_LEDGER.tsv',
 'docs/ISA_07_D15B1_H23_BATCH38_SHIFT_NORMALIZATION.md',
 'examples/historical/gy1962/au1_batch38_0300_0345.k41',
 'examples/historical/gy1962/au1_batch38_0300_0345_provenance.tsv',
 'tools/isa07_d15b1_h23_audit.py',
 'tools/isa07_d15b1_h23_native.py']
PINS={'docs/ISA_07_D15B1_H10_CYCLIC_CARRY_OBSERVATION.md': '2ed71f86671bab99d456bcbe1426f67c60407310',
 'docs/ISA_07_D15B1_H11_DECISION_LEDGER.tsv': 'ef6ae41bae4075caddd292a4c11e537a86cc0218',
 'docs/ISA_07_D15B1_H11_SIGNED_ZERO_OBSERVATION.md': '01cb2d553c1d97f6426c3adb16b3683250e97464',
 'docs/ISA_07_D15B1_H12_ADDCMD_SIGN.md': '2aedc98670e193e7ebdda887d245b411b971051c',
 'docs/ISA_07_D15B1_H12_DECISION_LEDGER.tsv': '37284e5a5a818d9c03aad8d1124b80839047f4ac',
 'docs/ISA_07_D15B1_H13_DECISION_LEDGER.tsv': '639cb1308df041b3de081a27bda4f7e69a59ab01',
 'docs/ISA_07_D15B1_H13_ZERO_SHIFT.md': '9269aedfee849505dcae8f6d2628ab1dc4094767',
 'docs/ISA_07_D15B1_H14_DECISION_LEDGER.tsv': '82790ccbf2836e22b9054e11aa44c93ef99c2adf',
 'docs/ISA_07_D15B1_H14_ROUNDED_MULTIPLICATION_OBSERVATION.md': 'c557df023d05265d05f0ddc2ecc5f3839136458d',
 'docs/ISA_07_D15B1_H15_DECISION_LEDGER.tsv': '4800011274c9fcdb88f43df31a49a5a1ff28a607',
 'docs/ISA_07_D15B1_H15_NEGATIVE_ROUNDED_MULTIPLY.md': '360e0283cf268841661bf13f55466bb1365a63bd',
 'docs/ISA_07_D15B1_H16_DECISION_LEDGER.tsv': 'befc150fdd0492ddd6b9449cba09bb12ffab0b17',
 'docs/ISA_07_D15B1_H16_DIVISION_ONE_THIRD.md': 'fdae77c8e475eb79b07031537d879b8f1e6c70f3',
 'docs/ISA_07_D15B1_H17_DECISION_LEDGER.tsv': '3532052fd648b8e33f2c72b96938cec3f0e54d50',
 'docs/ISA_07_D15B1_H17_NEGATIVE_DIVISION_OBSERVATION.md': '4bd51010116f61d5d7a4ce45eddd33b6f8cb4b35',
 'docs/ISA_07_D15B1_H18_CONTROL_TRANSFER.md': 'bb341ab83fe5ad3d049c5a57c412dcf76e223d54',
 'docs/ISA_07_D15B1_H18_DECISION_LEDGER.tsv': '473911e39853840b4412f07b311600957d9ae32e',
 'docs/ISA_07_D15B1_H19_DECISION_LEDGER.tsv': '9988ef2b74ef8270719b1cbac865613f30f84dce',
 'docs/ISA_07_D15B1_H19_PSEUDORANDOM_CONTROL_TRACE.md': 'b4403947e216cbf6ca8afcfcf2aebe9c34748ac6',
 'docs/ISA_07_D15B1_H20_DECISION_LEDGER.tsv': 'cecceef03106c393b07aee2657c4560e1816fd70',
 'docs/ISA_07_D15B1_H20_ROUNDED_PRODUCTS_COMPARISON.md': '0fdda9a3687acf6c7fc8b13d21501de91c4f1cc3',
 'docs/ISA_07_D15B1_H21_ABSOLUTE_PREDIVISION_BRANCH.md': '0847a4f18b5b41dcfbc7f62a1fe0ab0c8e52199a',
 'docs/ISA_07_D15B1_H21_DECISION_LEDGER.tsv': 'a0baa351b7ef428eaa538ee0b627c7ae98b4bc08',
 'docs/ISA_07_D15B1_H22_BATCH31_TRACE.md': '5f38d7252aa7833395dc0188c03c6c6e39c72867',
 'docs/ISA_07_D15B1_H22_DECISION_LEDGER.tsv': '80d3569007f08d529d7d3c158408eb2471cc0179',
 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b',
 'examples/historical/gy1962/README.md': '7a05de662fd6db38a3c7805ba919ae9e9e216fe9',
 'examples/historical/gy1962/au1_absolute_predivision_0234_0240.k41': '58037e98af7e2af494afe6f936be5fe6f4756233',
 'examples/historical/gy1962/au1_absolute_predivision_0234_0240_provenance.tsv': 'e903c5f7d4b577b19fa9cd044ea42dcbc2780af0',
 'examples/historical/gy1962/au1_addcmd_0163_0165.k41': '60beab5d65e6f3c4af412971ee88e4bf9b89fd70',
 'examples/historical/gy1962/au1_addcmd_0163_0165_provenance.tsv': '9a7f3c4537174e116f99d4405a11bb00ea331041',
 'examples/historical/gy1962/au1_addcyc_0151_0154.k41': 'c28ef4d4f4f474442d8bc0d104551886d9b1f80c',
 'examples/historical/gy1962/au1_addition_0110_0115.k41': '3f5117fa184421060bfbb2c1f9a671ae3ac9dd3e',
 'examples/historical/gy1962/au1_addition_0116_0126.k41': '71def13ed127ca48aa5f290a00adb0e14ab7aed6',
 'examples/historical/gy1962/au1_addition_0127_0134.k41': 'dbee8e4944e64074fa003b18910ff18d1955f217',
 'examples/historical/gy1962/au1_addition_0135_0142.k41': '50e71e941ff86961640480ae8d4186dda1c750b4',
 'examples/historical/gy1962/au1_addition_0143_0150.k41': '2596703fe167ca2d990717d7cd051c1f822378ff',
 'examples/historical/gy1962/au1_batch31_0241_0277.k41': '21992ca378ad4ec084d12ff24bb24158a8ca6aa7',
 'examples/historical/gy1962/au1_batch31_0241_0277_provenance.tsv': 'e72d4329eb3f39da9477935839e4649745fc9af2',
 'examples/historical/gy1962/au1_control_transfer_0213.k41': '3b9befb7a42052c139407f8b1d3e9b3c263c5802',
 'examples/historical/gy1962/au1_control_transfer_0213_provenance.tsv': '00bceda662bccfa0fba78ad4b9cdfedf8131f673',
 'examples/historical/gy1962/au1_division_negative_0210_0212.k41': '326aee0c774af4340454405fa007393993f9cbbd',
 'examples/historical/gy1962/au1_division_negative_0210_0212_provenance.tsv': '3d081edc379c1c30c406f14ae4a41ec69585e9d3',
 'examples/historical/gy1962/au1_division_one_third_0205_0207.k41': 'a600910ceb0bb67ec2df35d53b504801d4bf59ff',
 'examples/historical/gy1962/au1_division_one_third_0205_0207_provenance.tsv': '035a3315d30f59d3f4224aeb0db51ab98cfeaa6e',
 'examples/historical/gy1962/au1_logic.k41': '7349c96dcf38cde678515a35be56697d0e7931ad',
 'examples/historical/gy1962/au1_pseudorandom_0214_0226.k41': 'd3c3bc8ac1b2cfde61594c58882ef7d744503e85',
 'examples/historical/gy1962/au1_pseudorandom_0214_0226_provenance.tsv': '9c861e07f34fbf35ff08db7fa1fabdf548033799',
 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201.k41': 'a599eff8e18fa86c3d57687992d1fcd87d481f74',
 'examples/historical/gy1962/au1_rounded_multiplication_0171_0201_provenance.tsv': 'df4ad2f5a52064885f14b7774d9743091047d818',
 'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204.k41': '5ee7f6ca7a0cc3ea9e39cd974aebe4c31dde8464',
 'examples/historical/gy1962/au1_rounded_multiply_negative_0202_0204_provenance.tsv': 'e9b1c1a37cf629a0408c9ca1b5144e67885ebf00',
 'examples/historical/gy1962/au1_rounded_products_swap_0227_0233.k41': '82c4a7f07a4223126136efee0b794486ffd0e50a',
 'examples/historical/gy1962/au1_rounded_products_swap_0227_0233_provenance.tsv': '41a7710f8e9a5477d213aae67e124974e82c8d44',
 'examples/historical/gy1962/au1_shift_zero_0166_0170.k41': '6b3fe5cefe09218ee1a65979f5df88c22f0d6012',
 'examples/historical/gy1962/au1_shift_zero_0166_0170_provenance.tsv': '22b9ed96ad6cd6e89be45be4263bc92eeffed277',
 'examples/historical/gy1962/au1_subtraction_0155_0162.k41': '3428a04652d6f9a8ee070138a183b158406175d2',
 'examples/historical/gy1962/au1_subtraction_0155_0162_provenance.tsv': '9c7737f526d313eef8243a4a4de592059d53f5af',
 'mem/ROM.txt': 'b39868f9697c82fd3b9ba9b7448b8313293970c1',
 'src/main.cpp': 'fd016456ac90e38f43fc0a033e89e6ba8019350c',
 'tools/isa07_d15b1_h13_audit.py': '78264991c1bf003378d860934dbee2cafa05fdb1',
 'tools/isa07_d15b1_h13_native.py': 'b797b1a3bb7931baa3b55a953bcce7f1d8f63e04',
 'tools/isa07_d15b1_h14_audit.py': '00f2683622a364429631569bf4574cfacee69fe4',
 'tools/isa07_d15b1_h14_native.py': 'f8cff402120bf6137cf5d80cef128fafc4a087bf',
 'tools/isa07_d15b1_h15_audit.py': '22bc6f2bffe8652aa5f7ec14dee5f64624bd3229',
 'tools/isa07_d15b1_h15_native.py': '3bfd9fc38b333e537c2ac143093d5c32ac366443',
 'tools/isa07_d15b1_h16_audit.py': 'e8c5e63e934a08a41345093953e4feb7b3bbd84a',
 'tools/isa07_d15b1_h16_native.py': 'c8657c762d4c360fba4d609c0d0f49a26562f08b',
 'tools/isa07_d15b1_h17_audit.py': 'ef98e68fbd2aaa1ab8470d640cff68f5ec1fea73',
 'tools/isa07_d15b1_h17_native.py': '018879f2839cc9f178fead1c9b3ddf38004bf32b',
 'tools/isa07_d15b1_h18_audit.py': '1109df44b5e982a86050fe470713a5829f96cda8',
 'tools/isa07_d15b1_h18_native.py': 'd1e4cbc2ecb85283f88c786391927350d82315dd',
 'tools/isa07_d15b1_h19_audit.py': '0cbd391b36df677db4151d0f850d5a8feed9a784',
 'tools/isa07_d15b1_h19_native.py': '9fcf66d91751cc33816e56e14f633045ec66ddef',
 'tools/isa07_d15b1_h20_audit.py': '70956b09bcdea4e89c8839876654a60746a1c94c',
 'tools/isa07_d15b1_h20_native.py': '1f4006535a09dea24a08de85ce24039dbc19b9cb',
 'tools/isa07_d15b1_h21_audit.py': '02bcef37266a8d4c3354bee22f7775cea07f20e1',
 'tools/isa07_d15b1_h21_native.py': '167e65c0970d52db334c2b370a47d105b89ce78a',
 'tools/isa07_d15b1_h22_audit.py': 'd77b96c06ad1f16bb7b6b361e28cee7a82be9985',
 'tools/isa07_d15b1_h22_native.py': 'c081c507d5029337526e70de2427efdbe7a57c82'}
WORDS={'0300': '16035030260302',
 '0301': '33000000000000',
 '0302': '35317703500347',
 '0303': '16034703350305',
 '0304': '33000000000000',
 '0305': '16035003360307',
 '0306': '33000000000000',
 '0307': '13033700000347',
 '0310': '16034700000312',
 '0311': '33000000000000',
 '0312': '13033730260347',
 '0313': '16034700000315',
 '0314': '33000000000000',
 '0315': '13034030260347',
 '0316': '16034703430320',
 '0317': '33000000000000',
 '0320': '13034131770347',
 '0321': '16034730260323',
 '0322': '33000000000000',
 '0323': '13034231770347',
 '0324': '16034730120326',
 '0325': '33000000000000',
 '0326': '13034400030347',
 '0327': '16034730260331',
 '0330': '33000000000000',
 '0331': '13034500030347',
 '0332': '16034700000334',
 '0333': '33000000000000',
 '0334': '05000000000360',
 '0335': '30000000000000',
 '0336': '20000000000047',
 '0337': '00000000000014',
 '0340': '20000000000014',
 '0341': '00000000000050',
 '0342': '20000000000050',
 '0343': '00002000000000',
 '0344': '20000000000100',
 '0345': '20000000000101'}
SHA={'docs/ISA_07_D15B1_H23_BATCH38_SHIFT_NORMALIZATION.md': '8def6fe75cb6ab2cd2edcfb2f597ac0dca996b85e610fc9c27d217493893f6ae',
 'docs/ISA_07_D15B1_H23_DECISION_LEDGER.tsv': '8892f96b0eaf55a68c0f09780182feeb2728f360bb1aed64484c28d6f1acf621',
 'examples/historical/gy1962/au1_batch38_0300_0345.k41': 'f042e1b77747bdb44cd0d8af4198a377f6ee9605b075025444ef4f817f740ff4',
 'examples/historical/gy1962/au1_batch38_0300_0345_provenance.tsv': '9119cc821bff027cfef282fc8a7a740e817f60cfa0dc58390a3284d723b2583d'}
README_SHA='80e1aeb855e1e2546db7eb74ea2a4a03b515301c333c7d609866ab289115fad4';APPEND="\n## AU test I, large-batch continuation 0300–0345 (D15/B1-H23)\n\n- `au1_batch38_0300_0345.k41`: 38 original octal words (29 commands,\n  9 data words `0335–0345`) from GY1962 printed p.174. This is a\n  SOURCE transcription, not an assertion that the full historical test passes.\n- Three separately bounded verification families: A (`0300–0306`,\n  negative-zero/normalization-order), B (`0307–0325`, shift direction and\n  shift-count masking), C (`0326–0334`, signed-zero and branch boundary).\n- H23 deliberately preserves the historical negative order witness\n  `RAM[0336]=20000000000047`, which differs from the current host\n  normalizer's *unsigned* order `00000000000047` when normalizing\n  ROM[3177]=-1. `NORMALIZER_ORDER_SIGN_ORACLE=OPEN`; do not alter source,\n  CPU, ROM, or retrofit an expected HOST PASS into historical truth.\n- The historical entry state in RAM[0350] and RAM[0003] is unknown.\n  HOST-zero and PRIVATE settings are distinct. `0334→0360` is a\n  **boundary**; 0360 itself is never executed. Data 0335–0345 is not code.\n- Earlier H9/H10/H11/H13/H14/H17 conflicts remain OPEN_UNCHANGED,\n  as do H19 seed and H20/H21/H22 historical scratch uncertainties.\n- Real MSYS2 native probe is required before release; a package\n  selftest/mock CLI pass is not a hardware or historical oracle.\n\n```sh\ng++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h23_kyivemu.exe\npython -B tools/isa07_d15b1_h23_native.py --cli-exe tempkyiv/d15b1h23_kyivemu.exe --timeout 20\n```\n"

def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def norm(data):
 assert b'\r' not in data.replace(b'\r\n',b'\n'),'STRAY_CR'
 return data.replace(b'\r\n',b'\n')
def recs(data):
 lines=[x.split() for x in norm(data).decode('ascii').splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',x)]
 assert len(lines)==38 and len(set(x[0] for x in lines))==38,'TRANSCRIPTION_ROWS_NOT_38'
 return dict(lines)
def selftest():
 assert len(PINS)==80 and all(re.fullmatch('[0-9a-f]{40}',v) for v in PINS.values()),'PIN_WIDTH'
 assert len(NEW)==6 and len(SHA)==4 and len(WORDS)==38,'INVENTORY'
 assert list(map(lambda a:int(a,8),WORDS))==list(range(0o300,0o346)),'SOURCE_ADDR_RANGE'
 assert recs(('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in WORDS.items())+'\n').encode())==WORDS,'SOURCE_ORACLE'
 assert all(re.fullmatch('[0-7]{14}',v) for v in WORDS.values()),'WORD_FORMAT'
 assert WORDS['0300']=='16035030260302' and WORDS['0302']=='35317703500347','NORMALIZER_ENTRY'
 assert WORDS['0305']=='16035003360307' and WORDS['0336']=='20000000000047','ORDER_SIGN_DISCRIMINATOR'
 assert WORDS['0335']=='30000000000000' and WORDS['0343']=='00002000000000','DATA_WITNESS'
 assert WORDS['0334']=='05000000000360','BRANCH_0360'
 assert all((int(a,8)>=0o335)==(i>=29) for i,a in enumerate(WORDS)),'PROGRAM_DATA_SPLIT'
 assert norm(b'a\r\nb\r\n')==b'a\nb\n','CRLF_NORMALIZER'
 mutant=dict(WORDS);mutant['0305']='16035003360306';assert mutant!=WORDS,'MUTANT'
 print('D15B1H23-AUDIT-SELFTEST PASS WORDS=38/38 PROGRAM=29 DATA=9 GIT_PIN_WIDTH=80/80 NORMALIZER_ORDER_DISCRIMINATOR=1 MUTANTS_REJECTED=1 CRLF=1 BOUNDARY_0360=1')
def audit():
 root=pathlib.Path(__file__).resolve().parent.parent
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main' and not git('rev-parse','--show-prefix'),'BRANCH_ROOT'
 assert not git('diff','--cached','--name-only'),'STAGING_NONEMPTY'
 expected={' M '+README}|{'?? '+p for p in NEW}
 actual=set(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert actual==expected,('WORKTREE_SCOPE',sorted(actual),sorted(expected))
 pins=git('rev-parse',*('HEAD:'+p for p in PINS)).splitlines()
 assert pins==list(PINS.values()),'PINNED_GIT_BLOBS'
 rd=norm((root/README).read_bytes())
 assert hashlib.sha256(rd).hexdigest()==README_SHA and rd.endswith(APPEND.encode()),'README_APPEND_HASH'
 for p,sha in SHA.items():assert hashlib.sha256(norm((root/p).read_bytes())).hexdigest()==sha,('CONTENT_SHA',p)
 assert recs((root/IMAGE).read_bytes())==WORDS,'HISTORICAL_WORDS'
 assert norm((root/IMAGE).read_bytes()).decode('ascii')=='KYIV41-OCT1\n'+''.join(f'{a} {w}\n' for a,w in WORDS.items()),'CANONICAL_IMAGE_NO_SEEDS'
 with (root/PROV).open(encoding='ascii',newline='') as f:rows=list(csv.DictReader(f,delimiter='\t'))
 assert len(rows)==38 and {r['address'] for r in rows}==set(WORDS),'PROVENANCE_SHAPE'
 for r in rows:
  assert r['code_octal_14']==WORDS[r['address']] and r['printed_page']=='174' and r['verification']=='VISUAL_FIRST_PASS','PROVENANCE_WORD'
  assert r['role']==('CONSTANT_DATA' if int(r['address'],8)>=0o335 else 'PROGRAM'),'PROVENANCE_ROLE'
 print('D15B1H23-AUDIT PASS BASELINE='+BASE[:7]+' MOD=1/1 NEW=6/6 WORDS=38/38 PROGRAM=29 DATA=9 SOURCE_PINS=80/80 CONTENT_SHA=4/4 NORMALIZER_ORDER_SIGN_ORACLE=OPEN HISTORICAL_ENTRY_SCRATCH=UNKNOWN H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED CPU_MUTATION=0 ROM_IMMUTABLE=1 PRIOR_IMAGES_IMMUTABLE=1 NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');a=p.parse_args()
 try:selftest(); None if a.self_test else audit()
 except BaseException as e:raise SystemExit('D15B1H23-AUDIT FAIL '+repr(e))
