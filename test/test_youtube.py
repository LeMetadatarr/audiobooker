"""Offline tests for audiobooker.scrappers.youtube — pure logic paths."""
import unittest
from unittest.mock import patch

import pytest

pytest.importorskip("tutubo")

from audiobooker.base import AudioBook, AudiobookNarrator, BookAuthor
from audiobooker.scrappers.youtube import (
    HorrorBabble,
    TheCybrarian,
    TheDustyTome,
    YoutubeChannelSource,
    YoutubePlaylistSource,
    _iter_channel_videos,
    _iter_playlist_videos,
    _length_to_seconds,
    _parse_name,
    _parse_playlist_video,
    _parse_video_item,
    _require_tutubo,
    _video_to_book,
    extract_yt_metadata,
)


class TestLengthToSeconds(unittest.TestCase):
    def test_mm_ss(self):
        self.assertEqual(_length_to_seconds("12:34"), 12 * 60 + 34)

    def test_hh_mm_ss(self):
        self.assertEqual(_length_to_seconds("1:02:03"), 3723)

    def test_empty(self):
        self.assertEqual(_length_to_seconds(""), 0)

    def test_invalid(self):
        self.assertEqual(_length_to_seconds("abc:def"), 0)

    def test_one_part(self):
        # only 1 part -> falls through, returns 0
        self.assertEqual(_length_to_seconds("12"), 0)


class TestParseName(unittest.TestCase):
    def test_two_words(self):
        self.assertEqual(_parse_name("Mary Shelley"), ("Mary", "Shelley"))

    def test_three_words(self):
        self.assertEqual(_parse_name("H. P. Lovecraft"), ("H. P.", "Lovecraft"))

    def test_single_name(self):
        self.assertEqual(_parse_name("Plato"), ("", "Plato"))


class TestParseVideoItem(unittest.TestCase):
    def test_old_videorenderer(self):
        item = {"richItemRenderer": {"content": {"videoRenderer": {
            "videoId": "abc123",
            "title": {"runs": [{"text": "Dracula by Bram Stoker"}]},
            "lengthText": {"simpleText": "10:00"},
            "thumbnail": {"thumbnails": [{"url": "http://x/t.jpg"}]},
            "descriptionSnippet": {"runs": [{"text": "A vampire tale"}]},
        }}}}
        result = _parse_video_item(item)
        self.assertEqual(result["id"], "abc123")
        self.assertEqual(result["title"], "Dracula by Bram Stoker")
        self.assertEqual(result["length"], "10:00")
        self.assertEqual(result["desc"], "A vampire tale")

    def test_old_videorenderer_missing_id(self):
        item = {"richItemRenderer": {"content": {"videoRenderer": {
            "title": {"runs": [{"text": "X"}]},
        }}}}
        self.assertIsNone(_parse_video_item(item))

    def test_lockup_view_model(self):
        item = {"richItemRenderer": {"content": {"lockupViewModel": {
            "metadata": {"lockupMetadataViewModel": {
                "title": {"content": "Frankenstein"}}},
            "contentImage": {"thumbnailViewModel": {
                "image": {"sources": [{"url": "https://i/vi/xyz789/m.jpg"}]},
                "overlays": [{"thumbnailBottomOverlayViewModel": {
                    "badges": [{"thumbnailBadgeViewModel": {"text": "1:23:45"}}]
                }}]
            }}
        }}}}
        result = _parse_video_item(item)
        self.assertEqual(result["id"], "xyz789")
        self.assertEqual(result["title"], "Frankenstein")
        self.assertEqual(result["length"], "1:23:45")

    def test_lockup_missing_id(self):
        item = {"richItemRenderer": {"content": {"lockupViewModel": {
            "metadata": {"lockupMetadataViewModel": {
                "title": {"content": "Title"}}},
            "contentImage": {},
        }}}}
        self.assertIsNone(_parse_video_item(item))

    def test_neither_layout(self):
        self.assertIsNone(_parse_video_item({"richItemRenderer": {"content": {}}}))


class TestParsePlaylistVideo(unittest.TestCase):
    def test_basic(self):
        item = {"playlistVideoRenderer": {
            "videoId": "vid",
            "title": {"runs": [{"text": "Episode 1"}]},
            "lengthText": {"simpleText": "5:00"},
            "thumbnail": {"thumbnails": [{"url": "http://x/t.jpg"}]},
        }}
        result = _parse_playlist_video(item)
        self.assertEqual(result["id"], "vid")
        self.assertEqual(result["title"], "Episode 1")

    def test_missing_renderer(self):
        self.assertIsNone(_parse_playlist_video({}))

    def test_missing_title(self):
        item = {"playlistVideoRenderer": {"videoId": "vid", "title": {"runs": [{}]}}}
        self.assertIsNone(_parse_playlist_video(item))


class TestRequireTutubo(unittest.TestCase):
    def test_available(self):
        # Should not raise when tutubo is importable
        _require_tutubo()

    def test_missing(self):
        with patch("audiobooker.scrappers.youtube._TUTUBO_AVAILABLE", False):
            with self.assertRaises(ImportError):
                _require_tutubo()


class TestExtractMetadata(unittest.TestCase):
    def test_extracts_author(self):
        meta = extract_yt_metadata("Dracula by Bram Stoker", "")
        self.assertEqual(len(meta["authors"]), 1)
        self.assertEqual(meta["authors"][0].last_name, "Stoker")

    def test_extracts_two_authors(self):
        meta = extract_yt_metadata("Story by Mary Smith and John Doe", "")
        self.assertEqual(len(meta["authors"]), 2)

    def test_extracts_narrator(self):
        meta = extract_yt_metadata("Dracula narrated by Frank Muller", "")
        self.assertIsNotNone(meta["narrator"])
        self.assertEqual(meta["narrator"].last_name, "Muller")

    def test_extracts_year_from_desc(self):
        meta = extract_yt_metadata("Dracula", "Published in 1897")
        self.assertEqual(meta["year"], 1897)

    def test_extracts_year_from_title_when_desc_missing(self):
        meta = extract_yt_metadata("Dracula 1897", "")
        self.assertEqual(meta["year"], 1897)

    def test_no_year(self):
        meta = extract_yt_metadata("Dracula", "")
        self.assertEqual(meta["year"], 0)

    def test_strips_full_audiobook_suffix(self):
        meta = extract_yt_metadata("Dracula | FULL AUDIOBOOK", "")
        self.assertNotIn("AUDIOBOOK", meta["clean_title"].upper())

    def test_strips_brackets(self):
        meta = extract_yt_metadata("Dracula [REMASTERED]", "")
        self.assertNotIn("[", meta["clean_title"])

    def test_strips_horrorbabble_suffix(self):
        meta = extract_yt_metadata("The Outsider | HorrorBabble", "")
        self.assertNotIn("HorrorBabble", meta["clean_title"])

    def test_extracts_hashtags(self):
        meta = extract_yt_metadata("Dracula #horror #vampire #audiobook", "")
        # 'audiobook' is skipped, 'horror' and 'vampire' kept
        self.assertIn("horror", meta["extra_tags"])
        self.assertIn("vampire", meta["extra_tags"])
        self.assertNotIn("audiobook", meta["extra_tags"])

    def test_dedup_hashtags(self):
        meta = extract_yt_metadata("Dracula #horror #horror #horror", "")
        self.assertEqual(meta["extra_tags"].count("horror"), 1)


class TestVideoToBook(unittest.TestCase):
    def test_extract_metadata_default(self):
        v = {"id": "abc", "title": "Dracula by Bram Stoker", "desc": "1897",
             "length": "10:00", "thumb": "http://t/x.jpg"}
        b = _video_to_book(v, authors=[], tags=["Horror"], language="en")
        # extraction does not strip the "by Author" phrase from clean_title
        self.assertIn("Dracula", b.title)
        self.assertEqual(b.year, 1897)
        self.assertTrue(b.authors)
        self.assertEqual(b.runtime, 600)
        self.assertIn("youtube.com/watch?v=abc", b.streams[0])

    def test_extract_metadata_disabled(self):
        v = {"id": "abc", "title": "Dracula by Bram Stoker", "desc": "1897"}
        b = _video_to_book(v, authors=[BookAuthor(last_name="Configured")],
                           tags=["Horror"], language="en",
                           extract_metadata=False)
        # Title not cleaned
        self.assertIn("by Bram Stoker", b.title)
        self.assertEqual(b.authors[0].last_name, "Configured")
        self.assertEqual(b.year, 0)

    def test_configured_author_takes_precedence(self):
        v = {"id": "x", "title": "Story by Some Author", "desc": ""}
        b = _video_to_book(
            v, authors=[BookAuthor(last_name="ConfiguredOne")],
            tags=[], language="en")
        self.assertEqual(b.authors[0].last_name, "ConfiguredOne")

    def test_configured_narrator_takes_precedence(self):
        v = {"id": "x", "title": "Story narrated by Other Person",
             "desc": ""}
        n = AudiobookNarrator(first_name="Set", last_name="Narrator")
        b = _video_to_book(v, authors=[], tags=[], language="en", narrator=n)
        self.assertEqual(b.narrator.last_name, "Narrator")

    def test_hashtag_tags_override_default(self):
        v = {"id": "x", "title": "Story #weird #fiction", "desc": ""}
        b = _video_to_book(v, authors=[], tags=["DefaultTag"],
                           language="en")
        self.assertIn("weird", b.tags)
        self.assertNotIn("DefaultTag", b.tags)


class FakeYoutubeMixinSrc(YoutubeChannelSource):
    """Subclass that yields canned books so we can hit search methods."""

    def __init__(self, books):
        super().__init__(
            channel_url="http://x",
            authors=[],
            tags=[],
            language="en",
            min_runtime=0,
        )
        self._books = books

    def iterate_all(self):
        return iter(self._books)


class TestYtSourceMixinSearch(unittest.TestCase):
    def setUp(self):
        self.b1 = AudioBook(
            title="Dracula",
            authors=[BookAuthor(first_name="Bram", last_name="Stoker")],
            tags=["Horror"],
            narrator=AudiobookNarrator(first_name="Frank", last_name="Muller"),
        )
        self.b2 = AudioBook(
            title="Frankenstein",
            authors=[BookAuthor(first_name="Mary", last_name="Shelley")],
            tags=["Gothic"],
        )
        self.src = FakeYoutubeMixinSrc([self.b1, self.b2])

    def test_search_by_title(self):
        results = list(self.src.search_by_title("Dracula"))
        self.assertEqual(len(results), 1)

    def test_search_by_author(self):
        results = list(self.src.search_by_author("Stoker"))
        self.assertEqual(len(results), 1)

    def test_search_by_tag(self):
        results = list(self.src.search_by_tag("Horror"))
        self.assertEqual(len(results), 1)

    def test_search_by_narrator(self):
        results = list(self.src.search_by_narrator("Muller"))
        self.assertEqual(len(results), 1)

    def test_iterate_popular_alias(self):
        self.assertEqual(len(list(self.src.iterate_popular())), 2)


class TestYoutubeChannelSourceIterateAll(unittest.TestCase):
    def test_iterate_skips_short_and_blacklisted(self):
        videos = [
            {"id": "1", "title": "Short Video", "desc": "", "length": "1:00"},
            {"id": "2", "title": "Bad Trailer Update", "desc": "",
             "length": "10:00"},
            {"id": "3", "title": "Good Story by Author Name", "desc": "",
             "length": "10:00"},
        ]
        src = YoutubeChannelSource(
            channel_url="http://x",
            authors=[],
            tags=[],
            language="en",
            min_runtime=120,
            title_blacklist=["trailer"],
        )
        with patch("audiobooker.scrappers.youtube._iter_channel_videos",
                   return_value=iter(videos)):
            results = list(src.iterate_all())
        # Only the 3rd video survives
        self.assertEqual(len(results), 1)
        self.assertIn("Good Story", results[0].title)


class TestYoutubePlaylistSourceIterateAll(unittest.TestCase):
    def test_iterate(self):
        videos = [
            {"id": "1", "title": "OK", "desc": "", "length": "10:00"},
        ]
        src = YoutubePlaylistSource(
            playlist_url="http://x",
            authors=[],
            tags=[],
            language="en",
            min_runtime=60,
        )
        with patch("audiobooker.scrappers.youtube._iter_playlist_videos",
                   return_value=iter(videos)):
            results = list(src.iterate_all())
        self.assertEqual(len(results), 1)


class TestPreconfiguredChannels(unittest.TestCase):
    def test_cybrarian_constructs(self):
        src = TheCybrarian()
        self.assertIn("Cybrarian", src.channel_url)
        self.assertEqual(src.authors[0].last_name, "Howard")

    def test_horrorbabble_constructs(self):
        src = HorrorBabble()
        self.assertIn("HorrorBabble", src.channel_url)
        self.assertEqual(src.narrator.last_name, "Gordon")

    def test_dustytome_constructs(self):
        src = TheDustyTome()
        self.assertIn("DustyTome", src.channel_url)


class TestIterChannelVideos(unittest.TestCase):
    def test_yields_parsed_items(self):
        item = {"richItemRenderer": {"content": {"videoRenderer": {
            "videoId": "abc",
            "title": {"runs": [{"text": "T"}]},
            "lengthText": {"simpleText": "5:00"},
            "thumbnail": {"thumbnails": [{"url": "x"}]},
            "descriptionSnippet": {"runs": [{"text": "d"}]},
        }}}}
        fake_data = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": [
            {"tabRenderer": {"content": {"richGridRenderer": {
                "contents": [item]}}}},
        ]}}}
        with patch("audiobooker.scrappers.youtube._YTChannel") as Ch:
            Ch.return_value.initial_data = fake_data
            results = list(_iter_channel_videos("http://x"))
        self.assertEqual(len(results), 1)

    def test_skips_tabs_without_grid(self):
        fake_data = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": [
            {"tabRenderer": {"content": {}}},
        ]}}}
        with patch("audiobooker.scrappers.youtube._YTChannel") as Ch:
            Ch.return_value.initial_data = fake_data
            self.assertEqual(list(_iter_channel_videos("http://x")), [])


class TestIterPlaylistVideos(unittest.TestCase):
    def test_handles_exception(self):
        with patch("audiobooker.scrappers.youtube._YTPlaylist",
                   side_effect=Exception("fetch failed")):
            self.assertEqual(list(_iter_playlist_videos("http://x")), [])

    def test_yields_videos(self):
        item = {"playlistVideoRenderer": {
            "videoId": "v1",
            "title": {"runs": [{"text": "Ep"}]},
            "lengthText": {"simpleText": "5:00"},
            "thumbnail": {"thumbnails": [{"url": "x"}]},
        }}
        fake_data = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": [
            {"tabRenderer": {"content": {"sectionListRenderer": {
                "contents": [{"itemSectionRenderer": {"contents": [
                    {"playlistVideoListRenderer": {"contents": [item]}}
                ]}}]
            }}}},
        ]}}}
        with patch("audiobooker.scrappers.youtube._YTPlaylist") as Pl:
            Pl.return_value.initial_data = fake_data
            results = list(_iter_playlist_videos("http://x"))
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
