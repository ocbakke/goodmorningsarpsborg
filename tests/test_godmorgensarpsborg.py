import datetime
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "GodMorgenSarpsborg",
    PROJECT_ROOT / "GodMorgenSarpsborg.py",
)
gms = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gms)


class GodMorgenSarpsborgTest(unittest.TestCase):
    def test_henter_navnedag_fra_datafil(self):
        self.assertEqual(gms.hent_navnedag(5, 17), "Harald og Ragnhild")

    def test_beregner_paskedag(self):
        self.assertEqual(gms.beregn_paskedag(2026), datetime.date(2026, 4, 5))

    def test_finner_fast_offisiell_flaggdag(self):
        flaggdager = gms.hent_offisielle_flaggdager(datetime.date(2026, 5, 17))
        self.assertEqual([f["name"] for f in flaggdager], ["Grunnlovsdagen"])

    def test_finner_bevegelige_offisielle_flaggdager(self):
        påske = gms.hent_offisielle_flaggdager(datetime.date(2026, 4, 5))
        pinse = gms.hent_offisielle_flaggdager(datetime.date(2026, 5, 24))

        self.assertEqual([f["name"] for f in påske], ["1. påskedag"])
        self.assertEqual([f["name"] for f in pinse], ["1. pinsedag"])

    def test_finner_faste_norske_merkedager(self):
        kvinnedagen = gms.hent_norske_merkedager(datetime.date(2026, 3, 8))
        halloween = gms.hent_norske_merkedager(datetime.date(2026, 10, 31))

        self.assertIn("Kvinnedagen", [m["name"] for m in kvinnedagen])
        self.assertIn("Halloween", [m["name"] for m in halloween])

    def test_finner_morsdag_og_farsdag(self):
        morsdag = gms.hent_norske_merkedager(datetime.date(2026, 2, 8))
        farsdag = gms.hent_norske_merkedager(datetime.date(2026, 11, 8))

        self.assertEqual([m["name"] for m in morsdag], ["Morsdag"])
        self.assertEqual([m["name"] for m in farsdag], ["Farsdag"])

    def test_finner_bevegelige_helligdager_som_merkedager(self):
        langfredag = gms.hent_norske_merkedager(datetime.date(2026, 4, 3))
        kristi_himmelfartsdag = gms.hent_norske_merkedager(datetime.date(2026, 5, 14))

        self.assertEqual([m["name"] for m in langfredag], ["Langfredag"])
        self.assertTrue(langfredag[0]["public_holiday"])
        self.assertEqual([m["name"] for m in kristi_himmelfartsdag], ["Kristi himmelfartsdag"])

    def test_kan_legge_inn_ekstra_flaggdag_for_stortingsvalg(self):
        with patch.dict(os.environ, {"EKSTRA_FLAGGDAGER": "2029-09-10=Stortingsvalgdag"}):
            flaggdager = gms.hent_offisielle_flaggdager(datetime.date(2029, 9, 10))

        self.assertEqual([f["name"] for f in flaggdager], ["Stortingsvalgdag"])

    def test_gemini_prompt_fremhever_flaggdag(self):
        dato = datetime.date(2026, 5, 17)
        prompt = gms.lag_gemini_prompt(
            dato,
            ["1814: Norges Grunnlov ble undertegnet på Eidsvoll."],
            {"temp": 12, "max": 16, "forhold": "lettskyet"},
            {"opp": "04:30", "ned": "22:00"},
            gms.hent_offisielle_flaggdager(dato),
        )

        self.assertIn("Grunnlovsdagen", prompt)
        self.assertIn("allerede i ingressen", prompt)
        self.assertIn("fremhev flaggdagen først", prompt.lower())

    def test_gemini_prompt_tar_med_merkedag_uten_flaggdag(self):
        dato = datetime.date(2026, 10, 31)
        prompt = gms.lag_gemini_prompt(
            dato,
            ["1517: Martin Luther offentliggjorde sine teser."],
            {"temp": 8, "max": 10, "forhold": "regn"},
            {"opp": "07:30", "ned": "16:30"},
            [],
        )

        self.assertIn("Halloween", prompt)
        self.assertIn("Norske merkedager", prompt)
        self.assertIn("forklar kort hva dagen markerer i Norge", prompt)
        self.assertNotIn("Offisiell norsk flaggdag", prompt)

    def test_gemini_prompt_utelater_flaggdag_nar_det_ikke_er_flaggdag(self):
        dato = datetime.date(2026, 5, 12)
        prompt = gms.lag_gemini_prompt(
            dato,
            ["1820: Florence Nightingale ble født."],
            {"temp": 12, "max": 16, "forhold": "lettskyet"},
            {"opp": "04:45", "ned": "21:45"},
            [],
        )

        self.assertNotIn("flaggdag", prompt.lower())
        self.assertNotIn("offisiell norsk", prompt.lower())

    def test_epost_preview_escaper_artikkeltekst(self):
        html = gms.bygg_ferdig_epost_html("<script>alert('x')</script>", "https://example.test")

        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert", html)

    def test_pakrevd_env_feiler_for_manglende_verdi(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                gms.hent_påkrevd_env("GEMINI_API_KEY")


if __name__ == "__main__":
    unittest.main()
