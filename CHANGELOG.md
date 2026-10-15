# Changelog

## 1.3.1 - 2026-10-15

> Checked by the tests in this repository; not yet tried in FDM itself.

- Turkish titles keep the letter ı in file names: "Kırmızı Şarkı" was saved as `Krmz_Sark`, now
  as `Kirmizi_Sarki`.
- A title with a character outside the Windows code page, such as an emoji, no longer makes the
  extraction fail.
- yt-dlp checks HTTPS certificates again.
- The add-on package is built from the source and attached to each release.

## 1.3.0 - 2026-03-02

- Videos come with their sound: only formats that carry video and audio together are offered,
  plus the best audio-only format, because FDM cannot join separate streams.
- HLS (m3u8) streams.
- The size of each format is shown next to its quality.

## 1.2.0 - 2025-12-05

- First release.
