// Permanent source-backed regression for opcode 12. No external ROM/files.
// Compile with src/main.cpp and -Iinc. The disassembler formats text only.
#include "kyiv.h"
#include "kyiv_serial_division.h"
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
constexpr std::uint64_t sign = std::uint64_t{1} << 40;
constexpr std::uint64_t mag = sign - 1;
constexpr std::uint64_t pc = 0100;
struct Quiet {
    std::ostringstream output;
    std::streambuf* previous;
    Quiet() : previous(std::cout.rdbuf(output.rdbuf())) {}
    ~Quiet() {std::cout.rdbuf(previous);}
};
void check(bool condition, const std::string& what) {
    if (!condition) throw std::runtime_error(what);
}
struct State {std::uint64_t result, c, k, left, right; bool halted, continued;};
State run(std::uint64_t a, std::uint64_t b, unsigned dst=4, bool block=false) {
    Kyiv_t cpu(Kyiv_t::rom_boot_mode::deferred);
    cpu.kmem.write_memory(2,a);
    cpu.kmem.write_memory(3,b);
    cpu.kmem.write_memory(4,07777);
    const std::uint64_t instruction = (std::uint64_t{012} << 36)
       | (std::uint64_t{2} << 24) | (std::uint64_t{3} << 12) | dst;
    cpu.kmem.write_memory(pc,instruction);
    cpu.C_reg=pc;
    cpu.emergency_stop_blocked=block;
    bool continued=false;
    { Quiet silence; continued=cpu.execute_opcode(); }
    return {cpu.kmem.read_memory(dst),cpu.C_reg,cpu.K_reg,
            cpu.kmem.read_memory(2),cpu.kmem.read_memory(3),cpu.T_reg,continued};
}
void valid(const char* name,std::uint64_t a,std::uint64_t b,
           std::uint64_t expected,unsigned dst=4) {
    const auto s=run(a,b,dst);
    const auto instruction = (std::uint64_t{012} << 36)
       | (std::uint64_t{2} << 24) | (std::uint64_t{3} << 12) | dst;
    check(s.continued && !s.halted && s.c==pc+1 && s.k==instruction,
          std::string(name)+":control");
    check(s.result==(dst==0?0:expected),std::string(name)+":quotient");
    check(s.left==(dst==2?expected:a) && s.right==(dst==3?expected:b),
          std::string(name)+":source_alias");
}
} // namespace
int main() {
    try {
        valid("H16 +1/3", 01000000000000ULL,03000000000000ULL,05252525252525ULL);
        valid("H17 -1/7", 020002000000000ULL,00016000000000ULL,022222222222200ULL);
        // Four sign combinations, near-zero and near-unity representable cases.
        unsigned cases=0;
        const std::uint64_t pairs[][2]={{0,1},{0,mag},{1,mag},{1,sign/2},
            {mag-1,mag},{sign/2,sign/2+1},{1,2},{mag/3,mag/2}};
        for (const auto& pair : pairs) for (int sa=0;sa<2;++sa) for (int sb=0;sb<2;++sb) {
            const std::uint64_t a=pair[0] | (sa?sign:0);
            const std::uint64_t b=pair[1] | (sb?sign:0);
            const std::uint64_t q = ((a ^ b)&sign) |
                kyiv_serial_division::quotient_magnitude(a&mag,b&mag);
            valid("boundary",a,b,q);
            ++cases;
        }
        for (unsigned d : {0U,2U,3U,4U})
            valid("alias",020002000000000ULL,00016000000000ULL,022222222222200ULL,d);
        auto dz=run(1,0);
        check(dz.halted && !dz.continued && dz.c==pc+1 && dz.result==07777,
              "division_by_zero_stop");
        auto ov=run(sign/2,sign/2);
        check(ov.halted && !ov.continued && ov.c==pc+1 && ov.result==07777,
              "overflow_stop");
        auto ob=run(sign/2,sign/2,4,true);
        check(!ob.halted && ob.continued && ob.c==pc+2 && ob.result==0,
              "overflow_blocked_skip");
        std::cout << "H17_PERMANENT_REGRESSION=PASS; HISTORICAL=2/2; BOUNDARY="
            << cases << "; ALIAS=4; POLICY=3; NO_MODE_SWITCH=1\n";
    } catch (const std::exception& e) {
        std::cerr << "H17_PERMANENT_REGRESSION=FAIL; DETAIL=" << e.what() << '\n';
        return 1;
    }
}
