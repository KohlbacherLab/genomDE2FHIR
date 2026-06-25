#!/usr/bin/env bash
# Regenerate leaf skeletons from schemas and refresh the mapping tables.
# Idempotent: preserves hand-filled target columns. Run after any schema change.
set -euo pipefail
cd "$(dirname "$0")/.."

py=python3
declare -A roots=(
  [kdk_oncology]="schemas/kdk/Oncology.json"
  [kdk_rarediseases]="schemas/kdk/RareDiseases.json"
  [grz]="schemas/grz/grz-schema.json"
)

for name in "${!roots[@]}"; do
  $py scripts/extract_leaves.py "${roots[$name]}" "mapping/_leaves_${name}.csv"
  $py scripts/build_mapping_table.py "mapping/_leaves_${name}.csv" "mapping/mapping_${name}.csv"
done
echo "done."
