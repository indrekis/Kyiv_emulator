// ISA-06 D8-P7: true fourth RAM test entry 0117 -> 0120 -> 0121 -> 0122.
// GY62 1962 printed pp. 120, 170. ROM and initial RAM are FIXTURES.
// The entry result is emulator POLICY (not an authenticated hardware trace).
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
using W=uint64_t;
constexpr W SIGN=W{1}<<40;
struct Silent { std::ostringstream buffer; std::streambuf* old;
  Silent():old(std::cout.rdbuf(buffer.rdbuf())){} ~Silent(){std::cout.rdbuf(old);} };
bool step(Kyiv_t& cpu) { Silent hide; return cpu.execute_opcode(); }
void check(bool ok, const char* reason) { if (!ok) throw std::runtime_error(reason); }
void run() {
  Kyiv_t cpu;
  cpu.kmem.write_rom(03012, 1); // fixture, documented fixed-ROM word in repo
  cpu.kmem.write_memory(0014, SIGN); // deliberately start with -0 to test 0117
  cpu.kmem.write_memory(0017, 077);
  cpu.kmem.write_memory(0021, 077);
  constexpr W w117 = 0'01'0000'0000'0014ULL;
  constexpr W w120 = 0'01'3012'0000'0017ULL;
  constexpr W w121 = 0'01'0017'0000'0021ULL;
  cpu.kmem.write_memory(0117, w117);
  cpu.kmem.write_memory(0120, w120);
  cpu.kmem.write_memory(0121, w121);
  cpu.C_reg=0117;
  cpu.A_reg=0;
  cpu.P_reg=0371;
  cpu.Loop_reg=077;
  cpu.T_reg=false;
  check(step(cpu), "0117 unexpectedly stopped");
  check(cpu.K_reg==w117 && cpu.C_reg==0120, "0117 source word or next PC mismatch");
  check(cpu.kmem.read_memory(0014)==0, "0117 failed to initialize +0 in 0014");
  check(step(cpu), "0120 unexpectedly stopped");
  check(cpu.K_reg==w120 && cpu.C_reg==0121, "0120 source word or next PC mismatch");
  check(cpu.kmem.read_memory(0017)==1, "0120 failed to initialize pattern +1");
  check(step(cpu), "0121 unexpectedly stopped");
  check(cpu.K_reg==w121 && cpu.C_reg==0122, "0121 source word or next PC mismatch");
  check(cpu.kmem.read_memory(0021)==1, "0121 failed to initialize transfer register");
  check(cpu.kmem.read_memory(0014)==0 && !cpu.T_reg, "state after documented entry mismatch");
  std::cout << "POLICY-PASS documented_0117_entry steps=3 "
               "K0117=" << std::oct << w117 << " PC=0122 RAM0014=+0 "
               "RAM0017=1 RAM0021=1 ROM3012=FIXTURE first_bad_pc=0\n";
}
}
int main() {
  try { run(); std::cout << "ISA-06 D8-P7 STRICT=0/0 DOC-MISMATCH=0 POLICY=1/1 POLICY-FAIL=0 OBS=0\n";return 0; }
  catch (const std::exception& e) {
    std::cout << "POLICY-FAIL documented_0117_entry reason=" << e.what() << "\n";
    std::cout << "ISA-06 D8-P7 STRICT=0/0 DOC-MISMATCH=0 POLICY=0/1 POLICY-FAIL=1 OBS=0\n";
    return 1;
  }
}
