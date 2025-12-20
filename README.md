```text
██╗  ██╗ ██████╗██╗  ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║  ██║██╔══██╗██╔══██╗████╗ ████║
███████║██║     ███████║███████║██████╔╝██╔████╔██║
╚════██║██║     ██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║
     ██║╚██████╗██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║
     ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
```

### High-Performance 4chan Media Downloader for macOS

---

### ⚡ About

4Charm is a native macOS app built to rip through threads, catalogs, and whole boards with precision. Smart organization, failsafe resume, and aggressive optimization keep every session stable and fast.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ✨ Highlights

- 🎨 **Redesigned UI/UX** – Modern input panel, refined dark mode, clean status HUD.
- 🚀 **Hyper Bulk Downloads** – Queue threads, catalogs, and boards simultaneously.
- 🗂️ **Auto-Organized Storage** – Per-thread folders plus dedicated WEBM directories.
- 🔁 **Fail-Safe Resume** – Interrupted jobs pick up instantly.
- 🧬 **Zero Duplicates** – SHA-256 hashing prevents redundant downloads.
- ⚙️ **Multithread Engine** – Parallel workers for maximum throughput.
- 🚦 **Adaptive Rate Limiting** – Smart throttling avoids IP bans.
- 📁 **Custom Save Paths** – Drop content anywhere on disk.
- 📡 **Real-Time Logging** – Live scrollable log stream.
- 🖥️ **Apple Silicon Native** – Optimized for M1/M2/M3 chips.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🎯 Supported Media

- **Images:** JPG, PNG, GIF, WEBP, BMP
- **Videos:** WEBM, MP4, MOV, AVI, MKV
- **Documents:** PDF, TXT, ZIP, RAR

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 📦 Installation

1. Download the latest `4Charm_X.X.X.dmg` from [Releases](https://github.com/RazorBackRoar/4Charm/releases).
2. Mount the DMG → drag `4Charm.app` into `/Applications` → eject the DMG.
3. First launch (Gatekeeper):

   - **Method A:** Right-click `4Charm.app` → _Open_ → confirm.
   - **Method B:**

     ```bash
     sudo xattr -cr /Applications/4Charm.app
     ```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🚀 Usage

1. Launch 4Charm and paste up to 10 URLs (thread, catalog, or board).
2. Pick a download location.
3. Hit **Start Download** and watch the live log.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 📁 Download Structure

```text
Downloads/
├── g-12345678/          # https://boards.4chan.org/g/thread/12345678
│   ├── img001.jpg
│   ├── img002.png
│   └── WEBM/
│       ├── vid001.webm
│       └── vid002.webm
├── wg-99887766/         # https://boards.4chan.org/wg/thread/99887766
│   ├── panel01.png
│   └── WEBM/
│       └── clip01.webm
└── tv-44556677/         # https://boards.4chan.org/tv/thread/44556677
    └── ...
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 💻 Requirements

- macOS 10.13+
- ~2 GB free disk space
- Internet connection
- No Python install needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔧 Troubleshooting

- **“App is damaged / Cannot be opened”** – Use the Gatekeeper override above.
- **Slow downloads** – 4chan rate limits; 4Charm auto-adjusts but patience helps.
- **No media found** – Thread may be dead, URL malformed, or no assets exist.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🛠️ Building from Source

See `BUILD.md` for full instructions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 📜 License

MIT License – see `LICENSE`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🐞 Support

- Issues: <https://github.com/RazorBackRoar/4Charm/issues>
- Source: <https://github.com/RazorBackRoar/4Charm>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔐 Privacy

4Charm runs 100% locally. No telemetry, no analytics, only calls to 4chan’s public API.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
