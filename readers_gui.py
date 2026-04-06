#!/usr/bin/env python3
"""
Readers GUI Launcher
Simple graphical interface for non-technical authors.
No command line needed — just click and run.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import sys
import os
import threading
import webbrowser
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# shadcn-inspired minimal color palette (light mode)
BG = "#fafafa"
CARD = "#ffffff"
BORDER = "#e4e4e7"
FG = "#09090b"
MUTED = "#71717a"
MUTED_BG = "#f4f4f5"
ACCENT = "#09090b"
ACCENT_FG = "#ffffff"
BLUE = "#2563eb"
GREEN = "#16a34a"
ORANGE = "#f97316"
RED = "#dc2626"

# Font family — Inter isn't available in Tk, use system sans
FONT = "Helvetica"
MONO = "Menlo"


class ReadersGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Readers")
        self.root.configure(bg=BG)
        self.root.geometry("640x860")
        self.root.resizable(True, True)

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.book_file = tk.StringVar()
        self.provider = tk.StringVar(value="gemini")
        self.readers = tk.IntVar(value=1000)
        self.rounds = tk.IntVar(value=3)
        self.genre = tk.StringVar(value="general")
        self.workers = tk.IntVar(value=5)
        self.running = False

        self._check_dependencies()
        self._check_env_file()
        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=MUTED_BG, background=FG,
                         bordercolor=BORDER, lightcolor=FG, darkcolor=FG)
        style.configure("TCombobox", fieldbackground=CARD, background=CARD,
                         foreground=FG, bordercolor=BORDER, arrowcolor=MUTED)
        style.configure("TScrollbar", troughcolor=MUTED_BG, background=BORDER,
                         bordercolor=BG, arrowcolor=MUTED)

    def _check_dependencies(self):
        self.missing_deps = []
        for pkg, import_name in [("rich", "rich"), ("python-dotenv", "dotenv"),
                                  ("google-genai", "google.genai"), ("openai", "openai"),
                                  ("anthropic", "anthropic")]:
            try:
                __import__(import_name)
            except ImportError:
                self.missing_deps.append(pkg)

    def _check_env_file(self):
        env_path = SCRIPT_DIR / ".env"
        if not env_path.exists():
            self.env_status = "no_file"
        else:
            content = env_path.read_text()
            has_key = False
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    if val.strip() and not val.strip().startswith("#"):
                        has_key = True
                        break
            self.env_status = "has_keys" if has_key else "no_keys"

    def _build_ui(self):
        canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.main_frame = tk.Frame(canvas, bg=BG)
        self.main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=24, pady=16)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        f = self.main_frame

        # === HEADER ===
        tk.Label(f, text="Readers", font=(FONT, 28, "bold"),
                 fg=FG, bg=BG).pack(anchor="w", pady=(8, 0))
        tk.Label(f, text="Up to 500,000 AI readers judge your book.",
                 font=(FONT, 11), fg=MUTED, bg=BG).pack(anchor="w", pady=(0, 16))

        # Separator
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", pady=(0, 16))

        # === DEPENDENCY WARNING ===
        if self.missing_deps:
            warn_frame = tk.Frame(f, bg=CARD, highlightbackground=ORANGE,
                                  highlightthickness=1)
            warn_frame.pack(fill="x", pady=(0, 12))
            tk.Label(warn_frame, text="Missing packages detected.",
                     font=(FONT, 10, "bold"), fg=ORANGE, bg=CARD).pack(padx=12, pady=(10, 2), anchor="w")
            tk.Label(warn_frame, text="Click below to install required dependencies.",
                     font=(FONT, 9), fg=MUTED, bg=CARD).pack(padx=12, anchor="w")
            tk.Button(warn_frame, text="Install Dependencies", font=(FONT, 10),
                      bg=ORANGE, fg="white", relief="flat", cursor="hand2", bd=0,
                      activebackground="#ea580c", activeforeground="white",
                      command=self._install_deps).pack(padx=12, pady=(6, 10), anchor="w")

        # === API KEY STATUS ===
        if self.env_status != "has_keys":
            key_frame = tk.Frame(f, bg=CARD, highlightbackground=BORDER,
                                 highlightthickness=1)
            key_frame.pack(fill="x", pady=(0, 12))
            if self.env_status == "no_file":
                msg = "No .env file found. Copy .env.example to .env and add your API key.\nOllama works without a key."
            else:
                msg = "Your .env file has no active API keys. Uncomment and fill in at least one."
            tk.Label(key_frame, text=msg, font=(FONT, 9),
                     fg=MUTED, bg=CARD, wraplength=560, justify="left").pack(padx=12, pady=10)

        # === BOOK FILE ===
        self._section_label(f, "Book File")
        file_frame = tk.Frame(f, bg=BG)
        file_frame.pack(fill="x", pady=(0, 4))
        file_entry = tk.Entry(file_frame, textvariable=self.book_file, font=(FONT, 10),
                 bg=CARD, fg=FG, insertbackground=FG, relief="flat",
                 highlightbackground=BORDER, highlightthickness=1)
        file_entry.pack(side="left", fill="x", expand=True, ipady=7)
        tk.Button(file_frame, text="Browse", font=(FONT, 10),
                  bg=MUTED_BG, fg=FG, relief="flat", cursor="hand2", bd=0,
                  activebackground=BORDER,
                  command=self._browse_file).pack(side="right", padx=(8, 0), ipady=5, ipadx=12)
        tk.Label(f, text="200-500 word description works best. Full manuscripts will be auto-summarized.",
                 font=(FONT, 8), fg=MUTED, bg=BG).pack(anchor="w", pady=(2, 10))

        # === PROVIDER ===
        self._section_label(f, "Provider")
        prov_frame = tk.Frame(f, bg=BG)
        prov_frame.pack(fill="x", pady=(0, 10))
        providers = [
            ("Gemini  (recommended)", "gemini"),
            ("OpenAI  (GPT-4o-mini)", "openai"),
            ("Anthropic  (Claude)", "anthropic"),
            ("Ollama  (free, local)", "ollama"),
        ]
        for label, value in providers:
            tk.Radiobutton(prov_frame, text=label, variable=self.provider, value=value,
                           font=(FONT, 10), fg=FG, bg=BG, selectcolor=CARD,
                           activebackground=BG, activeforeground=BLUE,
                           highlightthickness=0).pack(anchor="w")

        # === GENRE ===
        self._section_label(f, "Genre")
        genre_frame = tk.Frame(f, bg=BG)
        genre_frame.pack(fill="x", pady=(0, 10))
        genres = [("General (all genres)", "general"), ("Romance", "romance"),
                  ("Thriller / Mystery", "thriller"), ("Fantasy", "fantasy"),
                  ("Sci-Fi", "scifi"), ("Literary Fiction", "literary"),
                  ("Nonfiction", "nonfiction"), ("Young Adult", "ya")]
        self._genre_map = {g[0]: g[1] for g in genres}
        self._genre_display = tk.StringVar(value="General (all genres)")
        genre_combo = ttk.Combobox(genre_frame, textvariable=self._genre_display,
                                    state="readonly",
                                    values=[g[0] for g in genres], font=(FONT, 10))
        genre_combo.pack(fill="x", ipady=4)
        def _sync_genre(*args):
            display = self._genre_display.get()
            self.genre.set(self._genre_map.get(display, "general"))
        self._genre_display.trace_add("write", _sync_genre)
        _sync_genre()

        # === READERS ===
        self._section_label(f, f"Readers: {self.readers.get():,}")
        self.readers_label = f.winfo_children()[-1]
        reader_frame = tk.Frame(f, bg=BG)
        reader_frame.pack(fill="x", pady=(0, 4))
        reader_scale = tk.Scale(reader_frame, from_=50, to=500000, orient="horizontal",
                                variable=self.readers, bg=BG, fg=FG, troughcolor=MUTED_BG,
                                highlightthickness=0, sliderrelief="flat",
                                font=(FONT, 9), showvalue=False, activebackground=BORDER,
                                command=lambda v: self.readers_label.config(
                                    text=f"Readers: {int(float(v)):,}"))
        reader_scale.pack(fill="x")

        # Presets
        preset_frame = tk.Frame(f, bg=BG)
        preset_frame.pack(fill="x", pady=(0, 10))
        for label, val in [("100", 100), ("1K", 1000), ("10K", 10000),
                           ("100K", 100000), ("500K", 500000)]:
            tk.Button(preset_frame, text=label, font=(MONO, 8),
                      bg=MUTED_BG, fg=MUTED, relief="flat", cursor="hand2", bd=0,
                      activebackground=BORDER,
                      command=lambda v=val: [self.readers.set(v),
                                             self.readers_label.config(
                                                 text=f"Readers: {v:,}")]
                      ).pack(side="left", padx=2, ipady=2, ipadx=8)

        # === ROUNDS ===
        self._section_label(f, f"Rounds: {self.rounds.get()}")
        self.rounds_label = f.winfo_children()[-1]
        rounds_scale = tk.Scale(f, from_=1, to=100, orient="horizontal",
                                variable=self.rounds, bg=BG, fg=FG, troughcolor=MUTED_BG,
                                highlightthickness=0, sliderrelief="flat",
                                font=(FONT, 9), showvalue=False, activebackground=BORDER,
                                command=lambda v: self.rounds_label.config(
                                    text=f"Rounds: {int(float(v))}"))
        rounds_scale.pack(fill="x", pady=(0, 10))

        # === WORKERS ===
        self._section_label(f, f"Workers: {self.workers.get()}")
        self.workers_label = f.winfo_children()[-1]
        workers_scale = tk.Scale(f, from_=1, to=20, orient="horizontal",
                                 variable=self.workers, bg=BG, fg=FG, troughcolor=MUTED_BG,
                                 highlightthickness=0, sliderrelief="flat",
                                 font=(FONT, 9), showvalue=False, activebackground=BORDER,
                                 command=lambda v: self.workers_label.config(
                                     text=f"Workers: {int(float(v))}"))
        workers_scale.pack(fill="x", pady=(0, 2))
        tk.Label(f, text="Default 5. More = faster. Use 1-3 for rate limits, 10-20 for 10K+ readers.",
                 font=(FONT, 8), fg=MUTED, bg=BG).pack(anchor="w", pady=(0, 10))

        # === ESTIMATE ===
        self.estimate_label = tk.Label(f, text="", font=(MONO, 9),
                                        fg=MUTED, bg=MUTED_BG, anchor="w")
        self.estimate_label.pack(fill="x", ipady=8, ipadx=12, pady=(0, 12))
        self._update_estimate()

        for var in [self.readers, self.rounds, self.provider]:
            var.trace_add("write", lambda *a: self._update_estimate())

        # === RUN BUTTON ===
        self.run_btn = tk.Button(f, text="Start Simulation",
                                  font=(FONT, 14, "bold"),
                                  bg=ACCENT, fg=ACCENT_FG, relief="flat", cursor="hand2",
                                  bd=0, activebackground="#27272a", activeforeground="white",
                                  command=self._start_simulation)
        self.run_btn.pack(fill="x", ipady=12, pady=(0, 12))

        # === PROGRESS ===
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(f, variable=self.progress_var,
                                             maximum=100, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(0, 6))

        self.status_label = tk.Label(f, text="Ready", font=(FONT, 10), fg=MUTED, bg=BG)
        self.status_label.pack(pady=(0, 12))

        # === LOG OUTPUT ===
        tk.Frame(f, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))
        self._section_label(f, "Output")
        self.log_text = scrolledtext.ScrolledText(f, height=12, font=(MONO, 9),
                                                   bg=CARD, fg=FG,
                                                   insertbackground=FG, relief="flat",
                                                   highlightbackground=BORDER,
                                                   highlightthickness=1, wrap="word")
        self.log_text.pack(fill="both", expand=True, pady=(0, 10))

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=(FONT, 11, "bold"),
                 fg=FG, bg=BG, anchor="w").pack(fill="x", pady=(8, 4))

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Book Description File",
            initialdir=str(SCRIPT_DIR / "examples"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.book_file.set(path)

    def _update_estimate(self):
        try:
            readers = self.readers.get()
            rounds = self.rounds.get()
            prov = self.provider.get()

            batch_size = 5
            batches_r1 = (readers + batch_size - 1) // batch_size
            active_r2 = readers // 3
            batches_social = (active_r2 + batch_size - 1) // batch_size
            social_rounds = max(0, rounds - 1)
            total_batches = batches_r1 + batches_social * social_rounds

            speeds = {"ollama": 8.0, "openai": 3.0, "anthropic": 4.0, "gemini": 2.5}
            costs = {"ollama": 0.0, "openai": 0.003, "anthropic": 0.004, "gemini": 0.001}

            est_min = total_batches * speeds.get(prov, 5) / 60
            est_cost = total_batches * costs.get(prov, 0.005)

            cost_str = f"${est_cost:.2f}" if est_cost > 0 else "FREE"
            self.estimate_label.config(
                text=f"  ~{est_min:.0f} min  |  ~{total_batches} calls  |  {cost_str}")
        except Exception:
            pass

    def _install_deps(self):
        self._log("Installing dependencies...\n")
        self.status_label.config(text="Installing...", fg=ORANGE)

        def _run():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "rich", "python-dotenv",
                     "google-genai", "openai", "anthropic"],
                    capture_output=True, text=True, timeout=120
                )
                self.root.after(0, lambda: self._log(result.stdout + result.stderr))
                self.root.after(0, lambda: self.status_label.config(
                    text="Installed. Restart the app.", fg=GREEN))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Done", "Dependencies installed. Please restart Readers."))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Error: {e}\n"))
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Install failed: {e}", fg=RED))

        threading.Thread(target=_run, daemon=True).start()

    def _start_simulation(self):
        if self.running:
            return

        book = self.book_file.get().strip()
        if not book:
            messagebox.showwarning("No Book File", "Select a book description file first.")
            return
        if not os.path.exists(book):
            messagebox.showerror("File Not Found", f"Could not find: {book}")
            return

        self.running = True
        self.run_btn.config(state="disabled", bg=MUTED, text="Running...")
        self.progress_bar.start(10)
        self.log_text.delete("1.0", "end")
        self.status_label.config(text="Simulation running...", fg=BLUE)

        genre = self.genre.get()
        workers = self.workers.get()
        cmd = [
            sys.executable, str(SCRIPT_DIR / "readers.py"),
            "--file", book,
            "--provider", self.provider.get(),
            "--readers", str(self.readers.get()),
            "--rounds", str(self.rounds.get()),
        ]
        if genre and genre != "general":
            cmd.extend(["--genre", genre])
        if workers > 1:
            cmd.extend(["--workers", str(workers)])

        self._log(f"$ {' '.join(cmd)}\n\n")

        def _run():
            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    cwd=str(SCRIPT_DIR), env=env, bufsize=1
                )

                report_path = None
                for line in iter(process.stdout.readline, ""):
                    self.root.after(0, lambda l=line: self._log(l))
                    if "Report saved:" in line:
                        parts = line.split("Report saved:")
                        if len(parts) > 1:
                            report_path = parts[1].strip().strip("\x1b[0m").strip()

                process.wait()
                exit_code = process.returncode

                def _finish():
                    self.progress_bar.stop()
                    self.running = False
                    self.run_btn.config(state="normal", bg=ACCENT, text="Start Simulation")

                    if exit_code == 0:
                        self.status_label.config(text="Complete. Report opened in browser.", fg=GREEN)
                        if not report_path:
                            output_dir = SCRIPT_DIR / "output"
                            if output_dir.exists():
                                htmls = sorted(output_dir.glob("readers_report_*.html"),
                                               key=lambda p: p.stat().st_mtime, reverse=True)
                                if htmls:
                                    webbrowser.open(f"file://{htmls[0].resolve()}")
                    else:
                        self.status_label.config(text=f"Finished with errors (code {exit_code})", fg=RED)

                self.root.after(0, _finish)

            except Exception as e:
                def _error():
                    self.progress_bar.stop()
                    self.running = False
                    self.run_btn.config(state="normal", bg=ACCENT, text="Start Simulation")
                    self.status_label.config(text=f"Error: {e}", fg=RED)
                    self._log(f"\nError: {e}\n")
                self.root.after(0, _error)

        threading.Thread(target=_run, daemon=True).start()

    def _log(self, text):
        import re
        clean = re.sub(r'\x1b\[[0-9;]*m', '', text)
        self.log_text.insert("end", clean)
        self.log_text.see("end")


def main():
    root = tk.Tk()
    app = ReadersGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
