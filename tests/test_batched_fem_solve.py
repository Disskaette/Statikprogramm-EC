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

        np.testing.assert_allclose(
            b1.displacement, beam_seq1.displacement, rtol=1e-9,
            err_msg="Two-span: batched displacement[0] must match sequential",
        )
        np.testing.assert_allclose(
            b2.displacement, beam_seq2.displacement, rtol=1e-9,
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
