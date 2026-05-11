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
        self.assertIn("fremhev flaggdagen først", prompt)

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
