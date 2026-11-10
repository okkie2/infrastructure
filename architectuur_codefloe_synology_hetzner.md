Versie 0.2 · 9 november 2026 · Status: voorgesteld ontwerp

# 1. Doel en uitgangspunten

Eén generieke CLI voor meerdere producten, waarmee broncode één keer wordt gebouwd tot een onveranderlijke Docker-image. Diezelfde image kan onafhankelijk en op ieder gewenst moment worden uitgerold naar Synology TEST of Hetzner PROD. De Synology fungeert daarnaast als back-upbestemming voor productie.

- Build en deployment zijn onafhankelijke acties; een Git-push veroorzaakt nooit automatisch een productie-release.

- Iedere applicatie heeft een eigen repository en Docker Compose-project.

- Hetzelfde image-digest wordt gebruikt in TEST en PROD; omgevingsconfiguratie en data blijven gescheiden.

- Alle handelingen zijn scriptbaar via CLI/API, zodat Codex ze kan uitvoeren.

- Productie-deployment vereist expliciete bevestiging en wordt gelogd.

# 2. Componenten en verantwoordelijkheden

| Component                  | Rol                                                                                     |
|----------------------------|-----------------------------------------------------------------------------------------|
| Codex / MacBook            | Code wijzigen; deployment-CLI starten; logs en resultaten analyseren                    |
| CodeFloe Git               | Broncode, workflows, versiegeschiedenis                                                 |
| CodeFloe Actions-runner    | Tests, Docker-build, publiceren image                                                   |
| CodeFloe containerregistry | Images opslaan onder versie en immutable digest                                         |
| Deployment-CLI (Node.js)   | Build triggeren, status volgen, digest bepalen, target kiezen en deployment coördineren |
| Synology DS225+            | TEST via Docker Compose; afgeschermde back-upopslag                                     |
| Hetzner Cloud VPS          | PROD via Docker Compose; Caddy, twee applicatiecontainers en één gedeelde PostgreSQL-container                                   |
| Restic + Tailscale         | Versleutelde, private back-uptransporten naar Synology                                  |

# 3. Logische stromen

## 3.1 Build

Codex commit en pusht code naar CodeFloe. De CLI of een expliciete workflowtrigger start een CodeFloe Actions-build. De runner controleert code, bouwt de image en pusht deze naar de registry. De build publiceert een machineleesbaar resultaat met commit-ID, image-referentie en SHA256-digest. De CLI controleert het resultaat en stopt bij fouten.

## 3.2 Release naar gekozen target

De CLI selecteert product, image-digest en target. Het target haalt de image uit de registry en start het bijbehorende Compose-project. De CLI voert healthchecks uit, registreert de release en rapporteert de status. Synology TEST en Hetzner PROD gebruiken eigen secrets, volumes, databases en domeinen.

## 3.3 Back-up

Een geplande taak op Hetzner maakt consistente database-exporten en back-ups van persistente applicatiebestanden. Restic versleutelt en verstuurt deze via een beveiligde verbinding naar een afgeschermde bestemming op Synology. Back-ups lopen onafhankelijk van deployments. Herstelbaarheid wordt periodiek getest.

# 4. CLI-contract

deploy build sinterapp

deploy release sinterapp --target synology --version sha256:\<digest\>

deploy release sinterapp --target hetzner --version sha256:\<digest\>

deploy run sinterapp --target synology

\# run = build, wachten, digest bepalen, deployen, controleren

De naam deploy is een zelf te ontwikkelen wrapper, geen bestaand standaardcommando. Een productie-release vraagt expliciete bevestiging, tenzij een vooraf goedgekeurde niet-interactieve procedure is ingericht. Gebruik bij voorkeur digest-referenties in plaats van latest.

# 5. Repository- en serverstructuur

deployment-tooling/

cli/deploy.js

config/products.yaml

config/targets.yaml

scripts/release.sh

scripts/healthcheck.sh

sinterapp/

Dockerfile

compose.yaml

.forgejo/workflows/build.yaml

/srv/sinterapp/ \# Hetzner

/volume1/docker/sinterapp/ \# Synology

# 6. Interfaces en technische keuzes

- CodeFloe API: handmatige buildtrigger, buildstatus en image-metadata. De exacte endpoints en permissies moeten tegen de actuele CodeFloe-documentatie worden gevalideerd.

- Registry: geauthenticeerde docker push/pull; aparte, minimaal bevoegde credentials voor runners en deploymenttargets.

- Deploy: SSH naar een beperkt deploymentaccount of een afgeschermde runner; docker compose pull/up --wait en HTTP-healthcheck.

- Netwerk: Caddy routeert publieke domeinen naar afzonderlijke productcontainers; databases blijven op interne Docker-netwerken.

- Hetzner API: VPS, firewall en netwerk provisioneren; niet nodig voor elke applicatierelease.

# 7. Beveiliging en operationele eisen

- Geen productiecredentials in Git of buildlogs; per target gescheiden secrets en rechten.

- Back-uprepository met minimale schrijfrechten; bescherming tegen verwijdering door een gecompromitteerde VPS via snapshots of tweede onafhankelijke kopie.

- Beperk runner-toegang op de Synology; geen toegang tot NAS-beheer, andere containers of back-ups.

- Pre-deploy checks, healthchecks en vastgelegde vorige image-digest; rollback van code waar veilig, database-migraties apart behandelen.

- Testomgeving gebruikt synthetische of geanonimiseerde data; productiegegevens nooit stilzwijgend kopiëren.

- Houd rekening met de beperkte 4 GB RAM van de CX23; monitor geheugen, schijf en containergebruik.

# 8. Open beslissingen en aannames

- Bevestigen dat CodeFloe-account toegang heeft tot hosted Actions, containerregistry en benodigde API-permissies; quota en facturering controleren.

- Vaststellen hoe buildresultaten en image-digests betrouwbaar door de CLI worden opgehaald.

- Keuze voor directe SSH-deployment versus afgeschermde self-hosted runner.

- Definitieve domeinnamen, secrets-opslag, database-migratieprocedure en retentiebeleid vaststellen.

- Beslissen of PROD alleen na handmatige goedkeuring mag worden uitgerold of via een expliciete automation-policy.


# 9. Productiecontainers en databases (besluit)

Op Hetzner draaien voor de huidige twee applicaties drie containers: één Django/Python-applicatie, één JavaScript-applicatie en één gedeelde PostgreSQL-server. PostgreSQL bevat twee afzonderlijke databases, elk met een eigen gebruiker en minimale rechten. De database heeft persistente opslag; applicatie-images bevatten geen productiegegevens. Databasewijzigingen worden apart van applicatiereleases beheerd. Synology is TEST en dagelijkse back-upbestemming, niet de primaire database. Dagelijkse consistente exports van beide PostgreSQL-databases worden eenrichtingsverkeer van Hetzner naar Synology, met gedateerde herstelpunten en periodieke hersteltest. TEST krijgt geen automatische toegang tot productiegegevens.

# 10. Transactionele e-mail (besluit)

## 10.1 Initiële inrichting

Beide applicaties versturen notificaties naar hun gebruikers via één Brevo-account (Europese SMTP-provider), met afzonderlijke geverifieerde afzenderdomeinen/adressen per applicatie. De applicaties verbinden rechtstreeks met Brevo via TLS-beveiligde SMTP; er draait aanvankelijk geen eigen mailserver of Postfix-relay op Hetzner. Privé-mail blijft bij Infomaniak. DNS-authenticatie (SPF, DKIM, DMARC) wordt per afzenderdomein bij de DNS-beheerder ingesteld volgens Brevo's actuele instructies. Hetzner hoeft niet in SPF als uitsluitend Brevo daadwerkelijk verzendt.

Alle applicaties gebruiken dezelfde configuratie-interface: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` en TLS-instelling. Credentials zijn per omgeving gescheiden en staan buiten Git, Docker-images en logs. Bij voorkeur heeft elke app een eigen SMTP-sleutel indien de provider dat ondersteunt.

## 10.2 Betrouwbaarheid en groei

Verzenden gebeurt asynchroon vanuit een persistente applicatie-outbox/queue, met begrensde retries, exponentiële back-off, unieke bericht-ID's, foutlogging en monitoring van mislukte of vertraagde verzendingen. Maak onderscheid tussen SMTP-acceptatie en daadwerkelijke aflevering; gebruik waar mogelijk provider-events voor bounces en klachten. Voorkom dubbele notificaties bij retries.

Uitgangspunt: circa 50 mails/dag. De eerder besproken gratis Brevo-limiet van 300 mails/dag moet bij inrichting worden geverifieerd; deze geldt accountbreed, over alle apps en domeinen. Bij groei boven het gratis quotum: eerst een passend betaald pakket of andere Europese SMTP-provider. Bij circa 2.000 mails/dag (ongeveer 60.000 per maand) worden prijs, rate limits, reputatie, afleverbaarheid en eventuele eigen SMTP-relay opnieuw beoordeeld. Een eigen mailserver is geen automatische vervolgstap.

Providerwissel vereist wijziging van SMTP-secrets/configuratie, afzenderverificatie en relevante DNS-records; applicatiecode en deploymentpipeline blijven ongewijzigd. Een centrale Postfix-relay is optioneel bij behoefte aan gedeelde buffering of providerroutering.

## 10.3 Acceptatie

Beide apps kunnen vanaf hun eigen geverifieerde domein notificaties naar externe mailboxen versturen. SPF/DKIM/DMARC slagen; een tijdelijke providerstoring verliest geen berichten; rate limits leiden tot retries en alarmen; providerwissel is getest zonder codewijziging.


# 11. Vastgestelde Hetzner-infrastructuur (9 november 2026)

Bron: screenshot Hetzner Console, aangeleverd door de eigenaar. Dit is een momentopname, geen live servercontrole.

| Eigenschap | Waarde |
|---|---|
| Servernaam | `ubuntu-4gb-hel1-1` |
| Servertype | CX23 |
| Server-ID | `175269905` |
| Locatie | Helsinki, Finland (`hel1`, `eu-central`) |
| vCPU | 2 |
| RAM | 4 GB |
| Lokale schijf | 40 GB |
| IPv4 | `37.27.251.21` |
| IPv6-prefix | `2a01:4f9:c015:84a6::/64` |
| Getoonde prijs | € 6,64 per maand (momentopname; controleer actuele factuur) |
| Status op screenshot | Aan / gestart |
| OS | Ubuntu volgens servernaam; exacte versie nog verifiëren |

**Capaciteitsbesluit:** start met twee applicatiecontainers en één gedeelde PostgreSQL-container op deze VPS. Reserveer ruimte voor OS, reverse proxy, logging, tijdelijke releases en back-ups; bewaak RAM, diskgebruik en CPU. De 40 GB lokale schijf is geen onafhankelijke back-upbestemming. Houd PostgreSQL uitsluitend bereikbaar via het interne Docker-netwerk.

**Netwerk en beveiliging:** controleer SSH-sleuteltoegang, niet-root beheer, firewallregels (alleen noodzakelijke inkomende poorten), updates en Docker/Compose-installatie. Beperk publieke blootstelling tot HTTPS en noodzakelijke beheerverbindingen. Gebruik de IPv4-adreswaarde alleen voor initiële verbindingen; publiceer applicaties via DNS en TLS.

**Open verificaties:** Ubuntu-versie, SSH-toegang, firewallstatus, Docker-installatie, werkelijk beschikbare resources, back-upbereikbaarheid naar Synology en of Hetzner-back-ups/snapshots ingeschakeld zijn.
