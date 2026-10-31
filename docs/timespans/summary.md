# Zeitspannen im Korpus

Manifest `genomde2fhir/tests/corpus_manifest.json`; Werte in Tagen; Monatsangaben auf den 15. gesetzt. Nur gültige KDK-Dateien; GRZ-Spannen (D9–D12) nur für die handgepaarten Beispiele.


## oncology (624 Fälle)

| Spanne | n | min | Q1 | Median | Q3 | max |
|:--|--:|--:|--:|--:|--:|--:|
| A1_age_at_board1_years | 624 | 2 | 28 | 43 | 56 | 86 |
| D1_consent_to_board1 | 624 | 9 | 592 | 2112 | 3402 | 5093 |
| D10_sample_to_board2 | 2 | 6 | -32 | 83 | 198 | 160 |
| D11_sample_to_grz_submit | 2 | 20 | 20 | 20 | 20 | 20 |
| D12_grz_minus_kdk_submit | 2 | -140 | -175 | -70 | 35 | 0 |
| D13_board_to_followup | 86 | -7762 | -3065 | -98 | -49 | 28 |
| D15_observation_span | 86 | -7748 | -3064 | -91 | -42 | 28 |
| D16_board2_to_therapy_start | 110 | -7825 | -3244 | -196 | -140 | -63 |
| D17_therapy_duration | 110 | 70 | 112 | 161 | 196 | 245 |
| D18_start_to_response | 110 | 56 | 63 | 77 | 98 | 105 |
| D2_board1_to_submit | 624 | 0 | 845 | 2412 | 3758 | 5216 |
| D20_board1_to_death | 38 | -7580 | -6288 | -4440 | -3064 | -2479 |
| D24_prior_therapy_to_dx | 654 | -8386 | -1512 | -324 | 2116 | 11666 |
| D26_prior_test_to_board1 | 566 | -4470 | -1205 | -14 | 1178 | 4300 |
| D3_consent_to_submit | 624 | 13 | 5249 | 5352 | 5466 | 5594 |
| D4_dx_to_board1 | 624 | -4320 | -840 | 578 | 1536 | 8949 |
| D6_board1_to_board2 | 605 | 0 | 967 | 2473 | 3760 | 5187 |
| D7_board2_to_submit | 605 | 0 | 17 | 29 | 37 | 60 |
| D8_dx_to_board2 | 605 | 167 | 1466 | 2749 | 4126 | 8963 |
| D9_board1_to_sample | 2 | -146 | -181 | -76 | 29 | -6 |

## rare-disease (84 Fälle)

| Spanne | n | min | Q1 | Median | Q3 | max |
|:--|--:|--:|--:|--:|--:|--:|
| A1_age_at_board1_years | 84 | 30 | 41 | 50 | 58 | 69 |
| D1_consent_to_board1 | 84 | 14 | 14 | 14 | 14 | 14 |
| D10_sample_to_board2 | 4 | 20 | 20 | 90 | 160 | 160 |
| D11_sample_to_grz_submit | 4 | 20 | 20 | 20 | 20 | 20 |
| D12_grz_minus_kdk_submit | 4 | -140 | -140 | -70 | 0 | 0 |
| D13_board_to_followup | 84 | 0 | 0 | 0 | 0 | 0 |
| D13e_board_to_diagnosis_established | 47 | 0 | 0 | 0 | 0 | 0 |
| D15_observation_span | 84 | 14 | 14 | 14 | 14 | 14 |
| D2_board1_to_submit | 84 | 14 | 14 | 14 | 14 | 14 |
| D20_board1_to_death | 36 | -7649 | -6458 | -5104 | -4243 | -2262 |
| D3_consent_to_submit | 84 | 28 | 28 | 28 | 28 | 28 |
| D5_onset_to_board1 | 84 | 163 | 191 | 244 | 296 | 327 |
| D6_board1_to_board2 | 84 | 14 | 14 | 14 | 14 | 14 |
| D7_board2_to_submit | 84 | 0 | 0 | 0 | 0 | 0 |
| D9_board1_to_sample | 4 | -146 | -146 | -76 | -6 | -6 |
