# Scripts

| Script | What it does |
|---|---|
| `setup-toolchain.sh` | Installs the pinned toolchain and the Python `.venv`. Safe to re-run. |
| `check-toolchain.sh` | Checks every installed tool and package matches its pin. |
| `build-soc.sh [dir]` | Builds the bitstream into `dir` (default `build/soc`). Fails if timing isn't met. |
| `program-board.sh [bitstream]` | Loads the bitstream onto the Arty. The FPGA forgets it at power off. |
| `map-subarrays.sh` | Finds where every subarray starts on this board and saves it to `results/subarrays-<board serial>.json`. Takes a few minutes. |
| `toolchain-versions.sh` | The pinned tool versions, read by the other scripts. |
| `fasm2frames` | Step in `build-soc.sh`; you never run it directly. |
