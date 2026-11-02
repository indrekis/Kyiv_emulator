# H114 — fast path to numerical FP simulation

**Basis:** `main` at `86759e9c5c8743d1cf5896c978d8845255e9db2c`, H62 and H71 source-qualified results. **Status:** SOURCE-LAYOUT PREFLIGHT ONLY; not a numerical FP pass.

## Scope

The ROM-set registry is intentionally small. `tools/historical/run.py` supports `list`, `validate`, and `prepare` for existing module 1 and the alternative historical FP simulation module set. Source text is never modified; output may be created only in a new directory. Inputs are UTF-8 `KYIV41-OCT1` records, 41-bit 14-octal-digit words. Overlaps and invalid addresses are rejected.

- Mathematical module 1: canonical 64 source words at 3300–3377, SHA-256 `9c659521d263fe78c2d6356cb28bfeaac374c1e71d723e35cc60be19ad3e1e84`.
- FP simulation (GY1962 printed pp.112–117): 251 printed words in five slots, 69 non-printed positions. The H66 source transcription **is not tracked on main**, and must be brought explicitly as `--image`; a supplied SHA-256 may pin its exact bytes. The runner refuses missing records, invented words at unknown addresses, implicit fill, and overlap with module 1.
- This preparer never updates `mem/ROM.txt`, `src`, `inc`, existing `.k41`, `docs/historical/ROADMAP.md`, or previously accepted evidence.
- Floating-point simulator is a **software simulation by machine code** (МП), not a new floating-point execution mode added to the CPU.

## Commands

```bash
python tools/historical/run.py list
python -m unittest discover -s tests/historical -p 'test_romsets.py' -v
python tools/historical/run.py validate module1
python tools/historical/run.py prepare module1 --out tempkyiv/h114_module1_preview
# Once the original H66 transcription has been located and verified:
python tools/historical/run.py prepare fp_simulation \
  --image tempkyiv/<exact_H66_transcription>.k41 \
  --sha256 <sha256_of_exact_H66_file> \
  --out tempkyiv/h114_fp_prepared
```

For FP, a `PASS_H114_SOURCE_LAYOUT_NOT_NATIVE` means only that the sparse source layout is consistent; it is **not** an execution success. If H66 image is absent, the expected status is `HOLD_H114_ROMSET`.

## Next: H115 — run genuine machine instructions and measure FP results

1. Recover precisely the H66 251-record source, bind its source hash and word-level provenance. Do not repeat transcription unless necessary.
2. Model and document the historical FP word-pair representation and dispatch ABI (NK 3000, entry 3300), using printed pp.110–118 and the H68–H70 traces. Produce independent numeric vectors for addition/subtraction/multiplication, then division/normalization.
3. Attempt bounded native run of unchanged production CPU with the alternative ROM-set. Interrupt at first unknown read; separately label any **reconstructed** word (not SOURCE_PRINTED) and run a negative/regression comparison.
4. Report numeric result words and error tolerance; keep `3574` OPEN_SOURCE unless a uniquely justified derivation exists. Native PASS must be conditioned on actual execution, not a Python arithmetic substitute.

## Relationship to broader ROADMAP

This is a deliberately minimal portion of C/E to unblock FP. Historical AU/UI, module1 and the RK4 H109–H113 demos are not being reopened. Integrate these through the common scenario mechanism later, after the first FP numerical demonstration. Local `ROADMAP.md` has uncommitted changes and is intentionally untouched; reconcile it after the FP preflight is merged.

## Provenance and rights

The user confirms that Yuriy Yushchenko granted permission for materials of Kateryna Yushchenko during development of the first emulator. The exact written scope/terms of this permission are not reconstructed here. Do not assume repository MIT license applies to every scanned third-party source.
