"""Recommendations of the oncology plan block.

Therapy, study and preventive-measure recommendations are built by `onco.careplan` (it runs first and the
MTB Therapieplan references them); this step is intentionally empty and kept so the pipeline order in
`builders/__init__.py` stays stable.
"""


def build(ctx):
    return None
