"""Extra coverage for audiobooker.base — equality, hash, narrator sync."""
import unittest
from unittest.mock import patch

from audiobooker.base import (
    AudioBook,
    AudiobookNarrator,
    BookAuthor,
    normalize_language,
)


class TestNormalizeLanguage(unittest.TestCase):
    def test_region_subtag(self):
        self.assertEqual(normalize_language("en-US"), "en")
        self.assertEqual(normalize_language("pt_BR"), "pt")

    def test_unknown_long_string(self):
        # "swahili" not in map, len != 2, no startswith match -> returns input
        self.assertEqual(normalize_language("swahili"), "swahili")

    def test_prefix_match(self):
        # "germ" prefix matches "germ"an
        self.assertEqual(normalize_language("germ"), "de")


class TestAuthorEquality(unittest.TestCase):
    def test_equal_case_insensitive(self):
        a = BookAuthor(first_name="Mary", last_name="Shelley")
        b = BookAuthor(first_name="MARY", last_name="shelley")
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))

    def test_not_equal_to_non_author(self):
        a = BookAuthor(first_name="Mary", last_name="Shelley")
        self.assertNotEqual(a, "Mary Shelley")


class TestNarratorEquality(unittest.TestCase):
    def test_equal_case_insensitive(self):
        a = AudiobookNarrator(first_name="Frank", last_name="Muller")
        b = AudiobookNarrator(first_name="FRANK", last_name="MULLER")
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))

    def test_not_equal_to_non_narrator(self):
        a = AudiobookNarrator(first_name="Frank", last_name="Muller")
        self.assertNotEqual(a, "Frank Muller")


class TestAudioBookSync(unittest.TestCase):
    def test_singular_promotes_to_list(self):
        n = AudiobookNarrator(first_name="A", last_name="B")
        b = AudioBook(title="X", narrator=n)
        self.assertEqual(b.narrators, [n])

    def test_plural_back_fills_singular(self):
        n1 = AudiobookNarrator(first_name="A", last_name="B")
        n2 = AudiobookNarrator(first_name="C", last_name="D")
        b = AudioBook(title="X", narrators=[n1, n2])
        self.assertEqual(b.narrator, n1)

    def test_not_equal_to_non_audiobook(self):
        b = AudioBook(title="X")
        self.assertNotEqual(b, "X")


class TestHasLiveStreams(unittest.TestCase):
    def test_true_when_any_url_reachable(self):
        b = AudioBook(title="X", streams=["http://a", "http://b"])
        with patch("audiobooker.utils.check_url_availability",
                   side_effect=[False, True]):
            self.assertTrue(b.has_live_streams())

    def test_false_when_none_reachable(self):
        b = AudioBook(title="X", streams=["http://a"])
        with patch("audiobooker.utils.check_url_availability",
                   return_value=False):
            self.assertFalse(b.has_live_streams())


if __name__ == "__main__":
    unittest.main()
