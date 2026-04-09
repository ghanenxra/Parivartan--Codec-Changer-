<![CDATA[<div align="center">

# 🎬 Parivartan — Video Transcoder

**A modern, dark-themed desktop video transcoder for H.265 ↔ H.264 conversion.**

Built with **Python**, **PyQt6**, and **FFmpeg** — featuring GPU acceleration, drag & drop, and real-time progress tracking.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-Desktop_UI-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Transcoding-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

---

</div>

## ✨ Features

| Feature | Description |
|---|---|
| 🔄 **H.265 ↔ H.264** | Convert between HEVC and AVC codecs with a single click |
| ⚡ **GPU Acceleration** | NVIDIA NVENC support for blazing-fast conversions |
| 🖥️ **CPU Fallback** | Automatic CPU encoding when GPU is unavailable |
| 📂 **Drag & Drop** | Drop video files directly onto the window |
| 🎨 **Modern Dark UI** | Sleek, dark-themed interface with smooth styling |
| 📊 **Real-Time Progress** | Live progress bar, speed indicator, ETA, and elapsed time |
| 🔍 **Media Inspector** | Detailed metadata viewer for streams, codecs, and tags |
| 🖼️ **Video Thumbnails** | Auto-generated preview thumbnails for loaded files |
| 🎚️ **Quality Presets** | Original, Balanced, and Compressed quality modes |
| 📦 **Multi-Format Output** | Export to MP4, MOV, or MKV containers |
| 📝 **Logging** | Automatic logging to `transcoder.log` for debugging |

---

## 📸 Screenshots

<!-- Add your screenshots here -->
<!-- ![Main Window](screenshots/main.png) -->
<!-- ![Metadata Dialog](screenshots/metadata.png) -->

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **FFmpeg & FFprobe** binaries (placed in the `assets/` folder)
- **NVIDIA GPU** *(optional — for hardware-accelerated encoding)*

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ghanenxra/Parivartan.git
   cd Parivartan
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Place FFmpeg binaries:**

   Download [FFmpeg](https://ffmpeg.org/download.html) and place `ffmpeg.exe` and `ffprobe.exe` inside the `assets/` directory:
   ```
   Parivartan/
   ├── assets/
   │   ├── ffmpeg.exe
   │   ├── ffprobe.exe
   │   ├── logo.ico
   │   └── ...
   ├── main.py
   ├── requirements.txt
   └── README.md
   ```

4. **Run the app:**
   ```bash
   python main.py
   ```

---

## 🎮 Usage

1. **Import a video** — Click `📂 Import Video` or **drag & drop** a file onto the window.
2. **Review metadata** — File details, codec, resolution, FPS, and audio info are displayed automatically. Click **Show More ▸** for full metadata.
3. **Configure settings:**
   - **Codec** — Choose between H.264 (AVC) or H.265 (HEVC).
   - **Quality** — Select Original, Balanced, or Compressed.
   - **Format** — Pick MP4, MOV, or MKV output.
   - **Output Folder** — Defaults to the source file's directory.
4. **Toggle GPU/CPU** — Use the GPU toggle at the top to switch between NVENC and CPU encoding.
5. **Start conversion** — Click `▶ Start Conversion` and monitor progress in real time.

### Supported Input Formats

`.mp4` · `.mkv` · `.mov` · `.avi` · `.webm` · `.ts`

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core application logic |
| **PyQt6** | Desktop GUI framework |
| **FFmpeg** | Video transcoding engine |
| **FFprobe** | Media metadata extraction |
| **NVIDIA NVENC** | Hardware-accelerated encoding |

---

## 📁 Project Structure

```
Parivartan/
├── assets/
│   ├── ffmpeg.exe              # FFmpeg binary
│   ├── ffprobe.exe             # FFprobe binary
│   ├── logo.ico                # App icon
│   ├── qr.png                  # Donation QR code
│   └── CormorantGaramond-Bold.ttf  # Custom font
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

---

## ☕ Support

If you find Parivartan useful, consider supporting the project:

- 💳 **PayPal:** [@ghanenxra](https://www.paypal.com/paypalme/ghanenxra)
- ⭐ **Star** this repository to show your support!

---

## 🔗 Links

- 🐙 **GitHub:** [github.com/ghanenxra](https://github.com/ghanenxra)
- 💬 **Discord:** [ghanenxra](https://discord.com/users/1323161662739714120)

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by [ghanenxra](https://github.com/ghanenxra)**

</div>
]]>
