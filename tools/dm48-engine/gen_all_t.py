import os, sys, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_voice, gen_engines, gen_main_t as gen_main
OUT = sys.argv[1]
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
gen_voice.build(OUT)
gen_engines.build(OUT)
gen_main.build(OUT)
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_scales.py"),
                os.path.join(OUT, "tunings")], check=True, capture_output=True)
import sec_ui
open(os.path.join(OUT, "settings.txt"), "w").write(" ".join(str(d) for d in sec_ui.DEFAULTS) + " velvet;\n")
open(os.path.join(OUT, "engines.txt"), "w").write("")
print("built", OUT)
