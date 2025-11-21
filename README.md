██╗ ██╗ ██████╗██╗ ██╗ █████╗ ██████╗ ███╗ ███╗
██║ ██║██╔════╝██║ ██║██╔══██╗██╔══██╗████╗ ████║
███████║██║ ███████║███████║██████╔╝██╔████╔██║
╚════██║██║ ██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║
██║╚██████╗██║ ██║██║ ██║██║ ██║██║ ╚═╝ ██║
╚═╝ ╚═════╝╚═╝ ╚═╝╚═╝ ╚═╝╚═╝ ╚═╝╚═╝ ╚═╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ About

4Charm is a powerful, lightning-fast 4chan media downloader built for macOS. Download threads, catalogs, and entire boards with intelligent organization and failsafe resume capabilities.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Features

🎨 Redesigned UI/UX — Modern, smooth interface with improved dark mode
🚀 Hyper Bulk Downloads — Batch download threads, catalogs, and boards simultaneously
🗂️ Auto-Organized Storage — Smart folder sorting with separate WEBM directories
🔁 Fail-Safe Resume — Interrupted sessions resume instantly where they left off
🧬 Zero Duplicates — SHA-256 hash-based deduplication saves disk space
⚙️ Multithread Engine — Parallel downloading for maximum throughput
🚦 Adaptive Rate Limiting — Smart throttling prevents IP bans/timeouts
📁 Custom Save Locations — Choose any directory on your system
📡 Real-Time Logging — Live status updates and scrollable logs
🖥️ Apple Silicon Native — Optimized for M1/M2/M3 chips

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Supported Media

Images: JPG, PNG, GIF, WEBP, BMP
Videos: WEBM, MP4, MOV, AVI, MKV
Documents: PDF, TXT, ZIP, RAR

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Installation

Download

Get the latest 4Charm_X.X.X.dmg from the Releases page: https://github.com/RazorBackRoar/4Charm/releases

Install

1. Mount the DMG file
2. Drag 4Charm.app to Applications
3. Eject the DMG

First Launch (Gatekeeper Override)

Since 4Charm uses ad-hoc signing, macOS will show a security warning on first launch.

Method A — Right-Click:

1. Open Applications folder
2. Right-click 4Charm.app → Open
3. Click "Open" to approve

Method B — Terminal:

```bash
sudo xattr -cr /Applications/4Charm.app
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 Usage

1. Launch 4Charm
2. Paste a URL:
   Thread: https://boards.4chan.org/g/thread/12345678
   Catalog: https://boards.4chan.org/g/catalog
   Board: https://boards.4chan.org/g/
3. Choose your download location
4. Click "Start Download"
5. Monitor progress in real-time

Batch Mode: Paste up to 10 URLs and download them all simultaneously.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Download Structure

```
Downloads/
├── g-12345678/
│   ├── img001.jpg
│   ├── img002.png
│   └── WEBM/
│       ├── vid001.webm
│       └── vid002.webm
└── g-catalog/
    └── ...
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💻 Requirements

macOS 10.13 or later
~200MB free disk space
Internet connection
No Python installation required

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Troubleshooting

"App is damaged" or "Cannot be opened"
This is a Gatekeeper security warning. Use the right-click method or terminal command above.

Slow downloads
4chan implements rate limiting. The app automatically adapts to avoid throttling.

No media found
The URL may be invalid, the thread may have been deleted, or no media may be present.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️ Building from Source

See BUILD.md for complete build instructions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📜 License

MIT License - See LICENSE for details.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🐞 Support

Issues: https://github.com/RazorBackRoar/4Charm/issues
Source: https://github.com/RazorBackRoar/4Charm

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 Privacy

4Charm operates 100% locally. No tracking, no analytics, no data collection. The app only communicates with 4chan's public API.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
