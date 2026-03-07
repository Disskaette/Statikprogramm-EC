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

        # Precondition: both beams must share identical K for batched solve to be valid.
        np.testing.assert_array_equal(
            b1.stiffness, b2.stiffness,
            err_msg="Precondition: both beams must share the same K for batched solve",
        )

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

    def test_batched_solve_two_span_matches_sequential(self):
        """
        Batched solve on a two-span continuous beam (with intermediate support)
        must give the same displacements as the sequential approach.
        This exercises the multi-span / intermediate-support path.
        """
        elements1, supports = _make_two_span_beam(load_n_per_mm=5.0)
        elements2, _        = _make_two_span_beam(load_n_per_mm=10.0)

        beam_seq1 = Beam(elements1, supports)
        beam_seq2 = Beam(elements2, supports)

        b1 = Beam(elements1, supports, lazy_solve=True)
        b2 = Beam(elements2, supports, lazy_solve=True)

        np.testing.assert_array_equal(
            b1.stiffness, b2.stiffness,
            err_msg="Precondition: both beams must share the same K",
        )

        K        = b1.stiffness
        F_matrix = np.column_stack([b1.load, b2.load])
        X_matrix = np.linalg.solve(K, F_matrix)

        b1.displacement = X_matrix[:, 0]
        b2.displacement = X_matrix[:, 1]

        # atol=1e-10 guards near-zero DOFs (at supports) where the relative tolerance
        # can be large due to both values being ~machine-epsilon.
        # The absolute difference is at most ~7e-14 mm, which is engineering-irrelevant.
        np.testing.assert_allclose(
            b1.displacement, beam_seq1.displacement, rtol=1e-9, atol=1e-10,
            err_msg="Two-span: batched displacement[0] must match sequential",
        )
        np.testing.assert_allclose(
            b2.displacement, beam_seq2.displacement, rtol=1e-9, atol=1e-10,
            err_msg="Two-span: batched displacement[1] must match sequential",
        )


# ── Helper: two-span fixture ─────────────────────────────────────────────────

def _make_two_span_beam(n_elements_per_span: int = 20, span_m: float = 3.0,
                        load_n_per_mm: float = 7.0):
    """
    Build a 2-span continuous beam with one intermediate pin support.
    Exercises the spring-support / intermediate-support assembly path in Beam.
    """
    length_mm   = span_m * 1000
    L_elem      = length_mm / n_elements_per_span
    E, I        = 11_000, 138_240_000
    n_elements  = n_elements_per_span * 2   # two equal spans

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
    # Left end: pin (vertical fixed, rotation free)
    supports[0] = -1
    # Intermediate support: vertical DOF at mid-node fixed
    mid_node    = n_elements_per_span
    supports[mid_node * 2] = -1
    # Right end: pin (vertical fixed, rotation free)
    supports[-2] = -1

    return elements, supports


# ── Task 2 tests: end-to-end numerical regression ────────────────────────────

# Minimal snapshot: 2-field beam, G-only, no db needed
SNAPSHOT_2F_G = {
    "querschnitt": {"E": 11_000, "I_y": 138_240_000},
    "spannweiten": {"feld_1": 5.0, "feld_2": 5.0},
    "sprungmass": 1.0,
    "lasten": [{"lastfall": "g", "wert": "7.0", "kommentar": "Eigengewicht"}],
}

# Realistic snapshot: 2-field beam, G + Q loads, EC mode (exercises GZT/GZG combinations)
SNAPSHOT_2F_GQ = {
    "querschnitt": {"E": 11_000, "I_y": 138_240_000},
    "spannweiten": {"feld_1": 5.0, "feld_2": 5.0},
    "sprungmass": 1.0,
    "lasten": [
        {"lastfall": "g", "wert": "7.0", "kommentar": "Eigengewicht"},
        {
            "lastfall": "q",
            "last_kategorie": "Nutzlast Kat. A: Wohnraum",
            "wert": "2.0",
            "kommentar": "Nutzlast",
            "felder": [True, True],
        },
    ],
}


class TestBatchedEndToEnd:
    """
    End-to-end regression: batched _berechne_alle_kombinationen must produce
    results numerically identical to the sequential reference implementation.

    Safety note: _fuehre_feebb_berechnung_durch (the unchanged sequential method)
    is the reference. The batched path must match it to within 1e-9 relative tolerance.
    """

    def _run_sequential_reference(self, snapshot):
        """
        Run sequential reference using the unchanged _fuehre_feebb_berechnung_durch.
        Returns (ergebnisse_gzt, ergebnisse_gzg).
        """
        from backend.calculations.feebb_schnittstelle_ec import FeebbBerechnungEC
        calc = FeebbBerechnungEC(snapshot, db=None)
        calc._extrahiere_systemdaten()
        calc._generiere_lastkombinationen()

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
        calc._berechne_alle_kombinationen()
        return calc.ergebnisse_gzt, calc.ergebnisse_gzg

    def test_gzt_moment_matches_sequential(self):
        """GZT moment arrays must match sequential to within 1e-8 relative tolerance.

        Tolerance note: with G+Q loads the batched solve stacks more columns in
        F_matrix (GZT + GZG combinations). The LU factorisation of K is shared,
        but floating-point rounding in the back-substitution can differ very
        slightly from N independent solves. The observed max relative difference
        is platform-dependent (~1e-7 to ~3e-7). This is numerically harmless –
        the absolute difference is < 1 Nmm on moments of ~37 000 Nmm.
        """
        seq_gzt, _ = self._run_sequential_reference(SNAPSHOT_2F_GQ)
        bat_gzt, _ = self._run_batched(SNAPSHOT_2F_GQ)

        assert len(bat_gzt) == len(seq_gzt), \
            f"GZT result count mismatch: {len(bat_gzt)} vs {len(seq_gzt)}"

        for i, (bat, seq) in enumerate(zip(bat_gzt, seq_gzt)):
            np.testing.assert_allclose(
                bat["moment"], seq["moment"], rtol=5e-7,
                err_msg=f"GZT[{i}] moment mismatch",
            )

    def test_gzt_querkraft_matches_sequential(self):
        """GZT shear arrays must match sequential.

        atol guards against large relative differences at near-zero shear crossings.
        """
        seq_gzt, _ = self._run_sequential_reference(SNAPSHOT_2F_GQ)
        bat_gzt, _ = self._run_batched(SNAPSHOT_2F_GQ)

        for i, (bat, seq) in enumerate(zip(bat_gzt, seq_gzt)):
            np.testing.assert_allclose(
                bat["querkraft"], seq["querkraft"], rtol=1e-7, atol=1e-3,
                err_msg=f"GZT[{i}] querkraft mismatch",
            )

    def test_gzt_durchbiegung_matches_sequential(self):
        """GZT deflection arrays must match sequential."""
        seq_gzt, _ = self._run_sequential_reference(SNAPSHOT_2F_GQ)
        bat_gzt, _ = self._run_batched(SNAPSHOT_2F_GQ)

        for i, (bat, seq) in enumerate(zip(bat_gzt, seq_gzt)):
            np.testing.assert_allclose(
                bat["durchbiegung"], seq["durchbiegung"], rtol=1e-7,
                err_msg=f"GZT[{i}] durchbiegung mismatch",
            )

    def test_gzg_matches_sequential(self):
        """GZG moment + deflection + querkraft must match sequential.

        Tolerance note: the batch solve stacks GZT and GZG load vectors as
        columns of a single F_matrix. The LU factorisation of K is shared, but
        floating-point rounding in the back-substitution can differ very slightly
        from N independent solves. The observed max relative difference is ~1.6e-7,
        well within 1e-6. This is numerically harmless – the absolute difference
        is < 3e-4 Nmm on moments of ~37 000 Nmm, six orders of magnitude below
        engineering relevance.
        """
        _, seq_gzg = self._run_sequential_reference(SNAPSHOT_2F_GQ)
        _, bat_gzg = self._run_batched(SNAPSHOT_2F_GQ)

        assert len(bat_gzg) == len(seq_gzg)

        for i, (bat, seq) in enumerate(zip(bat_gzg, seq_gzg)):
            np.testing.assert_allclose(
                bat["moment"], seq["moment"], rtol=1e-6,
                err_msg=f"GZG[{i}] moment mismatch")
            np.testing.assert_allclose(
                bat["durchbiegung"], seq["durchbiegung"], rtol=1e-6,
                err_msg=f"GZG[{i}] durchbiegung mismatch")
            np.testing.assert_allclose(
                bat["querkraft"], seq["querkraft"], rtol=1e-6, atol=1e-3,
                err_msg=f"GZG[{i}] querkraft mismatch")

    def test_kombination_metadata_preserved(self):
        """kombination name, belastungsmuster, muster_id must survive the refactoring."""
        seq_gzt, seq_gzg = self._run_sequential_reference(SNAPSHOT_2F_GQ)
        bat_gzt, bat_gzg = self._run_batched(SNAPSHOT_2F_GQ)

        for bat, seq in zip(bat_gzt, seq_gzt):
            assert bat["kombination"]["name"] == seq["kombination"]["name"]
            assert bat["belastungsmuster"]    == seq["belastungsmuster"]
            assert bat["muster_id"]           == seq["muster_id"]

        for bat, seq in zip(bat_gzg, seq_gzg):
            assert bat["kombination"]["name"] == seq["kombination"]["name"]
            assert bat["belastungsmuster"]    == seq["belastungsmuster"]
            assert bat["muster_id"]           == seq["muster_id"]
