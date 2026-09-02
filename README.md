# ✦ ChessBot Studio  ✦

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Selenium](https://img.shields.io/badge/Selenium-4.15%2B-green?style=for-the-badge&logo=selenium)
![Stockfish](https://img.shields.io/badge/Engine-Stockfish-orange?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Chess.com%20%7C%20Lichess-purple?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge)

**Aplikasi desktop otomasi catur berbasis Python dengan engine Stockfish, browser automation Selenium, Smart Humanizer, Analytics, dan banyak fitur canggih lainnya.**

</div>

---

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Prasyarat](#-prasyarat)
- [Instalasi](#-instalasi)
- [Cara Penggunaan](#-cara-penggunaan)
- [Penjelasan Tab GUI](#-penjelasan-tab-gui)
- [Hotkey](#%EF%B8%8F-hotkey)
- [Struktur Folder Output](#-struktur-folder-output)
- [Konfigurasi Lanjutan](#-konfigurasi-lanjutan)
- [Troubleshooting](#-troubleshooting)
- [Catatan Penting](#%EF%B8%8F-catatan-penting)

---

## ✨ Fitur Utama

### 🤖 Engine & Gameplay
| Fitur | Deskripsi |
|-------|-----------|
| **Stockfish Integration** | Koneksi langsung ke Stockfish UCI engine dengan konfigurasi Skill Level otomatis |
| **Dynamic ELO Scaling** | Target ELO 200–3200 dengan fluktuasi acak ±150 tiap game agar terlihat natural |
| **Opening Book** | Dukungan file Polyglot `.bin` untuk variasi langkah pembukaan |
| **Endgame Tablebase** | Integrasikan folder Syzygy — posisi ≤7 buah dimainkan sempurna via DTZ probe |
| **⚡ Pre-Move** | Kalkulasi langkah berikutnya di background saat giliran lawan — eksekusi instan saat giliran tiba |
| **Multi-PV Analysis** | Analisis top-2 langkah untuk implementasi fitur blunder humanizer |

### 🧠 Smart Humanizer
| Fitur | Deskripsi |
|-------|-----------|
| **Smart Delay** | Delay dinamis berdasarkan time control: Bullet (0.1–0.4s), Blitz (0.5–2s), Rapid (2–5s) |
| **Context-aware Delay** | Delay lebih pendek di pembukaan, lebih panjang saat makan bidak atau kena skak |
| **Hesitation Simulation** | 10% probabilitas delay panjang acak untuk mensimulasi keragu-raguan |
| **⏰ Time Management Adaptif** | Pangkas delay otomatis saat waktu menipis: <10 detik → 0.1s, <30 detik → 0.3s |
| **Blunder/Suboptimal** | Slider probabilitas 0–30% untuk sengaja memainkan langkah ke-2 terbaik |
| **🕵️ Anti-Detection Mouse** | Gerakan mouse acak 2–4 titik di papan sebelum setiap langkah via Selenium ActionChains |
| **🖥️ Fingerprint Randomizer** | Randomize User-Agent Chrome dari 4 profil browser yang berbeda tiap sesi |

### 👁️ Mode Asisten
Menampilkan **panah hijau SVG** langsung di atas papan catur di browser sebagai panduan langkah terbaik, tanpa menggerakkan bidak secara otomatis. Cocok digunakan sambil bermain manual.

### 📊 Analytics & Tracking
| Fitur | Deskripsi |
|-------|-----------|
| **Live Scoreboard** | Hitungan Win / Loss / Draw real-time di header GUI |
| **🎯 Accuracy Tracker** | Hitung rata-rata centipawn loss dan konversi ke persentase akurasi (0–100%) |
| **📈 Win Rate Graph** | Grafik live tren win rate per game menggunakan matplotlib |
| **📚 Opening Tracker** | Deteksi nama opening dari ECO mapping, tampilkan W/L/D per opening |
| **📊 Move Time CSV** | Export delay tiap langkah ke file `.csv` di folder `logs/move_times/` |
| **Brilliant Move Detection** | Deteksi dan notifikasi otomatis saat taktik brilliant tereksekusi |
| **Blunder Alert** | Notifikasi saat lawan melakukan blunder fatal (>250 cp) |

### 💾 Export & Simpan
| Fitur | Deskripsi |
|-------|-----------|
| **PGN Export** | Setiap game otomatis disimpan ke `pgn_games/` dalam format standar PGN |
| **Screenshot on Error** | Browser di-screenshot otomatis saat 3 error berturut-turut, simpan ke `logs/screenshots/` |
| **Auto Save Config** | Semua setting disimpan ke `chessbot_config.json` otomatis saat mulai/tutup |

### 🔄 Otomasi & Stabilitas
| Fitur | Deskripsi |
|-------|-----------|
| **Auto Next / Rematch** | Deteksi akhir game dan klik tombol New Game atau terima Rematch otomatis |
| **Auto-Login** | Inject cookie PHPSESSID untuk auto-login Chess.com |
| **👥 Multi-Account** | Masukkan beberapa cookie, rotasi akun otomatis setiap 10 game |
| **🔄 Auto-Reconnect** | Reload halaman otomatis jika browser/koneksi bermasalah (timeout 30 detik) |
| **🏳️ Auto-Resign / Draw** | Resign atau tawarkan draw otomatis jika evaluasi melewati threshold yang diset |

### ⏰ Kontrol & Penjadwalan
| Fitur | Deskripsi |
|-------|-----------|
| **Session Scheduler** | Set jam berhenti (HH:MM), bot mati sendiri tanpa perlu dijaga |
| **Global Hotkey F9** | Pause / Resume bot kapan saja dari keyboard |
| **🚨 Emergency Stop** | Tombol merah yang langsung matikan browser + engine + ambil screenshot |

### 📡 Notifikasi
| Fitur | Deskripsi |
|-------|-----------|
| **Discord Webhook** | Kirim ringkasan hasil game ke channel Discord otomatis |
| **Telegram Bot** | Kirim notifikasi ke Telegram via Bot API |

### 🖥️ UI/UX
| Fitur | Deskripsi |
|-------|-----------|
| **Dark / Light Theme** | Toggle tema CustomTkinter langsung dari header |
| **Minimize to Tray** | Bot tetap berjalan di system tray, window bisa ditutup |
| **Scrollable Tabs** | Semua panel bisa di-scroll, window bisa di-resize bebas |
| **Live FEN Display** | Tampilkan FEN posisi terkini, tombol copy ke clipboard |
| **Terminal Log** | Window log terpisah dengan tombol Clear dan Copy |

---

## 🛠️ Prasyarat

Sebelum menjalankan, pastikan sudah terinstall:

1. **Python 3.8+** — [Download](https://python.org/downloads)
2. **Stockfish Engine** — [Download](https://stockfishchess.org/download/) (ambil file `.exe` untuk Windows)
3. **Google Chrome** — versi terbaru
4. **ChromeDriver** — harus cocok dengan versi Chrome kamu — [Download](https://chromedriver.chromium.org/downloads) atau gunakan `webdriver-manager`
5. *(Opsional)* **Syzygy Tablebase** — [Download](https://syzygy-tables.info/) untuk endgame sempurna
6. *(Opsional)* **Polyglot Opening Book** `.bin` — tersedia di berbagai sumber online

---

## 📦 Instalasi

### 1. Clone Repository
```bash
git clone https://github.com/flyCAT190/Chess_bot.git
cd Chess_bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Daftar dependency:
```
customtkinter>=5.2.0   # GUI framework
selenium>=4.15.0       # Browser automation
chess>=1.10.0          # Chess logic + PGN + Polyglot + Syzygy
keyboard>=0.13.5       # Global hotkey F9
matplotlib>=3.7.0      # Win rate graph (opsional)
pystray>=0.19.5        # System tray (opsional)
Pillow>=10.0.0         # Icon tray (opsional)
```

> **Catatan:** `matplotlib`, `pystray`, dan `Pillow` bersifat opsional. Jika tidak terinstall, fitur terkait dinonaktifkan secara otomatis tanpa error.

### 3. Setup ChromeDriver

**Cara A — Manual:**
- Cek versi Chrome: buka `chrome://version/`
- Download ChromeDriver yang cocok dari [sini](https://chromedriver.chromium.org/downloads)
- Taruh `chromedriver.exe` di folder yang sama dengan `chessbot.py`, atau tambahkan ke PATH

**Cara B — Otomatis (direkomendasikan):**
```bash
pip install webdriver-manager
```
Lalu ganti baris di kode:
```python
# Ganti:
self.driver = webdriver.Chrome(options=options)

# Menjadi:
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
```

### 4. Jalankan
```bash
python chessbot.py
```

---

## 🎮 Cara Penggunaan

### Langkah Dasar

1. **Jalankan aplikasi** dengan `python chessbot.py`
2. **Tab ⚙️ Konfigurasi** — isi path Stockfish, pilih platform (Chess.com / Lichess)
3. **Tab 🎛️ Performa** — set Target ELO, waktu pikir, aktifkan/nonaktifkan fitur humanizer
4. **Buka browser** — klik **▶ MULAI SISTEM**, browser Chrome akan terbuka otomatis
5. **Login** ke Chess.com atau Lichess di browser yang terbuka
6. **Mulai game** — bot akan mendeteksi otomatis dan bermain

### Mode Auto (Full Bot)
- Pastikan switch **Mode Asisten** = OFF
- Bot bermain otomatis, termasuk auto next game jika **Auto Next** = ON

### Mode Asisten (Manual + Panduan)
- Aktifkan switch **👁️ Mode Asisten** = ON
- Bot tidak menggerakkan bidak, hanya menampilkan **panah hijau** di papan sebagai saran

### Auto-Login Chess.com
1. Login manual ke Chess.com di browser biasa
2. Buka DevTools → Application → Cookies → cari `PHPSESSID`
3. Salin nilainya ke field **Cookie** di tab Konfigurasi

---

## 📱 Penjelasan Tab GUI

### ⚙️ Tab Konfigurasi
| Field | Fungsi |
|-------|--------|
| **Stockfish Engine (.exe)** | Path ke file stockfish.exe |
| **Opening Book (.bin)** | Path ke file Polyglot opening book (opsional) |
| **Syzygy Tablebase (folder)** | Path ke folder berisi file `.rtbw`/`.rtbz` Syzygy (opsional) |
| **Platform** | Pilih Chess.com atau Lichess.org |
| **Warna** | Otomatis (auto-detect), Putih, atau Hitam |
| **FEN Display** | Menampilkan FEN posisi terkini + tombol copy |
| **Session Scheduler** | Aktifkan + isi jam berhenti format `HH:MM` |
| **Multi-Akun** | Isi beberapa cookie PHPSESSID (satu per baris), aktifkan rotasi |

### 🎛️ Tab Performa
| Setting | Fungsi |
|---------|--------|
| **Target ELO** | Slider 200–3200, dikalibrasi ke Stockfish Skill Level 0–20 |
| **Blunder %** | Probabilitas 0–30% untuk memainkan langkah ke-2 terbaik |
| **Waktu Pikir** | Batas waktu analisis Stockfish per langkah (0.1–5.0 detik) |
| **Smart Delay** | Aktifkan humanizer delay + pilih mode time control |
| **Beep** | Bunyi notifikasi saat giliran tiba |
| **Anti-Detection** | Gerakan mouse acak sebelum klik |
| **Auto-Reconnect** | Reload halaman otomatis jika browser bermasalah |
| **Fingerprint Rand.** | Randomize User-Agent Chrome tiap sesi |
| **Pre-Move** | Kalkulasi background saat giliran lawan |

### 🔬 Tab Advanced
| Setting | Fungsi |
|---------|--------|
| **Auto-Resign/Draw** | Aktifkan + set threshold centipawn loss |
| **Aksi** | Pilih antara Resign atau Tawarkan Draw |
| **Time Management** | Info batas delay adaptif berdasarkan sisa waktu jam |

### 📊 Tab Analytics
- **Win Rate Graph** — grafik live tren win rate per game
- **Opening Stats** — tabel win/loss/draw per nama opening yang dimainkan

### 📡 Tab Notifikasi
| Field | Fungsi |
|-------|--------|
| **Discord Webhook URL** | URL webhook Discord channel tujuan |
| **Telegram Token** | Token bot Telegram dari @BotFather |
| **Telegram Chat ID** | ID chat/group tujuan (gunakan @userinfobot untuk cek) |

---

## ⌨️ Hotkey

| Tombol | Fungsi |
|--------|--------|
| **F9** | Pause / Resume bot (global, bekerja di luar window) |
| **▶ MULAI** | Start bot + buka log terminal |
| **⏹ HENTIKAN** | Stop bot dengan graceful shutdown |
| **🚨 STOP** | Emergency stop — matikan paksa + screenshot |

---

## 📁 Struktur Folder Output

```
Chess_bot/
├── chessbot.py              # File utama
├── chessbot_config.json     # Config tersimpan otomatis
├── requirements.txt
│
├── pgn_games/               # File PGN tiap game
│   ├── game_1_20260902_200000.pgn
│   └── game_2_20260902_201500.pgn
│
└── logs/
    ├── screenshots/         # Screenshot saat error/emergency
    │   └── loop_error_20260902_200500.png
    │
    └── move_times/          # CSV delay tiap langkah
        └── game_1_20260902_200000.csv
```

### Format CSV Move Times
```
game,move_num,side,move,delay_s,eval,time
1,1,w,e2e4,0.31,+0.15,20:00:01
1,2,w,g1f3,0.87,+0.22,20:00:15
```

### Format Notifikasi (Discord / Telegram)
```
♟️ ChessBot Studio — Game #5
Hasil: 🏆 MENANG
Opening: Sicilian Defense
Langkah: 42 | Akurasi: 94.3%
Eval Akhir: +2.15
```

---

## ⚙️ Konfigurasi Lanjutan

### Mengatur ELO Target
ELO dikalibrasi otomatis ke Stockfish Skill Level menggunakan formula:
```
Skill Level = (ELO - 200) / 3000 × 20
```
- ELO 200  → Skill 0  (pemula)
- ELO 1600 → Skill 9  (menengah)
- ELO 3000 → Skill 20 (maksimal)

Setiap game baru, ELO diacak ±150 dari target untuk variasi natural.

### Mengatur Blunder Humanizer
- **0%** — bot selalu main langkah terbaik
- **5%** — ~1 dari 20 langkah adalah suboptimal (default, paling natural)
- **15%** — cukup sering blunder, mirip pemain amatir
- **30%** — hampir sepertiga langkah suboptimal

> Blunder tidak terjadi saat posisi skak atau di endgame kritis.

### Mengatur Threshold Auto-Resign
Nilai threshold dalam centipawn (cp):
- **300 cp** — resign saat tertinggal ~3 poin materi
- **500 cp** — resign saat posisi cukup buruk (default)
- **800 cp** — hanya resign di posisi sangat kalah

### Setup Discord Webhook
1. Buka channel Discord tujuan
2. Settings → Integrations → Webhooks → New Webhook
3. Copy Webhook URL → paste ke field Discord di tab Notifikasi

### Setup Telegram Bot
1. Chat ke [@BotFather](https://t.me/BotFather) di Telegram
2. Ketik `/newbot` dan ikuti instruksi
3. Salin **token** yang diberikan
4. Untuk Chat ID: forward pesan ke [@userinfobot](https://t.me/userinfobot) atau cek via API

---

## 🔧 Troubleshooting

### ❌ `Gagal memuat Stockfish`
- Pastikan path ke `.exe` benar dan file tidak corrupt
- Coba jalankan `stockfish.exe` langsung di CMD untuk verifikasi
- Download ulang dari [stockfishchess.org](https://stockfishchess.org/download/)

### ❌ `ChromeDriver version mismatch`
- Cek versi Chrome: `chrome://version/`
- Download ChromeDriver yang cocok dari [chromedriver.chromium.org](https://chromedriver.chromium.org)
- Atau gunakan `webdriver-manager` untuk auto-manage

### ❌ Bot tidak mendeteksi giliran / FEN selalu None
- Pastikan halaman sudah loading sempurna sebelum bot aktif
- Coba refresh halaman manual di browser yang dibuka bot
- Untuk Chess.com: pastikan berada di halaman game aktif, bukan lobby
- Auto-Reconnect akan menangani ini secara otomatis setelah 3 kali gagal

### ❌ Bot bergerak tapi langkah tidak terdaftar (Lichess)
- Lichess menggunakan simulasi mouse event — pastikan papan catur terlihat di viewport
- Jangan minimize atau overlap browser saat bot berjalan di Lichess

### ❌ `keyboard` error / Permission denied
- Jalankan CMD / terminal sebagai **Administrator**
- Library `keyboard` membutuhkan elevated permission di Windows

### ❌ Grafik win rate tidak muncul
```bash
pip install matplotlib
```

### ❌ System tray tidak berfungsi
```bash
pip install pystray Pillow
```

### ❌ `ModuleNotFoundError`
```bash
pip install -r requirements.txt --upgrade
```

---

## 📊 Perbandingan Mode

| Mode | Auto Gerak | Visual Panah | Cocok Untuk |
|------|-----------|--------------|-------------|
| **Full Auto** | ✅ | ❌ | Farming rating, grinding game |
| **Mode Asisten** | ❌ | ✅ | Belajar, panduan langkah saat bermain manual |

---

## 🗂️ Changelog

### v16.0 (Latest)
- ⚡ Pre-Move background calculation
- ⏰ Time Management Adaptif berdasarkan jam catur
- 🔢 Endgame Tablebase Syzygy support
- 👥 Multi-Account + auto rotasi
- 🖥️ Browser Fingerprint Randomizer
- 📚 Opening Repertoire Tracker (ECO)
- 📊 Move Time CSV export
- 📡 Discord + Telegram notifikasi
- ☀️ Dark/Light Theme Toggle
- 📥 Minimize to System Tray
- 🔄 Semua tab pakai ScrollableFrame (resizable)

### v15.0
- 🏳️ Auto-Resign / Auto-Draw
- ⏰ Session Scheduler
- 🕵️ Anti-Detection Mouse Movement
- 💾 PGN Export otomatis
- 📈 Win Rate Graph (matplotlib)
- 🎯 Accuracy Tracker
- 🔄 Auto-Reconnect
- 📸 Screenshot on Error

### v14.0
- 🔴 Emergency Stop Button
- ⚪ Live Status Label
- 📋 FEN Display + Copy
- 🔔 Beep Notifikasi Giliran
- 📋 Move History + Game Summary
- 🗑️ Clear / Copy Log
- 🛠️ Fix Lichess execute_move
- 🛠️ Fix auto-detect warna

### v13.0
- Rilis awal publik
- Smart Humanizer, Opening Book, Global Hotkey F9
- Live Scoreboard, Brilliant Move detection
- Auto Next / Rematch

---

## ⚠️ Catatan Penting

> **Disclaimer:** Aplikasi ini dibuat murni untuk tujuan **edukasi** dan **eksperimen otomasi Python**. Penggunaan bot pada pertandingan online resmi atau kompetitif dapat melanggar **Fair Play Policy** Chess.com maupun Lichess.org dan berisiko **pemblokiran akun permanen**. Penggunaan sepenuhnya menjadi tanggung jawab pengguna.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).

---

<div align="center">

**⭐ Jika project ini bermanfaat, jangan lupa berikan Star!**

Made with ❤️ by [flyCAT190](https://github.com/flyCAT190)

</div>
