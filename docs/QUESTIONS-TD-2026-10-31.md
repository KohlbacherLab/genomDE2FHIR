---
title: "MV-GenomSeq → MII KDS 2027: Rückfragen zur Mapping-Tabelle"
subtitle: "Überarbeitete Fassung zur Kommentierung"
date: "31. Oktober 2026"
lang: de
---

# Worum es geht

Wir bilden die drei Datenkranz-Zweige des Modellvorhabens Genomsequenzierung (KDK Onkologie, KDK Seltene
Erkrankungen, GRZ) auf die MII-Kerndatensatz-Profile ab, Zielversion **2027.0.0-Ballot**. Sie haben unsere
Mapping-Tabelle am 06.10.2026 kommentiert. Jede Ihrer 205 Anmerkungen ist entweder in unsere Tabelle übernommen
(einige übergangsweise mit einer eigenen Darstellung) oder Gegenstand einer Frage; die Fragen nennen 71 Ihrer Zeilen,
Zeilen mit gleichlautender Anmerkung eingeschlossen. Die Nummern 1–25 entsprechen unserer Fassung vom 10.10.2026; die
Fragen 4 und 8 sind in andere aufgegangen. Neu sind die Fragen 26–35 in Abschnitt J: Punkte ohne direkten
Zeilenbezug, darunter zwei Paketdefekte, die die Validierung jedes MTB-Therapieplans und fast jedes NGS-Berichts
scheitern lassen.

Diese Fassung ersetzt die vom 27.10.2026. Wir haben alle Aussagen über die Pakete noch einmal unabhängig prüfen lassen
und mehrere korrigiert (u. a. Fragen 13, 19, 24); einige Fragen, die die Pakete selbst beantworten, sind jetzt
Feststellungen.

**Aufbau jeder Frage.** Jede Frage hat vier kurze Absätze:

- *Hintergrund*: Welches Datenkranz-Feld betroffen ist und warum die Zuordnung nicht aufgeht.
- *Im Paket*: Was die Pakete tatsächlich festlegen. Geprüft am 27. und 31.10.2026 gegen `onkologie`, `mtb`, `molgen`
  je `2027.0.0-ballot.1`, `seltene` und `consent` je `2027.0.0-ballot`, `hl7.fhir.uv.genomics-reporting 3.0.0`
  (im Folgenden „GR“) und, wo es um Änderungen geht, die 2026-Pakete.
- *Ihre Anmerkung*: Die Zeilen Ihrer Tabelle (Tabs *KDK oncology*, *KDK rare diseases*, *GRZ*, *Open Issues*,
  Excel-Zeilennummern) und Ihr Vorschlag in unseren Worten.
- *Unser Stand*: Was unsere Umsetzung heute erzeugt.

Dann die **Frage**, so gestellt, dass eine Antwort reicht: Ja/Nein, eine Wahl zwischen (a)/(b), oder eine
konkrete Angabe. Wo Sie etwas nicht allein entscheiden können (Ballot-Ausgang, Zuständigkeit einer anderen
Gruppe), fragen wir nach Ihrer Empfehlung oder nach dem richtigen Ansprechpartner.

**Verweise.** Kennungen wie *MTB-12* bezeichnen unsere Entwürfe für Ballot-Kommentare zum KDS 2027. Sie sind
noch nicht eingereicht; die zitierten Entwürfe stehen vollständig in Anhang A. Deren Angabe „Bezug“ verweist auf
die Nummern in `docs/DISCUSS-TD-2026-10-09.md`. *HDB-975* und *HDB-976* sind Ihre
bereits eingereichten Ballot-Tickets. Begriffe aus unserem Projekt erklärt Anhang B, Beispiele unserer Ausgabe
zeigt Anhang C.

**Bitte vorab.** Zwei Punkte betreffen alle Fragen:

1. Die Kommentarfrist zum Ballot (27.10.2026) ist abgelaufen. Nimmt MII unsere Entwürfe noch an, und wer reicht sie
   ein, Sie oder wir?
2. Können Sie uns die Texte von HDB-975 und HDB-976 zur Verfügung stellen? Fünf unserer Entwürfe
   (MOLGEN-3 bis MOLGEN-5, SE-1, SE-2) sollen diese Tickets nur unterstützen und nicht wiederholen.
   Die Fragen 15, 16 und 18 hängen vom Wortlaut dieser Tickets ab.

# A. Einwilligung (alle drei Datensätze)

## Frage 1 – Einwilligungsbereiche des Modellvorhabens

**Hintergrund.** Die Teilnahmeerklärung zum Modellvorhaben hat drei Einwilligungsbereiche:
`mvSequencing`, `reIdentification`, `caseIdentification` (KDK `metaData.mvConsent.scope[].domain`, GRZ
`donors[].mvConsent.scope[].domain`). Sie sind keine Zwecke des Broad Consent.

**Im Paket.** `mii-pr-consent-einwilligung`: `Consent.provision.provision.code` ist 1..\* und *required* an
`mii-vs-consent-policy` gebunden, also an das gesamte Policy-CodeSystem `urn:oid:2.16.840.1.113883.3.1937.777.24.5.3`.
Das CodeSystem enthält in 2025.0.1 (66 Konzepte), 2026.0.0 und 2027.0.0-Ballot (je 124 Konzepte, 29 auf
oberster Ebene) die Konzepte …24.5.3.2 „IDAT erheben“, .6 „MDAT erheben“ und .8 „MDAT wissenschaftlich nutzen“
als Unterkonzepte von .1. Einen Code für das Modellvorhaben gibt es in keiner Version.

**Ihre Anmerkung.** KDK oncology 112; KDK rare diseases 46; GRZ 49; Open Issues 27, 63, 82. Das
Policy-CodeSystem sei 2027 unverändert, die OIDs .2/.6/.8 existierten in keiner Version, und die
MV-Bereiche seien ein Ballot-Kandidat für das Modul Consent.

**Unser Stand.** Die OIDs .2/.6/.8 existieren, bezeichnen aber Broad-Consent-Zwecke; deshalb verwenden wir sie
nicht mehr. Wir erzeugen ein eigenes Consent-Profil mit drei eigenen Codes für die drei Bereiche (Beispiel in
Anhang C). Es ist absichtlich nicht konform zu `mii-pr-consent-einwilligung`, weil die required-Bindung keinen
anderen Weg lässt (Entwurf CONSENT-1).

**Frage 1a.** Ist diese Interimslösung für Sie akzeptabel, bis Policy-Codes für das Modellvorhaben registriert sind?

**Frage 1b.** Wer ist für die Registrierung solcher Codes zuständig (AG Consent, TMF, eine andere Stelle), und
welche Form würden Sie empfehlen: eine eigene Gruppe unter …24.5.3 oder ein eigenes CodeSystem? Gibt es
bereits eine `policy.uri` für die MV-Teilnahmeerklärung?

# B. Variantennomenklatur und Identifikatoren (MTB, MolGen)

## Frage 2 – HGVS-Ausdrücke ohne Referenzsequenz

**Hintergrund.** Der KDK liefert `dnaChange` und `proteinChange` als bloße HGVS-Zeichenketten („c.34G>T“,
„p.V600E“); das Transkript steht getrennt in `transcriptId`, eine Protein-Referenzsequenz (NP_…) fehlt ganz.
Die HGVS-Nomenklatur verlangt für jeden Ausdruck eine passende Referenzsequenz.

**Im Paket.** `mii-pr-mtb-einfache-variante`: `component:representative-coding-hgvs.value[x]` und
`component:representative-protein-hgvs.value[x]` sind 1..1 und *required* an GR `hgvs-vs` gebunden. Das Profil
nennt als Beispiel für die Proteinebene `NP_000050.2:p.(Asn1836Lys)`. Unser Validierungsserver (matchbox
4.1.21 mit tx.fhir.org, Stand 10/2026) lehnt „c.34G>T“ und „p.V600E“ ab. Er akzeptiert „NM_004985.5:c.34G>T“,
und er akzeptiert auch die ClinVar-Schreibweise „NM_004985.5(KRAS):p.Gly12Cys“. Letztere ist nach
HGVS-Nomenklatur keine korrekte Protein-Referenz; die Akzeptanz durch den Server belegt also keine
normgerechte Form.

**Ihre Anmerkung.** KDK oncology 43, 48; Open Issues 7, 12. `dnaChange` und `proteinChange` nach
`coding.code` der Komponenten `representative-coding-hgvs` bzw. `-protein-hgvs`, System `varnomen`.

**Unser Stand.** Gleiche Komponenten und gleiches System. Liegt ein versioniertes Transkript vor, stellen wir
es voran („NM_004985.5:c.34G>T“) und behalten die Original-Zeichenkette in `text`. Für `p.`-Ausdrücke haben wir
keine Protein-Referenz; dort verwenden wir die ClinVar-Schreibweise mit Transkript und Gensymbol, mit der vom KDK
gelieferten Kurzform (aus „p.G12C“ wird „NM_004985.5(KRAS):p.G12C“). Ohne Transkript (bei
Vorbefunden im Schema optional, in der Praxis oft fehlend) geht die Zeichenkette unverändert hinaus und besteht
die Validierung nicht. Dasselbe gilt für `p.`-Ausdrücke mit Ensembl-Transkript, weil es ohne ENSP-Accession keine
gültige Form gibt. Beispiel in Anhang C.

**Frage 2a.** Ist es in Ihrem Sinn, dass der Sender den `c.`-Ausdruck mit dem Transkript qualifiziert und die
Original-Zeichenkette in `text` erhält?

**Frage 2b.** Welches Muster empfiehlt MII für `p.`-Ausdrücke ohne Protein-Referenzsequenz: (a) die
ClinVar-Schreibweise mit Transkript und Gensymbol, (b) die Komponente weglassen und den Ausdruck nur in `text`
führen, oder (c) beim BfArM eine Protein-Accession im Datenkranz anregen?

**Frage 2c.** Was soll geschehen, wenn auch das Transkript fehlt: unqualifizierte Zeichenkette senden
(Validierungsfehler in Kauf nehmen) oder die Komponente weglassen?

## Frage 3 – System-URIs für Transkripte und Sequence Ontology

**Hintergrund.** `transcriptId` im KDK kann ein Ensembl- (ENST…) oder ein RefSeq-Transkript (NM_…) sein; DNPM
erlaubt beides. Variantentypen und Lokalisationen werden mit der Sequence Ontology (SO) codiert. Für beide
Terminologien nennen die Pakete unterschiedliche System-URIs.

**Im Paket.**

- Transkript: `mii-pr-mtb-einfache-variante`, `component:representative-transcript-ref-seq.value[x]`: 1..1,
  *required* gebunden an `http://ensembl.org`; das Profil definiert die Komponente als „Ensemble Transcript ID
  ('ENST...')“. Diese URL ist in keinem der geprüften Pakete ein ValueSet; Validatoren melden deshalb nur eine
  Warnung. Das
  MTB-Beispiel verwendet RefSeq `NM_133433.4` mit dem System `https://www.ncbi.nlm.nih.gov/refseq/`, die
  MolGen-Beispiele `http://www.ncbi.nlm.nih.gov/refseq`. MolGen `variante` bindet dieselbe Komponente nur
  *example*. Keines der geprüften Pakete definiert eine System-URI für Ensembl (Entwurf MTB-2).
- SO: GR (`dna-change-type-vs`) und die MTB-Beispiele verwenden `http://www.sequenceontology.org`; 14
  MolGen-Beispieldateien und das logische MolGen-Modell `http://sequenceontology.org`. Die MTB- und
  MolGen-Komponenten sind *extensible* an das GR-ValueSet gebunden; Codings mit der zweiten Schreibweise liegen
  außerhalb (Entwurf MOLGEN-2).

**Ihre Anmerkung.** KDK oncology 49, 51, 55; Open Issues 13. MTB binde die Transkript-ID required an
`http://ensembl.org`; RefSeq müsse übersetzt oder im Ballot adressiert werden. `variantTypes` 1:1 übernehmen,
SO bevorzugt.

**Unser Stand.** Transkripte übernehmen wir unverändert, weil eine eindeutige Übersetzung NM_ ↔ ENST für
beliebige Eingaben nicht gesichert ist. System nach Präfix: `http://www.ensembl.org` bzw.
`http://www.ncbi.nlm.nih.gov/refseq`. SO-Codes übernehmen wir 1:1, das System immer in der www-Form.

**Frage 3a.** Soll MTB neben Ensembl-Transkripten (ENST…, laut Definition) auch RefSeq-Transkripte (NM_…) zulassen,
etwa durch eine *example*- oder *extensible*-Bindung wie in MolGen?

**Frage 3b.** Welche System-URIs sollen verwendet werden? Bitte je Zeile bestätigen oder korrigieren:

| Terminologie | Unsere Wahl | Alternativen in den Paketen |
|:--|:--|:--|
| Ensembl-Transkripte | `http://www.ensembl.org` | Bindung: `http://ensembl.org`; DNPM: `https://www.ensembl.org` |
| RefSeq-Transkripte | `http://www.ncbi.nlm.nih.gov/refseq` | MTB-Beispiel: `https://www.ncbi.nlm.nih.gov/refseq/` |
| Sequence Ontology | `http://www.sequenceontology.org` | MolGen-Beispiele: `http://sequenceontology.org` |
| HGNC-Gene | `http://www.genenames.org` (GR `hgnc-vs`, an das MTB und MolGen binden) | Onko-ValueSet 2027, alle neun MTB-Panel-ValueSets und alle MTB-Beispiele 2026/2027: `http://www.genenames.org/geneId` (Entwurf ONKO-3) |

## Frage 4

In Frage 3b aufgegangen.

# C. Onkologie: Diagnose und Staging

## Frage 5 – TNM: UICC-Codierung, Umkehrsuche und TNM-Auflage

**Hintergrund.** `tnmClassifications[]` im KDK sind SNOMED-CT-Codings (je ein Eintrag für T, N und M) mit
`version` = Version des Codesystems (SNOMED-Release, z. B. „2025-03-01“). Ein Feld für die TNM-Auflage hat der
KDK nicht.

**Im Paket.** `mii-pr-onko-tnm-t-kategorie` (ebenso -n-, -m-): `value[x].coding:uicc` 1..1 (required an
`mii-vs-onko-tnm-t-kategorie-werte`), `value[x].coding:snomed-ct` 0..1 (required an `…-werte-sct`);
`Observation.method` 0..1, mustSupport, required an `mii-vs-onko-tnm-version` (TNM-Auflage). In 2026 war
`value[x]` bereits required an das UICC-ValueSet gebunden; neu in 2027 sind die beiden Coding-Slices. Die
Kategorien hängen über `hasMember` an `mii-pr-onko-tnm-klassifikation` (dort `value[x]` = UICC-Stadium 0..1). Die
MII-ConceptMaps `mii-cm-onko-tnm-uicc-sct-clinical/-pathological` laufen nur in Richtung UICC → SNOMED; eine
dokumentierte Rückrichtung gibt es nicht. Für die T-, N- und M-Kategorien fehlen in den Maps Tis(pu), Tis(pd), N1mi und
MX (klinisch) bzw. Tis(pu), Tis(pd), T3e, M0 und MX (pathologisch); die übrigen ungemappten Codes sind Präfixe, Symbole
und L/V/Pn/S, die der KDK nicht liefert (Entwurf ONKO-5).

**Ihre Anmerkung.** KDK oncology 32, 36. TNM nach dem Onko-Modell 2027 abbilden: SNOMED-codierter Typ,
T/N/M-Kategorien über `hasMember`, UICC- und SNOMED-Wert-Slices.

**Unser Stand.** Wir folgen diesem Modell (Gruppierungscode 399537006 klinisch / 399588009 pathologisch, bei
gemischten Präfixen 399390009; kein Stadium, der KDK liefert keines). Die UICC-Codierung leiten wir ab, indem wir
in den veröffentlichten Maps UICC → SNOMED den UICC-Ausgangscode zum gelieferten SNOMED-Code suchen (nur T, N,
M). Ein Eintrag ohne Treffer, zum Beispiel SNOMED „cMX“, geht nach `mii-pr-onko-weitere-klassifikationen` mit
`code.text` „TNM“. `Observation.method` (0..1; mustSupport heißt „senden, wenn vorhanden“) bleibt leer, weil der
KDK keine Auflage liefert. Das SNOMED-Release-Datum
verwerfen wir: Ohne Angabe der Edition lässt sich daraus keine SNOMED-Versions-URI bilden.

**Frage 5a.** Ist die Ableitung der UICC-Codierung aus den Maps UICC → SNOMED (Umkehrsuche) für Sie der
vorgesehene Weg, bis MII eine Map in Richtung SNOMED → UICC ausliefert?

**Frage 5b.** Würden Sie ONKO-5 unterstützen (`coding:uicc` 0..1, wenn `coding:snomed-ct` vorhanden ist),
oder sehen Sie einen besseren Vorschlag?

## Frage 6 – ECOG 5 und „nicht anwendbar“

**Hintergrund.** `ecogPerformanceStatusScore` im KDK erlaubt 0–5, `unknown` und `notApplicable`. Das
MII-CodeSystem kennt 0–4 und U.

**Im Paket.** `mii-pr-onko-allgemeiner-leistungszustand-ecog`: `value[x]` 1..1, `coding:obds` 1..1 (required
an `mii-vs-onko-allgemeiner-leistungszustand-ecog`, Konzepte 0, 1, 2, 3, 4, U), `coding:loinc` 0..\* (required an
`…-ecog-loinc`, Konzepte LA9622-7 bis LA9627-6, also einschließlich „Dead“). Die ConceptMap
`mii-cm-onko-allgemeiner-leistungszustand-ecog-loinc` hat Zeilen für 0–4; U ist ohne Ziel, 5 fehlt. Weil
`coding:obds` Pflicht ist, kann LA9627-6 nie allein verwendet werden (Entwurf ONKO-4).

**Ihre Anmerkung.** KDK oncology 10, 76. Der LOINC-Slice sei 2027 vorhanden, das CS kenne weiterhin nur 0–4
und U; 5 und `notApplicable` seien ein Ballot-Kandidat.

**Unser Stand.** 0–4 gehen nach `coding:obds` plus `coding:loinc`; `unknown` nach obds U (`dataAbsentReason`
ist neben dem Pflichtwert ungültig). 5 und `notApplicable` erzeugen keine Observation und werden im Bericht als
verworfen gemeldet.

**Frage 6.** Welche Lösung bevorzugen Sie für ONKO-4?
(a) Codes `5` und „nicht anwendbar“ ins CodeSystem aufnehmen und die ConceptMap um 5 → LA9627-6 ergänzen.
(b) `coding:obds` auf 0..1 lockern (Invariante: obds oder loinc), sodass ECOG 5 als reines LOINC-Coding geht,
und für „nicht anwendbar“ `value[x]` auf 0..1 mit `dataAbsentReason` lockern.

**Frage 6c.** Wie soll eine ECOG-Angabe aus dem Follow-up mit dem Verlauf verknüpft werden? In 2027 lässt
`mii-pr-onko-verlauf.hasMember` das ECOG-Profil nicht mehr zu (Ziele: Tod, TNM, Lymphknoten, Histologie,
Fernmetastasen, Residualstatus, genetische Variante); derzeit verbindet nur das Datum beide.

## Frage 7 – Metachrone Tumoren

**Hintergrund.** `metachroneDiagnoses` im Follow-up ist ein Ja/Nein-Feld; die Tumoren selbst stehen in
`additionalDiagnoses[]`. Für das Ja/Nein-Feld gibt es kein Element.

**Im Paket.** `mii-pr-onko-diagnose-primaertumor` hat 2027 drei Verknüpfungs-Extensions, alle 0..\*:
`occurredFollowing` („Frühere Tumorerkrankungen (zeitliche Abfolge)“, Ziel u. a. `diagnose-primaertumor`),
`dueTo` („Verursacht durch (therapieassoziierte Sekundärmalignome)“) und `transformationVon`. Die Kategorie
`category:onkologie` (SNOMED 55342001) ist 1..1 (Entwurf ONKO-7).

**Ihre Anmerkung.** KDK oncology 79; Open Issues 22. Als weitere Condition nach `diagnose-primaertumor`
abbilden, mit der Pflicht-Kategorie 55342001 und `dueTo` für den Zusammenhang zur Erstdiagnose.

**Unser Stand.** Jede weitere Diagnose wird eine `diagnose-primaertumor` mit Kategorie 55342001, verknüpft über
`occurredFollowing` (nicht `dueTo`, weil das Profil `dueTo` auf therapieassoziierte Verursachung festlegt). Das
Ja/Nein-Feld behandeln wir so:

| Quelle | Ausgabe |
|:--|:--|
| `true`, Diagnosen vorhanden | nur die verknüpften Conditions; das Feld gilt als abgeleitet |
| `true`, keine Diagnose | eigene Extension „metachroner Tumor = true“ am Verlauf |
| `false` | eigene Extension „= false“ am Verlauf |
| Profilset 2026 (kein `occurredFollowing` auf Primärtumor) | immer die Extension |

**Frage 7a.** Stimmen Sie zu, dass ein metachroner Tumor über `occurredFollowing` und nicht über `dueTo` mit
der Erstdiagnose verknüpft wird?

**Frage 7b.** Soll das Ja/Nein-Feld ein eigenes Element im Onko-Modul erhalten (ONKO-7), damit auch `false` und
`true` ohne Diagnose standardisiert darstellbar sind, oder genügt die dokumentierte Ableitungsregel?

## Frage 8

In Frage 5 aufgegangen; die frühere Frage 5c ist jetzt eine Feststellung in Frage 5 („Unser Stand“).

## Frage 9 – Weitere Klassifikationen und Tumorausbreitung

**Hintergrund.** `additionalClassification[]` im KDK ist ein freies Paar aus `system` und `key` ohne Datum, zum
Beispiel System „TNM“ mit einem UICC-String, oder das DNPM-System zur Tumorausbreitung
(`dnpm-dip/mtb/diagnosis/kds-tumor-spread`) mit Werten wie `metastasized`.

**Im Paket.** `mii-pr-onko-weitere-klassifikationen`: `code.coding.code` *preferred* an
`mii-vs-onko-weitere-klassifikationen`, `valueCodeableConcept.coding` *preferred* an
`…-auspraegungen`. Daneben `mii-pr-mtb-tumorausbreitung` (SNOMED-codiert, `effective[x]` Pflicht, verknüpft
über `Condition.stage` des Primärtumors).

**Ihre Anmerkung.** KDK oncology 2, 3; Open Issues 2, 3. `weitere-klassifikationen` mit den
preferred-Bindungen verwenden, Status MAPPED.

**Unser Stand.** Je Eintrag eine `weitere-klassifikationen`-Observation mit `code.text` = System und
`value.text` = Wert, ohne Codings, weil die Systeme unserer Daten im ValueSet keinen Code haben. Einträge mit
dem DNPM-System zur Tumorausbreitung und bekanntem Wert werden stattdessen `mii-pr-mtb-tumorausbreitung` mit
SNOMED-Wert, datiert mit der Erstdiagnose, weil das DNPM-Modell die Angabe „zum Diagnosezeitpunkt“ definiert.

**Frage 9a.** Stimmen Sie zu, dass DNPM-Angaben zur Tumorausbreitung nach `mii-pr-mtb-tumorausbreitung` gehen
und nicht nach `weitere-klassifikationen`?

**Frage 9b.** Ist reiner Text für alle übrigen Systeme akzeptabel, oder sollen wir bekannte Systeme (FIGO, Ann
Arbor, Binet, …) aus den beiden ValueSets codieren, wenn der KDK-String eindeutig ist?

# D. MTB: Therapieplan und Follow-up

## Frage 10 – Therapieansprechen: Methode ist Pflicht, Datenquelle hat kein Element

**Hintergrund.** Das Follow-up liefert `therapyResponse` (CR, PR, SD, PD) und `therapyResponseSource`. Letzteres
nennt die Quelle der Angabe (Arztbrief, Entlassungsbericht, Tumordokumentation), nicht die Beurteilungsmethode.

**Im Paket.** `mii-pr-mtb-response-befund`: `Observation.method` 1..1, required an
`mii-vs-mtb-response-befund-beurteilungsmethode` (nur RECIST, RANO). `value[x]` ist *extensible* an
`mii-vs-onko-verlauf-gesamtbeurteilung` gebunden, mit den Slices `coding:oBDS` und `coding:MTB` (beide 0..\*, je
required an das eigene ValueSet). Für die Datenquelle gibt es kein Element (Entwurf MTB-12).

**Ihre Anmerkung.** KDK oncology 100; Open Issues 26. Ziel `response-befund.method` (RECIST, RANO), Wert
gebunden an `mii-vs-onko-verlauf-gesamtbeurteilung`, Enum-Abgleich nötig.

**Unser Stand.** Das Ziel `method` stammte aus unserem früheren Entwurf und war falsch. Der Datenkranz liefert
keine Methode, also validiert keine Response gegen `response-befund`. Wir verwenden ein eigenes Profil auf
Observation (ohne diese Slices), mit dem Wert als Code aus dem MTB-ValueSet und der Quelle in `note`. Dass
`therapyResponseSource` die Datenquelle ist, sagen das KDK-Schema („Source of therapy response data“) und Ihr
logisches Modell (`DatenquelleTherapieansprechen`). Sobald wir `response-befund` verwenden können, setzen wir neben
`coding:MTB` auch `coding:oBDS` (V/T/K/P), weil die extensible-Bindung des Werts das verlangt.

**Frage 10.** Welche Änderung soll MTB-12 vorschlagen: `method` 0..1, oder zusätzliche Codes `other`/`unknown`?
Und wo soll die Datenquelle hin: eigene Extension, `note`, oder `derivedFrom` → DocumentReference?

## Frage 11 – Durchgeführte Therapie → Empfehlung

**Hintergrund.** `therapies[].reference` im Follow-up verweist auf die Empfehlung des Boards, aus der die
Therapie hervorging; das kann auch eine Kombinations- oder eine Studienempfehlung sein.

**Im Paket.** `mii-pr-mtb-systemische-therapie`: `Procedure.extension:causedBy` 0..1, mustSupport, Ziel
`mii-pr-mtb-therapieempfehlung` (MedicationRequest; so schon in 2026.0.1). Die Basis-Extension
`procedure-causedBy` erlaubt weder RequestGroup (Kombination) noch ServiceRequest (Studie).
`Procedure.basedOn:tumorkonferenz` → Therapieplan. `mii-pr-mtb-systemtherapie-medication-statement.basedOn:therapieempfehlung`
0..1 → `therapieempfehlung-medikation`. Das Beispiel `Systemtherapie-Beispiel-1` (2027) setzt `causedBy` plus
`basedOn` (Entwurf MTB-11).

**Ihre Anmerkung.** KDK oncology 90; Open Issues 25. Lücke: `basedOn` ziele nur auf den CarePlan; eine direkte
Referenz auf die Empfehlung sei ein Ballot-Kandidat.

**Unser Stand.** `causedBy` auf die Empfehlung; bei einer Kombination auf deren erstes Mitglied, weil die
RequestGroup kein zulässiges Ziel ist. 2027 zusätzlich `MedicationStatement.basedOn:therapieempfehlung`. Eine
Therapie aus einer Studienempfehlung geht nach `Procedure.note`.

**Frage 11a.** Bestätigen Sie für Kombinationen das Muster „`causedBy` auf eine Mitgliedsempfehlung plus
`basedOn:tumorkonferenz` auf den Therapieplan“? Falls ja, beschränken wir MTB-11 auf Studienempfehlungen.

**Frage 11b.** Sollen wir `basedOn:tumorkonferenz` grundsätzlich setzen, wie im Beispiel 2027?

## Frage 12 – Evidenzgraduierung an Studienempfehlungen

**Hintergrund.** Studienempfehlungen (`recommendedStudies[]`) tragen `evidenceLevel` und
`evidenceLevelDetails[]` genauso wie Therapieempfehlungen.

**Im Paket.** `mii-ex-mtb-empfehlung-evidenzgraduierung` ist nur für RequestGroup, MedicationRequest und
Observation zugelassen. Studienempfehlungen sind `mii-pr-mtb-studieneinschluss-anfrage` (ServiceRequest) und
haben keinen Slice dafür. Das CodeSystem `mii-cs-mtb-empfehlung-evidenzgrad-zusatzverweis` enthält is, iv, Z, R;
„Z(FDA)“ wird im Definitionstext von Z erwähnt, hat aber keinen eigenen Code (Entwurf MTB-13).

**Ihre Anmerkung.** KDK oncology 206, 207; Open Issues 49, 50. Die Extension sei an
`mii-pr-mtb-therapieempfehlung` bestätigt, Status MAPPED. (Das ResearchStudy-Ziel in diesen Zeilen war unser
früherer Fehler.)

**Unser Stand.** Wir tragen Evidenzgrad und Zusatzverweis in einer eigenen ServiceRequest-Extension mit
denselben MII-CodeSystemen (Beispiel in Anhang C). `Z(FDA)` senden wir als Z; der Zusatz FDA geht nur als Text
mit, auch an Therapieempfehlungen. Die stützenden Varianten einer Studienempfehlung stehen in
`ServiceRequest.supportingInfo`, weil `studieneinschluss-anfrage` keinen Slice wie
`reasonReference:StuetzendeMolekulareAlteration` der Therapieempfehlung hat.

**Frage 12a.** Würden Sie MTB-13 unterstützen: ServiceRequest in den Kontext der Extension aufnehmen und sie an
`studieneinschluss-anfrage` slicen?

**Frage 12b.** Soll `Z(FDA)` einen eigenen Zusatzverweis-Code erhalten?

**Frage 12c.** Soll `studieneinschluss-anfrage` einen `reasonReference`-Slice für stützende Varianten erhalten
(wie die Therapieempfehlung), oder ist `supportingInfo` die vorgesehene Darstellung?

## Frage 13 – Therapieart an der Empfehlung

**Hintergrund.** `therapeuticStrategy` (CH, HO, IM, ZS, CI, CZ, CIZ, IZ, SZ, SO) ist die oBDS-Therapieart der
empfohlenen Therapie. An der Empfehlung gibt es dafür kein profiliertes Element.

**Im Paket.** `MedicationRequest.category` ist in `mii-pr-onko-therapieempfehlung-medikation` und
`mii-pr-mtb-therapieempfehlung` 0..\* mit *example*-Bindung. `mii-pr-onko-therapieempfehlung-kombinationstherapie`
(und das davon abgeleitete `mii-pr-mtb-therapieempfehlung-kombination`):
`RequestGroup.code` *preferred* an `mii-vs-onko-therapieempfehlung-typ` (gesamtes CS `mii-cs-onko-therapie-typ`,
16 Codes). `mii-vs-onko-systemische-therapie-art` enthält 13 Codes: dieselben ohne OP, ST, KW. Alle KDK-Werte
sind in beiden ValueSets enthalten (Entwurf ONKO-6).

**Ihre Anmerkung.** KDK oncology 228; Open Issues 55. MTB solle `category` oder eine Extension an
`mii-vs-onko-systemische-therapie-art` binden.

**Unser Stand.** Übergangsweise geht der Code in das example-gebundene `category`, bei Kombinationen zusätzlich in
`RequestGroup.code`.

**Frage 13a.** ONKO-6 schlägt einen Slice `MedicationRequest.category:therapieart` (0..1, *required*) im
Onko-Basisprofil `therapieempfehlung-medikation` vor, den MTB erbt. Ist der Ort richtig?

**Frage 13b.** Soll er an `mii-vs-onko-systemische-therapie-art` (Ihr Vorschlag) oder an
`mii-vs-onko-therapieempfehlung-typ` binden (konsistent zu `RequestGroup.code`)? Der Unterschied ist nur, ob OP,
ST und KW im ValueSet enthalten sind.

## Frage 14 – Empfehlungstyp (in-label, off-label, compassionate use, …)

**Hintergrund.** `recommendedSystemicTherapies[].type` hat die Werte inLabel, offLabel, compassionateUse,
secPreventive, unknown. Sie mischen Zulassungsstatus, Zweck und fehlende Information.

**Im Paket.** `mii-cs-mtb-zulassungsstatus` enthält in-label, off-label, leitlinie. Gebunden ist es nur in
`mii-ex-mtb-leitlinie-dokumentation`. Diese Extension hat den Kontext `Element`, dürfte also auch an einer
Therapieempfehlung stehen; als Slice geführt wird sie nur in `systemische-vortherapie` und
`behandlungsepisode`. Das logische Modell `mii-lm-mvgenomseq-onkologie` führt die fünf Werte als
`EmpfehlungTyp`, ohne Mapping (Entwurf MTB-14).

**Ihre Anmerkung.** KDK oncology 229; Open Issues 56. Ballot-Kandidat MTB, weil compassionateUse, secPreventive
und unknown im CS fehlen.

**Unser Stand.** Wir setzen an jedem MedicationRequest (und an der RequestGroup einer Kombination) eine eigene
Extension mit inLabel / offLabel / compassionateUse / secPreventive; `unknown` lassen wir weg.

**Frage 14a.** Welchen Weg soll MTB-14 vorschlagen: (A) die fehlenden Codes in `mii-cs-mtb-zulassungsstatus`
ergänzen und `leitlinie-dokumentation` an der Therapieempfehlung slicen, oder (B) eine eigene Extension
„Empfehlungstyp“ wie `EmpfehlungTyp` im logischen Modell? Sollen wir bis dahin für in-label und off-label
`leitlinie-dokumentation` an der Empfehlung verwenden, was Kontext und offenes Slicing schon heute zulassen?

**Frage 14b.** MTB-14 schlägt „unknown“ als Code vor. Halten Sie das für sinnvoll, oder soll ein unbekannter Typ
einfach fehlen?

# E. MolGen: Varianteninterpretation bei Seltenen Erkrankungen

## Frage 15 – ACMG-Kriterien

**Hintergrund.** Jede klassifizierte Variante im KDK Seltene Erkrankungen trägt `acmgCriteria[]` mit
Kriterium (PVS1 … BP7) und Stärke (`modifier`: pvs, ps, pm, pp, ba, bs, bp und die DNPM-Stufe „bm“, benign
moderate).

**Im Paket.** Kein MII-Modul und kein GR-Artefakt hat einen Slice für ACMG-Kriterien.
`mii-pr-molgen-diagnostische-implikation` hat `component:clinical-significance` (53037-8) und
`component:evidence-level` (93044-6, andere Bedeutung); das Komponenten-Slicing ist offen, ungeslicte
Komponenten sind also zulässig (Entwurf MOLGEN-6).

**Ihre Anmerkung.** KDK rare diseases 62, 63, 81, 82, 101, 102. Nur die allgemeine Korrektur, dass MolGen ein
einziges Profil `variante` hat; die Zeilen behalten unser altes Ziel „Observation (acmg-criterion)“ als MAPPED.

**Unser Stand.** Dieses alte Ziel existiert nicht. Wir legen die Kriterien als ungeslicte Komponenten neben
`clinical-significance` an `diagnostische-implikation` ab: `code` = Kriterium, Wert = Stärke aus einem eigenen
CodeSystem. Die Zeilen stehen auf DRAFT. Für die Kriterien verwenden wir derzeit die selbst gewählte URI
`https://clinicalgenome.org/codesystem/acmg-criteria`. Sie liegt im Namensraum von ClinGen, stammt aber nicht von
dort: ClinGen veröffentlicht die Kriterien in der SEPIO-CG-Terminologie, ohne FHIR-System-URI. Wir verlegen die URI in
unseren eigenen Namensraum, wenn MII kein CodeSystem benennt. Beispiel in Anhang C.

**Frage 15a.** Ist diese Komponente als Interimslösung akzeptabel, bis MolGen einen Slice definiert?

**Frage 15b.** Gehört ein ACMG-Kriterien-Slice in HDB-976 oder in einen eigenen Kommentar (MOLGEN-6)?

**Frage 15c.** Welches CodeSystem empfehlen Sie für die Kriterien: eine ClinGen-URI (welche?) oder ein
MII-eigenes?

## Frage 16 – Segregation: `notPerformed` und `fromMotherAndFather`

**Hintergrund.** `segregationAnalysis` hat die Werte deNovo, fromFather, fromMother, fromMotherAndFather,
notPerformed. Die Quelle (DNPM `segregation-analysis`) nennt den vierten Wert `from-both-parents`: je ein Allel
von jedem Elternteil.

**Im Paket.** `mii-pr-molgen-variante`, `component:variant-inheritance`: `value[x]` 1..1, *extensible* an LOINC
LL5489-1. LL5489-1 ist in keinem geprüften Paket enthalten. Eine Komponente nur mit `dataAbsentReason` verletzt
`value[x]` 1..1 (Entwurf MOLGEN-5).

**Ihre Anmerkung.** KDK rare diseases 76, 97, 114; Open Issues 67, 71, 75. `variant-inheritance` mit den
LA-Codes, eigener Code „biparental“ (HDB-976 c), `notPerformed` → `dataAbsentReason` not-performed.

**Unser Stand.** deNovo, fromFather, fromMother und biparental (eigener Code bis HDB-976 c) wie von Ihnen
vorgeschlagen. Bei `notPerformed` lassen wir die Komponente weg und melden den Wert im Bericht als verworfen.

**Frage 16a.** Wie soll `notPerformed` dargestellt werden: (a) Komponente weglassen, (b) ein Code „nicht
durchgeführt“, zum Beispiel zusammen mit HDB-976 c, oder (c) `value[x]` auf 0..1 lockern (geerbt aus GR, also über
HL7 Clinical Genomics)? Einen Platzhalterwert wie „Unknown“ plus `dataAbsentReason` halten wir für widersprüchlich.

**Frage 16b.** Deckt Ihr Code „biparental“ in HDB-976 c genau die Bedeutung „je ein Allel von jedem
Elternteil“ ab?

## Frage 17 – Erbgang `unclear`

**Hintergrund.** `modeOfInheritance` hat neben den Erbgängen den Wert `unclear`.

**Im Paket.** `mii-pr-molgen-diagnostische-implikation` und `mii-pr-mtb-diagnostische-implikation`:
`component:mode-of-inheritance.value[x]` 1..1, *preferred* an GR `condition-inheritance-mode-vs` (HPO). Das
gebundene ValueSet hat keinen passenden Code für „unklar“. Die LOINC-Antwortliste LL3731-8 und der Code
79742-3 kommen in keinem geprüften Paket vor (Entwurf MOLGEN-5).

**Ihre Anmerkung.** KDK rare diseases 73, 93, 111. Ziel `mode-of-inheritance` mit HPO; die LOINC-LA-Codes gälten
nur für das MTB-Gegenstück.

**Unser Stand.** Ziel und HPO-Codes übernommen. Für `unclear` senden wir nur `valueCodeableConcept.text`, weil eine
Komponente nur mit `dataAbsentReason` `value[x]` 1..1 verletzt. MTB und MolGen binden dieselbe HPO-Liste
(preferred); die LOINC-LA-Codes aus Ihrer Anmerkung kommen in keinem MII- oder GR-Paket vor, wir verwenden sie
nicht.

**Frage 17.** Die preferred-Bindung erlaubt den Textwert. Soll MolGen für „unklar“ trotzdem einen gemeinsamen Code
festlegen, damit Empfänger den Fall maschinell erkennen?

## Frage 18 – Befundkategorie (HDB-976)

**Hintergrund.** `diagnosticSignificance` im KDK hat die Werte primary, incidental, candidate; das Schema
beschreibt das Feld nur als „Significance for case“.

**Im Paket.** Kein Element in MolGen 2027; Ihr Ticket HDB-976 schlägt eine Komponente „Befundkategorie“ vor.
Die ACMG unterscheidet aktiv gesuchte Sekundärbefunde (secondary findings) von unerwarteten Zufallsbefunden
(incidental findings). `diagnostische-implikation` slict bereits `extension:secondary-finding` (HL7
`observation-secondaryFinding`); deren Wert ist 1..1 und benennt die zugrunde liegende Empfehlungsliste (extensible).
Unser Entwurf MOLGEN-4 übernimmt Ihre Codes primary-finding / secondary-finding / candidate.

**Ihre Anmerkung.** KDK rare diseases 66, 86, 105; Open Issues 64, 68, 72. Komponente an
`diagnostische-implikation` mit übergangsweise eigenem Code bis HDB-976 {primary-finding, secondary-finding,
candidate}; `Observation.note` nur als Notlösung.

**Unser Stand.** Umgesetzt wie von Ihnen geplant, mit eigenen Codes primary / incidental / candidate (die
KDK-Werte), ohne `note` und ohne die HL7-Extension.

**Frage 18a.** Was `incidental` im Datenkranz meint, klären wir mit BfArM und DNPM. Falls es Zufallsbefunde meint:
Soll HDB-976 dafür einen eigenen Code `incidental-finding` neben `secondary-finding` erhalten?

**Frage 18b.** Falls `incidental` Sekundärbefunde meint: Gibt es einen akzeptablen Wert für
`extension:secondary-finding`, wenn der KDK die Version der ACMG-SF-Liste nicht nennt? Ohne Wert lassen wir die
Extension weg.

# F. MTB: Vorbefunde

## Frage 19 – Freitext-Vorbefunde

**Hintergrund.** `priorDiagnostics[].complexVariants[]` ist eine Liste von Freitext-Zeilen ohne Typ
(Beispiele aus den Testdaten: „EGFR amplification“, „EML4-ALK fusion“). Sie lassen sich nicht sicher auf CNV,
DNA-Fusion oder RNA-Fusion verteilen, und Fusionen bräuchten strukturierte Partner-Angaben.

**Im Paket.** `mii-pr-mtb-ngs-bericht`: `DiagnosticReport.conclusion` 0..1, nicht mustSupport; die
`result`-Slices sind typisiert. `component:conclusion-string` (valueString, 0..1 MS) gibt es an jeder
Varianten-Observation, setzt aber eine Variante voraus. `behandlungsepisode.supportingInfo:Vorbefund` erlaubt
DiagnosticReport oder Observation. Das 2027 neue logische DNPM-Modell im MTB-Paket (`dnpm-lm-patient-record`) mappt
`priorDiagnosticReports` auf „Pathologie: DiagnosticReport (MolecularPathology)“. Das Profil
`mii-pr-mtb-molecular-pathology-report` gibt es schon in 2026.0.1; es ist ein pathologischer Befund (LOINC 60568-3)
mit `result`-Slices nur für Immunhistochemie und In-situ-Hybridisierung, also kein Container für NGS-Befunde
(Entwurf MTB-10).

**Ihre Anmerkung.** KDK oncology 41; Open Issues 5. Container `ngs-bericht` über
`supportingInfo:Vorbefund`, `complexVariants` je nach Typ in die typisierten `result`-Slices, vorbehaltlich einer
Prüfung der KDK-Feldstruktur.

**Unser Stand.** Wir verwenden Ihren Container. Die Prüfung ergab ein einfaches `string[]` ohne Typ; jeder
Eintrag wird eine Zeile in `ngs-bericht.conclusion`.

**Frage 19a.** Bestätigen Sie `ngs-bericht` als Container für NGS-Vorbefunde? Meint das DNPM-Mapping „Pathologie:“
das Modul Patho?

**Frage 19b.** Welchen Träger für die Freitext-Zeilen bevorzugen Sie: (a) `conclusion` (dann bitte mustSupport),
(b) je Eintrag eine Varianten-Observation nur mit `conclusion-string` (beides in MTB-10), oder (c) einen neuen
Freitext-Slice in `result`?

## Frage 20 – Untersuchungsart der Vorbefunde

**Hintergrund.** `priorDiagnostics[].type` hat die Werte exome, genome (kurz/lang), panel, single, array,
karyotyping, other, none. `single` ist ein Einzelgen-Test; die Methode (Sanger, gezielte Variantenanalyse, …)
nennt der KDK nicht.

**Im Paket.** `mii-pr-mtb-genomic-study-analysis`, `extension:method-type.value[x]`: required an
`mii-vs-mtb-genomic-analysis-method-type`. Das ValueSet umfasst das MII-CodeSystem (6 Codes) und das gesamte
GR-CodeSystem `genomic-study-method-type-cs` (81 Codes), darunter karyotyping, microarray, other und
targeted-variant-analysis. Es fehlen ein Code für Einzelgen-Tests und die Unterscheidung Kurz-/Langread
(Entwurf MTB-10).

**Ihre Anmerkung.** KDK oncology 57; Open Issues 21. Typ nach `method-type` (exome, genome, panel); für single,
array, karyotyping, other und none gebe es kein Konzept.

**Unser Stand.** Ihre drei Zuordnungen übernommen; array / karyotyping / other erhalten die GR-Codes
microarray / karyotyping / other. `single` hat keinen Code. Bei `none` erzeugen wir keine Studie und keinen
Bericht, außer der Eintrag enthält trotzdem Befunde. Der exakte KDK-Wert bleibt als eigener Code in
`mii-pr-mtb-genomic-study.Procedure.code` (0..1, example-Bindung) erhalten; an `genomic-study-analysis` ist
`Procedure.code` 0..0.

**Frage 20a.** Stimmen Sie zu, dass MTB-10 sich bei der Untersuchungsart auf Einzelgen-Tests und Kurz-/Langread
beschränkt?

**Frage 20b.** Wie soll `single` vorerst codiert werden: GR `sequence-analysis-of-the-entire-coding-region` (der
GTR-Begriff für Einzelgen-Tests), GR `targeted-variant-analysis`, `other`, oder nur der eigene Code an der
genomic study?

# G. GRZ: Sequenzier-QC

## Frage 21 – Mindestabdeckung

**Hintergrund.** Das GRZ liefert je Datensatz `meanDepthOfCoverage`, `minCoverage` (Schwellenwert der
Lesetiefe, z. B. 20×) und `targetedRegionsAboveMinCoverage` (Anteil der Zielregionen mit mindestens dieser
Lesetiefe).

**Im Paket.** `mii-ex-mtb-genomic-study-analysis-qc` hat die Sub-Extensions read-depth, read-length,
sequencing-coverage, metrics-description, sequencing-read-type, gap-statistics, alle ohne Definitionstext. Die
Namen stammen aus GR `genomic-study-analysis-metrics`; dort ist `read-depth` „the average read depth“ und
`sequencing-coverage` „the percentage of the studied regions that were sequenced“. Für einen Schwellenwert gibt
es keinen Platz (Entwürfe MTB-3, MTB-19). `mii-pr-mtb-genomic-study-analysis` slict außerdem die GR-Extension
`metrics` selbst (Kontext Procedure, also gültig) mit read-depth, sequencing-coverage und metrics-description.

**Ihre Anmerkung.** GRZ 30; Open Issues 77. `minCoverage` → `qc.sequencing-coverage`.

**Unser Stand.** `read-depth` = `meanDepthOfCoverage`. `sequencing-coverage` = `targetedRegionsAboveMinCoverage`
(× 100, Prozent); so steht es in unserer Tabelle (GRZ 35, ohne Anmerkung von Ihnen). `minCoverage` geht als Text
(„minCoverage=20x“) in `metrics-description`.

**Frage 21a.** Sieht MII „Anteil der Zielregionen mit mindestens `minCoverage`“ (Definition des BfArM) als
GR-`sequencing-coverage` („percentage of the studied regions that were sequenced“) an, oder als eigene Kennzahl?

**Frage 21b.** Stimmen Sie zu, dass der Schwellenwert `minCoverage` eine eigene Sub-Extension braucht (MTB-19)?

## Frage 22 – Read-Typ und Kontext der QC-Extension

**Hintergrund.** `sequencingLayout` im GRZ (single-end, paired-end, reverse, other) beschreibt den Read-Typ.

**Im Paket.** `qc.sequencing-read-type.value[x]` hat keine Bindung. Die Extension deklariert als Kontext
`Extension` statt `Procedure`, in 2026.0.1 wie im Ballot 2027; strenge Validatoren lehnen sie an der Procedure
ab. GR `metrics` hat keinen Platz für den Read-Typ (Entwurf MTB-3).

**Ihre Anmerkung.** GRZ 40; Open Issues 81. `sequencingLayout` → `qc.sequencing-read-type`; für MolGen analog
in der GR-Extension `metrics`.

**Unser Stand.** An der MTB-Procedure ein eigenes Coding (single-end / paired-end / reverse; `other` melden wir
als verworfen) in `qc`, zusammen mit read-depth, sequencing-coverage und metrics-description. Den
Validierungsfehler wegen des Kontexts weisen wir als bekannten Paketdefekt aus. An einer Procedure nach
`mii-pr-molgen-genomic-study-analysis` geht das Layout nur als Text in `metrics-description`.

**Frage 22a.** Welches CodeSystem und welche System-URI soll MTB an `sequencing-read-type` binden?

**Frage 22b.** Unterstützen Sie MTB-3 (Kontext der QC-Extension auf `Procedure` korrigieren)?

**Frage 22c.** Darf die MTB-QC-Extension auch an `mii-pr-molgen-genomic-study-analysis` verwendet werden?

**Frage 22d.** Sollen read-depth, sequencing-coverage und metrics-description an der MTB-Procedure in GR `metrics`
stehen (heute gültig) und nur der Read-Typ in `qc`? Dann würden wir unsere Umsetzung entsprechend umstellen.

# H. MTB: weitere molekulare Befunde

## Frage 23 – Expressionsniveau und Referenzkohorte

**Hintergrund.** `expressionVariants[].expressionType` hat die Werte noExpression, normalExpression,
highExpression, lowExpression; `.reference` ist Freitext („reference cohort of 400 patients“).

**Im Paket.** `mii-pr-mtb-rna-seq`: `value[x]:valueCodeableConcept` 0..1, required an LOINC LL1971-2
(Present/Absent; die geerbte Definition meint das Vorliegen der in den Komponenten beschriebenen Variante);
`Observation.interpretation` 0..\*, *extensible* an das Basis-ValueSet, nicht mustSupport (Entwurf MTB-15).

**Ihre Anmerkung.** KDK oncology 144; Open Issues 30. `rna-seq` habe keinen Platz für die vier Stufen;
Ballot-Kandidat.

**Unser Stand.** noExpression → Absent (LA9634-2); normal / high / low → Present (LA9633-4) mit `interpretation`
N / H / L. Die Referenzkohorte geht nach `note`. Das erhält alle Angaben und validiert, Empfänger dürfen
`interpretation` aber ignorieren.

**Frage 23a.** Ist Present/Absent plus `interpretation` als Codierung des Expressionsniveaus akzeptabel, obwohl
der Wert ursprünglich das Vorliegen einer Variante meint?

**Frage 23b.** Soll MTB-15 eine gebundene Komponente „Expressionsniveau“ plus eine String-Komponente
„Referenzkohorte“ vorschlagen, oder `interpretation` binden und als mustSupport kennzeichnen?

## Frage 24 – LOH an der Einzelvariante

**Hintergrund.** `smallVariants[].loh` ist ein Ja/Nein-Feld an der Variante.

**Im Paket.** `mii-pr-mtb-einfache-variante`: Komponenten-Slicing offen, kein LOH-Slice. LOH kommt in MTB zweimal
vor: an `mii-pr-mtb-copy-number-variant.component:copy-number-neutral-loh` (Wert ungebunden) und als genomweiter
Score an `mii-pr-mtb-hrd-score.component:LOH` (Code NCIt C18016 „Loss of Heterozygosity“) (Entwurf MTB-16).

**Ihre Anmerkung.** KDK oncology 165; Open Issues 35. Ballot: Konzept „loh“ plus Komponente an
`einfache-variante`; übergangsweise eine separate Biomarker-Observation mit `derivedFrom`.

**Unser Stand.** Eine ungeslicte Komponente mit eigenem Code `loh` (CodeSystem `mvgs-cs-molecular-feature`
unseres Pakets) und `valueBoolean` an der Variante. Das ist heute valide und entspricht der Form Ihres
Ballot-Ziels.

**Frage 24a.** Ist die Komponente an der Variante statt der separaten Biomarker-Observation akzeptabel?

**Frage 24b.** Soll die Ballot-Komponente (MTB-16) den Code NCIt C18016 wie an `hrd-score` tragen oder einen
neuen MII-Code, jeweils mit `valueBoolean`?

## Frage 25 – Mutationssignaturen (COSMIC SBS)

**Hintergrund.** `sbsSignatures[]` nennt je Eintrag eine oder mehrere COSMIC-Signaturen (`name[]`, z. B.
„SBS 6“, „SBS 13“) und die Katalogversion.

**Im Paket.** `mii-cs-mtb-molekulare-biomarker` hat kein Signatur-Konzept; `mii-pr-mtb-molekularer-biomarker.code`
ist *extensible* gebunden. Das MTB-Beispiel `RNA-Fusion-1` verwendet die System-URI
`https://cancer.sanger.ac.uk/cosmic` für eine Fusion (COSF1171), es gibt dafür aber kein NamingSystem (Entwurf
MTB-17).

**Ihre Anmerkung.** KDK oncology 152; Open Issues 32. NamingSystem für den COSMIC-Katalog, ValueSet ohne
aufgezählten Inhalt, Katalogversion in `Coding.version`, „SBS 6“ → „SBS6“, kein CodeSystem-Spiegel.

**Unser Stand.** Umgesetzt mit eigenem Interims-NamingSystem und eigenem `Observation.code`, eine Observation je
Signaturname (ein Eintrag mit „SBS 6“ und „SBS 13“ ergibt zwei), weil mehrere Codings in einem CodeableConcept
dasselbe Konzept bezeichnen müssten. Ein ValueSet, das das COSMIC-System ohne Aufzählung einschließt, haben wir nicht
angelegt.

**Frage 25.** Soll MII das COSMIC-NamingSystem, ein ValueSet (COSMIC-System ohne Aufzählung) und ein
Biomarker-Konzept „Mutationssignatur“ veröffentlichen, oder soll das im MV-GenomSeq-IG bleiben?

# I. Nicht als Frage gestellt

Diese Punkte aus Ihrer Tabelle haben wir nicht in Fragen umgesetzt, weil sie nach unserer Prüfung nur einen
Ballot-Kommentar brauchen oder schon gelöst sind. Falls Sie das anders sehen, bitte anmerken.

| Zeilen | Feld | Stand |
|:--|:--|:--|
| KDK oncology 9; Open Issues 4 | `diagnosticAssessment` (erblicher Tumorfall) | kein Element in Onko/MTB → Entwurf ONKO-8 |
| KDK oncology 87–88; Open Issues 23–24 | präventive Maßnahme: Ergebnis, Verweis | kein Element → ONKO-8; übergangsweise ServiceRequest (Maßnahme) und Ergebnis-Observation mit `basedOn` → ServiceRequest |
| KDK oncology 197–198; Open Issues 47–48 | therapeutisch / risikoreduzierend | kein Element → ONKO-8 |
| KDK rare diseases 20; Open Issues 59 | Studiendesign single/duo/trio (auch GRZ `genomicStudySubtype`) | kein Konzept → MOLGEN-7; übergangsweise eigene Extension |
| KDK rare diseases 6, 22–23, 29; Open Issues 58, 60–62 | GMFCS, Hospitalisierung | durch HDB-975 abgedeckt → SE-1, SE-2; übergangsweise eigene Darstellung |
| KDK rare diseases 129 | Therapiestrategie `other` | → SE-3 und Frage 34 |
| KDK oncology 134 | CNV-Typ (sechs Stufen) | → MTB-7; übergangsweise eigenes CodeSystem neben dem bwHC-Code |
| KDK oncology 194; Open Issues 46 | sonstige Empfehlungen | abbildbar: `CarePlan.activity:obds.detail.code` (WW, AS, WS, OP, ST, KW, SO) |
| KDK oncology 150; Open Issues 31 | Referenzkohorte der Expression | jetzt Teil von Frage 23 |
| mehrere | Elemente, die Sie als „2027“ markiert haben | die Träger gab es schon 2026; neu in 2027 sind einzelne Bindungen, Kardinalitäten und Typisierungen, darunter das Interpretations-ValueSet und das geschlossene value[x]-Slicing (→ MOLGEN-1) |

# J. Weitere Punkte ohne direkten Zeilenbezug

Diese Punkte stehen in Ihrer Tabelle nicht als Anmerkung, brauchen aber Ihre Einschätzung. Kurzform: Befund aus dem
Paket, unser Stand, Frage.

## Frage 26 – Zwei MTB-Paketdefekte, die die Validierung scheitern lassen

**Im Paket.** (1) `mii-pr-mtb-therapieplan`: Die Unter-Slices von `activity:extended` (Studieneinschluss, Biopsie,
humangenetische Beratung, Histologie-Evaluation, Therapieempfehlung) verweisen auf Profile, die das Elternprofil
`mii-pr-onko-tumorkonferenz` nicht zulässt; dort sind nur die drei Onko-Therapieempfehlungsprofile erlaubt (Entwurf
MTB-1). (2) `mii-pr-mtb-ngs-bericht`: Die `result`-Slices werden über das Profil unterschieden, und
`result:Tumorzellgehalt` (max 1) zielt auf core Observation; damit passt jede Ergebnis-Observation auch auf diesen
Slice, und ein Bericht mit mehr als einem Ergebnis verletzt dessen max (Entwurf MTB-22).

**Unser Stand.** Jeder MTB-Therapieplan mit nichtmedikamentösen Empfehlungen und fast jeder NGS-Bericht scheitert
an der Validierung. Wir weisen diese Fehler als bekannte Paketdefekte aus.

**Frage 26.** Werden MTB-1 und MTB-22 vor dem finalen Release 2027 korrigiert? Sollen wir sie als späte Kommentare
einreichen?

## Frage 27 – Mehrere Variantentypen in einem `coding-change-type`

**Im Paket.** `component:coding-change-type` ist in GR 0..1 und in MTB und MolGen geerbt. Mehrere Codings in einem
CodeableConcept sind nach FHIR alternative Darstellungen *desselben* Konzepts.

**Unser Stand.** `smallVariants[].variantTypes[]` ist eine Liste unabhängiger SO-Codes; wir legen alle als Codings in
ein CodeableConcept (Entwurf MTB-9). Bei mehreren verschiedenen Typen ist das fachlich nicht sauber.

**Frage 27.** Welche Konvention empfiehlt MII: (a) eine Auswahlregel (z. B. der spezifischste Typ) und die übrigen als
Text, (b) mehrere Codings wie bisher, oder (c) eine Änderung von `coding-change-type` auf 0..\* über HL7 Clinical
Genomics?

## Frage 28 – Fusionen und intragene Strukturvarianten

**Im Paket.** `mii-pr-mtb-dna-fusion` verlangt sechs, `mii-pr-mtb-rna-fusion` zehn Komponenten (Chromosomen,
Positionen, Gene, bei RNA auch Transkripte, Exons, Strang); ein Profil für Strukturvarianten ohne Fusion gibt es nicht.

**Unser Stand.** Der KDK liefert für Strukturvarianten nur die Partnergene und den Typ (`structureType`, darunter
`deletionOfGeneSegments` und `duplicationOfGeneSegments`). Fehlende Pflichtkomponenten senden wir mit
`dataAbsentReason` (konform, weil ihre Werte 0..1 sind); intragene Varianten landen in den Fusionsprofilen (Entwürfe
MTB-8, MTB-18).

**Frage 28.** Welches Zielprofil sieht MII für intragene Deletionen und Duplikationen vor, und sollen die
Bruchpunkt-Komponenten 0..1 werden?

## Frage 29 – Lokalisation der Variante im MTB-Bericht

**Im Paket.** MolGen hat `mii-pr-molgen-molekulare-konsequenz` (`component:feature-consequence`, SO);
`mii-pr-mtb-ngs-bericht.result` hat keinen Slice dafür.

**Unser Stand.** Wir erzeugen die Lokalisation als `molekulare-konsequenz` mit SO-Code. Abweichend von Ihrer
Anmerkung (KDK oncology 142, 164, 188: intron/intergenic „je nach Lage“) bilden wir
`notInCodingAndNotInRegulatoryElements` immer auf den Oberbegriff SO:0001537 ab, weil der KDK die Lage nicht nennt
(Entwürfe MTB-20, MOLGEN-3).

**Frage 29.** Soll `ngs-bericht.result` einen Slice für `molekulare-konsequenz` erhalten, oder soll die Variante sie
referenzieren? Ist SO:0001537 als Rückfall akzeptabel?

## Frage 30 – MV-GenomSeq-Artefakte im Onko-Modul und Zuständigkeit

**Im Paket.** `mii-lm-mvgenomseq-onkologie` und `mii-cm-onkologie-to-mvgenomseq` (draft) haben Mapping-Fehler: Die
vier TNM-Zeilen der ConceptMap zeigen auf das ECOG-Feld, die zweite ConceptMap hat keine Gruppe, und das Mapping von
`TNMSchluessel` sucht den LOINC-Code 33732-9 (Grading) im System SNOMED CT (Entwürfe ONKO-1, ONKO-2).

**Frage 30.** Möchte MII unsere Tabelle als Grundlage für diese Artefakte nutzen, und wer ist für die
MV-GenomSeq-Spezifikation zuständig (Onko-Modul, eigenes IG, BfArM)?

## Frage 31 – Identität und Verknüpfung der Ressourcen

**Unser Stand.** Wir vergeben deterministische IDs aus Sender, TAN und lokalen Kennungen, senden jeden Eintrag als
`PUT`, verknüpfen KDK und GRZ über TAN-C und TAN-G und kennzeichnen jede Ressource mit ihrer Meldung
(`meta.source`). Korrekturen löschen nichts (`docs/IDENTITY.md`).

**Frage 31.** Gibt es für MV-GenomSeq-Bundles bereits Regeln zu Identität und Verknüpfung (Patient je Spender,
Specimen, Bericht, Ergebnis), an die wir uns halten sollen, oder sollen wir unsere Regeln zur Abstimmung vorlegen?

## Frage 32 – ICD-O-3-Topographie: Prüfung

**Im Paket.** `mii-pr-onko-diagnose-primaertumor`: `bodySite.coding:icd-o-3` ist required an
`mii-vs-onko-icdo3-topographie` gebunden (schon 2026, 2027 nur an anderer Stelle). tx.fhir.org kennt die
ICD-O-3-Ausgaben 2014/2019 nicht (Entwurf ONKO-9).

**Frage 32.** Gegen welchen Terminologieserver sollen Implementierer ICD-O-3 prüfen? Bekommen wir Zugang zum
MII-Terminologieserver?

## Frage 33 – Panel-Katalog und Software für GRZ-Kits

**Im Paket.** MTB 2027 bringt elf DeviceDefinitions `mii-dd-mtb-panel-*`; in 2026 gab es keine.

**Unser Stand.** Für erkannte Panels verweisen wir aus `Device.definition` auf den Katalog; andere Kits und die
Software (Pipeline, Variant-Caller) beschreiben wir als Device mit Funktion (Entwurf MTB-21).

**Frage 33.** Wer pflegt den Katalog, und wie sollen GRZ-Kitnamen darauf abgebildet werden? Ist ein logischer Verweis
über die kanonische Kennung akzeptabel?

## Frage 34 – Festlegungen ohne Quellwert

**Unser Stand.** An drei Stellen verlangt das Zielprofil eine Angabe, die der Datenkranz nicht liefert, und wir
setzen einen Wert:

- Die Kategorie des MTB-Therapieplans (`CarePlan.category.coding`, required an `mii-vs-onko-therapieplanung-typ`)
  hat keinen Code für das molekulare Tumorboard; wir senden `praeth` plus Text (Entwurf MTB-23).
- Empfohlene Studien erhalten `ResearchStudy.status = active`, weil `status` Pflicht ist.
- Ein Follow-up mit `diagnosisEstablished = true` hebt eine Diagnose mit Status „unbestätigt“ auf „bestätigt“.

Bei Seltenen Erkrankungen leiten wir die Strategie `other` immer auf den nichtmedikamentösen Weg, weil das
medikamentöse ValueSet `other` nicht enthält (Entwurf SE-3).

**Frage 34.** Sind diese Festlegungen für Sie akzeptabel, oder sieht MII andere Werte vor?

## Frage 35 – Container für Follow-ups im MTB

**Im Paket.** MTB hat `mii-pr-mtb-follow-up-clinicalimpression` („Follow-Up als Prozess des Einholens von
Informationen über durchgeführte Therapien“, `supportingInfo:UmgesetzteTherapien` → Procedure).

**Unser Stand.** Wir bilden KDK-Follow-ups auf `mii-pr-onko-verlauf` (Observation) ab und verwenden das MTB-Profil
nicht.

**Frage 35.** Ist `mii-pr-mtb-follow-up-clinicalimpression` der vorgesehene Container für die Follow-ups des
Modellvorhabens, zusätzlich zum Onko-Verlauf?

# Anhang A – Zitierte Entwürfe für Ballot-Kommentare

Entwürfe aus `docs/BALLOT-COMMENTS-2027.md` (Stand 31.10.2026, nicht eingereicht), hier die in diesem Dokument zitierten (40). „Bezug“ verweist auf die Nummer in `docs/DISCUSS-TD-2026-10-09.md`; „Diff“ auf unseren Vergleich der Pakete 2026 und 2027 (`docs/2027-BALLOT-DIFF.md`).

### ONKO-1 – ConceptMap MV-GenomSeq: TNM-Zeilen zeigen auf ECOG, falsche Quell-URLs, leere Diagnose-Map

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/ConceptMap/mii-cm-onkologie-to-mvgenomseq`
  (status draft), Gruppe mit Quelle `…/StructureDefinition/mii-pr-onko-tnm-klassifikation`, `element[0..3]`;
  außerdem `…/ConceptMap/mii-cm-mii-to-mvgenomseq-condition-diagnose-primaertumor`.
- **Problem:** Alle vier TNM-Zeilen (TNM-Klassifikation, T-, N- und M-Kategorie) haben das Ziel
  `diagnosisOD.ECOGPerformanceStatusScore` (Copy-Paste-Fehler). Wer der Map folgt, schreibt
  OncologyCase.diagnosisOd.tnmClassifications[] in das ECOG-Feld. Die ECOG-Zeile ist als `equivalent` markiert, obwohl
  ECOG 5 und `notApplicable` nicht abbildbar sind (ONKO-4). Für OncologyFollowUp.followUpOds[].ecogPerformanceStatusScore
  gibt es kein Ziel.
- **Evidenz:** `target.code` = `diagnosisOD.ECOGPerformanceStatusScore` (4×, equivalence `equivalent`).
  `sourceUri` = `https://www.medizininformatik-initiative.de/fhir/ext/modul-onkologie/`, die Modulbasis ist aber `…/modul-onko/`.
  Die Diagnose-Gruppe nennt `…/fhir/ext/modul-diagnose/StructureDefinition/Diagnose`; das Canonical lautet
  `…/fhir/core/modul-diagnose/StructureDefinition/Diagnose`. Die zweite ConceptMap hat keine `group` und als Quelle `…/modul-onkologie/…`.
- **Vorschlag:** TNM-Zeilen auf `diagnosisOD.tnmClassifications[]` (code, system, version, text) umstellen. Die ECOG-Zeile
  nicht als vollständig kennzeichnen, sondern die fehlenden Werte nennen. Basis-URLs korrigieren und die leere
  ConceptMap füllen oder entfernen. Unsere gegen die Pakete geprüfte Mapping-Tabelle stellen wir als Quelle zur Verfügung.
- **Bezug:** 7

### ONKO-2 – Logisches Modell MV-GenomSeq: falsches TNMSchluessel-Mapping, Blöcke ohne Mapping

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-lm-mvgenomseq-onkologie`,
  `mii-lm-mvgenomseq-onkologie.OnkologieFall.Diagnose.TNMSchluessel` (mapping identity `MVGenomSeq-Datenkranz-to-MII-FHIR`).
- **Problem:** Das Mapping von `TNMSchluessel` sucht eine Observation mit Code 33732-9 im System SNOMED CT. 33732-9 ist
  aber ein LOINC-Code (Grading), deshalb trifft der Ausdruck weder TNM noch Grading. Derselbe Text steht schon in 2026.0.3.
  Kein Mapping haben:
  - der gesamte Block `OnkologieFollowup` (u. a. `ECOG`, `MetachroneTumore`, `MetachroneDiagnose`, `Therapien.DatenquelleTherapieansprechen`),
  - `OnkologiePlan.PraeventiveUntersuchungen`, `…MolekularesTumorboard.EmpfehlungOperationTherapeutisch` und `…Risikoreduzierend`,
  - `…Therapieempfehlung.EmpfehlungTyp` und `…EmpfohleneStudie.Evidenzgrad`,
  - `OnkologieMolekular.ExpressionsVariante.*` und `EinfacheVariante.LossOfHeterozygosity`.

  Außerdem hängen TMB, HRD, LST, TAI, SBS, SBSSignature und Lokalization unter `ExpressionsVariante`. Im KDK stehen sie
  in `complexBiomarkers[]`, `sbsSignatures[]` bzw. bei den Varianten. Betroffen sind OncologyCase.diagnosisOd.tnmClassifications[]
  sowie Felder aus OncologyFollowUp, OncologyPlan und OncologyMolecular.
- **Evidenz:** `mapping.map` = `Observation.where(code.coding.code='33732-9' and code.coding.system='http://snomed.info/sct')…`.
  Bei den genannten Elementen ist `mapping` leer. `Keimbahndiagnose` und `DiagnostischeVoruntersuchungen` sind als
  „no direct match" vermerkt.
- **Vorschlag:** `TNMSchluessel` auf `mii-pr-onko-tnm-klassifikation` und die T-, N- und M-Kategorieprofile mappen.
  Die offenen Blöcke entweder mappen oder ausdrücklich an KDS MTB bzw. eine MV-GenomSeq-Spezifikation übergeben; die
  ConceptMap ordnet Plan, FollowUp und Molecular bereits MTB zu. Die Komplex-Biomarker aus `ExpressionsVariante` herauslösen.
- **Bezug:** 7

### ONKO-3 – HGNC-System zwischen den Modulen uneinheitlich

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-genetische-variante`,
  `Observation.component:gene-studied.value[x]` (1..1, extensible `…/modul-onko/ValueSet/mii-vs-onko-marker-gene-hgnc`).
- **Problem:** Die neuen Onko-Gen-ValueSets verwenden das System `http://www.genenames.org/geneId`. Das betrifft
  `mii-vs-onko-marker-gene-hgnc` (40 Gene), `-praedispositionsgene-hgnc` und `-ighv-gensegmente-hgnc`; die MTB-Panel-ValueSets
  ebenso. MTB- und MolGen-Variantenprofile binden dagegen GR `hgnc-vs` mit dem System `http://www.genenames.org`. Für dieselben
  Gene gibt es damit zwei System-URIs. Betroffen sind OncologyMolecular.smallVariants[].genes[], .copyNumberVariants[].genes[]
  und .structuralVariants[].genes[]; RareDiseasesMolecular entsprechend. Das MII-Beispiel `MII-EXA-MTB-Einfache-Variante`
  nutzt `/geneId` an einem Element, das auf `hgnc-vs` gebunden ist.
- **Evidenz:** In 2026.0.3 war `gene-studied` an GR `hgnc-vs` gebunden. GR 3.0.0 `ValueSet/hgnc-vs` enthält nur
  `http://www.genenames.org` und `http://www.genenames.org/genegroup`. `mii-pr-mtb-einfache-variante.component:gene-studied.value[x]`
  ist extensible an `hgnc-vs` gebunden.
- **Vorschlag:** Ein HGNC-System für alle MII-Module festlegen, bevorzugt das GR-System `http://www.genenames.org`, und
  Onko- und MTB-ValueSets sowie die Beispiele angleichen. Alternativ beide URIs explizit dokumentieren (NamingSystem).
  Bitte auch klären, ob die 40-Gen-Liste bewusst eine geschlossene Aufzählung ist.
- **Bezug:** 9

### ONKO-4 – ECOG 5 und „nicht anwendbar" nicht darstellbar

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-allgemeiner-leistungszustand-ecog`:
  - `Observation.value[x]` 1..1,
  - `Observation.value[x].coding:obds` 1..1, required `…/ValueSet/mii-vs-onko-allgemeiner-leistungszustand-ecog`,
  - `Observation.value[x].coding:loinc` 0..*, required `…/ValueSet/mii-vs-onko-allgemeiner-leistungszustand-ecog-loinc`.
- **Problem:** OncologyCase.diagnosisOd.ecogPerformanceStatusScore und OncologyFollowUp.followUpOds[].ecogPerformanceStatusScore
  erlauben die Werte 0–5, `unknown` und `notApplicable`. Die oBDS-Codierung ist Pflicht und kennt nur 0–4 und U.
  `dataAbsentReason` ist neben `value[x]` 1..1 ausgeschlossen (obs-6). ECOG 5 und `notApplicable` müssen deshalb verworfen werden.
  Widersprüchlich ist außerdem: Das neue LOINC-ValueSet enthält LA9627-6 „Dead" (= ECOG 5). Wegen `coding:obds` 1..1 kann
  dieser Code aber nie allein konform verwendet werden.
- **Evidenz:** CS `mii-cs-onko-allgemeiner-leistungszustand-ecog` enthält 0, 1, 2, 3, 4, U. VS `…-ecog-loinc` enthält
  LA9622-7 bis LA9627-6. In der ConceptMap `mii-cm-onko-allgemeiner-leistungszustand-ecog-loinc` ist U `unmatched` und es
  fehlt eine Zeile für 5.
- **Vorschlag:** Code `5` (Tod) und ein explizites „nicht anwendbar" ins CS aufnehmen und in der ConceptMap die Zeile
  5 → LA9627-6 ergänzen. Alternative: `coding:obds` auf 0..1 setzen (Invariante: obds oder loinc) und für „nicht anwendbar"
  `value[x]` 0..1 mit `dataAbsentReason` zulassen. Zusätzlich dokumentieren, wie eine Verlaufs-ECOG gekennzeichnet wird:
  2027 lässt `mii-pr-onko-verlauf.hasMember` keine ECOG-Observation mehr zu.
- **Bezug:** 1

### ONKO-5 – TNM: UICC-Codierung ist Pflicht, der Datenkranz liefert SNOMED CT

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-tnm-t-kategorie`
  (ebenso `-n-kategorie` und `-m-kategorie`):
  - `Observation.value[x].coding:uicc` 1..1, required `…/ValueSet/mii-vs-onko-tnm-t-kategorie-werte`,
  - `Observation.value[x].coding:snomed-ct` 0..1, required `…-werte-sct`,
  - Invariante `tnm-sct-uicc-konsistenz` (error).
- **Problem:** OncologyCase.diagnosisOd.tnmClassifications[] liefert SNOMED-CT-Codings (code, system, version, display, text).
  Die UICC-Codierung muss deshalb per Rückabbildung SNOMED → UICC erzeugt werden. Die MII-ConceptMaps laufen nur in
  Richtung UICC → SNOMED; eine dokumentierte Rückrichtung gibt es nicht. Für die T-, N- und M-Kategorien, die der
  Datenkranz liefert, fehlen in den Maps Tis(pu), Tis(pd), N1mi und MX (klinisch) bzw. Tis(pu), Tis(pd), T3e, M0 und MX
  (pathologisch); die übrigen der 38 bzw. 39 ungemappten UICC-Codes sind Präfixe, Symbole und L/V/Pn/S, die der
  Datenkranz nicht liefert. Einträge ohne Treffer können nicht konform übermittelt werden.
- **Evidenz:** `mii-cm-onko-tnm-uicc-sct-clinical` und `-pathological` bilden nur in Richtung UICC → SCT ab.
  `tnm-sct-uicc-konsistenz` verlangt, dass das SNOMED-Display Präfix und UICC-Code enthält.
- **Vorschlag:** `coding:uicc` 0..1 setzen, wenn `coding:snomed-ct` vorhanden ist (Invariante: mindestens eine der beiden
  Codierungen). Eine geprüfte ConceptMap SCT → UICC ausliefern. Die Display-Invariante nur anwenden, wenn UICC vorhanden ist.
- **Bezug:** 2

### ONKO-6 – Therapieart (therapeuticStrategy) an der Therapieempfehlung

- **Profil/Element:** `MedicationRequest.category` (0..*, example-gebunden an `medicationrequest-category`) in
  `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-therapieempfehlung-medikation`
  und im abgeleiteten Profil `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-therapieempfehlung`.
- **Problem:** OncologyPlan.recommendedSystemicTherapies[].therapeuticStrategy (CH, HO, IM, ZS, CI, CZ, CIZ, IZ, SZ, SO)
  ist eine echte Teilmenge von `mii-cs-onko-therapie-typ`, hat aber kein profiliertes Element an der Empfehlung.
  Konform ist es heute nur auf zwei Wegen: als Coding im example-gebundenen `category` (ohne Slice) oder in einem
  RequestGroup-Wrapper je Empfehlung (`mii-pr-mtb-therapieempfehlung-kombination.RequestGroup.code`, preferred).
  `CarePlan.activity:obds.reference` ist 0..0.
- **Evidenz:** `mii-vs-onko-systemische-therapie-art` (CH … SO, ohne OP, ST, KW) ist nur an
  `mii-pr-onko-systemische-therapie.Procedure.code.coding:systemische_therapie_art` gebunden.
- **Vorschlag:** Slice `MedicationRequest.category:therapieart` (0..1, required) im Onko-Basisprofil anlegen; MTB erbt ihn.
  Bindung an `mii-vs-onko-systemische-therapie-art`, oder an `mii-vs-onko-therapieempfehlung-typ`, wenn es konsistent zu
  `RequestGroup.code` und `activity:obds` sein soll. Vorbild ist die Seltene-Lösung `category:MVGenomSeqTherapieStrategie`.
- **Bezug:** 3

### ONKO-7 – Metachrone Tumoren: die Ja/Nein-Angabe hat kein Element

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-diagnose-primaertumor`:
  `Condition.extension:occurredFollowing` (2027 auch mit Ziel `mii-pr-onko-diagnose-primaertumor`) und `Condition.extension:dueTo`.
  Außerdem `…/mii-pr-onko-verlauf`.
- **Problem:** OncologyFollowUp.followUpOds[].metachroneDiagnoses ist ein Boolean („metachrone Tumoren aufgetreten"). Die
  Diagnosen selbst stehen in `additionalDiagnoses[]`. Ab 2027 lässt sich das Auftreten nur ableiten, nämlich über eine
  Folge-Condition mit `occurredFollowing` → Erstdiagnose. `true` ohne begleitende Diagnose und ein explizites `false` gehen
  verloren. Unklar ist auch, welches Bindeglied vorgesehen ist: `occurredFollowing` (zeitlich) oder `dueTo` (kausal, therapieassoziiert).
- **Evidenz:** Im LM haben `OnkologieFollowup.MetachroneTumore` und `.MetachroneDiagnose` kein Mapping.
  `mii-pr-onko-verlauf` enthält kein passendes Element.
- **Vorschlag:** Entweder ein Element „metachroner Tumor ja/nein" einführen (Komponente oder Extension an `mii-pr-onko-verlauf`)
  oder die Ableitungsregel dokumentieren: `occurredFollowing` für metachrone Tumoren, `dueTo` nur für therapieassoziierte
  Zweittumoren. In beiden Fällen die LM-Mappings ergänzen.
- **Bezug:** 4

### ONKO-8 – Erblicher Tumorfall: diagnostische Bewertung, präventive Maßnahmen, Zweck der Intervention

- **Profil/Element:** Es gibt kein Zielelement. Am nächsten kommen
  `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-therapieempfehlung-operation`
  (ServiceRequest, ohne Intentions-Extension) und `…/mii-ex-onko-operation-intention` (Kontext nur `Procedure`).
- **Problem:** Drei KDK-Blöcke haben weder in Onko 2027 noch in MTB 2027 ein Ziel:
  - (a) OncologyCase.diagnosisOd.diagnosticAssessment (noGeneticDiagnosis, suspected…, furtherGeneticDiagnosticRecommended,
    confirmed…, partial…),
  - (b) OncologyFollowUp.followUpOds[].preventiveMeasures[].preventiveMeasureResult (noFindings, malignoma, unclear)
    und `.reference`,
  - (c) OncologyPlan.carePlanOd.suitableInterventions[].interventionIsTherapeutic und `.interventionsIsRiskReducing`.

  Ohne Interimslösung fehlen diese Daten in onkologischen Bundles.
- **Evidenz:**
  - Im LM steht bei `Keimbahndiagnose` „no direct match … existiert als Konzept nicht". `PraeventiveUntersuchungen`
    und `EmpfehlungOperationTherapeutisch/-Risikoreduzierend` haben kein Mapping.
  - CS `mii-cs-onko-intention` (K, P, D, R, S, X, O) enthält keinen Code für „risikoreduzierend".
  - Die neuen ValueSets `mii-vs-onko-praedispositionsgene-hgnc` und `-praedispositionssyndrome-orpha` werden von keinem
    Onko- oder MTB-Profil gebunden.
- **Vorschlag:**
  - (a) ein Profil für Keimbahndiagnose bzw. Bewertung, oder die Wiederverwendung von `mii-pr-seltene-genetic-diagnosis`
    mit `verificationStatus` dokumentieren;
  - (b) Profile für präventive Maßnahmen mit Ergebnis-ValueSet und Rückbezug;
  - (c) `mii-ex-onko-operation-intention` um „risikoreduzierend" erweitern und auf `mii-pr-onko-therapieempfehlung-operation` slicen.

  Bitte außerdem den Zweck der Prädispositions-ValueSets erläutern.
- **Bezug:** 5

### ONKO-9 – ICD-O-3-Topographie: required-Binding, Validierungsweg unklar

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-onko/StructureDefinition/mii-pr-onko-diagnose-primaertumor`
  (vererbt an `mii-pr-mtb-diagnose-primaertumor`):
  - `Condition.bodySite.coding:icd-o-3` 0..1, required `…/ValueSet/mii-vs-onko-icdo3-topographie` (VS an die Versionen 2014 und 2019 gebunden),
  - `Condition.bodySite` 0..*.
- **Problem:** OncologyCase.diagnosisOd.topography (code, system, version) wird mit required-Bindung gegen ICD-O-3 geprüft.
  tx.fhir.org kennt ICD-O-3 nur in der Ausgabe 2000 („Valid versions: 2000") und akzeptiert dort per
  `$validate-code` sogar nicht existierende Codes; die von der VS geforderten Ausgaben 2014 und 2019 fehlen. Implementierer
  können die Bindung daher nicht prüfen (matchbox: „version '2019' … could not be found", also ungeprüft).
  Erzwungen ist die Codierung nicht, weil `bodySite` optional bleibt.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft); tx.fhir.org-Abfragen vom 2026-10-09 (`docs/TERMINOLOGY-CAPABILITY.md`).
- **Vorschlag:** Dokumentieren, gegen welchen Terminologieserver oder welches Paket ICD-O-3 (2014/2019) geprüft werden soll,
  oder ein CodeSystem-Fragment bereitstellen. Außerdem klären, ob `required` beabsichtigt ist oder `extensible` genügt.
- **Bezug:** 8

### MTB-1 – Therapieplan: Unter-Slices von `activity:extended` widersprechen dem Elternprofil

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-therapieplan`:
  `CarePlan.activity:extended.reference` und die Unter-Slices `activity:extended/Studieneinschlussempfehlung.reference`,
  `/Biopsie.reference`, `/HumangenetischeBeratung.reference`, `/HistologieEvaluation.reference` und `/Therapieempfehlung.reference`.
- **Problem:** Seit 2027 erbt `activity:extended.reference` von `mii-pr-onko-tumorkonferenz` nur noch die Ziele
  `mii-pr-onko-therapieempfehlung-{kombinationstherapie,medikation,operation}`. Die MTB-Unter-Slices verweisen aber auf
  ServiceRequest-Profile, die direkt von core ServiceRequest abgeleitet sind: `mii-pr-mtb-studieneinschluss-anfrage`,
  `-biopsie-auftrag`, `-humangenetische-beratung-auftrag`, `-histologie-evaluation-auftrag`. Der Slice `Therapieempfehlung`
  lässt zusätzlich generische MedicationRequest- und RequestGroup-Ressourcen zu. Keine dieser Referenzen kann das Elternprofil
  erfüllen. Betroffen sind OncologyPlan.recommendedStudies[] und Empfehlungen wie OncologyPlan.carePlanOd.counsellingRecommended.
- **Evidenz:** `activity:extended.reference` ist 1..1 Reference auf die drei Onko-Profile. Die Unter-Slices sind 1..1 Reference
  auf die MTB-Profile. Die `baseDefinition` der vier Auftragsprofile ist `http://hl7.org/fhir/StructureDefinition/ServiceRequest`.
  In 2026.0.1 erlaubte die Elternliste noch MedicationRequest und ServiceRequest. Das Verhalten der Validatoren haben wir nicht getestet.
- **Vorschlag:** In `mii-pr-onko-tumorkonferenz` ServiceRequest, MedicationRequest und RequestGroup wieder als Ziele zulassen.
  Ein abgeleitetes Profil kann die Zielliste nicht erweitern. Zur Absicherung ein Beispiel „Therapieplan mit
  Studieneinschlussempfehlung" validieren.
- **Bezug:** Diff

### MTB-2 – Transkript-ID: required-Binding an `http://ensembl.org`, das kein ValueSet ist

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-einfache-variante`,
  `Observation.component:representative-transcript-ref-seq.value[x]` (1..1, required `http://ensembl.org`).
- **Problem:** OncologyMolecular.smallVariants[].transcriptId und OncologyCase.priorDiagnostics[].simpleVariants[].transcript
  liefern Ensembl- oder RefSeq-IDs; DNPM erlaubt beides. `http://ensembl.org` ist kein ValueSet. Validatoren melden nur
  „ValueSet not found" als Warnung, die Daten passieren also zufällig. Das mitgelieferte Beispiel widerspricht dem Profil:
  Es verwendet RefSeq `NM_133433.4` mit dem System `https://www.ncbi.nlm.nih.gov/refseq/`.
- **Evidenz:** Die Binding-URL `http://ensembl.org` gibt es in keinem Paket als ValueSet. Siehe Beispiel
  `Observation-MII-EXA-MTB-Einfache-Variante`. MolGen `variante` bindet dasselbe Element nur mit `example`.
- **Vorschlag:** Das Binding wie in MolGen auf `example` oder `extensible` setzen, oder ein echtes ValueSet für Ensembl,
  RefSeq und LRG mit festen System-URIs veröffentlichen. Die System-URIs dokumentieren: MTB-Beispiele nutzen
  `https://www.ncbi.nlm.nih.gov/refseq/`, MolGen-Beispiele `http://www.ncbi.nlm.nih.gov/refseq`.
- **Bezug:** 10

### MTB-3 – QC-Extension: Kontext „Extension" statt Procedure, keine Definitionen

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-ex-mtb-genomic-study-analysis-qc`,
  genutzt als `mii-pr-mtb-genomic-study-analysis.Procedure.extension:qc`. Sub-Extensions: `read-depth`, `read-length`,
  `sequencing-coverage`, `gap-statistics` (Quantity), `metrics-description` (string), `sequencing-read-type`
  (CodeableConcept, ungebunden).
- **Problem:** Als Kontext ist `extension` mit `http://hl7.org/fhir/StructureDefinition/Extension` deklariert, nicht
  `Procedure`. Strikte Validatoren können die Extension am Procedure ablehnen. Keine Sub-Extension hat einen Definitionstext.
  Die Namen übernehmen GR `genomic-study-analysis-metrics`; dort bedeutet `sequencing-coverage` den Anteil abgedeckter
  Regionen in Prozent und `read-depth` die mittlere Lesetiefe. Betroffen sind GRZ donors[].labData[].sequenceData.meanDepthOfCoverage,
  .targetedRegionsAboveMinCoverage und donors[].labData[].sequencingLayout.
- **Evidenz:** `StructureDefinition.context` = `[{type: extension, expression: Extension}]`, so auch schon in 2026.0.1.
  `sequencing-read-type.value[x]` hat keine Bindung.
- **Vorschlag:** Den Kontext auf `Procedure` korrigieren. Definitionen nach GR-Semantik und Einheiten ergänzen.
  Dokumentieren, wie `qc` sich zur ebenfalls geslicten GR-Extension `metrics` (Kontext Procedure, gültig; read-depth,
  sequencing-coverage, metrics-description) verhält: Für diese drei Werte gibt es dort schon heute einen konformen
  Träger; offen ist, ob `qc` sie ersetzen oder nur ergänzen soll.
  `sequencing-read-type` an ein ValueSet binden (z. B. single-end/paired-end, short/long read).
- **Bezug:** 22

### MTB-7 – CNV-Typ: CodeSystem undefiniert, Wert ungebunden

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-copy-number-variant`,
  `Observation.component:cnv-type` (0..*), `.code` mit Pattern `http://bwhc.de/mtb/genetics-copy-number-variant#type`,
  `.value[x]:valueCodeableConcept` (0..1, ohne Binding).
- **Problem:** Für die URI `http://bwhc.de/mtb/genetics-copy-number-variant` gibt es kein CodeSystem. Der Wert ist ungebunden,
  falsche Codes fallen also nicht auf. Die MTB-Beispiele nutzen die DNPM-Werte low-level-gain, high-level-gain und loss.
  OncologyMolecular.copyNumberVariants[].cnvType hat sechs Stufen: completeLoss, heterozygousLoss, loss, lowLevelGain,
  highLevelGain, gain. Für drei davon gibt es weder einen DNPM- noch einen MII-Code.
- **Evidenz:** Im Paket gibt es kein `CodeSystem` mit dieser URL.
- **Vorschlag:** Ein MII-CodeSystem und ValueSet für den CNV-Typ veröffentlichen, das die sechs Datenkranz-Stufen enthält,
  und die Komponente extensible daran binden.
- **Bezug:** 17

### MTB-8 – Fusionen: Partner-Gen- und Positions-Slices uneinheitlich

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-dna-fusion`.
  Typ-Slices gibt es nur für `five-prime-chromosome`, `three-prime-chromosome` und `three-prime-gene`
  (jeweils `valueCodeableConcept`) sowie für `five-prime-position` (`valueRange`). Analog gilt das für `mii-pr-mtb-rna-fusion`.
- **Problem:** In `dna-fusion` hat das 5'-Partner-Gen keinen `valueCodeableConcept`-Slice, das 3'-Gen dagegen schon.
  Ebenso hat `three-prime-position` keinen `valueRange`-Slice, `five-prime-position` aber schon. Keiner der Partner-Gen-Werte
  ist an `hgnc-vs` gebunden; gebunden ist nur das geerbte `gene-studied`. Das DNA-Fusionsbeispiel trägt kein Code-System.
  Betroffen sind OncologyMolecular.structuralVariants[].geneA und .geneB.
- **Evidenz:** im Snapshot geprüft (siehe oben).
- **Vorschlag:** Die Slices symmetrisch anlegen, alle Partner-Gen-Werte extensible an GR `hgnc-vs` binden (System gemäß ONKO-3)
  und das Beispiel korrigieren.
- **Bezug:** 21

### MTB-9 – Variantentyp: `coding-change-type` ist 0..1, der Datenkranz liefert eine Liste

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-einfache-variante`,
  `Observation.component:coding-change-type` (0..1; `value[x]` 1..1, extensible GR `dna-change-type-vs`). Gleich in
  `-dna-fusion`, `-rna-fusion` und MolGen `variante`.
- **Problem:** OncologyMolecular.smallVariants[].variantTypes[] und OncologyCase.priorDiagnostics[].simpleVariants[].variantTypes[]
  können mehrere SO-Codings je Variante enthalten. Es gibt aber nur eine Komponente; die Kardinalität 0..1 ist aus GR
  geerbt und kann von MII nicht erweitert werden. Das MII-Beispiel `fgfr2-fusion` trägt SO:0001565 gene_fusion in
  `coding-change-type` ein; dieser Code liegt außerhalb von `dna-change-type-vs`.
- **Evidenz:** max 1 in allen genannten Profilen. GR `dna-change-type-vs` = SO is-a SO:0002072. Geprüft 2026-10-10 an der
  SO-Hierarchie (OLS): SO:0000199 translocation liegt unter structural_alteration SO:0001785 → sequence_alteration
  SO:0001059 → sequence_comparison SO:0002072 und ist damit enthalten (ebenso deletion, duplication, inversion).
  SO:0001565 gene_fusion liegt unter feature_fusion / structural_variant SO:0001537 / sequence_variant SO:0001060
  (molekulare Konsequenz), nicht unter SO:0002072.
- **Vorschlag:** Als Konvention dokumentieren, dass mehrere SO-Codings in ein `CodeableConcept.coding[]` gehören. Bei
  Fusionen gehört der Strukturmechanismus (translocation, inversion, deletion, duplication) in `coding-change-type`;
  das Beispiel `fgfr2-fusion` entsprechend korrigieren (gene_fusion ist kein Mitglied des ValueSets). Das SO-System
  vereinheitlichen (GR nutzt `http://www.sequenceontology.org`, siehe MOLGEN-2). (Stand 2026-10-10: der frühere
  Vorschlag, gene_fusion zusätzlich einzutragen, ist zurückgezogen.)
- **Bezug:** 11

### MTB-10 – Vorbefunde: Freitext-Träger, Datum, Untersuchungsart

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-ngs-bericht`,
  verknüpft über `mii-pr-mtb-behandlungsepisode.ClinicalImpression.supportingInfo:Vorbefund`:
  - `DiagnosticReport.conclusion` 0..1, nicht MS,
  - `DiagnosticReport.effective[x]` 0..1, nicht MS,
  - `DiagnosticReport.issued` 0..1 MS (instant),
  - Extension `…/mii-ex-mtb-ngs-bericht-genomic-study`,
  - `mii-pr-mtb-genomic-study-analysis.Procedure.extension:method-type` (required `…/ValueSet/mii-vs-mtb-genomic-analysis-method-type`).
- **Problem:**
  - OncologyCase.priorDiagnostics[].complexVariants[] ist Freitext. Einen profilierten Freitext-Träger gibt es: die
    Komponente `conclusion-string` (GR `tbd-codes-cs#conclusion-string`, valueString, 0..1 MS) auf
    `mii-pr-mtb-einfache-variante` und den übrigen Varianten-Profilen (geerbt aus GR/MolGen `variante`). Sie setzt
    aber eine Varianten-Observation voraus und ist für eine Freitext-Zeile ohne strukturierte Variante nicht gedacht;
    auf Berichtsebene bleibt nur `DiagnosticReport.conclusion` (nicht MS). Der Konverter nutzt `conclusion`.
  - `.date` ist tagesgenau, das einzige MS-Datum `issued` ist aber ein instant.
  - Für `.type` gibt es keinen Code für `single` (Einzelgen). Die Unterscheidung Kurz-/Langread beim Genom geht verloren.
  - Die Verknüpfung Bericht → Studie ist als Extension definiert, aber in kein Profil eingehängt.
- **Evidenz:** `mii-ex-mtb-ngs-bericht-genomic-study` (Kontext DiagnosticReport) wird von keinem Profil verwendet.
  Das method-type-VS besteht aus dem MII-CS (6 Codes) und GR `genomic-study-method-type-cs`; Karyotypisierung, Microarray
  und other sind damit vorhanden.
- **Vorschlag:** `conclusion` als MS kennzeichnen oder festlegen, ob Freitext-Vorbefunde als Varianten-Observation mit
  `conclusion-string` erfasst werden sollen (Stand 2026-10-10: dieser profilierte Träger existiert bereits).
  `effectiveDateTime` als MS kennzeichnen. Die Extension `genomic-study` in `ngs-bericht` slicen. Einen Code für
  Einzelgen-Tests und die Unterscheidung Kurz-/Langread ergänzen (gezielte Analyse ist als GR
  `targeted-variant-analysis` bereits enthalten).
- **Bezug:** 12

### MTB-11 – Durchgeführte Therapie lässt sich nicht mit einer Studien- oder Kombinationsempfehlung verknüpfen

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-systemische-therapie`:
  - `Procedure.extension:causedBy.value[x]` → MII MedicationRequest, `mii-pr-mtb-therapieempfehlung` oder MedicationRequest,
  - `Procedure.basedOn` 0..1, nur Reference(CarePlan), mit Slice `basedOn:tumorkonferenz` → `mii-pr-mtb-therapieplan`.
- **Problem:** OncologyFollowUp.followUpOds[].therapies[].reference verweist auf eine Empfehlung des Boards. Für
  Therapieempfehlungen (MedicationRequest) ist `causedBy` der direkte Link und funktioniert heute. Für Therapien aus einer
  Studienempfehlung (`mii-pr-mtb-studieneinschluss-anfrage`, ServiceRequest) gibt es kein konformes Ziel. Die Basis-Extension
  `procedure-causedBy` erlaubt weder ServiceRequest noch RequestGroup. Nebenbefund: `mii-pr-mtb-systemtherapie-medication-statement.basedOn:tumorkonferenz`
  zielt auf `mii-pr-onko-tumorkonferenz`, `systemische-therapie.basedOn:tumorkonferenz` dagegen auf `mii-pr-mtb-therapieplan`.
- **Evidenz:** Die Zieltypen von `procedure-causedBy` sind in hl7.fhir.uv.extensions.r4#5.3.0 und core 4.0.1 geprüft.
  In core erlaubt `Procedure.basedOn` Reference(CarePlan | ServiceRequest).
- **Vorschlag:** `Procedure.basedOn` auf 0..* öffnen und einen Slice → `mii-pr-mtb-studieneinschluss-anfrage` ergänzen.
  Für Kombinationen dokumentieren, dass `causedBy` auf die Mitglieds-Therapieempfehlung zeigt. Die Ziele von
  `basedOn:tumorkonferenz` modulübergreifend vereinheitlichen.
- **Bezug:** 13

### MTB-12 – Therapieansprechen: `method` 1..1 ohne Datenquelle im Datenkranz; die Informationsquelle hat kein Element

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-response-befund`,
  `Observation.method` (1..1 MS, required `…/ValueSet/mii-vs-mtb-response-befund-beurteilungsmethode`, enthält nur RECIST und RANO).
- **Problem:**
  - OncologyFollowUp.followUpOds[].therapies[].therapyResponse und OncologyCase.priorProcedures[].therapyResponse
    (PD, SD, PR, CR) lassen sich 1:1 auf `coding:MTB` abbilden. Der Datenkranz übermittelt aber keine Beurteilungsmethode,
    deshalb ist keine Response-Observation konform.
  - OncologyFollowUp.followUpOds[].therapies[].therapyResponseSource gibt an, woher die Angabe stammt (Arztbrief,
    Entlassungsbericht, Tumordokumentation). Es ist keine Beurteilungsmethode und hat kein eigenes Element.
- **Evidenz:** CS `mii-cs-mtb-response-befund-beurteilungsmethode` enthält RECIST und RANO. LM
  `mii-lm-mvgenomseq-onkologie.OnkologieFollowup.Therapien.DatenquelleTherapieansprechen` ist 1..1 und hat kein Mapping.
- **Vorschlag:** `method` auf 0..1 setzen oder die Codes `other` und `unknown` ins CS aufnehmen. Für die Informationsquelle
  ein Element festlegen, entweder als Extension oder als dokumentierten Weg über `derivedFrom` → DocumentReference bzw. `note`.
- **Bezug:** 14

### MTB-13 – Studienempfehlungen: Evidenzgrad, Z(FDA), stützende Varianten

- **Profil/Element:**
  - `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-ex-mtb-empfehlung-evidenzgraduierung`
    (Kontext RequestGroup, MedicationRequest, Observation),
  - `…/mii-pr-mtb-studieneinschluss-anfrage`: Extension-Slices nur statusReason, Prioritaet und Publikation;
    `ServiceRequest.reasonReference` 0..* → `mii-pr-mtb-diagnose-primaertumor` oder Condition,
  - CS `…/CodeSystem/mii-cs-mtb-empfehlung-evidenzgrad-zusatzverweis` mit den Codes is, iv, Z und R.
- **Problem:**
  - OncologyPlan.recommendedStudies[].evidenceLevel und .evidenceLevelDetails[] haben keinen Platz. Der Kontext der
    Extension schließt ServiceRequest aus, und die Studien-Anfrage hat keinen entsprechenden Slice.
  - `Z(FDA)` in OncologyPlan.recommendedSystemicTherapies[].evidenceLevelDetails[] bedeutet „nur FDA-Zulassung". Es fällt
    auf `Z` (EMA-Zulassung) zusammen, denn Z(FDA) steht nur im Definitionstext von `Z`.
  - OncologyPlan.recommendedStudies[].variants[] passen nur in das offene `supportingInfo`. Anders als bei
    `mii-pr-mtb-therapieempfehlung` gibt es keinen `reasonReference:StuetzendeMolekulareAlteration`.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** ServiceRequest in den Kontext der Extension aufnehmen und `extension:Evidenzgraduierung` auf
  `studieneinschluss-anfrage` slicen. Einen eigenen Zusatzverweis-Code für Z(FDA) einführen.
  `reasonReference:StuetzendeMolekulareAlteration` analog zur Therapieempfehlung ergänzen.
- **Bezug:** 15

### MTB-14 – Empfehlungstyp (in-label, off-label, compassionate use, sekundärpräventiv, unbekannt)

- **Profil/Element:**
  - `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-therapieempfehlung`:
    Extension-Slices nur Prioritaet, Evidenzgraduierung und Publikation,
  - CS `…/CodeSystem/mii-cs-mtb-zulassungsstatus` (in-label, off-label, leitlinie). Gebunden ist es nur in
    `…/mii-ex-mtb-leitlinie-dokumentation`, und diese Extension wird nur in `mii-pr-mtb-systemische-vortherapie` und
    `mii-pr-mtb-behandlungsepisode` verwendet.
- **Problem:** OncologyPlan.recommendedSystemicTherapies[].type (inLabel, offLabel, compassionateUse, secPreventive, unknown)
  hat an der Empfehlung keinen profilierten Platz. Strukturell zulässig ist `mii-ex-mtb-leitlinie-dokumentation`
  (Kontext `Element`, `MedicationRequest.extension` offen geslict) für in-label und off-label; offen sind die
  vorgesehene Verwendung und die Werte compassionateUse, secPreventive und unknown, die im CS ganz fehlen. Das LM `mii-lm-mvgenomseq-onkologie` führt genau diese fünf Werte als
  `EmpfehlungTyp`, aber ohne Mapping.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** Eine Extension für Zulassungsstatus bzw. Empfehlungstyp auf `mii-pr-mtb-therapieempfehlung` slicen und
  das CS um compassionate-use, secondary-preventive und unknown ergänzen. Alternativ eine eigene Empfehlungstyp-Extension
  gemäß LM einführen.
- **Bezug:** 16

### MTB-15 – Expressionsniveau und Referenzkohorte lassen sich nicht codieren

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-rna-seq`:
  - `Observation.value[x]:valueCodeableConcept` (0..1, required `http://loinc.org/vs/LL1971-2`; das value[x]-Slicing ist im Snapshot geschlossen),
  - `Observation.interpretation` (extensible, Basis-ValueSet).
- **Problem:** OncologyMolecular.expressionVariants[].expressionType (noExpression, normal, high, low) passt nicht in das
  ValueSet Present/Absent, und die Komponenten sind nur numerisch oder boolesch. Interimslösung: LL1971-2 (noExpression →
  Absent, sonst Present) plus `interpretation` H/L/N. Damit ist die Stufe nur indirekt erkennbar.
  OncologyMolecular.expressionVariants[].reference ist eine Freitext-Bewertungsgrundlage, z. B. eine Vergleichskohorte,
  und passt nur in `note`.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** Eine Komponente `expression-level` mit gebundenem ValueSet (nicht exprimiert / normal / hoch / niedrig)
  und eine String-Komponente `reference-cohort` einführen. Alternativ `interpretation` an `mii-vs-mtb-interpretation-high-low`
  plus N und „nicht nachweisbar" binden.
- **Bezug:** 18, 6

### MTB-16 – LOH an der Einzelvariante hat kein Konzept

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-einfache-variante`,
  `Observation.component` (Slicing offen, kein LOH-Slice). Einen LOH-Slice gibt es nur in
  `mii-pr-mtb-copy-number-variant.component:copy-number-neutral-loh`.
- **Problem:** OncologyMolecular.smallVariants[].loh (Boolean) hat keinen profilierten Platz. Als Interimslösung dient eine
  unbenannte Komponente; sie ist valide, aber für MII-Nutzer nicht maschinenlesbar. Im LM gibt es
  `EinfacheVariante.LossOfHeterozygosity`, aber ohne Mapping.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** Das Konzept `loh` in `mii-cs-mtb-molekulare-biomarker` aufnehmen und auf `einfache-variante` einen Slice
  `component:loh` anlegen (valueBoolean). Als Code bietet sich NCIt C18016 „Loss of Heterozygosity“ an, das
  `mii-pr-mtb-hrd-score.component:LOH` bereits verwendet; `copy-number-neutral-loh` hat einen ungebundenen Wert.
- **Bezug:** 19

### MTB-17 – Mutationssignaturen (COSMIC SBS) haben kein Konzept

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-molekularer-biomarker`,
  `Observation.code` (1..1, extensible `…/ValueSet/mii-vs-mtb-molekulare-biomarker`).
- **Problem:** OncologyMolecular.sbsSignatures[].name[] und .version haben kein Biomarker-Konzept. Interimslösung: ein
  genomDE-eigener Code (die Bindung ist extensible) mit einem COSMIC-Wert unter `https://cancer.sanger.ac.uk/cosmic`. Diese
  System-URI nutzt auch das MTB-Beispiel `Observation-MII-EXA-MTB-RNA-Fusion-1`, es gibt dafür aber kein NamingSystem.
  Nach TDs Prüfung gibt es keine SBS-Codes in SNOMED CT, LOINC oder NCIt (nicht verifiziert).
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** Das Konzept `mutational-signature` (SBS/DBS/ID) in `mii-cs-mtb-molekulare-biomarker` aufnehmen, ein
  NamingSystem für COSMIC-Signaturen anlegen und die Katalogversion in `Coding.version` führen.
- **Bezug:** 20

### MTB-18 – Fusionen: Bruchpunkte sind Pflicht, intragene Strukturvarianten haben kein Profil

- **Profil/Element:**
  - `…/mii-pr-mtb-dna-fusion`: `Observation.component` 6..*; `five-/three-prime-gene`, `-chromosome` und `-position` jeweils 1..1,
  - `…/mii-pr-mtb-rna-fusion`: `Observation.component` 10..*; zusätzlich `-transcript-id`, `-exon-id` und `-strand` jeweils 1..1.
- **Problem:** OncologyMolecular.structuralVariants[] liefert nur geneA, geneB, structureType und sequenceType, keine
  Bruchpunkte. Jede Fusion muss deshalb mit 4 (DNA) bzw. 8 (RNA) Komponenten aufgefüllt werden, die nur aus Code und
  `dataAbsentReason` bestehen. Für intragene Strukturvarianten (Deletion, Duplikation oder Inversion innerhalb eines Gens)
  gibt es kein MTB-Profil.
- **Evidenz:** `value[x]` dieser Slices ist 0..1 und `dataAbsentReason` 0..1; die Mindestanzahl wird also nur mit Code
  plus `dataAbsentReason` erfüllt.
- **Vorschlag:** Die Bruchpunkt-Komponenten auf 0..1 MS setzen (vgl. DNPM-LM `dnpm-lm-ngs-report` im selben Paket).
  Ein Profil oder einen Leitfaden für Strukturvarianten ohne Fusion bereitstellen.
- **Bezug:** 21

### MTB-19 – Sequenzier-QC: Kennzahlen fehlen

- **Profil/Element:** `…/mii-ex-mtb-genomic-study-analysis-qc`, Sub-Extensions wie in MTB-3.
- **Problem:** Für GRZ donors[].labData[].sequenceData.minCoverage, .percentBasesAboveQualityThreshold (minimumQuality
  und percent), .nonCodingVariants sowie donors[].labData[].fragmentationMethod gibt es keinen Platz. `sequencing-coverage`
  ist nach GR-Semantik der Anteil abgedeckter Regionen, nicht die Mindestabdeckung. Interimslösung: strukturierter Text in
  `metrics-description`.
- **Evidenz:** Sub-Extension-Liste wie in MTB-3 (Snapshot geprüft).
- **Vorschlag:** Die Sub-Extensions `min-coverage`, `percent-bases-above-quality` (Schwelle und Prozent),
  `fragmentation-method` und `non-coding-variants` ergänzen.
- **Bezug:** 22

### MTB-20 – Variantenlokalisation im NGS-Bericht

- **Profil/Element:** `…/mii-pr-mtb-ngs-bericht`, `DiagnosticReport.result` (Slicing offen). Die Slices sind
  TumorMutionalBurden, MSI, Ploidie, HRDScore, BRCAness, EinfacheVariante, CopyNumberVariant, DNAFusion, RNAFusion,
  RNASeq, MolekularerBiomarkerHER2Status, MolekularerBiomarker und Tumorzellgehalt; ein Slice für die molekulare
  Konsequenz fehlt.
- **Problem:** OncologyMolecular.smallVariants[].localization (coding, inRegulatoryElements,
  notInCodingAndNotInRegulatoryElements) hat in MTB kein Ziel. Der Weg über
  `mii-pr-molgen-molekulare-konsequenz.component:feature-consequence` ist in MTB nicht beschrieben. Die DNPM-LMs im
  MTB-Paket enthalten `localization`, aber ohne FHIR-Mapping.
- **Evidenz:** Slice-Liste aus dem Snapshot (siehe Profil/Element).
- **Vorschlag:** In `ngs-bericht` einen `result`-Slice für `mii-pr-molgen-molekulare-konsequenz` (bzw. für das
  Lokalisationsprofil aus HDB-976) anlegen oder ausdrücklich darauf verweisen. Mit MOLGEN-3 abstimmen.
- **Bezug:** 26

### MTB-21 – Panel-Katalog (DeviceDefinition) für die Kits aus dem GRZ

- **Profil/Element:** `…/mii-pr-mtb-panel-devicedefinition` (neu in 2027) mit 11 Katalogeinträgen
  `DeviceDefinition-mii-dd-mtb-panel-*`; `mii-pr-mtb-genomic-study-analysis.Procedure.extension:device`
  (GR `genomic-study-analysis-device`).
- **Problem:** GRZ donors[].labData[].kitName, .kitManufacturer, .sequencerModel, .sequenceData.bioinformaticsPipelineName,
  .sequenceData.bioinformaticsPipelineVersion und .sequenceData.callerUsed[] sollen über Device bzw. DeviceDefinition
  abgebildet werden. Offen ist, wer den Katalog pflegt, wie die Kit-Bezeichnungen aus dem GRZ den Einträgen zugeordnet
  werden und wie Software (Pipelines, Variant Caller) unter `genomic-study-analysis-device` dargestellt wird.
- **Evidenz:** siehe Profil/Element (Paketinhalt geprüft).
- **Vorschlag:** Den Katalog um die im MV-GenomSeq genutzten Kits erweitern und den Pflegeprozess benennen. Einen
  `function`-Code für Software ergänzen oder die Darstellung dokumentieren.
- **Bezug:** 24

### MTB-22 – NGS-Bericht: `result`-Slices überlappen (Tumorzellgehalt, Ploidie, HRD-Score, MSI)

- **Profil/Element:** `…/mii-pr-mtb-ngs-bericht`, `DiagnosticReport.result`: Slicing über
  `discriminator type = profile, path = $this.resolve()`, `rules = open`.
- **Problem:** Der Slice `Tumorzellgehalt` (0..1) zielt auf das Kernprofil
  `http://hl7.org/fhir/StructureDefinition/Observation|4.0.1` statt auf `mii-pr-mtb-tumorzellgehalt`. Jedes
  Ergebnis-Observation erfüllt dieses Kernprofil und passt damit zusätzlich in `Tumorzellgehalt`; ab zwei Ergebnissen
  ist dessen max = 1 überschritten. Außerdem leiten `mii-pr-mtb-ploidie` und `mii-pr-mtb-hrd-score` von
  `mii-pr-mtb-molekularer-biomarker` ab, also passt jede Ploidie- und HRD-Observation in ihren eigenen Slice (0..1)
  **und** in `MolekularerBiomarker` (0..*). Der Validator meldet für konforme Instanzen „matches more than one slice"
  bzw. „max allowed = 1", und Profile, die den NGS-Bericht referenzieren (Behandlungsepisode, Therapieplan), schlagen
  in der Folge mit „Unable to find a profile match" fehl.
  Dieselbe Doppelzuordnung trifft weitere Slices: Der Slice `MSI` (`mii-pr-mtb-mikrosatelliteninstabilitaet`) hat
  kein `code`-Pattern, also passt jede TMB-Observation auch in `MSI` (matchbox: „Element matches more than one
  slice - TumorMutionalBurden, MSI"); sobald die `resolve()`-Slices ausgewertet werden, meldet matchbox an
  `DiagnosticReport.result[n]` zusätzlich „Element matches more than one slice - EinfacheVariante,
  CopyNumberVariant". Den Überlauf von `Tumorzellgehalt` („max allowed = 1") meldet matchbox am
  DiagnosticReport selbst (Expression ohne `.result`).
- **Evidenz:** Snapshot `mii-pr-mtb-ngs-bericht` (2027.0.0-ballot.1); `baseDefinition` von `mii-pr-mtb-ploidie` und
  `mii-pr-mtb-hrd-score`; Differential von `mii-pr-mtb-mikrosatelliteninstabilitaet` (kein `code`-Pattern, anders
  als `mii-pr-mtb-mutationslast` mit LOINC 94076-7); reproduziert mit matchbox 4.1.21 an jedem NGS-Bericht mit
  mehr als einem Ergebnis.
- **Vorschlag:** `Tumorzellgehalt.targetProfile` auf `mii-pr-mtb-tumorzellgehalt` setzen; `MolekularerBiomarker` so
  einschränken, dass die spezialisierten Biomarker-Profile nicht doppelt passen (z. B. Discriminator zusätzlich über
  `code`, oder die spezialisierten Slices nur als Re-Slices von `MolekularerBiomarker`); in
  `mii-pr-mtb-mikrosatelliteninstabilitaet` ein `code`-Pattern setzen.
- **Interims-Darstellung:** Bei mehreren `complexBiomarkers[]`-Einträgen erzeugen wir je Eintrag einen eigenen NGS-Bericht,
  damit TMB, HRD-Score und Ploidie höchstens einmal je Bericht vorkommen (REPRESENTATIONS #48). Die Überlappung mit
  `Tumorzellgehalt` bleibt und ist in der Validierung als Paketdefekt markiert
  (`mtb-ngs-bericht-result-slice-overlap`): der `Tumorzellgehalt`-Überlauf am DiagnosticReport selbst und die
  Mehrfachtreffer „matches more than one slice" (TumorMutionalBurden/MSI, EinfacheVariante/CopyNumberVariant) an
  `DiagnosticReport.result[n]`.
- **Bezug:** Diff (E2E-Validierung)

### MTB-23 – Therapieplan: keine Kategorie für das Molekulare Tumorboard

- **Profil/Element:** `…/mii-pr-mtb-therapieplan`, `CarePlan.category` 1..1, `coding` 1..* required an
  `mii-vs-onko-therapieplanung-typ` (Codes `praeth`, `postop`, `postth`, `ther`).
- **Problem:** Die Codes beschreiben den Zeitpunkt einer (organspezifischen) Tumorkonferenz. Für die Empfehlung eines
  Molekularen Tumorboards (OncologyPlan, molecularBoardDecisionDate) gibt es keinen passenden Code; die Beispiele des
  Pakets sind uneinheitlich (`CarePlan-mii-exa-mtb-kim-musterperson-therapieplan`: `praeth`,
  `CarePlan-mii-exa-mtb-therapieplan-kombinationstherapie`: `postth`). Wir setzen interimistisch `praeth` mit
  `text = "Molekulares Tumorboard"` (REPRESENTATIONS #42).
- **Evidenz:** CodeSystem `mii-cs-onko-therapieplanung-typ` 2027.0.0-ballot.1; Snapshot des Therapieplans; Beispiele s. o.
- **Vorschlag:** Code `mtb` („Molekulares Tumorboard") im CodeSystem ergänzen oder `category` im MTB-Profil auf einen
  eigenen Code fixieren; Beispiele angleichen.
- **Bezug:** Diff (Implementierung)

### MOLGEN-1 – `variante`: value[x]-Slicing ist nur im Snapshot geschlossen

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/variante`,
  `Observation.value[x]` (0..1). Im Snapshot ist `slicing.rules = closed`, einziger Slice ist `valueCodeableConcept`
  (required `http://loinc.org/vs/LL1971-2`).
- **Problem:** Das Differential definiert kein Slicing, und die Basis GR 3.0.0 `variant` ist offen. Geschlossen ist nur der
  ausgelieferte Snapshot, vermutlich ein Artefakt des IG Publishers. Validatoren arbeiten mit dem Snapshot, deshalb scheitert
  jeder Wert, der kein CodeableConcept ist. Das wird an die MTB-Profile `einfache-variante`, `copy-number-variant`,
  `dna-fusion`, `rna-fusion` und `rna-seq` vererbt; deren Differential deklariert das Slicing teils als offen. Betroffen sind
  alle Varianten-Observations aus OncologyMolecular.* und RareDiseasesMolecular.*.
- **Evidenz:** Das Differential enthält `Observation.value[x]` ohne `slicing`. Im Snapshot von 2026.0.4 ist das Slicing offen.
- **Vorschlag:** Klären, ob die Einschränkung beabsichtigt ist. Wenn ja, ins Differential aufnehmen; wenn nein, den Snapshot korrigieren.
- **Bezug:** Diff; 18, 25

### MOLGEN-2 – Beispiele verwenden eine abweichende SO-System-URI

- **Profil/Element:** MolGen-Beispiele, z. B. `Observation-mii-exa-molgen-variante-fgfr2-fusion` und
  `Observation-mii-exa-molgen-molekulare-konsequenz-brca1`. Betroffen sind die Werte von `component:coding-change-type`
  und `component:feature-consequence`.
- **Problem:** 14 Beispieldateien in molgen 2027.0.0-ballot.1 verwenden `http://sequenceontology.org`, GR-ValueSets und MTB
  dagegen `http://www.sequenceontology.org`. Wer die URI aus den Beispielen übernimmt, erzeugt Codings, die außerhalb der
  extensible ValueSets liegen. Betroffen sind OncologyMolecular.smallVariants[].variantTypes[] und .localization sowie die
  entsprechenden Felder in RareDiseasesMolecular.
- **Evidenz:** keine MolGen-Beispieldatei verwendet die www-Form.
- **Vorschlag:** Die Beispiele auf `http://www.sequenceontology.org` vereinheitlichen.
- **Bezug:** 11, 26

### MOLGEN-3 – Variantenlokalisation (Unterstützung von HDB-976)

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/mii-pr-molgen-molekulare-konsequenz`:
  - `Observation.component:feature-consequence` 0..*, nicht MS; `value[x]` 1..1, extensible GR `molecular-consequence-vs`
    (SO is-a SO:0001537),
  - `Observation.derivedFrom:variant` 0..*.
- **Problem:** Betroffen sind zwei Felder mit unterschiedlichen Wertelisten:
  - RareDiseasesMolecular.{small,copyNumber,structural}Variants[].localization[] mit codingRegion, splicingRegion,
    regulatoryRegion, intronic, intergenic,
  - OncologyMolecular.smallVariants[].localization mit coding, inRegulatoryElements, notInCodingAndNotInRegulatoryElements.

  Interimslösung: eine molekulare Konsequenz je Variante mit SO:0001580, SO:0001630, SO:0001566, SO:0001627 bzw. SO:0001628.
  Für `notInCodingAndNotInRegulatoryElements` gibt es keinen Einzelcode; die Abbildung auf SO:0001537 ist verlustbehaftet.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** HDB-976 unterstützen (Profil Variantenlokalisation mit ValueSet). Das ValueSet sollte beide Wertelisten
  des Datenkranzes abdecken, einschließlich eines Codes für „weder kodierend noch regulatorisch". Das Verhältnis zu
  `molekulare-konsequenz` klären.
- **Bezug:** 26

### MOLGEN-4 – Befundkategorie primär / Zufallsbefund / Kandidat (Unterstützung von HDB-976)

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/diagnostische-implikation`:
  - `Observation.component` (Slicing offen; Slices conclusion-string, evidence-level, clinical-significance,
    predicted-phenotype, mode-of-inheritance),
  - `Observation.extension:secondary-finding` 0..1 (core `observation-secondaryFinding`).
- **Problem:** RareDiseasesMolecular.{small,copyNumber,structural}Variants[].diagnosticSignificance (primary, incidental,
  candidate) hat keinen Code. `secondary-finding` gibt an, welche ACMG-SF-Leitlinie angewandt wurde, nicht die
  Befundkategorie. MolGen 2027 liefert kein CodeSystem. Interimslösung: eine unbenannte Komponente mit einem eigenen
  MV-GenomSeq-CodeSystem.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** HDB-976 unterstützen: ein MolGen-CodeSystem mit primary-finding, secondary-finding und candidate,
  verwendet als Komponenten-Slice auf `diagnostische-implikation`. Klären, ob der Datenkranz-Wert `incidental` einen
  Sekundärbefund (gezielt gesucht, ACMG SF) oder einen Zufallsbefund meint; im zweiten Fall braucht das CodeSystem einen
  eigenen Code `incidental-finding`.
- **Bezug:** 27

### MOLGEN-5 – Segregation `biparental` / `notPerformed` und Erbgang `unclear` (Unterstützung von HDB-976 c)

- **Profil/Element:**
  - `…/variante`, `Observation.component:variant-inheritance`: 0..1, `value[x]` 1..1, extensible `http://loinc.org/vs/LL5489-1`,
  - `…/diagnostische-implikation`, `Observation.component:mode-of-inheritance`: 0..1, `value[x]` 1..1, preferred
    GR `condition-inheritance-mode-vs` (HPO).
- **Problem:** Für RareDiseasesMolecular.{small,copyNumber,structural}Variants[].segregationAnalysis gilt:
  `fromMotherAndFather` hat keinen exakten Code, denn LA30680-5 „Parental" ist unspezifisch. `notPerformed` lässt sich wegen
  `value[x]` 1..1 nicht als `dataAbsentReason` darstellen. Das gleiche Problem hat .modeOfInheritance = `unclear`: Das
  HPO-ValueSet enthält kein Konzept „unbekannt". Beide 1..1 sind aus GR geerbt.
- **Evidenz:** LL5489-1 ist in keinem Paket enthalten; welche LA-Codes dazugehören, ist nicht verifiziert.
- **Vorschlag:** HDB-976 c unterstützen (Konzept `biparental`). Für „nicht durchgeführt" und „unklar" ein Muster
  dokumentieren, z. B. einen Code im MolGen-CS unter der extensible- bzw. preferred-Bindung. Alternativ gemeinsam mit
  HL7 Clinical Genomics `value[x]` 0..1 mit Invariante.
- **Bezug:** 28, 29

### MOLGEN-6 – ACMG-Evidenzkriterien haben kein Element

- **Profil/Element:** `…/diagnostische-implikation`. Es gibt keinen Slice für Kriterien, nur
  `component:clinical-significance` (53037-8, example LL4034-6).
- **Problem:** RareDiseasesMolecular.{small,copyNumber,structural}Variants[].acmgCriteria[].value (Pflicht, PVS1 … BP7) und
  .modifier (Stärke) haben in MolGen, Seltene und MTB 2027 kein Element. Damit verliert jede klassifizierte Variante ihre
  Begründung. `component:evidence-level` (93044-6) hat eine andere Bedeutung.
- **Evidenz:** Die Suche nach „acmg" findet in MolGen 2027, MTB 2027 und GR 3.0.0 kein SD, VS oder CS.
- **Vorschlag:** Einen Slice `component:acmg-criterion` 0..* auf `diagnostische-implikation` anlegen, mit valueCodeableConcept
  extensible an ein von MII benanntes CodeSystem für die Kriterien PVS1 … BP7 (ClinGen veröffentlicht die Kriterien in der
  SEPIO-CG-Terminologie, aber keine FHIR-System-URI). Die Stärke als Unterkomponente oder zweites Coding abbilden,
  einschließlich DNPM `bm`.
- **Bezug:** 30

### MOLGEN-7 – Studiendesign Single/Duo/Trio hat kein Konzept

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-molgen/StructureDefinition/anforderung-genetischer-test`
  (ServiceRequest; `subject` Patient oder Group, kein Design-Code) sowie `…/mii-pr-molgen-genomic-study` und
  `…/mii-pr-molgen-genomic-study-analysis`.
- **Problem:** RareDiseasesCase.priorRds[].genomicStudyType (single, duo, trio) hat kein Konzept, ebenso
  GRZ submission.genomicStudyType (derzeit nicht abgebildet). Weder MolGen und Seltene 2027 noch GR
  `genomic-study-method-type-cs` enthalten eines. Interimslösung: eine eigene MV-GenomSeq-Extension. Der DNPM-RD-Export
  setzt den Wert derzeit konstant auf `single` (nicht verifiziert für die aktuelle Version).
- **Evidenz:** siehe Problem.
- **Vorschlag:** Eine Extension `genomic-study-design` (singleton, duo, trio, other) an genomic-study bzw.
  genomic-study-analysis oder an der Anforderung einführen.
- **Bezug:** 31

### SE-1 – GMFCS (Unterstützung von HDB-975)

- **Profil/Element:** Im Paket gibt es kein Zielprofil. Das neue `…/modul-seltene/StructureDefinition/mii-pr-seltene-icf-assessment`
  passt nicht: `Observation.code` ist required an ICF gebunden und `Observation.value[x]` ist 0..0.
- **Problem:** RareDiseasesCase.diagnosisRd.diagnosisGmfcs und RareDiseasesFollowUp.followUpRds[].gmfcs (Stufe I–V)
  werden derzeit als generische Observation abgebildet. Der verbreitete LOINC-Code 62782-8 gilt nur für das Alter 6–12 Jahre.
- **Evidenz:** Die Suche nach „gmfcs" in allen Paketen findet nichts. Die vorgeschlagenen Codes gibt es laut unserem
  Terminologie-Check auf tx.fhir.org.
- **Vorschlag:** HDB-975 unterstützen: ein Observation-Profil GMFCS mit dem altersunabhängigen Code SNOMED 707621005 und
  Stufen aus LOINC LL1594-2 (LA16552-4, LA15151-6, LA15150-8, LA16556-5, LA16558-1) oder aus einem Modul-CS. Es sollte für
  Diagnose- und Verlaufszeitpunkt nutzbar sein (`effective[x]`).
- **Bezug:** 32

### SE-2 – Hospitalisierung: Dauer und Anzahl der Aufenthalte (Unterstützung von HDB-975)

- **Profil/Element:** Weder `mii-lm-seltene` noch die Profile haben ein Element dafür. Es gibt auch keine Seltene-Observation
  mit frei belegbarem valueCodeableConcept: `hpo-assessment` ist an HPO gebunden, `icf-assessment` hat keinen Wert.
- **Problem:** Es handelt sich um zwei verschiedene Bänder:
  - RareDiseasesCase.priorRds[].hospitalizationDuration in Tagen (none, upToFive, upToFifteen, upToFifty, moreThanFifty, unknown),
  - .hospitalizationPeriods als Zahl der Aufenthalte in 5 Jahren (none, upToFive, upToTen, upToFifteen, moreThanFifteen, unknown).
- **Evidenz:** siehe Profil/Element.
- **Vorschlag:** HDB-975 mit zwei getrennten ValueSets bzw. CodeSystems unterstützen, deren Codes 1:1 den Literalen des
  Datenkranzes entsprechen. Bis dahin verwenden wir zwei lokale CodeSystems.
- **Bezug:** 33

### SE-3 – Therapiestrategie `other` für medikamentöse Empfehlungen; Kombination

- **Profil/Element:**
  - `https://www.medizininformatik-initiative.de/fhir/ext/modul-seltene/StructureDefinition/mii-pr-seltene-therapieempfehlung`,
    `MedicationRequest.category:MVGenomSeqTherapieStrategie` (0..1, required `…/ValueSet/mii-vs-seltene-therapieempfehlung-strategie-medikamentoes`
    = systemic-medication, targeted-medication, prevention-medication, gene-therapy, combination),
  - `…-nicht-medikamentoes` = prophylactic, early-detection, nutrition, other,
  - `mii-pr-seltene-therapieempfehlung-kombination` hat keinen Strategie-Slice.
- **Problem:** RareDiseasesPlan.recommendedTherapies[].strategy entspricht 1:1 dem CS. Eine medikamentöse Empfehlung mit
  `other` kann ihre Strategie aber nicht tragen; es bleibt nur das Weglassen. Für `combination` gibt es am RequestGroup keinen Slice.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** `other` in das medikamentöse ValueSet aufnehmen oder beide Slices an das vollständige
  `mii-vs-seltene-therapieempfehlung-strategie` binden. Einen Strategie-Slice auf `-kombination` anlegen.
- **Bezug:** 34

### CONSENT-1 – Die Einwilligungsbereiche des MV-GenomSeq lassen sich nicht codieren

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung`,
  `Consent.provision.provision.code` (1..*, required `https://www.medizininformatik-initiative.de/fhir/modul-consent/ValueSet/mii-vs-consent-policy`,
  umfasst das gesamte CS `urn:oid:2.16.840.1.113883.3.1937.777.24.5.3`).
- **Problem:** Submission.mvConsent.scope[].domain (KDK Onkologie und Seltene) und GRZ donors[].mvConsent.scope[].domain
  (mvSequencing, reIdentification, caseIdentification) haben im Policy-CS (124 Konzepte) keinen Code. Die vorhandenen Codes
  …24.5.3.2 (IDAT erheben), .6 (MDAT erheben) und .8 (MDAT wissenschaftlich nutzen) gehören zum Broad Consent und bedeuten
  etwas anderes. Jede MV-Teilnahmeerklärung scheitert daher am required-Binding.
- **Evidenz:** Version des CS ist 2027.0.0-ballot. Eine Volltextsuche nach „genom", „Modellvorhaben" und „sequenzier" findet nichts.
- **Vorschlag:** Drei Policy-Codes für das MV-GenomSeq in einer eigenen Top-Level-Gruppe unter `…24.5.3` registrieren.
  Für die MV-Teilnahmeerklärung einen Eintrag in `mii-cs-consent-version-modules` und die zugehörige `policy.uri` festlegen.
  Zuständigkeit (AG Consent / TMF) und Zeitplan benennen.
- **Bezug:** 35

# Anhang B – Begriffe

| Begriff | Bedeutung |
|:--|:--|
| Datenkranz | Die JSON-Meldung an das BfArM im Modellvorhaben; drei Schemata: KDK Onkologie, KDK Seltene Erkrankungen (klinische Daten), GRZ (Genomrechenzentrum, Sequenzierdaten) |
| KDK, GRZ | Klinischer Datenknoten, Genomrechenzentrum: die zwei Meldewege und ihre Schemata |
| DNPM | Das Datenmodell der DNPM-Knoten, aus dem die KDK-Meldung erzeugt wird; Quelle vieler Enum-Werte (z. B. `bm` = benign moderate, `from-both-parents`) |
| GR | HL7 `hl7.fhir.uv.genomics-reporting` 3.0.0, die Basis der MTB- und MolGen-Variantenprofile |
| Interimslösung | Eine eigene Extension, ein eigenes CodeSystem oder Profil in unserem Paket `de.genomde.mvgs` (Canonical `https://genomde.de/fhir/…`), nur dort, wo der Ballot kein konformes Element hat; wird ersetzt, sobald MII ein Element bereitstellt |
| Unsere Umsetzung | Der Konverter `genomde2fhir` und die gleichwertigen FML-Maps; beide erzeugen dieselben Bundles |
| Validierungsserver | matchbox 4.1.21 mit den 2027-Ballot-Paketen; Codes prüft er gegen den HL7-Terminologieserver tx.fhir.org, der deutsche Systeme (BfArM, ICD-O-3-Ausgaben) nicht kennt |
| MAPPED, DRAFT | Bearbeitungsstand einer Zeile unserer Mapping-Tabelle, kein Konformitätsstatus |
| Umkehrsuche | Zu einem gelieferten SNOMED-Code den UICC-Ausgangscode in der veröffentlichten Map UICC → SNOMED suchen |
| MTB-n, ONKO-n, MOLGEN-n, SE-n, CONSENT-n | Unsere Entwürfe für Ballot-Kommentare (Anhang A) |
| HDB-975, HDB-976 | Ihre eingereichten Ballot-Tickets (Seltene: GMFCS, Hospitalisierung; MolGen: Lokalisation, Befundkategorie, biparental) |
| „Ihre Tabelle“ | `DRAFT-Mapping-Table-genomDE-DK-2026-10-06-TD-final.xlsx`, Zeilennummern je Tab |

# Anhang C – Beispiele aus unserer Ausgabe

Gekürzte Ressourcen, wie unsere Umsetzung sie erzeugt (Profilset 2027).

**Frage 1: MV-Einwilligung (eigenes Profil `mvgs-consent`)**

```json
{"resourceType": "Consent",
 "meta": {"profile": ["https://genomde.de/fhir/StructureDefinition/mvgs-consent"]},
 "status": "active",
 "scope": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "patient-privacy"}]},
 "category": [{"coding": [{"system": "http://loinc.org", "code": "57016-8"}]}],
 "patient": {"reference": "urn:uuid:…"},
 "provision": {"provision": [
   {"type": "permit", "period": {"start": "2025-03-01"},
    "code": [{"coding": [{"system": "https://genomde.de/fhir/CodeSystem/mvgs-cs-mv-consent-domain", "code": "mvSequencing"}]}]},
   {"type": "deny", "period": {"start": "2025-03-01"},
    "code": [{"coding": [{"system": "https://genomde.de/fhir/CodeSystem/mvgs-cs-mv-consent-domain", "code": "reIdentification"}]}]}]}}
```

**Frage 2: HGVS-Komponenten (Transkript NM_004985.5, KDK „c.34G>T“ / „p.G12C“)**

```json
{"code": {"coding": [{"system": "http://loinc.org", "code": "48004-6"}]},
 "valueCodeableConcept": {"coding": [{"system": "http://varnomen.hgvs.org", "code": "NM_004985.5:c.34G>T"}],
                          "text": "c.34G>T"}}
{"code": {"coding": [{"system": "http://loinc.org", "code": "48005-3"}]},
 "valueCodeableConcept": {"coding": [{"system": "http://varnomen.hgvs.org", "code": "NM_004985.5(KRAS):p.G12C"}],
                          "text": "p.G12C"}}
```

**Frage 12: Evidenzgraduierung an der Studienempfehlung (eigene Extension, ein CodeableConcept mit Evidenzgrad
und Zusatzverweisen)**

```json
{"url": "https://genomde.de/fhir/StructureDefinition/mvgs-ex-evidence-level",
 "valueCodeableConcept": {"coding": [
   {"system": "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/CodeSystem/mii-cs-mtb-empfehlung-evidenzgrad", "code": "m2A"},
   {"system": "https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/CodeSystem/mii-cs-mtb-empfehlung-evidenzgrad-zusatzverweis", "code": "Z"}]}}
```

**Frage 15: ACMG-Kriterium als ungeslicte Komponente an `diagnostische-implikation` (Kriterien-URI selbst gewählt, siehe Frage 15)**

```json
{"code": {"coding": [{"system": "https://clinicalgenome.org/codesystem/acmg-criteria", "code": "PM2"}]},
 "valueCodeableConcept": {"coding": [{"system": "https://genomde.de/fhir/CodeSystem/mvgs-cs-rd-acmg-strength", "code": "pm"}]}}
```

# Anhang D – Dokumente

Alle im öffentlichen Repository <https://github.com/KohlbacherLab/genomDE2FHIR> (Release v0.11.0, Stand `main`):

- `docs/QUESTIONS-TD-2026-10-31.md` (+ `.docx`) – dieses Dokument.
- `docs/BALLOT-COMMENTS-2027.md` – alle 46 Entwürfe für Ballot-Kommentare.
- `docs/DISCUSS-TD-2026-10-09.md` – unsere Diskussion Ihrer Anmerkungen; Quelle der „Bezug“-Nummern.
- `docs/ISSUES-TD-2026-10-09.md` – unsere Analyse Ihrer Tabelle vom 09.10. (englisch; Stand vor vier Korrekturrunden).
- `docs/REPRESENTATIONS.md` – Register der Interimslösungen mit Begründung.
- `docs/IDENTITY.md` – Identität, Verknüpfung und Korrekturen (Frage 31).
- `docs/LEITFADEN-TD-2026-10-16.md` – Einstieg in Code und Dokumente.
- `mapping/mapping_*.csv` – die Mapping-Tabelle, Stand nach Ihren Anmerkungen.
- `mvgs-ig/input/` – die Definitionen unserer Interimslösungen (Profile, Extensions, CodeSystems).
