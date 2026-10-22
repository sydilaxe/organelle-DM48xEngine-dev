import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio
P="../DM48 Engine"; sr=44100
ev=[(500,"eng-proc 0 18 60 100"),(501,"eng-proc 4 18 11 100"),(800,"eng-proc 0 18 60 100"),
    (1200,"eng-proc 0 18 60 0"),          # one note-off for two note-ons
    (1300,"eng-loop-clear bang"),           # clear sends offs for held loop notes
    (6000,"knob1 0.3")]
log=run(P,ev); x=audio(P).mean(1)
print("errors", [l for l in log.splitlines() if "error" in l][:3])
for t in (1.0, 2.0, 5.0):
    s=x[int(t*sr):int((t+0.5)*sr)]; print(f"t={t}s rms {np.sqrt((s**2).mean()):.4f}")
