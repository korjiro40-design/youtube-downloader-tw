import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import yt_dlp

APP_NAME = "YouTube 下載器・繁體中文版"

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("720x470")
        self.minsize(680, 430)
        self.url = tk.StringVar()
        self.mode = tk.StringVar(value="MP4 最佳畫質")
        self.folder = tk.StringVar(value=str(Path.home() / "Downloads" / "YouTube"))
        self.status = tk.StringVar(value="準備就緒")
        self.progress = tk.DoubleVar(value=0)
        self._build()

    def _build(self):
        root = ttk.Frame(self, padding=22)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="YouTube 下載器", font=("Microsoft JhengHei UI", 20, "bold")).pack(anchor="w")
        ttk.Label(root, text="單部影片與播放清單｜免指令｜可攜版", font=("Microsoft JhengHei UI", 10)).pack(anchor="w", pady=(2,18))

        ttk.Label(root, text="YouTube 網址").pack(anchor="w")
        row = ttk.Frame(root); row.pack(fill="x", pady=(5,14))
        ttk.Entry(row, textvariable=self.url).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="貼上網址", command=self.paste).pack(side="left", padx=(8,0))

        ttk.Label(root, text="下載格式").pack(anchor="w")
        ttk.Combobox(root, textvariable=self.mode, state="readonly", values=["MP4 最佳畫質","MP4 1080p","MP4 720p","MP3 高音質"], width=24).pack(anchor="w", pady=(5,14))

        ttk.Label(root, text="儲存位置").pack(anchor="w")
        row2 = ttk.Frame(root); row2.pack(fill="x", pady=(5,16))
        ttk.Entry(row2, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="瀏覽", command=self.browse).pack(side="left", padx=(8,0))
        ttk.Button(row2, text="開啟資料夾", command=self.open_folder).pack(side="left", padx=(8,0))

        self.btn = ttk.Button(root, text="開始下載", command=self.start)
        self.btn.pack(fill="x", ipady=8, pady=(0,16))
        ttk.Progressbar(root, variable=self.progress, maximum=100).pack(fill="x")
        ttk.Label(root, textvariable=self.status, wraplength=650).pack(anchor="w", pady=(8,0))
        ttk.Label(root, text="播放清單會自動依 01、02、03… 排序；請僅下載你有權保存的內容。", foreground="#666").pack(anchor="w", pady=(18,0))

    def paste(self):
        try: self.url.set(self.clipboard_get().strip())
        except tk.TclError: pass

    def browse(self):
        p = filedialog.askdirectory(initialdir=self.folder.get() or str(Path.home()))
        if p: self.folder.set(p)

    def open_folder(self):
        p = Path(self.folder.get()); p.mkdir(parents=True, exist_ok=True)
        os.startfile(str(p))

    def start(self):
        if not self.url.get().strip():
            messagebox.showwarning("缺少網址", "請先貼上 YouTube 網址。")
            return
        Path(self.folder.get()).mkdir(parents=True, exist_ok=True)
        self.btn.config(state="disabled")
        self.progress.set(0); self.status.set("正在準備下載…")
        threading.Thread(target=self.download, daemon=True).start()

    def hook(self, d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            name = os.path.basename(d.get("filename", ""))
            self.after(0, lambda: (self.progress.set(pct), self.status.set(f"下載中 {pct:.1f}%｜{name}")))
        elif d.get("status") == "finished":
            self.after(0, lambda: self.status.set("下載完成，正在處理檔案…"))

    def download(self):
        try:
            mode = self.mode.get()
            ffmpeg = resource_path("ffmpeg.exe")
            out = os.path.join(self.folder.get(), "%(playlist_index&{} - |)s%(title)s.%(ext)s")
            opts = {
                "outtmpl": out,
                "windowsfilenames": True,
                "ignoreerrors": False,
                "retries": 5,
                "fragment_retries": 5,
                "progress_hooks": [self.hook],
                "noplaylist": False,
                "ffmpeg_location": ffmpeg if os.path.exists(ffmpeg) else None,
                "quiet": True,
                "no_warnings": True,
            }
            if mode == "MP3 高音質":
                opts.update({"format":"bestaudio/best", "postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"0"}]})
            else:
                h = None if mode == "MP4 最佳畫質" else (1080 if "1080" in mode else 720)
                if h:
                    opts["format"] = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]"
                else:
                    opts["format"] = "bestvideo+bestaudio/best"
                opts["merge_output_format"] = "mp4"
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([self.url.get().strip()])
            self.after(0, self.done)
        except Exception as e:
            self.after(0, lambda err=str(e): self.fail(err))

    def done(self):
        self.progress.set(100); self.status.set("下載完成！")
        self.btn.config(state="normal")
        messagebox.showinfo("完成", "下載完成！")

    def fail(self, err):
        self.status.set("下載失敗")
        self.btn.config(state="normal")
        messagebox.showerror("下載失敗", err)

if __name__ == "__main__":
    App().mainloop()
