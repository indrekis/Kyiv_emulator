#include <array>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include "kyiv.h"

// This ISA probe intentionally does not link the standalone disassembler CLI,
// which defines its own main(). The disassembly hook is diagnostic only.
int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) {
    return 0;
}

namespace {
constexpr word_t SIGN = word_t{1} << 40;
constexpr word_t MASK = (word_t{1} << 41) - 1;
constexpr std::array<addr_t, 3> NK{{03000, 03001, 03002}};

void require(bool ok, const std::string& reason) {
    if (!ok) throw std::runtime_error(reason);
}
template<class F> void expect_throw(F f, const std::string& reason) {
    try { f(); } catch (const std::exception&) { return; }
    throw std::runtime_error(reason);
}
struct Silence {
    std::ostringstream sink;
    std::ios_base::fmtflags flags = std::cout.flags();
    std::streambuf* old = std::cout.rdbuf(sink.rdbuf());
    ~Silence() { std::cout.rdbuf(old); std::cout.flags(flags); }
};
}

int main() {
    int policy = 0;
    try {
        Kyiv_memory_t mem;
        const std::array<word_t, 3> cab{{SIGN, 0, MASK}};
        const std::array<word_t, 3> pnl{{0, SIGN, 0123456701234ULL}};
        for (std::size_t i = 0; i < NK.size(); ++i) {
            mem.write_rom(NK[i], cab[i]);
            require(mem.read_memory(NK[i]) == cab[i], "default must preserve cabinet storage");
            require(!mem.is_panel_nk_selected(NK[i]), "default source must be cabinet");
            mem.set_panel_nk_word(NK[i], pnl[i]);
        }
        for (unsigned bits = 0; bits < 8; ++bits) {
            for (std::size_t i = 0; i < NK.size(); ++i) {
                const bool panel = (bits & (1u << i)) != 0;
                mem.select_panel_nk(NK[i], panel);
                require(mem.is_panel_nk_selected(NK[i]) == panel, "selector state mismatch");
                require(mem.read_memory(NK[i]) == (panel ? pnl[i] : cab[i]), "8-way NK selection mismatch");
            }
            ++policy;
            std::cout << "POLICY-PASS nk_configuration_" << bits << " selected_mask=" << bits << '\n';
        }
        Kyiv_memory_t fresh;
        expect_throw([&]{ fresh.select_panel_nk(03000, true); }, "unconfigured panel selection accepted");
        expect_throw([&]{ fresh.set_panel_nk_word(03000, MASK + 1); }, "42-bit panel code accepted");
        expect_throw([&]{ fresh.set_panel_nk_word(03003, 1); }, "undocumented selector address accepted");
        expect_throw([&]{ fresh.select_panel_nk(03007, true); }, "undocumented selector switch accepted");
        require(!fresh.is_panel_nk_selected(03000), "rejected selection changed state");
        ++policy;
        std::cout << "POLICY-PASS nk_fail_closed_guards\n";

        mem.set_panel_nk_word(03000, 0); // operator sets +0
        mem.select_panel_nk(03000, true);
        mem.write_rom(03000, SIGN); // cabinet retains -0 independently
        require(mem.read_memory(03000) == 0, "ROM write overwrote selected panel word");
        mem.select_panel_nk(03000, false);
        require(mem.read_memory(03000) == SIGN, "cabinet signed zero was lost");
        expect_throw([&]{ mem.write_memory(03000, 0); }, "CPU RAM write into NK accepted");
        require(mem.read_memory(03000) == SIGN, "rejected RAM write changed cabinet");
        ++policy;
        std::cout << "POLICY-PASS nk_independent_cabinet_and_panel_writes\n";

        mem.set_panel_nk_word(03002, MASK);
        mem.select_panel_nk(03002, true);
        require(mem.read_memory(03002) == MASK, "41-bit all-ones machine code lost");
        mem.set_panel_nk_word(03002, 0);
        require(mem.read_memory(03002) == 0, "panel reprogramming not live");
        mem.select_panel_nk(03002, false);
        require(mem.read_memory(03002) == MASK, "cabinet code changed through panel");
        require(mem.read_memory(03003) == 0, "unrelated ROM address affected");
        ++policy;
        std::cout << "POLICY-PASS nk_full_41_bit_and_unrelated_rom\n";

        Kyiv_t cpu;
        cpu.kmem.write_memory(0100, 0'31'3000'0022'0177ULL);
        cpu.kmem.write_rom(03000, 0); // cabinet +0
        cpu.kmem.set_panel_nk_word(03000, SIGN); // panel -0
        cpu.kmem.select_panel_nk(03000, false);
        cpu.C_reg = 0100;
        cpu.T_reg = false;
        {
            Silence suppress;
            require(cpu.execute_opcode(), "unexpected CPU stop in cabinet branch");
        }
        require(cpu.C_reg == 0022, "cabinet +0 branch must route to 0022");
        cpu.kmem.select_panel_nk(03000, true);
        cpu.C_reg = 0100;
        cpu.T_reg = false;
        {
            Silence suppress;
            require(cpu.execute_opcode(), "unexpected CPU stop in panel branch");
        }
        require(cpu.C_reg == 0177, "panel -0 branch must route to 0177");
        ++policy;
        std::cout << "POLICY-PASS opcode31_observes_selected_NK3000_sign cabinet_next=0022 panel_next=0177\n";

        std::cout << "ISA-06 D8-P9 STRICT=0/0 DOC-MISMATCH=0 POLICY="
                  << policy << "/" << policy << " POLICY-FAIL=0 OBS=0\n";
        return policy == 12 ? 0 : 2;
    } catch (const std::exception& e) {
        std::cerr << "POLICY-FAIL nk_panel_memory_integration reason=" << e.what() << '\n';
        return 2;
    }
}
