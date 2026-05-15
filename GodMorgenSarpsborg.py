import argparse
import datetime
import html
import json
import logging
import os
import smtplib
import sys
import urllib.parse
import zoneinfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from pathlib import Path

# ==========================================
# KONFIGURASJON
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OSLO_TZ = zoneinfo.ZoneInfo("Europe/Oslo")

GEMINI_MODELL = os.environ.get("GEMINI_MODELL", "gemini-3-flash")
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "10"))
SMTP_TIMEOUT_SECONDS = float(os.environ.get("SMTP_TIMEOUT_SECONDS", "30"))

# E-post konfigurasjon
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "redaksjonen@sa.no")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# CUE INTEGRASJON
CUE_HOST = os.environ.get("CUE_HOST", "https://ece5.api.no")
PUB_CODE = os.environ.get("PUB_CODE", "sarp")
PUB_NAME = os.environ.get("PUB_NAME", "sarpsborgsarbeiderblad")

PLACEHOLDER_VALUES = {
    "",
    "DIN_GEMINI_API_NØKKEL_HER",
    "navn@sa.no",
    "xxxx xxxx xxxx xxxx",
}

logger = logging.getLogger("GodMorgenSarpsborg")


def setup_logging():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def hent_påkrevd_env(navn):
    verdi = os.environ.get(navn, "").strip()
    if verdi in PLACEHOLDER_VALUES:
        raise RuntimeError(f"Mangler påkrevd miljøvariabel: {navn}")
    return verdi


def hent_valgfri_env(navn):
    verdi = os.environ.get(navn, "").strip()
    return None if verdi in PLACEHOLDER_VALUES else verdi


@lru_cache(maxsize=None)
def last_json_fil(filnavn):
    with (DATA_DIR / filnavn).open(encoding="utf-8") as f:
        return json.load(f)


def requests_get(*args, **kwargs):
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Mangler avhengighet: requests. Kjør `pip install -r requirements.txt`.") from exc
    return requests.get(*args, **kwargs)



def hent_navnedag(måned, dag):
    """Henter norsk navnedag fra data/navnedager.json."""
    navnedager = last_json_fil("navnedager.json")
    return navnedager.get(f"{måned:02d}-{dag:02d}", "Ingen navnedag")


def beregn_paskedag(år):
    """Returnerer datoen for 1. påskedag etter gregoriansk kalender."""
    a = år % 19
    b = år // 100
    c = år % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    måned = (h + l - 7 * m + 114) // 31
    dag = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(år, måned, dag)


def hent_ekstra_flaggdager():
    """Leser ekstra flaggdager fra miljøvariabelen EKSTRA_FLAGGDAGER.

    Format: YYYY-MM-DD=Navn;YYYY-MM-DD=Navn
    Brukes særlig for stortingsvalgdag, som ikke kan beregnes fast.
    """
    rå = os.environ.get("EKSTRA_FLAGGDAGER", "").strip()
    ekstra = {}
    if not rå:
        return ekstra

    for deltekst in rå.split(";"):
        if not deltekst.strip():
            continue
        try:
            dato_str, navn = deltekst.split("=", 1)
            dato = datetime.date.fromisoformat(dato_str.strip())
            ekstra[dato] = {
                "name": navn.strip(),
                "prompt_note": f"Fremhev {navn.strip()} som offisiell flaggdag.",
                "type": "ekstra",
            }
        except ValueError:
            logger.warning("Ignorerer ugyldig EKSTRA_FLAGGDAGER-verdi: %s", deltekst)
    return ekstra


def hent_offisielle_flaggdager(dato):
    """Returnerer offisielle norske flaggdager som treffer datoen."""
    data = last_json_fil("offisielle_flaggdager.json")
    treff = []

    for flaggdag in data.get("fixed", []):
        if flaggdag["month"] == dato.month and flaggdag["day"] == dato.day:
            treff.append({**flaggdag, "type": "fast"})

    påskedag = beregn_paskedag(dato.year)
    bevegelige_datoer = {
        "easter_sunday": påskedag,
        "pentecost_sunday": påskedag + datetime.timedelta(days=49),
    }
    for flaggdag in data.get("movable", []):
        if bevegelige_datoer.get(flaggdag["rule"]) == dato:
            treff.append({**flaggdag, "type": "bevegelig"})

    ekstra = hent_ekstra_flaggdager().get(dato)
    if ekstra:
        treff.append(ekstra)

    return treff


def formater_flaggdager(flaggdager):
    if not flaggdager:
        return "Ingen offisiell flaggdag registrert."
    return "; ".join(f"{f['name']} ({f.get('prompt_note', 'offisiell flaggdag')})" for f in flaggdager)


def hent_vaer_data(mål_dato):
    """Henter utvidet værdata for Sarpsborg fra Met.no"""
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=59.28&lon=11.11"
    headers = {'User-Agent': 'SarpsborgArbeiderbladBot/1.0 (ocb@sa.no)'}
    try:
        response = requests_get(url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        timeseries = data['properties']['timeseries']
        dato_str = mål_dato.strftime('%Y-%m-%d')
        dagens_data = [t for t in timeseries if t['time'].startswith(dato_str)] or timeseries[:24]
        temp_liste = [t['data']['instant']['details']['air_temperature'] for t in dagens_data]
        temp_nu = dagens_data[0]['data']['instant']['details']['air_temperature']
        forhold_nu = dagens_data[0].get('data', {}).get('next_1_hours', {}).get('summary', {}).get('symbol_code',
                                                                                                   'skyet')
        utsikt = dagens_data[min(12, len(dagens_data) - 1)].get('data', {}).get('next_6_hours', {}).get('summary',
                                                                                                        {}).get(
            'symbol_code', forhold_nu)
        return {"temp": temp_nu, "max": max(temp_liste), "min": min(temp_liste),
                "forhold": forhold_nu.replace('_', ' '), "neste_6h": utsikt.replace('_', ' ')}
    except Exception as e:
        logger.exception("Kunne ikke hente værdata: %s", e)
        return {"temp": "ukjent", "max": "ukjent", "min": "ukjent", "forhold": "varierende", "neste_6h": "varierende"}


def beregn_dagslys_endring(dato):
    """Beregner endring i dagslys siden siste solverv"""
    solverv = datetime.date(dato.year if dato.month > 6 else dato.year - 1, 12, 21)
    if dato.month > 6 and dato.day > 21:
        solverv = datetime.date(dato.year, 6, 21)

    dager_siden = abs((dato - solverv).days)
    minutter = round(dager_siden * 4)
    status = "lengre" if solverv.month == 12 else "kortere"
    return f"Dagen er nå ca. {minutter} minutter {status} enn ved solverv."


def hent_sol_data(dato):
    """Henter soltider og konverterer til riktig norsk tid"""
    url = f"https://api.met.no/weatherapi/sunrise/3.0/sun?lat=59.28&lon=11.11&date={dato.strftime('%Y-%m-%d')}"
    headers = {'User-Agent': 'SarpsborgArbeiderbladBot/1.0 (ocb@sa.no)'}
    try:
        response = requests_get(url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        res = response.json()

        opp_iso = res['properties']['sunrise']['time']
        ned_iso = res['properties']['sunset']['time']

        opp_iso = opp_iso.replace('Z', '+00:00')
        ned_iso = ned_iso.replace('Z', '+00:00')

        opp_dt = datetime.datetime.fromisoformat(opp_iso).astimezone(OSLO_TZ)
        ned_dt = datetime.datetime.fromisoformat(ned_iso).astimezone(OSLO_TZ)

        return {"opp": opp_dt.strftime('%H:%M'), "ned": ned_dt.strftime('%H:%M')}
    except Exception as e:
        logger.exception("Kunne ikke hente soldata: %s", e)
        return None


def tekst_til_cue_html(tekst):
    """Konverterer ren tekst fra Gemini til Cue-kompatibel HTML"""
    sikker_tekst = html.escape(tekst)
    linjer = sikker_tekst.split('\n')
    html_deler = []
    for linje in linjer:
        linje = linje.strip()
        if not linje:
            continue
        if any(tittel in linje for tittel in ("Dagen i dag", "Flaggdag", "Været", "Trafikk", "Strømprisen")):
            html_deler.append(f"<h2>{linje}</h2>")
        elif not linje.startswith("God morgen"):
            html_deler.append(f"<p>{linje}</p>")
    return "".join(html_deler)


def lag_cue_lenke(tittel, brødtekst_ren):
    """Genererer URI-en for å opprette artikkel i Cue"""
    body_html = tekst_til_cue_html(brødtekst_ren)

    if len(body_html) > 5000:
        body_html = body_html[:5000] + "<p>... (tekst kuttet pga lengde)</p>"

    model = "story"
    server = f"{CUE_HOST}/{PUB_CODE}"
    cue = f"{server}/cue"
    webservice = f"{server}/webservice"

    # Bygger adresser for publikasjon
    modeluri = f"{webservice}/escenic/publication/{PUB_NAME}/model/content-type/{model}"
    publication_uri = f"{webservice}/escenic/publication/{PUB_NAME}/"

    sourceid = f"Redaksjonen-{datetime.datetime.now(OSLO_TZ).strftime('%y%m%d-%H%M%S')}"
    mimetype = f"x-ece/new-content; type={model}"

    # Bruker homePublication i stedet for homeSectionUri for å unngå 404 på seksjons-ID
    extra_data = {
        "modelURI": {
            "string": modeluri,
            "$class": "URI"
        },
        "homePublication": {
            "string": publication_uri,
            "$class": "URI"
        },
        "container": False,
        "values": {
            "title": tittel,
            "body": body_html,
            "byline": "Redaksjonen"
        }
    }

    # Koding slik at Cue klarer å lese JSON-formatet riktig
    mimetype_encoded = urllib.parse.quote(mimetype)
    extra_encoded = urllib.parse.quote(json.dumps(extra_data, separators=(',', ':')))

    params = f"uri={sourceid}&mimetype={mimetype_encoded}&extra={extra_encoded}"
    cue_url = f"{cue}/#/main?{params}"

    return cue_url


def hent_wikipedia_data(måned, dag):
    """Henter historiske hendelser fra norsk Wikipedia"""
    url = f"https://no.wikipedia.org/api/rest_v1/feed/onthisday/all/{måned:02d}/{dag:02d}"
    headers = {'User-Agent': 'SarpsborgArbeiderbladBot/1.0 (ocb@sa.no)'}
    try:
        response = requests_get(url, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()
        res = response.json()
        events = res.get('events') or res.get('selected') or []
        resultater = [e['text'] for e in events if isinstance(e, dict) and 'text' in e]
        if resultater:
            return resultater[:10]
        # Fallback til engelsk hvis norsk er tom
        url_en = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{måned:02d}/{dag:02d}"
        response_en = requests_get(url_en, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        response_en.raise_for_status()
        res_en = response_en.json()
        events_en = res_en.get('events') or res_en.get('selected') or []
        return [e['text'] for e in events_en if isinstance(e, dict) and 'text' in e][:10]
    except Exception as e:
        logger.exception("Kunne ikke hente Wikipedia-data: %s", e)
        return []


def lag_gemini_prompt(morgen, wiki_hendelser, vaer, sol, flaggdager):
    """Lager prompten slik at den kan testes uten Gemini-kall."""
    navnedag = hent_navnedag(morgen.month, morgen.day)
    ukedag = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"][morgen.weekday()]
    måned_navn = [
        "januar", "februar", "mars", "april", "mai", "juni", "juli", "august",
        "september", "oktober", "november", "desember",
    ][morgen.month - 1]
    dato_full = f"{ukedag} {morgen.day}. {måned_navn} {morgen.year}"

    sol_info = f"Sola står opp kl. {sol['opp']} og går ned kl. {sol['ned']}." if sol else ""
    lys_endring = beregn_dagslys_endring(morgen)
    historiske_hendelser = chr(10).join(wiki_hendelser) if wiki_hendelser else "Ingen hendelser hentet."

    if flaggdager:
        flaggdag_data = f"Offisiell norsk flaggdag: {formater_flaggdager(flaggdager)}"
        intro_instruks = (
            "Datoen er offisiell norsk flaggdag. Nevn flaggdagen naturlig allerede i ingressen, "
            "og la den komme først under 'Dagen i dag' før øvrige historiske hendelser."
        )
        dagen_i_dag_instruks = (
            "Fremhev flaggdagen først. Gjenfortell deretter 3 korte hendelser fra listen over "
            "på en engasjerende måte. Prioriter norske forhold."
        )
    else:
        flaggdag_data = ""
        intro_instruks = ""
        dagen_i_dag_instruks = (
            "Gjenfortell 3 korte hendelser fra listen over på en engasjerende måte. "
            "Prioriter norske forhold."
        )

    return f"""
    Du er journalist i Sarpsborg Arbeiderblad. Skriv spalten "God morgen, Sarpsborg!" for {dato_full}.
    DATA:
    Navnedag: {navnedag}.
    {flaggdag_data}
    Vær nå: {vaer['temp']} grader, {vaer['forhold']}.
    Max i dag: {vaer['max']} grader.
    Sol: {sol_info} {lys_endring}
    Historiske hendelser: {historiske_hendelser}.

    STRUKTUR:
    1. Tittel: God morgen, Sarpsborg!
    2. Intro med dato og hyggelig hilsen. {intro_instruks}
    3. Navnedag: Nevn at {navnedag} har navnedag.
    4. Mellomtittel: Dagen i dag ({dagen_i_dag_instruks})
    5. Mellomtittel: Været (Nevn {vaer['temp']} grader nå og at det blir opptil {vaer['max']} grader i dag. Beskriv forholdene {vaer['forhold']}. Inkluder soltider og at {lys_endring}).
    6. [Plass for værembed her].
    7. Mellomtittel: Trafikk
    8. Skriv: "Skal du ut i trafikken? Se her hvordan trafikken er nå og hvor lang reisetid du bør beregne:"
    9. [Plass for reisetid-embed her]
    10. Skriv: "Her kan du se trafikken over Sarpsbrua direkte:"
    11. [Plass for Sarpsbrua-embed her]
    12. Mellomtittel: Strømprisen
    13. Avslutning: "Vi ønsker alle våre lesere en strålende dag!"

    KRAV: KUN REN TEKST. Ingen Markdown-formatering som # eller *.
    """


def generer_artikkeltekst(morgen, wiki_hendelser, vaer, sol, flaggdager, gemini_api_key=None):
    """Bruker Gemini for å skrive selve teksten."""
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Mangler avhengighet: google-genai. Kjør `pip install -r requirements.txt`.") from exc

    prompt = lag_gemini_prompt(morgen, wiki_hendelser, vaer, sol, flaggdager)
    client = genai.Client(api_key=gemini_api_key or hent_påkrevd_env("GEMINI_API_KEY"))
    try:
        res = client.models.generate_content(model=GEMINI_MODELL, contents=prompt)
        if not getattr(res, "text", None):
            raise RuntimeError("Gemini returnerte ingen tekst")
        return res.text
    except Exception as e:
        logger.exception("Kunne ikke generere artikkeltekst: %s", e)
        return "Kunne ikke generere tekst pga teknisk feil."


def bygg_ferdig_epost_html(artikkel_tekst, cue_url):
    """Lager e-posten med Cue-knapp"""
    artikkel_preview = html.escape(artikkel_tekst)
    return f"""
    <html>
    <body style="font-family: sans-serif; line-height: 1.6; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 650px; margin: auto; border: 1px solid #ddd; padding: 30px; border-radius: 8px; background: white;">
            <h2 style="color: #d32f2f; margin-top: 0;">God morgen, Sarpsborg er klar!</h2>

            <a href="{cue_url}" style="display: inline-block; padding: 18px 30px; background-color: #2e7d32; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-bottom: 25px;">
                🚀 OPPRETT KLADD I CUE
            </a>

            <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 25px;">
                <strong>💡 Sjekkliste for journalist:</strong><br>
                Husk å se om det skjer noe spesielt i dag på <a href="https://www.sa.no/vis/hvaskjer/">Hva skjer i Sarpsborg</a> før du publiserer. Husk også å dobbeltsjekke at faktaene i saken stemmer 📖.
            </div>

            <div style="white-space: pre-wrap; background: #fafafa; padding: 20px; border: 1px solid #eee; font-size: 15px;">
{artikkel_preview}
            </div>
        </div>
    </body>
    </html>
    """


def send_epost(html_epost, mål_dato, email_sender, email_password):
    msg = MIMEMultipart()
    msg['From'] = email_sender
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"God morgen, Sarpsborg ({mål_dato.strftime('%d.%m')})"
    msg.attach(MIMEText(html_epost, 'html'))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
        smtp.starttls()
        smtp.login(email_sender, email_password)
        smtp.send_message(msg)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generer God morgen, Sarpsborg og send e-post.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generer tekst og Cue-lenke, men ikke send e-post.",
    )
    parser.add_argument(
        "--dato",
        help="Dato som skal genereres i ISO-format, for eksempel 2026-05-17. Standard er morgendagen i norsk tid.",
    )
    return parser.parse_args(argv)


def hovedprosess(dry_run=False, mål_dato=None):
    mål_dato = mål_dato or (datetime.datetime.now(OSLO_TZ).date() + datetime.timedelta(days=1))
    gemini_api_key = hent_påkrevd_env("GEMINI_API_KEY")

    email_sender = hent_valgfri_env("EMAIL_SENDER")
    email_password = hent_valgfri_env("EMAIL_PASSWORD")
    if not dry_run:
        email_sender = email_sender or hent_påkrevd_env("EMAIL_SENDER")
        email_password = email_password or hent_påkrevd_env("EMAIL_PASSWORD")

    logger.info("Starter generering for %s", mål_dato.strftime('%d.%m.%Y'))

    flaggdager = hent_offisielle_flaggdager(mål_dato)
    if flaggdager:
        logger.info("Offisiell flaggdag: %s", formater_flaggdager(flaggdager))

    wiki = hent_wikipedia_data(mål_dato.month, mål_dato.day)
    vaer = hent_vaer_data(mål_dato)
    sol = hent_sol_data(mål_dato)

    artikkel = generer_artikkeltekst(mål_dato, wiki, vaer, sol, flaggdager, gemini_api_key=gemini_api_key)
    cue_url = lag_cue_lenke("God morgen, Sarpsborg!", artikkel)
    html_epost = bygg_ferdig_epost_html(artikkel, cue_url)

    if dry_run:
        print("DRY RUN: E-post blir ikke sendt.")
        print(f"Dato: {mål_dato.isoformat()}")
        print(f"Flaggdag: {formater_flaggdager(flaggdager)}")
        print(f"Cue-lenke: {cue_url}")
        print("\n--- Artikkeltekst ---\n")
        print(artikkel)
        return {"artikkel": artikkel, "cue_url": cue_url, "flaggdager": flaggdager}

    send_epost(html_epost, mål_dato, email_sender, email_password)
    logger.info("E-post sendt til %s", EMAIL_RECEIVER)
    return {"artikkel": artikkel, "cue_url": cue_url, "flaggdager": flaggdager}


def main(argv=None):
    setup_logging()
    args = parse_args(argv)
    try:
        mål_dato = datetime.date.fromisoformat(args.dato) if args.dato else None
        hovedprosess(dry_run=args.dry_run, mål_dato=mål_dato)
    except Exception as e:
        logger.error("%s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
