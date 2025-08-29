#!/usr/bin/env python3
"""
Simple Tk GUI: load MP3, analyze, preview slices, auto-remix, export .xm
Prototype — depends on pydub, librosa, soundfile, numpy
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os

from converter import AudioConverter
from remixer import AutoRemixer

APP_TITLE = "MP3 -> XM Remixer (Prototype)"

class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("700x420")
        self.converter = AudioConverter()
        self.remixer = AutoRemixer()

        # UI components
        frm = ttk.Frame(root, padding=10)
        frm.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(fill="x", pady=(0,10))

        self.load_btn = ttk.Button(btn_frame, text="Load MP3", command=self.load_mp3)
        self.load_btn.pack(side="left")

        self.analyze_btn = ttk.Button(btn_frame, text="Analyze", command=self.analyze, state="disabled")
        self.analyze_btn.pack(side="left", padx=6)

        self.remix_btn = ttk.Button(btn_frame, text="Generate Remix", command=self.generate_remix, state="disabled")
        self.remix_btn.pack(side="left", padx=6)

        self.export_btn = ttk.Button(btn_frame, text="Export XM", command=self.export_xm, state="disabled")
        self.export_btn.pack(side="left", padx=6)

        self.preview_btn = ttk.Button(btn_frame, text="Preview Slice", command=self.preview_slice, state="disabled")
        self.preview_btn.pack(side="left", padx=6)

        # Settings
        settings = ttk.LabelFrame(frm, text="Settings")
        settings.pack(fill="x", pady=(0,10))

        ttk.Label(settings, text="Target sample rate:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.sr_var = tk.IntVar(value=22050)
        ttk.Entry(settings, textvariable=self.sr_var, width=8).grid(row=0, column=1, sticky="w")

        ttk.Label(settings, text="Channels (mono=1):").grid(row=0, column=2, sticky="w", padx=6)
        self.ch_var = tk.IntVar(value=1)
        ttk.Entry(settings, textvariable=self.ch_var, width=6).grid(row=0, column=3, sticky="w")

        ttk.Label(settings, text="BPM (optional):").grid(row=0, column=4, sticky="w", padx=6)
        self.bpm_var = tk.StringVar(value="")
        ttk.Entry(settings, textvariable=self.bpm_var, width=8).grid(row=0, column=5, sticky="w")

        # Slices list
        list_frame = ttk.LabelFrame(frm, text="Detected slices")
        list_frame.pack(fill="both", expand=True)

        self.slice_list = tk.Listbox(list_frame, selectmode="browse")
        self.slice_list.pack(side="left", fill="both", expand=True, padx=(6,0), pady=6)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.slice_list.yview)
        scrollbar.pack(side="left", fill="y", padx=(0,6), pady=6)
        self.slice_list.config(yscrollcommand=scrollbar.set)

        # Status bar
        self.status = tk.StringVar(value="Ready")
        statusbar = ttk.Label(root, textvariable=self.status, relief="sunken", anchor="w")
        statusbar.pack(fill="x", side="bottom")

        self.loaded_path = None
        self.slices = []
        self.remix_plan = None

    def set_status(self, text):
        self.status.set(text)
        self.root.update_idletasks()

    def load_mp3(self):
        path = filedialog.askopenfilename(title="Select MP3", filetypes=[("MP3 files","*.mp3"), ("All files","*.*")])
        if not path:
            return
        self.loaded_path = path
        self.set_status(f"Loaded: {os.path.basename(path)}")
        self.analyze_btn.config(state="normal")
        self.remix_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        self.preview_btn.config(state="disabled")
        self.slice_list.delete(0, tk.END)
        self.slices = []

    def analyze(self):
        if not self.loaded_path:
            messagebox.showerror("No file", "Load an MP3 first.")
            return
        self.set_status("Analyzing — detecting onsets (this may take a few seconds)...")
        self.analyze_btn.config(state="disabled")
        def work():
            try:
                sr = int(self.sr_var.get())
                ch = int(self.ch_var.get())
                slices = self.converter.analyze_onsets(self.loaded_path, sr=sr, mono=(ch==1))
                self.slices = slices
                self.slice_list.delete(0, tk.END)
                for i, s in enumerate(slices):
                    start, end = s
                    self.slice_list.insert(tk.END, f"Slice {i}: {start:.3f}s — {end:.3f}s")
                self.set_status(f"Analysis complete: {len(slices)} slices")
                self.remix_btn.config(state="normal" if slices else "disabled")
                self.preview_btn.config(state="normal" if slices else "disabled")
            except Exception as e:
                messagebox.showerror("Error analyzing audio", str(e))
                self.set_status("Error during analysis")
            finally:
                self.analyze_btn.config(state="normal")
        threading.Thread(target=work, daemon=True).start()

    def preview_slice(self):
        sel = self.slice_list.curselection()
        if not sel:
            messagebox.showinfo("Select slice", "Select a slice to preview.")
            return
        idx = sel[0]
        slice_info = self.slices[idx]
        self.set_status(f"Previewing slice {idx}...")
        def work():
            try:
                self.converter.preview_slice(self.loaded_path, slice_info)
                self.set_status("Preview finished")
            except Exception as e:
                messagebox.showerror("Preview error", str(e))
                self.set_status("Preview error")
        threading.Thread(target=work, daemon=True).start()

    def generate_remix(self):
        if not self.slices:
            messagebox.showerror("No slices", "Analyze the audio first.")
            return
        bpm = None
        try:
            bpm_text = self.bpm_var.get().strip()
            if bpm_text:
                bpm = float(bpm_text)
        except:
            messagebox.showwarning("BPM", "Invalid BPM, ignoring.")
            bpm = None
        self.set_status("Generating remix plan...")
        try:
            plan = self.remixer.generate_plan(self.loaded_path, self.slices, bpm=bpm)
            self.remix_plan = plan
            # display plan summary in list
            self.slice_list.delete(0, tk.END)
            for i, note in enumerate(plan['notes']):
                sidx, pitch, pattern, row = note
                self.slice_list.insert(tk.END, f"Note {i}: slice {sidx} -> pitch {pitch} pat{pattern} row{row}")
            self.set_status("Remix plan generated")
            self.export_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("Remix error", str(e))
            self.set_status("Remix error")

    def export_xm(self):
        if not self.remix_plan:
            messagebox.showerror("No remix", "Generate a remix plan first.")
            return
        out = filedialog.asksaveasfilename(title="Export XM", defaultextension=".xm", filetypes=[("XM module", "*.xm")])
        if not out:
            return
        self.set_status("Exporting XM (this may take a moment)...")
        def work():
            try:
                self.remixer.export_xm(self.loaded_path, self.remix_plan, out,
                                       sr=int(self.sr_var.get()), mono=(int(self.ch_var.get())==1))
                self.set_status(f"XM exported: {os.path.basename(out)}")
                messagebox.showinfo("Export complete", f"Wrote {out}")
            except Exception as e:
                messagebox.showerror("Export error", str(e))
                self.set_status("Export error")
        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()