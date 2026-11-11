"""Run DM48 Engine offline with a list of timed events; record audio + printed messages."""
import os, sys, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdgen import Canvas
# the engines as they appear on the ENGINE knob (sorted file names); knob value that selects one
from gen_engines import engine_names
ENGINE_NAMES = engine_names()


def eng_knob(name):
    return (ENGINE_NAMES.index(name) + 0.5) / len(ENGINE_NAMES)


PRINTS = ["screenLine1", "screenLine2", "screenLine3", "screenLine4", "screenLine5", "led", "LOAD", "dmx-sent",
          "eng-loopstat", "midiOutGate", "eng-load", "snap"]
def run(patchdir, events, wav="h.wav", extra_prints=()):
    """events: list of (time_ms, 'receiver args')"""
    d = os.path.join(patchdir)
    # reset settings (auto-save writes into the patch folder during a run)
    from sec_ui import DEFAULT_LINE
    open(os.path.join(d, "settings.txt"), "w").write(DEFAULT_LINE + ";\n")
    open(os.path.join(d, "engines.txt"), "w").write("")
    ev = sorted(events, key=lambda e: e[0])
    out, prev = [], 0
    for t, s in ev:
        out.append(f"{t - prev} {s};"); prev = t
    out.append("300 stoprec bang;"); out.append("0 pd quit;")
    open(os.path.join(d, "h_events.txt"), "w").write("\n".join(out) + "\n")
    c = Canvas()
    lb = c.obj("loadbang", 20, 20)
    tb = c.obj("t b b b", 20, 45); c.c(lb, 0, tb, 0)
    dsp = c.msg("; pd dsp 1", 200, 70); c.c(tb, 2, dsp, 0)
    wm = c.msg(f"open {wav}, start", 300, 70); c.c(tb, 1, wm, 0)
    qm = c.msg("read h_events.txt, tempo 1 msec, bang", 20, 70); c.c(tb, 0, qm, 0)
    ws = c.obj("writesf~ 2", 300, 150); c.c(wm, 0, ws, 0)
    q = c.obj("qlist", 20, 150); c.c(qm, 0, q, 0)
    cl = c.obj("catch~ outL", 300, 100); cr = c.obj("catch~ outR", 400, 100)
    c.c(cl, 0, ws, 0); c.c(cr, 0, ws, 1)
    sr = c.obj("r stoprec", 500, 100); sm = c.msg("stop", 500, 125); c.c(sr, 0, sm, 0); c.c(sm, 0, ws, 0)
    c.obj("main", 20, 250)
    for n in list(PRINTS) + list(extra_prints):
        r = c.obj("r " + n); p = c.obj("print " + n); c.c(r, 0, p, 0)
    c.save(os.path.join(d, "h_test.pd"))
    # Pd 0.54 very rarely dies right after start-up in CI (an empty recording, seen once in hundreds of runs,
    # never reproduced). Say so in the log, with Pd's exit code and last output, and run it once more.
    for attempt in (1, 2):
        if os.path.exists(os.path.join(d, wav)):
            os.remove(os.path.join(d, wav))          # so an old recording can't pass for this one
        res = subprocess.run(["pd", "-nosound", "-nomidi", "-batch", "-stderr", "-open", "h_test.pd"], cwd=d,
                             capture_output=True, text=True, timeout=120)
        try:
            ok = res.returncode == 0 and b"data" in open(os.path.join(d, wav), "rb").read(4096)
        except OSError:
            ok = False
        if ok or attempt == 2:
            return res.stderr
        print(f"WARN  Pd exited with code {res.returncode} and no recording; running it again. "
              f"Last output: {res.stderr[-400:]!r}", file=sys.stderr, flush=True)

def audio(patchdir, wav="h.wav"):
    import numpy as np
    b = open(os.path.join(patchdir, wav), "rb").read(); i = b.index(b"data") + 8
    return np.frombuffer(b[i:i + ((len(b) - i) // 4) * 4], dtype=np.int16).reshape(-1, 2).astype(float) / 32768

def f0(seg, sr=44100, lo=40, hi=2000):
    import numpy as np
    seg = seg * np.hanning(len(seg)); N = 1 << 18
    S = np.abs(np.fft.rfft(seg, N)); hps = S.copy()
    for h in (2, 3):
        dd = S[::h]; hps[:len(dd)] *= dd
    f = np.fft.rfftfreq(N, 1 / sr); m = (f > lo) & (f < hi)
    return f[np.argmax(hps * m)]

def centroid(seg, sr=44100):
    import numpy as np
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1 / sr)
    return (S * f).sum() / max(S.sum(), 1e-9)
