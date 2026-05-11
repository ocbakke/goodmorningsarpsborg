# God morgen, Sarpsborg

Automatiserer et daglig utkast til spalten "God morgen, Sarpsborg!".

Skriptet henter:

- navnedag fra `data/navnedager.json`
- offisielle norske flaggdager fra `data/offisielle_flaggdager.json`
- værvarsel og soltider fra MET
- historiske hendelser fra Wikipedia
- artikkeltekst fra Gemini

Til slutt bygger skriptet en Cue-lenke for artikkelkladd og sender teksten som HTML-epost til redaksjonen.

## Kjør lokalt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Sett miljøvariabler:

```bash
export GEMINI_API_KEY="..."
export EMAIL_SENDER="..."
export EMAIL_PASSWORD="..."
export EMAIL_RECEIVER="redaksjonen@sa.no"
```

Test uten å sende e-post:

```bash
python GodMorgenSarpsborg.py --dry-run
```

Generer for en bestemt dato:

```bash
python GodMorgenSarpsborg.py --dry-run --dato 2026-05-17
```

## Offisielle flaggdager

Kilden er Lovdata: [Forskrift angående bruk av statsflagget og handelsflagget § 4](https://lovdata.no/dokument/SF/forskrift/1927-10-21-9733).

Faste flaggdager som ligger i `data/offisielle_flaggdager.json`:

- 1. januar: 1. nyttårsdag
- 21. januar: H.K.H. Prinsesse Ingrid Alexandras fødselsdag
- 6. februar: Samefolkets dag
- 21. februar: H.M. Kong Harald Vs fødselsdag
- 1. mai: Offentlig høytidsdag
- 8. mai: Frigjøringsdagen 1945
- 17. mai: Grunnlovsdagen
- 7. juni: Unionsoppløsningen 1905
- 4. juli: H.M. Dronning Sonjas fødselsdag
- 20. juli: H.K.H. Kronprins Haakon Magnus' fødselsdag
- 29. juli: Olsokdagen
- 19. august: H.K.H. Kronprinsesse Mette-Marits fødselsdag
- 25. desember: 1. juledag

Bevegelige flaggdager beregnes i koden:

- 1. påskedag
- 1. pinsedag

Dagen for stortingsvalg er også offisiell flaggdag, men den har ikke en fast årlig dato. Legg den inn ved behov:

```bash
export EKSTRA_FLAGGDAGER="2029-09-10=Stortingsvalgdag"
```

Når datoen er en offisiell flaggdag, får Gemini beskjed om å nevne dette tidlig i ingressen og først under "Dagen i dag".

## Tester

```bash
python -m unittest discover -s tests
```
