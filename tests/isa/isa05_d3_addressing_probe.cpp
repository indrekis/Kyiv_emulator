// ISA-05 D3: control flow addressing and A/Cy/P register characterization.
// GY62, printed pp. 12-14, 54, 57-60. CPU remains unchanged in D3.
// STRICT: source-backed behavior; DOC-MISMATCH: known difference from a
// documented rule; OBS: disagreement/ambiguity in sources, no oracle.
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr uint64_t SIGN = uint64_t{1} << 40;
constexpr uint64_t MOD = 04000; // The 12th bit of an address field.
constexpr uint64_t PC = 0100;
constexpr uint64_t B = 0250;
int strict_ok = 0, strict_bad = 0, doc_ok = 0, doc_bad = 0, observations = 0;
std::string oct(uint64_t x) { std::ostringstream s; s << std::oct << x; return s.str(); }
uint64_t command(unsigned op, uint64_t a1, uint64_t a2, uint64_t a3) {
    return (uint64_t(op) << 36) | (a1 << 24) | (a2 << 12) | a3;
}
struct Mute {
    std::ostringstream data;
    std::streambuf* old;
    Mute(): old(std::cout.rdbuf(data.rdbuf())) {}
    ~Mute() { std::cout.rdbuf(old); }
};
bool execute(Kyiv_t& m, unsigned op, uint64_t a1, uint64_t a2, uint64_t a3) {
    m.C_reg = PC;
    m.kmem.write_memory(PC, command(op, a1, a2, a3));
    Mute muted;
    return m.execute_opcode();
}
struct Outcome {
    uint64_t c, p, cy, a, dst;
    bool go, stopped;
};
Outcome snap(const Kyiv_t& m, bool go, uint64_t dest=0006) {
    return {m.C_reg, m.P_reg, m.Loop_reg, m.A_reg,
            m.kmem.read_memory(dest), go, m.T_reg};
}
std::string detail(const Outcome& x) {
    return "C="+oct(x.c)+" P="+oct(x.p)+" Cy="+oct(x.cy)+
           " A="+oct(x.a)+" dest="+oct(x.dst)+
           " go="+std::to_string(x.go)+" stop="+std::to_string(x.stopped);
}
bool live(const Outcome& x, uint64_t c) {
    return x.go && !x.stopped && x.c == c;
}
void strict(const char* name, bool ok, const Outcome& v) {
    (ok ? strict_ok : strict_bad)++;
    std::cout << (ok ? "PASS " : "FAIL ") << name << " | " << detail(v) << '\n';
}
void document(const char* name, bool ok, const Outcome& v) {
    (ok ? doc_ok : doc_bad)++;
    std::cout << (ok ? "DOC-PASS " : "DOC-MISMATCH ") << name
              << " | " << detail(v) << '\n';
}
void observe(const char* name, const Outcome& v, const char* note) {
    observations++;
    std::cout << "OBS " << name << " | " << detail(v)
              << " | " << note << " [not an oracle]\n";
}
} // namespace

int main(int argc, char** argv) {
    const bool enforce_doc = argc>1 && std::string(argv[1])=="--enforce-doc";
    try {
        // 30 (UPP): modified source and target fields are allowed.
        {
            Kyiv_t m; m.A_reg=1; m.kmem.write_memory(3,SIGN);
            auto r=snap(m,execute(m,030,MOD|2,0240,B));
            strict("30_modified_first_field_reads_negative_zero",live(r,B)&&r.p==0240,r);
        }
        {
            Kyiv_t m; m.A_reg=2; m.kmem.write_memory(2,SIGN);
            auto r=snap(m,execute(m,030,2,0240,MOD|B));
            strict("30_modified_third_field_branches",live(r,B+2)&&r.p==0240,r);
        }
        {
            Kyiv_t m; m.A_reg=1; m.P_reg=0277; m.kmem.write_memory(3,0);
            auto r=snap(m,execute(m,030,MOD|2,0240,B));
            strict("30_positive_first_does_not_overwrite_P",live(r,PC+1)&&r.p==0277,r);
        }
        // 31 (UPCh): all addresses can be independently modified.
        {
            Kyiv_t m; m.A_reg=2; m.kmem.write_memory(2,0);
            auto r=snap(m,execute(m,031,2,MOD|0240,B));
            strict("31_positive_second_field_modified",live(r,0242),r);
        }
        {
            Kyiv_t m; m.A_reg=2; m.kmem.write_memory(2,SIGN);
            auto r=snap(m,execute(m,031,2,0240,MOD|B));
            strict("31_negative_third_field_modified",live(r,B+2),r);
        }
        {
            Kyiv_t m; m.A_reg=1; m.kmem.write_memory(3,SIGN);
            auto r=snap(m,execute(m,031,MOD|2,0240,B));
            strict("31_negative_first_field_modified",live(r,B),r);
        }
        // 26 (NGO) / 27 (OGO): unmodified fields are direct constants.
        {
            Kyiv_t m; m.A_reg=017; m.Loop_reg=020;
            auto r=snap(m,execute(m,026,6,7,B));
            strict("26_unmodified_fields_are_constants",live(r,PC+1)&&r.cy==6&&r.a==7,r);
        }
        {
            Kyiv_t m; m.A_reg=017;
            auto r=snap(m,execute(m,026,7,7,B));
            strict("26_equal_initial_group_values_branch",live(r,B)&&r.cy==7&&r.a==7,r);
        }
        {
            Kyiv_t m; m.A_reg=3; m.Loop_reg=4;
            auto r=snap(m,execute(m,027,MOD|1,0240,B));
            strict("27_first_field_step_not_modified",live(r,B)&&r.a==4,r);
        }
        {
            Kyiv_t m; m.A_reg=3; m.Loop_reg=6;
            auto r=snap(m,execute(m,027,1,0240,B));
            strict("27_continue_when_counter_below_limit",live(r,0240)&&r.a==4,r);
        }
        // 34 (F): extract second address of a fetched word, not content of
        // the current instruction's second field.
        {
            Kyiv_t m; m.A_reg=1;
            m.kmem.write_memory(3,command(0,0,5,0)); m.kmem.write_memory(5,012345);
            auto r=snap(m,execute(m,034,MOD|2,0170,6),6);
            strict("34_indirect_modified_first_address",live(r,PC+1)&&r.a==5&&r.dst==012345,r);
        }
        {
            Kyiv_t m; m.A_reg=1;
            m.kmem.write_memory(2,command(0,0,5,0)); m.kmem.write_memory(5,012345);
            auto r=snap(m,execute(m,034,2,0170,MOD|6),7);
            strict("34_modified_destination_uses_previous_A",live(r,PC+1)&&r.a==5&&r.dst==012345,r);
        }
        {
            Kyiv_t m; m.A_reg=1;
            m.kmem.write_memory(2,command(0,0,5,0)); m.kmem.write_memory(5,012345);
            auto r=snap(m,execute(m,034,2,MOD|0160,6),6);
            strict("34_current_second_field_ignored",live(r,PC+1)&&r.a==5&&r.dst==012345,r);
        }
        {
            Kyiv_t m; m.kmem.write_memory(2,command(0,0,5,0)); m.kmem.write_memory(5,012345);
            auto r=snap(m,execute(m,034,2,0,0),0);
            strict("34_destination_zero_discards_transfer",live(r,PC+1)&&r.a==5&&r.dst==0,r);
        }
        // Return address effect (only C change asserted in STRICT here).
        {
            Kyiv_t m; m.P_reg=0350;
            auto r=snap(m,execute(m,032,015,016,017));
            strict("32_return_uses_P_address",live(r,0350),r);
        }
        // DOCUMENTED MISMATCHES: recorded but not fixed by D3.
        {
            Kyiv_t m; m.P_reg=0350;
            auto r=snap(m,execute(m,032,0,0,0));
            document("32_formal_description_clears_P",live(r,0350)&&r.p==0,r);
        }
        {
            Kyiv_t m; m.A_reg=1;
            auto r=snap(m,execute(m,026,MOD|010,011,B));
            document("26_first_field_is_unmodified_constant",live(r,PC+1)&&r.cy==010&&r.a==011,r);
        }
        {
            Kyiv_t m; m.A_reg=1;
            auto r=snap(m,execute(m,026,010,MOD|011,B));
            document("26_second_field_is_unmodified_constant",live(r,PC+1)&&r.cy==010&&r.a==011,r);
        }
        {
            Kyiv_t m; m.A_reg=01777; m.Loop_reg=0;
            auto r=snap(m,execute(m,027,1,0240,B));
            document("27_ten_bit_A_wrap",live(r,B)&&r.a==0,r);
        }
        // OBS: inconsistent written descriptions; require reconstruction.
        {
            Kyiv_t m; m.A_reg=1; m.kmem.write_memory(2,SIGN);
            auto r=snap(m,execute(m,030,2,MOD|0240,B));
            observe("30_return_address_second_field_modifier",r,
                "GY62 p.13: a2; p.57: a2+e2*A");
        }
        {
            Kyiv_t m; m.A_reg=1; m.Loop_reg=020;
            auto r=snap(m,execute(m,026,010,011,MOD|B));
            observe("26_third_field_modifier",r,"special group-modifier rule unresolved");
        }
        {
            Kyiv_t m; m.A_reg=1; m.Loop_reg=020;
            auto r=snap(m,execute(m,027,1,MOD|0240,MOD|B));
            observe("27_second_third_field_modifiers",r,"field status needs table-level check");
        }
        {
            Kyiv_t m; m.kmem.write_memory(2,command(0,0,02005,0));
            auto r=snap(m,execute(m,034,2,0,6),6);
            observe("34_fetched_field_over_10_bit_A_range",r,
                "GY62 p.54 calls A 10 bits; encoding allows a larger field");
        }
    } catch (const std::exception& e) {
        strict_bad++;
        std::cerr << "FAIL unhandled exception: " << e.what() << '\n';
    } catch (...) {
        strict_bad++;
        std::cerr << "FAIL unhandled non-standard exception\n";
    }
    std::cout << "ISA-05 D3 STRICT=" << strict_ok << "/" << (strict_ok+strict_bad)
              << " DOC-PASS=" << doc_ok << " DOC-MISMATCH=" << doc_bad
              << " OBS=" << observations << " FAIL=" << strict_bad << '\n';
    return strict_bad || (enforce_doc && doc_bad) ? 1 : 0;
}
