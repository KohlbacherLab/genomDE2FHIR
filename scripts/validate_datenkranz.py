#!/usr/bin/env python3
"""
MOVED — the Datenkranz JSON-Schema validator now lives in its own package/repo:

    genomde-dk-validator  ·  https://github.com/KohlbacherLab/genomde-dk-validator

It is self-contained (BfArM KDK+GRZ schemas vendored), pip-installable, and adds
unknown-field detection and the BfArM Qualitätssicherung semantic rules (--kdk-rules /
--grz-rules). This file is a thin pointer kept for backward compatibility; the standalone
package is the single source of truth.

Install + use:

    pip install git+https://github.com/KohlbacherLab/genomde-dk-validator.git
    genomde-dk-validator example-data/synthData-v1              # schema + unknown fields
    genomde-dk-validator --kdk-rules example-data/synthData-v1/nct   # + KDK QS rules
    genomde-dk-validator --grz-rules example-data/synthData-v1/grz   # + GRZ QS rules

(Needs Python >= 3.9 for jsonschema >= 4.18.)
"""
import shutil
import sys

_MSG = __doc__


def main() -> int:
    sys.stderr.write(_MSG)
    if shutil.which("genomde-dk-validator"):
        sys.stderr.write("\nDetected `genomde-dk-validator` on PATH — invoke it directly with your args.\n")
    else:
        sys.stderr.write("\nNot installed yet — run the pip command above.\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
