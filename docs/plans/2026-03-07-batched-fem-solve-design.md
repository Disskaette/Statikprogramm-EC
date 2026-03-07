# Design: Batched FEM Solve – Fix API 504 Timeout

**Date:** 2026-03-07
**Status:** Approved
**Author:** Developer Dave + Maximilian Stark

---

## Problem

In EC mode the backend runs one FEM solve per `(Lastkombination × Belastungsmuster)` pair.
For `n` fields, the number of patterns is `2^n - 1`:

| Fields | Patterns | × 6 combos | = FEM solves |
|--------|----------|------------|--------------|
| 2      | 3        | × 6        | 18           |
| 3      | 7        | × 6        | 42           |
| 4      | 15       | × 6        | **90**       |
| 5      | 31       | × 6        | 186          |

Each solve calls `np.linalg.solve(K, F)` which internally does a full **LU factorisation**
of `K` (O(n³)). The stiffness matrix `K` is **identical for every single solve** because it
depends only on geometry (element lengths) and material (E·I) – never on the loads.
Only the load vector `F` changes between patterns.

Measured on a development machine:
- 90 separate solves: **291 ms**
- 1 batched solve (one LU + 90 back-substitutions): **6 ms**  → **51× speedup**

On the VPS (slower CPU, shared resources) this becomes the 504 timeout source.

---

## Solution

Split the FEM solve into two stages:

1. **Assemble** – build `K` and each load vector `F_i` without solving.
2. **Batch solve** – call `np.linalg.solve(K, F_matrix)` once, where `F_matrix` has shape
   `(n_dof, N_total)`. NumPy performs one LU factorisation and `N_total` cheap back-substitutions.

### Key insight: K is always identical

`K` is assembled from element stiffness sub-matrices and support boundary conditions.
Neither element geometry/material nor the support locations change between patterns.
Every call to `Beam(elements, supports)` currently re-factorises the same `K`. This is the waste.

---

## Changed Files

| File | Change |
|------|--------|
| `backend/calculations/feebb.py` | Add `lazy_solve: bool = False` to `Beam.__init__` |
| `backend/calculations/feebb_schnittstelle_ec.py` | Refactor `_berechne_alle_kombinationen` + add `_fuehre_postprocessing` helper |

---

## feebb.py – Minimal additive change

```python
class Beam():
    def __init__(self, elements, supports, lazy_solve: bool = False):
        # ... all existing assembly code unchanged ...
        # self.stiffness built from elements + supports
        # self.load built from element nodal loads + BC zeroing

        if not lazy_solve:
            self.displacement = np.linalg.solve(self.stiffness, self.load)
        # When lazy_solve=True: displacement is NOT set here.
        # The caller must set beam.displacement externally before postprocessing.
```

**Safety guarantee:** Default is `False`. Every existing caller (desktop GUI, non-EC
web path, tests) is completely unaffected. The new codepath only activates when
the caller explicitly passes `lazy_solve=True`.

---

## feebb_schnittstelle_ec.py – New batched flow

### New helper: `_fuehre_postprocessing(self, beam)`

Extracts the Postprocessor logic from `_fuehre_feebb_berechnung_durch` into a
dedicated method. Keeps error handling in one place.

```python
def _fuehre_postprocessing(self, beam: Beam) -> dict:
    """Run Postprocessor on a Beam that already has .displacement set."""
    post = Postprocessor(beam, 50)
    return {
        "moment":       post.interp("moment"),
        "querkraft":    post.interp("shear"),
        "durchbiegung": post.interp("displacement"),
    }
```

### Refactored: `_berechne_alle_kombinationen`

```python
def _berechne_alle_kombinationen(self):
    # ── Step 1: collect all (grenzzustand, kombi, muster) tasks ──────────
    tasks = []
    for kombi in self.kombinationen_gzt:
        for muster in self.belastungsmuster:
            tasks.append(("GZT", kombi, muster))
    for kombi in self.kombinationen_gzg:
        for muster in self.belastungsmuster:
            tasks.append(("GZG", kombi, muster))

    # ── Step 2: assemble all Beam objects (lazy – no solve yet) ──────────
    # K is identical for all tasks; F differs per (kombi, muster).
    beams = []
    muster_indices = []
    for (gs, kombi, muster) in tasks:
        feebb_dict = self._erstelle_feebb_dict_fuer_kombination(kombi, muster)
        elements   = [Element(e) for e in feebb_dict["elements"]]
        beam       = Beam(elements, feebb_dict["supports"], lazy_solve=True)
        beams.append(beam)
        muster_indices.append(self.belastungsmuster.index(muster))

    # ── Step 3: one batched solve ─────────────────────────────────────────
    # K is taken from the first beam (all beams share the same K).
    K        = beams[0].stiffness                              # (n_dof, n_dof)
    F_matrix = np.column_stack([b.load for b in beams])       # (n_dof, N_total)
    X_matrix = np.linalg.solve(K, F_matrix)                   # (n_dof, N_total)

    # ── Step 4: postprocess each solution ────────────────────────────────
    self.ergebnisse_gzt = []
    self.ergebnisse_gzg = []

    for idx, ((gs, kombi, muster), beam) in enumerate(zip(tasks, beams)):
        beam.displacement = X_matrix[:, idx]                  # inject solution
        ergebnis           = self._fuehre_postprocessing(beam)
        ergebnis["kombination"]      = kombi
        ergebnis["belastungsmuster"] = muster
        ergebnis["muster_id"]        = muster_indices[idx]

        if gs == "GZT":
            self.ergebnisse_gzt.append(ergebnis)
        else:
            self.ergebnisse_gzg.append(ergebnis)

    logger.info(
        f"✅ Batch-Solve: {len(tasks)} Solves in einem numpy-Aufruf. "
        f"{len(self.ergebnisse_gzt)} GZT + {len(self.ergebnisse_gzg)} GZG Ergebnisse."
    )
```

### Keep `_fuehre_feebb_berechnung_durch` unchanged

The existing method is left in place (it is the fallback reference implementation and
documents the original sequential logic). It is no longer called from
`_berechne_alle_kombinationen` but remains for context and potential future use.

---

## What does NOT change

- All FEM mathematics (element stiffness, load vectors, Hermite interpolation)
- All EC0/EC5 design checks (`nachweis_ec5.py`)
- Load combination logic (`_generiere_lastkombinationen`)
- The envelope computation (`_berechne_envelope`)
- The full result structure returned to the API (same keys, same shapes)
- All other callers of `Beam` (desktop GUI, non-EC web path)

---

## Verification

1. **Numeric identity check**: run a reference case (2 fields, G+Q) before and after the change.
   Moments and deflections must match to within floating-point tolerance (`1e-9` relative).
2. **K identity assertion**: assert `np.allclose(beams[0].stiffness, beams[i].stiffness)`
   for a sample of beams to confirm the batching assumption holds.
3. **Result structure**: assert same keys in result dict as before.
4. **Manual smoke test**: deploy and run 4-field EC calculation – should complete in < 5 s.

---

## Expected performance

| Scenario | Before | After (est. VPS) |
|----------|--------|------------------|
| 2 fields, G+Q | < 1 s | < 1 s |
| 4 fields, G+Q | 60+ s (504) | < 3 s |
| 5 fields, G+Q | timeout | < 6 s |
