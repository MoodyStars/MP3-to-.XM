"""
Simple remixer:
- generate_plan: maps slices to notes (slice index -> note number)
- export_xm: assembles samples and pattern data and writes XM via xm_writer
"""
import numpy as np
from xm_writer import XMWriter
from converter import AudioConverter

# Simple mapping: assign each slice to a note in a scale.
BASE_NOTE = 48  # C-4 in XM period table mapping we will use as note numbers (1..96 range in XM)
SCALE_STEPS = [0, 2, 4, 5, 7, 9, 11]  # major scale intervals

class AutoRemixer:
    def __init__(self):
        self.conv = AudioConverter()

    def generate_plan(self, mp3_path, slices, bpm=None):
        """
        Create a simple plan: for each slice, pick a pitch (cycle through scale),
        assign to a pattern and row. Return a plan containing notes and pattern structure.
        plan = {
            'samples': [ { 'slice_idx': int, 'sample_data': np.int16, 'sr': int } ],
            'notes': [ (slice_idx, note_number, pattern_index, row) ... ],
            'patterns_count': n,
            'channels': 4,
            'song_length': m
        }
        """
        samples = []
        notes = []
        # collect samples (convert slices to raw PCM)
        for i, s in enumerate(slices):
            pcm, sr = self.conv.extract_slice_samples(mp3_path, s, sr=22050, mono=True)
            samples.append({'slice_idx': i, 'pcm': pcm, 'sr': sr})

        # decide channels and patterns
        channels = 4
        patterns_count = 4
        rows_per_pattern = 64

        # map slices to notes across patterns somewhat musically
        for i, sample_info in enumerate(samples):
            # pitch selection: cycle through SCALE_STEPS in successive octaves
            step = SCALE_STEPS[i % len(SCALE_STEPS)]
            octave = (i // len(SCALE_STEPS))  # 0,1,...
            note = BASE_NOTE + step + octave*12
            pat = (i % patterns_count)
            row = (i * 8) % rows_per_pattern
            notes.append((sample_info['slice_idx'], note, pat, row))

        plan = {
            'samples': samples,
            'notes': notes,
            'patterns_count': patterns_count,
            'channels': channels,
            'rows_per_pattern': rows_per_pattern,
            'song_length': patterns_count
        }
        return plan

    def export_xm(self, mp3_path, plan, out_path, sr=22050, mono=True):
        """
        Build an XM using XMWriter. For each sample in plan, add as an instrument sample.
        Pattern data is assembled using simple note placements without effects.
        """
        # assemble sample list (the XMWriter will expect 16-bit PCM np arrays)
        samples = []
        for s in plan['samples']:
            # ensure sample has requested sr and mono; our extractor already resampled
            pcm = s['pcm']
            samples.append(pcm)

        # create pattern matrix: patterns_count x rows x channels of note dicts
        patterns = []
        patterns_count = plan['patterns_count']
        rows = plan['rows_per_pattern']
        channels = plan['channels']
        # initialize empty
        for _ in range(patterns_count):
            pat = [[None for _ in range(channels)] for _ in range(rows)]
            patterns.append(pat)
        # fill notes
        for note in plan['notes']:
            slice_idx, note_num, pat_idx, row = note
            # pick channel round-robin by slice_idx
            ch = slice_idx % channels
            # XM note numbers are 1..96 typically; cap for safety
            note_field = int(max(1, min(96, note_num)))
            # sample number in XM is 1-based; we use slice_idx+1
            pat = patterns[pat_idx]
            pat[row][ch] = {
                'note': note_field,
                'instrument': slice_idx + 1,
                'volume': 64,  # 0-64
                'effect': 0,
                'effect_param': 0
            }

        # use XMWriter to write module
        writer = XMWriter()
        song_name = os.path.splitext(os.path.basename(out_path))[0]
        # small title and default tempo
        tempo = 125
        bpm = 6
        writer.write_xm(out_path, song_name, samples, patterns, channels=channels, tempo=tempo, bpm=bpm)
        return out_path

import os