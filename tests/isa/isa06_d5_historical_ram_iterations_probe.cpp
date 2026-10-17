// ISA-06 D5: bounded, multi-instruction iterations of the fourth historical RAM test.
// GY62 (1962), Appendix 2, printed pp. 170-171.
// No CPU/ROM changes. ROM 3012/3026/3042 are explicit TEST FIXTURES.
// Equal-operand branch of 05 is emulator POLICY, never STRICT.
#include <cstdint>
#include <exception>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
using W = uint64_t;
constexpr W SIGN = W{1} << 40;
constexpr W UPPER_MAG = W{1} << 39;
constexpr W RET = 0371;
constexpr W SENTINEL = 077;
constexpr W ANY_NEXT_PC = ~W{0}; // STOP post-increment not historically established

struct HistoricalWord { W pc, word; };
// Direct 14-octal-digit transcription at original locations (GY62 p. 171).
// Do not use an emulator-produced assembler output as the original record.
constexpr HistoricalWord HIST[] = {
    {0122, 0'26'0000'0200'0000ULL},
    {0123, 0'01'0021'0000'0020ULL},
    {0124, 0'31'0014'0126'0125ULL},
    {0125, 0'01'3036'0020'0020ULL},
    {0126, 0'01'0020'0000'4000ULL},
    {0127, 0'16'0021'3042'0133ULL},
    {0130, 0'16'0021'3026'0135ULL},
    {0131, 0'13'3012'0021'0021ULL},
    {0132, 0'05'0000'0000'0136ULL},
    {0133, 0'01'3026'0000'0021ULL},
    {0134, 0'05'0000'0000'0136ULL},
    {0135, 0'01'3012'0000'0021ULL},
    {0136, 0'27'4001'0123'0137ULL},
    {0140, 0'26'0000'0200'0000ULL},
    {0141, 0'01'0021'0000'0020ULL},
    {0142, 0'31'0014'0144'0143ULL},
    {0143, 0'01'3036'0020'0020ULL},
    {0144, 0'16'4000'0020'0146ULL},
    {0145, 0'33'0000'0004'0000ULL},
    {0146, 0'16'0021'3042'0152ULL},
    {0147, 0'16'0021'3026'0154ULL},
    {0150, 0'13'3012'0021'0021ULL},
    {0151, 0'05'0000'0000'0155ULL},
    {0152, 0'01'3026'0000'0021ULL},
    {0153, 0'05'0000'0000'0155ULL},
    {0154, 0'01'3012'0000'0021ULL},
    {0155, 0'27'4001'0141'0156ULL},
};

W hist_word(W pc) {
    for (const auto& h : HIST) if (h.pc == pc) return h.word;
    throw std::logic_error("untranscribed historical PC");
}
struct Silence {
    std::ostringstream sink;
    std::streambuf* original;
    Silence():original(std::cout.rdbuf(sink.rdbuf())){}
    ~Silence(){std::cout.rdbuf(original);}
};
bool step(Kyiv_t& m) { Silence ignored; return m.execute_opcode(); }

struct Transition { W pc, next_pc; bool running; };
using Setup = std::function<void(Kyiv_t&)>;
using Verify = std::function<bool(const Kyiv_t&)>;
int strict_total = 0, strict_pass = 0;
int policy_total = 0, policy_pass = 0;
void run(const char* name, bool is_policy, const std::vector<Transition>& trace,
         const Setup& setup, const Verify& verify) {
    if (is_policy) ++policy_total; else ++strict_total;
    try {
        Kyiv_t m;
        // Explicit fixtures matching *transcribed* ROM: not independently
        // proven to be original hardware constants. No CWD dependencies.
        m.kmem.write_rom(03012, 1);         // +1 bit shift
        m.kmem.write_rom(03026, SIGN);      // -0
        m.kmem.write_rom(03042, UPPER_MAG); // top magnitude bit
        for (const auto& h : HIST) m.kmem.write_memory(h.pc, h.word);
        m.kmem.write_memory(0014, 0);      // select positive-sign branch 31
        m.kmem.write_memory(0021, SIGN);   // traveling pattern begins at -0
        m.kmem.write_memory(0020, SENTINEL);
        m.kmem.write_memory(0200, SENTINEL);
        m.kmem.write_memory(0201, SENTINEL);
        m.kmem.write_memory(01777, SENTINEL);
        m.P_reg = RET;
        m.A_reg = 0;
        m.Loop_reg = 077;
        setup(m);
        m.C_reg = trace.at(0).pc;
        bool ok = true;
        size_t completed = 0;
        W first_bad_pc = 0;
        for (const auto& t : trace) {
            if (m.C_reg != t.pc) { ok = false; first_bad_pc=t.pc; break; }
            const bool running = step(m);
            ++completed;
            if (m.K_reg != hist_word(t.pc) ||
                (t.next_pc != ANY_NEXT_PC && m.C_reg != t.next_pc) ||
                running != t.running || m.T_reg == t.running) {
                ok = false; first_bad_pc=t.pc; break;
            }
        }
        ok = ok && completed == trace.size() && verify(m) && m.P_reg == RET;
        if (is_policy) policy_pass += ok; else strict_pass += ok;
        std::cout << (ok ? (is_policy ? "POLICY-PASS " : "STRICT-PASS ")
                         : (is_policy ? "POLICY-FAIL " : "DOC-MISMATCH "))
                  << name << " | steps=" << completed << "/" << trace.size()
                  << " C=" << std::oct << m.C_reg << " A=" << m.A_reg
                  << " Cy=" << m.Loop_reg << " mem20=" << m.kmem.read_memory(0020)
                  << " mem21=" << m.kmem.read_memory(0021)
                  << " mem200=" << m.kmem.read_memory(0200)
                  << " mem201=" << m.kmem.read_memory(0201)
                  << " stop=" << m.T_reg << " first_bad_pc=" << first_bad_pc
                  << std::dec << "\n";
    } catch (const std::exception& e) {
        std::cout << (is_policy ? "POLICY-FAIL " : "DOC-MISMATCH ")
                  << name << " | exception=" << e.what() << "\n";
    }
}
// A -0 seed is used only for the *control* path. Arithmetic opcode 01
// may alter zero sign when copying it via addition to +0: D4 OBS.
const std::vector<Transition> WRITE_ZERO_CONTROL = {
    {0122,0123,true}, {0123,0124,true}, {0124,0126,true},
    {0126,0127,true}, {0127,0130,true}, {0130,0135,true},
    {0135,0136,true}, {0136,0123,true}
};
// An uninterrupted write loop over positive NONZERO values. The equality
// of opcode 05 is still unproven on the original machine: POLICY.
const std::vector<Transition> WRITE_POSITIVE_ONE = {
    {0122,0123,true}, {0123,0124,true}, {0124,0126,true},
    {0126,0127,true}, {0127,0130,true}, {0130,0131,true},
    {0131,0132,true}, {0132,0136,true}, {0136,0123,true}
};
const std::vector<Transition> WRITE_POSITIVE_SECOND = {
    {0123,0124,true}, {0124,0126,true}, {0126,0127,true},
    {0127,0130,true}, {0130,0131,true}, {0131,0132,true},
    {0132,0136,true}, {0136,0123,true}
};
// STRICT from comparison onward: the candidate and comparator are
// preinitialized. In particular, the ambiguous 0141 (-0)+(+0) is NOT run.
const std::vector<Transition> READ_ZERO_TAIL = {
    {0144,0146,true}, {0146,0147,true}, {0147,0154,true},
    {0154,0155,true}, {0155,0141,true}
};
// Read complete, with positive NONZERO inputs; equality of 05 is POLICY.
const std::vector<Transition> READ_POSITIVE_ONE = {
    {0140,0141,true}, {0141,0142,true}, {0142,0144,true},
    {0144,0146,true}, {0146,0147,true}, {0147,0150,true},
    {0150,0151,true}, {0151,0155,true}, {0155,0141,true}
};
const std::vector<Transition> READ_POSITIVE_SECOND = {
    {0141,0142,true}, {0142,0144,true}, {0144,0146,true},
    {0146,0147,true}, {0147,0150,true}, {0150,0151,true},
    {0151,0155,true}, {0155,0141,true}
};
std::vector<Transition> concat(const std::vector<Transition>& a,
                               const std::vector<Transition>& b) {
    auto result=a;
    result.insert(result.end(), b.begin(), b.end());
    return result;
}
// OBS ONLY: the -0 read phase uses arithmetic copying (-0)+(+0), an
// unresolved historical zero-sign result. Show the actual trace and bits,
// with no assertion of normative behavior and no PASS for RAM diagnostic.
void observe_read_negative_zero_prefix() {
    try {
        Kyiv_t m;
        m.kmem.write_rom(03012, 1);
        m.kmem.write_rom(03026, SIGN);
        m.kmem.write_rom(03042, UPPER_MAG);
        for (const auto& h : HIST) m.kmem.write_memory(h.pc, h.word);
        m.kmem.write_memory(0014, 0);
        m.kmem.write_memory(0021, SIGN);
        m.kmem.write_memory(0200, SIGN);
        m.C_reg = 0140;
        std::ostringstream observed;
        for (unsigned i=0;i<5 && !m.T_reg;i++) {
            const W before=m.C_reg;
            const bool running=step(m);
            observed << std::oct << before << "->" << m.C_reg << " ";
            if (!running) break;
        }
        std::cout << "OBS read_negative_zero_prefix | trace=" << observed.str()
                  << " mem20=" << std::oct << m.kmem.read_memory(0020)
                  << " mem200=" << m.kmem.read_memory(0200)
                  << " C=" << m.C_reg << std::dec << " stop=" << m.T_reg
                  << " [(-0)+(+0) sign is NOT a historical oracle]\n";
    } catch (const std::exception& e) {
        std::cout << "OBS read_negative_zero_prefix | exception=" << e.what()
                  << " [not a historical oracle]\n";
    }
}
} // namespace

int main() {
    // STRICT ONLY for control flow and reset of cell 0021 to +1.
    // Do NOT assert the resulting sign of cells 0020 or 0200: they were
    // written by 01 operating on (-0)+(+0), retained as OBS in D4.
    run("write_negative_zero_control_iteration", false, WRITE_ZERO_CONTROL,
        [](Kyiv_t&) {}, [](const Kyiv_t& m) {
            return m.C_reg == 0123 && m.A_reg == 0201 && m.Loop_reg == 0 &&
                   m.kmem.read_memory(0021) == 1 && !m.T_reg;
        });
    std::vector<Transition> write_wrap(WRITE_ZERO_CONTROL.begin()+1,
                                       WRITE_ZERO_CONTROL.end());
    write_wrap.back().next_pc = 0137;
    run("write_control_wrap_1777_to_zero_exit", false, write_wrap,
        [](Kyiv_t& m) { m.A_reg=01777; m.Loop_reg=0; },
        [](const Kyiv_t& m) {
            return m.C_reg == 0137 && m.A_reg == 0 && m.Loop_reg == 0 &&
                   m.kmem.read_memory(0021) == 1 && !m.T_reg;
        });
    run("read_negative_zero_prepared_tail", false, READ_ZERO_TAIL,
        [](Kyiv_t& m) {
            m.A_reg=0200; m.Loop_reg=0;
            m.kmem.write_memory(0020, SIGN);
            m.kmem.write_memory(0200, SIGN);
        },
        [](const Kyiv_t& m) {
            return m.C_reg == 0141 && m.A_reg == 0201 && m.Loop_reg == 0 &&
                   m.kmem.read_memory(0021) == 1 && !m.T_reg;
        });
    run("read_prepared_mismatch_historical_stop", false,
        {{0144,0145,true},{0145,ANY_NEXT_PC,false}},
        [](Kyiv_t& m) {
            m.A_reg=0200; m.Loop_reg=0;
            m.kmem.write_memory(0020, SIGN);
            m.kmem.write_memory(0200, 1);
        },
        [](const Kyiv_t& m) {
            return m.A_reg == 0200 && m.Loop_reg == 0 && m.T_reg;
        });
    // POLICY: 05 takes a branch on 0==0; all numeric inputs to 01 here are
    // positive and nonzero, so this does not require a zero-sign assumption.
    run("write_two_positive_iterations_opcode05_equality", true,
        concat(WRITE_POSITIVE_ONE, WRITE_POSITIVE_SECOND),
        [](Kyiv_t& m) { m.kmem.write_memory(0021, 1); },
        [](const Kyiv_t& m) {
            return m.C_reg == 0123 && m.A_reg == 0202 && m.Loop_reg == 0 &&
                   m.kmem.read_memory(0200) == 1 &&
                   m.kmem.read_memory(0201) == 2 &&
                   m.kmem.read_memory(0020) == 2 &&
                   m.kmem.read_memory(0021) == 4 && !m.T_reg;
        });
    run("read_two_positive_iterations_opcode05_equality", true,
        concat(READ_POSITIVE_ONE, READ_POSITIVE_SECOND),
        [](Kyiv_t& m) {
            m.kmem.write_memory(0021, 1);
            m.kmem.write_memory(0200, 1);
            m.kmem.write_memory(0201, 2);
        },
        [](const Kyiv_t& m) {
            return m.C_reg == 0141 && m.A_reg == 0202 && m.Loop_reg == 0 &&
                   m.kmem.read_memory(0020) == 2 &&
                   m.kmem.read_memory(0021) == 4 && !m.T_reg;
        });
    observe_read_negative_zero_prefix();
    std::cout << "ISA-06 D5 STRICT=" << strict_pass << '/' << strict_total
              << " POLICY=" << policy_pass << '/' << policy_total
              << " DOC-MISMATCH=" << (strict_total-strict_pass)
              << " POLICY-FAIL=" << (policy_total-policy_pass)
              << " OBS=1\n";
    return (strict_pass == strict_total && policy_pass == policy_total) ? 0 : 1;
}
