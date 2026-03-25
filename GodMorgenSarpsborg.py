import requests
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google import genai
from google.genai import types

# ==========================================
# KONFIGURASJON (Bruk miljøvariabler for sikkerhet)
# ==========================================
# I GitHub Actions setter du disse under Settings -> Secrets and variables -> Actions
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "DIN_API_NØKKEL_HER")
GEMINI_MODELL = "gemini-3-flash"

# E-post konfigurasjon
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")  # f.eks. en Gmail-adresse
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")  # App-passord for e-posten
EMAIL_RECEIVER = "redaksjonen@sa.no"
SMTP_SERVER = "smtp.gmail.com"  # Endre hvis dere bruker Outlook/annet
SMTP_PORT = 587

# Initialiser den nye genai-klienten
client = genai.Client(api_key=GEMINI_API_KEY)


def hent_wikipedia_data(måned, dag):
    """Henter hendelser fra engelsk Wikipedia for stabilitet"""
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{måned:02d}/{dag:02d}"
    headers = {
        'User-Agent': 'SarpsborgArbeiderbladBot/1.0 (kontakt@sa.no)',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        events_data = data.get('events', [])
        hendelser = []
        for event in events_data:
            if isinstance(event, dict) and 'text' in event:
                hendelser.append(event['text'])

        return {"hendelser": hendelser[:5], "navnedager": "Maria, Mari, Mareno"}
    except Exception as e:
        print(f"Feil ved henting av Wikipedia-data: {e}")
        return None


def generer_artikkeltekst(dato_tekst, wiki_data):
    """Bruker KI for å skrive brødteksten i saken"""
    prompt = f"""
    Du er morgen-journalist for lokalavisen Sarpsborg Arbeiderblad (SA).
    Skriv introduksjonen til den daglige spalten "God morgen, Sarpsborg!".

    Datoen i dag er {dato_tekst}.

    Her er historiske hendelser (på engelsk):
    {chr(10).join(wiki_data['hendelser'])}

    Dagens navnedager er: {wiki_data['navnedager']}

    Været for Sarpsborg i dag (fiktiv data): Delvis skyet, 8 grader, svak bris fra sørøst.

    OPPGAVE:
    1. Start med en hyggelig hilsen ("Det er [ukedag] [dato]...").
    2. Lag en seksjon med en <ul> (HTML-liste) som trekker frem de 3 mest interessante historiske hendelsene omskrevet til norsk.
    3. Lag en kort setning om hvem som har navnedag.
    4. Legg til et kort, vennlig avsnitt om været med lokal tilknytning.

    KRAV:
    - Formater svaret KUN i ren HTML uten ```html tags.
    - Bruk <h3> for mellomtitler.
    """

    response = client.models.generate_content(
        model=GEMINI_MODELL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=1500)
    )
    return response.text


def bygg_ferdig_html(artikkel_tekst):
    """Setter sammen KI-teksten med de faktiske smartembedsene fra Cue"""
    html_mal = f"""
    <html>
    <body style="font-family: sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: auto; border: 1px solid #eee; padding: 20px;">
            <h1 style="color: #d32f2f;">Forslag: God morgen, Sarpsborg</h1>
            <p style="background: #fff3e0; padding: 10px; border-left: 5px solid #ff9800;">
                <strong>Instruks:</strong> Kopier HTML-koden nedenfor og lim den inn i en HTML-blokk i Cue, eller bruk teksten som utgangspunkt.
            </p>
            <hr>
            {artikkel_tekst}

            <div class="cue-embeds" style="background: #f9f9f9; padding: 15px; border-radius: 8px;">
                <p><strong>Følgende embeds er inkludert i malen:</strong></p>
                <ul>
                    <li>Værvarsel (id=363100)</li>
                    <li>Trafikktabell (Sarpsborg)</li>
                    <li>Trafikkameraer</li>
                    <li>Strømpriser</li>
                    <li>SA.tv Video-plugg</li>
                </ul>
            </div>

            <div style="display:none;">
                <!-- HTML for Cue-innliming starter her -->
                <div class="sa-god-morgen-article">
                    {artikkel_tekst}
                    <div class="cue-embed"><a href="[https://www.sa.no/api/graff/v1/component/vaer-melding?id=363100](https://www.sa.no/api/graff/v1/component/vaer-melding?id=363100)">Vær</a></div>
                    <hr>
                    <h3>Trafikk</h3>
                    <div class="cue-embed"><a href="[https://www.sa.no/api/graff/v1/component/trafikk-tabell?key=sarpsborg](https://www.sa.no/api/graff/v1/component/trafikk-tabell?key=sarpsborg)">Trafikk</a></div>
                    <div class="cue-embed"><a href="[https://www.sa.no/api/graff/v1/component/trafikk-webkamera](https://www.sa.no/api/graff/v1/component/trafikk-webkamera)">Kamera</a></div>
                    <hr>
                    <h3>Strømprisen</h3>
                    <div class="cue-embed"><a href="[https://www.sa.no/api/graff/v1/component/strom-timepris](https://www.sa.no/api/graff/v1/component/strom-timepris)">Strøm</a></div>
                    <hr>
                    <div class="cue-embed"><a href="[https://services.api.no/api/componenthub/v1/dashboard?component=reels-carousel_reelsCarousel&publication=www.sa.no&tag=Sa.tv&title=Siste+videoer+fra+sa.no&limit=20](https://services.api.no/api/componenthub/v1/dashboard?component=reels-carousel_reelsCarousel&publication=www.sa.no&tag=Sa.tv&title=Siste+videoer+fra+sa.no&limit=20)">Video</a></div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_mal


def send_epost(html_innhold, dato_str):
    """Sender det ferdige resultatet på e-post"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("E-post-legitimasjon mangler. Hopper over sending.")
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"KI-forslag: God morgen, Sarpsborg ({dato_str})"

    msg.attach(MIMEText(html_innhold, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("E-post sendt til redaksjonen!")
    except Exception as e:
        print(f"Feil ved sending av e-post: {e}")


def hovedprosess():
    # Vi henter data for MORGENDAGEN hvis klokken er 11:00
    i_dag = datetime.datetime.now()
    morgen = i_dag + datetime.timedelta(days=1)

    ukedager = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    måneder = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober",
               "november", "desember"]

    dato_tekst = f"{ukedager[morgen.weekday()]} {morgen.day}. {måneder[morgen.month - 1]}"
    print(f"Genererer innhold for i morgen: {dato_tekst}")

    wiki_data = hent_wikipedia_data(morgen.month, morgen.day)

    if wiki_data:
        artikkel_tekst = generer_artikkeltekst(dato_tekst, wiki_data)
        ferdig_html = bygg_ferdig_html(artikkel_tekst)

        # Lagre fil lokalt (for debug i GitHub Actions)
        with open("forslag_morgenbrief.html", "w", encoding="utf-8") as f:
            f.write(ferdig_html)

        # Send til redaksjonen
        send_epost(ferdig_html, dato_tekst)
        print("Prosess fullført.")
    else:
        print("Feil: Ingen data hentet.")


if __name__ == "__main__":
    hovedprosess()
