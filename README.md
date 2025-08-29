# mp3-to-xm-remixer

Prototype Python GUI app that loads an MP3, slices/analyzes it, provides a simple remixer/cover generation, and exports a minimal FastTracker II XM module (.xm).

This project is a starting point and intentionally small. The XM writer implements a compact subset of the XM format (enough for basic trackers to load a one-instrument module with patterns and 16-bit PCM samples). More advanced XM features (multiple instruments with complex envelopes, per-note sample offsets, advanced effects) are not implemented yet.

Requirements
- Python 3.8+
- ffmpeg/avlib installed on your system (pydub requires ffmpeg to load mp3)
- pip packages (see requirements.txt)

Install
1. Create a venv (recommended):
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   venv\Scripts\activate      # Windows

2. Install requirements:
   pip install -r requirements.txt

Quick usage
1. Run the GUI:
   python main.py

2. In the GUI:
   - Click "Load MP3" to select an MP3 file.
   - Click "Analyze" to detect beats/slices and list slices.
   - Optionally preview slices.
   - Click "Generate Remix" to auto-map slices into patterns.
   - Click "Export XM" to write a .xm file.

Limitations & Notes
- This is a prototype. The XM writer writes a minimal valid XM module (single instrument). Some trackers may reject more complex patterns/effects.
- Audio slicing uses beat onsets detected with librosa. Results depend on the input material.
- pydub requires ffmpeg executable on PATH.
- For better results you can preprocess/stem your source audio (vocals/instruments separated) and import individual stems.

If you'd like:
- Multi-instrument XM export (map stems to different instruments)
- MIDI mapping instead of raw slices
- Save pattern editor UI (visual arrangement)
- Larger modules with more channels/patterns

I can implement any of the above — tell me which direction you prefer.
```
