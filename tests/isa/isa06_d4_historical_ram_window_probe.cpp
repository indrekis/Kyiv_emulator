// ISA-06 D4: bounded windows of the historical fourth RAM diagnostic.
// GY62 printed pp. 170-171; no complete historical RAM-test claim.
// All machine words in HIST are transcribed at their printed addresses.
// ROM words 3012/3026/3042 are controlled test fixtures, not certified ROM.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <utility>
#include <vector>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
using W = uint64_t;
constexpr W SIGN = W{1} << 40;
constexpr W UPPER_MAG = W{1} << 39;
constexpr W RET = 0371;
constexpr W INITIAL_CY = 0654;

struct HistoricalWord { W address, word; };
// Source: GY62 (1962), printed p. 171, 'Четвертый тест ОЗУ'.
// Stored as complete 14-octal-digit words, NOT re-encoded from opcode fields.
constexpr HistoricalWord HIST[] = {
    {0120, 0'01'3012'0000'0017ULL},
    {0121, 0'01'0017'0000'0021ULL},
    {0122, 0'26'0000'0200'0000ULL},
    {0123, 0'01'0021'0000'0020ULL},
    {0127, 0'16'0021'3042'0133ULL},
    {0130, 0'16'0021'3026'0135ULL},
    {0131, 0'13'3012'0021'0021ULL},
    {0133, 0'01'3026'0000'0021ULL},
    {0135, 0'01'3012'0000'0021ULL},
    {0146, 0'16'0021'3042'0152ULL},
    {0147, 0'16'0021'3026'0154ULL},
    {0150, 0'13'3012'0021'0021ULL},
    {0152, 0'01'3026'0000'0021ULL},
    {0154, 0'01'3012'0000'0021ULL},
    {0156, 0'13'3012'0017'0017ULL},
    {0157, 0'16'0017'3042'0161ULL},
};

W printed_word(W pc) {
    for (const auto& h : HIST) if (h.address == pc) return h.word;
    throw std::logic_error("missing historical word");
}
struct Silence {
    std::ostringstream capture;
    std::streambuf* original;
    Silence():original(std::cout.rdbuf(capture.rdbuf())){}
    ~Silence(){std::cout.rdbuf(original);}
};
bool step(Kyiv_t& m){ Silence silence; return m.execute_opcode(); }

struct Step { W pc, next; };
struct Scenario {
    const char* name;
    std::vector<Step> trace;
    W initial_21, initial_17;
    W check_address, check_value;
    W expected_A, expected_Cy;
};

int passed = 0;
int total = 0;
void check(const Scenario& s) {
    ++total;
    try {
        Kyiv_t m;
        // Controlled ROM: these values agree with the current human-transcribed
        // mem/ROM.txt, but no independent historical ROM oracle is claimed.
        m.kmem.write_rom(03012, 1);         // left shift by one
        m.kmem.write_rom(03026, SIGN);      // negative zero code
        m.kmem.write_rom(03042, UPPER_MAG); // highest magnitude bit
        for (const auto& h : HIST) m.kmem.write_memory(h.address, h.word);
        m.kmem.write_memory(0021, s.initial_21);
        m.kmem.write_memory(0017, s.initial_17);
        m.kmem.write_memory(0020, 077);
        m.C_reg = s.trace.front().pc;
        m.P_reg = RET;
        m.A_reg = 0;
        m.Loop_reg = INITIAL_CY;
        bool ok = true;
        unsigned completed = 0;
        for (const auto& st : s.trace) {
            if (m.C_reg != st.pc) {ok=false;break;}
            bool running = step(m);
            ++completed;
            if (!running || m.T_reg || m.C_reg != st.next ||
                m.K_reg != printed_word(st.pc)) {ok=false;break;}
        }
        ok = ok && m.kmem.read_memory(s.check_address) == s.check_value &&
            m.A_reg == s.expected_A && m.Loop_reg == s.expected_Cy &&
            m.P_reg == RET;
        // In the setup window 0120-0123, three writes must agree,
        // not merely the final one; 0122 sets A/Cy from raw fields.
        if (s.trace.front().pc == 0120) {
            ok = ok && m.kmem.read_memory(0017) == 1 &&
                 m.kmem.read_memory(0021) == 1 &&
                 m.kmem.read_memory(0020) == 1;
        }
        passed += ok;
        std::cout << (ok ? "STRICT-PASS " : "DOC-MISMATCH ") << s.name
                  << " | steps=" << completed << '/' << s.trace.size()
                  << " C=" << std::oct << m.C_reg
                  << " mem[" << s.check_address << "]="
                  << m.kmem.read_memory(s.check_address)
                  << " expected=" << s.check_value
                  << " A=" << m.A_reg << " Cy=" << m.Loop_reg
                  << " P=" << m.P_reg << std::dec << '\n';
    } catch (const std::exception& ex) {
        std::cout << "DOC-MISMATCH " << s.name
                  << " | exception=" << ex.what() << '\n';
    }
}
// The historical program continues the matched-upper-bit branches with
// opcode 01 applied to -0 and +0. GY62 pp. 11-13 does not resolve that
// sign-of-zero result to a strict oracle; record the actual CPU behavior.
void observe_negative_zero_add(const char* name, W pc) {
    try {
        Kyiv_t m;
        m.kmem.write_rom(03026, SIGN);
        m.kmem.write_memory(pc, printed_word(pc));
        m.kmem.write_memory(0021, UPPER_MAG);
        m.C_reg = pc;
        const bool running = step(m);
        std::cout << "OBS " << name << " | K=" << std::oct << m.K_reg
                  << " result=" << m.kmem.read_memory(0021)
                  << " C=" << m.C_reg << std::dec << " running=" << running
                  << " stop=" << m.T_reg
                  << " [sign of (-0)+(+0) not a historical oracle]\n";
    } catch (const std::exception& ex) {
        std::cout << "OBS " << name << " | exception=" << ex.what()
                  << " [not a historical oracle]\n";
    }
}
} // namespace

int main() {
    // Addresses and all executing instructions are verbatim from GY62 p. 171.
    // Expected branches follow GY62 pp. 12-13; test inputs are synthetic.
    const std::vector<Scenario> tests = {
        {"setup_0120_0123", {{0120,0121},{0121,0122},{0122,0123},{0123,0124}},
            0,0,0020,1,0200,0},
        {"write_regular_0127_0130_0131", {{0127,0130},{0130,0131},{0131,0132}},
            1,0,0021,2,0,INITIAL_CY},
        {"write_upper_bit_branch_0127", {{0127,0133}},
            UPPER_MAG,0,0021,UPPER_MAG,0,INITIAL_CY},
        {"write_negative_zero_to_one_0130_0135", {{0130,0135},{0135,0136}},
            SIGN,0,0021,1,0,INITIAL_CY},
        {"write_positive_zero_distinct_0130_0131", {{0130,0131},{0131,0132}},
            0,0,0021,0,0,INITIAL_CY},
        {"read_regular_0146_0147_0150", {{0146,0147},{0147,0150},{0150,0151}},
            1,0,0021,2,0,INITIAL_CY},
        {"read_upper_bit_branch_0146", {{0146,0152}},
            UPPER_MAG,0,0021,UPPER_MAG,0,INITIAL_CY},
        {"read_negative_zero_to_one_0147_0154", {{0147,0154},{0154,0155}},
            SIGN,0,0021,1,0,INITIAL_CY},
        {"tail_0156_0157_upper_bit_branch", {{0156,0157},{0157,0161}},
            0,UPPER_MAG>>1,0017,UPPER_MAG,0,INITIAL_CY},
    };
    for (const auto& s:tests) check(s);
    observe_negative_zero_add("write_reset_0133_zero_sign", 0133);
    observe_negative_zero_add("read_reset_0152_zero_sign", 0152);
    std::cout << "ISA-06 D4 STRICT=" << passed << '/' << total
              << " DOC-MISMATCH=" << (total-passed)
              << " POLICY=0 OBS=2\n";
    return (passed == total) ? 0 : 1;
}
