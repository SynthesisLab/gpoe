import argparse
import sys
from typing import Callable
from tqdm import tqdm
from grape import types
from grape.automaton.automaton_manager import (
    dump_automaton_to_file,
    load_automaton_from_file,
)
from grape.automaton.loop_manager import LoopingAlgorithm, add_loops
from grape.automaton.spec_manager import despecialize, type_request_from_specialized
from grape.cli import dsl_loader
from grape.evaluator import Evaluator
from grape.pruning.equivalence_class_manager import EquivalenceClassManager
from grape.pruning.obs_equiv_pruner import prune


def sample_inputs(
    nsamples: int, sample_dict: dict[str, Callable], equal_dict: dict[str, Callable]
) -> dict[str, list]:
    inputs = {}
    pbar = tqdm(total=nsamples * len(sample_dict))
    pbar.set_description_str("sampling")
    for sampled_type, sample_fn in sample_dict.items():
        pbar.set_postfix_str(sampled_type)
        eq_fn = equal_dict.get(sampled_type, lambda x, y: x == y)
        sampled_inputs = []
        tries = 0
        while len(sampled_inputs) < nsamples and tries < 100:
            sampled = sample_fn()
            if all(not eq_fn(sampled, el) for el in sampled_inputs):
                sampled_inputs.append(sampled)
                pbar.update()
                tries = 0
            tries += 1
        while len(sampled_inputs) < nsamples:
            before = len(sampled_inputs)
            sampled_inputs += sampled_inputs
            sampled_inputs = sampled_inputs[:nsamples]
            pbar.update(len(sampled_inputs) - before)

        inputs[sampled_type] = sampled_inputs
    pbar.close()
    return inputs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Grammar Pruning with Observational Equivalence",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    def is_python_file(file_path: str) -> bool:
        if not file_path.endswith(".py"):
            raise argparse.ArgumentTypeError("Only Python (.py) files are allowed.")
        return file_path

    parser.add_argument(
        "dsl",
        type=is_python_file,
        help="your python file defining your Domain Specific Language",
    )
    parser.add_argument(
        "--size", type=int, default=7, help="max size of programs to check"
    )
    parser.add_argument(
        "--samples", type=int, default=1000, help="number of inputs to sample"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="./grammar.grape",
        help="output file containing the pruned grammar",
    )
    loop_strategies = [
        LoopingAlgorithm.GRAPE,
        LoopingAlgorithm.OBSERVATIONAL_EQUIVALENCE,
        "none",
    ]
    parser.add_argument(
        "--strategy",
        choices=loop_strategies,
        default=loop_strategies[0],
        help="looping algorithm to use",
    )
    parser.add_argument(
        "--from",
        dest="automaton",
        type=str,
        help="your starting automaton file",
    )
    parser.add_argument(
        "--classes",
        type=str,
        default=None,
        help="save equivalence classes ina JSON file",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    dsl, target_type, sample_dict, equal_dict, skip_exceptions = (
        dsl_loader.load_python_file(args.dsl)
    )
    inputs = sample_inputs(args.samples, sample_dict, equal_dict)

    evaluator = Evaluator(dsl, inputs, equal_dict, skip_exceptions)
    manager = EquivalenceClassManager()
    base_grammar = None
    base_aut_file: str = args.automaton or ""
    if len(base_aut_file) > 0:
        base_grammar = load_automaton_from_file(base_aut_file)
    reduced_grammar = prune(
        dsl,
        evaluator,
        manager,
        args.size,
        None,
        base_grammar,
    )
    type_req = type_request_from_specialized(reduced_grammar, dsl)
    loop_algorithm = args.strategy
    if loop_algorithm != "none":
        grammar = add_loops(reduced_grammar, dsl, loop_algorithm, use_tqdm=True)
    else:
        grammar = reduced_grammar

    types.check_automaton(grammar, dsl, type_req)
    grammar = despecialize(grammar, type_req)
    missing = dsl.find_missing_variants(grammar)
    if missing:
        print(
            f"[warning] the following primitives are not present in some versions in the grammar: {', '.join(missing)}",
            file=sys.stderr,
        )
    grammar = dsl.merge_type_variants(grammar)
    missing = dsl.find_missing_primitives(grammar)
    if missing:
        print(
            f"[warning] the following primitives are not present in the grammar: {', '.join(missing)}",
            file=sys.stderr,
        )

    dump_automaton_to_file(grammar, args.output)

    if args.classes is not None:
        with open(args.classes, "w") as fd:
            fd.write(manager.to_json())


if __name__ == "__main__":
    main()
