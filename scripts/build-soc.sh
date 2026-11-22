#!/usr/bin/env bash
# Builds <output dir, default build/soc>/gateware/digilent_arty.bit. Fails if any clock misses timing.
set -euo pipefail
. "$(cd "$(dirname "$0")/.." && pwd)/env.sh"
output_dir="${1:-$ROWBIT_ROOT/build/soc}"
mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"  # absolute: the tools run inside gateware/
build_log="$output_dir.log"
name=digilent_arty  # LiteX's build name: the platform's name

fail() { tail -20 "$build_log"; echo "build failed, see $build_log"; exit 1; }

# LiteX only generates the sources; it can't drive nextpnr-himbaechel.
python3 "$ROWBIT_ROOT/soc/arty_soc.py" --output-dir "$output_dir" >"$build_log" 2>&1 || fail
cd "$output_dir/gateware"
db="$PRJXRAY_DB_DIR/$ROWBIT_FAMILY"
yosys -l "$name.rpt" "$name.ys" >>"$build_log" 2>&1 || fail
# Without --timing-allow-fail, a setup or hold violation makes nextpnr exit non-zero.
nextpnr-himbaechel --device "$ROWBIT_PART" --json "$name.json" -o xdc="$name.xdc" -o fasm="$name.fasm" \
  --report timing.json >>"$build_log" 2>&1 || fail
fasm2frames --part "$ROWBIT_PART" --db-root "$db" "$name.fasm" >"$name.frames" 2>>"$build_log" || fail
xc7frames2bit --part_file "$db/$ROWBIT_PART/part.yaml" --part_name "$ROWBIT_PART" \
  --frm_file "$name.frames" --output_file "$name.bit" >>"$build_log" 2>&1 || fail

python3 -c 'import json
for name, clock in json.load(open("timing.json"))["fmax"].items():
    print("%s: %.2f MHz (needs %.2f)" % (name, clock["achieved"], clock["constraint"]))'
