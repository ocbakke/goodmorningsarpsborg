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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Oppdatert til nyeste modellversjon
GEMINI_MODELL = "gemini-3-flash"

# E-post konfigurasjon (Google Workspace / Gmail)
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")  
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 
EMAIL_RECEIVER = "redaksjonen@sa.no"
SMTP_SERVER = "smtp.gmail.com"
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
    Din oppgave er å skrive spalten "God morgen, Sarpsborg!".
    
    VIKTIG KONTEKST:
    Denne teksten skal publiseres kl. 06:00 den {dato_tekst}. 
    Du skal skrive teksten som om det er akkurat denne dagen NÅ. 
    Bruk nåtidsform (f.eks. "I dag er det...", "Slik ser været ut i dag...").
    
    Historiske hendelser (på engelsk):
    {chr(10).join(wiki_data['hendelser'])}
    
    Dagens navnedager er: {wiki_data['navnedager']}
    
    Været for Sarpsborg i dag (fiktiv data): Delvis skyet, 8 grader, svak bris fra sørøst.
    
    OPPGAVE:
    1. Start med en hyggelig hilsen ("Det er [ukedag] [dato]...").
    2. Lag en seksjon med en <h3> med tittelen "Dagen i dag".
    3. Lag en <ul> (HTML-liste) som trekker frem de 3 mest interessante historiske hendelsene omskrevet til norsk.
    4. Lag en kort setning om hvem som har navnedag.
    5. Legg til en seksjon med en <h3> med tittelen "Vær", og skriv et kort, vennlig avsnitt om været med lokal tilknytning til Sarpsborg.
    
    KRAV:
    - Formater svaret KUN i ren HTML uten ```html tags rundt.
    - Bruk kun <h3> og <ul>/<li> for strukturering.
    - Tone: Morgenfrisk, lokal og hyggelig.
    """
    
    response = client.models.generate_content(
        model=GEMINI_MODELL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=1500)
    )
    return response.text

def bygg_ferdig_html(artikkel_tekst):
    """Setter sammen KI-teksten med de faktiske smartembedsene fra Cue"""
    # Vi rydder URL-ene slik at de er 100% rene for Cue-innliming
    html_mal = f"""
    <html>
    <body style="font-family: sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 650px; margin: auto; background: white; border: 1px solid #ddd; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #d32f2f; margin-top: 0;">Forslag: God morgen, Sarpsborg</h1>
            
            <div style="background: #fff3e0; padding: 15px; border-left: 5px solid #ff9800; margin-bottom: 25px;">
                <strong>Instruks for redaksjonen:</strong><br>
                Dette er et KI-generert forslag for i morgen. Kopier HTML-koden nedenfor og lim den inn i en HTML-blokk i Cue.
            </div>
            
            <hr style="border: 0; border-top: 1px solid #eee; margin: 25px 0;">
            
            <div style="padding: 15px; border: 2px dashed #d32f2f; background: #fafafa; font-family: monospace; font-size: 13px; color: #444; overflow-x: auto;">
                &lt;div class="sa-god-morgen-article"&gt;<br>
                {artikkel_tekst}<br>
                &lt;div class="cue-embed"&gt;&lt;a href="[https://www.sa.no/api/graff/v1/component/vaer-melding?id=363100](https://www.sa.no/api/graff/v1/component/vaer-melding?id=363100)"&gt;Vær&lt;/a&gt;&lt;/div&gt;<br>
                &lt;hr&gt;<br>
                &lt;h3&gt;Trafikk&lt;/h3&gt;<br>
                &lt;div class="cue-embed"&gt;&lt;a href="[https://www.sa.no/api/graff/v1/component/trafikk-tabell?key=sarpsborg](https://www.sa.no/api/graff/v1/component/trafikk-tabell?key=sarpsborg)"&gt;Trafikk&lt;/a&gt;&lt;/div&gt;<br>
                &lt;div class="cue-embed"&gt;&lt;a href="[https://www.sa.no/api/graff/v1/component/trafikk-webkamera](https://www.sa.no/api/graff/v1/component/trafikk-webkamera)"&gt;Kamera&lt;/a&gt;&lt;/div&gt;<br>
                &lt;hr&gt;<br>
                &lt;h3&gt;Strømprisen&lt;/h3&gt;<br>
                &lt;div class="cue-embed"&gt;&lt;a href="[https://www.sa.no/api/graff/v1/component/strom-timepris](https://www.sa.no/api/graff/v1/component/strom-timepris)"&gt;Strøm&lt;/a&gt;&lt;/div&gt;<br>
                &lt;hr&gt;<br>
                &lt;div class="cue-embed"&gt;&lt;a href="[https://services.api.no/api/componenthub/v1/dashboard?component=reels-carousel_reelsCarousel&amp;publication=www.sa.no&amp;tag=Sa.tv&amp;title=Siste+videoer+fra+sa.no&amp;limit=20](https://services.api.no/api/componenthub/v1/dashboard?component=reels-carousel_reelsCarousel&amp;publication=www.sa.no&amp;tag=Sa.tv&amp;title=Siste+videoer+fra+sa.no&amp;limit=20)"&gt;Video&lt;/a&gt;&lt;/div&gt;<br>
                &lt;/div&gt;
            </div>
            
            <div style="margin-top: 25px; font-size: 14px; color: #666;">
                <h3>Forhåndsvisning:</h3>
                <div style="border: 1px solid #eee; padding: 15px; background: #fff;">
                    {artikkel_tekst}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_mal

def send_epost(html_innhold, dato_str):
    """Sender det ferdige resultatet på e-post via SMTP"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("E-post-legitimasjon mangler i miljøvariabler.")
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
        print(f"E-post sendt til {EMAIL_RECEIVER}!")
    except Exception as e:
        print(f"Feil ved sending av e-post: {e}")

def hovedprosess():
    # Vi henter data for MORGENDAGEN
    i_dag = datetime.datetime.now()
    morgen = i_dag + datetime.timedelta(days=1)
    
    ukedager = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
    måneder = ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "desember"]
    
    dato_tekst = f"{ukedager[morgen.weekday()]} {morgen.day}. {måneder[morgen.month - 1]}"
    print(f"Starter generering for: {dato_tekst}")
    
    wiki_data = hent_wikipedia_data(morgen.month, morgen.day)
    
    if wiki_data:
        artikkel_tekst = generer_artikkeltekst(dato_tekst, wiki_data)
        ferdig_html = bygg_ferdig_html(artikkel_tekst)
        
        # Send til redaksjonen
        send_epost(ferdig_html, dato_tekst)
        print("Prosess fullført uten feil.")
    else:
        print("Feil: Kunne ikke hente Wikipedia-data.")

if __name__ == "__main__":
    hovedprosess()
