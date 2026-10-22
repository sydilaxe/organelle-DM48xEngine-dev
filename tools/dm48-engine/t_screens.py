import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0,'.')
from harness import run
from oledemu import render
P="../DM48 Engine"; OUT="../shots"; os.makedirs(OUT, exist_ok=True)
ev=[]
def key(t,n): ev.append((t,f"notesRaw {n} 100")); ev.append((t+40,f"notesRaw {n} 0"))
def snap(t,name): ev.append((t,f"snap symbol {name}"))
def tap(t): ev.append((t,"aux 1")); ev.append((t+50,"aux 0"))
t=600
ev.append((t-100,"eng-in 0 2 60 90"))
for k in range(60): ev.append((t-100+k*20, f"eng-in 4 2 11 {60+k}"))
snap(t+300,"page_play")
ev.append((t+350,"notesRaw 67 100")); ev.append((t+390,"notesRaw 67 0")); ev.append((t+420,"knob1 0.09")); snap(t+480,"page_tune_scale"); ev.append((t+490,"notesRaw 60 100")); ev.append((t+495,"notesRaw 60 0"))
for name,k in (("shape",62),("fx",64),("setup",65),("tune",67),("engine",69),("library",61)):
    t+=500; key(t,k); snap(t+300,"page_"+name)
t+=500; key(t,60)
tap(t+200); snap(t+700,"loop_rec"); tap(t+1700); snap(t+2400,"loop_play"); tap(t+2600); snap(t+3200,"loop_dub")
tap(t+3400)
ev.append((t+3600,"notesRaw 71 100")); ev.append((t+3650,"knob1 0.25")); snap(t+3800,"loop_reverse_toast"); ev.append((t+3700,"notesRaw 71 0"))
snap(t+5500,"loop_reverse")
ev.append((t+5550,"notesRaw 73 100")); snap(t+5650,"throw"); ev.append((t+5700,"notesRaw 73 0"))
key(t+5700,78); snap(t+5900,"arp_toast")
ev.append((t+6000,"eng-in 0 3 64 90")); snap(t+6800,"arp_on")
key(t+7000,69); ev.append((t+7100,"eng-in 4 3 11 99")); snap(t+7400,"engine_monitor")
key(t+7600,72); snap(t+7700,"freeze")
log = run(P, ev, extra_prints=["oscOut","SNAP"])
open(OUT+"/log.txt","w").write(log)
print(render(log.replace("snap: ","SNAP: "), OUT))
