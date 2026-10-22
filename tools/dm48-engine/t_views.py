"""Screenshots of the scope and audio-loop views for the manual."""
import sys, warnings
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run
from oledemu import render
P="../DM48 Engine"; OUT="shots"
ev=[]
def key(t,n,hold=60): ev.extend([(t,f"notesRaw {n} 100"),(t+hold,f"notesRaw {n} 0")])
def note(t,ch,n,dur,br=100): ev.extend([(t,f"eng-in 0 {ch} {n} 100"),(t+1,f"eng-in 4 {ch} 11 {br}"),(t+dur,f"eng-in 0 {ch} {n} 0")])
key(500,81); note(600,2,57,900); note(1700,3,64,600); key(3000,81)     # an audio take with two notes
note(3500,2,57,3000,90)
key(4000,80); ev.append((4600,"snap symbol view_scope"))
key(5000,80); ev.append((6200,"snap symbol view_loop"))
key(6500,60)
log=run(P,ev,extra_prints=["oscOut","SNAP"])
print(render(log.replace("snap: ","SNAP: "), OUT))
