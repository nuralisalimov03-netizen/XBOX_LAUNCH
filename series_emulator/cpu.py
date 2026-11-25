"""series_emulator.cpu — заглушка CPU-ядра (Zen 2 -- пока StubCPU).

Настоящая эмуляция x86-64 — фаза 1 ROADMAP.md. Здесь уже есть интерфейс
регистров и пошаговый цикл, чтобы тесты и другие модули могли на него опираться.
"""
from __future__ import annotations


class StubCPU:
    """Игрушечный аккумуляторный «процессор»: rax/rip + арифметика из байткода."""

    OPCODES = {"nop": 0x90, "set": 0xB8, "add": 0x01, "sub": 0x2B, "hlt": 0xF4}

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
