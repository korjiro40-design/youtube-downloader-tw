import os, sys, threading, subprocess, json, time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import yt_dlp

APP_NAME="YouTube 下載器・v4"
def resource_path(n): return os.path.join(getattr(sys,"_MEIPASS",os.path.dirname(os.path.abspath(__file__))),n)
def fmt_time(sec):
    if sec is None:return "未知"
    sec=int(round(float(sec)));h,r=divmod(sec,3600);m,s=divmod(r,60);return f"{h:02d}:{m:02d}:{s:02d}"
class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title(APP_NAME);self.geometry("780x550");self.minsize(710,480)
        self.url=tk.StringVar();self.mode=tk.StringVar(value="原始音訊・極速（推薦做筆記）");self.folder=tk.StringVar(value=str(Path.home()/"Downloads"/"YouTube"));self.status=tk.StringVar(value="準備就緒");self.detail=tk.StringVar(value="");self.progress=tk.DoubleVar(value=0);self.expected={};self._build()
    def _build(self):
        root=ttk.Frame(self,padding=22);root.pack(fill="both",expand=True)
        ttk.Label(root,text="YouTube 下載器 v4",font=("Microsoft JhengHei UI",20,"bold")).pack(anchor="w")
        ttk.Label(root,text="長影片安全版｜原始音訊極速下載｜MP3 語音模式｜自動時長驗證").pack(anchor="w",pady=(2,18))
        ttk.Label(root,text="YouTube 網址").pack(anchor="w");r=ttk.Frame(root);r.pack(fill="x",pady=(5,14));ttk.Entry(r,textvariable=self.url).pack(side="left",fill="x",expand=True);ttk.Button(r,text="貼上網址",command=self.paste).pack(side="left",padx=(8,0))
        ttk.Label(root,text="下載格式").pack(anchor="w");ttk.Combobox(root,textvariable=self.mode,state="readonly",values=["原始音訊・極速（推薦做筆記）","MP3 128k・語音課程","MP3 高音質・音樂","MP4 最佳畫質","MP4 1080p","MP4 720p"],width=34).pack(anchor="w",pady=(5,5));ttk.Label(root,text="提示：原始音訊不重新編碼，下載後最快完成；MP3 需要 FFmpeg 重新編碼。",foreground="#666").pack(anchor="w",pady=(0,14))
        ttk.Label(root,text="儲存位置").pack(anchor="w");r2=ttk.Frame(root);r2.pack(fill="x",pady=(5,16));ttk.Entry(r2,textvariable=self.folder).pack(side="left",fill="x",expand=True);ttk.Button(r2,text="瀏覽",command=self.browse).pack(side="left",padx=(8,0));ttk.Button(r2,text="開啟資料夾",command=self.open_folder).pack(side="left",padx=(8,0))
        self.btn=ttk.Button(root,text="開始下載",command=self.start);self.btn.pack(fill="x",ipady=8,pady=(0,16));ttk.Progressbar(root,variable=self.progress,maximum=100).pack(fill="x");ttk.Label(root,textvariable=self.status,wraplength=720).pack(anchor="w",pady=(8,0));ttk.Label(root,textvariable=self.detail,wraplength=720).pack(anchor="w",pady=(5,0))
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
        Path(self.folder.get()).mkdir(parents=True,exist_ok=True);self.btn.config(state="disabled");self.progress.set(0);self.status.set("階段 1/3：正在取得影片資訊…");self.detail.set("");self.expected={};threading.Thread(target=self.download,daemon=True).start()
    def hook(self,d):
        if d.get("status")=="downloading":
            total=d.get("total_bytes") or d.get("total_bytes_estimate");done=d.get("downloaded_bytes",0);pct=(done/total*100) if total else 0;speed=d.get("speed") or 0;eta=d.get("eta");name=os.path.basename(d.get("filename",""));info=d.get("info_dict") or {};idx=info.get("playlist_index");count=info.get("n_entries") or info.get("playlist_count");prefix=f"第 {idx}/{count} 部｜" if idx and count else "";sp=f"{speed/1048576:.2f} MB/s" if speed else "--";et=f"{eta//60:02d}:{eta%60:02d}" if isinstance(eta,int) else "--"
            self.after(0,lambda:(self.progress.set(pct),self.status.set(f"階段 2/3：{prefix}下載中 {pct:.1f}%｜{name}"),self.detail.set(f"已下載 {done/1048576:.1f} MB｜速度 {sp}｜剩餘 {et}")))
        elif d.get("status")=="finished":
            mode=self.mode.get();msg="下載完成，準備驗證…" if mode.startswith("原始音訊") else ("音訊下載完成，正在 MP3 轉檔…" if mode.startswith("MP3") else "影音下載完成，正在合併 MP4…")
            self.after(0,lambda:self.status.set("階段 2/3："+msg))
    def probe(self,p):
        q=subprocess.run([resource_path("ffprobe.exe"),"-v","error","-show_entries","format=duration","-of","json",str(p)],capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0));
        if q.returncode:raise RuntimeError("FFprobe 無法讀取成品："+q.stderr.strip())
        return float(json.loads(q.stdout)["format"]["duration"])
    def collect(self,info):
        es=info.get("entries") or [] if info.get("_type")=="playlist" else [info]
        for e in es:
            if e and e.get("id") and e.get("duration"):self.expected[e["id"]]=float(e["duration"])
    def download(self):
        try:
            ff=resource_path("ffmpeg.exe");fp=resource_path("ffprobe.exe")
            if not os.path.isfile(ff) or not os.path.isfile(fp):raise RuntimeError("缺少 FFmpeg/FFprobe，請重新下載最新版。")
            folder=Path(self.folder.get());out=str(folder/"%(playlist_index&{} - |)s%(title)s [%(id)s].%(ext)s")
            base={"outtmpl":out,"windowsfilenames":True,"ignoreerrors":False,"retries":20,"fragment_retries":20,"file_access_retries":10,"extractor_retries":10,"continuedl":True,"part":True,"concurrent_fragment_downloads":1,"progress_hooks":[self.hook],"noplaylist":False,"ffmpeg_location":os.path.dirname(ff),"quiet":False,"overwrites":True}
            with yt_dlp.YoutubeDL({**base,"skip_download":True,"quiet":True}) as y:self.collect(y.extract_info(self.url.get().strip(),download=False))
            mode=self.mode.get();opts=dict(base)
            if mode.startswith("原始音訊"):opts["format"]="bestaudio/best"
            elif mode.startswith("MP3 128k"):opts.update({"format":"bestaudio/best","postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"128"}]})
            elif mode.startswith("MP3 高音質"):opts.update({"format":"bestaudio/best","postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"0"}]})
            else:
                h=None if mode=="MP4 最佳畫質" else (1080 if "1080" in mode else 720);opts["format"]=f"bv*[height<={h}]+ba/b[height<={h}]/b" if h else "bv*+ba/b";opts["merge_output_format"]="mp4"
            with yt_dlp.YoutubeDL(opts) as y:
                code=y.download([self.url.get().strip()])
                if code!=0:raise RuntimeError(f"yt-dlp 回傳錯誤代碼 {code}")
            self.after(0,lambda:self.status.set("階段 3/3：正在驗證成品時長…"))
            checked=[]
            for f in sorted(folder.iterdir(),key=lambda p:p.stat().st_mtime if p.is_file() else 0,reverse=True):
                if not f.is_file() or f.suffix.lower() in [".part",".ytdl",".txt"] or time.time()-f.stat().st_mtime>7200:continue
                vid=next((k for k in self.expected if f"[{k}]" in f.name),None)
                if not vid:continue
                actual=self.probe(f);expected=self.expected[vid];ratio=actual/expected if expected else 1;checked.append((f,expected,actual,ratio))
                if ratio<0.98 or abs(actual-expected)>30:raise RuntimeError(f"成品不完整：{f.name}\n原始 {fmt_time(expected)}｜成品 {fmt_time(actual)}｜完整度 {ratio*100:.1f}%")
            if not checked:raise RuntimeError("找不到可驗證的成品，已取消完成判定。")
            summary="；".join(f"{f.name}: {fmt_time(a)}/{fmt_time(e)} ✓" for f,e,a,_ in checked[:3]);self.after(0,lambda:self.done(summary))
        except Exception as e:
            err=str(e)
            try:(Path(self.folder.get())/"download-error.txt").write_text(err,encoding="utf-8")
            except:pass
            self.after(0,lambda:self.fail(err))
    def done(self,s):self.progress.set(100);self.status.set("全部完成 ✓");self.detail.set(s);self.btn.config(state="normal");messagebox.showinfo("完成","下載與時長驗證通過。\n\n"+s)
    def fail(self,e):self.status.set("下載或驗證失敗");self.detail.set(e);self.btn.config(state="normal");messagebox.showerror("未完成",e+"\n\n錯誤已寫入 download-error.txt")
if __name__=="__main__":App().mainloop()
