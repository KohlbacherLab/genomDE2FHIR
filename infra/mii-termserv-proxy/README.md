# MII SU-TermServ terminology proxy (option 1)

Point matchbox's single `txServer` at the **MII SU-TermServ Ontoserver**
(`ontoserver.mii-termserv.de`) so ICD-10-GM / ICD-O-3 / OPS / ATC / ORPHA / Alpha-ID **and**
SNOMED CT / LOINC all resolve from one authoritative, MII-sanctioned server — no federation, no
corpus fixtures. This replaces `tx.fhir.org` (which lacks the German BfArM terminologies).

The Ontoserver enforces **mutual TLS** (access restricted to German institutions). matchbox can't
do mTLS to a tx server directly, so this nginx proxy holds the client certificate, terminates mTLS,
and exposes plain HTTP on the matchbox docker network. This is SU-TermServ's recommended pattern.

## What you need to provide (only this)
A **SU-TermServ client certificate + key**:
- Your Tübingen DIZ very likely already holds one. Otherwise request via **support-medic@uni-koeln.de**
  (see https://mii-termserv.de/en/faq/certificate-request/).
- **RSA 2048+ (4096 recommended); EC keys are not supported.**
- Place the **full chain** at `certs/client.crt` and the **unencrypted RSA key** at `certs/client.key`.
  (If you have a `.p12`/`.pfx`: `openssl pkcs12 -in c.p12 -clcerts -nokeys -out certs/client.crt`
  and `openssl pkcs12 -in c.p12 -nocerts -nodes -out certs/client.key`.)

`certs/` is gitignored — certificates never get committed.

## Activate
```bash
bash infra/mii-termserv-proxy/up.sh      # starts proxy + smoke-tests mTLS reachability
```
If the smoke test prints a FHIR `Bundle` (not an SSL/HTML error), mTLS works. Then wire matchbox:

1. In `~/Claude/genomDE FHIR Mapper/matchbox-config/application.yaml`, set
   `matchbox.fhir.context.txServer: http://mii-termserv-proxy/fhir`
2. `docker restart genomde-matchbox`
3. Re-validate: `python3 scripts/e2e_harness.py --roots examples --paths A`
   → the diagnose / medication / vortherapie rows should move from env to clean.

(Optional federation: if you'd rather keep tx.fhir.org for SNOMED/LOINC and only route the German
systems here, add a second `location` block in `nginx.conf` and route by upstream — but the MII
Ontoserver already serves SNOMED/LOINC, so one upstream is enough.)

## Status
Scaffold is ready and matchbox is currently on `tx.fhir.org` (SNOMED/LOINC only). Drop in the cert,
run `up.sh`, and I'll flip `txServer` + re-run the harness to confirm the German terms validate.
