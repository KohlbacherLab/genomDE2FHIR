#!/usr/bin/env bash
# Adversarial review of the 2027 plan and its implementation with kimi (k3), the review round that could not run on
# 2026-10-09 (weekly quota exhausted). Writes docs/REVIEW-PLAN-2027-kimi.md; integrate the verified findings into
# docs/PLAN-2027.md (Review log) as done for codex and vibe.
#   scripts/review_plan_kimi.sh            (run from the repository root)
set -euo pipefail
cd "$(dirname "$0")/.."
out=docs/REVIEW-PLAN-2027-kimi.md
read -r -d '' brief <<'TXT' || true
You are an adversarial reviewer. Review docs/PLAN-2027.md (plan v0.3 with implementation status in section 11) for
converting genomDE / MV-GenomSeq Datenkranz JSON (KDK oncology, KDK rare disease, GRZ) to FHIR R4 transaction Bundles on
the MII KDS 2027.0.0 ballot: (a) Python package genomde2fhir/, (b) FML StructureMaps mappers/fml/ for matchbox
$transform -> HAPI, (c) matchbox validation (genomde2fhir/src/genomde2fhir/validate.py, scripts/run_corpus.py,
docs/E2E-REPORT-2027.md). Reference mapping: docs/REVIEW-TD-2026-10-06.md and mapping/*.csv; decisions:
docs/REPRESENTATIONS.md, docs/IDENTITY.md; ballot packages in ~/.fhir/packages. Read the code, do not trust the docs.
Find what is wrong, unverified, non-conformant or will break: MII profile conformance claims, identity/idempotency,
validation classification that could hide real errors (WAIVERS, source/unchecked/cascade classes), FML vs Python parity
blind spots, terminology handling, corpus/acceptance claims. Output: numbered findings, most severe first, each with
severity (BLOCKER/MAJOR/MINOR), file:line evidence, when it bites, and a concrete fix. No praise, no summary of the plan.
TXT
kimi -m kimi-code/k3 -p "$brief" > "$out"
echo "wrote $out"
