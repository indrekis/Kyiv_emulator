# H113 — release-review notes (candidate)

## What is accepted

- H103: dynamic reconstructed machine output with group operations `26/27` for n=1..8; authentic printer not established.
- H108: original RK code consumes two synthetic machine RHS results.
- H109: n=2, two constant independent derivatives, 7 native cases / 1116 trajectory points.
- H110-H2: n=2, coupled oscillator, 11 native cases / 1146 trajectory points.
- H111: n=2, coupled hyperbolic system, 11 native cases / 1146 trajectory points.
- H112-H1: evidence offline re-audit: 29 cases / 3408 points and a deterministically regenerated HTML report; accepted on Windows/MSYS2.
- H113: source-controlled offline CI gate and delivery wrapper; its CI success does **not** itself rerun the emulator CPU.

## Explicitly unresolved

Historical ROM word 3200, missing word 3677, historical printer interface and byte layout, operator initialization / panel settings, unqualified n>2 RK integration, hardware cycle accuracy, historical/source licensing. Scratch initialization remains RECONSTRUCTED_ASSUMPTION. Synthetic RHS and substituted ROM are not authentic historical software.

## Publication decision

Ready for **maintainer review** as a bounded educational reconstruction. No version tag, main-branch commit, broad emulator release, or claim of original printer restoration is made by this package. Confirm licensing and source provenance before public redistribution of the nested evidence archive; the archive contains no original scans, but archival sources and generated tools still require a separate release review.

## H113 tracked files

- `examples/rk4_reconstructed/` : source documentation, tests, pinned H112-H1 evidence and audit runner.
- `.github/workflows/kyiv-rk4-evidence.yml` : dedicated offline GitHub Actions job for Ubuntu and Windows.

`ROADMAP.md`, `mem/ROM.txt`, main CPU code and `src/` are unchanged. Keep any preexisting uncommitted edits untouched.
