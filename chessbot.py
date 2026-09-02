"""
╔══════════════════════════════════════════════════════╗
║         ✦ ChessBot Studio v16.0 ✦                   ║
║  Engine • Humanizer • Analytics • Anti-Detection     ║
║  Scheduler • PGN • Tray • Opening Tracker • Discord  ║
╚══════════════════════════════════════════════════════╝
"""
import time
import random
import threading
import sys
import os
import csv
import json
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timedelta
import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import chess
import chess.engine
import chess.polyglot
import chess.pgn
import keyboard
import urllib.request

# ── Optional deps (graceful fallback) ──────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.backends.backend_tkagg as backend_tkagg
    from matplotlib.figure import Figure
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_OK = True
except ImportError:
    TRAY_OK = False

# ── Dirs ───────────────────────────────────────────────────────────────────
CONFIG_FILE = "chessbot_config.json"
PGN_DIR     = "pgn_games"
LOG_DIR     = "logs"
SS_DIR      = os.path.join(LOG_DIR, "screenshots")
CSV_DIR     = os.path.join(LOG_DIR, "move_times")
for _d in (PGN_DIR, LOG_DIR, SS_DIR, CSV_DIR):
    os.makedirs(_d, exist_ok=True)

# ── ECO Opening DB (subset ringkas) ────────────────────────────────────────
ECO_MAP = {
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b": "King's Pawn (1.e4)",
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b": "Queen's Pawn (1.d4)",
    "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b": "English Opening",
    "rnbqkbnr/pppppppp/8/8/1P6/8/P1PPPPPP/RNBQKBNR b": "Larsen's Opening",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w": "Open Game (1.e4 e5)",
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w": "Sicilian Defense",
    "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w": "French Defense",
    "rnbqkbnr/ppp1pppp/3p4/8/4P3/8/PPPP1PPP/RNBQKBNR w": "Caro-Kann / Pirc",
    "rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w": "Budapest / Englund",
    "rnbqkb1r/pppp1ppp/5n2/4p3/4PP2/8/PPPP2PP/RNBQKBNR w": "King's Gambit Accepted",
}

JS_GET_GAME = """
function getGameObject() {
    if (window.game) return window.game;
    const board = document.querySelector('.board, chess-board');
    if (board && board.game) return board.game;
    return null;
}
"""

# ══════════════════════════════════════════════════════════════════════════
# PRINT LOGGER
# ══════════════════════════════════════════════════════════════════════════
class PrintLogger:
    def __init__(self, widget):
        self.widget = widget

    def write(self, text):
        try:
            if self.widget.winfo_exists():
                self.widget.insert("end", text)
                self.widget.see("end")
        except: pass

    def flush(self): pass


# ══════════════════════════════════════════════════════════════════════════
# CHESS BOT ENGINE
# ══════════════════════════════════════════════════════════════════════════
class ChessBotEngine:
    def __init__(self, config, gui):
        self.config  = config
        self.gui     = gui
        self.is_running   = True
        self.is_paused    = False
        self.last_fen     = ""
        self.last_eval_cp = 0
        self.move_history = []
        self.game_number  = 0
        self.current_fen  = ""
        self._my_side     = "w"

        # Accuracy
        self.accuracy_diffs = []

        # PGN
        self.pgn_game = None
        self.pgn_node = None

        # Pre-move
        self._premove      = None
        self._premove_fen  = None
        self._premove_thread = None

        # Opening tracker
        self.opening_stats = {}   # {name: {"W":0,"L":0,"D":0}}
        self.current_opening = "Unknown"

        # Move-time CSV
        self._move_time_rows = []   # [(game, move_num, side, move, delay, eval)]
        self._move_time_start = None

        # Multi-account
        self._account_index = 0

        # Scheduler
        self._scheduler_stop_at = None

        keyboard.add_hotkey('f9', self.toggle_pause)
        print(f"[SISTEM] Memulai ChessBot Studio v16.0 — {self.config['platform']}")
        print("[SISTEM] ⌨️  F9 = Pause/Resume")

        # Engine
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.config['stockfish_path'])
            self.engine.configure({"Skill Level": self.elo_to_skill(self.config['target_elo'])})
        except Exception as e:
            print(f"[ERROR] Stockfish gagal: {e}"); self.is_running = False; return

        # Browser
        options = webdriver.ChromeOptions()
        # [FITUR 5] Randomize User-Agent
        if self.gui.var_fingerprint.get():
            ua = random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 Safari/605.1.15",
            ])
            options.add_argument(f"--user-agent={ua}")
            tz = random.choice(["Asia/Jakarta","Asia/Singapore","America/New_York","Europe/London","Asia/Tokyo"])
            options.add_experimental_option("prefs", {"intl.accept_languages": "en,en_US"})
            print(f"[FINGERPRINT] UA: {ua[:50]}... | TZ: {tz}")

        self.driver = webdriver.Chrome(options=options)

        # [FITUR 4] Multi-account login
        self._do_login()

        target_url = "https://lichess.org/" if self.config['platform'] == "Lichess.org" else "https://www.chess.com/play/online"
        self.driver.get(target_url)
        print("[SISTEM] Bot Standby. Menunggu Game...\n")

        self.last_slider_elo   = self.config['target_elo']
        self.current_match_elo = self.config['target_elo']
        self.is_new_match      = True

        self._apply_scheduler()
        self.board = chess.Board()

    # ─────────────────────────────────────────────────────────────────────
    # [FITUR 4] MULTI-ACCOUNT LOGIN
    # ─────────────────────────────────────────────────────────────────────
    def _do_login(self):
        accounts = self.gui.get_accounts()
        if not accounts:
            return
        idx = self._account_index % len(accounts)
        cookie = accounts[idx].strip()
        if not cookie:
            return
        if self.config['platform'] == "Chess.com":
            try:
                print(f"[AKUN] Login akun #{idx+1}...")
                self.driver.get("https://www.chess.com/")
                time.sleep(2)
                self.driver.add_cookie({
                    "name": "PHPSESSID", "value": cookie,
                    "domain": ".chess.com", "path": "/"
                })
                self.driver.refresh()
                time.sleep(2)
                print(f"[AKUN] ✅ Login akun #{idx+1} berhasil!")
            except Exception as e:
                print(f"[AKUN] ⚠️ Login gagal: {e}")

    def _rotate_account(self):
        self._account_index += 1
        print(f"\n[AKUN] 🔄 Rotasi ke akun #{(self._account_index % max(1, len(self.gui.get_accounts())))+1}\n")
        self._do_login()

    # ─────────────────────────────────────────────────────────────────────
    # SCHEDULER
    # ─────────────────────────────────────────────────────────────────────
    def _apply_scheduler(self):
        if not self.gui.var_scheduler.get():
            return
        try:
            h, m = map(int, self.gui.entry_sched_stop.get().strip().split(":"))
            now = datetime.now()
            stop_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if stop_dt <= now:
                stop_dt += timedelta(days=1)
            self._scheduler_stop_at = stop_dt
            print(f"[SCHEDULER] Berhenti pada {stop_dt.strftime('%H:%M')}")
        except: self._scheduler_stop_at = None

    def _check_scheduler(self):
        if self._scheduler_stop_at and datetime.now() >= self._scheduler_stop_at:
            print(f"\n[SCHEDULER] ⏰ Waktu berhenti tercapai. Bot dihentikan.\n")
            self.stop()
            self.gui.set_status("⏰ Scheduler: dihentikan")
            self.gui.after(0, lambda: self.gui.btn_start.configure(
                text="▶ MULAI SISTEM", fg_color="#10b981", hover_color="#059669"))

    # ─────────────────────────────────────────────────────────────────────
    # TOGGLE PAUSE
    # ─────────────────────────────────────────────────────────────────────
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        s = "⏸️ DIJEDA" if self.is_paused else "▶️ DILANJUTKAN"
        print(f"\n[F9] Bot {s}!\n")
        self.gui.set_status("⏸️ Dijeda" if self.is_paused else "▶️ Berjalan")

    # ─────────────────────────────────────────────────────────────────────
    # ELO / SKILL
    # ─────────────────────────────────────────────────────────────────────
    def elo_to_skill(self, elo):
        if elo >= 3000: return 20
        if elo <= 200:  return 0
        return int((elo - 200) / 3000 * 20)

    def auto_adjust_match_elo(self):
        base = self.gui.scale_elo.get()
        self.current_match_elo = max(200, min(3200, base + random.randint(-150, 150)))
        skill = self.elo_to_skill(self.current_match_elo)
        try:
            self.engine.configure({"Skill Level": skill})
            print(f"[ELO] 🎲 Game #{self.game_number} — ELO: {int(self.current_match_elo)} (Skill: {skill})")
        except: pass

    def update_live_settings(self):
        try:
            cur = self.gui.scale_elo.get()
            if cur != self.last_slider_elo:
                self.last_slider_elo = cur
                self.engine.configure({"Skill Level": self.elo_to_skill(cur)})
                print(f"[ELO] 🎯 Manual: {int(cur)}")
        except: pass

    # ─────────────────────────────────────────────────────────────────────
    # JS HELPER
    # ─────────────────────────────────────────────────────────────────────
    def js(self, script):
        try: return self.driver.execute_script(JS_GET_GAME + script)
        except: return None

    # ─────────────────────────────────────────────────────────────────────
    # GAME STATE
    # ─────────────────────────────────────────────────────────────────────
    def check_game_over(self):
        if self.config['platform'] == "Chess.com":
            return self.js("const g=getGameObject(); return g&&g.isGameOver?g.isGameOver():false;")
        try: return self.driver.execute_script("return document.querySelector('.result-wrap')!==null;")
        except: return False

    def check_result(self):
        res = self.js("""
        const m=document.querySelector('.game-over-modal-content')||document.querySelector('.game-over-header-component');
        if(m){const t=m.innerText.toLowerCase();
          if(t.includes('won')||t.includes('menang'))return'WIN';
          if(t.includes('lost')||t.includes('kalah'))return'LOSS';
          if(t.includes('draw')||t.includes('seri'))return'DRAW';}
        return'UNKNOWN';
        """)
        if res in ('WIN','LOSS','DRAW'):
            self.gui.update_scoreboard(res)
            if self.pgn_game:
                tag = {'WIN':'1-0' if self._my_side=='w' else '0-1',
                       'LOSS':'0-1' if self._my_side=='w' else '1-0',
                       'DRAW':'1/2-1/2'}
                self.pgn_game.headers['Result'] = tag.get(res,'*')
        return res or 'UNKNOWN'

    def handle_next_game(self):
        if not self.gui.var_nextgame.get() or self.config['platform'] != "Chess.com":
            return
        r = self.js("""
        const btns=Array.from(document.querySelectorAll('button')).filter(b=>b.offsetParent!==null&&b.innerText);
        const pt=document.body.innerText.toLowerCase();
        const isR=pt.includes('wants a rematch')||pt.includes('rematch offer');
        const rb=btns.find(b=>b.innerText.toLowerCase().includes('rematch'));
        if(rb&&isR){rb.click();return'REMATCH';}
        const nb=btns.find(b=>{const t=b.innerText.toLowerCase();return t.startsWith('new ')||t==='new game'||t.includes('play again');});
        if(nb){nb.click();return'NEWGAME';}return'WAIT';
        """)
        if r == 'REMATCH':   print("\n🤝 Rematch diterima!\n");   time.sleep(3)
        elif r == 'NEWGAME': print("\n🚀 Game baru dimulai!\n");  time.sleep(3)

    def get_fen(self):
        if self.config['platform'] == "Chess.com":
            return self.js("const g=getGameObject();return g?g.getFEN():null;")
        try:
            return self.driver.execute_script("""
                if(window.lichess&&window.lichess.analysis)return window.lichess.analysis.node.fen;
                const c=document.querySelector('.cg-wrap');
                if(c&&c.__vue__)return c.__vue__.fen||null;return null;""")
        except: return None

    def get_side(self):
        c = self.config['warna_manual']
        if c in ('w','b'): return c
        if self.config['platform'] == "Chess.com":
            s = self.js("const g=getGameObject();return g&&g.getPlayingAs?g.getPlayingAs():null;")
            if s is None:
                f = self.js("const b=document.querySelector('chess-board');return b?b.classList.contains('flipped'):false;")
                return "b" if f else "w"
            return "w" if s == 1 else "b"
        try:
            ib = self.driver.execute_script(
                "const w=document.querySelector('.cg-wrap');return w?w.classList.contains('orientation-black'):false;")
            return "b" if ib else "w"
        except: return "w"

    # ─────────────────────────────────────────────────────────────────────
    # [FITUR 2] TIME MANAGEMENT ADAPTIF
    # ─────────────────────────────────────────────────────────────────────
    def _get_my_clock_seconds(self):
        """Ambil sisa waktu jam catur kita (detik). Fallback None jika gagal."""
        try:
            if self.config['platform'] == "Chess.com":
                script = """
                const clocks = Array.from(document.querySelectorAll('.clock-time-monospace, .clock-component'));
                if (!clocks.length) return null;
                // Ambil jam yang sedang tidak aktif (giliran lawan = jam kita berhenti)
                // Tapi kita butuh jam kita → cari elemen bottom (biasanya kita di bawah)
                const bottom = document.querySelector('.clock-bottom .clock-time-monospace, .player-component.player-bottom .clock-time-monospace');
                if (!bottom) return null;
                const t = bottom.innerText.trim();
                const parts = t.split(':');
                if (parts.length === 2) return parseInt(parts[0])*60 + parseFloat(parts[1]);
                if (parts.length === 3) return parseInt(parts[0])*3600 + parseInt(parts[1])*60 + parseFloat(parts[2]);
                return null;
                """
                return self.driver.execute_script(script)
        except: return None

    def _time_management_delay(self, base_delay):
        """Sesuaikan delay berdasarkan sisa waktu."""
        secs = self._get_my_clock_seconds()
        if secs is None:
            return base_delay
        if secs < 10:
            return min(base_delay, 0.1)   # kritis: langsung gerak
        if secs < 30:
            return min(base_delay, 0.3)   # mendesak
        if secs < 60:
            return min(base_delay, 0.8)
        return base_delay                  # waktu cukup: delay normal

    # ─────────────────────────────────────────────────────────────────────
    # [FITUR 1] PRE-MOVE (kalkulasi background saat giliran lawan)
    # ─────────────────────────────────────────────────────────────────────
    def _start_premove_calc(self, fen):
        """Mulai kalkulasi pre-move di thread terpisah."""
        if not self.gui.var_premove.get():
            return
        self._premove = None
        self._premove_fen = None
        def _calc():
            try:
                b = chess.Board(fen)
                # Pertimbangkan kemungkinan respons lawan: ambil top move setelah kandidat lawan
                opp_info = self.engine.analyse(b, chess.engine.Limit(time=0.3), multipv=1)
                opp_move = opp_info[0].get("pv")[0] if opp_info else None
                if opp_move:
                    b.push(opp_move)
                    my_info = self.engine.analyse(b, chess.engine.Limit(time=self.gui.scale_time.get()), multipv=1)
                    my_move = my_info[0].get("pv")[0] if my_info else None
                    self._premove = my_move
                    self._premove_fen = b.fen()
                    if my_move:
                        print(f"[PRE-MOVE] 🧠 Kalkulasi selesai: {my_move} (siap dieksekusi)")
            except: pass
        self._premove_thread = threading.Thread(target=_calc, daemon=True)
        self._premove_thread.start()

    def _use_premove(self, current_fen):
        """Gunakan hasil pre-move jika FEN cocok."""
        if not self.gui.var_premove.get():
            return None
        if self._premove and self._premove_fen:
            b_pre = chess.Board(self._premove_fen)
            b_cur = chess.Board(current_fen)
            if b_pre.fen() == b_cur.fen():
                move = self._premove
                self._premove = None
                self._premove_fen = None
                print(f"[PRE-MOVE] ⚡ Menggunakan pre-move: {move}")
                return move
        return None

    # ─────────────────────────────────────────────────────────────────────
    # [FITUR 3] ENDGAME TABLEBASE
    # ─────────────────────────────────────────────────────────────────────
    def _tablebase_move(self):
        """Coba ambil move dari Syzygy tablebase jika tersedia."""
        tb_path = self.gui.entry_tablebase.get().strip()
        if not tb_path or not os.path.isdir(tb_path):
            return None
        piece_count = len(self.board.piece_map())
        if piece_count > 7:
            return None
        try:
            with chess.syzygy.open_tablebase(tb_path) as tb:
                dtz = tb.probe_dtz(self.board)
                # Cari move yang mempertahankan DTZ terbaik
                best_move = None
                best_dtz  = None
                for move in self.board.legal_moves:
                    self.board.push(move)
                    try:
                        d = tb.probe_dtz(self.board)
                        if best_dtz is None or d < best_dtz:
                            best_dtz  = d
                            best_move = move
                    except: pass
                    finally: self.board.pop()
                if best_move:
                    print(f"[TABLEBASE] ♟️ TB Move: {best_move} (DTZ: {best_dtz})")
                    return best_move
        except Exception as e:
            pass
        return None

    # ─────────────────────────────────────────────────────────────────────
    # [FITUR 6] OPENING TRACKER
    # ─────────────────────────────────────────────────────────────────────
    def _detect_opening(self, fen):
        # Cocokkan dengan ECO_MAP menggunakan prefix FEN (tanpa counter)
        fen_prefix = " ".join(fen.split()[:4])
        for key, name in ECO_MAP.items():
            if fen_prefix.startswith(" ".join(key.split()[:3])):
                return name
        return self.current_opening   # pertahankan opening terakhir yang terdeteksi

    def _update_opening_stat(self, opening, result):
        if not opening or opening == "Unknown":
            return
        if opening not in self.opening_stats:
            self.opening_stats[opening] = {"W":0,"L":0,"D":0}
        key = result[0] if result in ('WIN','LOSS','DRAW') else 'D'
        self.opening_stats[opening][key] += 1
        self.gui.update_opening_table(self.opening_stats)

    # ─────────────────────────────────────────────────────────────────────
    # [FITUR 7] MOVE TIME CSV
    # ─────────────────────────────────────────────────────────────────────
    def _record_move_time(self, move_num, side, move, delay, eval_str):
        self._move_time_rows.append([
            self.game_number, move_num, side, str(move), f"{delay:.2f}", eval_str,
            datetime.now().strftime("%H:%M:%S")
        ])

    def _save_move_time_csv(self):
        if not self._move_time_rows:
            return
        fname = os.path.join(CSV_DIR, f"game_{self.game_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            with open(fname, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["game","move_num","side","move","delay_s","eval","time"])
                w.writerows(self._move_time_rows)
            print(f"[CSV] 📊 Move times disimpan: {fname}")
        except Exception as e:
            print(f"[CSV] ⚠️ {e}")

    # ─────────────────────────────────────────────────────────────────────
    # [FITUR 8] DISCORD / TELEGRAM NOTIFIKASI
    # ─────────────────────────────────────────────────────────────────────
    def _send_notification(self, result, eval_str, moves):
        acc = self._calc_accuracy()
        opening = self.current_opening
        msg = (f"♟️ *ChessBot Studio* — Game #{self.game_number}\n"
               f"Hasil: {'🏆 MENANG' if result=='WIN' else '❌ KALAH' if result=='LOSS' else '🤝 SERI'}\n"
               f"Opening: {opening}\n"
               f"Langkah: {moves} | Akurasi: {acc}%\n"
               f"Eval Akhir: {eval_str}")

        # Discord
        dc_url = self.gui.entry_discord.get().strip()
        if dc_url.startswith("https://discord"):
            def _send_dc():
                try:
                    payload = json.dumps({"content": msg}).encode()
                    req = urllib.request.Request(dc_url, data=payload,
                        headers={"Content-Type": "application/json"}, method="POST")
                    urllib.request.urlopen(req, timeout=5)
                    print("[DISCORD] ✅ Notifikasi terkirim")
                except Exception as e:
                    print(f"[DISCORD] ⚠️ {e}")
            threading.Thread(target=_send_dc, daemon=True).start()

        # Telegram
        tg_token = self.gui.entry_tg_token.get().strip()
        tg_chat  = self.gui.entry_tg_chat.get().strip()
        if tg_token and tg_chat:
            def _send_tg():
                try:
                    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                    payload = json.dumps({"chat_id": tg_chat, "text": msg, "parse_mode": "Markdown"}).encode()
                    req = urllib.request.Request(url, data=payload,
                        headers={"Content-Type": "application/json"}, method="POST")
                    urllib.request.urlopen(req, timeout=5)
                    print("[TELEGRAM] ✅ Notifikasi terkirim")
                except Exception as e:
                    print(f"[TELEGRAM] ⚠️ {e}")
            threading.Thread(target=_send_tg, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────
    # ANTI-DETECTION MOUSE
    # ─────────────────────────────────────────────────────────────────────
    def _anti_detection_mouse(self):
        if not self.gui.var_anti_detection.get():
            return
        try:
            el = self.driver.find_element("css selector", "chess-board, .board, cg-board")
            r  = self.driver.execute_script(
                "const r=arguments[0].getBoundingClientRect();return{x:r.left,y:r.top,w:r.width,h:r.height};", el)
            ac = ActionChains(self.driver)
            for _ in range(random.randint(2, 4)):
                ac.move_by_offset(
                    random.uniform(0.1, 0.9) * r['w'],
                    random.uniform(0.1, 0.9) * r['h']
                ).pause(random.uniform(0.02, 0.08))
            ac.perform()
        except: pass

    # ─────────────────────────────────────────────────────────────────────
    # EXECUTE MOVE
    # ─────────────────────────────────────────────────────────────────────
    def execute_move(self, move):
        m = str(move)
        s, e, p = m[:2], m[2:4], m[4:] if len(m) > 4 else "q"
        self._anti_detection_mouse()

        if self.config['platform'] == "Chess.com":
            r = self.js(f"""
            const g=getGameObject();if(!g)return'NO_GAME';
            const l=g.getLegalMoves();let mv=l.find(m=>m.from==='{s}'&&m.to==='{e}');
            if(!mv)return'ILLEGAL';if('{p}'&&mv.promotionTypes)mv.promotionType='{p}';
            try{{g.move(Object.assign({{}},mv,{{animate:true,userGenerated:true}}));return'OK';}}
            catch(err){{return err.toString();}}
            """)
            if r == 'OK':
                print(f"♟️ {s}{e}"); return True
            return False

        elif self.config['platform'] == "Lichess.org":
            r = self.driver.execute_script(f"""
            function sq(n,rect,fl){{const f={{'a':0,'b':1,'c':2,'d':3,'e':4,'f':5,'g':6,'h':7}};
            let x=f[n[0]],y=8-parseInt(n[1]);if(fl){{x=7-x;y=7-y;}}
            const sw=rect.width/8,sh=rect.height/8;
            return{{x:rect.left+window.scrollX+x*sw+sw/2,y:rect.top+window.scrollY+y*sh+sh/2}};}}
            const cg=document.querySelector('cg-board');if(!cg)return'NO_BOARD';
            const rect=cg.getBoundingClientRect();
            const fl=document.querySelector('.cg-wrap').classList.contains('orientation-black');
            const p1=sq('{s}',rect,fl),p2=sq('{e}',rect,fl);
            const o={{bubbles:true,cancelable:true}};
            cg.dispatchEvent(new MouseEvent('mousedown',Object.assign(o,{{clientX:p1.x,clientY:p1.y}})));
            cg.dispatchEvent(new MouseEvent('mouseup',Object.assign(o,{{clientX:p2.x,clientY:p2.y}})));
            cg.dispatchEvent(new MouseEvent('click',Object.assign(o,{{clientX:p2.x,clientY:p2.y}})));
            return'OK';""")
            if r == 'OK':
                print(f"♟️ [Lichess] {s}{e}"); return True
            return False
        return False

    # ─────────────────────────────────────────────────────────────────────
    # AUTO-RESIGN / DRAW
    # ─────────────────────────────────────────────────────────────────────
    def _check_auto_resign(self, cp):
        if not self.gui.var_auto_resign.get() or cp is None:
            return False
        thr = self.gui.scale_resign_threshold.get()
        if cp > -thr:
            return False
        action = self.gui.combo_resign_action.get()
        print(f"\n{'🏳️ AUTO-RESIGN' if action=='Resign' else '🤝 AUTO-DRAW'}: eval {cp/100:.2f}\n")
        if action == "Resign":
            try:
                self.js("const b=Array.from(document.querySelectorAll('button'));const r=b.find(x=>x.innerText.toLowerCase().includes('resign'));if(r)r.click();")
            except: pass
        else:
            try:
                self.js("const b=Array.from(document.querySelectorAll('button'));const d=b.find(x=>x.innerText.toLowerCase().includes('draw'));if(d)d.click();")
            except: pass
        return True

    # ─────────────────────────────────────────────────────────────────────
    # DRAW ARROW / CLEAR
    # ─────────────────────────────────────────────────────────────────────
    def draw_arrow(self, move):
        s, e = str(move)[:2], str(move)[2:4]
        self.js(f"""
        const board=document.querySelector('.board,chess-board')||document.querySelector('cg-board');
        if(!board)return;
        let ex=document.getElementById('bot-arrow-svg');if(ex)ex.remove();
        let fl=('{self.config['platform']}'==='Chess.com')
            ?(window.game&&window.game.getPlayingAs?window.game.getPlayingAs()===2:board.classList.contains('flipped'))
            :document.querySelector('.cg-wrap').classList.contains('orientation-black');
        const rect=board.getBoundingClientRect(),sqW=rect.width/8,sqH=rect.height/8;
        const files={{'a':0,'b':1,'c':2,'d':3,'e':4,'f':5,'g':6,'h':7}};
        function gc(sq){{let f=files[sq[0]],r=8-parseInt(sq[1]);if(fl){{f=7-f;r=7-r;}}
        return{{x:rect.left+window.scrollX+(f*sqW)+(sqW/2),y:rect.top+window.scrollY+(r*sqH)+(sqH/2)}};}}
        const p1=gc('{s}'),p2=gc('{e}');
        const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
        svg.id='bot-arrow-svg';svg.style.cssText='position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:999999;';
        const defs=document.createElementNS('http://www.w3.org/2000/svg','defs');
        const mk=document.createElementNS('http://www.w3.org/2000/svg','marker');
        mk.setAttribute('id','chess-arr');mk.setAttribute('markerWidth','5');mk.setAttribute('markerHeight','5');
        mk.setAttribute('refX','3');mk.setAttribute('refY','2.5');mk.setAttribute('orient','auto');
        const poly=document.createElementNS('http://www.w3.org/2000/svg','polygon');
        poly.setAttribute('points','0 0,5 2.5,0 5');poly.setAttribute('fill','#00ff66');
        mk.appendChild(poly);defs.appendChild(mk);svg.appendChild(defs);
        const line=document.createElementNS('http://www.w3.org/2000/svg','line');
        line.setAttribute('x1',p1.x);line.setAttribute('y1',p1.y);line.setAttribute('x2',p2.x);line.setAttribute('y2',p2.y);
        line.setAttribute('stroke','#00ff66');line.setAttribute('stroke-width','6');line.setAttribute('marker-end','url(#chess-arr)');
        svg.appendChild(line);document.body.appendChild(svg);
        """)

    def clear_arrow(self):
        try: self.driver.execute_script("let a=document.getElementById('bot-arrow-svg');if(a)a.remove();")
        except: pass

    # ─────────────────────────────────────────────────────────────────────
    # EVAL + ACCURACY
    # ─────────────────────────────────────────────────────────────────────
    def analyze_eval(self, info_list, side, move):
        score = info_list[0].get("score")
        if not score: return "N/A", None
        pov    = score.pov(chess.WHITE if side == 'w' else chess.BLACK)
        cur_cp = pov.score(mate_score=10000)
        is_mate = pov.is_mate()
        ev = f"M{pov.mate()}" if is_mate else f"{pov.score()/100:+.2f}"
        if self.last_eval_cp is not None:
            diff = cur_cp - self.last_eval_cp
            if diff > 250: print("\n🚨 LAWAN BLUNDER!\n")
            tac = self.board.is_capture(move) or self.board.is_check()
            if (is_mate and self.last_eval_cp < 5000) or (cur_cp > 400 and diff > 100 and tac):
                print(f"\n💎 BRILLIANT: {move} ({ev})\n")
        self.last_eval_cp = cur_cp
        return ev, cur_cp

    def _record_accuracy(self, played_cp, best_cp):
        if played_cp is None or best_cp is None: return
        self.accuracy_diffs.append(abs(best_cp - played_cp))

    def _calc_accuracy(self):
        if not self.accuracy_diffs: return 100.0
        return round(max(0.0, 100.0 - sum(self.accuracy_diffs)/len(self.accuracy_diffs)/3.0), 1)

    # ─────────────────────────────────────────────────────────────────────
    # PGN
    # ─────────────────────────────────────────────────────────────────────
    def _init_pgn(self, side):
        self.pgn_game = chess.pgn.Game()
        self.pgn_node = self.pgn_game
        now = datetime.now()
        self.pgn_game.headers.update({
            'Event':  f"ChessBot Game #{self.game_number}",
            'Date':   now.strftime("%Y.%m.%d"),
            'White':  "Bot" if side=='w' else "Opponent",
            'Black':  "Bot" if side=='b' else "Opponent",
            'Result': '*',
            'Opening': self.current_opening,
        })

    def _pgn_add(self, move):
        try:
            if self.pgn_node:
                self.pgn_node = self.pgn_node.add_main_variation(move)
        except: pass

    def _save_pgn(self):
        if not self.pgn_game: return
        fn = os.path.join(PGN_DIR, f"game_{self.game_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pgn")
        try:
            with open(fn, "w") as f:
                print(self.pgn_game, file=f, end="\n\n")
            print(f"[PGN] 💾 {fn}")
        except Exception as e:
            print(f"[PGN] ⚠️ {e}")

    # ─────────────────────────────────────────────────────────────────────
    # BOOK MOVE
    # ─────────────────────────────────────────────────────────────────────
    def play_book_move(self):
        bp = self.config.get('book_path','')
        if not bp: return None
        try:
            with chess.polyglot.open_reader(bp) as r:
                e = r.choice(self.board)
                print(f"📖 {e.move}"); return e.move
        except: return None

    # ─────────────────────────────────────────────────────────────────────
    # BEEP
    # ─────────────────────────────────────────────────────────────────────
    def _beep(self):
        if not self.gui.var_beep.get(): return
        def _b():
            try:
                import winsound; winsound.Beep(880, 150)
            except: pass
        threading.Thread(target=_b, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────
    # MOVE LOG
    # ─────────────────────────────────────────────────────────────────────
    def _log_move(self, move, ev, is_book=False):
        n = self.board.fullmove_number
        s = "Putih" if self.board.turn == chess.WHITE else "Hitam"
        self.move_history.append(f"{'📖' if is_book else '🤖'} #{n}({s}): {move} [{ev}]")

    def _print_summary(self, result):
        acc = self._calc_accuracy()
        print(f"\n{'='*50}")
        print(f"📋 Game #{self.game_number} | {len(self.move_history)} langkah | Akurasi: {acc}% | Opening: {self.current_opening}")
        print(f"{'='*50}")
        for m in self.move_history[-10:]: print(f"  {m}")
        print(f"{'='*50}\n")
        self.gui.update_accuracy_label(acc)
        self.gui.add_graph_point(result)

    # ─────────────────────────────────────────────────────────────────────
    # SCREENSHOT / RECONNECT
    # ─────────────────────────────────────────────────────────────────────
    def _screenshot(self, ctx="error"):
        try:
            fn = os.path.join(SS_DIR, f"{ctx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.driver.save_screenshot(fn)
            print(f"[SS] 📸 {fn}")
        except: pass

    def _reconnect(self):
        print("\n[RECONNECT] 🔄 Reload...\n")
        self.gui.set_status("🔄 Reconnecting...")
        try:
            self.driver.refresh(); time.sleep(4)
            for _ in range(30):
                if self.get_fen():
                    print("[RECONNECT] ✅ Berhasil")
                    self.gui.set_status("✅ Reconnect OK")
                    self.last_fen = ""; return True
                time.sleep(1)
        except: pass
        return False

    # ─────────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────────────────
    def run(self):
        errs = 0
        # [FITUR 4] Rotasi akun setiap N game
        rotate_every = 10

        while self.is_running:
            self._check_scheduler()
            if self.is_paused:
                time.sleep(0.5); continue

            try:
                self.update_live_settings()

                # GAME OVER
                if self.check_game_over():
                    if self.last_fen != "GAMEOVER":
                        print("\n🏆 GAME SELESAI 🏆")
                        result = self.check_result()
                        self._print_summary(result)
                        self._save_pgn()
                        self._save_move_time_csv()
                        self._update_opening_stat(self.current_opening, result)
                        self._send_notification(result, f"{self.last_eval_cp/100:+.2f}" if self.last_eval_cp else "N/A", len(self.move_history))
                        self.last_fen       = "GAMEOVER"
                        self.last_eval_cp   = 0
                        self.is_new_match   = True
                        self.move_history   = []
                        self.accuracy_diffs = []
                        self._move_time_rows = []
                        self.gui.set_status("🏁 Game Selesai")

                        # Rotasi akun jika perlu
                        if self.gui.var_multiaccout.get() and self.game_number % rotate_every == 0:
                            self._rotate_account()

                    self.handle_next_game()
                    time.sleep(1); errs = 0; continue

                cur_fen = self.get_fen()
                if not cur_fen or cur_fen == self.last_fen:
                    time.sleep(0.5); continue

                errs = 0
                self.current_fen = cur_fen
                self.gui.update_fen_display(cur_fen)

                # Deteksi opening
                if self.board.fullmove_number <= 15:
                    detected = self._detect_opening(cur_fen)
                    if detected != self.current_opening:
                        self.current_opening = detected
                        print(f"[OPENING] 📚 {detected}")
                        self.gui.set_opening_label(detected)

                if self.is_new_match and cur_fen != "GAMEOVER":
                    self.game_number += 1
                    side = self.get_side()
                    self._my_side = side
                    self._init_pgn(side)
                    self.auto_adjust_match_elo()
                    self.is_new_match = False
                    self.current_opening = "Unknown"

                self.clear_arrow()
                turn = cur_fen.split()[1]
                side = self.get_side()

                if turn != side:
                    self.gui.set_status("👀 Menunggu Lawan")
                    # Pre-move: kalkulasi di background
                    self._start_premove_calc(cur_fen)
                    time.sleep(0.1); continue

                # ── GILIRAN KITA ─────────────────────────────────────────
                self.gui.set_status("🧠 Berpikir...")
                self._beep()
                self.board.set_fen(cur_fen)
                print(f"\n[GILIRAN] Kalkulasi... (Move #{self.board.fullmove_number})")

                best_move = None
                is_book   = False
                ev        = "N/A"
                best_cp   = None
                played_cp = None

                # 1. Coba pre-move
                best_move = self._use_premove(cur_fen)
                if best_move:
                    ev = "⚡pre"

                # 2. Buku pembukaan
                if not best_move:
                    best_move = self.play_book_move()
                    if best_move: is_book = True; ev = "📖"

                # 3. Tablebase endgame
                if not best_move:
                    best_move = self._tablebase_move()
                    if best_move: ev = "🔢TB"

                # 4. Engine
                if not best_move:
                    blunder = self.gui.scale_blunder.get()
                    mpv     = 2 if blunder > 0 else 1
                    infos   = self.engine.analyse(
                        self.board, chess.engine.Limit(time=self.gui.scale_time.get()), multipv=mpv)
                    best_move = infos[0].get("pv")[0]
                    ev, best_cp = self.analyze_eval(infos, side, best_move)
                    played_cp = best_cp

                    if blunder > 0 and len(infos) > 1 and not self.board.is_check():
                        if random.random() < blunder / 100.0:
                            alt = infos[1]
                            best_move = alt.get("pv")[0]
                            alt_s = alt.get("score")
                            if alt_s:
                                played_cp = alt_s.pov(
                                    chess.WHITE if side=='w' else chess.BLACK).score(mate_score=10000)
                            print(f"🤡 Humanizer suboptimal ({blunder}%)")

                    self._record_accuracy(played_cp, best_cp)
                    print(f"📊 Eval: {ev} | {best_move}")

                    if self._check_auto_resign(played_cp):
                        self.last_fen = cur_fen; continue

                self._log_move(best_move, ev, is_book)
                self._pgn_add(best_move)

                # ── Asisten / Auto ────────────────────────────────────────
                if self.gui.var_assistant.get():
                    print(f"💡 Assist: {best_move}")
                    self.draw_arrow(best_move)
                    self.last_fen = cur_fen
                    self.gui.set_status("💡 Asisten Aktif")
                else:
                    # Hitung delay
                    if self.gui.var_smart_humanizer.get():
                        mode = self.gui.combo_time_control.get()
                        mn, mx, mh = (
                            (0.1,0.4,1.0)   if "Bullet" in mode else
                            (0.5,2.0,3.0)   if "Blitz"  in mode else
                            (2.0,5.0,8.0)   if "Rapid"  in mode else
                            (5.0,15.0,20.0)
                        )
                        delay = random.uniform(mn, mx)
                        if self.board.fullmove_number <= 8:                  delay *= 0.5
                        elif best_move and self.board.is_capture(best_move): delay *= 1.5
                        elif self.board.is_check():                          delay *= 2.0
                        if random.random() < 0.10:
                            delay += random.uniform(mh/2, mh)
                    else:
                        lo = self.gui.scale_min_delay.get() if hasattr(self.gui,'scale_min_delay') else 0.5
                        hi = self.gui.scale_max_delay.get() if hasattr(self.gui,'scale_max_delay') else 2.0
                        delay = random.uniform(lo, max(lo, hi))

                    # [FITUR 2] Time management adaptif
                    delay = self._time_management_delay(delay)

                    self.gui.set_status(f"⏳ {delay:.1f}s...")
                    print(f"⏳ Eksekusi dalam {delay:.1f}s...")
                    self._record_move_time(self.board.fullmove_number,
                                          "w" if self.board.turn==chess.WHITE else "b",
                                          best_move, delay, ev)
                    time.sleep(delay)

                    if self.execute_move(best_move):
                        self.last_fen = cur_fen
                        self.gui.set_status("✅ Langkah Dimainkan")

            except Exception as ex:
                errs += 1
                print(f"[ERROR] {ex}")
                if errs >= 3:
                    self._screenshot("loop_error"); errs = 0
                    if self.gui.var_auto_reconnect.get():
                        if not self._reconnect():
                            print("[SISTEM] Reconnect gagal. Bot berhenti.")
                            self.stop()

            time.sleep(0.1)

    # ─────────────────────────────────────────────────────────────────────
    # STOP / EMERGENCY
    # ─────────────────────────────────────────────────────────────────────
    def stop(self):
        self.is_running = False
        try: keyboard.unhook_all()
        except: pass
        try: self.engine.quit(); self.driver.quit()
        except: pass

    def emergency_stop(self):
        print("\n🚨 EMERGENCY STOP\n")
        self._screenshot("emergency"); self.stop()


# ══════════════════════════════════════════════════════════════════════════
# GUI — v16.0
# ══════════════════════════════════════════════════════════════════════════
class ChessBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("✦ ChessBot Studio v16.0 ✦")
        self.geometry("860x700")
        self.minsize(700, 540)
        self.resizable(True, True)
        self.configure(fg_color="#18181b")

        self.bot_thread   = None
        self.bot_instance = None
        self.log_window   = None
        self.log_textbox  = None
        self.stats        = {"WIN":0,"LOSS":0,"DRAW":0}
        self._graph_data  = []
        self._tray_icon   = None
        self._is_hidden   = False

        self.create_widgets()
        self.load_config()
        self._setup_tray()

    # ── Helpers ──────────────────────────────────────────────────────────
    def set_status(self, t):
        try: self.lbl_status.configure(text=t)
        except: pass

    def update_fen_display(self, fen):
        try:
            self.entry_fen.configure(state="normal")
            self.entry_fen.delete(0,"end"); self.entry_fen.insert(0, fen)
            self.entry_fen.configure(state="readonly")
        except: pass

    def update_scoreboard(self, r):
        self.stats[r] += 1
        self.lbl_score.configure(
            text=f"🏆 {self.stats['WIN']}  |  ❌ {self.stats['LOSS']}  |  🤝 {self.stats['DRAW']}")

    def update_accuracy_label(self, acc):
        try: self.lbl_accuracy.configure(text=f"🎯 Akurasi: {acc}%")
        except: pass

    def set_opening_label(self, name):
        try: self.lbl_opening.configure(text=f"📚 {name}")
        except: pass

    def add_graph_point(self, result):
        self._graph_data.append(result)
        self._refresh_graph()

    def _refresh_graph(self):
        if not MATPLOTLIB_OK or not hasattr(self, '_graph_ax'): return
        try:
            ax = self._graph_ax; ax.clear()
            wr = []
            wins = 0
            for i, r in enumerate(self._graph_data):
                if r == 'WIN': wins += 1
                wr.append(wins / (i+1) * 100)
            ax.plot(range(1, len(wr)+1), wr, color='#10b981', lw=1.5)
            ax.set_facecolor('#0f172a')
            ax.tick_params(colors='#94a3b8', labelsize=7)
            ax.set_ylabel('%', color='#94a3b8', fontsize=8)
            ax.set_ylim(0, 100)
            self._graph_canvas.draw()
        except: pass

    def update_opening_table(self, stats):
        """Update tabel opening stats di tab Analytics."""
        try:
            self.opening_text.configure(state="normal")
            self.opening_text.delete("1.0","end")
            self.opening_text.insert("end", f"{'Opening':<32} W   L   D\n")
            self.opening_text.insert("end", "─"*48 + "\n")
            for name, s in sorted(stats.items(), key=lambda x: -(x[1]['W'])):
                self.opening_text.insert("end", f"{name[:31]:<32} {s['W']:<4}{s['L']:<4}{s['D']}\n")
            self.opening_text.configure(state="disabled")
        except: pass

    def get_accounts(self):
        """Kembalikan list cookie dari textarea multi-akun."""
        try:
            raw = self.txt_accounts.get("1.0","end").strip()
            return [c.strip() for c in raw.split("\n") if c.strip()]
        except: return []

    # ── [FITUR 9] DARK/LIGHT THEME TOGGLE ────────────────────────────────
    def toggle_theme(self):
        cur = ctk.get_appearance_mode()
        new = "Light" if cur == "Dark" else "Dark"
        ctk.set_appearance_mode(new)
        self.btn_theme.configure(text="☀️ Light Mode" if new == "Dark" else "🌙 Dark Mode")

    # ── [FITUR 10] MINIMIZE TO TRAY ──────────────────────────────────────
    def _setup_tray(self):
        if not TRAY_OK: return
        try:
            img = Image.new('RGB', (64,64), color=(30,30,35))
            d   = ImageDraw.Draw(img)
            d.text((8, 16), "♟️", fill=(56, 189, 248))
            menu = pystray.Menu(
                pystray.MenuItem("Tampilkan",  self._show_window),
                pystray.MenuItem("Pause/Resume", lambda: self.bot_instance.toggle_pause() if self.bot_instance else None),
                pystray.MenuItem("Stop Bot",   self.emergency_stop),
                pystray.MenuItem("Keluar",     self._quit_app),
            )
            self._tray_icon = pystray.Icon("ChessBot", img, "ChessBot Studio v16.0", menu)
            threading.Thread(target=self._tray_icon.run, daemon=True).start()
        except: pass

    def _hide_to_tray(self):
        if not TRAY_OK or not self._tray_icon: return
        self._is_hidden = True
        self.withdraw()

    def _show_window(self, *_):
        self._is_hidden = False
        self.deiconify()
        self.lift()

    def _quit_app(self, *_):
        self.save_config()
        if self.bot_instance: self.bot_instance.stop()
        if self._tray_icon:
            try: self._tray_icon.stop()
            except: pass
        self.destroy()

    # ── WIDGETS ──────────────────────────────────────────────────────────
    def create_widgets(self):
        # HEADER
        hf = ctk.CTkFrame(self, fg_color="#1f2023", corner_radius=8, border_width=1, border_color="#333")
        hf.pack(fill="x", padx=10, pady=(8,4))
        ctk.CTkLabel(hf, text="⚡ ChessBot Studio v16.0",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color="#38bdf8").pack(side="left", padx=12, pady=6)
        btn_bar = ctk.CTkFrame(hf, fg_color="transparent")
        btn_bar.pack(side="right", padx=8)
        self.btn_theme = ctk.CTkButton(btn_bar, text="☀️ Light", width=80, height=24,
            fg_color="#27272a", hover_color="#3f3f46", command=self.toggle_theme)
        self.btn_theme.pack(side="left", padx=3)
        if TRAY_OK:
            ctk.CTkButton(btn_bar, text="📥 Tray", width=70, height=24,
                fg_color="#27272a", hover_color="#3f3f46",
                command=self._hide_to_tray).pack(side="left", padx=3)

        # SCOREBOARD
        sf = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=6, border_width=1, border_color="#1e293b")
        sf.pack(fill="x", padx=10, pady=(0,2))
        self.lbl_score = ctk.CTkLabel(sf, text="🏆 0  |  ❌ 0  |  🤝 0",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc")
        self.lbl_score.pack(side="left", pady=5, padx=10)
        self.lbl_accuracy = ctk.CTkLabel(sf, text="🎯 Akurasi: —",
            font=ctk.CTkFont(size=10), text_color="#34d399")
        self.lbl_accuracy.pack(side="left", padx=8)
        self.lbl_opening = ctk.CTkLabel(sf, text="📚 —",
            font=ctk.CTkFont(size=10), text_color="#a78bfa")
        self.lbl_opening.pack(side="left", padx=8)

        # STATUS
        stf = ctk.CTkFrame(self, fg_color="#0c0c0f", corner_radius=6, border_width=1, border_color="#27272a")
        stf.pack(fill="x", padx=10, pady=(0,4))
        self.lbl_status = ctk.CTkLabel(stf, text="⚪ Idle",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#a1a1aa")
        self.lbl_status.pack(pady=3)

        # TABVIEW
        self.tabs = ctk.CTkTabview(self, fg_color="#18181b",
                                   segmented_button_fg_color="#1f2023",
                                   segmented_button_selected_color="#10b981",
                                   segmented_button_selected_hover_color="#059669")
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0,2))
        for tab in ("⚙️ Konfigurasi", "🎛️ Performa", "🔬 Advanced", "📊 Analytics", "📡 Notifikasi"):
            self.tabs.add(tab)

        self._build_tab_config(self.tabs.tab("⚙️ Konfigurasi"))
        self._build_tab_perf(self.tabs.tab("🎛️ Performa"))
        self._build_tab_advanced(self.tabs.tab("🔬 Advanced"))
        self._build_tab_analytics(self.tabs.tab("📊 Analytics"))
        self._build_tab_notif(self.tabs.tab("📡 Notifikasi"))

        # BOTTOM BAR
        bc = ctk.CTkFrame(self, fg_color="#1f2023", corner_radius=8, border_width=1, border_color="#333")
        bc.pack(fill="x", padx=10, pady=(0,8))
        sw = ctk.CTkFrame(bc, fg_color="transparent")
        sw.pack(fill="x", padx=12, pady=(6,2))
        self.var_assistant = tk.BooleanVar(value=False)
        ctk.CTkSwitch(sw, text="👁️ Mode Asisten", variable=self.var_assistant).pack(side="left")
        self.var_nextgame = tk.BooleanVar(value=True)
        ctk.CTkSwitch(sw, text="🔁 Auto Next", variable=self.var_nextgame).pack(side="right")
        br = ctk.CTkFrame(bc, fg_color="transparent")
        br.pack(fill="x", padx=12, pady=(2,8))
        br.columnconfigure(0, weight=3); br.columnconfigure(1, weight=1)
        self.btn_start = ctk.CTkButton(br, text="▶ MULAI SISTEM",
            font=ctk.CTkFont(size=13, weight="bold"), height=36,
            fg_color="#10b981", hover_color="#059669", command=self.toggle_bot)
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0,5))
        ctk.CTkButton(br, text="🚨 STOP",
            font=ctk.CTkFont(size=12, weight="bold"), height=36,
            fg_color="#7f1d1d", hover_color="#991b1b",
            command=self.emergency_stop).grid(row=0, column=1, sticky="ew")

    # ── TAB: KONFIGURASI ─────────────────────────────────────────────────
    def _build_tab_config(self, tab):
        tab.columnconfigure((0,1), weight=1)
        tab.rowconfigure(0, weight=1)

        # Kiri — scrollable
        lc = ctk.CTkScrollableFrame(tab, fg_color="#1f2023", corner_radius=8,
                                    scrollbar_button_color="#3f3f46")
        lc.grid(row=0, column=0, padx=(4,2), pady=4, sticky="nsew")

        ctk.CTkLabel(lc, text="📁 File & Akun",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(8,4))
        self._file_input(lc, "Stockfish Engine (.exe)", self.browse_stockfish, "entry_stockfish")
        self._file_input(lc, "Opening Book (.bin)", self.browse_book, "entry_book")
        self._file_input(lc, "Syzygy Tablebase (folder)", self.browse_tablebase, "entry_tablebase", is_dir=True)

        ctk.CTkLabel(lc, text="🌐 Platform & Warna:",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w", padx=10, pady=(4,0))
        pf = ctk.CTkFrame(lc, fg_color="transparent")
        pf.pack(fill="x", padx=10, pady=(2,4))
        pf.columnconfigure((0,1), weight=1)
        self.combo_platform = ctk.CTkOptionMenu(pf, height=26,
                                                values=["Chess.com","Lichess.org"], fg_color="#27272a")
        self.combo_platform.grid(row=0, column=0, sticky="ew", padx=(0,3))
        self.combo_color = ctk.CTkOptionMenu(pf, height=26,
                                             values=["Otomatis","Putih","Hitam"], fg_color="#27272a")
        self.combo_color.grid(row=0, column=1, sticky="ew")

        # FEN Display
        ctk.CTkLabel(lc, text="📌 FEN posisi saat ini:",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w", padx=10, pady=(4,0))
        fb = ctk.CTkFrame(lc, fg_color="transparent")
        fb.pack(fill="x", padx=10, pady=(2,4))
        self.entry_fen = ctk.CTkEntry(fb, height=26, fg_color="#0f172a", border_color="#1e3a5f",
                                      text_color="#67e8f9", font=ctk.CTkFont(size=9))
        self.entry_fen.insert(0, "Belum ada posisi...")
        self.entry_fen.configure(state="readonly")
        self.entry_fen.pack(side="left", fill="x", expand=True, padx=(0,3))
        ctk.CTkButton(fb, text="📋", width=28, height=26,
                      fg_color="#1e3a5f", hover_color="#164e63",
                      command=self.copy_fen).pack(side="right")

        # Scheduler
        schf = ctk.CTkFrame(lc, fg_color="#111827", corner_radius=6,
                            border_width=1, border_color="#1d4ed8")
        schf.pack(fill="x", padx=10, pady=(4,6))
        self.var_scheduler = tk.BooleanVar(value=False)
        ctk.CTkSwitch(schf, text="⏰ Session Scheduler",
                      variable=self.var_scheduler,
                      progress_color="#3b82f6").pack(anchor="w", padx=8, pady=(6,2))
        sr = ctk.CTkFrame(schf, fg_color="transparent")
        sr.pack(fill="x", padx=8, pady=(0,6))
        ctk.CTkLabel(sr, text="Stop pukul:",
                     font=ctk.CTkFont(size=10), text_color="#93c5fd").pack(side="left")
        self.entry_sched_stop = ctk.CTkEntry(sr, width=56, height=24,
                                             placeholder_text="22:00",
                                             fg_color="#0f172a", border_color="#1d4ed8")
        self.entry_sched_stop.pack(side="left", padx=6)

        # Kanan — multi-akun scrollable
        rc = ctk.CTkScrollableFrame(tab, fg_color="#1f2023", corner_radius=8,
                                    scrollbar_button_color="#3f3f46")
        rc.grid(row=0, column=1, padx=(2,4), pady=4, sticky="nsew")

        ctk.CTkLabel(rc, text="👥 Multi-Akun",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(8,4))
        ctk.CTkLabel(rc, text="Cookie PHPSESSID (satu per baris):",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w", padx=10)
        self.txt_accounts = ctk.CTkTextbox(rc, height=100, fg_color="#0f172a",
                                           text_color="#67e8f9",
                                           font=ctk.CTkFont("Consolas", 10))
        self.txt_accounts.pack(fill="x", padx=10, pady=(4,4))
        self.var_multiaccout = tk.BooleanVar(value=False)
        ctk.CTkSwitch(rc, text="🔄 Rotasi akun tiap 10 game",
                      variable=self.var_multiaccout,
                      progress_color="#f59e0b").pack(anchor="w", padx=10, pady=(0,6))

    # ── TAB: PERFORMA ────────────────────────────────────────────────────
    def _build_tab_perf(self, tab):
        f = ctk.CTkScrollableFrame(tab, fg_color="#1f2023", corner_radius=8,
                                   scrollbar_button_color="#3f3f46")
        f.pack(fill="both", expand=True, padx=4, pady=4)

        self.lbl_elo = ctk.CTkLabel(f, text="🎯 Target Elo: 2000",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#34d399")
        self.lbl_elo.pack(anchor="w", padx=10, pady=(8,0))
        self.scale_elo = ctk.CTkSlider(f, from_=200, to=3200, height=14,
            progress_color="#10b981",
            command=lambda v: self.lbl_elo.configure(text=f"🎯 Target Elo: {int(v)}"))
        self.scale_elo.set(2000)
        self.scale_elo.pack(fill="x", padx=10, pady=(2,8))

        self.lbl_blunder = ctk.CTkLabel(f, text="🤡 Blunder: 5%",
            font=ctk.CTkFont(size=10), text_color="#fca5a5")
        self.lbl_blunder.pack(anchor="w", padx=10)
        self.scale_blunder = ctk.CTkSlider(f, from_=0, to=30, height=14,
            button_color="#ef4444", progress_color="#b91c1c",
            command=lambda v: self.lbl_blunder.configure(text=f"🤡 Blunder: {int(v)}%"))
        self.scale_blunder.set(5)
        self.scale_blunder.pack(fill="x", padx=10, pady=(2,8))

        self.lbl_time = ctk.CTkLabel(f, text="⏱️ Waktu Pikir: 0.5s",
            font=ctk.CTkFont(size=10), text_color="#cbd5e1")
        self.lbl_time.pack(anchor="w", padx=10)
        self.scale_time = ctk.CTkSlider(f, from_=0.1, to=5.0, height=14,
            command=lambda v: self.lbl_time.configure(text=f"⏱️ Waktu Pikir: {v:.1f}s"))
        self.scale_time.set(0.5)
        self.scale_time.pack(fill="x", padx=10, pady=(2,8))

        # Smart Humanizer
        sh = ctk.CTkFrame(f, fg_color="#18181b", corner_radius=6,
                          border_width=1, border_color="#8b5cf6")
        sh.pack(fill="x", padx=10, pady=(0,6))
        self.var_smart_humanizer = tk.BooleanVar(value=True)
        ctk.CTkSwitch(sh, text="🧠 Smart Delay Humanizer",
                      variable=self.var_smart_humanizer,
                      progress_color="#8b5cf6").pack(anchor="w", padx=8, pady=(6,2))
        self.combo_time_control = ctk.CTkOptionMenu(sh, height=24, fg_color="#27272a",
            values=["Bullet (1-2 min)", "Blitz (3-5 min)", "Rapid (10-15 min)"])
        self.combo_time_control.set("Blitz (3-5 min)")
        self.combo_time_control.pack(fill="x", padx=8, pady=(0,6))

        # Switches grid 2x2
        sw = ctk.CTkFrame(f, fg_color="transparent")
        sw.pack(fill="x", padx=10, pady=(0,4))
        sw.columnconfigure((0,1), weight=1)
        self.var_beep = tk.BooleanVar(value=True)
        ctk.CTkSwitch(sw, text="🔔 Beep giliran", variable=self.var_beep,
                      progress_color="#fbbf24").grid(row=0, column=0, sticky="w", pady=2)
        self.var_anti_detection = tk.BooleanVar(value=True)
        ctk.CTkSwitch(sw, text="🕵️ Anti-Detection", variable=self.var_anti_detection,
                      progress_color="#a78bfa").grid(row=0, column=1, sticky="w", pady=2)
        self.var_auto_reconnect = tk.BooleanVar(value=True)
        ctk.CTkSwitch(sw, text="🔄 Auto-Reconnect", variable=self.var_auto_reconnect,
                      progress_color="#38bdf8").grid(row=1, column=0, sticky="w", pady=2)
        self.var_fingerprint = tk.BooleanVar(value=False)
        ctk.CTkSwitch(sw, text="🖥️ Fingerprint Rand.", variable=self.var_fingerprint,
                      progress_color="#f97316").grid(row=1, column=1, sticky="w", pady=2)

        # Pre-move
        pmf = ctk.CTkFrame(f, fg_color="#0f2a0f", corner_radius=6,
                           border_width=1, border_color="#166534")
        pmf.pack(fill="x", padx=10, pady=(4,8))
        self.var_premove = tk.BooleanVar(value=True)
        ctk.CTkSwitch(pmf, text="⚡ Pre-Move (background calc)",
                      variable=self.var_premove,
                      progress_color="#22c55e").pack(anchor="w", padx=8, pady=6)

    # ── TAB: ADVANCED ────────────────────────────────────────────────────
    def _build_tab_advanced(self, tab):
        f = ctk.CTkScrollableFrame(tab, fg_color="#1f2023", corner_radius=8,
                                   scrollbar_button_color="#3f3f46")
        f.pack(fill="both", expand=True, padx=4, pady=4)

        # Auto-Resign
        arf = ctk.CTkFrame(f, fg_color="#1a0a0a", corner_radius=6,
                           border_width=1, border_color="#7f1d1d")
        arf.pack(fill="x", padx=10, pady=(8,6))
        self.var_auto_resign = tk.BooleanVar(value=False)
        ctk.CTkSwitch(arf, text="🏳️ Auto-Resign / Draw",
                      variable=self.var_auto_resign,
                      progress_color="#ef4444").pack(anchor="w", padx=8, pady=(6,2))
        self.lbl_resign = ctk.CTkLabel(arf, text="Threshold: 500 cp",
            font=ctk.CTkFont(size=10), text_color="#fca5a5")
        self.lbl_resign.pack(anchor="w", padx=8)
        self.scale_resign_threshold = ctk.CTkSlider(arf, from_=100, to=1000, height=14,
            button_color="#ef4444", progress_color="#7f1d1d",
            command=lambda v: self.lbl_resign.configure(text=f"Threshold: {int(v)} cp"))
        self.scale_resign_threshold.set(500)
        self.scale_resign_threshold.pack(fill="x", padx=8, pady=(2,4))
        ar = ctk.CTkFrame(arf, fg_color="transparent")
        ar.pack(fill="x", padx=8, pady=(0,6))
        ctk.CTkLabel(ar, text="Aksi:", font=ctk.CTkFont(size=10),
                     text_color="#fca5a5").pack(side="left")
        self.combo_resign_action = ctk.CTkOptionMenu(ar, height=24, width=140,
            fg_color="#3f0000", values=["Resign","Tawarkan Draw"])
        self.combo_resign_action.pack(side="left", padx=6)

        # Time management info
        tmf = ctk.CTkFrame(f, fg_color="#0a1a0a", corner_radius=6,
                           border_width=1, border_color="#166534")
        tmf.pack(fill="x", padx=10, pady=(0,8))
        ctk.CTkLabel(tmf, text="⏰ Time Management Adaptif",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#22c55e").pack(anchor="w", padx=10, pady=(8,2))
        ctk.CTkLabel(tmf,
            text="< 10 detik → delay 0.1s\n< 30 detik → delay 0.3s\n< 60 detik → delay 0.8s",
            font=ctk.CTkFont(size=10), text_color="#86efac",
            justify="left").pack(anchor="w", padx=10, pady=(0,8))

    # ── TAB: ANALYTICS ───────────────────────────────────────────────────
    def _build_tab_analytics(self, tab):
        tab.columnconfigure((0,1), weight=1)
        tab.rowconfigure(0, weight=1)

        # Win rate graph
        gf = ctk.CTkFrame(tab, fg_color="#0f172a", corner_radius=8,
                          border_width=1, border_color="#1e3a5f")
        gf.grid(row=0, column=0, padx=(4,2), pady=4, sticky="nsew")
        ctk.CTkLabel(gf, text="📈 Win Rate",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#38bdf8").pack(anchor="w", padx=8, pady=(6,0))
        if MATPLOTLIB_OK:
            fig = Figure(figsize=(3, 2.2), dpi=80, facecolor='#0f172a')
            self._graph_ax = fig.add_subplot(111)
            self._graph_ax.set_facecolor('#0f172a')
            self._graph_ax.tick_params(colors='#94a3b8', labelsize=7)
            self._graph_canvas = backend_tkagg.FigureCanvasTkAgg(fig, master=gf)
            self._graph_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        else:
            ctk.CTkLabel(gf, text="pip install matplotlib",
                         font=ctk.CTkFont(size=10),
                         text_color="#f87171").pack(pady=20)

        # Opening table
        of = ctk.CTkFrame(tab, fg_color="#1f2023", corner_radius=8,
                          border_width=1, border_color="#333")
        of.grid(row=0, column=1, padx=(2,4), pady=4, sticky="nsew")
        ctk.CTkLabel(of, text="📚 Opening Stats",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=8, pady=(6,4))
        self.opening_text = ctk.CTkTextbox(of, fg_color="#0f172a", text_color="#a78bfa",
                                           font=ctk.CTkFont("Consolas", 9))
        self.opening_text.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.opening_text.insert("end", "Belum ada data opening.\n")
        self.opening_text.configure(state="disabled")

    # ── TAB: NOTIFIKASI ──────────────────────────────────────────────────
    def _build_tab_notif(self, tab):
        f = ctk.CTkScrollableFrame(tab, fg_color="#1f2023", corner_radius=8,
                                   scrollbar_button_color="#3f3f46")
        f.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(f, text="📡 Discord Webhook",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(8,4))
        ctk.CTkLabel(f, text="URL Webhook:",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w", padx=10)
        self.entry_discord = ctk.CTkEntry(f, height=30, fg_color="#0f172a",
                                          placeholder_text="https://discord.com/api/webhooks/...")
        self.entry_discord.pack(fill="x", padx=10, pady=(2,10))

        ctk.CTkLabel(f, text="📱 Telegram Bot",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=10, pady=(0,4))
        tg = ctk.CTkFrame(f, fg_color="transparent")
        tg.pack(fill="x", padx=10, pady=(2,4))
        tg.columnconfigure((0,1), weight=1)
        ctk.CTkLabel(tg, text="Bot Token:", font=ctk.CTkFont(size=10),
                     text_color="#94a3b8").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(tg, text="Chat ID:", font=ctk.CTkFont(size=10),
                     text_color="#94a3b8").grid(row=0, column=1, sticky="w")
        self.entry_tg_token = ctk.CTkEntry(tg, height=28, fg_color="#0f172a",
                                           placeholder_text="123456:ABC...")
        self.entry_tg_token.grid(row=1, column=0, sticky="ew", padx=(0,4))
        self.entry_tg_chat = ctk.CTkEntry(tg, height=28, fg_color="#0f172a",
                                          placeholder_text="-100...")
        self.entry_tg_chat.grid(row=1, column=1, sticky="ew")

        ctk.CTkLabel(f, text="💡 Terkirim otomatis setelah tiap game selesai.",
                     font=ctk.CTkFont(size=10), text_color="#6b7280").pack(anchor="w", padx=10, pady=(6,4))
        ctk.CTkButton(f, text="🧪 Test Notifikasi", height=28, width=150,
            fg_color="#1e3a5f", hover_color="#164e63",
            command=self._test_notif).pack(anchor="w", padx=10, pady=(0,8))

    def _test_notif(self):
        if self.bot_instance:
            self.bot_instance._send_notification("WIN","N/A",20)
        else:
            # Kirim test tanpa bot aktif
            class _FakeBot:
                def __init__(self, gui): self.gui=gui; self.game_number=0; self.current_opening="Test"; self.accuracy_diffs=[]
                def _calc_accuracy(self): return 100.0
            fb = _FakeBot(self)
            fb._send_notification = lambda *a,**k: None
            # Manual send
            threading.Thread(target=lambda: ChessBotEngine._send_notification(fb,"WIN","N/A",0), daemon=True).start()

    # ── FILE INPUT HELPER ─────────────────────────────────────────────────
    def _file_input(self, parent, label, cmd, attr, is_dir=False):
        ctk.CTkLabel(parent,text=label,font=ctk.CTkFont(size=10),text_color="#94a3b8").pack(anchor="w",padx=12)
        box = ctk.CTkFrame(parent,fg_color="transparent"); box.pack(fill="x",padx=12,pady=(1,6))
        entry = ctk.CTkEntry(box,height=28,fg_color="#141417",border_color="#3f3f46")
        entry.pack(side="left",fill="x",expand=True,padx=(0,4))
        ctk.CTkButton(box,text="📂" if not is_dir else "📁",width=32,height=28,fg_color="#3f3f46",
            command=lambda: self._handle_browse(entry, cmd, is_dir)).pack(side="right")
        setattr(self, attr, entry)

    def _handle_browse(self, entry, cmd, is_dir=False):
        res = cmd()
        if res: entry.delete(0,"end"); entry.insert(0,res)

    def browse_stockfish(self): return filedialog.askopenfilename(filetypes=[("EXE","*.exe")])
    def browse_book(self):      return filedialog.askopenfilename(filetypes=[("BIN","*.bin")])
    def browse_tablebase(self): return filedialog.askdirectory()

    def copy_fen(self):
        v = self.entry_fen.get()
        if v and v != "Belum ada posisi...":
            self.clipboard_clear(); self.clipboard_append(v)
            self.set_status("📋 FEN disalin!")

    def emergency_stop(self):
        if self.bot_instance: self.bot_instance.emergency_stop()
        self.btn_start.configure(text="▶ MULAI SISTEM",fg_color="#10b981",hover_color="#059669")
        self.set_status("🚨 Emergency Stop")

    # ── CONFIG SAVE/LOAD ─────────────────────────────────────────────────
    def save_config(self):
        d = {
            "stockfish_path":  self.entry_stockfish.get(),
            "book_path":       self.entry_book.get(),
            "tablebase_path":  self.entry_tablebase.get(),
            "platform":        self.combo_platform.get(),
            "target_elo":      self.scale_elo.get(),
            "blunder_chance":  self.scale_blunder.get(),
            "scheduler_stop":  self.entry_sched_stop.get(),
            "resign_threshold": self.scale_resign_threshold.get(),
            "discord_url":     self.entry_discord.get(),
            "tg_token":        self.entry_tg_token.get(),
            "tg_chat":         self.entry_tg_chat.get(),
            "accounts":        self.txt_accounts.get("1.0","end").strip(),
        }
        try:
            with open(CONFIG_FILE,"w") as f: json.dump(d,f,indent=2)
        except: pass

    def load_config(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE) as f: d=json.load(f)
            def _s(key, entry, default=""): entry.delete(0,"end"); entry.insert(0, d.get(key,default))
            _s("stockfish_path", self.entry_stockfish)
            _s("book_path",      self.entry_book)
            _s("tablebase_path", self.entry_tablebase)
            _s("scheduler_stop", self.entry_sched_stop)
            _s("discord_url",    self.entry_discord)
            _s("tg_token",       self.entry_tg_token)
            _s("tg_chat",        self.entry_tg_chat)
            if "platform"    in d: self.combo_platform.set(d["platform"])
            if "target_elo"  in d:
                self.scale_elo.set(d["target_elo"])
                self.lbl_elo.configure(text=f"🎯 Target Elo: {int(d['target_elo'])}")
            if "blunder_chance" in d:
                self.scale_blunder.set(d["blunder_chance"])
                self.lbl_blunder.configure(text=f"🤡 Blunder: {int(d['blunder_chance'])}%")
            if "resign_threshold" in d:
                self.scale_resign_threshold.set(d["resign_threshold"])
                self.lbl_resign.configure(text=f"Threshold: {int(d['resign_threshold'])} cp")
            if "accounts" in d:
                self.txt_accounts.delete("1.0","end")
                self.txt_accounts.insert("1.0", d["accounts"])
        except: pass

    def get_config(self):
        return {
            "stockfish_path": self.entry_stockfish.get(),
            "book_path":      self.entry_book.get(),
            "platform":       self.combo_platform.get(),
            "warna_manual":   {"Otomatis":"auto","Putih":"w","Hitam":"b"}[self.combo_color.get()],
            "target_elo":     int(self.scale_elo.get()),
        }

    # ── BOT TOGGLE ───────────────────────────────────────────────────────
    def toggle_bot(self):
        self.save_config()
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_instance.stop()
            self.btn_start.configure(text="▶ MULAI SISTEM",fg_color="#10b981",hover_color="#059669")
            self.set_status("⚪ Idle")
        else:
            if not self.log_window or not self.log_window.winfo_exists():
                self.log_window = ctk.CTkToplevel(self)
                self.log_window.title("📟 Terminal Log")
                self.log_window.geometry("680x480")
                tb = ctk.CTkFrame(self.log_window,fg_color="#111")
                tb.pack(fill="x",padx=8,pady=(8,0))
                ctk.CTkButton(tb,text="🗑️ Clear",width=90,height=24,fg_color="#3f3f46",
                    command=self._clear_log).pack(side="left",padx=4)
                ctk.CTkButton(tb,text="📋 Copy",width=90,height=24,fg_color="#1e3a5f",
                    command=self._copy_log).pack(side="left",padx=4)
                txt = ctk.CTkTextbox(self.log_window,fg_color="#000",
                    text_color="#34d399",font=ctk.CTkFont("Consolas",12))
                txt.pack(fill="both",expand=True,padx=8,pady=8)
                self.log_textbox = txt
                sys.stdout = PrintLogger(txt)

            self.btn_start.configure(text="⏹ HENTIKAN",fg_color="#e11d48",hover_color="#be123c")
            self.set_status("▶️ Berjalan...")
            self.bot_instance = ChessBotEngine(self.get_config(), self)
            self.bot_thread   = threading.Thread(target=self.bot_instance.run, daemon=True)
            self.bot_thread.start()

    def _clear_log(self):
        try:
            if self.log_textbox and self.log_textbox.winfo_exists():
                self.log_textbox.delete("1.0","end")
        except: pass

    def _copy_log(self):
        try:
            if self.log_textbox and self.log_textbox.winfo_exists():
                self.clipboard_clear()
                self.clipboard_append(self.log_textbox.get("1.0","end"))
                self.set_status("📋 Log disalin!")
        except: pass

    def on_close(self):
        if TRAY_OK and self._tray_icon:
            self._hide_to_tray()   # Minimize ke tray, tidak langsung tutup
        else:
            self.save_config()
            if self.bot_instance: self.bot_instance.stop()
            self.destroy()


# ══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = ChessBotGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
