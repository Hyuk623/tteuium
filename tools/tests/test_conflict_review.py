"""Conflict page: the chain shown is exactly the decisions that join the two masks."""
from tools.conflict_review import chain


def doc(oid, kind, verdict, *panels):
    return dict(object_id=oid, decision=verdict, decision_detail=dict(kind=kind, masks=[dict(view=v, mask_ids=m) for v, m in panels]))


def test_chain_follows_same_and_duplicate_links_only():
    docs = [doc('d1', 'match', 'same', ('18', ['a373']), ('28', ['a182'])),
            doc('d2', 'match', 'same', ('21', ['a3']), ('28', ['a182'])),
            doc('d3', 'match', 'different', ('18', ['a373']), ('21', ['a3'])),
            doc('d4', 'dup', 'duplicate', ('27', ['a161', 'a166']), ('28', ['a174'])),
            doc('d5', 'match', 'same', ('22', ['a37']), ('27', ['a166']))]
    assert [d['object_id'] for d in chain(docs, 'a373', 'a3')] == ['d1', 'd2']
    assert [d['object_id'] for d in chain(docs, 'a37', 'a161')] == ['d5', 'd4']
    assert chain(docs, 'a373', 'a37') == []
