// D14-C2-H2/P2. Genuine Kyiv_t execution; this is NOT a synthetic opcode engine.
#include "kyiv.h"
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;
// This real-CPU probe intentionally replaces only diagnostic disassembly.
// Opcode execution remains in the linked src/main.cpp Kyiv_t implementation.
int disassembly(const uint64_t&, Kyiv_memory_t&, const addr3_t&) { return 0; }
using word = std::uint64_t;
static constexpr word SIGN = word{1}<<40;
static constexpr word MASK = (word{1}<<41)-1;
static word ins(unsigned op,unsigned a,unsigned b,unsigned c) {
    return (word(op)<<36)|(word(a)<<24)|(word(b)<<12)|word(c);
}
static void need(bool cond,const std::string& what) {
    if(!cond) throw std::runtime_error("CHECK_"+what);
}
struct silent {
    std::ostringstream sink;
    std::streambuf* old;
    silent():old(std::cout.rdbuf(sink.rdbuf())){}
    ~silent(){std::cout.rdbuf(old);}
};
static void good(Kyiv_t& cpu,addr_t pc,addr_t expected_c,word expected_k) {
    cpu.C_reg=pc;
    bool executed;
    { silent quiet; executed=cpu.execute_opcode(); }
    need(executed,"STEP_RETURN");
    need(cpu.C_reg==expected_c,"SUCCESS_C");
    need(cpu.K_reg==expected_k,"SUCCESS_K");
    need(cpu.A_reg==017,"SUCCESS_A");
}
static void fails(Kyiv_t& cpu,addr_t pc,const std::string& tag) {
    cpu.C_reg=pc;
    const word cmd=cpu.kmem.read_memory(pc);
    std::vector<word> before;
    for(addr_t i=0;i<02000;++i) before.push_back(cpu.kmem.read_memory(i));
    const auto a=cpu.A_reg;
    bool threw=false;
    { silent quiet;
      try { (void)cpu.execute_opcode(); }
      catch(const std::exception&) {threw=true;}
    }
    need(threw,"EXPECTED_REJECTION_"+tag);
    need(cpu.C_reg==pc,"REJECT_C_"+tag);
    need(cpu.K_reg==cmd,"REJECT_K_FETCH_"+tag);
    need(cpu.A_reg==a,"REJECT_A_"+tag);
    for(addr_t i=0;i<02000;++i)
        need(cpu.kmem.read_memory(i)==before.at(static_cast<std::size_t>(i)),
             "REJECT_RAM_"+tag);
}
int main(int argc,char**argv) {
    if(argc!=3) return 3;
    const fs::path path=argv[1];
    const std::string scenario=argv[2];
    try {
        Kyiv_t cpu;
        cpu.A_reg=017;
        const kyiv_drum_media::geometry g{"cpu-optin-2x4",3,2,4};
        if(scenario=="legacy") {
            const auto p=ins(025,1,0100,3);
            cpu.kmem.write_memory(0100,p);
            cpu.kmem.write_memory(0101,ins(033,0,0,0));
            good(cpu,0100,0101,cpu.kmem.read_memory(0101));
            need(cpu.drum_num_write==0100 && cpu.drum_zone_write==3,"LEGACY_UNCHANGED");
            need(!cpu.has_experimental_drum(),"LEGACY_UNATTACHED");
            std::cout<<"D14C2H2P2-CASE legacy PASS CPU_REAL=1\n";
            return 0;
        }
        cpu.attach_experimental_drum(path,g,
            kyiv_drum_host_address::policy::a3_linear_v1,1);
        need(cpu.has_experimental_drum(),"ATTACHED");
        if(scenario=="attach-rollback") {
            bool threw=false;
            try {cpu.attach_experimental_drum(path.string()+".missing",g,
               kyiv_drum_host_address::policy::a3_linear_v1,1);}
            catch(const std::exception&) {threw=true;}
            need(threw && cpu.has_experimental_drum(),"ATTACH_ROLLBACK");
            cpu.detach_experimental_drum();
            need(!cpu.has_experimental_drum(),"DETACH");
            std::cout<<"D14C2H2P2-CASE attach-rollback PASS CPU_REAL=1\n";
            return 0;
        }
        const auto prep_write=ins(025,1,0100,3);
        const auto prep_read=ins(025,0,0100,3);
        const auto write_cmd=ins(023,0200,0202,0102);
        const auto read_cmd=ins(024,0220,0222,0221); // branch INSIDE overwritten span
        cpu.kmem.write_memory(0100,prep_write);
        cpu.kmem.write_memory(0101,write_cmd);
        cpu.kmem.write_memory(0102,prep_read);
        cpu.kmem.write_memory(0103,read_cmd);
        cpu.kmem.write_memory(0104,ins(033,0,0,0));
        cpu.kmem.write_memory(0200,0); // +0
        cpu.kmem.write_memory(0201,SIGN); // -0
        cpu.kmem.write_memory(0202,MASK); // -maximum magnitude
        cpu.kmem.write_memory(0220,01234);
        cpu.kmem.write_memory(0221,0567);
        cpu.kmem.write_memory(0222,0765);
        if(scenario=="success") {
            good(cpu,0100,0101,write_cmd);
            need(cpu.experimental_drum->write_prepared(),"WRITE_PREPARED");
            need(!cpu.experimental_drum->read_prepared(),"READ_NOT_PREPARED");
            good(cpu,0101,0102,prep_read);
            need(cpu.experimental_drum->snapshot().inspect({0,0,3}).word==0,
                 "WRITE_SLOT3");
            need(cpu.experimental_drum->snapshot().inspect({0,1,0}).word==SIGN,
                 "WRITE_SLOT4");
            good(cpu,0102,0103,read_cmd);
            need(cpu.experimental_drum->write_prepared() &&
                 cpu.experimental_drum->read_prepared(),"BOTH_PREPARED");
            good(cpu,0103,0221,SIGN); // K must reflect the NEW RAM contents.
            need(cpu.kmem.read_memory(0220)==0,"READ_POS_ZERO");
            need(cpu.kmem.read_memory(0221)==SIGN,"READ_NEG_ZERO");
            need(cpu.kmem.read_memory(0222)==MASK,"READ_NEG_MAX");
        } else if(scenario=="unprepared-write") {
            fails(cpu,0101,scenario);
        } else if(scenario=="unprepared-read") {
            fails(cpu,0103,scenario);
        } else if(scenario=="bad-prepare") {
            cpu.kmem.write_memory(0100,ins(025,1,0101,3));
            fails(cpu,0100,scenario);
            need(!cpu.experimental_drum->write_prepared(),"NO_PARTIAL_PREP");
        } else if(scenario=="bad-pin") {
            cpu.kmem.write_memory(0100,ins(025,1,0200,3));
            fails(cpu,0100,scenario);
        } else if(scenario=="bad-mark") {
            cpu.kmem.write_memory(0100,prep_write|(word{1}<<23));
            fails(cpu,0100,scenario);
        } else if(scenario=="bad-direction") {
            cpu.kmem.write_memory(0100,ins(025,2,0100,3));
            fails(cpu,0100,scenario);
        } else if(scenario=="bad-word") {
            good(cpu,0100,0101,write_cmd);
            cpu.kmem.write_memory(0201,word{1}<<45);
            fails(cpu,0101,scenario);
        } else if(scenario=="bad-ram") {
            good(cpu,0100,0101,write_cmd);
            cpu.kmem.write_memory(0101,ins(023,0,0,0102));
            fails(cpu,0101,scenario);
        } else if(scenario=="bad-next-fetch") {
            // 04000 is NOT an encodable a3 address: it is the A3 mark.
            // Instead put the actual opcode 25 at the last ROM address;
            // its next-instruction prefetch at 04000 must fail before prepare.
            cpu.kmem.write_rom(03777,prep_write);
            fails(cpu,03777,scenario);
            need(!cpu.experimental_drum->write_prepared(),"NO_PREP_ON_BAD_PREFETCH");
        } else if(scenario=="end-of-drum") {
            cpu.kmem.write_memory(0100,ins(025,1,0100,7));
            good(cpu,0100,0101,write_cmd);
            fails(cpu,0101,scenario); // slot 7 and two more => out of drum
        } else if(scenario=="unwritten") {
            good(cpu,0102,0103,read_cmd);
            fails(cpu,0103,scenario);
        } else if(scenario=="fs-fail") {
            good(cpu,0100,0101,write_cmd);
            const fs::path backup=path.string()+".hold";
            fs::rename(path,backup);
            fs::create_directory(path);
            try {
                fails(cpu,0101,scenario);
                need(cpu.experimental_drum->snapshot().written_count()==0,
                     "FS_MEDIA_ROLLBACK");
            } catch (...) {
                fs::remove(path);fs::rename(backup,path);throw;
            }
            fs::remove(path);fs::rename(backup,path);
        } else {
            throw std::runtime_error("UNKNOWN_SCENARIO");
        }
        std::cout<<"D14C2H2P2-CASE "<<scenario
                 <<" PASS CPU_REAL=1 C="<<cpu.C_reg<<" K="<<cpu.K_reg
                 <<" A="<<cpu.A_reg<<"\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"D14C2H2P2-FAIL "<<scenario<<" "<<e.what()<<"\n";
        return 2;
    }
}
