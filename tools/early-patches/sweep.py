# usage: sweep.py <patchdir> <cutoffknob>  -> renders a breath swell, prints spectral centroid vs breath
import sys, os, shutil, subprocess, numpy as np
src, knob = sys.argv[1], float(sys.argv[2])
d = 'sw'; shutil.rmtree(d, ignore_errors=True); shutil.copytree(src, d); shutil.copy('test/test.pd', d)
ev = [f"0 knob1 {knob};", "0 knob4 0;", "300 mpe-in-note 57 40 2;"]
for i in range(101):  # breath 1..127..1 over 4 s
    v = int(1 + 126 * (1 - abs(i - 50) / 50))
    ev.append(f"40 mpe-in-cc {v} 2 2;")
ev += ["0 mpe-in-note 57 0 2;", "300 stoprec bang;", "0 pd quit;"]
open(f'{d}/events.txt', 'w').write("\n".join(ev) + "\n")
subprocess.run(['pd', '-nosound', '-nomidi', '-batch', '-open', 'test.pd'], cwd=d, capture_output=True, timeout=60)
b = open(f'{d}/test.wav', 'rb').read(); i = b.index(b'data') + 8; sr = 44100
x = np.frombuffer(b[i:i + ((len(b) - i) // 4) * 4], dtype=np.int16).reshape(-1, 2).astype(float).mean(1) / 32768
out = []
for k, t in enumerate(np.arange(0.4, 4.3, 0.4)):
    seg = x[int(t * sr):int((t + 0.1) * sr)]
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1 / sr)
    breath = int(1 + 126 * (1 - abs((t - 0.3) / 0.04 - 50) / 50))
    out.append(f"br{max(breath,1):3d}:{(S*f).sum()/S.sum():5.0f}Hz")
print(f"cutoff knob {knob}: " + "  ".join(out))
