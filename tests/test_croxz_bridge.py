"""Tests for fdm-croxz/croxz_bridge.py, the Python side of the add-on.

Run from the repository root:  python -m unittest discover -s tests -v

The end-to-end tests run the bridge the way FDM does, as a separate Python process, with a
stand-in for yt-dlp first on PATH (tests/fake_ytdlp.py), so they need no network.
"""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(os.path.dirname(TESTS), "fdm-croxz")
BRIDGE = os.path.join(ADDON, "croxz_bridge.py")
FIXTURES = os.path.join(TESTS, "fixtures")

sys.path.insert(0, ADDON)
import croxz_bridge as bridge  # noqa: E402


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fixture:
        return json.load(fixture)


class SanitizeFilenameTests(unittest.TestCase):
    def test_removes_characters_windows_forbids(self):
        self.assertEqual(bridge.sanitize_filename('a/b:c*?"<>|d'), "abcd")

    def test_joins_words_with_underscores_and_trims_dots(self):
        self.assertEqual(bridge.sanitize_filename("  ..My  Video..  "), "My_Video")

    def test_falls_back_to_download_when_nothing_is_left(self):
        self.assertEqual(bridge.sanitize_filename(""), "download")
        self.assertEqual(bridge.sanitize_filename("???"), "download")

    def test_keeps_turkish_letters_as_their_ascii_base(self):
        self.assertEqual(bridge.sanitize_filename("Kırmızı Şarkı"), "Kirmizi_Sarki")
        self.assertEqual(bridge.sanitize_filename("Ağır Çekim Ölüm Düşüş"), "Agir_Cekim_Olum_Dusus")
        self.assertEqual(bridge.sanitize_filename("Café 🔥 Şarkı"), "Cafe_Sarki")

    def test_limits_the_length(self):
        self.assertEqual(len(bridge.sanitize_filename("a" * 300)), 200)


class UrlTests(unittest.TestCase):
    def test_direct_downloads_are_recognized_by_extension(self):
        self.assertTrue(bridge.is_direct_download_url("https://example.com/files/setup.exe"))
        self.assertTrue(bridge.is_direct_download_url("https://example.com/a/b.MP4?x=1"))
        self.assertFalse(bridge.is_direct_download_url("https://www.youtube.com/watch?v=abc123"))

    def test_streams_are_left_to_yt_dlp(self):
        url = "https://cdn.example.com/live/master.m3u8?token=1"
        self.assertTrue(bridge.is_stream_url(url))
        self.assertFalse(bridge.is_direct_download_url(url))


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.video = load_fixture("video.json")

    def test_keeps_formats_with_sound_best_first_and_the_best_audio_last(self):
        kept = bridge.merge_video_audio_formats(self.video["formats"])
        self.assertEqual([f["format_id"] for f in kept], ["95", "94", "18", "251"])

    def test_labels_show_quality_and_size(self):
        result = bridge.transform_single(self.video)
        labels = [f.get("format") for f in result["formats"]]
        self.assertEqual(labels[0], "720p [65.8MB] (mp4)")
        self.assertEqual(labels[-1], "160kbps [3.9MB] (webm)")

    def test_hls_formats_carry_their_manifest(self):
        result = bridge.transform_single(self.video)
        first = result["formats"][0]
        self.assertEqual(first["protocol"], "m3u8_native")
        self.assertEqual(first["manifestUrl"], "https://manifest.googlevideo.com/95/index.m3u8")


@unittest.skipUnless(os.name == "posix", "the yt-dlp stand-in is a shell wrapper")
class BridgeProcessTests(unittest.TestCase):
    """Runs croxz_bridge.py in its own process, as FDM's launchPythonScript does."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.args_file = os.path.join(self.temp.name, "args.json")
        wrapper = os.path.join(self.temp.name, "yt-dlp")
        with open(wrapper, "w", encoding="utf-8") as script:
            script.write('#!/bin/sh\nexec "{}" "{}" "$@"\n'.format(
                sys.executable, os.path.join(TESTS, "fake_ytdlp.py")))
        os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.temp.cleanup()

    def run_bridge(self, command, url, fixture="video.json", encoding="utf-8"):
        env = dict(os.environ)
        env["PATH"] = self.temp.name + os.pathsep + env.get("PATH", "")
        env["FAKE_YTDLP_ARGS"] = self.args_file
        env["FAKE_YTDLP_OUTPUT"] = os.path.join(FIXTURES, fixture)
        # The encoding Python gives a redirected stdout, such as cp1254 on a Turkish Windows.
        env["PYTHONIOENCODING"] = encoding
        return subprocess.run(
            [sys.executable, BRIDGE, command, url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)

    def ytdlp_args(self):
        with open(self.args_file, encoding="utf-8") as args_file:
            return json.load(args_file)

    def test_extract_prints_one_json_object_for_fdm(self):
        run = self.run_bridge("extract", "https://www.youtube.com/watch?v=abc123")

        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout.decode("utf-8"))
        self.assertEqual(data["original_title"], "Café 🔥 Şarkı")
        self.assertEqual(len(data["formats"]), 4)
        self.assertIn("--no-playlist", self.ytdlp_args())
        self.assertNotIn("--no-check-certificates", self.ytdlp_args())

    def test_titles_outside_the_console_code_page_still_print(self):
        # The emoji in the title has no place in cp1254.
        run = self.run_bridge("extract", "https://www.youtube.com/watch?v=abc123", encoding="cp1254")

        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout.decode("ascii"))
        self.assertEqual(data["original_title"], "Café 🔥 Şarkı")

    def test_playlist_lists_each_entry(self):
        run = self.run_bridge(
            "playlist", "https://www.youtube.com/playlist?list=PL1", fixture="playlist.json")

        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout.decode("utf-8"))
        self.assertEqual(data["_type"], "playlist")
        self.assertEqual([e["url"] for e in data["entries"]], [
            "https://www.youtube.com/watch?v=one", "https://www.youtube.com/watch?v=two"])
        self.assertIn("--flat-playlist", self.ytdlp_args())


if __name__ == "__main__":
    unittest.main()
