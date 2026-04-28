import unittest

from audiobooker.utils import extract_year, extractor_narrator, normalize_name, fuzzy_match, score_book
from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator, normalize_language
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


class TestFuzzyMatch(unittest.TestCase):
    def test_exact_substring(self):
        self.assertTrue(fuzzy_match("sherlock", "The Adventures of Sherlock Holmes"))

    def test_close_spelling(self):
        self.assertTrue(fuzzy_match("lovcraft", "lovecraft"))

    def test_no_match(self):
        self.assertFalse(fuzzy_match("xyz123", "The Great Gatsby"))

    def test_case_insensitive(self):
        self.assertTrue(fuzzy_match("HORROR", "horror"))

    def test_similar_names_not_matched(self):
        # "Stephen King" must not match "Stephen Crane"
        self.assertFalse(fuzzy_match("Stephen King", "Stephen Crane"))

    def test_partial_name_in_full(self):
        self.assertTrue(fuzzy_match("Conan Doyle", "Sir Arthur Conan Doyle"))


class TestNormalizeLanguage(unittest.TestCase):
    def test_full_english(self):
        self.assertEqual(normalize_language("English"), "en")

    def test_already_code(self):
        self.assertEqual(normalize_language("fr"), "fr")

    def test_mixed_case(self):
        self.assertEqual(normalize_language("FRENCH"), "fr")

    def test_empty(self):
        self.assertEqual(normalize_language(""), "")


class TestAudioBookHash(unittest.TestCase):
    def test_same_book_equals(self):
        a = AudioBook(title="Frankenstein", authors=[BookAuthor(first_name="Mary", last_name="Shelley")])
        b = AudioBook(title="Frankenstein", authors=[BookAuthor(first_name="Mary", last_name="Shelley")])
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))

    def test_different_books_not_equal(self):
        a = AudioBook(title="Frankenstein", authors=[BookAuthor(last_name="Shelley")])
        b = AudioBook(title="Dracula", authors=[BookAuthor(last_name="Stoker")])
        self.assertNotEqual(a, b)

    def test_dedup_in_set(self):
        a = AudioBook(title="Dracula", authors=[BookAuthor(last_name="Stoker")])
        b = AudioBook(title="Dracula", authors=[BookAuthor(last_name="Stoker")])
        self.assertEqual(len({a, b}), 1)

    def test_source_field(self):
        book = AudioBook(title="Test", source="Librivox")
        self.assertEqual(book.source, "Librivox")

    def test_language_normalized(self):
        book = AudioBook(title="Test", language="English")
        self.assertEqual(book.language, "en")


class TestScoreBook(unittest.TestCase):
    def _book(self, title, authors=None, tags=None, narrator=None):
        return AudioBook(
            title=title,
            authors=authors or [],
            tags=tags or [],
            narrator=narrator,
        )

    def test_exact_title_scores_highest(self):
        target = self._book("Harry Potter and the Philosopher's Stone",
                            authors=[BookAuthor(first_name="J.K.", last_name="Rowling")])
        other = self._book("Great Big Treasury of Beatrix Potter",
                           authors=[BookAuthor(first_name="Beatrix", last_name="Potter")])
        s_target = score_book("Harry Potter", target, "search_by_title")
        s_other = score_book("Harry Potter", other, "search_by_title")
        self.assertGreater(s_target, s_other)

    def test_author_method_ignores_title(self):
        king = self._book("Fairy Tale", authors=[BookAuthor(first_name="Stephen", last_name="King")])
        crane = self._book("Red Badge of Courage", authors=[BookAuthor(first_name="Stephen", last_name="Crane")])
        s_king = score_book("Stephen King", king, "search_by_author")
        s_crane = score_book("Stephen King", crane, "search_by_author")
        self.assertGreater(s_king, s_crane)

    def test_narrator_method_scores_narrator(self):
        book = self._book("It", narrator=AudiobookNarrator(first_name="Frank", last_name="Muller"))
        score = score_book("Frank Muller", book, "search_by_narrator")
        self.assertGreater(score, 0.9)

    def test_tag_method_scores_tag(self):
        book = self._book("Letters of Insurgents", tags=["Anarchy", "Radio Drama"])
        score = score_book("Anarchy", book, "search_by_tag")
        self.assertGreater(score, 0.9)

    def test_min_score_above_zero_for_match(self):
        book = self._book("The Dark Tower", authors=[BookAuthor(first_name="Stephen", last_name="King")])
        self.assertGreater(score_book("Dark Tower", book, "search_by_title"), 0.5)

    def test_irrelevant_book_scores_low(self):
        book = self._book("Romeo and Juliet", authors=[BookAuthor(first_name="William", last_name="Shakespeare")])
        self.assertLess(score_book("Lovecraft", book, "search_by_author"), 0.3)


if __name__ == "__main__":
    unittest.main()
