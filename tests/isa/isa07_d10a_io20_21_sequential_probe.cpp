// ISA-07 D10-A: two genuine CPU steps, IO20/21 then XOR at sequential PC.
// GY62 printed p.58 documents C+1 -> C, memory[C] -> K for both.
// Host text adapter is intentionally unchanged: not a numeric-format oracle.
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iostream>
#include <string>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
constexpr word_t instr(unsigned op, unsigned a1, unsigned a2, unsigned a3) {
    return (word_t(op) << 36) | (word_t(a1) << 24) |
           (word_t(a2) << 12) | word_t(a3);
}
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string mode(argv[1]);
    const bool number = mode.rfind("20-",0) == 0;
    const bool command = mode.rfind("21-",0) == 0;
    if (!number && !command) return 2;
    if (mode != "20-range" && mode != "20-single" &&
        mode != "20-offset" && mode != "20-short" &&
        mode != "20-missing" && mode != "20-zone1" &&
        mode != "21-range" && mode != "21-single" &&
        mode != "21-offset" && mode != "21-h1" &&
        mode != "21-a3" && mode != "21-missing") return 2;
    try {
        Kyiv_t m;
        constexpr addr_t pc = 0100;
        constexpr addr_t next = pc + 1;
        const unsigned a1 = (mode.find("-single") != std::string::npos ||
                             mode.find("-offset") != std::string::npos) ? 0201 : 0200;
        const unsigned a2 = (mode.find("-single") != std::string::npos) ? 0201 :
                            (mode.find("-offset") != std::string::npos) ? 0203 : 0202;
        // 20: a3 is a card-zone offset; 21: nonzero a3 must not redirect PC.
        const unsigned a3 = (mode == "20-zone1") ? 1 : (command ? 0120 : 0);
        const word_t follow = instr(017, 0300, 0301, 0302); // 5 XOR 3 = 6
        m.kmem.write_memory(pc, instr(number ? 020 : 021,a1,a2,a3));
        m.kmem.write_memory(next, follow);
        m.kmem.write_memory(0120, instr(033,0,0,0)); // Decoy: must not execute.
        m.kmem.write_memory(0300,5);
        m.kmem.write_memory(0301,3);
        m.kmem.write_memory(0302,0);
        for (addr_t a=0200; a<=0203; ++a) m.kmem.write_memory(a,0);
        m.C_reg=pc;
        m.K_reg=0;
        m.h=(mode=="21-h1") ? 1 : 0;
        m.perfo_num=0;
        const bool run1=m.execute_opcode(); // CPU STEP 1
        const addr_t pc1=m.C_reg;
        const word_t k1=m.K_reg;
        const word_t a=m.kmem.read_memory(0200);
        const word_t b=m.kmem.read_memory(0201);
        const word_t c=m.kmem.read_memory(0202);
        const word_t d=m.kmem.read_memory(0203);
        const size_t h1=m.h;
        const bool run2=m.execute_opcode(); // CPU STEP 2: actually execute XOR
        const addr_t pc2=m.C_reg;
        const word_t k2=m.K_reg;
        const word_t xor_result=m.kmem.read_memory(0302);
        std::cout << std::oct
                  << "D10A-OBS mode=" << mode
                  << " pc0=" << pc << " pc1=" << pc1 << " pc2=" << pc2
                  << std::dec << " k1_match=" << (k1==follow)
                  << " k2_match=" << (k2==follow)
                  << " memory=" << a << '/' << b << '/' << c << '/' << d
                  << " h=" << h1 << " xor=" << xor_result
                  << " running=" << run1 << '/' << run2 << " steps=2" << '\n';
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D10A-EXCEPTION mode=" << mode << " reason=" << e.what() << '\n';
        return 3;
    } catch (...) {
        std::cerr << "D10A-EXCEPTION mode=" << mode << " reason=unknown\n";
        return 3;
    }
}
