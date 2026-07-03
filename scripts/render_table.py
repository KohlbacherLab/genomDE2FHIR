#!/usr/bin/env python3
"""Render the mapping tables (3 CSVs) into one self-contained, filterable HTML page.
Usage: python3 scripts/render_table.py  ->  docs/mapping-table.html
"""
import csv, json, html
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
rows = []
for b, fn in [("ONC", "mapping_kdk_oncology.csv"), ("RD", "mapping_kdk_rarediseases.csv"), ("GRZ", "mapping_grz.csv")]:
    for r in csv.DictReader(open(ROOT / "mapping" / fn)):
        r["_b"] = b
        rows.append(r)
data = json.dumps(rows, ensure_ascii=False)
n = len(rows)
mapped = sum(1 for r in rows if r["status"] == "MAPPED")
draft = sum(1 for r in rows if r["status"] == "DRAFT")
nomap = sum(1 for r in rows if r["status"] == "NOMAP")
HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>genomDE2FHIR mapping table</title>
<style>
body{font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:16px;color:#1a1a1a;background:#fafafa}
h1{font-size:18px;font-weight:600;margin:0 0 4px}
.sub{color:#666;margin:0 0 12px}
.bar{position:sticky;top:0;background:#fafafa;padding:8px 0;border-bottom:1px solid #ddd;display:flex;gap:8px;flex-wrap:wrap;align-items:center;z-index:5}
.bar input,.bar select{padding:5px 8px;border:1px solid #ccc;border-radius:6px;font-size:13px}
.bar input[type=text]{flex:1;min-width:220px}
.pill{padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.MAPPED{background:#dcfce7;color:#166534}.DRAFT{background:#fef9c3;color:#854d0e}.NOMAP{background:#e5e7eb;color:#374151}
table{border-collapse:collapse;width:100%;background:#fff;margin-top:8px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid #eee;vertical-align:top}
th{position:sticky;top:46px;background:#f1f5f9;font-weight:600;cursor:pointer;font-size:12px}
td.p{font-family:ui-monospace,Menlo,monospace;font-size:12px;white-space:nowrap}
td.e{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#334155}
tr:hover{background:#f8fafc}
.b{font-weight:600;font-size:11px;padding:1px 5px;border-radius:4px}
.ONC{background:#fee2e2;color:#991b1b}.RD{background:#dbeafe;color:#1e40af}.GRZ{background:#dcfce7;color:#166534}
.cnt{color:#666;font-size:12px;margin-left:auto}
td small{color:#777}
</style></head><body>
<h1>genomDE Datenkranz &rarr; MII KDS &mdash; mapping table</h1>
<p class="sub">__N__ leaves &middot; <span class="pill MAPPED">MAPPED __MAPPED__</span> <span class="pill DRAFT">DRAFT __DRAFT__</span> <span class="pill NOMAP">NOMAP __NOMAP__</span></p>
<div class="bar">
<input type="text" id="q" placeholder="search path / module / profile / element / transform...">
<select id="fb"><option value="">all branches</option><option>ONC</option><option>RD</option><option>GRZ</option></select>
<select id="fs"><option value="">all status</option><option>MAPPED</option><option>DRAFT</option><option>NOMAP</option></select>
<span class="cnt" id="cnt"></span>
</div>
<table><thead><tr>
<th data-k="_b">Br</th><th data-k="path">path</th><th data-k="required">req</th>
<th data-k="mii_module">module</th><th data-k="mii_profile">profile</th><th data-k="fhir_element">FHIR element</th><th data-k="reference">reference</th><th data-k="status">status</th>
</tr></thead><tbody id="tb"></tbody></table>
<script>
const DATA=__DATA__;let sortK=null,sortDir=1;
const short=s=>s&&s.startsWith("http")?s.split("/").pop():s;
const esc=s=>(s||"").replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
function render(){
 const q=document.getElementById("q").value.toLowerCase(),fb=document.getElementById("fb").value,fs=document.getElementById("fs").value;
 let r=DATA.filter(d=>(!fb||d._b===fb)&&(!fs||d.status===fs)&&(!q||(d.path+d.mii_module+d.mii_profile+d.fhir_element+d.transform+d.enum).toLowerCase().includes(q)));
 if(sortK)r.sort((a,b)=>((a[sortK]||"")>(b[sortK]||"")?1:-1)*sortDir);
 document.getElementById("cnt").textContent=r.length+" / "+DATA.length+" rows";
 document.getElementById("tb").innerHTML=r.map(d=>`<tr>
<td><span class="b ${d._b}">${d._b}</span></td>
<td class="p" title="${esc(d.enum)}">${esc(d.path)}${d.type?` <small>${esc(d.type)}</small>`:""}</td>
<td>${d.required==="yes"?"&#9679;":""}</td>
<td>${esc(d.mii_module)}</td>
<td class="e" title="${esc(d.mii_profile)}">${esc(short(d.mii_profile))}</td>
<td class="e" title="${esc(d.transform)}">${esc(d.fhir_element)}</td>
<td class="e" title="${esc(d.reference)}">${esc(d.reference)}</td>
<td><span class="pill ${d.status}">${d.status}</span></td></tr>`).join("");
}
document.querySelectorAll("th").forEach(th=>th.onclick=()=>{const k=th.dataset.k;sortDir=(sortK===k)?-sortDir:1;sortK=k;render();});
["q","fb","fs"].forEach(id=>document.getElementById(id).oninput=render);
render();
</script></body></html>"""
out = (HTML.replace("__DATA__", data).replace("__N__", str(n)).replace("__MAPPED__", str(mapped))
       .replace("__DRAFT__", str(draft)).replace("__NOMAP__", str(nomap)))
(ROOT / "docs" / "mapping-table.html").write_text(out)
print(f"wrote docs/mapping-table.html ({n} rows, {len(out)//1024} KB)")
