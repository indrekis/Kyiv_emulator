#!/usr/bin/env python3
"""D15/B1-H22: fail-closed pinned source and 31-word per-address audit."""
from __future__ import annotations
import argparse,csv,hashlib,pathlib,re,subprocess
BASE='fc6cde6655573f0f317a35e112736778ebeb13f4';README='examples/historical/gy1962/README.md';IMAGE='examples/historical/gy1962/au1_batch31_0241_0277.k41';PROV='examples/historical/gy1962/au1_batch31_0241_0277_provenance.tsv';NEW=['docs/ISA_07_D15B1_H22_DECISION_LEDGER.tsv', 'docs/ISA_07_D15B1_H22_BATCH31_TRACE.md', 'examples/historical/gy1962/au1_batch31_0241_0277.k41', 'examples/historical/gy1962/au1_batch31_0241_0277_provenance.tsv', 'tools/isa07_d15b1_h22_audit.py', 'tools/isa07_d15b1_h22_native.py']
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
 'docs/ISA_07_D15B1_H9_SOURCE_CONFLICT.md': 'e648218821f5841a57ccdeb1c16b6b5a97a28a4b',
 'examples/historical/gy1962/README.md': '123b26dd7a972d71364ecf84c36aedd8563835a2',
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
 'tools/isa07_d15b1_h21_native.py': '167e65c0970d52db334c2b370a47d105b89ce78a'}
WORDS={'0241': '02303503550357',
 '0242': '11035603570352',
 '0243': '01035603520356',
 '0244': '11035703570357',
 '0245': '05035700000247',
 '0246': '05000000000242',
 '0247': '12035403550357',
 '0250': '02035703560352',
 '0251': '05035230020254',
 '0252': '22035403570253',
 '0253': '33000000000012',
 '0254': '31300002140043',
 '0255': '31300102140043',
 '0256': '33000000000000',
 '0257': '05000000000042',
 '0260': '01777777777777',
 '0261': '02525252525252',
 '0262': '05252525252524',
 '0263': '35000203500347',
 '0264': '16034700020266',
 '0265': '33000000000000',
 '0266': '16035030260270',
 '0267': '33000000000000',
 '0270': '35000003500347',
 '0271': '16034700000273',
 '0272': '33000000000000',
 '0273': '16035030260275',
 '0274': '33000000000000',
 '0275': '35302603500347',
 '0276': '16034730260300',
 '0277': '33000000000000'}
SHA={'docs/ISA_07_D15B1_H22_BATCH31_TRACE.md': 'f0c659d0925e91974fc8d2b6f5fbeb1035c318538f920fee21c2e24b17b8b6cf',
 'docs/ISA_07_D15B1_H22_DECISION_LEDGER.tsv': '8171996b408756fcee8f9196976cd53a32657dcd950ea9f6d809480a0d9e2d8d',
 'examples/historical/gy1962/au1_batch31_0241_0277.k41': '3a464c2cceccfca0b2b6910a373dbf4142ce5505a93f11d48d40afcf33b6fce8',
 'examples/historical/gy1962/au1_batch31_0241_0277_provenance.tsv': '9be265b220ae8499e9858e3ee9025326c8f34bc11d30cd9dfa93fe3c6817a100'}
README_SHA='25ba9badc523add076c88fd0534159d69c9df25a1fa1e8c476797d3732f4509f';APPEND='\n## AU test I, consolidated batch 0241–0277 (D15/B1-H22)\n\n- `au1_batch31_0241_0277.k41` faithfully transcribes 31 consecutively\n  addressed octal words from Glushkov/Yushchenko 1962, printed p.174:\n  28 program words (0241–0257,0263–0277) plus 3 data words 0260–0262.\n- This intentionally groups six independent subgroups A–F into one\n  Git release while retaining a bounded per-instruction native witness\n  for each executed path. Independent entries 0241, 0247, 0254 and 0263,\n  0270, 0273, 0275 are not assumed to be linked by historical control.\n- `0252` is a real I/O opcode and MUST NOT be executed in this batch;\n  the false predicate is checked by stopping at C=0252. The branches to\n  0214/0042/0043 and the boundary 0300 are also never executed.\n- HOST_ZERO is emulator zero-initialization only; historical scratch\n  and random seed are UNKNOWN. Explicit PRIVATE seeds and private patched\n  branch discriminator remain separate from the canonical historical image.\n- The independent exact-integer oracle models *current HOST policy*,\n  including division-by-zero stop, signed-zero comparisons, rounding,\n  normalization and ROM 3026=-0; it is NOT a historical hardware oracle.\n- H9/H10/H11/H13/H14/H17 conflicts OPEN_UNCHANGED;\n  H19_SEED=UNKNOWN; H20/H21_SCRATCH=UNKNOWN; CPU/ROM/prior images immutable.\n\n```sh\ng++ -std=c++17 -O0 -Iinc src/main.cpp src/asm_disasm.cpp -o tempkyiv/d15b1h22_kyivemu.exe\npython -B tools/isa07_d15b1_h22_native.py --cli-exe tempkyiv/d15b1h22_kyivemu.exe --timeout 20\n```\n'

def git(*args):return subprocess.check_output(['git',*args],stderr=subprocess.PIPE).decode().rstrip('\n')
def norm(data):
 assert b'\r' not in data.replace(b'\r\n',b'\n'),'STRAY_CR'
 return data.replace(b'\r\n',b'\n')
def recs(data):
 lines=[x.split() for x in norm(data).decode('ascii').splitlines() if re.fullmatch(r'[0-7]{4} [0-7]{14}',x)]
 assert len(lines)==31 and len(set(x[0] for x in lines))==31,'COUNT_OR_DUPLICATE'
 return dict(lines)
def selftest():
 assert len(PINS)==74 and all(re.fullmatch('[a-f0-9]{40}',p) for p in PINS.values()),'PIN_WIDTH'
 assert len(NEW)==6 and len(SHA)==4 and len(WORDS)==31,'SHAPE'
 assert recs(('KYIV41-OCT1\n'+'\n'.join(a+' '+w for a,w in WORDS.items())+'\n').encode())==WORDS,'CANONICAL_WORDS'
 assert [int(a,8) for a in WORDS]==list(range(int('0241',8),int('0300',8))),'OCTAL_CONTIGUITY'
 assert WORDS['0252']=='22035403570253' and WORDS['0260']=='01777777777777' and WORDS['0276']=='16034730260300','SOURCE_GUARDS'
 assert int(WORDS['0260'],8)==(1<<37)-1,'MASK_37'
 assert all(len(w)==14 and re.fullmatch(r'[0-7]{14}',w) for w in WORDS.values()),'FORMAT'
 assert norm(b'a\r\nb\r\n')==b'a\nb\n','CRLF'
 assert WORDS['0252']!='22035403570254','MUTANT'
 print('D15B1H22-AUDIT-SELFTEST PASS WORDS=31/31 PROGRAM=28 DATA=3 MUTANTS_REJECTED=1 CRLF=1 GIT_PIN_WIDTH=74/74 IO_BOUNDARY=1')
def audit():
 root=pathlib.Path(__file__).resolve().parent.parent
 assert git('rev-parse','HEAD')==BASE,'BASELINE'
 assert git('branch','--show-current')=='main' and not git('rev-parse','--show-prefix'),'ROOT_BRANCH'
 expected={' M '+README}|{'?? '+x for x in NEW}
 status=set(git('status','--porcelain=v1','--untracked-files=all').splitlines())
 assert status==expected,('SCOPE',sorted(status),sorted(expected))
 observed=git('rev-parse',*('HEAD:'+p for p in PINS)).splitlines()
 assert observed==list(PINS.values()),'BATCHED_GIT_PINS'
 readme=norm((root/README).read_bytes())
 assert hashlib.sha256(readme).hexdigest()==README_SHA and readme.endswith(APPEND.encode()),'README_SHA_APPEND'
 for path,sha in SHA.items():assert hashlib.sha256(norm((root/path).read_bytes())).hexdigest()==sha,('CONTENT_SHA',path)
 assert recs((root/IMAGE).read_bytes())==WORDS,'WORD_TRANSCRIPTION'
 with (root/PROV).open(encoding='ascii',newline='') as f:rows=list(csv.DictReader(f,delimiter='\t'))
 assert len(rows)==31 and {r['address'] for r in rows}==set(WORDS),'PROV_ROWS'
 for r in rows:
  assert r['code_octal_14']==WORDS[r['address']] and r['printed_page']=='174' and r['verification']=='VISUAL_FIRST_PASS','PROV_WORD'
  assert r['role']==('CONSTANT_DATA' if r['address'] in ('0260','0261','0262') else 'PROGRAM'),'PROV_ROLE'
 print('D15B1H22-AUDIT PASS BASELINE='+BASE[:7]+' MOD=1/1 NEW=6/6 WORDS=31/31 PROGRAM=28 DATA=3 SOURCE_PINS=74/74 CONTENT_SHA=4/4 ROM_IMMUTABLE=1 CPU_MUTATION=0 PREVIOUS_IMAGES_IMMUTABLE=1 HISTORICAL_SCRATCH=UNKNOWN H19_SEED=UNKNOWN H20_H21_SCRATCH=UNKNOWN H9_H10_H11_H13_H14_H17_CONFLICTS=OPEN_UNCHANGED NATIVE_GATE=PENDING HARDWARE_ORACLE=0')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');x=p.parse_args()
 try:selftest();None if x.self_test else audit()
 except BaseException as e:raise SystemExit('D15B1H22-AUDIT FAIL '+repr(e))
