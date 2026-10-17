// ISA-06 D6: sign of exact-zero arithmetic sum; characterization only.
// GY62 printed pp. 7, 11, 13, 17, 170-171; DPS64 pp. 96-103, 136-139, 144-146.
// No change to CPU/ROM. Zero-sum signs are OBS, NEVER historical STRICT.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
using W = uint64_t;
constexpr W SIGN = W{1} << 40;
constexpr W MASK41 = (SIGN << 1) - 1;
constexpr W PC = 0100;
constexpr W RET = 0137;
constexpr W LOOP = 0765;

W make_instruction(W op, W a1, W a2, W a3) {
    return (op << 36) | ((a1 & 07777) << 24)
         | ((a2 & 07777) << 12) | (a3 & 07777);
}
std::string oct(W v) {
    std::ostringstream os;
    os << std::oct << v;
    return os.str();
}
struct Quiet {
    std::ostringstream captured;
    std::streambuf* old;
    Quiet() : old(std::cout.rdbuf(captured.rdbuf())) {}
    ~Quiet() { std::cout.rdbuf(old); }
};

struct Case {
    const char* name;
    W op, pc, source1, source2, destination;
    W val1, val2;
    W expected;            // Used ONLY for STRICT; ignored for OBS.
    bool strict;
};

int strict_total=0, strict_pass=0, obs_total=0;

void run(const Case& c) {
    if (c.strict) ++strict_total; else ++obs_total;
    try {
        Kyiv_t cpu;
        const W k = make_instruction(c.op,c.source1,c.source2,c.destination);
        // All test state is explicit, independent of the constructor's ROM path.
        cpu.kmem.write_memory(c.pc,k);
        if (c.source1 != 0) cpu.kmem.write_memory(c.source1,c.val1);
        if (c.source2 != 0) cpu.kmem.write_memory(c.source2,c.val2);
        // Cell 0000 always reads as +0. Do not attempt to modify it.
        cpu.C_reg = c.pc;
        cpu.A_reg = 0;
        cpu.P_reg = RET;
        cpu.Loop_reg = LOOP;
        const W a = cpu.kmem.read_memory(c.source1);
        const W b = cpu.kmem.read_memory(c.source2);
        bool running;
        { Quiet quiet; running = cpu.execute_opcode(); }
        const W result = cpu.kmem.read_memory(c.destination);
        if (!c.strict) {
            std::cout << "OBS " << c.name
                      << " | PC=" << oct(c.pc) << " K=" << oct(cpu.K_reg)
                      << " a=" << oct(a) << " b=" << oct(b)
                      << " result=" << oct(result)
                      << " sign=" << ((result & SIGN) ? "negative" : "positive")
                      << " magnitude=" << oct(result & (SIGN-1))
                      << " C=" << oct(cpu.C_reg) << " A=" << oct(cpu.A_reg)
                      << " P=" << oct(cpu.P_reg) << " Cy=" << oct(cpu.Loop_reg)
                      << " running=" << running << " stop=" << cpu.T_reg
                      << " [no historical zero-sign oracle]\n";
            return;
        }
        const bool ok = result == c.expected && cpu.K_reg == k &&
            cpu.C_reg == c.pc+1 && running && !cpu.T_reg &&
            cpu.A_reg == 0 && cpu.P_reg == RET && cpu.Loop_reg == LOOP &&
            (result & ~MASK41) == 0;
        strict_pass += ok;
        std::cout << (ok ? "STRICT-PASS " : "DOC-MISMATCH ") << c.name
                  << " | PC=" << oct(c.pc) << " K=" << oct(cpu.K_reg)
                  << " a=" << oct(a) << " b=" << oct(b)
                  << " result=" << oct(result) << " expected=" << oct(c.expected)
                  << " C=" << oct(cpu.C_reg) << " A=" << oct(cpu.A_reg)
                  << " P=" << oct(cpu.P_reg) << " Cy=" << oct(cpu.Loop_reg)
                  << " running=" << running << " stop=" << cpu.T_reg << "\n";
    } catch (const std::exception& e) {
        if (c.strict) {
            std::cout << "DOC-MISMATCH " << c.name << " | exception=" << e.what() << "\n";
        } else {
            std::cout << "OBS " << c.name << " | exception=" << e.what()
                      << " [not a historical oracle]\n";
        }
    } catch (...) {
        std::cout << (c.strict ? "DOC-MISMATCH " : "OBS ") << c.name
                  << " | unknown exception\n";
    }
}
} // namespace

int main() {
    // GY62 p. 11: ordinary algebraic sums with nonzero outcomes.
    run({"01_positive_plus_positive_nonzero", 001,PC,0002,0003,0004, 05,02,07,true});
    run({"01_positive_plus_negative_nonzero", 001,PC,0002,0003,0004, 05,SIGN|02,03,true});
    run({"01_negative_plus_positive_nonzero", 001,PC,0002,0003,0004, SIGN|05,02,SIGN|03,true});
    run({"01_negative_plus_negative_nonzero", 001,PC,0002,0003,0004, SIGN|05,SIGN|02,SIGN|07,true});
    // GY62 p. 13: subtraction of equal numbers gives -0.
    run({"02_sub_equal_negative_zero_regression", 002,PC,0002,0003,0004, 05,05,SIGN,true});

    // Exact-zero addition results: observations only, never STRICT.
    run({"01_positive_zero_plus_positive_zero", 001,PC,0002,0003,0004, 0,0,0,false});
    run({"01_positive_zero_plus_negative_zero", 001,PC,0002,0003,0004, 0,SIGN,0,false});
    run({"01_negative_zero_plus_positive_zero", 001,PC,0002,0003,0004, SIGN,0,0,false});
    run({"01_negative_zero_plus_negative_zero", 001,PC,0002,0003,0004, SIGN,SIGN,0,false});
    run({"01_positive_nonzero_minus_equal_negative", 001,PC,0002,0003,0004, 05,SIGN|05,0,false});
    run({"01_negative_nonzero_plus_equal_positive", 001,PC,0002,0003,0004, SIGN|05,05,0,false});
    // GY62 p.171: exact transcribed historical machine words at original PCs.
    // Source cell 0021 holds fixture -0; 0000 is hardwired +0.
    run({"historical_0123_01_negative_zero_copy", 001,0123,0021,0000,0020, SIGN,0,0,false});
    run({"historical_0141_01_negative_zero_copy", 001,0141,0021,0000,0020, SIGN,0,0,false});

    std::cout << "ISA-06 D6 STRICT=" << strict_pass << '/' << strict_total
              << " DOC-MISMATCH=" << (strict_total-strict_pass)
              << " POLICY=0 OBS=" << obs_total << "\n";
    return strict_pass == strict_total ? 0 : 1;
}
