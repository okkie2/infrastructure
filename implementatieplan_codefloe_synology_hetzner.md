Versie 0.2 · 9 november 2026 · Status: voorgesteld ontwerp

# 1. Resultaat en werkwijze

Een werkende deployment-CLI voor SinterApp als pilot. Na validatie is dezelfde tooling inzetbaar voor ProductForge en volgende producten. Werk in kleine, toetsbare stappen; voer geen automatische PROD-deployments in voordat TEST, herstel en toegangsbeveiliging aantoonbaar werken.

# 2. Fases en acceptatiecriteria

## Fase 0 — Inventarisatie en toegang

- Controleer CodeFloe-repository, Actions, registry, API-tokens en runners; verifieer daadwerkelijke quota.

- Inventariseer Synology Docker/Compose-versies, SSH, opslag, Tailscale en Hetzner VPS-capaciteit.

- Leg productnaam, DNS, healthcheck, database en huidige secrets vast.

Acceptatie: Alle vereiste interfaces zijn aantoonbaar bereikbaar; ontbrekende mogelijkheden en kosten zijn vastgelegd.

## Fase 1 — Minimale build

- Maak Dockerfile en reproduceerbare lokale build voor SinterApp.

- Voeg CodeFloe Actions-workflow toe voor lint, tests, build en registry push.

- Tag met commit-ID; registreer de immutable digest en maak een controleerbaar buildresultaat.

Acceptatie: Een commit resulteert in een testbare image in de registry; mislukte tests blokkeren publicatie.

## Fase 2 — Synology TEST

- Maak apart Compose-project en testconfiguratie op Synology.

- Richt registry pull-credentials, beperkte deploymenttoegang en interne netwerkisolatie in.

- Implementeer deploy release naar Synology, inclusief healthcheck en logregistratie.

Acceptatie: Een eerder gebouwde image wordt zonder rebuild gestart; testdatabase is volledig gescheiden.

## Fase 3 — Hetzner PROD

- Provision VPS, updates, firewall, SSH en Docker Compose; configureer Caddy en HTTPS.

- Maak eigen PROD Compose-project, secrets en persistente opslag.

- Voeg expliciete productiebevestiging, healthcheck en registratie vorige digest toe.

Acceptatie: Dezelfde image-digest draait op PROD; foutscenario stopt of herstelt veilig en is zichtbaar.

## Fase 4 — Generieke CLI

- Bouw Node.js-CLI met build, release en run subcommands.

- Voeg product- en targetconfiguratie, statuspolling, timeouts, idempotentie en duidelijke exitcodes toe.

- Ondersteun versie-selectie en logging van wie, wat, wanneer en waar.

Acceptatie: Eén commando start de volledige keten; release van een bestaande digest gebruikt geen buildminuten.

## Fase 5 — Back-up en herstel

- Configureer database-export en Restic over Tailscale naar Synology.

- Stel retentie, beperkte credentials en bescherming tegen verwijdering in.

- Voer een volledige restore op een schone testomgeving uit en documenteer RTO/RPO.

Acceptatie: Gegevens kunnen aantoonbaar worden teruggezet; een mislukte back-up veroorzaakt een melding.

## Fase 6 — Uitbreiding en overdracht

- Voeg ProductForge toe via declaratieve productconfiguratie.

- Documenteer operationele commando’s, incidentprocedure, kosten en monitoring.

- Laat Codex een volledige build + TEST-release en gecontroleerde PROD-release uitvoeren.

Acceptatie: Tweede product vereist geen kopie van de CLI-code; beheer is reproduceerbaar.

# 3. Concrete CLI-scenario’s

deploy build sinterapp

deploy release sinterapp --target synology --version sha256:\<digest\>

deploy release sinterapp --target hetzner --version sha256:\<digest\>

deploy run sinterapp --target synology

# 4. Minimale end-to-end testset

- Succesvolle build → image-digest gepubliceerd → Synology-deployment → healthcheck groen.

- Dezelfde digest naar Hetzner zonder nieuwe build; controleer versie in beide omgevingen.

- Build faalt: geen deployment.

- Registry onbereikbaar: duidelijke fout en bestaande containers blijven draaien.

- Healthcheck faalt: release als mislukt gemarkeerd; herstelprocedure getest.

- PROD zonder bevestiging: deployment geweigerd.

- Back-up maken, repository ontoegankelijk simuleren, melding controleren; volledige restore uitvoeren.

- Onjuiste target/secrets: geen toegang tot de andere omgeving.

# 5. Afhankelijkheden en risico’s

| Risico                            | Maatregel                                                                |
|-----------------------------------|--------------------------------------------------------------------------|
| CodeFloe API of runner wijkt af   | Eerst proof-of-concept en documentatiecontrole                           |
| Onvoldoende RAM op CX23           | Geheugenmeting; zo nodig grotere VPS                                     |
| Synology thuis offline            | PROD blijft werken; back-upachterstand signaleren                        |
| Gecompromitteerde CI-runner       | Least privilege, aparte deploymentaccounts, geen NAS-brede Docker-socket |
| Database-migratie breekt rollback | Backwards-compatible migraties en expliciet herstelplan                  |
| Registryquota bereikt             | Retentie en opschonen; verbruik monitoren                                |

# 6. Definition of Done

- Build en release zijn onafhankelijk aanroepbaar.

- Synology TEST en Hetzner PROD zijn expliciet selecteerbare targets.

- Iedere release is herleidbaar tot commit en image-digest.

- Productiedata en testdata zijn gescheiden.

- Productie vereist bevestiging; credentials zijn beperkt en veilig opgeslagen.

- Back-ups en volledige restore zijn getest.

- Tweede product kan declaratief worden toegevoegd.

# 7. Eerste uitvoerbare stap

Valideer in CodeFloe een minimale Actions-workflow die een eenvoudige Docker-image bouwt, naar de registry pusht en de exacte digest rapporteert. Pas na een geslaagde proef de Synology-deployment bouwen. Dit voorkomt dat de CLI wordt ontworpen rond onbevestigde API-aannames.


# 8. Uitbreiding: gedeelde PostgreSQL en dagelijkse back-ups

- Configureer op Hetzner één PostgreSQL-container met persistent volume en twee databases, ieder met eigen gebruiker en rechten.
- Configureer de Django- en JavaScript-container met afzonderlijke databaseconnecties; publiceer de PostgreSQL-poort niet op internet.
- Maak dagelijks consistente dumps van beide databases en verstuur deze versleuteld, eenrichtingsverkeer Hetzner → Synology.
- Bewaar gedateerde back-ups en test periodiek een volledige restore. Houd productie- en testdata gescheiden.

**Acceptatie:** beide apps werken onafhankelijk met hun eigen database; containervervanging behoudt data; beide databases zijn aantoonbaar herstelbaar vanaf Synology.

# 9. Uitbreiding: e-mail via Brevo

1. Maak één Brevo-account en controleer actuele gratis quota, SMTP-toegang, limieten en eventuele branding.
2. Voeg voor iedere applicatie het gewenste afzenderdomein toe; verifieer het domein en stel vereiste SPF-, DKIM- en DMARC-records in bij de DNS-beheerder.
3. Maak waar mogelijk aparte SMTP-credentials per applicatie. Bewaar ze als secrets op Hetzner; gebruik aparte TEST-configuratie zodat tests geen echte gebruikers mailen.
4. Configureer Django en JavaScript via dezelfde `SMTP_*`-variabelen en TLS; geen Brevo-specifieke API in de applicatiecode nodig.
5. Bouw per applicatie een persistente uitgaande mailqueue/outbox met worker, retries, back-off, deduplicatie en logging. Zorg dat mislukte mailverzending de hoofdtransactie niet stilzwijgend laat falen.
6. Voeg monitoring toe voor wachtrijlengte, afleverfouten, bounces, rate limits en dagelijks verbruik; stel waarschuwingen in.
7. Test aflevering naar externe providers, authenticatie (SPF/DKIM/DMARC), tijdelijke SMTP-uitval, daglimiet en herstart van de worker.
8. Documenteer een providerwissel: nieuwe SMTP-instellingen en secrets, DNS-verificatie, testverzending, gecontroleerde omschakeling en rollback.
9. Evalueer bij >300 mails/dag een betaald pakket of alternatieve Europese SMTP-provider. Bij ~2.000 mails/dag: vergelijk kosten, afleverbaarheid, rate limits en eventueel een Postfix-relay; eigen mailserver alleen na expliciete afweging.

**Acceptatie:** beide apps verzenden via één Brevo-account met eigen afzenderidentiteit; tijdelijk falende verzendingen blijven herstelbaar in de queue; geen credentials in Git; een alternatieve SMTP-provider kan zonder codewijziging worden ingesteld.


# 10. Hetzner CX23: concrete serverinrichting

Uitgangspunt: bestaande Hetzner-server `ubuntu-4gb-hel1-1`, CX23, Helsinki; 2 vCPU, 4 GB RAM, 40 GB lokale schijf, IPv4 `37.27.251.21`. Deze gegevens zijn afkomstig van een screenshot van 9 november 2026 en moeten bij uitvoering worden geverifieerd.

1. **Inventariseer:** bevestig Ubuntu-versie, vrije schijfruimte, geheugen, SSH-toegang en bestaande firewallregels. Controleer of snapshots/back-ups geactiveerd zijn.
2. **Beveilig:** configureer SSH met sleutels, een aparte beheerder, beperkte sudo-rechten, automatische beveiligingsupdates en een Hetzner Cloud Firewall; laat alleen noodzakelijke poorten toe. Voorkom jezelf buiten te sluiten: verifieer een tweede SSH-sessie vóór uitschakelen van andere toegang.
3. **Installeer:** Docker Engine en Docker Compose-plugin via ondersteunde Ubuntu-pakketten; configureer logrotatie en veilige Docker-toegang.
4. **Netwerk:** configureer reverse proxy met HTTPS, DNS en interne Docker-netwerken; publiceer PostgreSQL-poort 5432 niet.
5. **Data:** maak één PostgreSQL-service met persistent volume, twee databases en twee aparte gebruikers. Leg secrets buiten Git vast.
6. **Applicaties:** deploy eerst één, daarna de tweede applicatie via de bestaande CLI en immutable image-digests. Meet CPU-, RAM- en schijfgebruik.
7. **Herstel:** configureer dagelijkse consistente PostgreSQL-exports naar Synology, versleuteld transport, retentie en hersteltest.
8. **E-mail:** configureer Brevo SMTP en mailqueue zoals beschreven in sectie 9; verifieer DNS-authenticatie.
9. **Acceptatie:** beide apps bereikbaar via HTTPS; database uitsluitend intern; herstart/redeploy behoudt data; automatische back-up en restore getest; monitoring waarschuwt bij capaciteitsproblemen.

**Let op:** de getoonde € 6,64/maand is een screenshotprijs en geen gegarandeerde toekomstige prijs. Bij 4 GB RAM kan gelijktijdige piekbelasting van PostgreSQL, twee apps en builds problemen geven; images worden daarom op CodeFloe gebouwd.
