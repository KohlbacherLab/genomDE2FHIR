---
title: "MV-GenomSeq → MII KDS: Rückfragen zur Mapping-Tabelle"
date: "10. Oktober 2026"
lang: de
geometry: margin=2cm
fontsize: 10pt
colorlinks: true
header-includes:
  - \usepackage{xurl}
  - \renewcommand{\texttt}[1]{{\urlstyle{tt}\nolinkurl{#1}}}
---

Nachfolgend stehen, jeweils als Frage formuliert, alle Punkte, in denen unser implementiertes Mapping (Konverter genomde2fhir, Ziel MII KDS 2027.0.0-Ballot) von Ihrer annotierten Tabelle vom 06.10.2026 abweicht oder noch offen ist.
Zeilennummern sind die Excel-Zeilen Ihrer Tabs KDK oncology, KDK rare diseases, GRZ und Open Issues.
Kennungen wie MTB-10 verweisen auf unsere Entwürfe für Ballot-Kommentare zu 2027 (noch nicht eingereicht).

## A. Einwilligung (alle drei Datensätze)

**1. Ist unsere Interimslösung für die MV-Einwilligung akzeptabel, bis Policy-Codes für das MV-GenomSeq registriert sind? Wer registriert sie (eigene Gruppe unter `2.16.840.1.113883.3.1937.777.24.5.3` oder separates CodeSystem), bis wann, und mit welcher policy.uri für die MV-Teilnahmeerklärung?**\
*Ihre Tabelle:* KDK oncology 112; KDK rare diseases 46; GRZ 49; Open Issues 27, 63, 82. Das Policy-CodeSystem ist 2027 unverändert, die OIDs …24.5.3.2/.6/.8 existieren in keiner Version, und die MV-Domänen sind ein Ballot-Kandidat für das Modul Consent.\
*Wir derzeit:* Die OIDs .2/.6/.8 existieren in 2025.0.1, 2026.0.0 und 2027.0.0-ballot als Kinder von .1 (IDAT erheben, MDAT erheben, MDAT wissenschaftlich nutzen; Ihre 29 sind die Top-Level-Konzepte von 124) und bezeichnen Broad-Consent-Zwecke, daher verwenden wir sie nicht mehr. Stattdessen erzeugen wir ein lokales Profil mvgs-consent auf Basis von Consent mit den lokalen Codes mvSequencing / reIdentification / caseIdentification, bewusst nicht konform zu mii-pr-consent-einwilligung, dessen provision.provision.code required gebunden ist (CONSENT-1).

## B. Variantennomenklatur und Identifikatoren (MTB, MolGen)

**2. Darf coding.code den mit dem Transkript qualifizierten HGVS-Ausdruck tragen („NM_004985.5:c.34G>T“, im ClinVar-Stil „NM_004985.5(KRAS):p.Gly12Cys“), mit der KDK-Zeichenkette in text, und ist diese Qualifizierung Aufgabe des Senders? Was soll ohne verwendbares Transkript geschehen: unqualifizierte Zeichenkette senden, Komponente weglassen oder bei BfArM ein Pflicht-Transkript (und eine Protein-Accession) anregen?**\
*Ihre Tabelle:* KDK oncology 43, 48; Open Issues 7, 12. dnaChange und proteinChange gehen unverändert in coding.code von representative-coding-hgvs bzw. representative-protein-hgvs (system varnomen).\
*Wir derzeit:* Gleiche Slices und gleiches System; da tx.fhir.org die required-Bindung an hgvs-vs prüft (unqualifiziertes „c.34G>T“ oder „p.V600E“ wird abgelehnt, die qualifizierten Formen werden akzeptiert), qualifizieren wir, sobald ein versioniertes Transkript vorliegt, und behalten die KDK-Zeichenkette in text. Ohne Transkript (bei Vorbefunden im KDK optional, in der Praxis fehlend) und bei p. mit Ensembl-Transkript (ohne ENSP-/NP-Accession keine gültige Form) geht die Zeichenkette wie in Ihrer Tabelle unverändert hinaus und besteht die Validierung nicht.

**3. Ist die required-Bindung von representative-transcript-ref-seq an `http://ensembl.org` beabsichtigt, obwohl dies kein ValueSet ist, das MTB-eigene Beispiel RefSeq verwendet und MolGen denselben Slice nur example bindet (MTB-2)? Welche System-URIs sollen Ensembl- und RefSeq-Transkripte tragen?**\
*Ihre Tabelle:* KDK oncology 49, 51; Open Issues 13 (in KDK oncology 169–172 nur die Korrektur des Komponentennamens). MTB bindet den Wert required an `http://ensembl.org`, daher müssten RefSeq-Transkripte (NM\_) übersetzt oder im Ballot adressiert werden.\
*Wir derzeit:* Wir folgen Ihrer Ballot-Option und übernehmen Transkripte unverändert (ein versionsgenaues NM\_/ENST-Paar gibt es nur für MANE-Transkripte); das System setzen wir nach Accession-Präfix auf `http://www.ensembl.org` bzw. `http://www.ncbi.nlm.nih.gov/refseq`. Die Quellen widersprechen sich: Die Bindung nennt `http://ensembl.org`, das MTB-Beispiel `https://www.ncbi.nlm.nih.gov/refseq/`, DNPM liefert `https://www.ensembl.org`, und kein MII- oder HL7-Paket definiert eine Ensembl-URI.

**4. Welche System-URI der Sequence Ontology ist maßgeblich: `http://www.sequenceontology.org` (GR dna-change-type-vs, MTB-Beispiele) oder `http://sequenceontology.org` (MolGen-Beispiele und logisches Modell)?**\
*Ihre Tabelle:* KDK oncology 55. Das gelieferte variantTypes-Coding 1:1 übernehmen, SO bevorzugt.\
*Wir derzeit:* Wir übernehmen code, display und version 1:1, schreiben jedes SO-System aber in der www-Form des GR-ValueSets, an das der Slice gebunden ist (fehlt bei Vorbefunden das System, setzen wir SO). MOLGEN-2 bittet um Angleichung der MolGen-Beispiele.

## C. Onkologie: Diagnose und Staging

**5. coding:uicc ist in den T/N/M-Profilen 2027 1..1, der KDK liefert aber nur SNOMED: Ist die Ableitung über eine lokal gepflegte Umkehrung der MII-ConceptMaps UICC→SNOMED der vorgesehene Weg, und wer pflegt sie? Wird ONKO-5 (coding:uicc 0..1, wenn coding:snomed-ct vorhanden ist) angenommen?**\
*Ihre Tabelle:* KDK oncology 32. TNM nach dem Onko-Modell 2027: SNOMED-gebundener Typ, T/N/M-Kategorien über hasMember (nicht component) mit UICC- und SNOMED-Wert-Slices, Profil- und VS-Namen von 2027.\
*Wir derzeit:* Wir folgen diesem Modell (Gruppierungscode 399537006 / 399588009, bei gemischten c/p-Präfixen 399390009; kein Stadium als value, da der KDK keines liefert) und leiten coding:uicc über unsere Umkehr-Map ab (nur T/N/M), 2027 ergänzt um coding:snomed-ct. MII veröffentlicht nur Maps UICC→SNOMED, die nicht jeden Code abdecken; nicht zuordenbare Einträge gehen nach weitere-klassifikationen mit code.text „TNM“.

**6. Werden in 2027 final ECOG 5 und ein explizites „nicht anwendbar“ in mii-cs-onko-allgemeiner-leistungszustand-ecog aufgenommen (samt ConceptMap-Zeile 5 → LA9627-6), oder soll ONKO-4 eine Lockerung von coding:obds (1..1) fordern?**\
*Ihre Tabelle:* KDK oncology 10, 76. Der LOINC-Slice ist in Onko 2027 vorhanden, das CS kennt aber weiterhin nur 0–4 und U, daher sind 5 und notApplicable ein Ballot-Kandidat Onko.\
*Wir derzeit:* 0–4 gehen nach coding:obds plus coding:loinc (LA9622-7 bis LA9626-8), unknown nach obds U, da dataAbsentReason neben dem Pflichtwert ungültig ist; 5 und notApplicable erzeugen keine Observation und werden als verworfen gemeldet. Das LOINC-ValueSet 2027 enthält LA9627-6 bereits, coding:obds 1..1 verhindert aber ein reines LOINC-Coding.

**7. Stimmen Sie zu, dass ein metachroner Tumor über occurredFollowing (zeitliche Abfolge) und nicht über dueTo (therapieassoziierte Sekundärmalignome) mit der Erstdiagnose verknüpft wird? Soll das Ja/Nein-Kennzeichen metachroneDiagnoses ein eigenes Onko-Element erhalten (ONKO-7)?**\
*Ihre Tabelle:* KDK oncology 79; Open Issues 22. Bestätigt als weitere Condition nach diagnose-primaertumor, mit der neuen Pflicht-Kategorie 55342001 und dueTo für den Zusammenhang zur Erstdiagnose.\
*Wir derzeit:* metachroneDiagnoses ist ein Boolean, die Tumoren kommen in additionalDiagnoses[]; diese erzeugen wir wie vorgeschlagen als diagnose-primaertumor mit Kategorie 55342001 und verknüpfen sie 2027 über occurredFollowing (Profil: „zeitliche Abfolge“, dueTo dagegen „therapieassoziierte Sekundärmalignome“). Das Kennzeichen wird aus diesen Verknüpfungen abgeleitet, wenn alle Diagnosen verknüpft sind; sonst (und 2026) bleibt es in einer lokalen Extension am Follow-up-Verlauf.

**8. Bestätigen Sie, dass tnmClassifications[].version das SNOMED-CT-Release ist (z. B. „2025-03-01“) und nicht die TNM-Auflage, und dass das mustSupport-Element Observation.method (TNM-Auflage) bei SNOMED-codiertem TNM leer bleiben darf? Soll ein Release-Datum in eine SNOMED-Versions-URI umgesetzt oder verworfen werden?**\
*Ihre Tabelle:* KDK oncology 36. Nur Ihre allgemeine Anmerkung zu TNM 2027, nichts speziell zu version.\
*Wir derzeit:* Wir übernehmen version (2027) in coding:snomed-ct.version nur, wenn es eine SNOMED-Versions-URI ist; in unseren Daten ist es immer ein Release-Datum und wird verworfen. Der aktuelle KDK hat kein Feld für die TNM-Auflage, daher setzen wir Observation.method nur bei nicht schemakonformen UICC-Zeichenketten mit expliziter Auflagennummer.

**9. Stimmen Sie zu, dass DNPM-Einträge zur Tumorausbreitung nach mii-pr-mtb-tumorausbreitung (datiert mit dem Datum der Hauptdiagnose) statt nach weitere-klassifikationen gehen? Ist für alle übrigen Systeme reiner Text akzeptabel, oder sollen bekannte Systeme (FIGO, Ann Arbor, Binet, …) aus mii-vs-onko-weitere-klassifikationen und -auspraegungen codiert werden?**\
*Ihre Tabelle:* KDK oncology 2, 3; Open Issues 2, 3. mii-pr-onko-weitere-klassifikationen mit den preferred-Bindungen für code und value verwenden, Status MAPPED.\
*Wir derzeit:* Je Eintrag eine weitere-klassifikationen-Observation mit code.text = System und value.text = key ohne Codings, da das KDK-System eine freie Zeichenkette ist und die Systeme in unseren Daten („TNM“, das DNPM-System zur Tumorausbreitung) im ValueSet keinen Code haben. Einträge mit System dnpm-dip/mtb/diagnosis/kds-tumor-spread und bekanntem key werden stattdessen zu mii-pr-mtb-tumorausbreitung mit SNOMED-Wert, verknüpft über Condition.stage:ErstdiagnoseZeitpunkt des Primärtumors.

## D. MTB: Therapieplan und Follow-up

**10. Stimmen Sie zu, dass therapyResponseSource die Datenquelle der Response ist (z. B. Arztbrief, Tumordokumentation) und nicht die Beurteilungsmethode? Würde MTB response-befund.method auf 0..1 lockern (oder other/unknown ergänzen) und einen Platz für die Datenquelle definieren (MTB-12)? Genügt coding:MTB für den Wert, oder muss coding:oBDS hinzukommen?**\
*Ihre Tabelle:* KDK oncology 100; Open Issues 26. Ziel mii-pr-mtb-response-befund.method (RECIST, RANO), value gebunden an mii-vs-onko-verlauf-gesamtbeurteilung, Enum-Abgleich nötig.\
*Wir derzeit:* Das method-Ziel stammte aus unserem eigenen früheren Entwurf und war falsch; genomDE liefert kein RECIST/RANO, daher validiert mit method 1..1 keine genomDE-Response gegen response-befund, und wir verwenden ein lokales Response-Profil auf Basis von Observation mit der Quelle in note. Der Wert CR/PR/SD/PD geht 1:1 in den Slice coding:MTB.

**11. Ist procedure-causedBy → mii-pr-mtb-therapieempfehlung die vorgesehene Verknüpfung einer durchgeführten Therapie mit ihrer Empfehlung, sodass sich der Ballot-Punkt auf Therapien aus einer Studienempfehlung beschränkt (MTB-11)? Sollen wir zusätzlich basedOn:tumorkonferenz → Therapieplan setzen, wie im Beispiel 2027?**\
*Ihre Tabelle:* KDK oncology 90; Open Issues 25. Lücke: Procedure.basedOn zielt nur auf den CarePlan, eine direkte Referenz auf die Empfehlung wäre ein Ballot-Kandidat MTB.\
*Wir derzeit:* Wir setzen Procedure.extension:causedBy (0..1, MS seit mtb 2026.0.1, auch im Mapping des logischen MTB-Modells und im Beispiel 2027), bei einer Kombination auf deren erstes Mitglied, und 2027 zusätzlich MedicationStatement.basedOn:therapieempfehlung. Nur eine Therapie aus einer Studienempfehlung (ServiceRequest) hat kein konformes Ziel und geht nach Procedure.note.

**12. Wird MTB ServiceRequest in den Kontext von mii-ex-mtb-empfehlung-evidenzgraduierung aufnehmen und an studieneinschluss-anfrage slicen (MTB-13)? Ist bis dahin unsere lokale Extension mit denselben MII-CodeSystemen akzeptabel? Soll Z(FDA) einen eigenen Zusatzverweis-Code erhalten?**\
*Ihre Tabelle:* KDK oncology 206, 207; Open Issues 49, 50. Die Extension ist an mii-pr-mtb-therapieempfehlung bestätigt, Status MAPPED vorgeschlagen (das ResearchStudy-Ziel in diesen Zeilen war unser eigener früherer Fehler).\
*Wir derzeit:* Studienempfehlungen sind mii-pr-mtb-studieneinschluss-anfrage (ServiceRequest), die der Kontext der Extension (RequestGroup, MedicationRequest, Observation) ebenso ausschließt wie ResearchStudy; daher tragen wir die Codings für Evidenzgrad und Zusatzverweis in einer lokalen ServiceRequest-Extension. Z(FDA) hat im Zusatzverweis-CS keinen Code; wir senden Z plus Text, auch in den Therapiezeilen (KDK oncology 220).

**13. Soll der Ballot-Slice für den Therapietyp an Empfehlungen an mii-vs-onko-systemische-therapie-art (Ihr Vorschlag) oder an mii-vs-onko-therapieempfehlung-typ binden (wie bereits RequestGroup.code von -kombination)? Dürfen wir ihn am Onko-Basisprofil mii-pr-onko-therapieempfehlung-medikation einreichen, sodass MTB ihn erbt (ONKO-6)?**\
*Ihre Tabelle:* KDK oncology 228; Open Issues 55. Die Werte sind die oBDS-Therapieart, MTB soll category oder eine Extension an mii-vs-onko-systemische-therapie-art binden.\
*Wir derzeit:* Übergangsweise geht der Code aus mii-cs-onko-therapie-typ in das nur example-gebundene MedicationRequest.category, bei Kombinationen zusätzlich in RequestGroup.code. Alle KDK-Codes sind in beiden ValueSets enthalten; die Wahl entscheidet nur, ob auch OP, ST und KW zulässig sind.

**14. Welchen Weg soll MTB-14 nehmen: (A) compassionate use, sekundärpräventiv und unbekannt in mii-cs-mtb-zulassungsstatus ergänzen und mii-ex-mtb-leitlinie-dokumentation an die Therapieempfehlung slicen, oder (B) eine eigene Extension für den Empfehlungstyp wie EmpfehlungTyp im logischen Modell? Soll „unbekannt“ überhaupt ein Code sein?**\
*Ihre Tabelle:* KDK oncology 229; Open Issues 56. mii-cs-mtb-zulassungsstatus ist nur an mii-ex-mtb-leitlinie-dokumentation gebunden, und es fehlen compassionateUse, secPreventive und unknown, also Ballot-Kandidat MTB.\
*Wir derzeit:* Wir stimmen zu; übergangsweise setzen wir an jedem MedicationRequest (und an der RequestGroup einer Kombination) eine lokale Extension mit inLabel / offLabel / compassionateUse / secPreventive und lassen „unknown“ weg.

## E. MolGen: Varianteninterpretation bei Seltenen Erkrankungen

**15. Ist eine ungeslicte Komponente je ACMG-Kriterium an diagnostische-implikation akzeptabel, bis MolGen einen Slice definiert (code aus ClinGen acmg-criteria PVS1 bis BP7, value = Stärke aus einem lokalen CodeSystem einschließlich der DNPM-Stufe „bm“)? Gehört das in HDB-976 oder in einen eigenen Kommentar (MOLGEN-6), mit dem ClinGen-CodeSystem oder einem Modul-CodeSystem?**\
*Ihre Tabelle:* KDK rare diseases 62, 63, 81, 82, 101, 102. Nur die allgemeine Korrektur, dass MolGen ein einziges generisches Profil variante hat; die Zeilen behalten unser altes Ziel Observation(acmg-criterion) als MAPPED.\
*Wir derzeit:* Kein MII-Modul und kein GR-3.0.0-Artefakt hat ein Element für ACMG-Kriterien, dieses Ziel existiert also nicht; wir legen die Kriterien neben clinical-significance an diagnostische-implikation ab (gültig, da deren Komponenten-Slicing offen ist) und haben die Zeilen auf DRAFT gesetzt. Soweit wir wissen, umfasst HDB-976 Lokalisation, Befundkategorie und biparental, aber keine ACMG-Kriterien.

**16. Da variant-inheritance.value[x] 1..1 ist (aus GR geerbt): Wie soll segregationAnalysis „notPerformed“ dargestellt werden – Komponente weglassen, LA4489-6 „Unknown“ plus dataAbsentReason not-performed oder ein Modul-Code (z. B. mit HDB-976 c)? Bedeutet fromMotherAndFather je ein Allel von jedem Elternteil?**\
*Ihre Tabelle:* KDK rare diseases 76, 97, 114; Open Issues 67, 71, 75. variante.component:variant-inheritance mit den LA-Codes, eigener Code „biparental“ (HDB-976 c) und notPerformed → dataAbsentReason=not-performed.\
*Wir derzeit:* Für deNovo, fromFather, fromMother und biparental (lokaler Code bis HDB-976 c) folgen wir Ihnen; eine Komponente nur mit dataAbsentReason besteht die Validierung aber nicht, daher lassen wir sie bei notPerformed weg und melden den Wert als verworfen. „Unknown“ plus dataAbsentReason würde validieren, da obs-6 nur auf Observation-Ebene gilt.

**17. modeOfInheritance „unclear“ hat kein HPO-Konzept, und value[x] ist 1..1: Ist ein reiner Textwert akzeptabel, oder soll MolGen einen Code ergänzen bzw. value[x] lockern (MOLGEN-5)? Welches MTB-Element meinten Sie für die LOINC-LA-Codes?**\
*Ihre Tabelle:* KDK rare diseases 73, 93, 111. Ziel diagnostische-implikation.component:mode-of-inheritance mit HPO; die LOINC-LA-Codes gelten nur für das MTB-Pendant.\
*Wir derzeit:* Ziel und HPO-Codes sind übernommen; „unclear“ deckt Ihre Anmerkung nicht ab, und die dort noch genannte dataAbsentReason schließt value[x] 1..1 aus, daher senden wir nur valueCodeableConcept.text. mii-pr-mtb-diagnostische-implikation hat dieselbe preferred-Bindung an HPO, und 79742-3 / LL3731-8 kommen in keinem MII- oder GR-Paket vor, daher verwenden wir nirgends LA-Codes.

**18. Können Sie uns Canonical und Code-Definitionen von HDB-976 zukommen lassen? Soll KDK „incidental“ zu „secondary-finding“ werden (ACMG unterscheidet aktiv gesuchte Sekundärbefunde von unerwarteten Zufallsbefunden), und sollen Zufallsbefunde zusätzlich observation-secondaryFinding setzen, obwohl die Version der ACMG-SF-Liste nicht übermittelt wird?**\
*Ihre Tabelle:* KDK rare diseases 66, 86, 105; Open Issues 64, 68, 72. Komponente „Befundkategorie“ an diagnostische-implikation mit übergangsweise eigenem MVGS-Code bis HDB-976 {primary-finding, secondary-finding, candidate}, Observation.note nur als Notlösung.\
*Wir derzeit:* Umgesetzt wie von Ihnen geplant, mit den lokalen Codes primary / incidental / candidate (die KDK-Literale), ohne note und ohne secondaryFinding-Extension; nach Annahme von HDB-976 stellen wir 1:1 auf dessen Codes um.

## F. MTB: Vorbefunde

**19. complexVariants ist ein untypisiertes Freitext-Array, das sich nicht CopyNumberVariant / DNAFusion / RNAFusion zuordnen lässt: Welchen Träger bevorzugen Sie – (a) ngs-bericht.conclusion (idealerweise MS), (b) je Eintrag eine Variante nur mit component:conclusion-string oder (c) einen neuen Freitext-Slice in result (MTB-10)? Ist ngs-bericht noch der richtige Container, wenn das logische MTB-Modell 2027 priorDiagnosticReports auf mii-pr-mtb-molecular-pathology-report abbildet?**\
*Ihre Tabelle:* KDK oncology 41; Open Issues 5. Container ngs-bericht über behandlungsepisode.supportingInfo:Vorbefund, complexVariants je nach Typ in die typisierten result-Slices, vorbehaltlich einer Prüfung der KDK-Feldstruktur.\
*Wir derzeit:* Wir verwenden Ihren Container; die Prüfung ergibt ein einfaches string[] ohne Typ, und Fusionen bräuchten zudem strukturierte Partner-Komponenten, daher wird jeder Eintrag eine Zeile in ngs-bericht.conclusion (0..1, nicht MS).

**20. Da das required gebundene method-type-ValueSet auch das gesamte GR-CodeSystem genomic-study-method-type umfasst: Stimmen Sie zu, dass sich der Ballot-Punkt zu den Untersuchungsarten der Vorbefunde (MTB-10) auf Einzelgen-Tests und Kurz- vs. Langread beschränkt? Würde ein GR-Code wie targeted-variant-analysis vorerst für „single“ genügen?**\
*Ihre Tabelle:* KDK oncology 57; Open Issues 21. Der Typ gehört an genomic-study-analysis extension:method-type (exome, genome, panel abgebildet, Read-Länge geht verloren), für single, array, karyotyping, other und none gibt es kein Konzept.\
*Wir derzeit:* Ihre drei Zuordnungen sind übernommen, array / karyotyping / other erhalten die GR-Codes microarray / karyotyping / other; „single“ hat keinen method-Code, und „none“ erzeugt keine genomic study. Der genaue KDK-Typ einschließlich Kurz-/Langread bleibt als lokaler Code in Procedure.code der genomic study (example-Bindung) erhalten.

## G. GRZ: Sequenzier-QC

**21. Stimmen Sie zu, dass qc.sequencing-coverage wie in GR genomic-study-analysis-metrics der prozentuale Anteil sequenzierter Zielregionen ist, sodass der Schwellenwert für die Mindestabdeckung eine eigene Sub-Extension braucht (MTB-19)?**\
*Ihre Tabelle:* GRZ 30; Open Issues 77. minCoverage → qc.sequencing-coverage (für MolGen analog in der GR-Extension metrics).\
*Wir derzeit:* sequencing-coverage (0..1) trägt bereits targetedRegionsAboveMinCoverage (×100, %), das auch Ihre Tabelle dorthin abbildet (GRZ 35); minCoverage, ein Schwellenwert der Lesetiefe, geht als z. B. „minCoverage=20x“ in metrics-description. Die MTB-Sub-Extensions haben keine eigenen Definitionen (MTB-3).

**22. Welches CodeSystem soll MTB an qc.sequencing-read-type binden? Wird der Kontext der qc-Extension korrigiert (in 2026.0.1 und im Ballot 2027 als Extension statt Procedure deklariert), und darf sie auch im MolGen-Pfad verwendet werden, wo GR metrics keinen Platz für den Read-Typ hat (MTB-3)?**\
*Ihre Tabelle:* GRZ 40; Open Issues 81. sequencingLayout → qc.sequencing-read-type an mii-pr-mtb-genomic-study-analysis (für MolGen analog in der GR-Extension metrics).\
*Wir derzeit:* Im MTB-Pfad setzen wir ein lokales Coding (single-end / paired-end / reverse), da der Slot keine Bindung hat; matchbox lehnt die Extension an der Procedure wegen des deklarierten Kontexts ab. Im MolGen-Pfad geht das Layout nur als Text in metrics-description.

## H. MTB: weitere molekulare Befunde

**23. Ist unsere Interimslösung für das Expressionsniveau (LL1971-2 Present/Absent plus Observation.interpretation H / N / L) bis MTB-15 akzeptabel? Würde MTB lieber eine gebundene Komponente für das Expressionsniveau ergänzen oder interpretation binden und als MS kennzeichnen?**\
*Ihre Tabelle:* KDK oncology 144; Open Issues 30. rna-seq hat keinen Platz für noExpression/normal/high/low, also Ballot-Kandidat MTB.\
*Wir derzeit:* noExpression → Absent (LA9634-2), normal / high / low → Present (LA9633-4) mit interpretation N / H / L; das erhält alle vier Stufen und validiert (interpretation ist extensible an das Basis-ValueSet gebunden). interpretation ist allerdings nicht MS, Empfänger können es also ignorieren.

**24. Ist LOH als ungeslicte Komponente an der einfachen Variante (lokaler Code loh, valueBoolean) statt einer separaten Biomarker-Observation mit derivedFrom akzeptabel? Soll die Ballot-Komponente (MTB-16) einen Boolean oder einen LOINC-Ja/Nein-Wert tragen?**\
*Ihre Tabelle:* KDK oncology 165; Open Issues 35. Ballot: Konzept „loh“ plus Komponente an einfache-variante; übergangsweise eine separate Biomarker-Observation mit derivedFrom auf die Variante.\
*Wir derzeit:* So bleibt das Kennzeichen an seiner Variante und ist heute gültig, da das Komponenten-Slicing von einfache-variante offen ist; die Form entspricht Ihrem Ballot-Ziel, nur mit lokalem Code.

**25. Wird MII das COSMIC-NamingSystem (URI `https://cancer.sanger.ac.uk/cosmic`, wie im MTB-Beispiel zur RNA-Fusion), das ValueSet ohne aufgezählten Inhalt und ein Biomarker-Konzept für Mutationssignaturen veröffentlichen, oder soll unsere Interimslösung im MV-GenomSeq-IG bleiben? Ist eine Observation je Signaturname so gemeint?**\
*Ihre Tabelle:* KDK oncology 152; Open Issues 32. NamingSystem für den COSMIC-Katalog plus ValueSet ohne Inhalt, Katalogversion in Coding.version, „SBS 6“ → „SBS6“, kein CodeSystem-Spiegel.\
*Wir derzeit:* Umgesetzt mit eigenem Interims-NamingSystem (mvgs-ns-cosmic) und lokalem Observation.code, da mii-vs-mtb-molekulare-biomarker kein Signatur-Konzept hat; das ValueSet haben wir nicht angelegt (MTB-17).

---

*Insgesamt haben wir 205 annotierte Zeilen geprüft: 140 übernehmen wir wie vorgeschlagen, die übrigen 65 führen zu den 25 Fragen oben (die Zeilenlisten nennen auch Zeilen mit derselben Anmerkung).*
