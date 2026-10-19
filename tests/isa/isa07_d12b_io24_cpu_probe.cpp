// D12-B: two genuine CPU steps on success and whole-RAM nonmutation on error.
// Build with src/main.cpp (never src/asm_disasm.cpp, which owns main).
#include "kyiv.h"
#include <cstdint>
#include <exception>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
namespace {
constexpr word_t instruction(unsigned op, unsigned a, unsigned b, unsigned c) {
    return (word_t(op) << 36) | (word_t(a) << 24) | (word_t(b) << 12) | word_t(c);
}
std::string octword(word_t w) {
    std::ostringstream stream;
    stream << std::oct << w;
    return stream.str();
}
}
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const std::string mode(argv[1]);
    try {
        Kyiv_t m;
        constexpr addr_t pc=0100, lhs=0700, rhs=0701, dst=0702;
        const addr_t target=(mode=="altjump")?0130:0120;
        const addr_t a1=(mode=="single")?0201:(mode=="last-ram")?01777:
            (mode=="zero-discard")?0:(mode=="reversed")?0202:
            (mode=="ram-over")?02000:0200;
        const addr_t a2=(mode=="single"||mode=="last-ram"||
            mode=="zero-discard"||mode=="ram-over")?a1:
            (mode=="reversed")?0200:0202;
        const word_t first=instruction(024,static_cast<unsigned>(a1),
                                       static_cast<unsigned>(a2),static_cast<unsigned>(target));
        const word_t next=instruction(017,lhs,rhs,dst);
        m.kmem.write_memory(pc,first);
        m.kmem.write_memory(pc+1,instruction(033,0,0,0));
        m.kmem.write_memory(target,next);
        m.kmem.write_memory(lhs,5);
        m.kmem.write_memory(rhs,3);
        m.kmem.write_memory(dst,0);
        m.C_reg=pc;
        m.K_reg=0;
        m.drum_num_read=(mode=="track1")?1:
            (mode=="track-missing")?2:(mode=="negative-track")?-1:0;
        m.drum_zone_read=(mode=="zone2")?2:
            (mode=="zone-over")?99:(mode=="negative-zone")?-1:0;
        m.drum_num_write=4;
        m.drum_zone_write=6;
        const auto wasA=m.A_reg;
        const auto wasP=m.P_reg;
        const auto wasL=m.Loop_reg;
        const auto wasH=m.h;
        const bool wasT=m.T_reg;
        const int wasTrack=m.drum_num_read, wasZone=m.drum_zone_read;
        const int wasWriteTrack=m.drum_num_write, wasWriteZone=m.drum_zone_write;
        std::vector<word_t> before;
        before.reserve(02001);
        for (addr_t a=0;a<=02000;++a) before.push_back(m.kmem.read_memory(a));
        bool success=false, run1=false, run2=false;
        std::string reason="NONE";
        try {
            run1=m.execute_opcode();
            success=true;
        } catch (const std::runtime_error& e) {
            reason=e.what();
            if (reason.rfind("IO24: ",0)==0) reason.erase(0,6);
            else reason="UNEXPECTED_RUNTIME_ERROR";
        } catch (const std::exception&) {
            reason="UNEXPECTED_EXCEPTION";
        } catch (...) {
            reason="UNEXPECTED_OTHER";
        }
        const addr_t pc1=m.C_reg;
        const word_t k1=m.K_reg;
        std::size_t changed=0;
        bool outside=false;
        for (addr_t a=0;a<=02000;++a) {
            if (m.kmem.read_memory(a)!=before[static_cast<std::size_t>(a)]) {
                ++changed;
                if (a<a1 || a>a2 || a>=02000) outside=true;
            }
        }
        const bool stable=m.A_reg==wasA && m.P_reg==wasP &&
            m.Loop_reg==wasL && m.h==wasH && m.T_reg==wasT &&
            m.drum_num_read==wasTrack && m.drum_zone_read==wasZone &&
            m.drum_num_write==wasWriteTrack && m.drum_zone_write==wasWriteZone;
        if (success) run2=m.execute_opcode();
        std::cout << "D12B-CPU mode=" << mode << " status="
                  << (success?"OK":"ERROR") << " reason=" << reason
                  << " pc1=" << std::oct << pc1 << " pc2=" << m.C_reg << std::dec
                  << " k1=" << (k1==(success?next:first))
                  << " k2=" << (m.K_reg==(success?next:first))
                  << " stable=" << stable
                  << " outside=" << outside
                  << " changed=" << changed
                  << " ram=" << octword(m.kmem.read_memory(0200)) << '/'
                  << octword(m.kmem.read_memory(0201)) << '/'
                  << octword(m.kmem.read_memory(0202))
                  << " last=" << octword(m.kmem.read_memory(01777))
                  << " zero=" << octword(m.kmem.read_memory(0))
                  << " unmapped=" << octword(m.kmem.read_memory(02000))
                  << " xor=" << m.kmem.read_memory(dst)
                  << " steps=" << (success?2:1)
                  << " run=" << run1 << '/' << run2
                  << " HOST_POLICY=1 HARDWARE_ORACLE=0\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "D12B-PROBE-ERROR " << e.what() << '\n';
        return 3;
    }
}
