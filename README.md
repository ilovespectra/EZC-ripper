# Playlist Media Saver (local Mac app)

A local webpage for entering a YouTube playlist URL and choosing MP4 video or MP3 audio output.

## Start

1. Download the repository with **Code → Download ZIP**, then unzip it.
2. In Terminal, change into the unzipped `playlist-media-saver` folder and run `bash Setup.command` once. It installs yt-dlp and a platform-matched FFmpeg into this app folder using Python; it does not use Homebrew. Node.js 22 or newer must already be on your PATH.
3. Run `bash Start.command` in the same Terminal window and keep it open while downloading.
4. In your browser, open **http://127.0.0.1:8765** (include `:8765`).
5. Paste a playlist URL. Files go by default to `~/Downloads/Recovered YouTube Music`, grouped into a folder named after the playlist. You can change the path in the page.
6. Press Ctrl+C in the Terminal window to stop the helper.

The helper listens only on `127.0.0.1`; it is not deployed to a public server. The installed tools live in this app folder.

## What it does

- Requires a YouTube playlist link containing a `list=` ID.
- Offers MP4 video and MP3 audio output, keeping playlist order in filenames. MP3 conversion uses the bundled FFmpeg.
- Continues past individual item failures and displays downloader output.
- Uses yt-dlp's Node runtime and GitHub EJS components for YouTube's JavaScript challenges. This requires internet access.
- Uses macOS's system certificate bundle for verified HTTPS requests, avoiding failures from an unconfigured Python certificate file. TLS verification stays enabled.
- Uses no account cookies, proxies, or access-control workarounds. If YouTube refuses a video, the page displays the downloader error; the UI cannot override that decision.

Playback in a browser does not guarantee that a separate downloader can retrieve the video. This app does not sign into YouTube.
