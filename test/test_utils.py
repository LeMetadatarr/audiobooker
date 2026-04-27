import unittest

from audiobooker.utils import extract_year, extractor_narrator, normalize_name
from audiobooker.scrappers.loyalbooks import calc_runtime


class TestExtractorNarrator(unittest.TestCase):
    def test_single_read_by(self):
        narrator = extractor_narrator("1996 Stephen King – The Regulators Audiobook read by Frank Muller")
        self.assertEqual(narrator.first_name, "Frank")
        self.assertEqual(narrator.last_name, "Muller")

        narrator = extractor_narrator("The Shining Audiobook read by Campbell Scott")
        self.assertEqual(narrator.first_name, "Campbell")
        self.assertEqual(narrator.last_name, "Scott")

        narrator = extractor_narrator("Alice In Wonderland read by Natasha now has its own podcast")
        self.assertEqual(narrator.first_name, "Natasha")
        self.assertEqual(narrator.last_name, "")

    def test_audiobook_by(self):
        narrator = extractor_narrator("Harry Potter and the Chamber of Secrets Audiobook by Jim Dale")
        self.assertEqual(narrator.first_name, "Jim")
        self.assertEqual(narrator.last_name, "Dale")

        narrator = extractor_narrator("Pride and Prejudice Audiobook by Jane Austen")
        self.assertEqual(narrator.first_name, "Jane")
        self.assertEqual(narrator.last_name, "Austen")

    def test_narrated_by(self):
        narrator = extractor_narrator("The shadow over innsmouth by H.P. Lovecraft, narrated by Wayne June")
        self.assertEqual(narrator.first_name, "Wayne")
        self.assertEqual(narrator.last_name, "June")

        narrator = extractor_narrator("The Catcher in the Rye by J.D. Salinger, narrated by Matt Damon")
        self.assertEqual(narrator.first_name, "Matt")
        self.assertEqual(narrator.last_name, "Damon")

    def test_no_narrator(self):
        self.assertIsNone(extractor_narrator("The Great Gatsby"))


class TestExtractYear(unittest.TestCase):
    def test_year_present(self):
        self.assertEqual(extract_year("1996 Stephen King – The Regulators Audiobook read by Frank Muller"), 1996)
        self.assertEqual(extract_year("Harry Potter and the Chamber of Secrets (1998) Audiobook by Jim Dale"), 1998)

    def test_no_year(self):
        self.assertEqual(extract_year("The Great Gatsby"), 0)

    def test_multiple_years(self):
        self.assertEqual(extract_year("The Odyssey (2001) and Moby Dick (1954) Audiobook"), 2001)

    def test_year_in_sentence(self):
        self.assertEqual(extract_year("This is a sentence with the year 2022 in it."), 2022)


class TestNormalizeName(unittest.TestCase):
    def test_first_and_last(self):
        first, last = normalize_name("H. P. Lovecraft")
        self.assertEqual(first, "H.")
        self.assertEqual(last, "P. Lovecraft")

    def test_single_name(self):
        first, last = normalize_name("Plato")
        self.assertEqual(first, "Plato")
        self.assertEqual(last, "")

    def test_strips_parens(self):
        first, last = normalize_name("(H.G.) Wells")
        self.assertIn("Wells", last or first)

    def test_titlecase(self):
        first, last = normalize_name("jane austen")
        self.assertEqual(first, "Jane")
        self.assertEqual(last, "Austen")


class TestCalcRuntime(unittest.TestCase):
    def test_seconds_only(self):
        self.assertEqual(calc_runtime({"itunes_duration": "45"}), 45)

    def test_minutes_seconds(self):
        self.assertEqual(calc_runtime({"itunes_duration": "1:30"}), 90)

    def test_hours_minutes_seconds(self):
        self.assertEqual(calc_runtime({"itunes_duration": "1:02:03"}), 3723)

    def test_zero(self):
        self.assertEqual(calc_runtime({"itunes_duration": "0:00"}), 0)


if __name__ == "__main__":
    unittest.main()
