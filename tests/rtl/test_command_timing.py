import cocotb

from rowbit.program import Command, encode_instruction
from sequencer_bench import Bench, run_simulation

NOP = (Command.NOP,)


@cocotb.test()
async def commands_land_on_their_slot_and_cycle(dut):
    bench = Bench(dut)
    await bench.start()
    await bench.load([
        encode_instruction([NOP, (Command.ACT, 2, 0x1234), NOP, (Command.PRE, 2, 0)], wait=2),
        encode_instruction([(Command.RD, 5, 8), (Command.WR, 6, 16), (Command.REF,), (Command.ZQCS,)]),
        encode_instruction([(Command.PRE, 0, 1 << 10)]),
    ])
    await bench.run()
    await bench.controller_refresh()
    await bench.wait_done()

    issued = bench.issued()
    first = issued[0][0]
    assert [(cycle - first, *rest) for cycle, *rest in issued] == [
        (0, 1, "ACT", 2, 0x1234),
        (0, 3, "PRE", 2, 0),
        (3, 0, "RD", 5, 8),    # wait=2 leaves two idle cycles
        (3, 1, "WR", 6, 16),
        (3, 2, "REF", 0, 0),
        (3, 3, "ZQCS", 0, 0),
        (4, 0, "PRE", 0, 1 << 10),
    ]


def test_command_timing():
    run_simulation(__file__)
