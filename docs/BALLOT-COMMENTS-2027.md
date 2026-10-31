# MII KDS 2027.0.0 – Ballot-Kommentare aus dem Projekt genomDE2FHIR (MV-GenomSeq)

*Entwurf vom 2026-10-09 zur Einreichung durch die Projektleitung. Noch nicht eingereicht.*

## Einleitung

- **Absender:** Projekt genomDE2FHIR – Abbildung des Datenkranzes des Modellvorhabens Genomsequenzierung
  (MV-GenomSeq: KDK Onkologie, KDK Seltene Erkrankungen, GRZ-Submission) auf die MII-KDS-Module.
  Einreichende Person: Projektleitung (Name und Einrichtung beim Einreichen ergänzen).
- **Gegenstand:** Ballot 2027.0.0, Pakete `de.medizininformatikinitiative.kerndatensatz.onkologie#2027.0.0-ballot.1`,
  `…mtb#2027.0.0-ballot.1`, `…molgen#2027.0.0-ballot.1`, `…seltene#2027.0.0-ballot`, `…consent#2027.0.0-ballot`,
  `…biobank#2027.0.0-ballot`.
- **Frist:** ca. **2026-10-27**. Abgeleitet aus der E-Mail von Thomas Debertshäuser (TD, BIH, MII-Modulverantwortlicher)
  vom 2026-10-06 („drei Wochen"). Das Datum ist nicht verifiziert und muss vor dem Einreichen bestätigt werden.
- **Bereits eingereicht:** TD hat am 2026-10-06 **HDB-975** (Modul Seltene: GMFCS, Hospitalisierungsbänder) und
  **HDB-976** (Modul MolGen: Variantenlokalisation, Befundkategorie, `biparental`) eingereicht. SE-1, SE-2 und
  MOLGEN-3 bis MOLGEN-5 **unterstützen** diese Tickets und ergänzen MV-GenomSeq-spezifische Details. Die Tickettexte
  lagen uns nicht vor (nicht verifiziert). Vor dem Einreichen abgleichen und die Punkte gegebenenfalls als Kommentar
  am bestehenden Ticket statt als neues Ticket einbringen.
- **Prüfung:** Element-IDs, Kardinalitäten und Bindings stammen aus den **Snapshots** der genannten Pakete und wurden
  am 2026-10-09 nachgeprüft. Nicht nachprüfbare Aussagen sind mit „(nicht verifiziert)" markiert.
- **Typ:** *Defekt* = Fehler oder Widerspruch in den Ballot-Artefakten. *Anforderung* = fehlende Ausdrucksmöglichkeit
  für ein Datenkranz-Feld. Unsere Interims-Darstellung bis zur Entscheidung steht in `docs/REPRESENTATIONS.md`.
- **Bezug:** Nummer des Punkts in `docs/DISCUSS-TD-2026-10-09.md` (Abstimmung mit TD am 2026-10-09). „Diff" heißt:
  nur im Paketvergleich 2026→2027 gefunden (`docs/2027-BALLOT-DIFF.md`).
- **Datenkranz-Felder** sind als JSON-Pfad der KDK-Schemata (`OncologyCase`, `OncologyPlan`, `OncologyFollowUp`,
  `OncologyMolecular`, `RareDiseases*`, `Submission`) bzw. des GRZ-Schemas (`GRZ donors[]…`) angegeben.

---

## Onkologie (`de.medizininformatikinitiative.kerndatensatz.onkologie#2027.0.0-ballot.1`)

### IG-Defekte

#### ONKO-1 – ConceptMap MV-GenomSeq: TNM-Zeilen zeigen auf ECOG, falsche Quell-URLs, leere Diagnose-Map

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

#### ONKO-2 – Logisches Modell MV-GenomSeq: falsches TNMSchluessel-Mapping, Blöcke ohne Mapping

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

#### ONKO-3 – HGNC-System zwischen den Modulen uneinheitlich

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

### Anforderungen

#### ONKO-4 – ECOG 5 und „nicht anwendbar" nicht darstellbar

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

#### ONKO-5 – TNM: UICC-Codierung ist Pflicht, der Datenkranz liefert SNOMED CT

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

#### ONKO-6 – Therapieart (therapeuticStrategy) an der Therapieempfehlung

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

#### ONKO-7 – Metachrone Tumoren: die Ja/Nein-Angabe hat kein Element

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

#### ONKO-8 – Erblicher Tumorfall: diagnostische Bewertung, präventive Maßnahmen, Zweck der Intervention

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

#### ONKO-9 – ICD-O-3-Topographie: required-Binding, Validierungsweg unklar

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

---

## MTB (`de.medizininformatikinitiative.kerndatensatz.mtb#2027.0.0-ballot.1`)

### IG-Defekte

#### MTB-1 – Therapieplan: Unter-Slices von `activity:extended` widersprechen dem Elternprofil

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

#### MTB-2 – Transkript-ID: required-Binding an `http://ensembl.org`, das kein ValueSet ist

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

#### MTB-3 – QC-Extension: Kontext „Extension" statt Procedure, keine Definitionen

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

#### MTB-4 – Biomarker-CodeSystem: Displays für Allel A und Allel B vertauscht

- **Profil/Element:** CodeSystem `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/CodeSystem/mii-cs-mtb-molekulare-biomarker`,
  Codes `copy-number-allele-a` und `copy-number-allele-b`. Sie sind die Pattern-Codes von
  `mii-pr-mtb-copy-number-variant.component:cna.code` bzw. `component:cnb.code`.
- **Problem:** `copy-number-allele-a` trägt das Display „Copy Number of Allele B" und umgekehrt. Displays erscheinen in
  Anzeigen und Exporten, sodass allelspezifische Kopienzahlen vertauscht dargestellt werden können. Ein direktes KDK-Feld
  gibt es nicht, der Fehler betrifft aber jede MII-CNV-Instanz mit `cna`/`cnb`.
- **Evidenz:** gleicher Stand in 2026.0.1 und 2027.
- **Vorschlag:** Die beiden Displays tauschen.
- **Bezug:** 23

#### MTB-5 – NCIt-System-URI ist die Webseite eines fremden IG

- **Profil/Element:**
  - `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-ploidie`,
    `Observation.code.coding:NCIT` (1..1, patternCoding system `https://nih-ncpi.github.io/ncpi-fhir-ig/CodeSystem-ncit.html`, Code C18303),
  - ebenso `…/mii-pr-mtb-hrd-score`, `Observation.component:LOH.code` (C18016).
- **Problem:** Als System ist eine HTML-Seite des NCPI-IG eingetragen statt der kanonischen NCIt-URI. Instanzen müssen diese
  URL übernehmen, damit sie validieren. Betroffen ist OncologyMolecular.complexBiomarkers[].ploidy. Außerdem hat
  `valueQuantity` keine festgelegte Einheit; das Beispiel enthält 2.4 ohne Einheit.
- **Evidenz:** siehe patternCoding oben.
- **Vorschlag:** Das kanonische NCIt-System `http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl` verwenden und UCUM `1`
  als Einheit für die Ploidie festlegen.
- **Bezug:** 23

#### MTB-6 – RNA-Seq: sechs Komponenten-Slices ohne festen Code

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-mtb/StructureDefinition/mii-pr-mtb-rna-seq`,
  `Observation.component:transcript-id`, `:transcripts-per-million`, `:tissue-corrected-expression`, `:raw-counts`,
  `:library-size` und `:cohort-ranking` (jeweils 0..1).
- **Problem:** Das Component-Slicing unterscheidet über `value:code`, die sechs Slices haben aber keinen festen Code.
  `mii-cs-mtb-molekulare-biomarker` enthält auch keine passenden Codes. Instanzen lassen sich diesen Slices deshalb nicht
  eindeutig zuordnen. Betroffen ist OncologyMolecular.expressionVariants[].
- **Evidenz:** `component:<slice>.code` ist 1..1, aber nur example-gebunden und ohne `pattern[x]`.
- **Vorschlag:** Für jeden Slice einen festen Code definieren, im MTB-Biomarker-CS oder über LOINC.
- **Bezug:** 18, 23

#### MTB-7 – CNV-Typ: CodeSystem undefiniert, Wert ungebunden

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

#### MTB-8 – Fusionen: Partner-Gen- und Positions-Slices uneinheitlich

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

### Anforderungen

#### MTB-9 – Variantentyp: `coding-change-type` ist 0..1, der Datenkranz liefert eine Liste

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

#### MTB-10 – Vorbefunde: Freitext-Träger, Datum, Untersuchungsart

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

#### MTB-11 – Durchgeführte Therapie lässt sich nicht mit einer Studien- oder Kombinationsempfehlung verknüpfen

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

#### MTB-12 – Therapieansprechen: `method` 1..1 ohne Datenquelle im Datenkranz; die Informationsquelle hat kein Element

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

#### MTB-13 – Studienempfehlungen: Evidenzgrad, Z(FDA), stützende Varianten

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

#### MTB-14 – Empfehlungstyp (in-label, off-label, compassionate use, sekundärpräventiv, unbekannt)

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

#### MTB-15 – Expressionsniveau und Referenzkohorte lassen sich nicht codieren

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

#### MTB-16 – LOH an der Einzelvariante hat kein Konzept

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

#### MTB-17 – Mutationssignaturen (COSMIC SBS) haben kein Konzept

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

#### MTB-18 – Fusionen: Bruchpunkte sind Pflicht, intragene Strukturvarianten haben kein Profil

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

#### MTB-19 – Sequenzier-QC: Kennzahlen fehlen

- **Profil/Element:** `…/mii-ex-mtb-genomic-study-analysis-qc`, Sub-Extensions wie in MTB-3.
- **Problem:** Für GRZ donors[].labData[].sequenceData.minCoverage, .percentBasesAboveQualityThreshold (minimumQuality
  und percent), .nonCodingVariants sowie donors[].labData[].fragmentationMethod gibt es keinen Platz. `sequencing-coverage`
  ist nach GR-Semantik der Anteil abgedeckter Regionen, nicht die Mindestabdeckung. Interimslösung: strukturierter Text in
  `metrics-description`.
- **Evidenz:** Sub-Extension-Liste wie in MTB-3 (Snapshot geprüft).
- **Vorschlag:** Die Sub-Extensions `min-coverage`, `percent-bases-above-quality` (Schwelle und Prozent),
  `fragmentation-method` und `non-coding-variants` ergänzen.
- **Bezug:** 22

#### MTB-20 – Variantenlokalisation im NGS-Bericht

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

#### MTB-21 – Panel-Katalog (DeviceDefinition) für die Kits aus dem GRZ

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

#### MTB-22 – NGS-Bericht: `result`-Slices überlappen (Tumorzellgehalt, Ploidie, HRD-Score, MSI)

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

#### MTB-23 – Therapieplan: keine Kategorie für das Molekulare Tumorboard

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

---

## MolGen (`de.medizininformatikinitiative.kerndatensatz.molgen#2027.0.0-ballot.1`)

### IG-Defekte

#### MOLGEN-1 – `variante`: value[x]-Slicing ist nur im Snapshot geschlossen

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

#### MOLGEN-2 – Beispiele verwenden eine abweichende SO-System-URI

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

### Anforderungen

#### MOLGEN-3 – Variantenlokalisation (Unterstützung von HDB-976)

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

#### MOLGEN-4 – Befundkategorie primär / Zufallsbefund / Kandidat (Unterstützung von HDB-976)

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

#### MOLGEN-5 – Segregation `biparental` / `notPerformed` und Erbgang `unclear` (Unterstützung von HDB-976 c)

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

#### MOLGEN-6 – ACMG-Evidenzkriterien haben kein Element

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

#### MOLGEN-7 – Studiendesign Single/Duo/Trio hat kein Konzept

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

---

## Seltene (`de.medizininformatikinitiative.kerndatensatz.seltene#2027.0.0-ballot`)

### IG-Defekte

Keine.

### Anforderungen

#### SE-1 – GMFCS (Unterstützung von HDB-975)

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

#### SE-2 – Hospitalisierung: Dauer und Anzahl der Aufenthalte (Unterstützung von HDB-975)

- **Profil/Element:** Weder `mii-lm-seltene` noch die Profile haben ein Element dafür. Es gibt auch keine Seltene-Observation
  mit frei belegbarem valueCodeableConcept: `hpo-assessment` ist an HPO gebunden, `icf-assessment` hat keinen Wert.
- **Problem:** Es handelt sich um zwei verschiedene Bänder:
  - RareDiseasesCase.priorRds[].hospitalizationDuration in Tagen (none, upToFive, upToFifteen, upToFifty, moreThanFifty, unknown),
  - .hospitalizationPeriods als Zahl der Aufenthalte in 5 Jahren (none, upToFive, upToTen, upToFifteen, moreThanFifteen, unknown).
- **Evidenz:** siehe Profil/Element.
- **Vorschlag:** HDB-975 mit zwei getrennten ValueSets bzw. CodeSystems unterstützen, deren Codes 1:1 den Literalen des
  Datenkranzes entsprechen. Bis dahin verwenden wir zwei lokale CodeSystems.
- **Bezug:** 33

#### SE-3 – Therapiestrategie `other` für medikamentöse Empfehlungen; Kombination

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

---

## Consent (`de.medizininformatikinitiative.kerndatensatz.consent#2027.0.0-ballot`)

### IG-Defekte

Keine.

### Anforderungen

#### CONSENT-1 – Die Einwilligungsbereiche des MV-GenomSeq lassen sich nicht codieren

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

---

## Biobank (`de.medizininformatikinitiative.kerndatensatz.biobank#2027.0.0-ballot`)

### IG-Defekte

#### BIOBANK-1 – SpecimenCore: `lagerprozess.extension` ist 1..*, ohne dass eine bestimmte Extension Pflicht ist

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-biobank/StructureDefinition/SpecimenCore`,
  `Specimen.processing:lagerprozess.extension` (1..*) und `Specimen.processing:lagerprozess.extension:temperaturbedingungen` (0..1).
- **Problem:** In 2027 wurde `temperaturbedingungen` in SpecimenCore auf 0..1 gelockert und gleichzeitig `lagerprozess.extension`
  von 0..* auf 1..* verschärft. Ein Lagerprozess muss damit irgendeine Extension tragen, ohne dass eine bestimmte gefordert
  ist; vermutlich ein Versehen. Betroffen ist GRZ donors[].labData[].sampleConservation, wenn es als Lagerprozess abgebildet wird.
- **Evidenz:** Im Differential von SpecimenCore ist `lagerprozess.extension` min 1 und `…:temperaturbedingungen` 0..1.
  In 2026.0.1 waren es 0..* bzw. 1..1.
- **Vorschlag:** `lagerprozess.extension` auf 0..* zurücksetzen, oder `temperaturbedingungen` dort bei 1..1 belassen.
- **Bezug:** Diff

### Anforderungen

#### BIOBANK-2 – Specimen-Profil verlangt Temperaturbedingungen 1..1 für jeden Verarbeitungsschritt

- **Profil/Element:** `https://www.medizininformatik-initiative.de/fhir/ext/modul-biobank/StructureDefinition/Specimen`,
  `Specimen.processing.extension:temperaturbedingungen` 1..1; in SpecimenCore 0..1.
- **Problem:** GRZ donors[].labData[].sampleConservation (fresh-tissue, cryo-frozen, ffpe, other, unknown) enthält keine
  Temperatur. Mit dem Specimen-Profil lässt sich die Konservierung nur mit einer erfundenen Temperatur abbilden. Wir
  verwenden deshalb SpecimenCore.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** Klarstellen, dass SpecimenCore das Zielprofil für Sequenzierproben außerhalb von Biobanken ist, oder
  `temperaturbedingungen` im Specimen-Profil auf 0..1 setzen.
- **Bezug:** Diff

#### BIOBANK-3 – Probenart: SNOMED-Slice ist Pflicht, das GRZ liefert BTO

- **Profil/Element:** SpecimenCore und Specimen, `Specimen.type.coding:sct` (1..*, extensible `…/ValueSet/mii-vs-biobank-probenart-sct`).
- **Problem:** GRZ donors[].labData[].tissueTypeId und .tissueOntology.name liefern die Gewebeart in der Regel als BTO-Code
  (BRENDA Tissue Ontology); ob das für alle Einsender gilt, ist nicht verifiziert. Eine SNOMED-Codierung ist aber Pflicht.
  Ohne offizielle Abbildung muss jeder Implementierer BTO → SNOMED selbst mappen.
- **Evidenz:** siehe Profil/Element (Snapshot geprüft).
- **Vorschlag:** Eine MII-ConceptMap BTO → SNOMED bereitstellen, analog zu den vorhandenen SPREC → SNOMED-Maps
  `mii-cm-biobank-*-sprec-sct`, oder einen Hinweis zum Umgang mit Proben geben, die nur einen BTO-Code haben.
- **Bezug:** Diff (offener Punkt MIIUP-04)

---

## Bewusst nicht eingereicht

- **Punkte, in denen TDs Anmerkungen nicht zu den Paketen passen** (`docs/REVIEW-TD-2026-10-06.md`, Abschnitt D). Daraus
  entsteht kein Kommentar:
  - Die Consent-OIDs .2/.6/.8 existieren.
  - `procedure-causedBy` → Therapieempfehlung existiert (siehe MTB-11, dort nur die Studienempfehlung).
  - `therapyResponseSource` ist keine RECIST/RANO-Methode.
  - Karyotypisierung, Array und other sind im method-type-VS enthalten.
  - `minCoverage` ≠ `sequencing-coverage`.
  - Die als „2027" bezeichneten Elemente sind identisch mit 2026.
  - Die LOINC-Codes für den Erbgang gelten nicht nur für MTB.
- **Seltene 2026.0.1 (nur bekannter Fehler, im Ballot behoben):** Im Therapieplan zielt `activity:NichtMedikamentoesTherapie`
  auch auf die Basis-ServiceRequest, sodass eine Studieneinschluss-Anfrage in `activity.reference` zwei Slices
  (`NichtMedikamentoesTherapie`, `Studieneinschlussempfehlung`) trifft. In 2027.0.0-ballot ist das behoben. Für das
  Profilset 2026 verweist die Anfrage stattdessen per `ServiceRequest.basedOn` auf den Therapieplan (REPRESENTATIONS #52).
- **Patho:** Die nicht deklarierte Abhängigkeit von `hl7.fhir.eu.laboratory` betrifft kein Feld des MV-GenomSeq-Datenkranzes.
  Sie kann bei Bedarf separat gemeldet werden.

## Vor dem Einreichen klären

1. Wer reicht ein, TD oder wir, und in welcher Form (HDB-Ticket je Kommentar oder je Modul)?
2. Texte von HDB-975 und HDB-976 abgleichen (SE-1, SE-2, MOLGEN-3 bis MOLGEN-5).
3. Frist 2026-10-27 bestätigen.

---

## Übersicht

| ID | Modul | Typ | Datenkranz-Feld | Bezug |
|:--|:--|:--|:--|:--|
| ONKO-1 | Onkologie | Defekt | OncologyCase.diagnosisOd.tnmClassifications[] | 7 |
| ONKO-2 | Onkologie | Defekt | OncologyCase.diagnosisOd.tnmClassifications[]; OncologyFollowUp.*; OncologyPlan.* | 7 |
| ONKO-3 | Onkologie | Defekt | OncologyMolecular.*Variants[].genes[] (HGNC) | 9 |
| ONKO-4 | Onkologie | Anforderung | OncologyCase.diagnosisOd.ecogPerformanceStatusScore; OncologyFollowUp.followUpOds[].ecogPerformanceStatusScore | 1 |
| ONKO-5 | Onkologie | Anforderung | OncologyCase.diagnosisOd.tnmClassifications[] | 2 |
| ONKO-6 | Onkologie | Anforderung | OncologyPlan.recommendedSystemicTherapies[].therapeuticStrategy | 3 |
| ONKO-7 | Onkologie | Anforderung | OncologyFollowUp.followUpOds[].metachroneDiagnoses | 4 |
| ONKO-8 | Onkologie | Anforderung | OncologyCase.diagnosisOd.diagnosticAssessment; OncologyFollowUp.followUpOds[].preventiveMeasures[]; OncologyPlan.carePlanOd.suitableInterventions[] | 5 |
| ONKO-9 | Onkologie | Anforderung | OncologyCase.diagnosisOd.topography | 8 |
| MTB-1 | MTB | Defekt | OncologyPlan.recommendedStudies[]; OncologyPlan.carePlanOd.counsellingRecommended | Diff |
| MTB-2 | MTB | Defekt | OncologyMolecular.smallVariants[].transcriptId; OncologyCase.priorDiagnostics[].simpleVariants[].transcript | 10 |
| MTB-3 | MTB | Defekt | GRZ donors[].labData[].sequenceData.meanDepthOfCoverage, .targetedRegionsAboveMinCoverage; donors[].labData[].sequencingLayout | 22 |
| MTB-4 | MTB | Defekt | – (kein KDK-Feld; MII-CNV `cna`/`cnb`) | 23 |
| MTB-5 | MTB | Defekt | OncologyMolecular.complexBiomarkers[].ploidy | 23 |
| MTB-6 | MTB | Defekt | OncologyMolecular.expressionVariants[] | 18, 23 |
| MTB-7 | MTB | Defekt | OncologyMolecular.copyNumberVariants[].cnvType | 17 |
| MTB-8 | MTB | Defekt | OncologyMolecular.structuralVariants[].geneA, .geneB | 21 |
| MTB-9 | MTB | Anforderung | OncologyMolecular.smallVariants[].variantTypes[]; OncologyMolecular.structuralVariants[].structureType | 11 |
| MTB-10 | MTB | Anforderung | OncologyCase.priorDiagnostics[].complexVariants[], .date, .type | 12 |
| MTB-11 | MTB | Anforderung | OncologyFollowUp.followUpOds[].therapies[].reference | 13 |
| MTB-12 | MTB | Anforderung | OncologyFollowUp.followUpOds[].therapies[].therapyResponse, .therapyResponseSource; OncologyCase.priorProcedures[].therapyResponse | 14 |
| MTB-13 | MTB | Anforderung | OncologyPlan.recommendedStudies[].evidenceLevel, .evidenceLevelDetails[], .variants[]; OncologyPlan.recommendedSystemicTherapies[].evidenceLevelDetails[] | 15 |
| MTB-14 | MTB | Anforderung | OncologyPlan.recommendedSystemicTherapies[].type | 16 |
| MTB-15 | MTB | Anforderung | OncologyMolecular.expressionVariants[].expressionType, .reference | 18, 6 |
| MTB-16 | MTB | Anforderung | OncologyMolecular.smallVariants[].loh | 19 |
| MTB-17 | MTB | Anforderung | OncologyMolecular.sbsSignatures[].name[], .version | 20 |
| MTB-18 | MTB | Anforderung | OncologyMolecular.structuralVariants[] | 21 |
| MTB-19 | MTB | Anforderung | GRZ donors[].labData[].sequenceData.minCoverage, .percentBasesAboveQualityThreshold, .nonCodingVariants; donors[].labData[].fragmentationMethod | 22 |
| MTB-20 | MTB | Anforderung | OncologyMolecular.smallVariants[].localization | 26 |
| MTB-21 | MTB | Anforderung | GRZ donors[].labData[].kitName, .kitManufacturer, .sequencerModel, .sequenceData.bioinformaticsPipelineName, .sequenceData.callerUsed[] | 24 |
| MTB-22 | MTB | Defekt | alle Ergebnisse des NGS-Berichts (OncologyMolecular.*) | Diff |
| MTB-23 | MTB | Anforderung | OncologyPlan (molecularBoardDecisionDate) | Diff |
| MOLGEN-1 | MolGen | Defekt | alle Varianten-Observations (OncologyMolecular.*, RareDiseasesMolecular.*) | Diff; 18, 25 |
| MOLGEN-2 | MolGen | Defekt | OncologyMolecular.smallVariants[].variantTypes[], .localization; RareDiseasesMolecular entsprechend | 11, 26 |
| MOLGEN-3 | MolGen | Anforderung (HDB-976) | RareDiseasesMolecular.*Variants[].localization[]; OncologyMolecular.smallVariants[].localization | 26 |
| MOLGEN-4 | MolGen | Anforderung (HDB-976) | RareDiseasesMolecular.*Variants[].diagnosticSignificance | 27 |
| MOLGEN-5 | MolGen | Anforderung (HDB-976 c) | RareDiseasesMolecular.*Variants[].segregationAnalysis, .modeOfInheritance | 28, 29 |
| MOLGEN-6 | MolGen | Anforderung | RareDiseasesMolecular.*Variants[].acmgCriteria[].value, .modifier | 30 |
| MOLGEN-7 | MolGen | Anforderung | RareDiseasesCase.priorRds[].genomicStudyType; GRZ submission.genomicStudyType | 31 |
| SE-1 | Seltene | Anforderung (HDB-975) | RareDiseasesCase.diagnosisRd.diagnosisGmfcs; RareDiseasesFollowUp.followUpRds[].gmfcs | 32 |
| SE-2 | Seltene | Anforderung (HDB-975) | RareDiseasesCase.priorRds[].hospitalizationDuration, .hospitalizationPeriods | 33 |
| SE-3 | Seltene | Anforderung | RareDiseasesPlan.recommendedTherapies[].strategy | 34 |
| CONSENT-1 | Consent | Anforderung | Submission.mvConsent.scope[].domain; GRZ donors[].mvConsent.scope[].domain | 35 |
| BIOBANK-1 | Biobank | Defekt | GRZ donors[].labData[].sampleConservation | Diff |
| BIOBANK-2 | Biobank | Anforderung | GRZ donors[].labData[].sampleConservation | Diff |
| BIOBANK-3 | Biobank | Anforderung | GRZ donors[].labData[].tissueTypeId, .tissueOntology.name | Diff (MIIUP-04) |
