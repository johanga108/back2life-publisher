#!/usr/bin/env python3
"""Tests for stable Google Sheet-to-post synchronization."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_next as app


class CsvResponse:
    def __init__(self, value: str) -> None:
        self.value = value.encode("utf-8")

    def __enter__(self) -> "CsvResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.value


class ContentSheetSyncTests(unittest.TestCase):
    def test_ids_keep_text_dates_and_images_aligned_after_rename(self) -> None:
        posts = [
            {"id": "first", "title": "Old first", "text": "A", "image": "a.jpg"},
            {"id": "second", "title": "Old second", "text": "B", "image": "b.jpg"},
        ]
        calendar = {"dates": ["2026-09-01", "2026-09-02"]}
        sheet = (
            "date,title,text,id\n"
            "2026-10-12,Renamed second,New B,second\n"
            "2026-10-11,Renamed first,New A,first\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts_path = root / "posts.json"
            calendar_path = root / "calendar.json"
            posts_path.write_text(json.dumps(posts), encoding="utf-8")
            calendar_path.write_text(json.dumps(calendar), encoding="utf-8")
            with (
                patch.object(app, "POSTS_PATH", posts_path),
                patch.object(app, "CALENDAR_PATH", calendar_path),
                patch.object(app.urllib.request, "urlopen", return_value=CsvResponse(sheet)),
                patch.dict(os.environ, {"CONTENT_SHEET_CSV_URL": "https://example.test"}),
            ):
                synced_posts, synced_dates, using_sheet_dates = app.load_content()

        self.assertTrue(using_sheet_dates)
        self.assertEqual("Renamed first", synced_posts[0]["title"])
        self.assertEqual("New A", synced_posts[0]["text"])
        self.assertEqual("a.jpg", synced_posts[0]["image"])
        self.assertEqual("Renamed second", synced_posts[1]["title"])
        self.assertEqual("b.jpg", synced_posts[1]["image"])
        self.assertEqual("2026-10-11", synced_dates[0].isoformat())
        self.assertEqual("2026-10-12", synced_dates[1].isoformat())

    def test_unknown_sheet_id_fails_instead_of_shifting_content(self) -> None:
        posts = [{"id": "known", "title": "Known", "text": "A"}]
        calendar = {"dates": ["2026-09-01"]}
        sheet = "date,title,text,id\n2026-10-11,Unknown,Text,wrong\n"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts_path = root / "posts.json"
            calendar_path = root / "calendar.json"
            posts_path.write_text(json.dumps(posts), encoding="utf-8")
            calendar_path.write_text(json.dumps(calendar), encoding="utf-8")
            with (
                patch.object(app, "POSTS_PATH", posts_path),
                patch.object(app, "CALENDAR_PATH", calendar_path),
                patch.object(app.urllib.request, "urlopen", return_value=CsvResponse(sheet)),
                patch.dict(os.environ, {"CONTENT_SHEET_CSV_URL": "https://example.test"}),
            ):
                with self.assertRaisesRegex(RuntimeError, "Unknown post ID"):
                    app.load_content()


if __name__ == "__main__":
    unittest.main()
