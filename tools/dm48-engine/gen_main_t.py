"""Assemble main.pd for DM48 Engine."""
import os
from pdgen import Canvas
from gen_voice import BEND, JUST
from sec_core import NCH, midi_in, keys, process, monitor, chain, to, msg_to
from sec_looper import looper
from sec_ui import ui, settings
from sec_rest import engine_manager, library, audio, glue, MAXBYTES, MAXEV
from sec_midiout import midi_out, clock


def build(out_dir):
    m = Canvas(w=1400, h=900)
    m.comment("DM48 Engine - MPE synth host + MIDI looper + DM48X tuning library for the Organelle", 20, 5)
    m.comment("Engines are plug-in voice patches in engines/ (see engines/README.txt). Tunings live in tunings/.", 20, 22)
    m.comment("Keys: see README.txt. Aux / footswitch: tap = rec > play > overdub > play ... hold = clear.", 20, 39)
    y = 90
    for nm, size in ((BEND, NCH), (JUST, 12), ("englheld", NCH * 128), ("englive", 17 * 128), ("englbraw", 17),("engfz0", 34075), ("engfz1", 34075), ("engfz2", 34075), ("engfz3", 34075), ("engfz4", 34075), ("engfz5", 34075), ("engfz6", 34075),
                     ("dmxb", MAXBYTES), ("dmxt", MAXEV), ("dmxs", MAXEV), ("dmx1", MAXEV), ("dmx2", MAXEV)):
        m.obj(f"array define {nm} {size}", 700, y)
        y += 22
    for nm in ("englp", "engfiles", "englist", "engparams", "engdesc", "englheldt", "englivet"):
        m.obj(f"text define {nm}", 700, y)
        y += 22
    y = 90
    vals = ("engmode engcurve engnr enggr engpage englstate engllen engltop engldub engli englnum englpos "
            "englcpos englclay engcount engsel engpv1 engpv2 engpv3 engpv4 engoctb engocts engmout engsending engbeat "
            "dmxp dmxe dmxr dmxk dmxn dmxc dmxd dmxst dmxi dmxsel dmxcount").split()
    for i, nm in enumerate(vals):
        m.obj(f"value {nm}", 950 + (i // 18) * 150, 90 + (i % 18) * 22)
    y = 80
    for c in (midi_in(), keys(), process(), monitor(), looper(), ui(), settings(), engine_manager(),
              library(), audio(), glue()):
        m.sub(c, 20, y)
        y += 25
    # ---- start-up, in order (right outlet first)
    st = chain(m, m.obj("loadbang", 300, 80), ["t b b b b b b"], 300, 105)
    to(m, st, "s $0-scan", 300, 300, outlet=5)
    to(m, st, "s $0-scanlib", 400, 300, outlet=5)
    msg_to(m, st, "; engparams clear; engparams read engines.txt", 300, 140, outlet=4)
    to(m, st, "s $0-loadsettings", 300, 330, outlet=3)
    to(m, st, "s $0-lstat", 450, 330, outlet=2)
    to(m, msg_to(m, st, "0", 300, 170, outlet=1), "s eng-page", 300, 360)
    # keep the Organelle's own MIDI out (knob CCs, key notes) off: this patch sends its own MIDI
    to(m, msg_to(m, to(m, st, "delay 3000", 500, 170), "0", 500, 195), "s midiOutGate", 500, 220)
    m.save(os.path.join(out_dir, "main.pd"))
