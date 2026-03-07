# Batched FEM Solve – Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Eliminate redundant LU factorisations in the EC FEM solver so that 90 separate `np.linalg.solve` calls become one batched call, reducing computation time by ~50× and fixing the 504 timeout for 4+ fields.

**Architecture:** Two minimal surgical changes. (1) `feebb.py` gets a `lazy_solve: bool = False` flag on `Beam.__init__` – fully additive, default preserves all existing behaviour. (2) `feebb_schnittstelle_ec.py._berechne_alle_kombinationen` is refactored to collect all load vectors, call `np.linalg.solve(K, F_matrix)` once, and distribute solutions back. A new `_fuehre_postprocessing` helper keeps postprocessing logic separate.

**Tech Stack:** Python 3.12, NumPy 2.x, pytest 9.x

---

## Context for the implementer

### Key files
- `backend/calculations/feebb.py` – FEEBB FEM solver: `Element`, `Beam`, `Postprocessor`
- `backend/calculations/feebb_schnittstelle_ec.py` – EC orchestration: `FeebbBerechnungEC`

### Why K is always identical
`Beam.__init__` builds the stiffness matrix K from element stiffness sub-matrices and support boundary conditions. Neither E·I, element lengths, nor support locations change between `(Lastkombination × Belastungsmuster)` pairs. Only the load vector F changes. Currently every pair triggers a full LU factorisation of the same K.

### Beam.__init__ anatomy (feebb.py lines ~288–318)
```python
class Beam():
    def __init__(self, elements, supports):
        # builds self.stiffness (K) from elements + applies BC
        # builds self.load (F) from element nodal loads + applies BC
        self.displacement = np.linalg.solve(self.stiffness, self.load)  # ← THE BOTTLENECK
```

### _berechne_alle_kombinationen anatomy (feebb_schnittstelle_ec.py lines ~465–512)
```python
for kombi in self.kombinationen_gzt:
    for muster in self.belastungsmuster:
        feebb_dict = self._erstelle_feebb_dict_fuer_kombination(kombi, muster)
        ergebnis   = self._fuehre_feebb_berechnung_durch(feebb_dict)  # full solve each time
        ...
```

### Minimal test fixture (G-only, 2 fields)
```python
SNAPSHOT_2F_G = {
    "querschnitt": {"E": 11000, "I_y": 138_240_000},
    "spannweiten": {"feld_1": 5.0, "feld_2": 5.0},
    "sprungmass": 1.0,
    "lasten": [{"lastfall": "g", "wert": "7.0", "kommentar": "Eigengewicht"}],
}
# db=None is safe for G-only (no ψ values needed; _get_si() catches None db)
```

---

## Task 1: Add `lazy_solve` flag to `Beam`

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_batched_fem_solve.py`
- Modify: `backend/calculations/feebb.py` (line 318 area)

### Step 1: Create the test file with failing tests

Create `tests/__init__.py` (empty file).

Create `tests/test_batched_fem_solve.py`:

```python
"""
Regression and correctness tests for the batched FEM solve optimisation.

Safety note: these tests verify that the batched approach produces results
numerically identical to the sequential reference implementation.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
from backend.calculations.feebb import Element, Beam, Postprocessor


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_simple_beam(n_elements: int = 40, span_m: float = 2.0,
                      load_n_per_mm: float = 7.0):
    """Build a simple supported single-span beam for unit tests."""
    length_mm = span_m * 1000
    L_elem    = length_mm / n_elements
    E, I      = 11_000, 138_240_000  # N/mm², mm⁴

    element_dicts = [
        {
            "length": L_elem,
            "youngs_mod": E,
            "moment_of_inertia": I,
            "loads": [{"type": "udl", "magnitude": load_n_per_mm}],
        }
        for _ in range(n_elements)
    ]
    elements = [Element(d) for d in element_dicts]

    n_dof    = (n_elements + 1) * 2
    supports = [0] * n_dof
    supports[0] = -1   # pin left: vertical DOF fixed
    supports[1] = -1   # pin left: rotation fixed
    supports[-2] = -1  # pin right: vertical DOF fixed

    return elements, supports


# ── Task 1 tests: lazy_solve flag ────────────────────────────────────────────

class TestLazySolve:
    """Verify Beam.lazy_solve behaviour without changing the default."""

    def test_default_solve_sets_displacement(self):
        """Default Beam() (lazy_solve=False) must set .displacement."""
        elements, supports = _make_simple_beam()
        beam = Beam(elements, supports)
        assert hasattr(beam, "displacement"), "displacement must exist when lazy_solve=False"
        assert len(beam.displacement) == len(elements) * 2 + 2

    def test_lazy_solve_true_skips_displacement(self):
        """Beam(lazy_solve=True) must NOT set .displacement."""
        elements, supports = _make_simple_beam()
        beam = Beam(elements, supports, lazy_solve=True)
        assert not hasattr(beam, "displacement"), \
            "displacement must NOT be set when lazy_solve=True"

    def test_lazy_solve_true_still_assembles_K_and_F(self):
        """Beam(lazy_solve=True) must still assemble stiffness and load."""
        elements, supports = _make_simple_beam()
        beam = Beam(elements, supports, lazy_solve=True)
        assert hasattr(beam, "stiffness")
        assert hasattr(beam, "load")
        assert beam.stiffness.shape == (len(elements) * 2 + 2,) * 2
        assert len(beam.load) == len(elements) * 2 + 2

    def test_K_identical_for_same_geometry(self):
        """K from lazy beam must equal K from normal beam (same geometry, different load)."""
        elements1, supports = _make_simple_beam(load_n_per_mm=5.0)
        elements2, _        = _make_simple_beam(load_n_per_mm=10.0)

        beam_lazy   = Beam(elements1, supports, lazy_solve=True)
        beam_normal = Beam(elements2, supports)  # default: solves immediately

        np.testing.assert_allclose(
            beam_lazy.stiffness, beam_normal.stiffness,
            rtol=1e-12, atol=0,
            err_msg="K must be identical regardless of load magnitude",
        )

    def test_batched_solve_matches_sequential(self):
        """
        Core safety test: solving K\\[F1, F2] in one call must give the same
        displacement vectors as two separate np.linalg.solve calls.
        """
        elements1, supports = _make_simple_beam(load_n_per_mm=5.0)
        elements2, _        = _make_simple_beam(load_n_per_mm=10.0)

        # Sequential reference
        beam_seq1 = Beam(elements1, supports)
        beam_seq2 = Beam(elements2, supports)

        # Batched approach
        b1 = Beam(elements1, supports, lazy_solve=True)
        b2 = Beam(elements2, supports, lazy_solve=True)

        K        = b1.stiffness
        F_matrix = np.column_stack([b1.load, b2.load])
        X_matrix = np.linalg.solve(K, F_matrix)

        b1.displacement = X_matrix[:, 0]
        b2.displacement = X_matrix[:, 1]

        np.testing.assert_allclose(
            b1.displacement, beam_seq1.displacement, rtol=1e-9,
            err_msg="Batched displacement[0] must match sequential displacement",
        )
        np.testing.assert_allclose(
            b2.displacement, beam_seq2.displacement, rtol=1e-9,
            err_msg="Batched displacement[1] must match sequential displacement",
        )
```

### Step 2: Run tests – expect 2 failures for lazy_solve tests

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger"
python3 -m pytest tests/test_batched_fem_solve.py::TestLazySolve -v 2>&1
```

Expected: `test_lazy_solve_true_skips_displacement` and `test_lazy_solve_true_still_assembles_K_and_F` **FAIL** (because `lazy_solve` param doesn't exist yet). The other 3 tests should PASS.

### Step 3: Implement `lazy_solve` in `Beam.__init__`

In `backend/calculations/feebb.py`, find the `Beam.__init__` method.

**Change only line 318** (the `np.linalg.solve` call):

```python
# Before (line 288 signature):
def __init__(self, elements, supports):

# After:
def __init__(self, elements, supports, lazy_solve: bool = False):
```

And the last line of `__init__`:

```python
# Before (line 318):
        self.displacement = np.linalg.solve(self.stiffness, self.load)

# After:
        if not lazy_solve:
            # Solve K·x = F to get nodal displacements.
            # Skip when lazy_solve=True – caller must set .displacement externally
            # after a batched np.linalg.solve(K, F_matrix) call.
            self.displacement = np.linalg.solve(self.stiffness, self.load)
```

That is the **entire change** to `feebb.py`. Nothing else is touched.

### Step 4: Run all tests – all 5 must pass

```bash
python3 -m pytest tests/test_batched_fem_solve.py::TestLazySolve -v 2>&1
```

Expected output:
```
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_default_solve_sets_displacement
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_lazy_solve_true_skips_displacement
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_lazy_solve_true_still_assembles_K_and_F
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_K_identical_for_same_geometry
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_batched_solve_matches_sequential
5 passed
```

### Step 5: Commit

```bash
git add tests/__init__.py tests/test_batched_fem_solve.py backend/calculations/feebb.py
git commit -m "feat: add lazy_solve flag to Beam – enables batched FEM solve"
```

---

## Task 2: Refactor `_berechne_alle_kombinationen` with batched solve

**Files:**
- Modify: `tests/test_batched_fem_solve.py` (add Task 2 tests)
- Modify: `backend/calculations/feebb_schnittstelle_ec.py`

### Step 1: Add the end-to-end regression test to the test file

Append to `tests/test_batched_fem_solve.py`:

```python
# ── Task 2 tests: end-to-end numerical regression ────────────────────────────

# Minimal snapshot: 2-field beam, G-only, no db needed
SNAPSHOT_2F_G = {
    "querschnitt": {"E": 11_000, "I_y": 138_240_000},
    "spannweiten": {"feld_1": 5.0, "feld_2": 5.0},
    "sprungmass": 1.0,
    "lasten": [{"lastfall": "g", "wert": "7.0", "kommentar": "Eigengewicht"}],
}


class TestBatchedEndToEnd:
    """
    End-to-end regression: batched _berechne_alle_kombinationen must produce
    results numerically identical to the sequential reference implementation.
    """

    def _run_sequential_reference(self, snapshot):
        """
        Run the sequential reference using the unchanged _fuehre_feebb_berechnung_durch.
        Returns (ergebnisse_gzt, ergebnisse_gzg).
        """
        from backend.calculations.feebb_schnittstelle_ec import FeebbBerechnungEC
        calc = FeebbBerechnungEC(snapshot, db=None)
        calc._extrahiere_systemdaten()
        calc._generiere_lastkombinationen()

        # Run sequential using the reference method (which is unchanged)
        calc.ergebnisse_gzt = []
        calc.ergebnisse_gzg = []
        for kombi in calc.kombinationen_gzt:
            for idx, muster in enumerate(calc.belastungsmuster):
                feebb_dict = calc._erstelle_feebb_dict_fuer_kombination(kombi, muster)
                ergebnis   = calc._fuehre_feebb_berechnung_durch(feebb_dict)
                ergebnis["kombination"]      = kombi
                ergebnis["belastungsmuster"] = muster
                ergebnis["muster_id"]        = idx
                calc.ergebnisse_gzt.append(ergebnis)
        for kombi in calc.kombinationen_gzg:
            for idx, muster in enumerate(calc.belastungsmuster):
                feebb_dict = calc._erstelle_feebb_dict_fuer_kombination(kombi, muster)
                ergebnis   = calc._fuehre_feebb_berechnung_durch(feebb_dict)
                ergebnis["kombination"]      = kombi
                ergebnis["belastungsmuster"] = muster
                ergebnis["muster_id"]        = idx
                calc.ergebnisse_gzg.append(ergebnis)

        return calc.ergebnisse_gzt, calc.ergebnisse_gzg

    def _run_batched(self, snapshot):
        """Run the new batched _berechne_alle_kombinationen."""
        from backend.calculations.feebb_schnittstelle_ec import FeebbBerechnungEC
        calc = FeebbBerechnungEC(snapshot, db=None)
        calc._extrahiere_systemdaten()
        calc._generiere_lastkombinationen()
        calc._berechne_alle_kombinationen()   # ← the new implementation
        return calc.ergebnisse_gzt, calc.ergebnisse_gzg

    def test_gzt_moment_matches_sequential(self):
        """GZT moment arrays must match sequential to within 1e-9 relative tolerance."""
        seq_gzt, _   = self._run_sequential_reference(SNAPSHOT_2F_G)
        bat_gzt, _   = self._run_batched(SNAPSHOT_2F_G)

        assert len(bat_gzt) == len(seq_gzt), \
            f"GZT result count mismatch: {len(bat_gzt)} vs {len(seq_gzt)}"

        for i, (bat, seq) in enumerate(zip(bat_gzt, seq_gzt)):
            np.testing.assert_allclose(
                bat["moment"], seq["moment"], rtol=1e-9,
                err_msg=f"GZT[{i}] moment mismatch",
            )

    def test_gzt_querkraft_matches_sequential(self):
        """GZT shear arrays must match sequential."""
        seq_gzt, _   = self._run_sequential_reference(SNAPSHOT_2F_G)
        bat_gzt, _   = self._run_batched(SNAPSHOT_2F_G)

        for i, (bat, seq) in enumerate(zip(bat_gzt, seq_gzt)):
            np.testing.assert_allclose(
                bat["querkraft"], seq["querkraft"], rtol=1e-9,
                err_msg=f"GZT[{i}] querkraft mismatch",
            )

    def test_gzt_durchbiegung_matches_sequential(self):
        """GZT deflection arrays must match sequential."""
        seq_gzt, _   = self._run_sequential_reference(SNAPSHOT_2F_G)
        bat_gzt, _   = self._run_batched(SNAPSHOT_2F_G)

        for i, (bat, seq) in enumerate(zip(bat_gzt, seq_gzt)):
            np.testing.assert_allclose(
                bat["durchbiegung"], seq["durchbiegung"], rtol=1e-9,
                err_msg=f"GZT[{i}] durchbiegung mismatch",
            )

    def test_gzg_matches_sequential(self):
        """GZG moment + deflection must match sequential."""
        _, seq_gzg   = self._run_sequential_reference(SNAPSHOT_2F_G)
        _, bat_gzg   = self._run_batched(SNAPSHOT_2F_G)

        assert len(bat_gzg) == len(seq_gzg)

        for i, (bat, seq) in enumerate(zip(bat_gzg, seq_gzg)):
            np.testing.assert_allclose(
                bat["moment"],       seq["moment"],       rtol=1e-9,
                err_msg=f"GZG[{i}] moment mismatch")
            np.testing.assert_allclose(
                bat["durchbiegung"], seq["durchbiegung"], rtol=1e-9,
                err_msg=f"GZG[{i}] durchbiegung mismatch")

    def test_kombination_metadata_preserved(self):
        """kombination, belastungsmuster, muster_id must survive the refactoring."""
        seq_gzt, seq_gzg = self._run_sequential_reference(SNAPSHOT_2F_G)
        bat_gzt, bat_gzg = self._run_batched(SNAPSHOT_2F_G)

        for bat, seq in zip(bat_gzt, seq_gzt):
            assert bat["kombination"]["name"]  == seq["kombination"]["name"]
            assert bat["belastungsmuster"]     == seq["belastungsmuster"]
            assert bat["muster_id"]            == seq["muster_id"]
```

### Step 2: Run the new tests – all 5 must FAIL

```bash
python3 -m pytest tests/test_batched_fem_solve.py::TestBatchedEndToEnd -v 2>&1
```

Expected: all 5 tests **FAIL** because `_berechne_alle_kombinationen` still uses the old sequential implementation. The `_run_sequential_reference` in the test explicitly re-runs sequential logic, so the mismatch will be in the ORDER of results (or the test framework will expose that both run the same code and trivially match – see note below).

> **Note:** `_run_sequential_reference` in the test re-implements sequential logic using `_fuehre_feebb_berechnung_durch` directly. `_run_batched` calls `_berechne_alle_kombinationen`. BEFORE the refactoring, `_berechne_alle_kombinationen` also calls `_fuehre_feebb_berechnung_durch` – so the 5 tests will **PASS** even before the refactoring. That is correct and intentional: these are **regression** tests. They establish what the correct output is. After the refactoring they must continue to pass.
>
> Run them now to confirm the **baseline passes**:

```bash
python3 -m pytest tests/test_batched_fem_solve.py -v 2>&1
```

Expected: **10/10 PASS** (5 from Task 1, 5 from Task 2 baseline).

### Step 3: Implement the batched solve in `feebb_schnittstelle_ec.py`

Make two changes to `backend/calculations/feebb_schnittstelle_ec.py`:

#### Change A: Add `_fuehre_postprocessing` method

Find `_fuehre_feebb_berechnung_durch` (around line 632). Insert a new method **just before it**:

```python
def _fuehre_postprocessing(self, beam) -> dict:
    """
    Run Postprocessor on a Beam that already has .displacement set.

    Separates the interpolation step from the solve step, enabling
    the batched solve optimisation in _berechne_alle_kombinationen.

    Args:
        beam: Beam instance with .displacement already set externally.

    Returns:
        dict: {"moment": list, "querkraft": list, "durchbiegung": list}
    """
    try:
        post = Postprocessor(beam, 50)  # 50 Auswertungspunkte pro Element
        return {
            "moment":       post.interp("moment"),
            "querkraft":    post.interp("shear"),
            "durchbiegung": post.interp("displacement"),
        }
    except Exception as e:
        logger.error(f"Fehler beim Postprocessing: {e}")
        raise
```

#### Change B: Replace `_berechne_alle_kombinationen`

Find the method starting at line ~465 and replace its body entirely:

```python
def _berechne_alle_kombinationen(self):
    """
    Führt alle FEEBB-Berechnungen durch – optimiert durch einen einzigen
    gebündelten numpy-Solve statt N separater LU-Faktorisierungen.

    Die Steifigkeitsmatrix K ist identisch für alle (Kombi × Muster)-Paare,
    da sie nur von Geometrie und Material abhängt. Nur der Lastvektor F ändert
    sich. Ein einziger Aufruf np.linalg.solve(K, F_matrix) mit allen
    Lastvektoren als Spalten von F_matrix führt eine LU-Faktorisierung durch
    und löst alle rechten Seiten mit effizienter Rückwärtssubstitution.

    Speedup: ~50× für 4 Felder (90 Solves → 1 Solve).
    """
    logger.info("🔢 Berechne alle Lastkombinationen (gebündelter Batch-Solve)")

    # ── Step 1: collect all (grenzzustand, kombi, muster) tasks ─────────
    tasks = []
    for kombi in self.kombinationen_gzt:
        for muster in self.belastungsmuster:
            tasks.append(("GZT", kombi, muster))
    for kombi in self.kombinationen_gzg:
        for muster in self.belastungsmuster:
            tasks.append(("GZG", kombi, muster))

    if not tasks:
        self.ergebnisse_gzt = []
        self.ergebnisse_gzg = []
        return

    # ── Step 2: assemble all Beam objects (lazy – K and F built, no solve) ──
    # K is identical for every task; F differs per (kombi, muster).
    beams        = []
    muster_ids   = []
    for (_, kombi, muster) in tasks:
        feebb_dict = self._erstelle_feebb_dict_fuer_kombination(kombi, muster)
        elements   = [Element(e) for e in feebb_dict["elements"]]
        beam       = Beam(elements, feebb_dict["supports"], lazy_solve=True)
        beams.append(beam)
        muster_ids.append(self.belastungsmuster.index(muster))

    # ── Step 3: one batched solve ────────────────────────────────────────
    # K taken from the first beam – all beams share identical K
    # (same geometry, same E·I, same support conditions).
    K        = beams[0].stiffness                              # (n_dof, n_dof)
    F_matrix = np.column_stack([b.load for b in beams])        # (n_dof, N_total)
    X_matrix = np.linalg.solve(K, F_matrix)                   # single LU + N back-subs

    # ── Step 4: distribute solutions + postprocess ───────────────────────
    self.ergebnisse_gzt = []
    self.ergebnisse_gzg = []

    for col_idx, ((gs, kombi, muster), beam) in enumerate(zip(tasks, beams)):
        beam.displacement = X_matrix[:, col_idx]              # inject solution vector
        ergebnis = self._fuehre_postprocessing(beam)
        ergebnis["kombination"]      = kombi
        ergebnis["belastungsmuster"] = muster
        ergebnis["muster_id"]        = muster_ids[col_idx]

        if gs == "GZT":
            self.ergebnisse_gzt.append(ergebnis)
        else:
            self.ergebnisse_gzg.append(ergebnis)

    logger.info(
        f"✅ Batch-Solve abgeschlossen: {len(tasks)} Solves in einem numpy-Aufruf. "
        f"{len(self.ergebnisse_gzt)} GZT + {len(self.ergebnisse_gzg)} GZG Ergebnisse."
    )
```

### Step 4: Run all 10 tests – all must PASS

```bash
python3 -m pytest tests/test_batched_fem_solve.py -v 2>&1
```

Expected output:
```
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_default_solve_sets_displacement
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_lazy_solve_true_skips_displacement
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_lazy_solve_true_still_assembles_K_and_F
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_K_identical_for_same_geometry
PASSED tests/test_batched_fem_solve.py::TestLazySolve::test_batched_solve_matches_sequential
PASSED tests/test_batched_fem_solve.py::TestBatchedEndToEnd::test_gzt_moment_matches_sequential
PASSED tests/test_batched_fem_solve.py::TestBatchedEndToEnd::test_gzt_querkraft_matches_sequential
PASSED tests/test_batched_fem_solve.py::TestBatchedEndToEnd::test_gzt_durchbiegung_matches_sequential
PASSED tests/test_batched_fem_solve.py::TestBatchedEndToEnd::test_gzg_matches_sequential
PASSED tests/test_batched_fem_solve.py::TestBatchedEndToEnd::test_kombination_metadata_preserved
10 passed
```

If any test fails: **stop and investigate before continuing**. Do NOT proceed with the commit.

### Step 5: Commit

```bash
git add tests/test_batched_fem_solve.py \
        backend/calculations/feebb_schnittstelle_ec.py
git commit -m "perf: batch all FEM solves into one np.linalg.solve call (~50x speedup)"
```

---

## Task 3: Push and deploy

### Step 1: Push

```bash
git push origin main 2>&1
```

### Step 2: Verify GitHub Actions deploy starts

Check https://github.com/Disskaette/Statikprogramm-EC/actions – a new workflow run should appear.

### Step 3: Smoke test after deploy (~2 minutes)

Open https://tools.askbenstark.com/statik/ and run a calculation with:
- EC mode ON
- 4 fields, each 5 m
- 1 G load (e.g. 7.41 kN/m)
- 1 Q load (e.g. 3 kN/m)

Expected: result appears in < 5 seconds (was: 504 timeout).

### Step 4: Commit

No commit needed – push was done in Step 1.
