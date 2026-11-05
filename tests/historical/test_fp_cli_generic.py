"""H115 B22 R2: offline structural and provenance checks; native gate is in stage."""
from pathlib import Path
import hashlib
import re
import unittest
ROOT=Path(__file__).resolve().parents[2]
H=ROOT/'inc/kyiv_fp_cli_v2.h'
CLI=ROOT/'src/asm_disasm.cpp'
ROM=ROOT/'examples/fp_rom_reconstructed/inputs/FP_FUNCTIONAL_1962_RECONSTRUCTED.k41'
EULER=ROOT/'examples/fp_euler_reconstructed/inputs/EULER_IMAGE.k41'
RK4=ROOT/'examples/fp_rom_reconstructed/reference/RK4_ORIGINAL_B16.k41'
ORIGINAL=ROOT/'examples/historical/gy1962/rom_modules/fp_simulation_251_printed.k41'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class GenericFpCLI(unittest.TestCase):
 def test_historical_preserved(self):
  self.assertEqual(sha(ORIGINAL),'ead80a8af8a207f619647ac1579ff934c6050a55d85a61b92a838ebd3d7662ba')
 def test_functional_rom_preserved(self):
  self.assertEqual(sha(ROM),'dd9f09ed319f54c61b655c5b4aa3df1eb69e0733ee76333577194f29fa75f120')
 def test_euler_preserved(self):
  self.assertEqual(sha(EULER),'c0007fbe8bbb42084e87f768244fd8f49ccd0377b4fb966cc7204f6cac4b9165')
 def test_rk4_preserved(self):
  self.assertEqual(sha(RK4),'904b500e989f3280483534951386934b970c252a20de66ec8777104204f45e35')
 def test_no_program_whitelist(self):
  s=H.read_text(encoding='utf-8')
  for forbidden in ('qualified_program(', 'euler_digest', 'original_rk4_digest', 'FP_UNQUALIFIED_PROGRAM', 'FP_FINAL_T_DRIFT', 'FP_FINAL_Y_DRIFT', 'FP_STEP_COUNT_DRIFT'):
   self.assertNotIn(forbidden,s)
 def test_no_address_or_opcode_whitelist(self):
  s=H.read_text(encoding='utf-8')
  for forbidden in ('readable(', 'FP_UNKNOWN_READ_', 'FP_IO_FORBIDDEN', 'FP_UNPRINTED_3574', 'FP_RAW_USER_COMMAND_FETCH_'):
   self.assertNotIn(forbidden,s)
 def test_one_time_boot(self):
  s=H.read_text(encoding='utf-8')
  self.assertEqual(len(re.findall(r'cpu\.C_reg\s*=\s*(?!=)',s)),1)
  self.assertIn('cpu.emergency_stop_blocked=true',s)
  self.assertIn('set_panel_nk_word(03000',s)
 def test_generic_rom_pin(self):
  s=H.read_text(encoding='utf-8')
  self.assertIn('kyiv_sha256_v1::digest(rom_raw)==cfg.rom_sha',s)
  self.assertNotIn('FP_UNQUALIFIED_RECONSTRUCTED_ROM',s)
  self.assertIn('FP_ROM_OUTSIDE_REPLACEABLE_RANGE',s)
 def test_explicit_end(self):
  s=H.read_text(encoding='utf-8')
  self.assertIn('--end-pointer',s)
  self.assertIn('pc==03305',s)
  self.assertIn('pointer==cfg.end',s)
 def test_cli_registration(self):
  s=CLI.read_text(encoding='utf-8')
  self.assertEqual(s.count('#include "kyiv_fp_cli_v2.h"'),1)
  self.assertEqual(s.count('if (mode == "fp-image") return kyiv_fp_cli_v2::run(argc, argv);'),1)
  self.assertIn('if (mode == "image")',s)
if __name__=='__main__':unittest.main()
