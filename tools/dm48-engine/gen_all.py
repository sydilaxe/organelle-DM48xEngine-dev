import os, sys, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_voice, gen_engines, gen_main
OUT = sys.argv[1]
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
gen_voice.build(OUT)
gen_voice.build_ehost(OUT)
gen_engines.build(OUT)
gen_main.build(OUT)
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_scales.py"),
                os.path.join(OUT, "tunings")], check=True, capture_output=True)
import sec_ui
open(os.path.join(OUT, "settings.txt"), "w").write(sec_ui.DEFAULT_LINE + ";\n")
open(os.path.join(OUT, "engines.txt"), "w").write("")
open(os.path.join(OUT, "scales.txt"), "w").write("".join(n + ";\n" for n in sec_ui.SCALE_NAMES))
from readme_text import README
open(os.path.join(OUT, "README.txt"), "w").write(README)
print("built", OUT)
