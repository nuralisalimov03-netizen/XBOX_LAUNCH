"""Точка входа SeriesDemo.exe — оконное демо каркаса эмулятора."""
import sys

from series_emulator.frontend import run_gui

if __name__ == "__main__":
    sys.exit(run_gui())
