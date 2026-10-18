// ISA-07 D11-A: REAL Kyiv_t opcode 21 host behavior observations only.
// Does NOT validate historical paper-tape encoding or historical IO errors.
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }

namespace {
constexpr word_t ins(unsigned op, unsigned a, unsigned b, unsigned c) {
    return (word_t(op) << 36) | (word_t(a) << 24) | (word_t(b) << 12) | word_t(c);
}
std::string octal(std::uint64_t n) {
    std::ostringstream s; s << std::oct << n; return s.str();
}
}

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string mode = argv[1];
    bool single = mode == "single";
    bool h1 = mode == "h1";
    constexpr addr_t pc=0100, first=0200, last=0203;
    constexpr word_t sentinel = 01234567012345ULL;
    const word_t follow=ins(017, 0300, 0301, 0302);
    try {
        Kyiv_t m;
        for (addr_t i=first; i<=last; ++i) m.kmem.write_memory(i,sentinel);
        m.kmem.write_memory(0300,5);
        m.kmem.write_memory(0301,3);
        m.kmem.write_memory(0302,0);
        m.kmem.write_memory(pc, ins(021,first,single?first:0202,0120));
        m.kmem.write_memory(pc+1,follow);
        m.kmem.write_memory(0120,ins(033,0,0,0));
        m.C_reg=pc; m.K_reg=0; m.h=h1?1:0;
        std::vector<word_t> before;
        for(addr_t i=0;i<02000;++i) before.push_back(m.kmem.read_memory(i));
        bool ok=false; std::string error="NONE";
        try { m.execute_opcode(); ok=true; }
        catch (const std::exception& e) { error=e.what(); }
        catch (...) { error="NONSTD"; }
        const auto pc1=m.C_reg;
        const auto k1=m.K_reg;
        const auto h1observed=m.h;
        unsigned changed=0; bool outside=false;
        for(addr_t i=0;i<02000;++i) {
            if(m.kmem.read_memory(i)!=before[i]) {
                ++changed;
                if(i<first || i>0202) outside=true;
            }
        }
        bool next=false; bool k2=false;
        if(ok) {
            try { next=m.execute_opcode(); k2=(m.K_reg==follow); }
            catch (...) { error="STEP2_EXCEPTION"; }
        }
        std::cout << "D11A-OBS mode=" << mode
                  << " status=" << (ok?"OK":"THROW")
                  << " pc1=" << octal(pc1)
                  << " k1=" << (k1==(ok?follow:ins(021,first,single?first:0202,0120)))
                  << " h1=" << h1observed
                  << " changed=" << changed
                  << " outside=" << outside
                  << " w0=" << octal(m.kmem.read_memory(first))
                  << " w1=" << octal(m.kmem.read_memory(first+1))
                  << " w2=" << octal(m.kmem.read_memory(first+2))
                  << " next=" << next
                  << " k2=" << k2
                  << " xor=" << m.kmem.read_memory(0302)
                  << " long_bits=" << (sizeof(long)*8)
                  << " error_kind=" << (error=="NONE"?"NONE":"CONVERSION_OR_IO")
                  << " HOST_OBSERVATION=1 HARDWARE_ORACLE=0\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D11A-PROBE-ERROR " << e.what() << '\n';
        return 3;
    }
}
