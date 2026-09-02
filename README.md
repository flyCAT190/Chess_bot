# ✦ ChessBot Studio v13.0 ✦

ChessBot Studio adalah aplikasi desktop berbasis Python (CustomTkinter) yang mengintegrasikan engine catur **Stockfish** dengan browser automation (**Selenium**) untuk membantu atau mengotomatiskan permainan catur secara real-time di platform **Chess.com** dan **Lichess.org**.

Dilengkapi dengan sistem *Smart Humanizer*, kalkulasi *Blunder/Suboptimal* acak, dukungan pembukaan catur (*Opening Book*), serta *Global Hotkey* untuk kontrol instan.

---

## ✨ Fitur Utama

- **🧠 Smart Humanizer & Delay**: Menyesuaikan jeda waktu berpikir secara dinamis berdasarkan kontrol waktu (Bullet, Blitz, Rapid) dan situasi papan (seperti langkah pembukaan, makan bidak, atau skak).
- **🤡 Humanizer Blunder/Suboptimal**: Fitur opsional untuk sengaja melakukan langkah suboptimal atau blunder kecil secara berkala agar permainan terlihat seperti manusia asli.
- **👁️ Mode Asisten**: Menampilkan panah visual hijau langsung di atas papan catur situs web sebagai panduan langkah terbaik tanpa menggerakkan bidak secara otomatis.
- **🔁 Auto Next / Rematch**: Otomatis mendeteksi akhir game dan siap melanjutkan ke permainan berikutnya atau menerima *rematch* di Chess.com.
- **📊 Live Scoreboard & Analytics**: Mencatat statistik kemenangan (Win, Loss, Draw) secara langsung dan mendeteksi langkah taktis/brilian (*Brilliant Move*).
- **⌨️ Global Hotkey (F9)**: Tekan tombol **F9** di keyboard kapan saja untuk melakukan *Pause* atau *Resume* bot dengan cepat.
- **🎯 Dynamic ELO Scaling**: Menyesuaikan skill level engine Stockfish secara otomatis atau manual sesuai target ELO.

---

## 🛠️ Prasyarat

Sebelum menjalankan bot ini, pastikan Anda telah menginstal:
1. **Python 3.8+** di komputer Anda.
2. **Stockfish Engine** (Unduh file `.exe` Stockfish dari situs resminya).
3. **Google Chrome** & **ChromeDriver** yang kompatibel dengan versi browser Chrome Anda.

---

## 📦 Instalasi & Penggunaan

1. **Clone atau Unduh Repository Ini**
   ```bash
   git clone https://github.com/flyCAT190/chess-bot-studio.git
   cd chess-bot-studio
   ```

2. **Install Pustaka (Library) yang Dibutuhkan**
   Gunakan file `requirements.txt` untuk menginstal seluruh dependensi dengan cepat:
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan Aplikasi**
   ```python
   python chess_bot_selenium.py
   ```

---

## ⚙️ Konfigurasi di GUI

- **Path Stockfish Engine**: Arahkan ke file `.exe` Stockfish Anda.
- **Buku Pembukaan (.bin)**: *(Opsional)* Masukkan file pembukaan catur Polyglot untuk variasi langkah awal.
- **Cookie Session (PHPSESSID)**: *(Opsional)* Masukkan cookie sesi akun Chess.com Anda untuk melakukan *auto-login*.
- **Target Elo & Blunder**: Sesuaikan tingkat kesulitan dan persentase peluang blunder manusiawi sesuai kebutuhan.

---

## ⚠️ Catatan Penting
Aplikasi ini dibuat untuk tujuan edukasi dan eksperimen otomasi pemrograman Python. Penggunaan bot bantuan engine pada pertandingan resmi/kompetitif secara online dapat melanggar ketentuan layanan platform catur (Fair Play Policy) dan berisiko pada pemblokiran akun. Gunakan secara bijak!
