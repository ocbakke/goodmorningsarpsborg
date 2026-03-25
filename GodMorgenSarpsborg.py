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
GEMINI_MODELL = "gemini-2.5-flash"

# E-post konfigurasjon (Google Workspace / Gmail)
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")  
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 
EMAIL_RECEIVER = "redaksjonen@sa.no"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Initialiser den nye genai-klienten
client = genai.Client(api_key=GEMINI_API_KEY)

def hent_navnedag(måned, dag):
    """Komplett database over norske navnedager basert på offisiell liste"""
    navnedager = {
        # JANUAR
        (1, 1): "Ingen navnedag (Jesu navnedag)", (1, 2): "Dagfinn og Dagfrid", (1, 3): "Alfred, Alf og Alva",
        (1, 4): "Roar og Roger", (1, 5): "Hanna og Hanne", (1, 6): "Aslaug, Aisha og Alex", (1, 7): "Eldbjørg og Knut",
        (1, 8): "Turid og Torfinn", (1, 9): "Gunnar og Gunn", (1, 10): "Sigmund, Sigrun og Sina",
        (1, 11): "Børge og Børre", (1, 12): "Nelly og Nataniel", (1, 13): "Gisle og Gislaug",
        (1, 14): "Herbjørn, Herbjørg og Hermine", (1, 15): "Laurits, Laura og Lykke",
        (1, 16): "Hjalmar, Hilmar og Hassan", (1, 17): "Anton, Tønnes og Tony", (1, 18): "Hildur og Hild",
        (1, 19): "Marius, Margunn og Matheo", (1, 20): "Fabian, Sebastian og Bastian",
        (1, 21): "Agnes, Agnete og Abdul", (1, 22): "Ivan, Vanja og Vanessa", (1, 23): "Emil, Emilie og Emma",
        (1, 24): "Joar, Jarle og Jarl", (1, 25): "Paul og Pål", (1, 26): "Øystein og Esten", (1, 27): "Gaute og Gry",
        (1, 28): "Karl, Karoline og Carlos", (1, 29): "Herdis, Hermod og Hermann", (1, 30): "Gunnhild og Gunda",
        (1, 31): "Idun og Ivar",
        # FEBRUAR
        (2, 1): "Birte og Bjarte", (2, 2): "Jomar, Jostein, Omar og Bianca", (2, 3): "Ansgar, Asgeir og Angelika",
        (2, 4): "Veronika og Vera", (2, 5): "Agate og Ågot", (2, 6): "Dortea, Dorte og Dominik",
        (2, 7): "Rikard og Rigmor", (2, 8): "Åshild, Åsne og Ådne", (2, 9): "Lone, Leikny og Levi",
        (2, 10): "Ingfrid og Ingrid", (2, 11): "Ingve og Yngve", (2, 12): "Randi og Ronja",
        (2, 13): "Svanhild og Scott", (2, 14): "Valentin og Valentina", (2, 15): "Sigbjørn, Silas og Sienna",
        (2, 16): "Julian, Juliane og Jill", (2, 17): "Aleksandra, Sandra og Sondre",
        (2, 18): "Frøydis, Frode og Fatima", (2, 19): "Ella, Elna og Ebba", (2, 20): "Halldis og Halldor",
        (2, 21): "Samuel, Selma og Celine", (2, 22): "Tina, Tim og Tilde", (2, 23): "Torstein og Torunn",
        (2, 24): "Mattias, Mattis og Mats", (2, 25): "Viktor, Viktoria og Vincent", (2, 26): "Inger og Ingjerd",
        (2, 27): "Leander, Laila og Lill", (2, 28): "Marina, Maren og Mira", (2, 29): "Ingen navnedag",
        # MARS
        (3, 1): "Audny og Audun", (3, 2): "Erna og Ernst", (3, 3): "Gunnbjørg, Gunnveig og Gunnlaug",
        (3, 4): "Ada, Adrian og Adele", (3, 5): "Patrick og Patricia", (3, 6): "Annfrid, Aida og Alida",
        (3, 7): "Arild, Are og Ali", (3, 8): "Beate, Betty og Bettina", (3, 9): "Sverre og Sindre",
        (3, 10): "Edel og Edle", (3, 11): "Edvin og Tale", (3, 12): "Gregor og Gro", (3, 13): "Greta og Grete",
        (3, 14): "Mathilde, Mette og Mille", (3, 15): "Christel, Christer og Chris", (3, 16): "Gudmund og Gudny",
        (3, 17): "Gjertrud og Trude", (3, 18): "Aleksander, Sander og Edvard", (3, 19): "Josef, Josefine og Joel",
        (3, 20): "Joakim og Kim", (3, 21): "Bendik, Bengt og Bent", (3, 22): "Paula og Pauline",
        (3, 23): "Gerda og Gerd", (3, 24): "Ulrikke og Rikke", (3, 25): "Maria, Marie og Mari",
        (3, 26): "Gabriel og Glenn", (3, 27): "Rudolf og Rudi", (3, 28): "Åsta og Åste", (3, 29): "Jonas og Jonatan",
        (3, 30): "Holger, Olga og Olai", (3, 31): "Vebjørn og Vegard",
        # APRIL
        (4, 1): "Aron, Arve og Arvid", (4, 2): "Sigvard og Sivert", (4, 3): "Gunnvald og Gunvor",
        (4, 4): "Nanna, Nancy og Nina", (4, 5): "Irene, Eirin og Eiril", (4, 6): "Åsmund og Asmund",
        (4, 7): "Oddveig og Oddvin", (4, 8): "Asle, Atle og Ava", (4, 9): "Rannveig og Rønnaug",
        (4, 10): "Ingvald og Ingveig", (4, 11): "Ylva og Ulf", (4, 12): "Julius og Julie", (4, 13): "Asta og Astrid",
        (4, 14): "Ellinor, Nora og Noah", (4, 15): "Oda, Odin og Odd", (4, 16): "Magnus, Mons og Mohammad",
        (4, 17): "Elise, Else og Elsa", (4, 18): "Eilen og Eilert", (4, 19): "Arnfinn, Arnstein og Alvin",
        (4, 20): "Kjellaug og Kjellrun", (4, 21): "Jeanette, Jannike og Jessica", (4, 22): "Oddgeir og Oddny",
        (4, 23): "Georg, Jørgen og Jørn", (4, 24): "Albert, Olaug og Olivia", (4, 25): "Markus, Mark og Marco",
        (4, 26): "Terese, Tea og Telma", (4, 27): "Charles, Charlotte og Lotte", (4, 28): "Vivi, Vivian og Viljar",
        (4, 29): "Toralf og Torolf", (4, 30): "Gina og Gitte",
        # MAI
        (5, 1): "Filip, Valborg og Filippa", (5, 2): "Åsa og Åse", (5, 3): "Gjermund og Gøril",
        (5, 4): "Monika, Mona og Milla", (5, 5): "Nicole, Noel og Noor", (5, 6): "Guri, Gyri og Gudbrand",
        (5, 7): "Maia, Mai og Maiken", (5, 8): "Åge, Åke og Åslaug", (5, 9): "Kasper, Jesper og Kaspian",
        (5, 10): "Asbjørg, Asbjørn og Espen", (5, 11): "Magda, Malvin og Madelen", (5, 12): "Normann og Norvald",
        (5, 13): "Linda, Line og Linn", (5, 14): "Kristian, Kristen og Karsten", (5, 15): "Hallvard og Halvor",
        (5, 16): "Sara, Siren og Samira", (5, 17): "Harald og Ragnhild", (5, 18): "Eirik, Erik og Erika",
        (5, 19): "Torjus, Torje og Truls", (5, 20): "Bjørnar og Bror", (5, 21): "Helene, Ellen og Eli",
        (5, 22): "Henning og Henny", (5, 23): "Oddleif og Oddlaug", (5, 24): "Ester og Iris",
        (5, 25): "Ragna og Ragnar", (5, 26): "Annbjørg, Annlaug og Anneli", (5, 27): "Katinka, Cato og Carmen",
        (5, 28): "Vilhelm, William og Willy", (5, 29): "Magnar, Magnhild og Mario", (5, 30): "Gard og Geir",
        (5, 31): "Pernille og Preben",
        # JUNI
        (6, 1): "June og Juni", (6, 2): "Runa, Runar og Rune", (6, 3): "Rasmus, Rakel og Rafael",
        (6, 4): "Heidi, Heid og Helmer", (6, 5): "Torbjørg, Torbjørn og Torben", (6, 6): "Gustav og Gyda",
        (6, 7): "Robert og Robin", (6, 8): "Renate og René", (6, 9): "Kolbjørn og Kassandra",
        (6, 10): "Ingolf og Ingunn", (6, 11): "Borgar, Bjørge og Bjørg", (6, 12): "Sigfrid, Sigrid og Siri",
        (6, 13): "Tone, Tonje og Tanja", (6, 14): "Erlend, Erland og Erle", (6, 15): "Vigdis, Viggo og Vilja",
        (6, 16): "Torhild, Toril og Tiril", (6, 17): "Botolv og Bodil", (6, 18): "Bjarne og Bjørn",
        (6, 19): "Erling, Elling og Ellie", (6, 20): "Sølve og Sølvi", (6, 21): "Agnar, Annar og Ahmed",
        (6, 22): "Håkon og Maud", (6, 23): "Elfrid, Eldrid og Elliot", (6, 24): "Johannes, Jon og Hans",
        (6, 25): "Jørund og Jorunn", (6, 26): "Jenny, Jonny og Jennifer", (6, 27): "Aina, Ina og Ine",
        (6, 28): "Lea, Leo og Leon", (6, 29): "Peter, Petter og Per", (6, 30): "Solbjørg, Solgunn og Sol",
        # JULI
        (7, 1): "Ask og Embla", (7, 2): "Kjartan og Kjellfrid", (7, 3): "Andrea, Andrine og André",
        (7, 4): "Ulrik og Ulla", (7, 5): "Mirjam, Mina og Michelle", (7, 6): "Torgrim og Torgunn",
        (7, 7): "Håvard, Hulda og Hussein", (7, 8): "Sunniva, Synnøve og Synne", (7, 9): "Gøran, Jøran og Ørjan",
        (7, 10): "Anita, Anja og Amina", (7, 11): "Kjetil og Kjell", (7, 12): "Elias, Eldar og Elida",
        (7, 13): "Mildrid, Melissa og Mia", (7, 14): "Solfrid, Solrun og Frøya", (7, 15): "Oddmund og Oddrun",
        (7, 16): "Susanne, Sanna og Saga", (7, 17): "Guttorm og Gorm", (7, 18): "Arnulf og Ørnulf",
        (7, 19): "Gerhard og Gjert", (7, 20): "Margareta, Margit og Marit", (7, 21): "Johanne, Janne og Jane",
        (7, 22): "Malene, Malin og Mali", (7, 23): "Brita, Brit og Britt", (7, 24): "Kristine, Kristin og Kristi",
        (7, 25): "Jakob, Jack og Jim", (7, 26): "Anna, Anne og Ane", (7, 27): "Marita og Rita",
        (7, 28): "Reidar og Reidun", (7, 29): "Olav, Ola og Ole", (7, 30): "Aurora, Audhild og Aud",
        (7, 31): "Elin, Eline og Elina",
        # AUGUST
        (8, 1): "Peder og Petra", (8, 2): "Karen, Karin og Karina", (8, 3): "Oline, Oliver og Olve",
        (8, 4): "Arnhild, Arna og Arne", (8, 5): "Osvald og Oskar", (8, 6): "Loke, Lilja og Luis",
        (8, 7): "Didrik og Doris", (8, 8): "Evy, Yvonne og Yasmin", (8, 9): "Ronald og Ronny",
        (8, 10): "Lorents, Lars og Lasse", (8, 11): "Torvald, Tarald og Tara", (8, 12): "Klara, Camilla og Lara",
        (8, 13): "Anny, Anine og Ann", (8, 14): "Stella og Storm", (8, 15): "Margot, Mary og Marielle",
        (8, 16): "Brage, Brynjulf og Brynhild", (8, 17): "Verner og Wenche", (8, 18): "Tormod, Torodd og Valdemar",
        (8, 19): "Sigvald og Sigve", (8, 20): "Bernhard og Bernt", (8, 21): "Ragnvald og Ragni",
        (8, 22): "Harriet og Harry", (8, 23): "Signe og Signy", (8, 24): "Belinda og Bertil",
        (8, 25): "Ludvig, Lovise og Louise", (8, 26): "Øyvind, Eivind og Even", (8, 27): "Roald og Rolf",
        (8, 28): "Artur, August og Angela", (8, 29): "Johan, Jone og Jo", (8, 30): "Benjamin og Ben",
        (8, 31): "Aria, Ariana og Ariel",
        # SEPTEMBER
        (9, 1): "Solveig og Solvor", (9, 2): "Lisa, Lise og Liss", (9, 3): "Alise, Alvhild og Vilde",
        (9, 4): "Ida, Idar og Iben", (9, 5): "Brede, Brian og Njål", (9, 6): "Siril og Siv", (9, 7): "Regine og Rose",
        (9, 8): "Amalie, Alma og Allan", (9, 9): "Trygve, Tyra og Trym", (9, 10): "Tord og Tor",
        (9, 11): "Dagny, Dag og Damian", (9, 12): "Jofrid og Jorid", (9, 13): "Stian og Stig",
        (9, 14): "Ingebjørg og Ingeborg", (9, 15): "Aslak, Eskil og Ailo", (9, 16): "Lillian, Lilly og Linnea",
        (9, 17): "Hildegunn og Hjørdis", (9, 18): "Henriette og Henry", (9, 19): "Konstanse, Connie og Kornelia",
        (9, 20): "Tobias og Tage", (9, 21): "Trine, Trond og Tamara", (9, 22): "Kyrre og Kåre",
        (9, 23): "Snorre og Snefrid", (9, 24): "Jan og Jens", (9, 25): "Ingvar og Yngvar",
        (9, 26): "Einar, Endre og Elvira", (9, 27): "Dagmar og Dagrun", (9, 28): "Lena, Lene og Elena",
        (9, 29): "Mikael, Mikal og Mikkel", (9, 30): "Helga, Helge og Hege",
        # OKTOBER
        (10, 1): "Rebekka og Remi", (10, 2): "Live, Liv og Linus", (10, 3): "Evald, Evelyn og Emine",
        (10, 4): "Frans, Frank og Fanny", (10, 5): "Brynjar, Boye og Bo", (10, 6): "Målfrid, Møyfrid og Mio",
        (10, 7): "Birgitte, Birgit og Berit", (10, 8): "Benedikte og Bente", (10, 9): "Leif, Liam og Dennis",
        (10, 10): "Fridtjof, Frida og Frits", (10, 11): "Kevin, Kennet og Kent", (10, 12): "Valter, Vibeke og Vilma",
        (10, 13): "Terje, Tarjei og Torgeir", (10, 14): "Kaia, Kai og Kaisa", (10, 15): "Hedvig og Hedda",
        (10, 16): "Finn, Felix og Ferdinand", (10, 17): "Marta, Marte og Mathea",
        (10, 18): "Kjersti, Kjerstin og Lukas", (10, 19): "Tora og Tore", (10, 20): "Henrik, Heine og Henrikke",
        (10, 21): "Bergljot, Birger og Birk", (10, 22): "Karianne, Karine og Kine", (10, 23): "Severin, Søren og Sean",
        (10, 24): "Eilif, Eivor og Emrik", (10, 25): "Margrete, Merete og Märta", (10, 26): "Amandus og Amanda",
        (10, 27): "Sturla og Sture", (10, 28): "Simon, Simen og Simone", (10, 29): "Norunn, Naomi og Nikoline",
        (10, 30): "Aksel og Ove", (10, 31): "Edit og Edna",
        # NOVEMBER
        (11, 1): "Veslemøy og Vetle", (11, 2): "Tove og Tuva", (11, 3): "Raymond og Roy",
        (11, 4): "Otto, Ottar og Otilie", (11, 5): "Egil, Egon og Eira", (11, 6): "Leonard, Lennart og Leonora",
        (11, 7): "Ingebrigt og Ingelin", (11, 8): "Ingvild og Yngvild", (11, 9): "Tordis, Teodor og Theo",
        (11, 10): "Gudbjørg og Gudveig", (11, 11): "Martin, Morten og Martine", (11, 12): "Torkjell, Torkil og Tomine",
        (11, 13): "Kirsten og Kirsti", (11, 14): "Fredrik, Fred og Freddy", (11, 15): "Oddfrid og Oddvar",
        (11, 16): "Edmund, Edgar og Emilian", (11, 17): "Hugo, Hogne og Hauk", (11, 18): "Magne og Magny",
        (11, 19): "Elisabet og Lisbet", (11, 20): "Halvdan og Helle", (11, 21): "Mariann, Marianne og Max",
        (11, 22): "Cecilie, Silje og Sissel", (11, 23): "Klement, Klaus og Klaudia", (11, 24): "Gudrun og Guro",
        (11, 25): "Katarina, Katrine og Kari", (11, 26): "Konrad og Kurt", (11, 27): "Torlaug, Torleif og Colin",
        (11, 28): "Ruben og Rut", (11, 29): "Sofie, Sonja og Sofia", (11, 30): "Andreas, Anders og Ana",
        # DESEMBER
        (12, 1): "Arnold, Arnljot og Arnt", (12, 2): "Borghild, Borgny og Bård", (12, 3): "Sveinung og Svein",
        (12, 4): "Barbara og Barbro", (12, 5): "Stine og Ståle", (12, 6): "Nikolai, Nils og Niklas",
        (12, 7): "Hallfrid, Hallstein og Hallgeir", (12, 8): "Marlene, Marion og Morgan", (12, 9): "Anniken og Annette",
        (12, 10): "Judit, James og Jardar", (12, 11): "Daniel, Dan og Daniela", (12, 12): "Pia og Peggy",
        (12, 13): "Lucia, Lydia og Luna", (12, 14): "Steinar og Stein", (12, 15): "Hilda og Hilde",
        (12, 16): "Oddbjørg og Oddbjørn", (12, 17): "Inga, Inge og Iman", (12, 18): "Kristoffer, Kate og Kristiane",
        (12, 19): "Iselin, Isak og Isa", (12, 20): "Abraham, Amund og Abel", (12, 21): "Tomas, Tom og Tommy",
        (12, 22): "Ingemar og Ingar", (12, 23): "Sigurd og Sjur", (12, 24): "Adam og Eva", (12, 25): "Ingen navnedag",
        (12, 26): "Stefan, Steffen og Steven", (12, 27): "Narve, Natalie og Nadia", (12, 28): "Unni, Une og Unn",
        (12, 29): "Vidar, Vemund og Vårin", (12, 30): "David, Diana og Dina", (12, 31): "Sylfest, Sylvia og Sylvi"
    }
    return navnedager.get((måned, dag), "Ingen navnedag")


def hent_wikipedia_data(måned, dag):
    """Henter hendelser fra Wikipedia med flertrinns fallback for å sikre innhold"""
    kilder = [
        f"https://no.wikipedia.org/api/rest_v1/feed/onthisday/all/{måned:02d}/{dag:02d}",
        f"https://no.wikipedia.org/api/rest_v1/feed/onthisday/selected/{måned:02d}/{dag:02d}",
        f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{måned:02d}/{dag:02d}"
    ]
    headers = {'User-Agent': 'SarpsborgArbeiderbladBot/1.0 (ocb@sa.no)'}
    for url in kilder:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                events = data.get('events') or data.get('selected') or []
                resultater = [e['text'] for e in events if isinstance(e, dict) and 'text' in e]
                if resultater: return resultater[:15]
        except:
            continue
    return []


def hent_vaer_data(mål_dato):
    """Henter utvidet værdata for Sarpsborg fra Met.no for en spesifikk dato"""
    url = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=59.28&lon=11.11"
    headers = {'User-Agent': 'SarpsborgArbeiderbladBot/1.0 (ocb@sa.no)'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        timeseries = data['properties']['timeseries']
        dato_str = mål_dato.strftime('%Y-%m-%d')
        dagens_data = [t for t in timeseries if t['time'].startswith(dato_str)]

        if not dagens_data:
            dagens_data = timeseries[:24]

        temp_liste = [t['data']['instant']['details']['air_temperature'] for t in dagens_data]
        max_temp = max(temp_liste)
        min_temp = min(temp_liste)

        temp_nu = dagens_data[0]['data']['instant']['details']['air_temperature']
        forhold_nu = dagens_data[0].get('data', {}).get('next_1_hours', {}).get('summary', {}).get('symbol_code',
                                                                                                   'varierende')

        midt_pa_dagen = dagens_data[len(dagens_data) // 2]
        utsikt = midt_pa_dagen.get('data', {}).get('next_6_hours', {}).get('summary', {}).get('symbol_code', forhold_nu)

        return {
            "temp": temp_nu,
            "max": max_temp,
            "min": min_temp,
            "forhold": forhold_nu.replace('_', ' '),
            "neste_6h": utsikt.replace('_', ' ')
        }
    except Exception as e:
        print(f"Vær-feil: {e}")
        return {"temp": "ukjent", "max": "ukjent", "min": "ukjent", "forhold": "varierende", "neste_6h": "varierende"}


def beregn_dagslys_endring(dato):
    """Beregner endring i dagslys siden siste solverv"""
    solverv = datetime.datetime(dato.year if dato.month > 6 else dato.year - 1, 12, 21)
    if dato.month > 6 and dato.day > 21:
        solverv = datetime.datetime(dato.year, 6, 21)

    dager_siden = abs((dato - solverv).days)
    minutter = round(dager_siden * 4)
    status = "lengre" if solverv.month == 12 else "kortere"
    return f"Dagen er nå ca. {minutter} minutter {status} enn ved solverv."


def hent_sol_data(dato):
    """Henter soltider"""
    url = f"https://api.met.no/weatherapi/sunrise/3.0/sun?lat=59.28&lon=11.11&date={dato.strftime('%Y-%m-%d')}&offset=+01:00"
    headers = {'User-Agent': 'SarpsborgArbeiderbladBot/1.0 (ocb@sa.no)'}
    try:
        res = requests.get(url, headers=headers).json()
        opp = res['properties']['sunrise']['time'][11:16]
        ned = res['properties']['sunset']['time'][11:16]
        return {"opp": opp, "ned": ned}
    except:
        return None


def generer_artikkeltekst(morgen, wiki_hendelser, vaer, sol):
    """Bruker Python-data for å generere teksten via Gemini"""
    dag_nr = morgen.timetuple().tm_yday
    skuddår = (morgen.year % 4 == 0 and (morgen.year % 100 != 0 or morgen.year % 400 == 0))
    dager_i_år = 366 if skuddår else 365
    dager_igjen = dager_i_år - dag_nr
    navnedag = hent_navnedag(morgen.month, morgen.day)
    ukedag = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"][morgen.weekday()]
    måned_navn = \
    ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august", "september", "oktober", "november",
     "desember"][morgen.month - 1]
    dato_full = f"{ukedag} {morgen.day}. {måned_navn} {morgen.year}"

    sol_info = f"Sola står opp kl. {sol['opp']} og går ned kl. {sol['ned']}." if sol else ""
    lys_endring = beregn_dagslys_endring(morgen)

    prompt = f"""
    Du er journalist i Sarpsborg Arbeiderblad. Skriv spalten "God morgen, Sarpsborg!" for {dato_full}.

    DATA DU SKAL BRUKE:
    - Dato: {dato_full} (Dag {dag_nr}/{dager_i_år}, {dager_igjen} igjen)
    - Navnedag: {navnedag}
    - TEMPERATUR HELE DAGEN: Laveste {vaer['min']}°C, høyeste {vaer['max']}°C.
    - FORHOLD NÅ: {vaer['temp']} grader, {vaer['forhold']}.
    - UTSIKT RESTEN AV DAGEN: {vaer['neste_6h']}.
    - SOL: {sol_info}. {lys_endring}
    - HISTORIE: {chr(10).join(wiki_hendelser)}

    STRUKTUR:
    1. Tittel: God morgen, Sarpsborg!
    2. Intro: Hyggelig hilsen med dato og dager igjen.
    3. Navnedag: Nevn {navnedag}.
    4. Mellomtittel: Dagen i dag
    5. Historie: Gjenfortell 3 korte hendelser fra listen. Prioriter Norge. Vær kortfattet!
    6. Mellomtittel: Været
    7. Vær-tekst: Beskriv været basert på tallene. Nevn {vaer['temp']} grader nå og at det blir opptil {vaer['max']} grader i dag. Ta med soltider og dagslys-endring.
    8. [Plass for værembed her]
    9. Mellomtittel: Trafikk
    10. Trafikk-tekst og embeds for reisetid, Sarpsbrua og E6.
    11. Mellomtittel: Strømprisen
    12. Strøm-tekst og embed.
    13. Avslutning: "Vi ønsker alle våre lesere en strålende dag!"

    VIKTIG: Sørg for at makstemperaturen på {vaer['max']} grader nevnes. Ingen # eller *.
    """
    for i in range(5):
        try:
            res = client.models.generate_content(
                model=GEMINI_MODELL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=3000)
            )
            if res.text: return res.text
        except errors.ServerError:
            time.sleep((2 ** i) + 1)
        except Exception:
            time.sleep(1)
    return "Feil ved generering av tekst."


def bygg_ferdig_html(artikkel_tekst):
    """Lager den ferdige e-posten"""
    return f"""
    <html>
    <body style="font-family: sans-serif; line-height: 1.6; padding: 20px;">
        <div style="max-width: 650px; margin: auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
            <h2 style="color: #d32f2f;">KI-forslag: God morgen, Sarpsborg</h2>
            <div style="white-space: pre-wrap; background: #fafafa; padding: 15px; border: 1px solid #eee;">
{artikkel_tekst}

--- SMART-EMBED LENKER ---
Vær: https://www.sa.no/api/graff/v1/component/vaer-melding?id=363100
Trafikk: https://www.sa.no/api/graff/v1/component/trafikk-tabell?key=sarpsborg
Kamera: https://www.sa.no/api/graff/v1/component/trafikk-webkamera
Strøm: https://www.sa.no/api/graff/v1/component/strom-timepris
Video: https://services.api.no/api/componenthub/v1/dashboard?component=reels-carousel_reelsCarousel&publication=www.sa.no&tag=Sa.tv&title=Siste+videoer+fra+sa.no&limit=20
            </div>
        </div>
    </body>
    </html>
    """


def send_epost(html, emne):
    """Sender e-post"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD: return
    msg = MIMEMultipart();
    msg['From'] = EMAIL_SENDER;
    msg['To'] = EMAIL_RECEIVER;
    msg['Subject'] = emne
    msg.attach(MIMEText(html, 'html'))
    try:
        s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT);
        s.starttls();
        s.login(EMAIL_SENDER, EMAIL_PASSWORD)
        s.send_message(msg);
        s.quit();
        print("E-post sendt!")
    except Exception as e:
        print(f"E-post-feil: {e}")


def hovedprosess():
    morgen = datetime.datetime.now() + datetime.timedelta(days=1)
    print(f"Starter generering for {morgen.strftime('%d.%m.%Y')}...")
    wiki = hent_wikipedia_data(morgen.month, morgen.day)
    vaer = hent_vaer_data(morgen)
    sol = hent_sol_data(morgen)
    artikkel = generer_artikkeltekst(morgen, wiki, vaer, sol)
    html = bygg_ferdig_html(artikkel)
    send_epost(html, f"God morgen, Sarpsborg ({morgen.strftime('%d.%m')})")


if __name__ == "__main__":
    hovedprosess()
