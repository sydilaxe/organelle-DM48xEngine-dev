import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio
P="../DM48 Engine"; sr=44100
names=["halo","lyra","steel","under","velvet","volt"]
for name in sys.argv[1:]:
    i=names.index(name)
    ev=[(100,"notesRaw 69 100"),(150,"notesRaw 69 0"),(200,f"knob1 {(i+0.5)/6}"),(300,"notesRaw 60 100"),(350,"notesRaw 60 0"),
        (400,"notesRaw 64 100"),(450,"notesRaw 64 0"),(500,"knob4 0.5"),(510,"knob4 0.0"),(520,"knob3 0.5"),(530,"knob3 0.0"),
        (600,"eng-in 0 2 93 100"),(601,"eng-in 4 2 11 127"),(2600,"eng-in 0 2 93 0")]
    run(P,ev); x=audio(P).mean(1)[int(1.2*sr):int(2.4*sr)]
    S=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2; fr=np.fft.rfftfreq(len(x),1/sr)
    f0=440*2**((93-69)/12); h=np.round(fr/f0); near=np.abs(fr-h*f0)<f0*0.03
    # energy away from harmonics (incl. detune neighbours excluded by 3% window)
    print(f"{name}: non-harmonic energy {10*np.log10(S[~near & (fr>100)].sum()/S[near].sum()):.1f} dB rel. harmonics")
