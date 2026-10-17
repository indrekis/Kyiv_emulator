// ISA-06 D8-P8: full documented entry 0117 and both natural 39-cycle epochs, NEVER EXECUTE 0164.
// GY62 1962 printed pp. 120, 170-171; original 0117 plus all 39 P6 words.
// ROM and other initial registers remain controlled FIXTURES. Entry 0117 must clear poisoned RAM[0014].
// This is POLICY, NOT a certified hardware trace; no NK3000/3001 injection or implementation.
#include <array>
#include <cstdint>
#include <exception>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include "kyiv.h"
#include "asm_disasm.h"
int disassembly(const uint64_t&,Kyiv_memory_t&,const addr3_t&){return 0;}
namespace {
using W=uint64_t;
constexpr W SIGN=W{1}<<40, TOP_MAG=W{1}<<39;
constexpr W FIRST=0200,LAST=01777;
constexpr size_t CELLS=LAST-FIRST+1, MAX_STEPS=1350000;
struct HistoricalWord {W pc,word;};
// This list is copied verbatim from P4; structural audit compares every octal token.
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
constexpr HistoricalWord BRIDGE[] = {
    {0120, 0'01'3012'0000'0017ULL},
    {0121, 0'01'0017'0000'0021ULL},
    {0137, 0'01'0017'0000'0021ULL},
    {0156, 0'13'3012'0017'0017ULL},
    {0157, 0'16'0017'3042'0161ULL},
    {0160, 0'05'0000'0000'0121ULL},
};
constexpr HistoricalWord TAIL[] = {
    {0161, 0'31'0014'0162'0164ULL},
    {0162, 0'02'0000'0000'0014ULL},
    {0163, 0'05'0000'0000'0120ULL},
    {0164, 0'31'3000'0022'0177ULL},
    {0165, 0'33'0000'0001'0077ULL},
    {0166, 0'33'0000'0003'0177ULL},
};

constexpr HistoricalWord ENTRY[] = {
    {0117, 0'01'0000'0000'0014ULL},
};

W original(W pc){
  for(auto w:ENTRY)if(w.pc==pc)return w.word;
  for(auto w:HIST)if(w.pc==pc)return w.word;
  for(auto w:BRIDGE)if(w.pc==pc)return w.word;
  for(auto w:TAIL)if(w.pc==pc)return w.word;
  throw std::runtime_error("PC outside original fourth-test program");
}
std::string oct(W x){std::ostringstream s;s<<std::oct<<x;return s.str();}
struct NullBuf:std::streambuf {
  int overflow(int c)override{return traits_type::not_eof(c);}
  std::streamsize xsputn(const char*,std::streamsize n)override{return n;}
};
struct Silence {
  NullBuf sink; std::streambuf* before;
  Silence():before(std::cout.rdbuf(&sink)){}
  ~Silence(){std::cout.rdbuf(before);}
};
struct Cycle {
  unsigned n=0,epoch=0;
  W sign=0,pattern=0,next_pattern=0;
  size_t steps=0,writes=0,reads=0,negative_writes=0,negative_reads=0;
  bool handoff=false;
  std::array<W,CELLS> snapshot{};
};
void init(Kyiv_t& cpu){
  // Repo mem/ROM.txt has these entries, but not a certified historical ROM dump.
  cpu.kmem.write_rom(03012,1);
  cpu.kmem.write_rom(03026,SIGN);
  cpu.kmem.write_rom(03042,TOP_MAG);
  for(auto w:ENTRY)cpu.kmem.write_memory(w.pc,w.word);
  for(auto w:HIST)cpu.kmem.write_memory(w.pc,w.word);
  for(auto w:BRIDGE)cpu.kmem.write_memory(w.pc,w.word);
  for(auto w:TAIL)cpu.kmem.write_memory(w.pc,w.word);
  cpu.kmem.write_memory(0014,SIGN); // deliberate pre-entry poison: historical 0117 must overwrite -0 to +0
  cpu.kmem.write_memory(0017,077);
  cpu.kmem.write_memory(0020,077);
  cpu.kmem.write_memory(0021,077);
  for(W a=FIRST;a<=LAST;++a)cpu.kmem.write_memory(a,077);
  cpu.C_reg=0117;cpu.A_reg=0;cpu.Loop_reg=077;
  cpu.P_reg=0371;cpu.T_reg=false;
}
struct Journal {
  std::ofstream file;
  explicit Journal(const std::string& path){
    if(path.empty())return;
    file.open(path,std::ios::binary|std::ios::trunc);
    if(!file)throw std::runtime_error("cannot open trace file");
    file<<"cycle\tepoch\tpattern\tsign\tsteps\twrites\treads\tnegative_writes\tnegative_reads\tcompleted_by\tnext_pattern\n";
  }
  void cycle(const Cycle& c,const std::string& by){
    if(!file)return;
    file<<c.n<<'\t'<<c.epoch<<'\t'<<oct(c.pattern)<<'\t'<<oct(c.sign)
        <<'\t'<<c.steps<<'\t'<<c.writes<<'\t'<<c.reads<<'\t'
        <<c.negative_writes<<'\t'<<c.negative_reads<<'\t'
        <<by<<'\t'<<oct(c.next_pattern)<<'\n';
  }
};
struct Outcome{
  bool ok=false;size_t total=0;unsigned cycles=0,positive=0,negative=0;
  W bad_pc=0,bad_k=0,finish_sign=0;std::string reason;
};
Outcome journey(Journal& log){
  Kyiv_t cpu;init(cpu);
  Outcome result;
  Cycle current;
  unsigned epoch=1;
  bool active=false,started_second_epoch=false,documented_entry_seen=false;
  auto failure=[&](W pc,const std::string& msg){
    result.bad_pc=pc;result.bad_k=cpu.K_reg;result.reason=msg;
  };
  auto close_cycle=[&](W pc,const std::string& by)->bool{
    current.next_pattern=cpu.kmem.read_memory(0017);
    if(!active||current.writes!=CELLS||current.reads!=CELLS||
       !current.handoff||current.negative_reads!=current.negative_writes){
      failure(pc,"incomplete RAM cycle or mismatched signed-zero tally");return false;
    }
    for(size_t i=0;i<CELLS;++i){
      if(cpu.kmem.read_memory(FIRST+i)!=current.snapshot[i]){
        failure(pc,"RAM snapshot changed outside write sweep");return false;
      }
    }
    ++result.cycles;
    if(epoch==1)++result.positive;else ++result.negative;
    log.cycle(current,by);
    active=false;
    return true;
  };
  {
    // Suppress the emulator's verbose per-instruction stdout without buffering it.
    Silence silence;
    for(size_t step=0;step<MAX_STEPS;++step){
      W pc=cpu.C_reg;
      if(pc==0164){
        if(!documented_entry_seen || result.cycles!=78 ||
           result.positive!=39 || result.negative!=39 ||
           !started_second_epoch || epoch!=2 || active ||
           cpu.kmem.read_memory(0014)!=SIGN ||
           cpu.kmem.read_memory(0017)!=TOP_MAG ||
           result.positive==0 ||result.negative==0){
          failure(pc,"0164 reached with incomplete or incorrect epoch state");break;
        }
        result.finish_sign=cpu.kmem.read_memory(0014);
        result.ok=true; break; // CRITICAL: 0164 IS NOT EXECUTED
      }
      if(pc==0121){
        if(!documented_entry_seen){failure(pc,"missing documented 0117 entry");break;}
        if(active){failure(pc,"duplicate cycle entry");break;}
        active=true;current=Cycle{};
        current.n=result.cycles+1;current.epoch=epoch;
        current.sign=cpu.kmem.read_memory(0014);
        current.pattern=cpu.kmem.read_memory(0017);
        if(current.sign!=(epoch==1?W{0}:SIGN)){
          failure(pc,"unexpected RAM[0014] sign at pattern entry");break;
        }
      }
      W expected=0;
      try{expected=original(pc);}catch(const std::exception& e){failure(pc,e.what());break;}
      W before_a=cpu.A_reg;
      W before20=cpu.kmem.read_memory(0020);
      if(pc==0126){
        if(!active||current.writes>=CELLS||before_a!=FIRST+current.writes){
          failure(pc,"nonsequential RAM write address");break;
        }
      }
      if(pc==0144){
        if(!active||current.reads>=CELLS||before_a!=FIRST+current.reads){
          failure(pc,"nonsequential RAM read address");break;
        }
        if(cpu.kmem.read_memory(before_a)!=current.snapshot[current.reads] ||
           before20!=current.snapshot[current.reads]){
          failure(pc,"41-bit RAM read differs from written snapshot");break;
        }
      }
      bool running=false;
      try{running=cpu.execute_opcode();}
      catch(const std::exception& e){failure(pc,std::string("execute exception: ")+e.what());break;}
      ++result.total;
      if(active)++current.steps;
      if(!running||cpu.T_reg||cpu.K_reg!=expected){
        failure(pc,"unexpected STOP or fetched K differs from source");break;
      }
      if(pc==0117){
        if(documented_entry_seen || cpu.C_reg!=0120 ||
           cpu.kmem.read_memory(0014)!=0){
          failure(pc,"0117 failed to clear injected -0 to +0");break;
        }
        documented_entry_seen=true;
      }
      if(pc==0126){
        W code=cpu.kmem.read_memory(before_a);
        if(code!=before20){failure(pc,"write changed source 41-bit code");break;}
        current.snapshot[current.writes++]=code;
        if(code==SIGN)++current.negative_writes;
      }
      if(pc==0144){
        if(cpu.C_reg!=0146){failure(pc,"historical exact compare did not match");break;}
        if(cpu.kmem.read_memory(before_a)==SIGN)++current.negative_reads;
        ++current.reads;
      }
      if(pc==0137){
        current.handoff=true;
        if(cpu.C_reg!=0140||current.writes!=CELLS){
          failure(pc,"write-read handoff incorrect");break;
        }
      }
      if(pc==0156&&current.reads!=CELLS){
        failure(pc,"read sweep incomplete before shift");break;
      }
      if(pc==0157){
        if(cpu.C_reg!=0160&&cpu.C_reg!=0161){
          failure(pc,"terminal pattern comparison targeted unknown PC");break;
        }
      }
      if(pc==0160){
        if(cpu.C_reg!=0121){failure(pc,"non-terminal reentry failed");break;}
        if(!close_cycle(pc,"0160_REENTER"))break;
      }
      if(pc==0161){
        W next=epoch==1?0162:0164;
        if(cpu.C_reg!=next){failure(pc,"RAM[0014] sign-dispatch mismatch");break;}
        if(!close_cycle(pc,epoch==1?"0161_RESTART":"0161_BOUNDARY"))break;
        if(epoch==2){
          // The main loop will stop BEFORE fetching 0164.
          continue;
        }
      }
      if(pc==0162){
        if(cpu.kmem.read_memory(0014)!=SIGN){
          failure(pc,"equal subtraction did not yield negative zero");break;
        }
      }
      if(pc==0163){
        if(cpu.C_reg!=0120){failure(pc,"restart to 0120 failed");break;}
        epoch=2;started_second_epoch=true;
      }
    }
  }
  if(!result.ok && result.reason.empty()){
    result.bad_pc=cpu.C_reg;result.bad_k=cpu.K_reg;
    result.reason="step budget exceeded before natural 0164";
  }
  return result;
}
} // namespace
int main(int argc,char** argv){
  std::string trace;
  if(argc==3&&std::string(argv[1])=="--trace")trace=argv[2];
  else if(argc!=1){std::cerr<<"usage: probe [--trace path.tsv]\n";return 2;}
  try{
    Journal journal(trace);
    Outcome r=journey(journal);
    std::cout<<(r.ok?"POLICY-PASS ":"POLICY-FAIL ")
             <<"full_0117_entry_2epoch_0164_boundary"
             <<" total_steps="<<r.total<<" total_cycles="<<r.cycles
             <<" positive_cycles="<<r.positive<<" negative_cycles="<<r.negative
             <<" C="<<(r.ok?"0164":oct(r.bad_pc))
             <<" sign0014="<<oct(r.finish_sign)
             <<" first_bad_pc="<<oct(r.bad_pc)
             <<" fetched_K="<<oct(r.bad_k)
             <<" reason="<<r.reason
             <<" entry0117=EXECUTED initial0014=NEGZERO_POISON"
             <<" 0164_UNEXECUTED=1 ROM3000_NOT_INJECTED=1\n";
    std::cout<<"ISA-06 D8-P8 STRICT=0/0 DOC-MISMATCH=0 POLICY="
             <<(r.ok?1:0)<<"/1 POLICY-FAIL="<<(r.ok?0:1)<<" OBS=0\n";
    if(!trace.empty())std::cout<<"TRACE="<<trace<<'\n';
    return r.ok?0:1;
  }catch(const std::exception& e){
    std::cerr<<"POLICY-FAIL unhandled: "<<e.what()<<'\n';return 1;
  }
}
