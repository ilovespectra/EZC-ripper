# EZC Ripper — native Mac app

**EZC Ripper** is a standalone Mac desktop app for saving one YouTube video or a whole playlist as MP4 video or MP3 audio. It puts downloads in a local queue, lets you choose a save folder, and keeps progress and cancellation controls in the app. It runs on your Mac; it is not a cloud file-transfer service.

EZC Ripper is separate from [EZC Cloud Transfer](https://ezc.kolektivkrog.si/), which transfers Google Drive and Google Photos files, and from the [older Python-based EZC project](https://github.com/ilovespectra/EZC). Those are different products; their downloads are not EZC Ripper installers.

**Current repository:** [playlist-media-saver on GitHub](https://github.com/ilovespectra/playlist-media-saver) (private). **Native-app releases:** [GitHub Releases](https://github.com/ilovespectra/playlist-media-saver/releases). There is no public EZC Ripper installer published yet.

## Run from source

On an Apple-silicon Mac with Python 3.11+ and Node.js 22+:

1. Run `bash Setup.command` once to prepare the local Python environment and FFmpeg.
2. Run `npm install` from the project folder.
3. Start the desktop app with `npm start`.

`npm run package` builds the macOS Apple-silicon DMG. The packaged app starts its downloader helper locally; you do not need to open a separate browser page or host a server.

## What it does

- Accepts HTTPS YouTube watch, `youtu.be`, Shorts, live, and embed video links, plus playlist links containing a `list=` ID. When a video ID and `list=` appear together, only the video is downloaded.
- Offers MP4 video and MP3 audio output. Playlist items keep their order in filenames; single videos are saved directly in the selected folder. MP3 conversion uses the bundled FFmpeg.
- Continues past individual item failures and displays downloader output.
- Keeps independent progress, logs, destinations, and cancellation for each queued video or playlist. Playlist items download sequentially within each job; concurrency is between jobs. The queue supports up to 100 unfinished jobs and retains the latest 50 finished results.
- Shares one minimum **2-second gap between outbound HTTP requests across all downloader processes**, including metadata/API calls, media/chunk requests, redirects, and retries. Open streams may keep transferring during the gap. This is a conservative user-selected budget, not a guarantee against YouTube throttling or an assertion about its published limits.
- Uses yt-dlp's native urllib/HTTP/DASH/HLS paths to enforce that budget. Streams that require an external network downloader (including some live streams) fail with an explicit error rather than bypass the limit. FFmpeg still merges and converts local files. A playlist releases its item slot after each attempted item, including failures; its process, cookies, playlist ordering, and selected destination are retained for its next turn.
- Uses a native folder picker instead of an editable path field. Browser mode uses macOS's folder dialog; the EZC desktop app uses Electron's native folder dialog.
- Uses yt-dlp's Node runtime and GitHub EJS components for YouTube's JavaScript challenges. This requires internet access.
- Uses macOS's system certificate bundle for verified HTTPS requests, avoiding failures from an unconfigured Python certificate file. TLS verification stays enabled.
- Can optionally use EZC's persistent YouTube sign-in session or a browser profile selected in the form. Cookie values are never displayed; temporary cookie files are stored privately and removed after each job. Opening the app in a browser does not automatically select that browser's cookies. If Google blocks embedded sign-in, use the standard-browser fallback and explicitly choose that browser's cookies.
- Does not bypass DRM or access restrictions. Playback in a browser does not guarantee a separate downloader can retrieve the video; EZC displays retrieval errors instead of overriding them.

## Developer Console

From the EZC source folder, run `npm run dev:console`. Choose `patch`, `minor`,
`major`, or `current`; after confirmation it runs the test suite, updates the
version and lockfile, and builds the Apple-silicon DMG. Failed builds restore
the prior version metadata. This console builds locally; the app does not yet
have a configured public release feed for in-app updates.
