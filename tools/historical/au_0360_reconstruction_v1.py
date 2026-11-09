#!/usr/bin/env python3
"""H117: bounded, non-historical AU 0360 functional loop experiment.

Reuses the actual Kyiv_t backend. Canonical source words are NEVER modified;
private composite images are emitted beneath the specified new output directory.
No CPU arithmetic is implemented in Python. No hardware claims.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import queue
import re
import subprocess
import sys
import threading
import time
import unittest

REPO_HEAD = "f7e2b69c497b983c9163d04acf28a44bb5e783b1"
SOURCE_0042 = "01306600000353"  # printed GY62 p.173, H37 source manifest
SOURCE_0334 = "05000000000360"  # printed GY62 p.174, tracked AU image
RECON_0360 = "05000000000042"  # HOST FUNCTIONAL candidate, *not* GY62 printed
ROM_SHA = "a1d9c28e969fa1d74966a78fdbb1bf85b4c45354a764cb8665a73b0a62bdab38"
IMAGE_IDS = (
    "au1_absolute_predivision_0234_0240", "au1_addcmd_0163_0165",
    "au1_addcyc_0151_0154", "au1_addition_0110_0115",
    "au1_addition_0116_0126", "au1_addition_0127_0134",
    "au1_addition_0135_0142", "au1_addition_0143_0150",
    "au1_batch31_0241_0277", "au1_batch38_0300_0345",
    "au1_control_transfer_0213", "au1_division_negative_0210_0212",
    "au1_division_one_third_0205_0207", "au1_logic",
    "au1_pseudorandom_0214_0226", "au1_rounded_multiplication_0171_0201",
    "au1_rounded_multiply_negative_0202_0204",
    "au1_rounded_products_swap_0227_0233", "au1_shift_zero_0166_0170",
    "au1_subtraction_0155_0162",
)
START_NK_WORD = "20000000000000"  # panel negative zero, documented H37 HOST protocol
STOP_BEFORE = {0o232, 0o252}  # guarded native I/O boundaries
MAX_PER_EPOCH = 400


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_image(path: pathlib.Path) -> dict[int, str]:
    try:
        s = path.read_bytes().decode("utf-8-sig")
    except UnicodeError as exc:
        raise ValueError(f"INVALID_UTF8:{path}") from exc
    head = False
    entries = {}
    for raw in s.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if not head:
            if line != "KYIV41-OCT1":
                raise ValueError(f"INVALID_HEADER:{path}")
            head = True
            continue
        fields = line.split()
        if len(fields) != 2 or not re.fullmatch(r"[0-7]{4}", fields[0]) or not re.fullmatch(r"[0-7]{14}", fields[1]):
            raise ValueError(f"INVALID_RECORD:{path}:{line}")
        addr = int(fields[0], 8)
        if addr == 0 or addr >= 0o2000 or int(fields[1],8) >= (1<<41):
            raise ValueError(f"INVALID_RAM_WORD:{path}:{line}")
        if addr in entries:
            raise ValueError(f"DUPLICATE_LOCAL_ADDRESS:{path}:{fields[0]}")
        entries[addr] = fields[1]
    if not head or not entries:
        raise ValueError(f"EMPTY_IMAGE:{path}")
    return entries


def source_images(repo: pathlib.Path) -> tuple[dict[int, str], dict]:
    root = repo / "examples/historical/gy1962"
    actual = {p.stem for p in root.glob("au1_*.k41")}
    if actual != set(IMAGE_IDS):
        raise ValueError(f"CANONICAL_IMAGE_SET_DRIFT expected=20 actual={len(actual)} missing={sorted(set(IMAGE_IDS)-actual)} extra={sorted(actual-set(IMAGE_IDS))}")
    combined, source = {}, {}
    for name in IMAGE_IDS:
        path = root / (name + ".k41")
        raw = path.read_bytes()
        source[name] = {"sha256": sha256(raw), "records": len(parse_image(path))}
        for address, word in parse_image(path).items():
            old = combined.get(address)
            if old is not None and old != word:
                raise ValueError(f"SOURCE_COLLISION:{address:04o}")
            combined[address] = word
    if combined.get(0o334) != SOURCE_0334:
        raise ValueError("SOURCE_0334_DRIFT")
    if 0o42 in combined or 0o360 in combined:
        raise ValueError("SOURCE_0042_OR_0360_COLLISION")
    if len(combined) != 220:
        raise ValueError(f"SOURCE_ADDRESS_COUNT_DRIFT:{len(combined)}")
    manifest = json.loads((root / "scenarios/au1_h37_entry_qualification.json").read_text(encoding="utf-8"))
    if manifest["source_only_word"]["word"] != SOURCE_0042 or manifest["source_only_word"]["address"] != "0042":
        raise ValueError("H37_0042_SOURCE_DRIFT")
    return combined, {"canonical_images": source, "source_only_0042":SOURCE_0042,
                       "source_0334":SOURCE_0334,"source_word_count":len(combined),
                       "canonical_image_count":len(IMAGE_IDS)}


def compose(repo: pathlib.Path, dest: pathlib.Path, patch: bool) -> tuple[dict[int,str],dict]:
    words, manifest = source_images(repo)
    words[0o42] = SOURCE_0042
    if patch:
        # Only explicitly marked functional candidate; never source printed.
        words[0o360] = RECON_0360
    text = "KYIV41-OCT1\n" + "".join(f"{addr:04o} {val}\n" for addr,val in sorted(words.items()))
    dest.write_text(text, encoding="ascii", newline="\n")
    manifest.update({"private_composite":dest.name,"composite_sha256":sha256(dest.read_bytes()),
                     "reconstructed_0360":RECON_0360 if patch else None,
                     "reconstructed_status":"HOST_FUNCTIONAL_CANDIDATE" if patch else "ABSENT",
                     "historical_0360_source":"BLOCKED"})
    return words,manifest


def check_patch_file(repo: pathlib.Path, patch_image: pathlib.Path | None = None) -> None:
    path=patch_image if patch_image is not None else repo/"examples/historical/gy1962/reconstructions/au1_0360_functional_v1.k41"
    d=parse_image(path)
    if d!={0o360:RECON_0360}:
        raise ValueError("H117_PATCH_WORD_INVALID")
    if sha256((repo/"mem/ROM.txt").read_bytes())!=ROM_SHA:
        raise ValueError("FIXED_ROM_SHA_DRIFT")


def native_path(p:pathlib.Path)->str:
    """Windows native executable receives a native, not MSYS path, over stdin."""
    try:
        r=subprocess.run(["cygpath","-m",str(p.resolve())],check=True,capture_output=True,text=True,timeout=5)
        return r.stdout.strip()
    except FileNotFoundError:
        return str(p.resolve())


class Backend:
    def __init__(self, exe:pathlib.Path, rom:pathlib.Path, stderr:pathlib.Path):
        self.error=stderr.open("w",encoding="utf-8")
        self.proc=subprocess.Popen([native_path(exe),native_path(rom)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                          stderr=self.error, text=True,encoding="utf-8",bufsize=1)
        self.response_queue=queue.Queue()
        def collect():
            for line in self.proc.stdout:
                self.response_queue.put(line.rstrip("\r\n"))
            self.response_queue.put(None)
        self.reader=threading.Thread(target=collect,daemon=True);self.reader.start()
    def call(self,*fields, timeout=12):
        if self.proc.poll() is not None:
            raise RuntimeError("BACKEND_EXITED_EARLY")
        line="\t".join(fields)
        self.proc.stdin.write(line+"\n");self.proc.stdin.flush()
        try:
            result=self.response_queue.get(timeout=timeout)
        except queue.Empty as exc:
            self.proc.kill();raise RuntimeError("BACKEND_PROTOCOL_TIMEOUT") from exc
        if result is None or not result.startswith("OK\t"):
            raise RuntimeError("BACKEND_PROTOCOL_ERROR:"+str(result))
        chunks=result.split("\t")
        obj={}
        for c in chunks[2:]:
            if "=" in c:
                k,v=c.split("=",1);obj[k]=v
        return result,obj
    def close(self):
        try:
            if self.proc.poll() is None:
                self.call("QUIT",timeout=3)
        except Exception:
            pass
        if self.proc.poll() is None:self.proc.kill()
        try:self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:self.proc.kill()
        self.error.close()
    def __enter__(self):return self
    def __exit__(self,*a):self.close()


def run_epoch(backend: Backend, known:set[int], ident:str, limit:int=MAX_PER_EPOCH):
    events=[]
    for i in range(limit):
        _,state=backend.call("STATE")
        current=int(state["C"],8)
        if state["T"]!="0":
            return {"result":"CPU_STOP","steps":i,"events":events,"state":state}
        if current==0o360:
            return {"result":"BOUNDARY_0360","steps":i,"events":events,"state":state}
        if current in STOP_BEFORE:
            return {"result":"IO_BOUNDARY","steps":i,"events":events,"state":state}
        if current<0o3000 and current not in known:
            return {"result":"UNKNOWN_RAM_INSTRUCTION","steps":i,"events":events,"state":state}
        _,step=backend.call("STEP","1")
        if step.get("EXECUTED")!="1" or step.get("PATH")!=f"{current:04o}":
            raise RuntimeError(f"UNEXPECTED_STEP:{ident}:{i}:{step}")
        events.append({"epoch":ident,"index":i+1,"before":f"{current:04o}",
                       "after":step["C"],"T":step["T"],"A":step["A"],"P":step["P"]})
    _,state=backend.call("STATE")
    return {"result":"STEP_LIMIT","steps":limit,"events":events,"state":state}


def run_native(repo:pathlib.Path, backend_path:pathlib.Path, out:pathlib.Path, patch_image:pathlib.Path | None = None) -> dict:
    if out.exists():raise ValueError("OUTPUT_EXISTS")
    out.mkdir(parents=True)
    result={"schema":"KYIV_H117_AU0360_NATIVE_V1", "source_status":"0360_UNKNOWN",
            "reconstruction":"HOST_FUNCTIONAL_PROPOSED", "classification":"NOT_HARDWARE_ORACLE",
            "baseline_head":REPO_HEAD, "decision":"HOLD_NOT_YET_QUALIFIED"}
    try:
        check_patch_file(repo, patch_image)
        base, base_manifest=compose(repo,out/"au_canonical_private.k41",False)
        patched,patch_manifest=compose(repo,out/"au_functional_private.k41",True)
        (out/"INPUT_MANIFEST.json").write_text(json.dumps({"baseline":base_manifest,"patched":patch_manifest},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        sessions=[];rows=[]
        for which,filename,words in [("CONTROL",out/"au_canonical_private.k41",base),
                                     ("RECONSTRUCTED",out/"au_functional_private.k41",patched)]:
            with Backend(backend_path,repo/"mem/ROM.txt",out/(which.lower()+"_backend_stderr.txt")) as be:
                be.call("PING")
                _,loaded=be.call("LOAD",native_path(filename),"0042")
                if loaded.get("C")!="0042": raise RuntimeError("START_PC_INVALID")
                be.call("SETNK","3000",START_NK_WORD)
                first=run_epoch(be,set(words),which+"_FIRST")
                rows.extend(first.pop("events"))
                s={"session":which,"first":first}
                if first["result"]=="BOUNDARY_0360":
                    for addr in ("0347","0353","0357"):
                        _,dump=be.call("DUMP",addr,"1")
                        s["before_0360_ram_"+addr]=dump["DATA"]
                if which=="RECONSTRUCTED" and first["result"]=="BOUNDARY_0360":
                    _,jump=be.call("STEP","1")
                    s["jump"]={"path":jump.get("PATH"),"pc":jump.get("C"),"T":jump.get("T")}
                    rows.append({"epoch":"RECONSTRUCTED_JUMP","index":1,"before":"0360","after":jump.get("C"),"T":jump.get("T"),"A":jump.get("A"),"P":jump.get("P")})
                    if jump.get("PATH")=="0360" and jump.get("C")=="0042" and jump.get("T")=="0":
                        second=run_epoch(be,set(words),"RECONSTRUCTED_SECOND")
                        rows.extend(second.pop("events"))
                        s["second"]=second
                sessions.append(s)
        result["sessions"]=sessions
        ctrl,fnc=sessions
        result["first_epoch_source_boundary"] = ctrl["first"]["result"]=="BOUNDARY_0360" and ctrl["first"]["steps"]==97
        result["first_epoch_invariant"] = fnc["first"]["result"]=="BOUNDARY_0360" and fnc["first"]["steps"]==ctrl["first"]["steps"] and all(fnc.get("before_0360_ram_"+a)==ctrl.get("before_0360_ram_"+a) for a in ("0347","0353","0357"))
        result["reconstructed_jump"] = fnc.get("jump",{}).get("pc")=="0042" and fnc.get("jump",{}).get("path")=="0360" and fnc.get("jump",{}).get("T")=="0"
        result["second_epoch_reaches_boundary"] = fnc.get("second",{}).get("result")=="BOUNDARY_0360"
        result["second_epoch_steps"]=fnc.get("second",{}).get("steps")
        result["decision"]="PASS_FUNCTIONAL_LOOP_TWO_EPOCHS_NOT_HISTORICAL" if all(result[k] for k in ("first_epoch_source_boundary","first_epoch_invariant","reconstructed_jump","second_epoch_reaches_boundary")) else "HOLD_OBSERVED_RECONSTRUCTION_LIMITATION"
        with (out/"TRACE.tsv").open("w",encoding="utf-8",newline="\n") as f:
            f.write("epoch\tindex\tbefore\tafter\tT\tA\tP\n")
            for row in rows:f.write("\t".join(str(row.get(k,"")) for k in ("epoch","index","before","after","T","A","P"))+"\n")
    except Exception as exc:
        result["error"] = type(exc).__name__+":"+str(exc)
        result["decision"]="HOLD_EXCEPTION"
    (out/"RESULT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    files=sorted(p for p in out.iterdir() if p.is_file())
    (out/"SHA256SUMS.txt").write_text("".join(f"{sha256(p.read_bytes())}  {p.name}\n" for p in files),encoding="ascii")
    return result


class StaticTests(unittest.TestCase):
    def test_word_properties(self):
        self.assertEqual(int(RECON_0360,8),(5<<36)|0o42)
        self.assertEqual(len(RECON_0360),14)
        self.assertNotEqual(SOURCE_0334,RECON_0360)
    def test_witness(self):
        self.assertEqual(int(SOURCE_0334[-4:],8),0o360)
        self.assertEqual(int(SOURCE_0042[-4:],8),0o353)
        self.assertEqual(len(IMAGE_IDS),20)
    def test_parser_rejects_bad(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/"bad.k41"
            for data in ("KYIV41-OCT1\n0360 05000000000042\n0360 05000000000042\n",
                         "KYIV41-OCT1\n0360 77777777777777\n",
                         "KYIV41-OCT1\n0360 05000000000048\n"):
                p.write_text(data)
                with self.assertRaises(ValueError):parse_image(p)
    def test_preflight_independent_of_cpu(self):
        self.assertEqual(STOP_BEFORE,{0o232,0o252})
        self.assertTrue(0o360<0o2000)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo",type=pathlib.Path,default=pathlib.Path("."))
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--selftest",action="store_true")
    group.add_argument("--validate",action="store_true")
    group.add_argument("--run",action="store_true")
    ap.add_argument("--backend",type=pathlib.Path)
    ap.add_argument("--out",type=pathlib.Path)
    ap.add_argument("--patch-image",type=pathlib.Path)
    args=ap.parse_args()
    if args.selftest:
        result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(StaticTests))
        print("H117_AU_SELFTEST_PASS" if result.wasSuccessful() else "H117_AU_SELFTEST_HOLD")
        return 0 if result.wasSuccessful() else 2
    root=args.repo.resolve()
    try:
        check_patch_file(root,args.patch_image.resolve() if args.patch_image else None)
        words,manifest=source_images(root)
        if args.validate:
            print(f"H117_AU_VALIDATE_PASS|CANONICAL_IMAGES={len(IMAGE_IDS)}|UNIQUE_SOURCE_WORDS={len(words)}|MISSING_0360=1|SOURCE_0042=1")
            return 0
        if not args.backend or not args.out or not args.backend.is_file():
            raise ValueError("BACKEND_OR_OUTPUT_MISSING")
        result=run_native(root,args.backend.resolve(),args.out.resolve(),args.patch_image.resolve() if args.patch_image else None)
        print("H117_AU_NATIVE="+result["decision"])
        return 0 if result["decision"].startswith("PASS_") else 2
    except Exception as exc:
        print(f"H117_AU_HOLD|{type(exc).__name__}:{exc}")
        return 2
if __name__=="__main__": sys.exit(main())
