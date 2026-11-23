#!/usr/bin/env bash
# Maps this board's subarrays (repaired rows included) once, into results/subarrays-<board serial>.json.
set -euo pipefail
. "$(cd "$(dirname "$0")/.." && pwd)/env.sh"
python3 -m rowbit.characterize.subarrays
