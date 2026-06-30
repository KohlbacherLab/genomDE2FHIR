#!/usr/bin/env bash
# Profile-validation sweep: validate each resource in out/<dir>/*.json bundles against
# its meta.profile via matchbox $validate (MII packages must be loaded). Reports errors/profile.
# Usage: bash scripts/validate-bundles.sh [py|fml] [N_bundles]
set -uo pipefail; cd "$(dirname "$0")/.."
MB="${MB:-http://localhost:8090/matchboxv3/fhir}"; DIR="${1:-py}"; N="${2:-5}"
python3 - "$MB" "$DIR" "$N" <<'PY'
import json,glob,urllib.request,urllib.parse,collections,sys
MB,DIR,N=sys.argv[1],sys.argv[2],int(sys.argv[3])
res_err=collections.defaultdict(lambda:[0,0])  # profile -> [ok,err]
samples=collections.defaultdict(list)
for bf in sorted(glob.glob(f"out/{DIR}/*.json"))[:N]:
    for e in json.load(open(bf)).get("entry",[]):
        r=e["resource"]; prof=(r.get("meta",{}).get("profile") or [None])[0]
        if not prof: continue
        req=urllib.request.Request(f"{MB}/$validate?profile="+urllib.parse.quote(prof),
            data=json.dumps(r).encode(),method="POST",
            headers={"Content-Type":"application/fhir+json","Accept":"application/fhir+json"})
        try: oo=json.load(urllib.request.urlopen(req,timeout=60))
        except urllib.error.HTTPError as ex: oo=json.load(ex)
        errs=[i for i in oo.get("issue",[]) if i.get("severity") in ("error","fatal")]
        tag=prof.split("/")[-1]
        res_err[tag][1 if errs else 0]+=1
        for i in errs:
            d=i.get("diagnostics","")[:150]
            if d not in samples[tag]: samples[tag].append(d)
print(f"=== profile-validation sweep: out/{DIR} (first {N} bundles) ===")
for tag,(ok,err) in sorted(res_err.items()):
    # res_err[tag] = [err_count, ok_count] due to index trick; fix:
    pass
PY
