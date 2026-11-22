import cocotb
import pytest

from rowbit.program import Command, encode_instruction
from sequencer_bench import Bench, run_simulation

ENTRIES = [0x0123456789ABCDEF_FEDCBA9876543210, (1 << 128) - 2]


@cocotb.test()
async def write_data_follows_each_write_by_the_write_latency(dut):
    latency = int(dut.WRITE_LATENCY.value)
    bench = Bench(dut)
    await bench.start()
    await bench.load([encode_instruction([(Command.WR, 0, 0)]),
                      encode_instruction([(Command.NOP,), (Command.NOP,), (Command.WR, 0, 8)])], ENTRIES)
    await bench.run()
    await bench.controller_refresh()
    await bench.wait_done()

    log = {entry["cycle"]: entry for entry in bench.dfi_log}
    writes = [(cycle, slot) for cycle, slot, command, *_ in bench.issued() if command == "WR"]
    assert len(writes) == 2
    for (cycle, slot), entry in zip(writes, ENTRIES):
        assert log[cycle]["wrdata_en"] == 1 << slot
        assert log[cycle + latency]["wrdata"] == entry


@pytest.mark.parametrize("latency", [1, 2])
def test_write_data(latency):
    run_simulation(__file__, {"WRITE_LATENCY": latency})
