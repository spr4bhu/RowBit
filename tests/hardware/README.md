# Hardware tests

The real DRAM chip. Needs the Arty connected and the bitstream built: `python3 -m pytest tests/hardware`

The tests program the board themselves and skip if no Arty is connected.

| File | What it checks |
|---|---|
| `test_bridge.py` | Register and block round trips over the UART, at full speed. |
| `test_dram.py` | The BIOS calibrated DRAM and random words read back. |
| `test_sequencer.py` | Sequencer and controller see each other's reads and writes. |
| `test_activation_latency.py` | Reading too soon after activate gives errors; at spec it doesn't. |
| `test_retention.py` | Bit flips grow with time without refresh. Slow (refresh off for 20 s, then 40 s). |
| `test_copy.py` | Row copy overwrites the destination with the source. |
| `test_init.py` | Row init sets every row to the pattern. |
| `test_subarrays.py` | Every subarray boundary is found; copies work inside a subarray and fail across. |
