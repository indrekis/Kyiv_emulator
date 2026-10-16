// ISA-05 D1 — flow-control characterization (GY62 pp. 12–14, 17).
// CPU remains unchanged. Tests distinguish STRICT, DOC-MISMATCH, and OBS.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include <utility>
#include "kyiv.h"
#include "asm_disasm.h"

// Keep the CPU-only probe independent of CLI main() in asm_disasm.cpp.
int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t NEG = uint64_t{1} << 40;
constexpr uint64_t PC = 0100;
constexpr uint64_t BRANCH = 0250;
int strict_pass = 0, strict_fail = 0, doc_mismatch = 0, doc_match = 0, obs_count = 0;

std::string oct(uint64_t v) {
    std::ostringstream s; s << std::oct << v; return s.str();
}
uint64_t instruction(unsigned op, uint64_t a1=2, uint64_t a2=3, uint64_t a3=BRANCH) {
    return (uint64_t(op) << 36) | (a1 << 24) | (a2 << 12) | a3;
}
struct Silence {
    std::ostringstream output;
    std::streambuf* previous;
    Silence() : previous(std::cout.rdbuf(output.rdbuf())) {}
    ~Silence() { std::cout.rdbuf(previous); }
};
bool step(Kyiv_t& m, unsigned op, uint64_t a1=2, uint64_t a2=3, uint64_t a3=BRANCH) {
    m.kmem.write_memory(PC,instruction(op,a1,a2,a3));
    m.C_reg=PC;
    Silence silence;
    return m.execute_opcode();
}
struct Result {
    uint64_t pc=0, p=0, loop=0, a=0, destination=0;
    bool continues=false, stopped=false;
};
Result snap(const Kyiv_t& m, bool go, uint64_t dst=4) {
    return {m.C_reg,m.P_reg,m.Loop_reg,m.A_reg,m.kmem.read_memory(dst),go,m.T_reg};
}
std::string detail(const Result& x) {
    return "C=" + oct(x.pc) + " P=" + oct(x.p) + " Cy=" + oct(x.loop) +
           " A=" + oct(x.a) + " dest=" + oct(x.destination) +
           " continues=" + std::to_string(x.continues) +
           " stopped=" + std::to_string(x.stopped);
}
void strict(const char* name, bool ok, const std::string& evidence) {
    (ok ? strict_pass : strict_fail)++;
    std::cout << (ok ? "PASS " : "FAIL ") << name << " | " << evidence << '\n';
}
void documentary(const char* name, bool ok, const std::string& evidence) {
    (ok ? doc_match : doc_mismatch)++;
    std::cout << (ok ? "DOC-PASS " : "DOC-MISMATCH ") << name << " | " << evidence << '\n';
}
void observe(const char* name, const std::string& evidence) {
    ++obs_count;
    std::cout << "OBS " << name << " | " << evidence << " [no historical assertion]\n";
}
template<class F>
void run(const char* name, const char* kind, F&& f) {
    try { f(); }
    catch (const std::exception& e) {
        if (std::string(kind)=="S") strict(name,false,std::string("exception: ")+e.what());
        else if (std::string(kind)=="D") documentary(name,false,std::string("exception: ")+e.what());
        else observe(name,std::string("exception: ")+e.what());
    } catch (...) {
        if (std::string(kind)=="S") strict(name,false,"unexpected exception");
        else if (std::string(kind)=="D") documentary(name,false,"unexpected exception");
        else observe(name,"unexpected exception");
    }
}
Result comparison(unsigned op, uint64_t first, uint64_t second) {
    Kyiv_t m;
    m.kmem.write_memory(2,first);
    m.kmem.write_memory(3,second);
    bool go=step(m,op);
    return snap(m,go);
}
bool branch(const Result& r, uint64_t expected) {
    return r.pc==expected && r.continues && !r.stopped;
}
} // namespace

int main(int argc, char** argv) {
    const bool enforce_doc = argc > 1 && std::string(argv[1])=="--enforce-doc";
    // GY62 p. 17 explicitly states negative zero < positive zero.
    run("04_negative_less_positive", "S", [] {
        auto r=comparison(004,NEG|2,3); strict("04_negative_less_positive",branch(r,BRANCH),detail(r));
    });
    run("04_positive_greater_negative", "S", [] {
        auto r=comparison(004,2,NEG|3); strict("04_positive_greater_negative",branch(r,PC+1),detail(r));
    });
    run("04_minus_zero_below_plus_zero", "S", [] {
        auto r=comparison(004,NEG,0); strict("04_minus_zero_below_plus_zero",branch(r,BRANCH),detail(r));
    });
    run("04_plus_zero_not_below_minus_zero", "D", [] {
        auto r=comparison(004,0,NEG); documentary("04_plus_zero_not_below_minus_zero",branch(r,PC+1),detail(r));
    });
    run("04_equal_nonzero", "O", [] {
        auto r=comparison(004,7,7); observe("04_equal_nonzero",detail(r));
    });
    run("05_absolute_less", "S", [] {
        auto r=comparison(005,NEG|2,3); strict("05_absolute_less",branch(r,BRANCH),detail(r));
    });
    run("05_absolute_greater", "S", [] {
        auto r=comparison(005,NEG|3,2); strict("05_absolute_greater",branch(r,PC+1),detail(r));
    });
    run("05_equal_magnitudes", "O", [] {
        auto r=comparison(005,NEG|7,7); observe("05_equal_magnitudes",detail(r));
    });
    run("16_exact_equal_nonzero", "S", [] {
        auto r=comparison(016,NEG|7,NEG|7); strict("16_exact_equal_nonzero",branch(r,BRANCH),detail(r));
    });
    run("16_sign_difference_nonzero", "S", [] {
        auto r=comparison(016,7,NEG|7); strict("16_sign_difference_nonzero",branch(r,PC+1),detail(r));
    });
    run("16_pluszero_not_equal_minuszero", "D", [] {
        auto r=comparison(016,0,NEG); documentary("16_pluszero_not_equal_minuszero",branch(r,PC+1),detail(r));
    });
    run("16_minuszero_not_equal_pluszero", "D", [] {
        auto r=comparison(016,NEG,0); documentary("16_minuszero_not_equal_pluszero",branch(r,PC+1),detail(r));
    });
    run("31_positive_zero_to_second", "S", [] {
        Kyiv_t m; m.kmem.write_memory(2,0);
        bool go=step(m,031,2,0240,0250); auto r=snap(m,go);
        strict("31_positive_zero_to_second",branch(r,0240),detail(r));
    });
    run("31_negative_zero_to_third", "S", [] {
        Kyiv_t m; m.kmem.write_memory(2,NEG);
        bool go=step(m,031,2,0240,0250); auto r=snap(m,go);
        strict("31_negative_zero_to_third",branch(r,0250),detail(r));
    });
    run("30_minus_zero_call_saves_return_address", "S", [] {
        Kyiv_t m; m.kmem.write_memory(2,NEG); m.P_reg=0277;
        bool go=step(m,030,2,0240,0250); auto r=snap(m,go);
        strict("30_minus_zero_call_saves_return_address",branch(r,0250)&&r.p==0240,detail(r));
    });
    run("30_plus_zero_no_call", "S", [] {
        Kyiv_t m; m.kmem.write_memory(2,0); m.P_reg=0277;
        bool go=step(m,030,2,0240,0250); auto r=snap(m,go);
        strict("30_plus_zero_no_call",branch(r,PC+1)&&r.p==0277,detail(r));
    });
    run("32_return_ignores_address_fields", "S", [] {
        Kyiv_t m; m.P_reg=0350;
        bool go=step(m,032,0177,0200,0250); auto r=snap(m,go);
        strict("32_return_ignores_address_fields",branch(r,0350)&&r.p==0,detail(r));
    });
    run("26_begin_group_uses_fields_not_contents", "S", [] {
        Kyiv_t m; m.kmem.write_memory(2,0456);m.kmem.write_memory(3,0555);
        bool go=step(m,026,2,3,0250); auto r=snap(m,go);
        strict("26_begin_group_uses_fields_not_contents",branch(r,PC+1)&&r.loop==2&&r.a==3,detail(r));
    });
    run("26_begin_group_equal_addresses_branch", "S", [] {
        Kyiv_t m;
        bool go=step(m,026,2,2,0250); auto r=snap(m,go);
        strict("26_begin_group_equal_addresses_branch",branch(r,0250)&&r.loop==2&&r.a==2,detail(r));
    });
    run("27_end_group_at_limit", "S", [] {
        Kyiv_t m;m.A_reg=5;m.Loop_reg=8;
        bool go=step(m,027,3,0240,0250);auto r=snap(m,go);
        strict("27_end_group_at_limit",branch(r,0250)&&r.a==8,detail(r));
    });
    run("27_end_group_continue_loop", "S", [] {
        Kyiv_t m;m.A_reg=5;m.Loop_reg=9;
        bool go=step(m,027,3,0240,0250);auto r=snap(m,go);
        strict("27_end_group_continue_loop",branch(r,0240)&&r.a==8,detail(r));
    });
    run("34_indirect_load_by_field", "S", [] {
        Kyiv_t m;
        m.kmem.write_memory(2,instruction(000,0000,0005,0000));
        m.kmem.write_memory(5,012345);
        bool go=step(m,034,2,0,4);auto r=snap(m,go);
        strict("34_indirect_load_by_field",branch(r,PC+1)&&r.a==5&&r.destination==012345,detail(r));
    });
    std::cout << "ISA-05 D1 STRICT=" << strict_pass << '/' << (strict_pass+strict_fail)
              << " DOC-MISMATCH=" << doc_mismatch << " DOC-PASS=" << doc_match
              << " OBS=" << obs_count << " FAIL=" << strict_fail << '\n';
    return strict_fail || (enforce_doc && doc_mismatch) ? 1 : 0;
}
