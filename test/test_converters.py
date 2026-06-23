"""Tests for audiobooker.converters — audiobook_to_release."""
import unittest

from audiobooker.base import (
    AudioBook,
    AudioBookChapter,
    AudiobookNarrator,
    BookAuthor,
)
from audiobooker.converters import audiobook_to_release


def _book(**kwargs):
    defaults = dict(
        title="Frankenstein",
        authors=[BookAuthor(first_name="Mary", last_name="Shelley")],
        language="en",
        year=1818,
        runtime=36000,
        source="librivox",
        streams=["http://example.com/a.mp3", "http://example.com/b.mp3"],
        image="http://example.com/cover.jpg",
        tags=["Horror", "Classic"],
        genres=["gothic"],
        codec="mp3",
        bitrate="128",
        description="Test description",
    )
    defaults.update(kwargs)
    return AudioBook(**defaults)


class TestAudiobookToRelease(unittest.TestCase):
    def test_basic_conversion(self):
        rel = audiobook_to_release(_book())
        self.assertEqual(rel.work.title, "Frankenstein")
        self.assertEqual(rel.work.year, 1818)
        self.assertEqual(rel.work.runtime, 36000.0)
        self.assertEqual(rel.uri, "http://example.com/a.mp3")
        self.assertEqual(rel.codec, "mp3")
        self.assertEqual(rel.bitrate, "128")
        self.assertEqual(rel.audio_language, "en")
        self.assertEqual(rel.image, "http://example.com/cover.jpg")
        # Public-domain license assigned for librivox source
        self.assertEqual(rel.license.identifier, "public_domain")
        # Author credit present
        roles = [c.role for c in rel.work.credits]
        self.assertIn("author", roles)

    def test_loyalbooks_public_domain(self):
        rel = audiobook_to_release(_book(source="LoyalBooks"))
        self.assertEqual(rel.license.identifier, "public_domain")

    def test_non_public_domain_source(self):
        rel = audiobook_to_release(_book(source="StephenKingAudioBooks"))
        self.assertIsNone(rel.license)

    def test_no_streams_no_uri(self):
        rel = audiobook_to_release(_book(streams=[]))
        self.assertEqual(rel.uri, "")

    def test_singular_narrator_added_as_credit(self):
        b = _book(narrator=AudiobookNarrator(first_name="Frank", last_name="Muller"))
        rel = audiobook_to_release(b)
        roles = [c.role for c in rel.work.credits]
        self.assertIn("narrator", roles)

    def test_dedup_narrators(self):
        n1 = AudiobookNarrator(first_name="Frank", last_name="Muller")
        n2 = AudiobookNarrator(first_name="frank", last_name="muller")  # same
        n3 = AudiobookNarrator(first_name="Wayne", last_name="June")
        b = _book(narrators=[n1, n2, n3])
        rel = audiobook_to_release(b)
        narrator_credits = [c for c in rel.work.credits if c.role == "narrator"]
        self.assertEqual(len(narrator_credits), 2)

    def test_skips_empty_narrator(self):
        # When narrators contains a None, should be skipped
        b = _book()
        b.narrators = [None, AudiobookNarrator(first_name="Ann", last_name="X")]
        rel = audiobook_to_release(b)
        narrator_credits = [c for c in rel.work.credits if c.role == "narrator"]
        self.assertEqual(len(narrator_credits), 1)

    def test_chapters_converted(self):
        b = _book(chapters=[
            AudioBookChapter(title="Ch1", offset=0.0, runtime=600.0,
                             image="http://x/img.jpg"),
            AudioBookChapter(title="Ch2", offset=600.0, runtime=0.0),
        ])
        rel = audiobook_to_release(b)
        self.assertEqual(len(rel.chapters), 2)
        self.assertEqual(rel.chapters[0].end, 600.0)
        self.assertIsNone(rel.chapters[1].end)

    def test_external_ids_audiobooker_id(self):
        b = _book(external_ids={"librivox_id": "12345", "isbn_13": ""})
        rel = audiobook_to_release(b)
        self.assertEqual(rel.external_ids["librivox_id"], "12345")
        self.assertIn("audiobooker_id", rel.external_ids)
        # Falsy ext id values are filtered
        self.assertNotIn("isbn_13", rel.external_ids)

    def test_release_date_from_year(self):
        rel = audiobook_to_release(_book(year=1900))
        self.assertEqual(rel.release_date, "1900")

    def test_release_date_empty_when_no_year(self):
        rel = audiobook_to_release(_book(year=0))
        self.assertEqual(rel.release_date, "")

    def test_extra_passes_through(self):
        rel = audiobook_to_release(_book())
        self.assertEqual(rel.extra["source"], "librivox")
        self.assertEqual(rel.extra["tags"], "Horror, Classic")
        self.assertIn("stream_urls", rel.extra)
        self.assertEqual(rel.extra["description"], "Test description")

    def test_genres_used_when_present(self):
        rel = audiobook_to_release(_book(genres=["horror", "gothic"]))
        self.assertEqual(rel.work.content_genres, ["horror", "gothic"])

    def test_genres_empty_when_no_genres(self):
        rel = audiobook_to_release(_book(genres=[]))
        self.assertEqual(rel.work.content_genres, [])

    def test_no_runtime(self):
        rel = audiobook_to_release(_book(runtime=0))
        self.assertIsNone(rel.work.runtime)


if __name__ == "__main__":
    unittest.main()
