// ISA-07 D14-B3: standalone real C++17 persistence probe, no Kyiv_t linkage.
// Python independently specifies binary bytes and injects corrupted images.
#include "kyiv_drum_persistence.h"
#include <cstdint>
#include <iostream>
#include <iomanip>
#include <string>
#include <vector>

namespace m=kyiv_drum_media;
namespace p=kyiv_drum_persistence;

static void dump(const m::logical_media& disk) {
    const auto& g=disk.profile();
    std::cout << "D14B3-READ OK " << g.profile_id << ' '
              << g.drums << ' ' << g.tracks_per_drum << ' '
              << g.slots_per_track << ' ' << disk.written_count() << '\n';
    for (std::size_t i=0; i<disk.capacity(); ++i) {
        const auto c=disk.inspect(p::from_linear(g,i));
        if(c.written) std::cout << "CELL " << i << ' ' << c.word << '\n';
    }
}
static bool match(const m::logical_media& a,const m::logical_media& b) {
    if(!p::same_geometry(a.profile(),b.profile()) ||
       a.written_count()!=b.written_count()) return false;
    for(std::size_t i=0;i<a.capacity();++i) {
        const auto ca=a.inspect(p::from_linear(a.profile(),i));
        const auto cb=b.inspect(p::from_linear(b.profile(),i));
        if(ca.written!=cb.written || (ca.written && ca.word!=cb.word)) return false;
    }
    return true;
}
static m::logical_media make_media(char** argv) {
    return m::logical_media({argv[3], static_cast<std::size_t>(std::stoull(argv[4])),
        static_cast<std::size_t>(std::stoull(argv[5])),
        static_cast<std::size_t>(std::stoull(argv[6]))});
}
int main(int argc,char** argv) {
    if(argc==2 && std::string(argv[1])=="crc") {
        constexpr char check[]="123456789";
        const auto value=p::crc64(reinterpret_cast<const std::uint8_t*>(check),9);
        std::cout << "D14B3-CRC " << std::hex << std::setw(16)
                  << std::setfill('0') << value << '\n';
        return 0;
    }
    if(argc<3) return 2;
    const std::string op=argv[1];
    if((op=="save" || op=="loadinto") ? argc!=7 : argc!=3) return 2;
    try {
        if(op=="read") {
            dump(p::load(argv[2]));
        } else if(op=="loadinto") {
            auto dest=make_media(argv);
            dest.store({0,0,0},m::sign_bit);
            const auto baseline=dest;
            try {
                p::load_into(dest,argv[2]);
                dump(dest);
            } catch(const m::media_error& e) {
                std::cout << "D14B3-LOADINTO ERROR " << e.what()
                          << " UNCHANGED=" << (match(dest,baseline)?1:0) << '\n';
            }
        } else if(op=="save") {
            auto disk=make_media(argv);
            std::string kind;
            std::size_t d=0,t=0,s=0;
            std::uint64_t raw=0;
            while(std::cin>>kind) {
                if(kind=="PUT") {
                    if(!(std::cin>>d>>t>>s>>raw)) return 3;
                    disk.store({d,t,s},raw);
                } else if(kind=="ERASE") {
                    if(!(std::cin>>d>>t>>s)) return 3;
                    disk.erase({d,t,s});
                } else return 3;
            }
            p::save_atomic(disk,argv[2]);
            std::cout << "D14B3-SAVE OK " << disk.written_count() << '\n';
        } else return 2;
        return 0;
    } catch(const m::media_error& e) {
        std::cout << "D14B3-ERROR " << e.what() << '\n';
        return 0;
    } catch(const std::exception& e) {
        std::cerr << "D14B3-UNEXPECTED " << e.what() << '\n';
        return 3;
    }
}
