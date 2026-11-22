from types import SimpleNamespace

from rowbit.operations.copy import init_rows
from rowbit.program import PROGRAM_DEPTH, Command, Program
from test_program_builder import decode


class RecordingSequencer:
    # Long timings so every command needs its own instruction: the most a copy can take.
    dram = SimpleNamespace(activate_to_precharge=20, precharge_to_activate=10)

    def __init__(self):
        self.programs = []

    def program(self):
        return Program(read_phase=0, write_phase=0, close_delay=20)

    def run(self, instructions):
        self.programs.append(instructions)


def test_init_rows_splits_many_rows_over_programs_that_fit():
    sequencer, rows = RecordingSequencer(), list(range(1, 1001))
    init_rows(sequencer, 2, 0, rows)
    assert len(sequencer.programs) > 1
    assert all(len(program) <= PROGRAM_DEPTH for program in sequencer.programs)
    activates = [address for program in sequencer.programs
                 for _, command, bank, address in decode(program) if command == Command.ACT and bank == 2]
    assert activates == [row for destination in rows for row in (0, destination)]
