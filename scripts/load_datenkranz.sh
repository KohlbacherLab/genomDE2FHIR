#!/usr/bin/env bash
# Load one genomDE / MV-GenomSeq Datenkranz JSON file into a FHIR server with the FML maps (deliverable b):
#   1. pick the main map from the file's branch (same rules as genomde2fhir.io.classify),
#   2. matchbox $transform  -> FHIR R4 transaction Bundle (MII KDS 2027 profiles),
#   3. POST the Bundle to HAPI (conditional PUTs on the resource key: loading the same file again creates nothing).
#
# Usage: scripts/load_datenkranz.sh <datenkranz.json> [matchbox-base] [hapi-base]
#   defaults: http://localhost:8091/matchboxv3/fhir  http://localhost:8092/fhir
#   env OUT=<file> keeps the transformed Bundle; env DRY_RUN=1 transforms only (Bundle on stdout, no HAPI POST).
# Prerequisite (once per matchbox start, and after every map change):
#   python scripts/build_mvgs.py --install <matchbox-base> --maps
set -euo pipefail

file=${1:?usage: $0 <datenkranz.json> [matchbox-base] [hapi-base]}
mb=${2:-http://localhost:8091/matchboxv3/fhir}; mb=${mb%/}
hapi=${3:-http://localhost:8092/fhir}; hapi=${hapi%/}
command -v jq >/dev/null || { echo "jq is required" >&2; exit 2; }
[ -r "$file" ] || { echo "cannot read $file" >&2; exit 2; }

branch=$(jq -r 'if (has("donors") and has("submission")) then "Grz"
                elif (.case | type) == "object" and (.case | has("diagnosisOd")) then "Oncology"
                elif (.case | type) == "object" and (.case | has("diagnosisRd")) then "RareDisease"
                else "unknown" end' "$file")
[ "$branch" != unknown ] || { echo "$file: not a KDK oncology / rare-disease or GRZ Datenkranz" >&2; exit 2; }
map="https://genomde.de/fhir/StructureMap/Datenkranz${branch}ToMii"

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
code=$(curl -sS -o "$tmp/bundle.json" -w '%{http_code}' -X POST \
  -H 'Content-Type: application/fhir+json' -H 'Accept: application/fhir+json' \
  --data-binary @"$file" "$mb/StructureMap/\$transform?source=$map")
if [ "$code" -ge 300 ] || [ "$(jq -r .resourceType "$tmp/bundle.json")" != Bundle ]; then
  echo "transform failed (HTTP $code, map $map):" >&2
  jq -r '[.issue[]? | .diagnostics // .details.text] | join("\n")' "$tmp/bundle.json" >&2 2>/dev/null || head -c 600 "$tmp/bundle.json" >&2
  echo "hint: are the maps loaded? python scripts/build_mvgs.py --install $mb --maps" >&2
  exit 1
fi
[ -z "${OUT:-}" ] || cp "$tmp/bundle.json" "$OUT"
if [ -n "${DRY_RUN:-}" ]; then cat "$tmp/bundle.json"; exit 0; fi

code=$(curl -sS -o "$tmp/response.json" -w '%{http_code}' -X POST \
  -H 'Content-Type: application/fhir+json' -H 'Accept: application/fhir+json' \
  --data-binary @"$tmp/bundle.json" "$hapi")
if [ "$code" -ge 300 ]; then
  echo "HAPI rejected the transaction (HTTP $code):" >&2
  jq -r '[.issue[]? | .diagnostics] | join("\n")' "$tmp/response.json" >&2 2>/dev/null || head -c 600 "$tmp/response.json" >&2
  exit 1
fi
echo "$file -> $map -> $hapi: $(jq -r '[.entry[].response.status | split(" ")[0]] | group_by(.)
      | map("\(length)x \(.[0])") | join(", ")' "$tmp/response.json") ($(jq '.entry | length' "$tmp/bundle.json") entries)"
