#!/usr/bin/env bash
# Builds build/soc/gateware/digilent_arty.bit. Fails if any clock misses timing.
set -euo pipefail
. "$(cd "$(dirname "$0")/.." && pwd)/env.sh"
build_log="$ROWBIT_ROOT/build/soc.log"
mkdir -p "$ROWBIT_ROOT/build"

python3 "$ROWBIT_ROOT/soc/arty_soc.py" "$@" >"$build_log" 2>&1 || { tail -20 "$build_log"; exit 1; }

# LiteX passes --timing-allow-fail to nextpnr, so check the routed result ourselves
# (the earlier report is only a placement estimate).
last_route_line="$(grep -n "Running router2" "$build_log" | tail -1 | cut -d: -f1)"
routed_timing="$(tail -n +"$last_route_line" "$build_log" | grep "Max frequency")"
echo "$routed_timing"
if [ -z "$routed_timing" ] || grep -q FAIL <<<"$routed_timing"; then
  echo "timing failed, see $build_log"
  exit 1
fi
