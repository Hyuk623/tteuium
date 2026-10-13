"""Split experiment and appearance matching: leakage rules, unmatched option, ties/conflicts kept for review."""
import numpy as np

from tools import split_experiment as se
from tools import xview_appearance as xa


def test_no_existing_tomato_model_is_a_valid_baseline_for_the_split():
    assert se.ROLES['dwt_02'] == 'evaluation' and se.ROLES['dwt_01'] == 'development'
    assert not se.valid_for_split(['dwt_01', 'dwt_03', 'dwt_04'])      # held-out dwt_02 fold still saw dwt_01
    assert not se.valid_for_split(['dwt_02', 'dwt_03'])
    assert se.valid_for_split(['dwt_03', 'dwt_04']) and se.valid_for_split([])


def test_assignment_allows_unmatched_and_never_forces_a_pair():
    S = np.array([[0.90, 0.20], [0.30, 0.40]])
    pairs, flags = xa.assign(S, cut=0.5)
    assert [(i, j) for i, j, _ in pairs] == [(0, 0)]           # row 1 stays unmatched (0.40 < cut)


def test_ties_and_contested_columns_are_flagged():
    S = np.array([[0.90, 0.89], [0.85, 0.30]])
    pairs, flags = xa.assign(S, cut=0.5)
    f = {(q['row'], q['col']): q['flags'] for q in flags}
    assert 'tie' in f[(0, 1)] or 'tie' in f.get((0, 0), [])
    assert any('contested' in v for v in f.values())         # both rows prefer column 0


def test_contradictory_cycle_is_found():
    links = {('A', 'B'): {'a1': 'b1'}, ('B', 'C'): {'b1': 'c1'}, ('A', 'C'): {'a1': 'c2'}}
    assert xa.cycles(links) == [('a1', 'b1', 'c1', 'c2')]
    ok = {('A', 'B'): {'a1': 'b1'}, ('B', 'C'): {'b1': 'c1'}, ('A', 'C'): {'a1': 'c1'}}
    assert xa.cycles(ok) == []


def test_masked_crop_greys_the_background_and_keeps_context():
    photo = np.zeros((100, 100, 3), np.uint8); photo[:] = (10, 200, 10)
    mask = np.zeros((100, 100), bool); mask[40:60, 30:70] = True
    masked, ctx = xa.crops(photo, mask)
    assert masked.shape == ctx.shape and (masked[0, 0] == 128).all() and (ctx[0, 0] == (10, 200, 10)).all()


def test_set_vector_is_normalised_mean():
    F = dict(ids=['a', 'b'], photos=['p', 'p'], masked=np.array([[1.0, 0], [0, 1.0]]), context=np.eye(2))
    v = xa.set_vector(F, ['a', 'b'])
    assert np.isclose(np.linalg.norm(v), 1) and np.allclose(v, [2 ** -0.5, 2 ** -0.5])
    assert xa.set_vector(F, ['zzz']) is None
