# 4Charm

Paste a public 4chan thread, catalog, or board. 4Charm downloads the images and WEBM files into a folder on your Mac, then skips anything you already have.

<p align="center">
  <img src="https://github.com/RazorBackRoar/4Charm/raw/main/docs/screenshots/app.png" alt="4Charm window with a thread queue and download log" width="860">
</p>

<p align="center">

[![Download](https://img.shields.io/github/v/release/RazorBackRoar/4Charm?style=for-the-badge&label=Download%20DMG)](https://github.com/RazorBackRoar/4Charm/releases/latest)
[![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-2ea44f?style=for-the-badge&logo=apple&logoColor=white)](https://support.apple.com/en-us/HT211814)
[![Python](https://img.shields.io/badge/python-3.14-2ea44f?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

</p>

## Run it

1. Download [4Charm.dmg](https://github.com/RazorBackRoar/4Charm/releases/latest/download/4Charm.dmg)
2. Drag **4Charm.app** into Applications
3. First launch: right-click the app and choose **Open**

macOS 12 or later on Apple Silicon. You do not need Python.

Paste a URL, press **Start Download**, and the files land in the folder you picked.

## What it does

- Queue up to 50 threads or catalogs
- Resume a download that got interrupted
- Skip duplicates by SHA-256
- Keep WEBM files in their own folder
- Show live progress, speed, and ETA

4Charm only downloads public 4chan media. It is not affiliated with 4chan. You are responsible for following 4chan's rules and the law where you live.

## Build it yourself

```bash
git clone https://github.com/RazorBackRoar/4Charm.git
cd 4Charm
uv sync
uv run python -m four_charm.main
```

`uv run pytest tests/ -q` runs the tests. `razorbuild 4Charm` writes `dist/4Charm.dmg`.

## License

MIT. See [LICENSE](LICENSE).

If you need me, give me a holler.

<!-- razorcore:runtime:start -->
## Runtime Requirements

For users:
- Download the macOS `.dmg` or `.app` release. Python does not need to be installed.

For developers:
- Primary development/build target: Python 3.14 with `uv`.
- Source/build target: Python 3.14 only.
- Setup: `uv sync`
- Run: `uv run python -m four_charm.main`
<!-- razorcore:runtime:end -->
