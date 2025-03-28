from abc import ABC, abstractmethod
from typing import List


class Program(ABC):
    def __hash__(self):
        return self._hash

    def __eq__(self, other: "Program") -> bool:
        return self._hash == other._hash

    def __repr__(self):
        return str(self)

    def same_var_used_more_than_once(self) -> tuple[bool, set[int]]:
        used = set()
        return self.__used_vars__(used), used

    def can_be_embed_into(self, other: "Program") -> bool:
        return False

    @abstractmethod
    def size(self) -> int:
        pass

    @abstractmethod
    def __used_vars__(self, used: set[int]) -> bool:
        """
        Return true if the same var has been used twice.
        """
        pass

    @classmethod
    def parse(cls, program: str) -> "Program":
        if "(" == program[0]:
            program = program.strip("() ")
            function = Program.parse(program[: program.find(" ")])
            rest = program[program.find(" ") + 1 :].strip()
            args = []
            while len(rest) > 0:
                arg = Program.parse(rest)
                rest = rest[len(str(arg)) :].strip(" ")
                args.append(arg)
                if rest.startswith(")"):
                    break
            return Function(function, args)

        else:
            if " " in program:
                program = program[: program.find(" ")]
            program = program.strip("() ")
            if program.startswith("var"):
                return Variable(int(program[len("var") :]))
            else:
                return Primitive(program)


class Variable(Program):
    def __init__(self, no: int):
        self.no = no
        self._hash = no

    def __str__(self):
        return f"var{self.no}"

    def __used_vars__(self, used: set[int]) -> bool:
        if self.no in used:
            return True
        used.add(self.no)
        return False

    def can_be_embed_into(self, other: "Program") -> bool:
        return True

    def size(self) -> int:
        return 1


class Primitive(Program):
    def __init__(self, name: str):
        self.name: str = name
        self._hash = hash(name)

    def __str__(self):
        return self.name

    def __used_vars__(self, used: set[int]) -> bool:
        return False

    def can_be_embed_into(self, other: "Program") -> bool:
        return self == other

    def size(self) -> int:
        return 1


class Function(Program):
    def __init__(self, function: Program, arguments: List[Program]):
        self.function = function
        self.arguments = arguments
        self._hash = hash((function, *arguments))

    def __str__(self):
        args = " ".join(map(str, self.arguments))
        return f"({self.function} {args})"

    def __used_vars__(self, used: set[int]) -> bool:
        if self.function.__used_vars__(used):
            return True
        return any(arg.__used_vars__(used) for arg in self.arguments)

    def can_be_embed_into(self, other: "Program") -> bool:
        if isinstance(other, Function):
            return self.function.can_be_embed_into(other.function) and all(
                argm.can_be_embed_into(argo)
                for argm, argo in zip(self.arguments, other.arguments)
            )
        else:
            return False

    def size(self) -> int:
        return self.function.size() + sum(arg.size() for arg in self.arguments)
