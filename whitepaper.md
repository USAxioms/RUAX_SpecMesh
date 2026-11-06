# WAD18 Spectrum and Beamforming Reference Model (RUAX-TELE-007)
**Capsule v2.0.0.** Integer-only, bit-reproducible reference model and test oracle for channel-plan validation, UPA steering-phase generation, and recompute-and-compare state auditing.

> **Scope statement.** This is a *reference model and test oracle*, not a controller. It does not drive RF or photonic hardware, does not run in an air-gapped enclave, and is not certified. Every physical parameter is a **PLACEHOLDER** (8×8 UPA, d = λ/2, f_c = 140 GHz, 2.16 GHz channels, 216 MHz guard, 16-bit phase words, 60° scan limit, EIRP check inputs). The spectral mask is a **stepped placeholder** (−25/−35/−45 dBc at 0.1·BW and 0.5·BW offsets); it is *not* the verbatim ITU-R SM.1541 or FCC Part 30 mask. Real mask tables must be loaded from the governing standard before any compliance claim.

## 1. Requested invariants and what is actually provable
| Requested | Delivered, reformulated | Why |
|---|---|---|
| Phase error Δθ ≤ 10⁻¹⁸ rad "bit-exact" | Each phase word is the correctly rounded (to 10⁻¹⁸) value of the exact real phase: error ≤ 0.5 ulp = 5·10⁻¹⁹ rad, plus < 10⁻⁵⁰ ulp from kernel truncation | sin/cos/π are irrational; exactness is impossible, bounded error + bit parity is possible |
| I_bleed = 0 | `I_bleed(plan) = Σ_{pairs} max(0, hi_i + guard − lo_j)` is computed exactly in integers; the plan is accepted iff it is 0, plus a discrete mask inequality on declared emission samples | Physical filters never have zero leakage; a *declared allocation* can be proven overlap-free |
| ΔS/Δt ≠ 0 ⇒ isolate | Integer math cannot drift. `audit` recomputes the table (bit-parity), checks range, and checks array linearity; any failure ⇒ `ISOLATE_CHANNEL` | Detects memory faults, corruption, tampering, or logic regressions |
| Safety radiation boundary | Scan-cone check and a coherent-array EIRP computation in dB | Limits are inputs, not built in |

## 2. Axioms
A1 all quantities are integers at 10¹⁸ scale (no float literal, `/` operator or `float()` call; enforced by an AST test). A2 all functions are total: overflow saturates to ±(2¹²⁷−1), invalid decimal strings return `(0, False)`, `log` of a non-positive value returns the saturated minimum, no exception on any integer input. A3 conservative direction: hazard-enlarging quantities round up (leakage ratio), capability-granting round down. A4 bit parity: only Python integer arithmetic with defined floor semantics; `demo_expected.txt` pins the output.

## 3. Arithmetic kernel (deviation from the requested CORDIC)
CORDIC accumulates rounding error across iterations, so a 1-ulp guarantee needs guard bits plus an error analysis anyway. This capsule instead computes at scale P = 10⁹⁰ (72 guard digits) and rounds once:
- π, ln 2, ln 10 are *derived* (Machin: π = 16·atan(1/5) − 4·atan(1/239); ln 2 = 2·atanh(1/3); ln 10 = 3 ln 2 + 2·atanh(1/9)) with integer series at 10¹⁰⁰.
- `sincos`: reduce modulo π/2 to |r| ≤ π/4 (nearest quadrant), Taylor series with integer floor division, quadrant rotation.
- `ln`: normalise to m ∈ [P, 2P) (the bit length of P is 299, so m ∈ [0.509P, 1.0185P) and one conditional shift suffices; tested), then ln m = 2·atanh((m−P)/(m+P)).
- log10 = ln/ln 10; dB = 10·log10 (power) or 20·log10 (amplitude), scaled *before* the single rounding.

**Theorem 1 (correct rounding up to a negligible term).** For any WAD18 input, `sin_wad`, `cos_wad`, `ln_wad`, `log10_wad`, `db_*` return round-to-nearest of the exact value, up to an absolute internal error ε < 10⁻⁶⁸ (that is < 10⁻⁵⁰ ulp). *Sketch:* each series term loses < 1 unit of 10⁻⁹⁰ per floor division, ≤ 100 terms ⇒ < 10⁻⁸⁷; π/2 has error < 10⁻⁹⁰ and the quadrant index is at most 1.1·10²⁰ for any saturated input ⇒ reduced-argument error < 10⁻⁷⁰; the ln(m) series is bounded the same way and k·ln 2 adds k·10⁻⁹⁰. The final `round_div` adds ≤ 0.5 ulp. ∎ (A pen-and-paper bound, not machine-checked.) It is *tested* against independent exact-rational Taylor/atanh oracles built from `fractions.Fraction`: 13 angles for sin and cos, 6 arguments plus 5 powers of two for ln, π to 18 digits, and 24 full 8×8 phase tables, all equal word-for-word.

## 4. Channel plan and mask
Channel i occupies [lo_i, hi_i] with lo = c − ⌊bw/2⌋, hi = c + ⌈bw/2⌉ (odd bandwidths widen by 1 ulp, the safe direction). `plan_uniform` places n channels symmetrically at pitch bw + guard.
**Theorem 2.** Sort channels by center. `validate_plan` accepts iff (a) every channel lies in the band, (b) bw > 0, guard ≥ 0, and (c) for every pair a < b in sorted order, hi_a + guard ≤ lo_b. Equivalently I_bleed = 0. For the placeholder plan, hi_i + guard = lo_{i+1} *exactly* (zero slack), and a 1-ulp shift is rejected with I_bleed = 1 (both tested). The all-pairs form also catches nested or very wide channels that an adjacent-only check would miss.
Mask check: `check_mask` takes (offset from occupied edge, level in dBc) samples; negative offsets are in-band and not governed. Level > limit(offset) is a violation. `leakage_dbc` turns two linear powers into dBc with the ratio rounded *up*.
**Limit.** These checks prove a declared allocation and declared emission samples satisfy the mask. They do not prove anything about physical RF leakage.

## 5. Steering phases
For element (m, n) of a d = λ/2 array, 2π·d/λ = π, so
φ_mn = −π · (f/f_c) · (m·sinθ·cosφ + n·sinθ·sinφ) mod 2π,
where f/f_c models beam squint across a channel (the element spacing is fixed at the f_c half-wavelength). All sin/cos and products are evaluated at 10⁻⁹⁰; one rounding yields the word in [0, 2π_WAD). **Theorem 3:** each word is within 0.5 ulp (circular) of the exact phase plus < 10⁻⁵⁰ ulp for |f/f_c| ≤ 10³ and array sizes ≤ 10³ (error budget from Theorem 1 times ≤ 10⁶). The word domain is [0, 2π_WAD) with 2π_WAD = 6283185307179586477 (0.075 ulp above 2π); a word that rounds to 2π_WAD wraps to 0.
`quantize` maps words to B-bit codes (B clamped to [1, 32], placeholder B = 16) by round-to-nearest.
**Auditor.** `audit` returns the reasons it failed: `PARITY_FAIL` (table ≠ recomputation from (θ, φ, f/f_c)), `RANGE_FAIL` (a word outside [0, 2π_WAD)), `LINEARITY_FAIL` (|w_mn − (w_m0 + w_0n)| circular > 1 ulp). **Lemma (linearity tolerance):** for correct tables the three words carry ≤ 0.5 ulp each and the modulus mismatch ≤ 0.075 ulp, so the integer discrepancy is ≤ 1; tested on a grid of 72 (θ, φ, f/f_c) triples. Any reason ⇒ action `ISOLATE_CHANNEL`. The digest is SHA-256 over the canonical table text.
`steering_ok` enforces 0 ≤ θ ≤ θ_max. `eirp_dbm` = P_element,dBm + 20·log10(N) (coherent N-element array, 0 dBi elements). Limits are caller-supplied.

## 6. R³ mapping
Step 1 State capture: integer telemetry inputs only (no ingest hardware here). Step 2 Invariant proof: plan validation, mask check, scan and EIRP checks, then `audit`. Step 3 Output: the quantized integer phase codes (demo prints a 16-bit table). The format expected by any specific photonic transceiver is **not specified** and must be supplied.

## 7. Verification
- 60 unit tests: exact-rational oracles, golden 90-digit vectors (regression pins for bit parity), boundary tests at one-ulp offsets, tamper tests for each auditor reason, ledger tamper and non-ASCII totality tests.
- AST mutation engine (`tools/mutants.py`): mutates comparison, arithmetic and boolean operators, integer constants and booleans, one at a time, in every source module. **509 mutants: 494 killed, 15 equivalent (each justified in `tools/equivalent_mutants.json`), 0 survivors.**
- Process notes, stated for honesty: the first full run left 70 survivors. Analysis found test gaps (e.g. log of 1 ulp, 3-entry ledger chains, exact 2π wrap, single-row tables, non-ASCII payloads), dead or redundant code (an unreachable normalisation loop, a redundant guard, CLI code), and sub-resolution mutants that perturb only 10⁻⁹⁰ digits (killed by golden vectors). A **defect in the mutation harness itself** was found midway: two mutants with the same description on different AST nodes shared a checkpoint key, so a result could leak between them (potentially hiding a survivor). It was fixed (the node index is now part of the key) and the suite rerun from scratch. The 15 equivalents are boundary-equal returns (`sat`/`clamp` at exactly the bound, `x = 0` cases), padding-length constants that cannot change a sliced parse, `k = 0` shifts, and a construction-scale constant whose derived constants were verified bit-identical across 10⁹⁹, 10¹⁰⁰ and 10¹⁰¹.
- Mutation testing shows the tests are sensitive to these mutation classes; it does not prove the model correct against reality.

## 8. Reproduce
`python3 tools/verify_capsule.py` (add `--full` to include the roughly four-minute mutation run). `python3 tools/build_capsule.py out.zip` rebuilds a byte-identical ZIP (fixed timestamps, sorted entries). The ledger (`ledger/ledger.jsonl`, SHA-256 hash chain, no timestamps) carries the full history from capsule v1.0.0; `python3 tools/ledger_cli.py verify` checks it. A hash chain proves internal consistency, not authenticity; signatures are out of scope.

## 9. Open items
Real mask tables and EIRP limits; hardware word format and bit width; array calibration and mutual-coupling models; amplitude taper and sidelobe/radiation-pattern verification (only phase is generated here); PLL/clock-phase drift (a physical effect outside integer math); machine-checked proofs of Theorems 1–3; certification and an actual air-gapped deployment path.
