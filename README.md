# 4Charm

```text
██╗  ██╗ ██████╗██╗  ██╗ █████╗ ██████╗ ███╗   ███╗
██║  ██║██╔════╝██║  ██║██╔══██╗██╔══██╗████╗ ████║
███████║██║     ███████║███████║██████╔╝██╔████╔██║
╚════██║██║     ██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║
     ██║╚██████╗██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║
     ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
```

> **High-performance 4chan media downloader for macOS**  
> Native app built with Python and PySide6. Download entire threads, catalogs, or boards with intelligent organization, fail-safe resume, and zero duplicates.

[![GitHub release](https://img.shields.io/github/v/release/RazorBackRoar/4Charm)](https://github.com/RazorBackRoar/4Charm/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![macOS](https://img.shields.io/badge/macOS-10.13+-blue.svg)](https://www.apple.com/macos)
[![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-Native-green.svg)](https://support.apple.com/en-us/HT211814)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-green.svg)](https://doc.qt.io/qtforpython/)

---

## 🤔 Why 4Charm?

Most 4chan downloaders are either CLI tools that require terminal knowledge, browser extensions with limited functionality, or janky Python scripts that break constantly. 4Charm is different.

| Feature | 4Charm | Browser Extensions | CLI Tools | Other Python Apps |
|---------|--------|-------------------|-----------|------------------|
| **Native macOS UI** | ✅ Modern Qt6 | ❌ Browser-dependent | ❌ Terminal only | ⚠️ Often Tkinter/outdated |
| **Apple Silicon Optimized** | ✅ M1/M2/M3 native | ❌ N/A | ⚠️ Depends | ❌ Rarely |
| **Bulk Downloads** | ✅ 10 concurrent URLs | ⚠️ Limited | ✅ Yes | ⚠️ Sometimes |
| **Smart Organization** | ✅ Per-thread + WEBM folders | ❌ Dumps everything | ⚠️ Basic | ❌ Usually flat |
| **Fail-Safe Resume** | ✅ Automatic | ❌ No | ⚠️ Manual | ❌ Usually no |
| **Duplicate Prevention** | ✅ SHA-256 hashing | ❌ No | ❌ Rarely | ❌ Rarely |
| **Rate Limit Handling** | ✅ Adaptive throttling | ❌ Often causes bans | ⚠️ Manual config | ⚠️ Hit or miss |
| **Real-Time Feedback** | ✅ Live log stream | ❌ Limited | ✅ Terminal output | ⚠️ Varies |
| **Setup Complexity** | ✅ Drag & drop install | ✅ Easy | ❌ Dependencies hell | ❌ Python env required |

**The bottom line:** 4Charm gives you CLI-level power with a GUI that doesn't suck, on a platform (macOS) that's often ignored by archival tools.

---

## ✨ Features

### Core Functionality
- **Bulk URL Processing** - Queue up to 10 URLs simultaneously (threads, catalogs, or entire boards)
- **Multi-threaded Engine** - Parallel download workers with configurable concurrency
- **Smart Organization** - Automatic per-thread folder structure with dedicated WEBM subdirectories
- **Fail-Safe Resume** - Interrupted downloads automatically resume from last checkpoint
- **Zero Duplicates** - SHA-256 content hashing prevents redundant downloads
- **Custom Save Paths** - Save downloads anywhere on your filesystem

### Performance & Reliability
- **Adaptive Rate Limiting** - Smart throttling system prevents IP bans while maximizing throughput
- **Optimized for Apple Silicon** - Native ARM64 builds for M1/M2/M3 chips
- **Real-Time Logging** - Live scrollable log stream with detailed download status
- **Error Recovery** - Graceful handling of network failures, 404s, and API timeouts

### User Experience
- **Modern UI/UX** - Clean dark mode interface with refined input panel and status HUD
- **No Dependencies** - Bundled as standalone .app, no Python installation required
- **Gatekeeper Compatible** - Properly signed and notarized for macOS security

### Technical Stack
- **Built with Python 3.13** - Modern, stable
- **PySide6 (Qt6)** - Native-feeling GUI framework
- **4chan API Integration** - Official API endpoints with proper rate limit compliance
- **Cross-thread Safe** - Thread-safe queue management and file I/O

---

## 🚀 Quick Start

### For End Users

1. **Download** the latest release:  
   → [4Charm_X.X.X.dmg](https://github.com/RazorBackRoar/4Charm/releases)

2. **Install** the app:
   ```bash
   # Mount the DMG, drag to Applications, eject
   open 4Charm_X.X.X.dmg
   # Drag 4Charm.app to /Applications
   ```

3. **First launch** (bypass Gatekeeper if needed):
   ```bash
   sudo xattr -cr /Applications/4Charm.app
   ```
   *Alternative: Right-click → Open → Confirm*

4. **Use it:**
   - Launch 4Charm
   - Paste up to 10 4chan URLs (threads, catalogs, or boards)
   - Choose download location
   - Click **Start Download**
   - Watch the live log for progress

### For Developers

See [BUILD.md](BUILD.md) for:
- Setting up the development environment
- Building from source
- Creating distributable .dmg files
- Contributing guidelines

---

## 📁 How It Works

### Download Structure

4Charm creates an organized, predictable folder hierarchy:

```
Downloads/
├── g-12345678/              # Board code + thread ID
│   ├── img001.jpg           # Images in root
│   ├── img002.png
│   ├── doc001.pdf           # Documents in root
│   └── WEBM/                # Videos in subfolder
│       ├── vid001.webm
│       └── vid002.webm
│
├── wg-99887766/
│   ├── wallpaper001.png
│   └── WEBM/
│       └── clip001.webm
│
└── tv-44556677/
    └── ...
```

### Naming Convention

Files are named sequentially to preserve order and avoid conflicts:
- `img001.jpg`, `img002.png` - Images
- `vid001.webm`, `vid002.mp4` - Videos (in WEBM subfolder)
- `doc001.pdf`, `doc002.txt` - Documents

### Duplicate Prevention

Every file is SHA-256 hashed before download:
```python
# Pseudocode
if sha256(remote_file) in downloaded_hashes:
    skip_download()
else:
    download_and_hash()
```

This prevents downloading the same image twice, even if:
- Reposted in different threads
- Downloaded during resume after interrupt
- Present in multiple catalog pages

### Rate Limiting Strategy

4Charm implements adaptive throttling:
1. **Initial requests** - Normal speed
2. **429 response detected** - Exponential backoff
3. **Rate limit lifted** - Gradually increase speed
4. **Sustained success** - Return to optimal rate

This keeps you under 4chan's radar while maximizing download speed.

---

## 🎯 Supported Media

| Type | Formats | Notes |
|------|---------|-------|
| **Images** | JPG, PNG, GIF, WEBP, BMP | All standard image formats |
| **Videos** | WEBM, MP4, MOV, AVI, MKV | WEBM most common on 4chan |
| **Documents** | PDF, TXT, ZIP, RAR | Archives preserved as-is |

**Total supported:** 15+ file formats

---

## 💻 Requirements

### System Requirements
- **OS:** macOS 10.13 (High Sierra) or later
- **Disk Space:** ~2 GB free (for app + downloads)
- **Network:** Stable internet connection
- **Architecture:** Intel or Apple Silicon (M1/M2/M3)

### What You Get
- ✅ Standalone .app file - just download and run
- ✅ No installation headaches
- ✅ No technical setup required
- ✅ Works right out of the box

---

## 🛠️ Troubleshooting

### Common Issues

**"App is damaged / Cannot be opened"**
```bash
# Solution: Remove quarantine attribute
sudo xattr -cr /Applications/4Charm.app
```
This happens because the app isn't signed with an Apple Developer ID. The command tells macOS to trust it.

**Downloads are slow**
- 4chan has speed limits for everyone
- 4Charm automatically adjusts to stay safe
- Be patient - it's working correctly!

**"No media found" for a valid thread**
- Thread might be deleted or archived
- Double-check the URL for typos
- Some threads are text-only with no media

**App crashes on launch**
- Make sure you're on macOS 10.13 or newer
- Check System Preferences → Security & Privacy
- Try the Gatekeeper fix at the top

**Downloads didn't finish**
- Just restart 4Charm and add the URL again
- It will skip files you already downloaded
- Check your download folder - you might have more than you think!

---

## 🤝 Contributing

Contributions welcome! If you find bugs or have ideas for improvements:

1. **Report bugs:** [GitHub Issues](https://github.com/RazorBackRoar/4Charm/issues)
2. **Suggest features:** [GitHub Discussions](https://github.com/RazorBackRoar/4Charm/discussions)
3. **Fork and improve:** Submit a pull request

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

**TL;DR:** Do whatever you want with this code. Use it, modify it, sell it, just keep the license notice.

---

## 🔐 Privacy & Security

### What 4Charm Does
- ✅ Downloads media from 4chan's public API
- ✅ Stores files locally on your Mac
- ✅ Reads/writes local configuration

### What 4Charm Does NOT Do
- ❌ No telemetry or analytics
- ❌ No tracking or logging of URLs you download
- ❌ No phone-home behavior
- ❌ No ads or monetization
- ❌ No account creation or login

**Data flow:** Your Mac ↔ 4chan's API. That's it.

### Security Considerations
- App is **not sandboxed** (requires filesystem access for downloads)
- App is **not notarized** (no Apple Developer ID)
- Source code is **100% open** for audit

If you're concerned, build from source and inspect the code yourself.

---

## 💬 Support & Community

### Getting Help
- **Bug reports:** [GitHub Issues](https://github.com/RazorBackRoar/4Charm/issues)
- **Feature requests:** [GitHub Discussions](https://github.com/RazorBackRoar/4Charm/discussions)
- **Source code:** [GitHub Repository](https://github.com/RazorBackRoar/4Charm)

### Reporting Bugs
Please include:
- macOS version
- 4Charm version
- Steps to reproduce
- Relevant log output (from the in-app log viewer)

---

## 🙏 Acknowledgments

- Built with [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python)
- Uses [4chan API](https://github.com/4chan/4chan-API) for media discovery
- Inspired by the need for a decent macOS archival tool

---

<div align="center">

**Made with ⚡ for archivists, by archivists**

[⬇️ Download](https://github.com/RazorBackRoar/4Charm/releases) • [📖 Docs](BUILD.md) • [🐛 Report Bug](https://github.com/RazorBackRoar/4Charm/issues) • [💡 Request Feature](https://github.com/RazorBackRoar/4Charm/discussions)

</div>
