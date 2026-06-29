#!/usr/bin/env python3
"""Export the 3 mapping CSVs to one multi-tab .xlsx for Google Sheets editing.
Source cols (A-G, schema-derived skeleton) shaded grey/read-only-by-convention;
target cols (H-M) editable, with a status dropdown + colour coding.
Usage: python3 scripts/export_xlsx.py  ->  mapping/mapping-table.xlsx
Round-trip back: in Sheets, File > Download > CSV per tab into mapping/<name>.csv.
"""
import csv
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
SHEETS = [("KDK oncology", "mapping_kdk_oncology.csv"),
          ("KDK rare diseases", "mapping_kdk_rarediseases.csv"),
          ("GRZ", "mapping_grz.csv")]
SRC = ["path", "type", "required", "array", "enum", "format", "description"]  # A-G
TGT = ["mii_module", "mii_profile", "fhir_element", "transform", "status", "notes"]  # H-M
COLS = SRC + TGT
WIDTHS = [42, 9, 8, 6, 22, 9, 30, 12, 34, 34, 40, 9, 26]
STATUS = ["MAPPED", "DRAFT", "NOMAP", "TODO", "REMOVED?"]
FILL = {"MAPPED": "C6EFCE", "DRAFT": "FFEB9C", "NOMAP": "E5E7EB", "TODO": "FCE4D6", "REMOVED?": "F8CBAD"}
hdr_src = PatternFill("solid", fgColor="D9D9D9")
hdr_tgt = PatternFill("solid", fgColor="BDD7EE")
src_fill = PatternFill("solid", fgColor="F2F2F2")
thin = Side(style="thin", color="DDDDDD")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

wb = Workbook()
# legend sheet
lg = wb.active; lg.title = "README"
lg["A1"] = "genomDE Datenkranz → MII KDS — mapping table"; lg["A1"].font = Font(bold=True, size=14)
notes = [
 "", "One tab per source branch (GRZ and KDK kept separate — project convention).",
 "Columns A–G (grey) = schema-derived skeleton: DO NOT EDIT (regenerated from the JSON Schemas).",
 "Columns H–M (blue) = the mapping you edit: mii_module, mii_profile, fhir_element, transform, status, notes.",
 "status dropdown: MAPPED / DRAFT / NOMAP / TODO / REMOVED?  (colour-coded).",
 "",
 "Authoritative source of truth = the CSVs in git (KohlbacherLab/genomDE2FHIR, mapping/).",
 "Round-trip after editing: File > Download > Comma-separated values (.csv) for EACH tab,",
 "save over mapping/<same-filename>.csv in the repo, then commit. Keep column order intact.",
]
for i, t in enumerate(notes, start=2):
    lg.cell(row=i, column=1, value=t)
lg.column_dimensions["A"].width = 110

for title, fn in SHEETS:
    ws = wb.create_sheet(title)
    for c, name in enumerate(COLS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.font = Font(bold=True)
        cell.fill = hdr_src if name in SRC else hdr_tgt
        cell.border = border
        ws.column_dimensions[get_column_letter(c)].width = WIDTHS[c - 1]
    rows = list(csv.DictReader(open(ROOT / "mapping" / fn)))
    for r, row in enumerate(rows, start=2):
        for c, name in enumerate(COLS, start=1):
            cell = ws.cell(row=r, column=c, value=row.get(name, ""))
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=name in ("enum", "description", "transform", "fhir_element"))
            if name in SRC:
                cell.fill = src_fill
    last = len(rows) + 1
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}{last}"
    # status dropdown on column L (12)
    dv = DataValidation(type="list", formula1='"' + ",".join(STATUS) + '"', allow_blank=True)
    ws.add_data_validation(dv); dv.add(f"L2:L{last}")
    # colour status cells
    for st, hexc in FILL.items():
        ws.conditional_formatting.add(f"L2:L{last}",
            CellIsRule(operator="equal", formula=[f'"{st}"'], fill=PatternFill("solid", fgColor=hexc)))

out = ROOT / "mapping" / "mapping-table.xlsx"
wb.save(out)
print(f"wrote {out.relative_to(ROOT)} ({sum(1 for _ in open(ROOT/'mapping'/'mapping_kdk_oncology.csv'))-1}+ rows across 3 tabs)")
