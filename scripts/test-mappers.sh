#!/usr/bin/env bash
# Bulk-test both oncology mappers over example-data/oncology/*.json:
#  (a) Python: genomde_to_fhir.py must emit a Bundle (fhir.resources validates construction)
#  (b) FML:   matchbox $transform must return a Bundle (not an OperationOutcome)
# Reports ok/fail counts + first failures. Usage: bash scripts/test-mappers.sh
set -uo pipefail
cd "$(dirname "$0")/.."
MB="${MB:-http://localhost:8090/matchboxv3/fhir}"
SM="https://www.medizininformatik-initiative.de/fhir/StructureMap/GenomDeOncologyToMii"
mkdir -p out/py out/fml
py_ok=0; py_fail=0; fml_ok=0; fml_fail=0; fails=""
for f in example-data/oncology/*.json; do
  b=$(basename "$f" .json)
  # (a) Python
  if python3 mappers/python/genomde_to_fhir.py "$f" -o "out/py/$b.json" >/dev/null 2>"out/py/$b.err"; then
    py_ok=$((py_ok+1)); else py_fail=$((py_fail+1)); fails+="PY  $b: $(tail -1 out/py/$b.err)\n"; fi
  # (b) FML via matchbox
  code=$(curl -s -X POST -H "Content-Type: application/fhir+json" -H "Accept: application/fhir+json" \
        --data-binary @"$f" "$MB/StructureMap/\$transform?source=$SM" -o "out/fml/$b.json" -w '%{http_code}')
  rt=$(python3 -c "import json,sys;print(json.load(open('out/fml/$b.json')).get('resourceType'))" 2>/dev/null)
  if [ "$code" = "200" ] && [ "$rt" = "Bundle" ]; then
    fml_ok=$((fml_ok+1)); else fml_fail=$((fml_fail+1));
    diag=$(python3 -c "import json;print((json.load(open('out/fml/$b.json')).get('issue',[{}])[0].get('diagnostics','') or '')[:160])" 2>/dev/null)
    fails+="FML $b [$code/$rt]: $diag\n"; fi
done
echo "=== Python: ok=$py_ok fail=$py_fail | FML(matchbox): ok=$fml_ok fail=$fml_fail (of $(ls example-data/oncology/*.json|wc -l|tr -d ' ')) ==="
[ -n "$fails" ] && { echo "--- failures ---"; printf "%b" "$fails" | head -20; } || echo "all green"
# resource-count distribution (FML)
echo "--- FML bundle resource totals ---"
python3 - <<'PY'
import json,glob,collections
c=collections.Counter()
for f in glob.glob("out/fml/*.json"):
    d=json.load(open(f))
    if d.get("resourceType")=="Bundle":
        for e in d["entry"]: c[e["resource"]["resourceType"]]+=1
print(dict(c.most_common()))
PY
