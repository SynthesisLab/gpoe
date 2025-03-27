from collections import defaultdict
from itertools import product
from typing import Any

from gpoe.program import Primitive, Program, Variable
from gpoe.tree_automaton import DFTA


def return_type(type_req: str) -> str:
    return type_req.split("->")[-1].strip()


def arguments(type_req: str) -> tuple[str, ...]:
    return tuple(map(lambda x: x.strip(), type_req.split("->")[:-1]))


def parse(type_req: str) -> tuple[tuple[str, ...], str]:
    elems = tuple(map(lambda x: x.strip(), type_req.split("->")))
    return elems[:-1], elems[-1]


def all_variants(type_req: str) -> list[str]:
    elements = map(lambda x: x.strip(), type_req.split("->"))
    names = []
    names2possibles = {}
    for i, el in enumerate(elements):
        if el.startswith("'"):
            # Polymorphic type
            if "[" in el and "]" in el:
                sum_parenthesis = el[el.find("[") + 1 : -1]
                possibles = all_variants(sum_parenthesis)
                name = el[1 : el.find("[")].strip()
                names2possibles[name] = possibles
            else:
                name = el[1:]
                assert name in names2possibles, (
                    f"polymorphic name '{name}' used before definition! defined: {', '.join(map(str, names2possibles.keys()))}"
                )
            names.append(name)
        elif "|" in el:
            # Sum type
            names.append(i)
            possibles = list(map(lambda x: x.strip(), el.split("|")))
            names2possibles[i] = possibles
        else:
            names.append(i)
            names2possibles[i] = [el]
    out = []
    possibles = [[(name, x) for x in poss] for name, poss in names2possibles.items()]

    def get_by_name(n, conf):
        return [t for name, t in conf if name == n][0]

    for conf in product(*possibles):
        type_req_variant = "->".join(map(lambda n: get_by_name(n, conf), names))
        out.append(type_req_variant)
    return out


def check_automaton(
    dfta: DFTA[Any, Program], dsl: dict[str, tuple[str, callable]], type_req: str
) -> bool:
    var_types = arguments(type_req)
    state2type = {}
    state2reasons = defaultdict(list)

    def print_reason(state: Any) -> str:
        elements = [""]
        for (P, args), dst in state2reasons[state]:
            if len(args) > 0:
                elements.append(
                    f"\t{P} ({', '.join(map(lambda a: f'{a} [{state2type[a]}]', args))}) -> {dst} [{state2type[dst]}]"
                )
            else:
                elements.append(f"\t{P} -> {dst} [{state2type[dst]}]")
        return "\n".join(elements)

    def print_diff(transition) -> str:
        (P, args), dst = transition

        if len(args) == 0:
            if isinstance(P, Variable):
                target_type = var_types[P.no]
            else:
                target_type = dsl[str(P)][0]
            return f"\t{P} -> {dst} [{state2type[dst]} found: {target_type}]"
        else:
            assert isinstance(P, Primitive)
            arg_types, rtype = parse(dsl[P.name][0])
            args_part = []
            for arg_state, arg_type in zip(args, arg_types):
                base = f"{arg_state} [{state2type[arg_state]}"
                if state2type[arg_state] == arg_type:
                    base += "]"
                else:
                    base += f" found: {arg_type}]"
                args_part.append(base)
            return f"\t{P} ({', '.join(args_part)}) -> {dst} [{state2type[dst]}{'' if state2type[dst] == rtype else f' found: {rtype}'}]"

    def check(state: Any, target_type: str, transition) -> None:
        assert state not in state2type or state2type[state] == target_type, (
            f"type conflict for state: {state} between {target_type} and {state2type[state]} with transitions for {state2type[state]}: {print_reason(dst)}\nand transition for {target_type}:\n\t{print_diff(transition)}"
        )
        state2type[state] = target_type
        state2reasons[state].append(transition)

    for transition in dfta.rules.items():
        (P, args), dst = transition
        if len(args) == 0:
            if isinstance(P, Variable):
                target_type = var_types[P.no]
            else:
                target_type = dsl[str(P)][0]
            check(dst, target_type, transition)
        else:
            assert isinstance(P, Primitive)
            arg_types, rtype = parse(dsl[P.name][0])
            check(dst, rtype, transition)
            for arg_state, arg_type in zip(args, arg_types):
                check(arg_state, arg_type, transition)
