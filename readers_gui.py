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

# Colors matching the Readers brand
BG = "#0d0d16"
SURFACE = "#13131f"
BORDER = "#1f1f35"
TEXT = "#ededf4"
TEXT_DIM = "#7878a0"
CORAL = "#ff6b6b"
GOLD = "#fbbf24"
EMERALD = "#34d399"


class ReadersGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Readers — AI Reader Simulation")
        self.root.configure(bg=BG)
        self.root.geometry("680x820")
        self.root.resizable(True, True)

        # Try to set icon
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
        self._build_ui()

    def _check_dependencies(self):
        """Check if required packages are installed."""
        self.missing_deps = []
        for pkg, import_name in [("rich", "rich"), ("python-dotenv", "dotenv"),
                                  ("google-genai", "google.genai"), ("openai", "openai"),
                                  ("anthropic", "anthropic")]:
            try:
                __import__(import_name)
            except ImportError:
                self.missing_deps.append(pkg)

    def _check_env_file(self):
        """Check if .env exists and has keys."""
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
        # Main scrollable frame
        canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.main_frame = tk.Frame(canvas, bg=BG)
        self.main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        f = self.main_frame

        # === HEADER ===
        tk.Label(f, text="Readers", font=("Segoe UI", 28, "bold"),
                 fg=GOLD, bg=BG).pack(pady=(10, 0))
        tk.Label(f, text="Up to 500,000 AI Readers Judge Your Book",
                 font=("Segoe UI", 11), fg=TEXT_DIM, bg=BG).pack()
        tk.Label(f, text="PRISM Demographics  |  Genre-Specific Personas  |  Purchase Intent",
                 font=("Segoe UI", 9), fg=CORAL, bg=BG).pack(pady=(2, 15))

        # === DEPENDENCY WARNING ===
        if self.missing_deps:
            warn_frame = tk.Frame(f, bg="#2a1a1a", highlightbackground=CORAL,
                                  highlightthickness=1)
            warn_frame.pack(fill="x", pady=(0, 10))
            tk.Label(warn_frame, text="Missing packages detected. Click 'Install Dependencies' below.",
                     font=("Segoe UI", 9), fg=CORAL, bg="#2a1a1a",
                     wraplength=600).pack(padx=10, pady=8)
            tk.Button(warn_frame, text="Install Dependencies", font=("Segoe UI", 10, "bold"),
                      bg=CORAL, fg="white", relief="flat", cursor="hand2",
                      command=self._install_deps).pack(padx=10, pady=(0, 8))

        # === API KEY STATUS ===
        if self.env_status != "has_keys":
            key_frame = tk.Frame(f, bg="#1a1a2a", highlightbackground=GOLD,
                                 highlightthickness=1)
            key_frame.pack(fill="x", pady=(0, 10))
            if self.env_status == "no_file":
                msg = "No .env file found. You need an API key to run cloud providers.\nCopy .env.example to .env and add your key. Ollama works without a key."
            else:
                msg = "Your .env file exists but has no active API keys.\nUncomment and fill in at least one key (Gemini recommended)."
            tk.Label(key_frame, text=msg, font=("Segoe UI", 9),
                     fg=GOLD, bg="#1a1a2a", wraplength=600, justify="left").pack(padx=10, pady=8)
            tk.Button(key_frame, text="Open .env.example", font=("Segoe UI", 9),
                      bg=SURFACE, fg=TEXT_DIM, relief="flat", cursor="hand2",
                      command=lambda: os.startfile(str(SCRIPT_DIR / ".env.example"))).pack(padx=10, pady=(0, 8))

        # === BOOK FILE ===
        self._section_label(f, "1. Select Your Book File")
        file_frame = tk.Frame(f, bg=BG)
        file_frame.pack(fill="x", pady=(0, 10))
        tk.Entry(file_frame, textvariable=self.book_file, font=("Segoe UI", 10),
                 bg=SURFACE, fg=TEXT, insertbackground=TEXT, relief="flat",
                 highlightbackground=BORDER, highlightthickness=1).pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(file_frame, text="Browse...", font=("Segoe UI", 10),
                  bg=SURFACE, fg=TEXT_DIM, relief="flat", cursor="hand2",
                  command=self._browse_file).pack(side="right", padx=(8, 0), ipady=4)

        tk.Label(f, text="Tip: A 200-500 word book description works best. Full manuscripts will be auto-summarized.",
                 font=("Segoe UI", 8), fg=TEXT_DIM, bg=BG, wraplength=600,
                 justify="left").pack(anchor="w", pady=(0, 5))

        # === PROVIDER ===
        self._section_label(f, "2. Choose AI Provider")
        prov_frame = tk.Frame(f, bg=BG)
        prov_frame.pack(fill="x", pady=(0, 10))
        providers = [
            ("Gemini (Recommended — fast & cheap)", "gemini"),
            ("OpenAI (GPT-4o-mini)", "openai"),
            ("Anthropic (Claude)", "anthropic"),
            ("Ollama (Free — local, no API key)", "ollama"),
        ]
        for label, value in providers:
            tk.Radiobutton(prov_frame, text=label, variable=self.provider, value=value,
                           font=("Segoe UI", 10), fg=TEXT, bg=BG, selectcolor=SURFACE,
                           activebackground=BG, activeforeground=GOLD,
                           highlightthickness=0).pack(anchor="w")

        # === GENRE ===
        self._section_label(f, "3. Genre (PRISM Demographics)")
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
                                    values=[g[0] for g in genres], font=("Segoe UI", 10))
        genre_combo.pack(fill="x", ipady=4)
        # Keep self.genre synced to the actual CLI value, not the display name
        def _sync_genre(*args):
            display = self._genre_display.get()
            self.genre.set(self._genre_map.get(display, "general"))
        self._genre_display.trace_add("write", _sync_genre)
        _sync_genre()  # Initialize on startup

        # === READERS ===
        self._section_label(f, f"4. Number of Readers: {self.readers.get():,}")
        self.readers_label = f.winfo_children()[-1]  # Reference to update
        reader_frame = tk.Frame(f, bg=BG)
        reader_frame.pack(fill="x", pady=(0, 5))
        reader_scale = tk.Scale(reader_frame, from_=50, to=500000, orient="horizontal",
                                variable=self.readers, bg=BG, fg=TEXT, troughcolor=SURFACE,
                                highlightthickness=0, sliderrelief="flat",
                                font=("Segoe UI", 9), showvalue=False,
                                command=lambda v: self.readers_label.config(
                                    text=f"4. Number of Readers: {int(float(v)):,}"))
        reader_scale.pack(fill="x")

        # Quick presets
        preset_frame = tk.Frame(f, bg=BG)
        preset_frame.pack(fill="x", pady=(0, 10))
        for label, val in [("100 (Quick)", 100), ("1,000", 1000), ("10,000", 10000),
                           ("100,000", 100000), ("500,000", 500000)]:
            tk.Button(preset_frame, text=label, font=("Segoe UI", 8),
                      bg=SURFACE, fg=TEXT_DIM, relief="flat", cursor="hand2",
                      command=lambda v=val: [self.readers.set(v),
                                             self.readers_label.config(
                                                 text=f"4. Number of Readers: {v:,}")]
                      ).pack(side="left", padx=2, ipady=2, ipadx=6)

        # === ROUNDS ===
        self._section_label(f, f"5. Social Rounds: {self.rounds.get()}")
        self.rounds_label = f.winfo_children()[-1]
        rounds_scale = tk.Scale(f, from_=1, to=100, orient="horizontal",
                                variable=self.rounds, bg=BG, fg=TEXT, troughcolor=SURFACE,
                                highlightthickness=0, sliderrelief="flat",
                                font=("Segoe UI", 9), showvalue=False,
                                command=lambda v: self.rounds_label.config(
                                    text=f"5. Social Rounds: {int(float(v))}"))
        rounds_scale.pack(fill="x", pady=(0, 10))

        # === WORKERS ===
        self._section_label(f, f"6. Parallel Workers: {self.workers.get()}")
        self.workers_label = f.winfo_children()[-1]
        workers_scale = tk.Scale(f, from_=1, to=20, orient="horizontal",
                                 variable=self.workers, bg=BG, fg=TEXT, troughcolor=SURFACE,
                                 highlightthickness=0, sliderrelief="flat",
                                 font=("Segoe UI", 9), showvalue=False,
                                 command=lambda v: self.workers_label.config(
                                     text=f"6. Parallel Workers: {int(float(v))}"))
        workers_scale.pack(fill="x", pady=(0, 2))
        tk.Label(f, text="Default: 5 (recommended). More workers = faster. Use 1-3 if you hit rate limits, 10-20 for 10K+ readers.",
                 font=("Segoe UI", 8), fg=TEXT_DIM, bg=BG, wraplength=600,
                 justify="left").pack(anchor="w", pady=(0, 10))

        # === ESTIMATE ===
        self.estimate_label = tk.Label(f, text="", font=("Segoe UI", 9),
                                        fg=TEXT_DIM, bg=BG, wraplength=600, justify="left")
        self.estimate_label.pack(fill="x", pady=(0, 10))
        self._update_estimate()

        # Bind changes to update estimate
        for var in [self.readers, self.rounds, self.provider]:
            var.trace_add("write", lambda *a: self._update_estimate())

        # === RUN BUTTON ===
        self.run_btn = tk.Button(f, text="START SIMULATION",
                                  font=("Segoe UI", 16, "bold"),
                                  bg=CORAL, fg="white", relief="flat", cursor="hand2",
                                  activebackground="#ff8888", activeforeground="white",
                                  command=self._start_simulation)
        self.run_btn.pack(fill="x", ipady=12, pady=(5, 10))

        # === PROGRESS ===
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(f, variable=self.progress_var,
                                             maximum=100, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(0, 5))

        self.status_label = tk.Label(f, text="Ready. Select a book file and click START.",
                                      font=("Segoe UI", 10), fg=EMERALD, bg=BG)
        self.status_label.pack(pady=(0, 10))

        # === LOG OUTPUT ===
        self._section_label(f, "Output Log")
        self.log_text = scrolledtext.ScrolledText(f, height=12, font=("Consolas", 9),
                                                   bg=SURFACE, fg=TEXT,
                                                   insertbackground=TEXT, relief="flat",
                                                   highlightbackground=BORDER,
                                                   highlightthickness=1, wrap="word")
        self.log_text.pack(fill="both", expand=True, pady=(0, 10))

    def _section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 11, "bold"),
                 fg=TEXT, bg=BG, anchor="w").pack(fill="x", pady=(8, 3))

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
                text=f"Estimate: ~{est_min:.0f} min  |  ~{total_batches} API calls  |  Cost: {cost_str}")
        except Exception:
            pass

    def _install_deps(self):
        self._log("Installing dependencies...\n")
        self.status_label.config(text="Installing packages...", fg=GOLD)

        def _run():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "rich", "python-dotenv",
                     "google-genai", "openai", "anthropic"],
                    capture_output=True, text=True, timeout=120
                )
                self.root.after(0, lambda: self._log(result.stdout + result.stderr))
                self.root.after(0, lambda: self.status_label.config(
                    text="Dependencies installed! Restart the app.", fg=EMERALD))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Done", "Dependencies installed. Please restart Readers GUI."))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Error: {e}\n"))
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Install failed: {e}", fg=CORAL))

        threading.Thread(target=_run, daemon=True).start()

    def _start_simulation(self):
        if self.running:
            return

        # Validate
        book = self.book_file.get().strip()
        if not book:
            messagebox.showwarning("No Book File", "Please select a book description file first.")
            return
        if not os.path.exists(book):
            messagebox.showerror("File Not Found", f"Could not find: {book}")
            return

        self.running = True
        self.run_btn.config(state="disabled", bg="#666", text="RUNNING...")
        self.progress_bar.start(10)
        self.log_text.delete("1.0", "end")
        self.status_label.config(text="Simulation running... this may take a while.", fg=GOLD)

        # Build command
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

        self._log(f"Running: {' '.join(cmd)}\n\n")

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
                    # Detect report path
                    if "Report saved:" in line:
                        parts = line.split("Report saved:")
                        if len(parts) > 1:
                            report_path = parts[1].strip().strip("\x1b[0m").strip()

                process.wait()
                exit_code = process.returncode

                def _finish():
                    self.progress_bar.stop()
                    self.running = False
                    self.run_btn.config(state="normal", bg=CORAL, text="START SIMULATION")

                    if exit_code == 0:
                        self.status_label.config(text="Simulation complete! Report opened in browser.", fg=EMERALD)
                        # Try to find the report if not detected from output
                        if not report_path:
                            output_dir = SCRIPT_DIR / "output"
                            if output_dir.exists():
                                htmls = sorted(output_dir.glob("readers_report_*.html"),
                                               key=lambda p: p.stat().st_mtime, reverse=True)
                                if htmls:
                                    webbrowser.open(f"file://{htmls[0].resolve()}")
                    else:
                        self.status_label.config(text=f"Simulation finished with errors (exit code {exit_code})", fg=CORAL)

                self.root.after(0, _finish)

            except Exception as e:
                def _error():
                    self.progress_bar.stop()
                    self.running = False
                    self.run_btn.config(state="normal", bg=CORAL, text="START SIMULATION")
                    self.status_label.config(text=f"Error: {e}", fg=CORAL)
                    self._log(f"\nError: {e}\n")
                self.root.after(0, _error)

        threading.Thread(target=_run, daemon=True).start()

    def _log(self, text):
        # Strip ANSI escape codes for clean display
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
