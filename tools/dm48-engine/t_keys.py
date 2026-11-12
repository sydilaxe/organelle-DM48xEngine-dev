import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run
P="../DM48 Engine"
ev=[]
def key(t, n, hold=50): ev.append((t, f"notesRaw {n} 100")); ev.append((t+hold, f"notesRaw {n} 0"))
key(300, 62)            # D -> SHAPE page
ev.append((500, "knob1 0.9"))   # Breath>Tone on SHAPE
key(700, 64)            # E -> FX
key(900, 72)            # C5 freeze on
key(1100, 72)           # off
key(1300, 75)           # octave up
key(1500, 77); key(2000, 77)    # tap tempo 500 ms
ev.append((2200, "notesRaw 72 100")); ev.append((2250, "knob2 0.8")); ev.append((2300, "notesRaw 72 0"))  # combo: reverb size
key(2500, 61)           # LIBRARY
key(2800, 60)           # PLAY
ev.append((3000, "knob1 0.2"))  # plain knob: PLAY param
log = run(P, ev, extra_prints=["eng-page","eng-frz-tap","eng-frz-off","eng-octshift","eng-dtime-ms","eng-rsize","eng-p1","eng-bamt"])
for l in log.splitlines():
    if not l.startswith(("screenLine2","screenLine3","screenLine4","led","midiOutGate")): print(l)
