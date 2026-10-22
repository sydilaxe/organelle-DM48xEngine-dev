import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio, centroid
P="../DM48 Engine"; sr=44100
names=["halo","lyra","steel","under","velvet","volt"]
def k(n): return (names.index(n)+0.5)/6
ev=[(300,"eng-in 0 2 57 100"),(301,"eng-in 4 2 11 100"),(302,"eng-in 0 3 64 100"),(303,"eng-in 4 3 11 100"),
    (500,"notesRaw 69 100"),(550,"notesRaw 69 0"),          # ENGINE page
    (600,"knob1 0.79"),                                      # first touch only records the knob
    (2000,f"knob1 {k('halo')}"),                             # -> halo (after 350 ms rest)
    (5000,f"knob1 {k('lyra')}"),(5100,f"knob1 {k('steel')}"),(5200,f"knob1 {k('volt')}"),  # quick browse
    (11000,"eng-in 0 2 57 0"),(11001,"eng-in 0 3 64 0"),(12500,"knob2 0.5")]
log=run(P,ev,extra_prints=["eng-xfade","eng-slupd"])
print([l for l in log.splitlines() if "error" in l.lower() or "fail" in l][:5])
print([l for l in log.splitlines() if l.startswith(("eng-load","eng-xfade"))])
x=audio(P).mean(1)
for t in np.arange(1.0, 11.0, 0.5):
    s=x[int(t*sr):int((t+0.25)*sr)]
    print(f"{t:4.1f}s rms {20*np.log10(np.sqrt((s**2).mean())+1e-9):6.1f} dB  centroid {centroid(s):6.0f}")
