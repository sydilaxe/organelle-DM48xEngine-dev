"""Assemble main.pd for DM48 Engine."""
import os
from pdgen import Canvas
from gen_voice import BEND, JUST
from sec_core import NCH, midi_in, keys, combos, process, monitor, chain, to, msg_to
from sec_looper import looper
from sec_ui import ui, settings
from sec_rest import engine_manager, library, audio, glue, MAXBYTES, MAXEV
from sec_midiout import midi_out, clock
from sec_arp import arp
from sec_oled import oled, rows
from sec_ui import SCALE_TABLE, NSCALES, FAM_START, FAM_COUNT, FAM_OF


def build(out_dir):
    m = Canvas(w=1400, h=900)
    m.comment("DM48 Engine - MPE synth host + MIDI looper + DM48X tuning library for the Organelle", 20, 5)
    m.comment("Engines are plug-in voice patches in engines/ (see engines/README.txt). Tunings live in tunings/.", 20, 22)
    m.comment("Keys: see README.txt. Aux / footswitch: tap = rec > play > overdub > play ... hold = clear.", 20, 39)
    y = 90
    for nm, size in ((BEND, NCH), (JUST, 12), ("englheld", NCH * 128), ("engkeyon", NCH * 128), ("englive", 17 * 128),
                     ("dmxb", MAXBYTES), ("dmxt", MAXEV), ("dmxs", MAXEV), ("dmx1", MAXEV), ("dmx2", MAXEV)):
        m.obj(f"array define {nm} {size}", 700, y)
        y += 22
    m.obj(f"array define engscales {NSCALES * 12}", 700, 60)
    for nm, vals in (("engfamstart", FAM_START), ("engfamcount", FAM_COUNT), ("engfamof", FAM_OF)):
        m.obj(f"array define {nm} {len(vals)}", 900, 20 + len(m.items) % 40)
    scl = m.msg("; engscales 0 " + " ".join(str(round(v, 4)) for v in SCALE_TABLE)
                + "; engfamstart 0 " + " ".join(map(str, FAM_START)) + "; engfamcount 0 " + " ".join(map(str, FAM_COUNT))
                + "; engfamof 0 " + " ".join(map(str, FAM_OF)), 700, 40)
    for nm in ("englp", "engfiles", "englist", "engparams", "engdesc", "engarp", "engscalenames"):
        m.obj(f"text define {nm}", 700, y)
        y += 22
    y = 90
    vals = ("engmode engcurve engnr enggr engpage englstate engllen engltop engldub engli englnum englpos "
            "englcpos englclay engcount engsel engpv1 engpv2 engpv3 engpv4 engoctb engocts engmout engsending engrxmute engrsize engfreeze engbeat engheld engmoved englanc englspd englcur englcnt engarpon engarpbr engarpi engarpn engarpdiv engperm engarppat engarpoct engcombok engtunidx enggn enggv "
            "dmxp dmxe dmxr dmxk dmxn dmxc dmxd dmxst dmxi dmxsel dmxcount dmxkey").split()
    for i, nm in enumerate(vals):
        m.obj(f"value {nm}", 950 + (i // 18) * 150, 90 + (i % 18) * 22)
    y = 80
    for c in (midi_in(), keys(), combos(), process(), monitor(), looper(), ui(), settings(), engine_manager(),
              library(), audio(), glue(), midi_out(), clock(), arp(), oled(), rows()):
        m.sub(c, 20, y)
        y += 25
    # ---- start-up, in order (right outlet first)
    st = chain(m, m.obj("loadbang", 300, 80), ["t b b b b b b"], 300, 105)
    to(m, st, "s $0-scan", 300, 300, outlet=5)
    m.c(st, 5, scl, 0)
    msg_to(m, st, "; engscalenames clear; engscalenames read scales.txt", 450, 270, outlet=5)
    to(m, st, "s $0-scanlib", 400, 300, outlet=5)
    msg_to(m, st, "; engparams clear; engparams read engines.txt", 300, 140, outlet=4)
    for i, (nm, v) in enumerate((("engheld", -1), ("englspd", 1), ("engbeat", 500), ("engarpdiv", 4), ("engperm", 1), ("engarppat", 0), ("engarpoct", 1), ("engkl1", -1), ("engkl2", -1), ("engkl3", -1), ("engkl4", -1))):
        to(m, msg_to(m, st, str(v), 550 + i * 60, 140, outlet=5), f"v {nm}", 550 + i * 60, 165)
    for i, (nm, v) in enumerate((("eng-rsize", 0.5), ("eng-throwfb", 0.97))):
        to(m, msg_to(m, st, str(v), 750 + i * 60, 140, outlet=5), f"s {nm}", 750 + i * 60, 165)
    to(m, st, "s $0-loadsettings", 300, 330, outlet=3)
    to(m, st, "s $0-lstat", 450, 330, outlet=2)
    to(m, msg_to(m, st, "0", 300, 170, outlet=1), "s eng-page", 300, 360)
    # keep the Organelle's own MIDI out (knob CCs, key notes) off: this patch sends its own MIDI
    to(m, msg_to(m, to(m, st, "delay 3000", 500, 170), "0", 500, 195), "s midiOutGate", 500, 220)
    m.save(os.path.join(out_dir, "main.pd"))
