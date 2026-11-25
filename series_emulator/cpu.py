"""series_emulator.cpu — CPU-модуль эмулятора.

MiniX64 (фаза 1 из ROADMAP.md): интерпретатор упрощённого x86-64 класс-подобного
набора — 4 регистра общего назначения (rax/rbx/rcx/rdx), флаги ZF/SF,
условные переходы. StubCPU сохранён для совместимости старых тестов.
"""
from __future__ import annotations


class StubCPU:
    """Игрушечный аккумуляторный «процессор»: rax/rip + арифметика из байткода."""

    def __init__(self, rax: int = 0):
        self.rax = rax
        self.rip = 0
        self.halted = False
        self.trace = []
        self.program = []

    def load_program(self, program):
        self.program = list(program)
        self.rip = 0
        self.halted = False

    def step(self) -> str:
        if self.rip >= len(self.program):
            self.halted = True
            return "halt"
        op = self.program[self.rip]
        self.rip += 1
        if op == "nop":
            done = "nop"
        elif op == "set":
            self.rax = int(self.program[self.rip]); self.rip += 1
            done = "set rax=%d" % self.rax
        elif op == "add":
            self.rax += int(self.program[self.rip]); self.rip += 1
            done = "add -> %d" % self.rax
        elif op == "sub":
            self.rax -= int(self.program[self.rip]); self.rip += 1
            done = "sub -> %d" % self.rax
        elif op == "hlt":
            self.halted = True
            done = "halt"
        else:
            raise ValueError("Неизвестная инструкция: %r" % op)
        self.trace.append(done)
        return done

    def run(self, max_steps: int = 10000):
        steps = 0
        while not self.halted and steps < max_steps:
            self.step()
            steps += 1
        return steps


GP_REGS = ("rax", "rbx", "rcx", "rdx")


class ProgramError(Exception):
    pass


class MiniX64:
    """Интерпретатор мини-x86-64: mov/add/sub/inc/dec/cmp/jmp/je/jne/hlt.

    Программа — список инструкций-кортежей, например:
        ("mov", "rax", 5), ("add", "rax", 3), ("cmp", "rax", 8), ("je", 5), ("hlt",)
    Переходы — по индексу инструкции.
    """

    OPCODES = {"mov", "add", "sub", "inc", "dec", "cmp", "jmp", "je", "jne", "hlt"}

    def __init__(self):
        self.regs = {r: 0 for r in GP_REGS}
        self.rip = 0
        self.halted = False
        self.flags = {"zf": False, "sf": False}
        self.program = []
        self.trace = []

    def load(self, program):
        for instr in program:
            if not instr or instr[0] not in self.OPCODES:
                raise ProgramError("Плохая инструкция: %r" % (instr,))
        self.program = list(program)
        self.rip = 0
        self.halted = False
        self.trace = []

    def _value(self, operand):
        if isinstance(operand, str):
            if operand in self.regs:
                return self.regs[operand]
            raise ProgramError("Неизвестный регистр: %r" % operand)
        if isinstance(operand, int):
            return operand
        raise ProgramError("Плохой операнд: %r" % (operand,))

    def step(self):
        if self.halted or self.rip >= len(self.program):
            self.halted = True
            return "halt"
        pos = self.rip
        instr = self.program[pos]
        op, args = instr[0], instr[1:]

        if op == "hlt":
            self.halted = True
        elif op == "mov":
            dst = args[0]
            if dst not in self.regs:
                raise ProgramError("mov: не регистр: %r" % dst)
            self.regs[dst] = self._value(args[1])
        elif op in ("add", "sub"):
            dst = args[0]
            if dst not in self.regs:
                raise ProgramError("%s: не регистр: %r" % (op, dst))
            delta = self._value(args[1])
            self.regs[dst] += delta if op == "add" else -delta
        elif op in ("inc", "dec"):
            dst = args[0]
            if dst not in self.regs:
                raise ProgramError("%s: не регистр: %r" % (op, dst))
            self.regs[dst] += 1 if op == "inc" else -1
        elif op == "cmp":
            a, b = self._value(args[0]), self._value(args[1])
            self.flags["zf"] = a == b
            self.flags["sf"] = (a - b) < 0
        elif op == "jmp":
            self.rip = int(args[0])
            self.trace.append((pos, op))
            return op
        elif op in ("je", "jne"):
            taken = self.flags["zf"] if op == "je" else not self.flags["zf"]
            if taken:
                self.rip = int(args[0])
                self.trace.append((pos, op))
                return op
        else:
            raise ProgramError("Необработанная инструкция: %r" % (instr,))

        self.rip = pos + 1
        self.trace.append((pos, op, args))
        return op

    def run(self, max_steps: int = 100000):
        steps = 0
        while not self.halted and steps < max_steps:
            self.step()
            steps += 1
        if not self.halted:
            raise ProgramError("Программа не завершилась за %d шагов" % max_steps)
        return steps


def fib_program(n: int):
    """Программа для MiniX64: rax = fib(n), fib(0)=0, fib(1)=1.

    Регистры: rax=fib(тек.), rbx=fib(пред.), rcx=счётчик.
    """
    return [
        ("mov", "rax", 0),
        ("mov", "rbx", 1),
        ("mov", "rcx", n),
        ("cmp", "rcx", 0),
        ("je", 13),
        ("mov", "rdx", "rax"),
        ("add", "rax", "rbx"),
        ("mov", "rbx", "rdx"),
        ("dec", "rcx"),
        ("cmp", "rcx", 0),
        ("jne", 5),
        ("jmp", 13),
        ("hlt",),
    ]
