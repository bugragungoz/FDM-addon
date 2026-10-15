# Croxz Universal Downloader for FDM

An add-on for [Free Download Manager 6](https://www.freedownloadmanager.org/) that downloads video
and audio from YouTube and over 40 other sites. Paste a video's link into FDM and choose a quality:
the add-on asks [yt-dlp](https://github.com/yt-dlp/yt-dlp) which formats the page has, and FDM
downloads the one you pick. Playlist and channel links list their videos.

## Install

You need FDM 6 and yt-dlp. The add-on runs a small Python script; if Python is missing, FDM offers
to install it when you add the add-on.

1. Install yt-dlp, on Windows for example with `winget install yt-dlp.yt-dlp`, and check that
   `yt-dlp --version` works in a new terminal. A `yt-dlp.exe` in `%LOCALAPPDATA%\yt-dlp` works too.
2. Download [`fdm-croxz.fda`](https://github.com/bugragungoz/FDM-addon/releases/latest/download/fdm-croxz.fda)
   from [Releases](https://github.com/bugragungoz/FDM-addon/releases).
3. In FDM, open **Tools > Add-ons**, choose **Install from file** and select the file. Allow the
   add-on to run Python, then restart FDM.

To update, install the new `.fda` from Releases the same way. FDM updates only signed add-ons on its
own.

## Use

- **A video:** paste its page link, such as `https://www.youtube.com/watch?v=...`, into FDM. FDM lists
  the qualities, each with its size where the site gives one, and the best audio-only format last
  for music.
- **A playlist or channel:** paste a link such as `https://www.youtube.com/playlist?list=...` or
  `https://www.youtube.com/@name/videos`, then choose which videos to download.
- **Files:** links to files such as `.exe`, `.zip` or `.pdf` stay with FDM; the add-on does not take
  them.

Only formats that carry both video and sound are offered, because FDM cannot join a separate video
stream and audio stream into one file. Some sites offer their highest qualities only as separate
streams, so the best quality listed can be lower than on the site.

Supported sites include YouTube, X (Twitter), Instagram, TikTok, Vimeo, Dailymotion, Twitch,
Facebook, Reddit, SoundCloud, Bandcamp, Mixcloud, Bilibili, Rumble, Odysee, VK, Streamable, TED and
Imgur; the full list is `MEDIA_PATTERNS` in [msparser.js](fdm-croxz/msparser.js). The add-on also
takes HLS (`.m3u8`) and DASH (`.mpd`) stream links.

### When something fails

| Message or problem | What to do |
| --- | --- |
| `yt-dlp not found` | Install yt-dlp (step 1), check `yt-dlp --version` in a new terminal, restart FDM. |
| A site that worked stops working | Update yt-dlp with `yt-dlp -U`: sites change, and yt-dlp follows them. |
| `No downloadable formats found` | The page has no format with both video and sound; update yt-dlp, or the site offers none. |

## How it works

| File | Role |
| --- | --- |
| [manifest.json](fdm-croxz/manifest.json) | Name, version, the Python permission and the scripts FDM loads. |
| [msparser.js](fdm-croxz/msparser.js) | Decides which links the add-on takes and asks the bridge for a video's formats. |
| [msbatchparser.js](fdm-croxz/msbatchparser.js) | The same for playlists, channels and albums. |
| [croxz_bridge.py](fdm-croxz/croxz_bridge.py) | Runs `yt-dlp --dump-json`, keeps the formats FDM can use, and prints them as JSON. |

File names are made from the title in plain ASCII: `Kırmızı Şarkı` is saved as `Kirmizi_Sarki`.

## Development

```bash
python -m unittest discover -s tests -v   # the bridge, with a stand-in for yt-dlp
node --test tests/parsers.test.js         # the two parsers, with a stand-in for FDM
```

GitHub Actions runs both on every push, the Python tests on 3.8 (the version FDM installs) and 3.12.
To release, raise `version` in `manifest.json`, add its section to [CHANGELOG.md](CHANGELOG.md) and
push to `master`: the workflow builds `fdm-croxz.fda` from the `fdm-croxz` folder and publishes it.

[fdm-addons-docs-master](fdm-addons-docs-master/) is a copy of FDM's add-on documentation, the
reference for the manifest and the parser functions. The GitHub repository it came from no longer
opens.

## License

[MIT](LICENSE). The copied FDM documentation is under the MIT License of the FDM Team.

This add-on was later revised with Claude Opus 5.5.
