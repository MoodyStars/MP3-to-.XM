"""
Audio analysis and slice preview/export helpers.
- analyze_onsets: detect slices (onset detection via librosa)
- preview_slice: play a slice using pydub (requires ffmpeg)
- extract_slice_samples: return numpy PCM data for a slice
"""
import numpy as np
from pydub import AudioSegment
import librosa
import soundfile as sf
import tempfile
import os
import sys
import math
import subprocess

class AudioConverter:
    def analyze_onsets(self, mp3_path, sr=22050, mono=True, hop_length=512):
        """
        Load file and detect onsets. Returns list of (start_sec, end_sec).
        We'll create slices between onsets; the last slice ends at audio end.
        """
        y, sr_actual = librosa.load(mp3_path, sr=sr, mono=mono)
        onsets = librosa.onset.onset_detect(y=y, sr=sr_actual, hop_length=hop_length, backtrack=True)
        times = librosa.frames_to_time(onsets, sr=sr_actual, hop_length=hop_length)
        times = list(times)
        # ensure start at 0
        if not times or times[0] > 0.05:
            times.insert(0, 0.0)
        # append end
        duration = librosa.get_duration(y=y, sr=sr_actual)
        if not times or abs(times[-1] - duration) > 0.05:
            times.append(duration)
        slices = []
        for i in range(len(times)-1):
            start = float(times[i])
            end = float(times[i+1])
            # filter very small slices
            if end - start >= 0.025:
                slices.append((start, end))
        return slices

    def preview_slice(self, mp3_path, slice_tuple):
        """
        Play a slice quickly using pydub AudioSegment (blocks until complete).
        """
        start, end = slice_tuple
        seg = AudioSegment.from_file(mp3_path)
        ms_start = int(start * 1000)
        ms_end = int(end * 1000)
        chunk = seg[ms_start:ms_end]
        # play - pydub doesn't include player; use simple temporary export to play via default system player
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        chunk.export(tmp.name, format="wav")
        # open using system default player (blocking)
        if sys.platform.startswith("darwin"):
            subprocess.call(["afplay", tmp.name])
        elif sys.platform.startswith("linux"):
            # try aplay (may not exist), else use ffplay
            try:
                subprocess.call(["aplay", tmp.name])
            except:
                subprocess.call(["ffplay", "-nodisp", "-autoexit", tmp.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform.startswith("win"):
            # use PowerShell to play
            subprocess.call(["powershell", "-c", f"(New-Object Media.SoundPlayer '{tmp.name}').PlaySync();"])
        else:
            # fallback to ffplay
            subprocess.call(["ffplay", "-nodisp", "-autoexit", tmp.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.unlink(tmp.name)

    def extract_slice_samples(self, mp3_path, slice_tuple, sr=22050, mono=True):
        """
        Return a numpy int16 array of PCM samples for the requested slice, resampled to sr.
        """
        start, end = slice_tuple
        y, sr_actual = librosa.load(mp3_path, sr=sr, mono=mono, offset=start, duration=(end-start))
        # convert float32 in [-1,1] to int16
        y = np.clip(y, -1.0, 1.0)
        pcm = (y * 32767.0).astype(np.int16)
        # If mono, ensure shape (n,)
        if pcm.ndim > 1:
            pcm = np.mean(pcm, axis=0).astype(np.int16)
        return pcm, sr

    def write_wav_temp(self, pcm, sr):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        sf.write(tmp.name, pcm.astype('int16'), sr, subtype='PCM_16')
        return tmp.name