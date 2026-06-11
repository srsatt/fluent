#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tests"))
from test_update_db import make_fixtures  # noqa: E402

RSS_SETUP = REPO_ROOT / "scripts" / "rss-setup.py"
RSS_PREVIEW = REPO_ROOT / "scripts" / "rss-preview.py"


class RssToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fluent-rss-"))
        self.data_dir = self.tmp / "data"
        self.data_dir.mkdir()
        make_fixtures(self.data_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _env(self):
        env = os.environ.copy()
        env["FLUENT_DATA_DIR"] = str(self.data_dir)
        env["FLUENT_DB"] = "json"
        return env

    def test_rss_setup_stores_preferences(self):
        payload = {
            "feeds": [{
                "url": "https://example.com/podcast.xml",
                "label": "Example Podcast",
                "content_type": "audio",
            }],
            "transcription": {
                "enabled": True,
                "provider": "whisper.cpp",
                "binary": "whisper-cli",
                "model": "/tmp/ggml-test.bin",
                "language": "nl",
                "ffmpeg": "ffmpeg",
            },
        }
        proc = subprocess.run(
            ["python3", str(RSS_SETUP)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        profile = json.loads((self.data_dir / "learner-profile.json").read_text())
        rss = profile["preferences"]["rss"]
        self.assertEqual(rss["feeds"][0]["url"], "https://example.com/podcast.xml")
        self.assertNotIn("transcription", rss)
        stt = json.loads((self.data_dir / "rss-stt-settings.json").read_text())
        self.assertEqual(stt["provider"], "whisper.cpp")
        self.assertEqual(stt["model"], "/tmp/ggml-test.bin")

    def test_rss_preview_reads_local_media_feed(self):
        feed = self.tmp / "feed.xml"
        feed.write_text(textwrap.dedent("""
            <?xml version="1.0"?>
            <rss version="2.0">
              <channel>
                <title>Slow News</title>
                <item>
                  <title>Nieuwe treinverbinding</title>
                  <guid>episode-1</guid>
                  <pubDate>Thu, 11 Jun 2026 10:00:00 GMT</pubDate>
                  <description><![CDATA[Een korte aflevering over reizen met de trein.]]></description>
                  <enclosure url="https://cdn.example.com/episode-1.mp3" type="audio/mpeg" length="12345" />
                </item>
              </channel>
            </rss>
        """).strip(), encoding="utf-8")

        proc = subprocess.run(
            ["python3", str(RSS_PREVIEW), "--file", str(feed), "--json"],
            text=True,
            capture_output=True,
            env=self._env(),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["items"][0]["title"], "Nieuwe treinverbinding")
        self.assertEqual(result["items"][0]["media_type"], "audio")
        self.assertEqual(result["items"][0]["feed_title"], "Slow News")


if __name__ == "__main__":
    unittest.main()
