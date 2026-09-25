import os, sys, threading, subprocess, json, time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import yt_dlp

APP_NAME = "YouTube 下載器・v3 長影片安全版"

def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

def fmt_time(sec):
    if sec is None: return "未知"
    sec = int(round(float(sec))); h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(APP_NAME); self.geometry("760x530"); self.minsize(700,470)
        self.url=tk.StringVar(); self.mode=tk.StringVar(value="MP3 高音質")
        self.folder=tk.StringVar(value=str(Path.home()/"Downloads"/"YouTube")); self.status=tk.StringVar(value="準備就緒")
        self.detail=tk.StringVar(value=""); self.progress=tk.DoubleVar(value=0); self.expected={}; self.completed=[]; self._build()
    def _build(self):
        root=ttk.Frame(self,padding=22); root.pack(fill="both",expand=True)
        ttk.Label(root,text="YouTube 下載器 v3",font=("Microsoft JhengHei UI",20,"bold")).pack(anchor="w")
        ttk.Label(root,text="長影片安全版｜完成後自動比對原始時長與成品時長").pack(anchor="w",pady=(2,18))
        ttk.Label(root,text="YouTube 網址").pack(anchor="w"); row=ttk.Frame(root); row.pack(fill="x",pady=(5,14))
        ttk.Entry(row,textvariable=self.url).pack(side="left",fill="x",expand=True); ttk.Button(row,text="貼上網址",command=self.paste).pack(side="left",padx=(8,0))
        ttk.Label(root,text="下載格式").pack(anchor="w"); ttk.Combobox(root,textvariable=self.mode,state="readonly",values=["MP3 高音質","MP4 最佳畫質","MP4 1080p","MP4 720p"],width=24).pack(anchor="w",pady=(5,14))
        ttk.Label(root,text="儲存位置").pack(anchor="w"); r=ttk.Frame(root); r.pack(fill="x",pady=(5,16))
        ttk.Entry(r,textvariable=self.folder).pack(side="left",fill="x",expand=True); ttk.Button(r,text="瀏覽",command=self.browse).pack(side="left",padx=(8,0)); ttk.Button(r,text="開啟資料夾",command=self.open_folder).pack(side="left",padx=(8,0))
        self.btn=ttk.Button(root,text="開始下載",command=self.start); self.btn.pack(fill="x",ipady=8,pady=(0,16))
        ttk.Progressbar(root,variable=self.progress,maximum=100).pack(fill="x"); ttk.Label(root,textvariable=self.status,wraplength=700).pack(anchor="w",pady=(8,0)); ttk.Label(root,textvariable=self.detail,wraplength=700).pack(anchor="w",pady=(5,0))
        ttk.Label(root,text="若成品明顯短於 YouTube 原始時長，v3 會判定失敗，不再誤報完成。",foreground="#666").pack(anchor="w",pady=(18,0))
    def paste(self):
        try:self.url.set(self.clipboard_get().strip())
        except tk.TclError:pass
    def browse(self):
        p=filedialog.askdirectory(initialdir=self.folder.get() or str(Path.home()));
        if p:self.folder.set(p)
    def open_folder(self):
        p=Path(self.folder.get());p.mkdir(parents=True,exist_ok=True);os.startfile(str(p))
    def start(self):
        if not self.url.get().strip():messagebox.showwarning("缺少網址","請先貼上 YouTube 網址。");return
        Path(self.folder.get()).mkdir(parents=True,exist_ok=True);self.btn.config(state="disabled");self.progress.set(0);self.status.set("正在取得影片資訊…");self.detail.set("");self.expected={};self.completed=[]
        threading.Thread(target=self.download,daemon=True).start()
    def hook(self,d):
        if d.get("status")=="downloading":
            total=d.get("total_bytes") or d.get("total_bytes_estimate");done=d.get("downloaded_bytes",0);pct=(done/total*100) if total else 0
            speed=d.get("speed") or 0;eta=d.get("eta");name=os.path.basename(d.get("filename","")); info=d.get("info_dict") or {}; idx=info.get("playlist_index");count=info.get("n_entries") or info.get("playlist_count")
            prefix=f"第 {idx}/{count} 部｜" if idx and count else ""; mb=done/1048576; sp=f"{speed/1048576:.2f} MB/s" if speed else "--"; et=f"{eta//60:02d}:{eta%60:02d}" if isinstance(eta,int) else "--"
            self.after(0,lambda:(self.progress.set(pct),self.status.set(f"{prefix}下載中 {pct:.1f}%｜{name}"),self.detail.set(f"已下載 {mb:.1f} MB｜速度 {sp}｜剩餘 {et}")))
        elif d.get("status")=="finished": self.after(0,lambda:self.status.set("媒體串流完成，正在合併／轉檔與驗證…"))
    def probe(self,path):
        exe=resource_path("ffprobe.exe"); p=subprocess.run([exe,"-v","error","-show_entries","format=duration","-of","json",str(path)],capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0));
        if p.returncode: raise RuntimeError("FFprobe 無法讀取成品："+p.stderr.strip())
        return float(json.loads(p.stdout)["format"]["duration"])
    def collect_expected(self,info):
        if info.get("_type")=="playlist":
            for e in info.get("entries") or []:
                if e and e.get("id") and e.get("duration"): self.expected[e["id"]]=float(e["duration"])
        elif info.get("id") and info.get("duration"): self.expected[info["id"]]=float(info["duration"])
    def download(self):
        try:
            ffmpeg=resource_path("ffmpeg.exe");ffprobe=resource_path("ffprobe.exe")
            if not os.path.isfile(ffmpeg) or not os.path.isfile(ffprobe):raise RuntimeError("缺少 FFmpeg/FFprobe，請下載 v3 完整可攜版。")
            folder=Path(self.folder.get()); out=str(folder/"%(playlist_index&{} - |)s%(title)s [%(id)s].%(ext)s")
            base={"outtmpl":out,"windowsfilenames":True,"ignoreerrors":False,"retries":20,"fragment_retries":20,"file_access_retries":10,"extractor_retries":10,"continuedl":True,"part":True,"concurrent_fragment_downloads":1,"progress_hooks":[self.hook],"noplaylist":False,"ffmpeg_location":os.path.dirname(ffmpeg),"quiet":False,"no_warnings":False,"overwrites":True}
            with yt_dlp.YoutubeDL({**base,"skip_download":True,"quiet":True}) as y:
                info=y.extract_info(self.url.get().strip(),download=False); self.collect_expected(info)
            mode=self.mode.get(); opts=dict(base)
            if mode=="MP3 高音質": opts.update({"format":"bestaudio/best","postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"0"}]})
            else:
                h=None if mode=="MP4 最佳畫質" else (1080 if "1080" in mode else 720); opts["format"]=(f"bv*[height<={h}]+ba/b[height<={h}]/b" if h else "bv*+ba/b");opts["merge_output_format"]="mp4"
            with yt_dlp.YoutubeDL(opts) as y: code=y.download([self.url.get().strip()])
            if code!=0:raise RuntimeError(f"yt-dlp 回傳錯誤代碼 {code}")
            self.after(0,lambda:self.status.set("正在檢查成品完整性…"))
            ext="mp3" if mode=="MP3 高音質" else "mp4"; files=sorted(folder.glob(f"*.{ext}"),key=lambda p:p.stat().st_mtime,reverse=True)
            checked=[]
            for f in files:
                if time.time()-f.stat().st_mtime>7200: continue
                vid=None
                for k in self.expected:
                    if f"[{k}]" in f.name:vid=k;break
                if not vid:continue
                actual=self.probe(f); expected=self.expected[vid]; ratio=actual/expected if expected else 1
                checked.append((f,expected,actual,ratio))
                if ratio<0.98 or abs(actual-expected)>30:
                    raise RuntimeError(f"成品不完整：{f.name}\n原始時長 {fmt_time(expected)}，成品只有 {fmt_time(actual)}（{ratio*100:.1f}%）。\n請重新下載；v3 已阻止把此檔誤判為成功。")
            if not checked: raise RuntimeError("下載後找不到可驗證的成品檔案，已取消『完成』判定。")
            summary="；".join([f"{f.name}: {fmt_time(a)}/{fmt_time(e)} ✓" for f,e,a,_ in checked[:3]])
            self.after(0,lambda:self.done(summary))
        except Exception as e:
            err=str(e)
            try:(Path(self.folder.get())/"download-error.txt").write_text(err,encoding="utf-8")
            except Exception:pass
            self.after(0,lambda:self.fail(err))
    def done(self,summary):
        self.progress.set(100);self.status.set("下載、轉檔與時長驗證全部完成 ✓");self.detail.set(summary);self.btn.config(state="normal");messagebox.showinfo("完成","檔案已下載完成，且時長驗證通過。\n\n"+summary)
    def fail(self,err):
        self.status.set("下載或完整性驗證失敗");self.detail.set(err);self.btn.config(state="normal");messagebox.showerror("未完成",err+"\n\n詳細錯誤已寫入 download-error.txt")

if __name__=="__main__":App().mainloop()
