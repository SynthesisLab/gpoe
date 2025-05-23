from grape.automaton_generator import grammar_by_saturation
from grape.dsl import DSL
from grape.enumerator import Enumerator


dsl = DSL(
    {
        "1": ("int", 1),
        "+": ("int -> int -> int", lambda x, y: x + y),
    }
)

grammar = grammar_by_saturation(dsl, "int->int")
max_size = 5


def test_enumerator_size():
    e = Enumerator(grammar)
    g = e.enumerate_until_size(max_size)
    p = next(g)
    try:
        while True:
            p = g.send(True)
            assert p.size() < max_size
    except StopIteration:
        pass


def test_enumerator_unicity():
    programs = set()
    e = Enumerator(grammar)
    g = e.enumerate_until_size(max_size)
    p = next(g)
    try:
        while True:
            p = g.send(True)
            assert p not in programs
            programs.add(p)
    except StopIteration:
        pass


def test_enumerator_quantity():
    e = Enumerator(grammar)
    g = e.enumerate_until_size(max_size)
    p = next(g)
    count = 1
    try:
        while True:
            g.send(True)
            count += 1

    except StopIteration:
        pass
    assert grammar.trees_until_size(max_size - 1) == count


def test_enumerator_deterministic_order():
    e1 = Enumerator(grammar)
    e2 = Enumerator(grammar)
    g1 = e1.enumerate_until_size(max_size)
    g2 = e2.enumerate_until_size(max_size)
    assert next(g1) == next(g2)
    try:
        while True:
            assert g1.send(True) == g2.send(True)
    except StopIteration:
        pass
