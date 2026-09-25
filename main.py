import os, sys, threading, subprocess, json, time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import yt_dlp
APP_NAME="YouTube 下載器・v5 極速版"
def rp(n):return os.path.join(getattr(sys,"_MEIPASS",os.path.dirname(os.path.abspath(__file__))),n)
def ft(s):
    if s is None:return "未知"
    s=int(round(float(s)));h,r=divmod(s,3600);m,s=divmod(r,60);return f"{h:02d}:{m:02d}:{s:02d}"
class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title(APP_NAME);self.geometry("790x580");self.minsize(720,500);self.url=tk.StringVar();self.mode=tk.StringVar(value="原始音訊・極速（推薦做筆記）");self.turbo=tk.BooleanVar(value=True);self.folder=tk.StringVar(value=str(Path.home()/"Downloads"/"YouTube"));self.status=tk.StringVar(value="準備就緒");self.detail=tk.StringVar();self.progress=tk.DoubleVar();self.expected={};self._build()
 def _build(self):
  r=ttk.Frame(self,padding=22);r.pack(fill="both",expand=True);ttk.Label(r,text="YouTube 下載器 v5 極速版",font=("Microsoft JhengHei UI",20,"bold")).pack(anchor="w");ttk.Label(r,text="優先避免轉碼／避免影音合併／快速完整性驗證").pack(anchor="w",pady=(2,18));ttk.Label(r,text="YouTube 網址").pack(anchor="w");x=ttk.Frame(r);x.pack(fill="x",pady=(5,14));ttk.Entry(x,textvariable=self.url).pack(side="left",fill="x",expand=True);ttk.Button(x,text="貼上網址",command=self.paste).pack(side="left",padx=(8,0));ttk.Label(r,text="下載格式").pack(anchor="w");ttk.Combobox(r,textvariable=self.mode,state="readonly",values=["原始音訊・極速（推薦做筆記）","MP4 720p・極速單檔","MP3 128k・語音課程","MP3 高音質・音樂","MP4 1080p","MP4 最佳畫質"],width=36).pack(anchor="w",pady=(5,6));ttk.Checkbutton(r,text="⚡ 極速模式（多 fragment 下載＋快速驗證）",variable=self.turbo).pack(anchor="w",pady=(0,14));ttk.Label(r,text="儲存位置").pack(anchor="w");x=ttk.Frame(r);x.pack(fill="x",pady=(5,16));ttk.Entry(x,textvariable=self.folder).pack(side="left",fill="x",expand=True);ttk.Button(x,text="瀏覽",command=self.browse).pack(side="left",padx=(8,0));ttk.Button(x,text="開啟資料夾",command=self.openf).pack(side="left",padx=(8,0));self.btn=ttk.Button(r,text="開始下載",command=self.start);self.btn.pack(fill="x",ipady=8,pady=(0,16));ttk.Progressbar(r,variable=self.progress,maximum=100).pack(fill="x");ttk.Label(r,textvariable=self.status,wraplength=730).pack(anchor="w",pady=(8,0));ttk.Label(r,textvariable=self.detail,wraplength=730).pack(anchor="w",pady=(5,0));ttk.Label(r,text="最快：原始音訊不轉碼；MP4 720p 極速優先下載 YouTube 已含影音的單一檔案。",foreground="#666").pack(anchor="w",pady=(18,0))
 def paste(self):
  try:self.url.set(self.clipboard_get().strip())
  except:pass
 def browse(self):
  p=filedialog.askdirectory(initialdir=self.folder.get() or str(Path.home()));
  if p:self.folder.set(p)
 def openf(self):p=Path(self.folder.get());p.mkdir(parents=True,exist_ok=True);os.startfile(str(p))
 def start(self):
  if not self.url.get().strip():messagebox.showwarning("缺少網址","請先貼上 YouTube 網址。");return
  Path(self.folder.get()).mkdir(parents=True,exist_ok=True);self.btn.config(state="disabled");self.progress.set(0);self.status.set("階段 1/3：取得影片資訊…");self.detail.set("");self.expected={};threading.Thread(target=self.download,daemon=True).start()
 def hook(self,d):
  if d.get("status")=="downloading":
   total=d.get("total_bytes") or d.get("total_bytes_estimate");done=d.get("downloaded_bytes",0);pct=done/total*100 if total else 0;speed=d.get("speed") or 0;eta=d.get("eta");info=d.get("info_dict") or {};idx=info.get("playlist_index");cnt=info.get("n_entries") or info.get("playlist_count");pre=f"第 {idx}/{cnt} 部｜" if idx and cnt else "";sp=f"{speed/1048576:.2f} MB/s" if speed else "--";et=f"{eta//60:02d}:{eta%60:02d}" if isinstance(eta,int) else "--";self.after(0,lambda:(self.progress.set(pct),self.status.set(f"階段 2/3：{pre}下載 {pct:.1f}%"),self.detail.set(f"{done/1048576:.1f} MB｜{sp}｜剩餘 {et}")))
  elif d.get("status")=="finished":
   m=self.mode.get();msg="下載完成，直接驗證…" if m.startswith("原始音訊") or m.startswith("MP4 720p") else ("正在快速轉成 MP3…" if m.startswith("MP3") else "正在無轉碼合併影音…");self.after(0,lambda:self.status.set("階段 2/3："+msg))
 def probe(self,p):
  q=subprocess.run([rp("ffprobe.exe"),"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)],capture_output=True,text=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),timeout=30)
  if q.returncode:raise RuntimeError("無法驗證成品："+q.stderr.strip())
  return float(q.stdout.strip())
 def collect(self,i):
  es=(i.get("entries") or []) if i.get("_type")=="playlist" else [i]
  for e in es:
   if e and e.get("id") and e.get("duration"):self.expected[e["id"]]=float(e["duration"])
 def download(self):
  try:
   ff=rp("ffmpeg.exe");fp=rp("ffprobe.exe")
   if not os.path.isfile(ff) or not os.path.isfile(fp):raise RuntimeError("缺少 FFmpeg/FFprobe。")
   folder=Path(self.folder.get());out=str(folder/"%(playlist_index&{} - |)s%(title)s [%(id)s].%(ext)s");turbo=self.turbo.get();base={"outtmpl":out,"windowsfilenames":True,"ignoreerrors":False,"retries":20,"fragment_retries":20,"continuedl":True,"part":True,"concurrent_fragment_downloads":4 if turbo else 1,"progress_hooks":[self.hook],"noplaylist":False,"ffmpeg_location":os.path.dirname(ff),"quiet":False,"overwrites":True}
   with yt_dlp.YoutubeDL({**base,"skip_download":True,"quiet":True}) as y:self.collect(y.extract_info(self.url.get().strip(),download=False))
   m=self.mode.get();o=dict(base)
   if m.startswith("原始音訊"):o["format"]="bestaudio[ext=m4a]/bestaudio/best"
   elif m.startswith("MP4 720p"):o["format"]="best[ext=mp4][height<=720][vcodec!=none][acodec!=none]/best[height<=720][vcodec!=none][acodec!=none]/bv*[height<=720]+ba/b[height<=720]";o["merge_output_format"]="mp4"
   elif m.startswith("MP3 128k"):o.update({"format":"bestaudio[ext=m4a]/bestaudio/best","postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"128"}]})
   elif m.startswith("MP3 高音質"):o.update({"format":"bestaudio/best","postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"0"}]})
   else:
    h=1080 if "1080" in m else None;o["format"]=f"bv*[height<={h}]+ba/b[height<={h}]/b" if h else "bv*+ba/b";o["merge_output_format"]="mp4"
   with yt_dlp.YoutubeDL(o) as y:
    if y.download([self.url.get().strip()])!=0:raise RuntimeError("yt-dlp 下載失敗")
   self.after(0,lambda:self.status.set("階段 3/3：快速驗證時長…"));checked=[]
   for f in sorted(folder.iterdir(),key=lambda p:p.stat().st_mtime if p.is_file() else 0,reverse=True):
    if not f.is_file() or f.suffix.lower() in [".part",".ytdl",".txt"] or time.time()-f.stat().st_mtime>7200:continue
    vid=next((k for k in self.expected if f"[{k}]" in f.name),None)
    if not vid:continue
    actual=self.probe(f);expected=self.expected[vid];ratio=actual/expected if expected else 1;checked.append((f,expected,actual));
    if ratio<.98 or abs(actual-expected)>30:raise RuntimeError(f"成品不完整：{f.name}\n原始 {ft(expected)}｜成品 {ft(actual)}")
   if not checked:raise RuntimeError("找不到可驗證成品。")
   s="；".join(f"{f.name}: {ft(a)}/{ft(e)} ✓" for f,e,a in checked[:3]);self.after(0,lambda:self.done(s))
  except Exception as e:
   er=str(e)
   try:(Path(self.folder.get())/"download-error.txt").write_text(er,encoding="utf-8")
   except:pass
   self.after(0,lambda:self.fail(er))
 def done(self,s):self.progress.set(100);self.status.set("全部完成 ✓");self.detail.set(s);self.btn.config(state="normal");messagebox.showinfo("完成","極速下載與驗證完成。\n\n"+s)
 def fail(self,e):self.status.set("失敗");self.detail.set(e);self.btn.config(state="normal");messagebox.showerror("未完成",e+"\n\n錯誤已寫入 download-error.txt")
if __name__=="__main__":App().mainloop()
