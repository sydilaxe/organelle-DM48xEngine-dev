"""Build 'DM48 Engine Manual.pdf' from HTML with inline SVG + emulator screenshots (headless Chromium)."""
import base64, os, subprocess, sys

SHOTS = sys.argv[1]
OUT_PDF = sys.argv[2]
TUN = sys.argv[3]   # TUNINGS.txt


def img(name, w=256):
    p = os.path.join(SHOTS, name + ".png")
    b = base64.b64encode(open(p, "rb").read()).decode()
    return f'<img class="oled" style="width:{w}px" src="data:image/png;base64,{b}">'


def shot(name, cap, w=256):
    return f'<figure class="shot">{img(name, w)}<figcaption>{cap}</figcaption></figure>'


# ---------------------------------------------------------------- Organelle M (grey), stylised
WHITE = ["C", "D", "E", "F", "G", "A", "B"]
LOW = {"C": "PLAY", "C#": "LIBRARY", "D": "SHAPE", "D#": "PANIC", "E": "FX", "F": "SETUP", "G": "TUNE",
       "A": "ENGINE", "A#": "UNDO", "B": "LOOP ▶■", "F#": "VOICE", "G#": ""}
HIGH = {"C": "FREEZE", "C#": "THROW", "D": "OCT −", "D#": "OCT +", "E": "WET", "F": "TAP", "F#": "ARP",
        "G": "PERM", "G#": "", "A": "", "A#": "", "B": ""}


def organelle_svg(highlight=None):
    W, H = 900, 430
    kx0, ky0, kw, kh = 70, 250, 54, 150
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" class="dev">']
    s.append('<defs><linearGradient id="body" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="#9a9da1"/><stop offset="1" stop-color="#7d8085"/></linearGradient>'
             '<linearGradient id="knob" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3c40"/>'
             '<stop offset="1" stop-color="#18191b"/></linearGradient></defs>')
    s.append(f'<rect x="10" y="10" width="{W-20}" height="{H-20}" rx="26" fill="url(#body)" stroke="#5f6266" stroke-width="3"/>')
    # speaker grille
    for i in range(7):
        for j in range(4):
            s.append(f'<circle cx="{60 + i * 13}" cy="{50 + j * 13}" r="3.2" fill="#55585c"/>')
    # knobs 1-4
    for i in range(4):
        cx = 220 + i * 78
        s.append(f'<circle cx="{cx}" cy="85" r="27" fill="url(#knob)" stroke="#111" stroke-width="2"/>'
                 f'<line x1="{cx}" y1="85" x2="{cx}" y2="62" stroke="#ddd" stroke-width="3"/>'
                 f'<text x="{cx}" y="135" class="lbl">KNOB {i + 1}</text>')
    # screen
    s.append('<rect x="540" y="45" width="190" height="98" rx="6" fill="#111" stroke="#333" stroke-width="3"/>'
             '<rect x="551" y="54" width="168" height="80" fill="#0b0d12"/>'
             '<text x="635" y="99" class="scr">OLED</text>')
    # encoder + volume
    s.append('<circle cx="790" cy="75" r="22" fill="url(#knob)" stroke="#111" stroke-width="2"/>'
             '<text x="790" y="118" class="lbl">SELECT</text>'
             '<circle cx="840" cy="160" r="15" fill="url(#knob)" stroke="#111" stroke-width="2"/>'
             '<text x="840" y="192" class="lbl">VOL</text>')
    # aux button
    s.append('<circle cx="60" cy="200" r="20" fill="#1c1d20" stroke="#111" stroke-width="2"/>'
             '<circle cx="60" cy="200" r="8" fill="#7fd0ff" opacity="0.9"/>'
             '<text x="60" y="236" class="lbl">AUX</text>'
             '<text x="60" y="248" class="lbl small">looper</text>')
    # keys: 14 white
    for octv, names in ((0, LOW), (1, HIGH)):
        for i, n in enumerate(WHITE):
            x = kx0 + (octv * 7 + i) * kw
            hl = highlight and (octv, n) in highlight
            fill = "#f3f3f0" if not hl else "#ffe08a"
            s.append(f'<rect x="{x}" y="{ky0}" width="{kw - 4}" height="{kh}" rx="5" fill="{fill}" stroke="#555"/>')
            lab = names.get(n, "")
            if lab:
                s.append(f'<text x="{x + kw / 2 - 2}" y="{ky0 + kh - 14}" class="key">{lab}</text>')
            s.append(f'<text x="{x + kw / 2 - 2}" y="{ky0 + kh - 30}" class="keyn">{n}</text>')
        # black keys
        for i, n in enumerate(["C#", "D#", None, "F#", "G#", "A#", None]):
            if not n:
                continue
            x = kx0 + (octv * 7 + i) * kw + kw * 0.62
            hl = highlight and (octv, n) in highlight
            fill = "#2a2b2e" if not hl else "#c79a1c"
            s.append(f'<rect x="{x}" y="{ky0}" width="{kw * 0.72}" height="{kh * 0.58}" rx="4" fill="{fill}" stroke="#111"/>')
            lab = names.get(n, "")
            if lab:
                s.append(f'<text x="{x + kw * 0.36}" y="{ky0 + kh * 0.58 - 10}" class="keyb">{lab}</text>')
    s.append(f'<text x="{kx0 + 3.5 * kw}" y="{ky0 - 12}" class="sect">LOW OCTAVE · pages &amp; looper</text>')
    s.append(f'<text x="{kx0 + 10.5 * kw}" y="{ky0 - 12}" class="sect">HIGH OCTAVE · performance</text>')
    s.append('</svg>')
    return "".join(s)


def strip_svg():
    """annotated status strip"""
    return """<svg viewBox="0 0 640 120" class="strip" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="20" width="640" height="40" fill="#0b0d12"/>
<g fill="none" stroke="#eaf3ff" stroke-width="3">
 <rect x="2" y="25" width="22" height="22"/><rect x="32" y="25" width="22" height="22"/><rect x="62" y="25" width="22" height="22"/>
 <rect x="92" y="25" width="22" height="22"/><rect x="122" y="25" width="22" height="22"/><rect x="152" y="25" width="22" height="22"/>
 <rect x="182" y="25" width="22" height="22"/><rect x="230" y="25" width="240" height="28"/><rect x="510" y="25" width="128" height="28"/></g>
<rect x="2" y="25" width="22" height="22" fill="#eaf3ff"/>
<rect x="230" y="25" width="150" height="28" fill="#eaf3ff"/><rect x="487" y="30" width="14" height="18" fill="#eaf3ff"/>
<rect x="510" y="30" width="80" height="18" fill="#eaf3ff"/>
<g font-family="Inter, Helvetica, Arial" font-size="15" fill="#222">
<text x="0" y="85">page tabs (filled = current)</text>
<text x="350" y="85" text-anchor="middle">loop: progress · blinks while recording</text>
<text x="350" y="104" text-anchor="middle">tick marks while overdubbing</text>
<text x="494" y="15" text-anchor="middle">arp</text>
<text x="574" y="85" text-anchor="middle">breath</text></g></svg>"""


def page_table(rows):
    out = ['<table class="knobs"><tr><th>Knob</th><th>Control</th><th>What it does</th></tr>']
    for k, n, d in rows:
        out.append(f"<tr><td class='k'>{k}</td><td><b>{n}</b></td><td>{d}</td></tr>")
    out.append("</table>")
    return "".join(out)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sec_ui
scale_html = "<table><tr><th>Family</th><th>Scales</th></tr>" + "".join(
    f"<tr><td><b>{f}</b></td><td>{' · '.join(ns)}</td></tr>" for f, ns in sec_ui.FAMILIES) + "</table>"
tunings = open(TUN).read().split("\n\n")
tun_html = "".join(f"<pre class='tun'>{t.strip()}</pre>" for t in tunings[1:] if t.strip())

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm;
  @bottom-center { content: counter(page); font: 9pt Inter, Helvetica, Arial; color:#888; } }
body { font-family: Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif; color:#1d1f22; font-size:10.4pt; line-height:1.45; }
h1 { font-size: 30pt; margin: 0 0 4mm 0; letter-spacing:-0.5px; }
h2 { font-size: 16pt; margin: 8mm 0 3mm; padding-bottom: 1.5mm; border-bottom: 2px solid #2c6e8f; color:#163c4f; break-after: avoid; }
h3 { font-size: 12pt; margin: 5mm 0 2mm; color:#163c4f; break-after: avoid; }
p { margin: 0 0 2.6mm; }
.cover { height: 250mm; display:flex; flex-direction:column; justify-content:center; break-after: page; }
.cover .sub { font-size: 14pt; color:#4a5560; margin-bottom: 10mm; }
.cover .meta { color:#6b7580; font-size: 10pt; margin-top: 10mm; }
svg.dev { width: 100%; margin: 3mm 0; }
svg.dev .lbl { font: 600 11px Inter, Arial; fill:#222; text-anchor: middle; }
svg.dev .lbl.small { font-weight: 400; font-size: 10px; }
svg.dev .scr { font: 600 14px monospace; fill:#7fd0ff; text-anchor: middle; }
svg.dev .key { font: 700 9.4px Inter, Arial; fill:#163c4f; text-anchor: middle; }
svg.dev .keyn { font: 400 10px Inter, Arial; fill:#999; text-anchor: middle; }
svg.dev .keyb { font: 700 8.4px Inter, Arial; fill:#ffe9a8; text-anchor: middle; }
svg.dev .sect { font: 700 12px Inter, Arial; fill:#222; text-anchor: middle; }
svg.strip { width: 100%; margin: 2mm 0 4mm; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; font-size: 9.8pt; break-inside: avoid; }
th { text-align:left; background:#e8eef2; padding: 1.6mm 2mm; }
td { border-top: 1px solid #dde3e8; padding: 1.5mm 2mm; vertical-align: top; }
td.k { width: 12mm; font-weight:700; color:#2c6e8f; }
.grid { display:flex; flex-wrap:wrap; gap: 4mm; margin: 2mm 0 4mm; }
figure.shot { margin:0; break-inside: avoid; }
figure.shot img.oled { border: 6px solid #2a2b2e; border-radius: 6px; image-rendering: pixelated; display:block; }
figcaption { font-size: 8.8pt; color:#555; margin-top: 1mm; max-width: 256px; }
.note { background:#f4f8fa; border-left: 4px solid #2c6e8f; padding: 2.5mm 3.5mm; margin: 3mm 0; break-inside: avoid; }
.warn { background:#fff7e6; border-left: 4px solid #d99a1c; padding: 2.5mm 3.5mm; margin: 3mm 0; break-inside: avoid; }
code, pre { font-family: 'JetBrains Mono', Menlo, Consolas, monospace; font-size: 8.8pt; }
pre { background:#f5f6f7; padding: 2.5mm 3mm; border-radius: 3px; white-space: pre-wrap; break-inside: avoid; }
pre.tun { font-size: 8pt; margin: 0 0 2mm; white-space: pre; }
.two { columns: 2; column-gap: 7mm; }
.toc li { margin: 0.6mm 0; }
.pb { break-before: page; }
"""

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>DM48 Engine Manual</title><style>{CSS}</style></head><body>

<section class="cover">
<h1>DM48 Engine</h1>
<div class="sub">A breath-controlled MPE synth host, MIDI looper, arpeggiator and DM48X tuning library
for the Critter &amp; Guitari Organelle M — made for the Lekholm DM48X digital harmonica.</div>
{organelle_svg()}
<div class="meta">Organelle OS 5 · Pure Data vanilla (no externals) · Patch folder: <b>DM48 Engine</b><br>
The illustration is stylised; key labels show what each Organelle key does in this patch.</div>
</section>

<h2>Contents</h2>
<ol class="toc">
<li>Quick start</li><li>How it is organised</li><li>The keyboard as a control surface</li><li>The screen</li>
<li>Pages and knobs</li><li>Engines</li><li>Looper</li><li>Arpeggiator</li><li>Effects</li>
<li>Tuning: just intonation and the DM48X tuning library</li><li>MIDI: MPE, Standard, echo and clock</li>
<li>Making your own engine</li><li>Performance on the Organelle M</li><li>Saving, files and troubleshooting</li>
<li>Appendix: tunings included</li></ol>

<h2>1. Quick start</h2>
<ol>
<li>Copy the <b>DM48 Engine</b> folder into your Patches folder (USB drive, SD card, or the OS 5 web editor).</li>
<li>Plug the DM48X into the Organelle's USB port. Go to <b>System › MIDI Setup › Device</b>, choose the DM48X, and <b>Save</b>.</li>
<li>Set up the DM48X (Global settings):
<table><tr><th>DM48X setting</th><th>Value</th><th>Why</th></tr>
<tr><td>MIDI channel</td><td><b>Multich. 2-13</b></td><td>One channel per hole (MPE). Channel 1 stays free for global messages.</td></tr>
<tr><td>Mono/poly</td><td><b>Poly</b></td><td>Chords and the arpeggiator need more than one note.</td></tr>
<tr><td>Double notes</td><td><b>Allow</b></td><td>Both C holes in Solo tuning can sound.</td></tr>
<tr><td>Breath CC#</td><td><b>11</b> (default) or <b>Aftertouch</b></td><td>Breath is read from CC 2, 7, 11, channel pressure or poly pressure.</td></tr>
<tr><td>Breath sens</td><td>anything but <b>Off</b></td><td>Off sends no breath; notes then only use their start velocity.</td></tr>
<tr><td>Bend range</td><td>see §11</td><td>Match the patch's <i>Note Bend</i> setting.</td></tr></table></li>
<li>Load <b>DM48 Engine</b>. Play. Tap <b>Aux</b> (or the footswitch) to start a loop.</li></ol>
<div class="note">If the DM48X is plugged in after the patch is loaded, reload the patch so the Organelle connects to it.</div>

<h2>2. How it is organised</h2>
<p>The DM48X is the instrument; the Organelle is the sound engine and the control surface. Every note keeps its own MIDI channel,
so breath, bends and timbre shape each note on its own (MPE). Signal flow:</p>
<pre>DM48X ─► MIDI in ─► arpeggiator ─► looper (records) ─► voices (8, any engine) ─► delay ─► reverb ─► limiter ─► out
                                        │                                             └► MIDI out echo + clock
                                        └─ loop playback on its own channels (no clashes with live notes)</pre>
<p>Breath does far more than volume: each engine maps it to several small timbre changes (brightness, harmonics, noise, detune,
drive). <b>Breath&gt;Tone</b> on the SHAPE page scales all of them at once.</p>

<h2 class="pb">3. The keyboard as a control surface</h2>
<p>You play the DM48X, so the Organelle's 24 keys are free for control. The low octave selects pages and runs the looper;
the high octave holds performance effects.</p>
{organelle_svg()}
<table><tr><th>Key</th><th>Low octave</th><th>High octave</th></tr>
<tr><td>C</td><td>PLAY page</td><td>Reverb <b>freeze</b> on/off</td></tr>
<tr><td>C♯</td><td>LIBRARY page</td><td>Delay <b>throw</b> (while held)</td></tr>
<tr><td>D</td><td>SHAPE page</td><td>Octave down on/off</td></tr>
<tr><td>D♯</td><td><b>Panic</b>: silence everything</td><td>Octave up on/off</td></tr>
<tr><td>E</td><td>FX page</td><td><b>Wet only</b> (dry signal off) on/off</td></tr>
<tr><td>F</td><td>SETUP page</td><td><b>Tap tempo</b> — two taps less than 2 s apart</td></tr>
<tr><td>F♯</td><td>VOICE page</td><td><b>Arpeggiator</b> on/off</td></tr>
<tr><td>G</td><td>TUNE page</td><td>Arp <b>permutations</b> on/off</td></tr>
<tr><td>G♯</td><td>—</td><td>Screen <b>view</b>: pages › scope › audio loop waveform</td></tr>
<tr><td>A</td><td>ENGINE page</td><td><b>Audio loop</b>: record › play › overdub (hold 1 s: clear)</td></tr>
<tr><td>A♯</td><td>Loop <b>undo</b> last overdub</td><td>Audio loop <b>undo</b> (newest layer)</td></tr>
<tr><td>B</td><td>Loop <b>stop / start</b></td><td>Audio loop <b>stop / start</b></td></tr></table>
<p>Keys act when you <b>release</b> them. If you turn a knob while holding a key, the knob does a <b>combo</b> instead and the key's normal action is skipped:</p>
<table><tr><th>Hold</th><th>Turn</th><th>Result</th></tr>
<tr><td>B (loop)</td><td>any knob</td><td><b>Loop speed and direction.</b> Centre = normal. Right = forward, faster the further you turn (up to 4×).
Left = reverse, faster the further you turn (up to 4×). The MIDI clock follows.</td></tr>
<tr><td>C (freeze)</td><td>any knob</td><td>Reverb size</td></tr>
<tr><td>C♯ (throw)</td><td>any knob</td><td>Throw feedback (how long the throw rings; above 100 it slowly grows)</td></tr>
<tr><td>E (wet)</td><td>any knob</td><td>Reverb amount</td></tr>
<tr><td>F (tap)</td><td>any knob</td><td>Tempo 40–200 BPM</td></tr>
<tr><td>F♯ (arp)</td><td>knob 1 / 2 / 3</td><td>Arp rate / pattern / octave range</td></tr>
<tr><td>A (high, audio loop)</td><td>knob 1 / 2 / 3 / 4</td><td>Audio loop <b>speed &amp; direction</b> (tape style) / <b>pitch</b> −12…+12 / <b>level</b> / <b>layer fade</b></td></tr>
<tr><td>B (high, audio loop)</td><td>any knob</td><td>Record <b>Pre</b> (left) or <b>Post</b> (right) effects</td></tr></table>
<p><b>Aux button</b> and <b>footswitch</b> run the looper (§7). On the LIBRARY page, Aux sends a tuning instead; the footswitch still runs the looper.</p>

<h2 class="pb">4. The screen</h2>
<p>Rows 1–4 show the four knobs of the current page in the PLAY-patch style: knob number, a bar for its value, then its name and value.
Rows whose value is a word (scale, key, engine, MIDI mode) show plain text. Line 5 shows the page name and the looper state, and briefly
shows messages when you press a key or turn a combo. The top strip is always visible:</p>
{strip_svg()}
<div class="grid">
{shot("page_play", "PLAY page with the Velvet engine. Strip: page 1 of 8, breath meter on the right.")}
{shot("loop_reverse", "Loop playing in reverse at 1.8× (&lt;1.8). The loop bar shows the position.")}
{shot("loop_dub", "Overdubbing: tick marks on the loop bar.")}
{shot("arp_on", "Arpeggiator on: dot next to the breath meter.")}
</div>

<h2>5. Pages and knobs</h2>
<p>Switch pages with the low-octave keys. A knob changes its setting only once you move it. The smooth settings (PLAY, SHAPE, FX, Level) pick up where they are: turning the knob moves the value from its current setting and it meets the knob at the end of its travel, so nothing jumps when you change page. Selector knobs (scales, engine, octave…) go straight to the knob's position.</p>
<h3>PLAY — the engine</h3>
<p>The four knobs belong to the loaded engine; their names change with it (see §6). Each engine remembers its own settings.</p>
<div class="grid">{shot("page_play", "PLAY (Velvet)")}{shot("page_shape", "SHAPE")}</div>
<h3>SHAPE — breath and envelope</h3>
{page_table([("1", "Breath&gt;Tone", "How much breath changes the timbre (all engines). 0 = breath only changes volume."),
             ("2", "Body", "A sine one octave below every note."),
             ("3", "Release", "Fade after a note ends (10 ms – 3 s)."),
             ("4", "Breath Curve", "0.5 = easy to get loud · 1 = linear · 3 = needs strong breath.")])}
<h3>FX</h3>
{page_table([("1", "Delay", "20 – 1500 ms. Tap tempo sets it too."),
             ("2", "Feedback", "Repeats."), ("3", "Delay Mix", "Delay level."), ("4", "Reverb", "Reverb level.")])}
<h3>SETUP</h3>
{page_table([("1", "Octave", "−2 … +2 octaves (the high-octave D / D♯ keys add another ±1)."),
             ("2", "Note Bend", "Bend range for channels 2–16: 1, 2, 3, 12, 24 or 48 semitones (MPE standard is 48)."),
             ("3", "Ch1 Bend", "Bend range on channel 1, which bends every note."),
             ("4", "Vibrato", "Vibrato speed. Depth comes from CC 1 (DM48X breath modulation or ribbon).")])}
<h3>TUNE</h3>
{page_table([("1", "Family", "Western · Temperament · Gamelan · African · Japanese · Chinese · SE-Asian · Maqam · Indian · Byzantine."),
             ("2", "Scale", "A scale within the family (78 in all — see the appendix). Line 4 shows its number in the family."),
             ("3", "Key", "The note the scale is counted from: set it to the key of your harp tuning.")])}
<p>Western includes <b>Just 5-limit</b> (9/8 5/4 4/3 3/2 5/3 15/8 …) and <b>Just 7</b> (the 4th is 21/16 and the minor 3rd / flat 7th are 7/6 / 7/4:
on a C harp the draw chord G-B-D-F becomes the pure 4:5:6:7 chord).</p>
<h3>ENGINE</h3>
{page_table([("1", "Engine", "Choose the sound engine (all .pd files in engines/)."),
             ("2", "MIDI", "MPE (each channel is its own note) or Standard (all channels merged into one)."),
             ("3", "Level", "Output level."),
             ("4", "MIDI out", "Off · Echo · Echo+Clock. Line 4 shows the MIDI arriving from the DM48X.")])}
<h3>VOICE — legato and glide</h3>
{page_table([("1", "Mode", "<b>Poly</b> (a voice per note) or <b>Mono legato</b>: one voice; a new note while one is held moves the voice there without a new attack, and releasing it goes back to the note still held."),
             ("2", "Glide", "Portamento time, 0 (off) – 2 s. Bends during a glide don't cut it short."),
             ("3", "When", "<b>Glide always</b>, or <b>Glide legato</b>: only from notes you are still holding (overlap the notes to slide)."),
             ("4", "From", "<b>From nearest</b>: polyphonic portamento — each new note slides from the nearest note of the chord before (recent chords first), so a chord slides into the next chord. <b>From last</b>: every new note slides from the last note played.")])}
<p>Glide works with every engine: the engine receives the start pitch, then a ramp to the new pitch. In Mono legato the engine gets no new note at all, only the ramp, so strings keep ringing and envelopes don't restart.</p>
<div class="grid">{shot("page_fx", "FX")}{shot("tune_family", "TUNE: family, scale, key")}{shot("engine_monitor", "ENGINE: line 4 shows incoming MIDI")}{shot("page_library", "LIBRARY")}</div>

<h2 class="pb">6. Engines</h2>
<p>An engine is one voice; the patch runs eight. All seven bundled engines react to breath in several small ways at once,
and they are level-matched, so switching doesn't jump in volume.</p>
<p><b>Switching engines while you play.</b> Every engine is loaded once when the patch starts and stays switched off
(costing nothing) until you choose it. Changing the engine fades the old one out and the new one in within about 30 ms,
and the notes you are holding carry on with the new sound. Nothing is loaded at that moment, so there is no pop.
Turning the engine knob quickly through several engines switches once, to where the knob stops.</p>
<table><tr><th>Engine</th><th>Character</th><th>Knobs</th><th>What breath does</th></tr>
<tr><td><b>Feral</b></td><td>raw, unstable, weird</td><td>Sync · Snarl · Tone · Tail</td><td>The most breath-hungry engine, built from scratch. A capacitor-charge oscillator bends from a smooth ramp into a charging curve as you blow, and a hard-synced second oscillator screams as breath sweeps its ratio (Sync sets the range). Everything goes through a vactrol low-pass gate: breath opens volume and brightness together, instantly, and it closes with a slow tail (Tail). Fast changes in breath — puffs and accents — jab the pitch sharp, kick the sync, add crackle and drive the asymmetric diode clipper (Snarl) harder. Soft breath is very quiet and dark; full breath is loud and bright, with a wide range in between.</td></tr>
<tr><td><b>Volt</b></td><td>raw, electric</td><td>Fold · Grit · Detune · Tone</td><td>More wave-folding, more sample-rate grit, a brighter filter and a slight upward strain of pitch.</td></tr>
<tr><td><b>Halo</b></td><td>ethereal, resonant</td><td>Shimmer · Resonance · Air · Bloom</td><td>Upper partials bloom in (Bloom sets how fast), breath noise rings two tuned resonators, which brighten.</td></tr>
<tr><td><b>Under</b></td><td>bass, subharmonic</td><td>Subs · Drive · Tone · Octave</td><td>Deeper subharmonics (f/3, f/4) fade in, more saturation, the filter opens. Octave knob: 0, −1, −2.</td></tr>
<tr><td><b>Velvet</b></td><td>lush analog pad</td><td>Cutoff · Spread · Swell · Warmth</td><td>The filter opens, the three saws spread wider, warmth and a slow pitch drift deepen. Swell softens the attack.</td></tr>
<tr><td><b>Steel</b></td><td>pedal steel string</td><td>Tone · Sustain · Steel · Attack</td><td>A waveguide string bowed by breath (no pluck): breath is the volume pedal and the bow, brightens the string and adds a little drive. Attack sets how fast the sound swells in when you blow, from 5 ms (instant) to 2 s (a slow volume-pedal swell). Steel adds the stiff, metallic stretch of the partials.</td></tr>
<tr><td><b>Lyra</b></td><td>LIRA-8 style drone</td><td>Mod · Sharp · Detune · Drive</td><td>Two triangle oscillators modulate each other. Breath deepens the cross-modulation, sharpens the waves toward squares, widens the beating and pushes the drive. Pitch stays steady.</td></tr></table>
<p>Steel is based on <b>Steelie</b> by gur_shulman (WTFPL). Lyra is based on <b>LIRA-8</b> by Miguel Moreno (BSD licence; after the Soma Laboratory Lyra-8).</p>
<p>CC 74 (MPE timbre, if your controller sends it) also brightens each engine per note.</p>

<h2>7. Looper</h2>
<p>The looper records <b>MIDI</b>, not audio: notes, per-note bends, breath and timbre, on their own channels. Playback goes through
the current engine, so you can change engine, tuning or effects while a loop plays.</p>
<table><tr><th>Action</th><th>How</th></tr>
<tr><td>Record</td><td>Tap Aux (or footswitch). Line 5: <code>rec</code>, loop bar blinks.</td></tr>
<tr><td>Close the loop and play</td><td>Tap again. The loop length is the time you recorded.</td></tr>
<tr><td>Overdub</td><td>Tap while playing (<code>dub x2</code>); tap again to keep playing. Up to 7 layers.</td></tr>
<tr><td>Undo last layer</td><td>Low A♯.</td></tr>
<tr><td>Stop / start</td><td>Low B.</td></tr>
<tr><td>Clear</td><td>Hold Aux (or footswitch) for 0.7 s.</td></tr>
<tr><td>Speed and direction</td><td>Hold low B and turn any knob: centre normal, right forward faster, left reverse faster.</td></tr></table>
<div class="grid">{shot("loop_rec", "Recording")}{shot("loop_play", "Playing")}{shot("loop_reverse_toast", "Turning the speed combo")}</div>
<p>In reverse, notes still begin with their note-on: the looper swaps note-ons and note-offs when it runs backwards.
Each loop layer plays on its own set of channels, so loop notes never cut off live notes or each other.</p>
<h3>Audio looper</h3>
<p>The MIDI loop always plays through the current engine. The <b>audio looper</b> records the sound itself, so you can
layer different engines: record a pass with Halo, switch to Steel, overdub, and so on. Up to 6 stereo layers, 45 s long.</p>
<table><tr><th>Action</th><th>How</th></tr>
<tr><td>Record / play / overdub</td><td>Tap high A: record › play › overdub › play … (a thin line under the loop bar shows the audio loop)</td></tr>
<tr><td>In time with a MIDI loop</td><td>If a MIDI loop is playing, the audio loop waits for its start and records exactly one cycle, so both stay in time.</td></tr>
<tr><td>Undo</td><td>High A♯ removes the newest layer (again for the one before).</td></tr>
<tr><td>Stop / start</td><td>High B.</td></tr>
<tr><td>Clear</td><td>Hold high A for 1 s.</td></tr>
<tr><td>Speed &amp; direction</td><td>Hold high A + knob 1: like tape, pitch follows speed; left of centre plays backwards.</td></tr>
<tr><td>Pitch</td><td>Hold high A + knob 2: −12…+12 semitones, speed unchanged.</td></tr>
<tr><td>Level / layer fade</td><td>Hold high A + knob 3 / knob 4. Layer fade makes older layers fade a little each pass (off at the right end).</td></tr>
<tr><td>Pre / Post</td><td>Hold high B + a knob. <b>Pre</b> records the synth before the effects; the loop then goes through the delay and reverb you set now.
<b>Post</b> records the finished sound with its effects.</td></tr></table>
<p><b>Overdub at any speed, like tape.</b> Each layer remembers the speed (and direction) it was recorded at. Overdub at 2× and then
bring the loop back to 1×: that layer plays at half speed, an octave lower and stretched, while the first take plays normally.
A layer recorded in reverse plays backwards when the loop runs forwards. Changing the speed ends an overdub; the next one is a new layer
at the new speed. A layer holds up to 45 s, so a long loop can't be overdubbed very slowly (the screen says so).
Each layer records for at least one whole pass, so undo always removes exactly what you played.</p>
<h3>Screen views</h3>
<p>High G♯ switches the screen between the pages, a <b>scope</b> of the output (steady on the note's waveform, auto-scaled),
and the <b>audio loop waveform</b> with its playhead. Any page key returns to the pages. The top strip and line 5 stay.</p>
<div class="grid">{shot("view_scope", "Scope (high G#)")}{shot("view_loop", "Audio loop waveform with playhead")}</div>

<h2>8. Arpeggiator</h2>
<p>High F♯ turns it on. Hold notes on the DM48X and the arpeggiator plays them one at a time — each on its own channel, so
breath and bends still shape every note. It runs at the tap tempo.</p>
<table><tr><th>Hold F♯ +</th><th>Sets</th></tr>
<tr><td>knob 1</td><td>Rate: 1/4, 1/8, 1/8 triplet, 1/16, 1/16 triplet, 1/32</td></tr>
<tr><td>knob 2</td><td>Pattern: up, down, up-down, pedal (lowest note alternating), random</td></tr>
<tr><td>knob 3</td><td>Octave range 1–3</td></tr></table>
<p><b>Breath</b> shapes the notes, not the pattern:</p>
<ul><li><b>Density</b> — soft breath plays only some steps; stronger breath fills them in; near full breath some steps double (ratchets).</li>
<li><b>Scatter</b> — above half breath, notes jump an octave up or down (two octaves when strong) and drift off the grid.</li></ul>
<p><b>Permutations</b> (high G, on by default): each pass through the pattern rotates the note order, and every other pass is mirrored.
The looper records what the arpeggiator plays.</p>

<h2>9. Effects</h2>
<p>Master chain: stereo ping-pong <b>delay</b> (warm-filtered repeats) → <b>reverb</b> (an 8-line feedback delay network after the VerbRack patch: four diffusers, slowly moving delay lines for a smooth tail, highs die away faster than lows; size sets 1.8–15 s of decay; mono-safe for the built-in speaker) → <b>limiter</b> (always on,
with a soft clipper after it). <b>Freeze</b> holds the reverb tail indefinitely and mutes its input. <b>Throw</b> pushes the delay into long feedback
while you hold the key. <b>Wet only</b> removes the dry sound for washes. <b>Tap tempo</b> sets the delay time, the arp and the MIDI clock.</p>
<div class="grid">{shot("freeze", "Freeze toggled on")}{shot("throw", "Delay throw")}</div>

<h2 class="pb">10. Tuning: just intonation and the DM48X tuning library</h2>
<h3>Just intonation in the synth</h3>
<p>MIDI notes are equal-tempered, so the tuning happens in the patch: every note is retuned on its own, so chords stay pure in any mix.
The TUNE page offers 78 scales in ten families — just intonation, historical temperaments, gamelan slendro and pelog, African xylophone
and kora tunings, Japanese, Chinese and Southeast Asian scales, maqam and quarter-tone scales, Indian ragas and Byzantine modes.
Each is a set of 12 offsets in cents, counted from <i>Key</i>. The world-music scales come from the <b>Astral</b> patch's scale library.
Pitches are measured exact in testing (e.g. E in Pelog Degung Sejati is +24 cents).</p>
<h3>The LIBRARY page</h3>
<p>Sends tunings (MIDI files in the <code>tunings/</code> folder) to the DM48X, without stopping the loop or touching the sound.</p>
<ol><li>On the DM48X: <b>Tuning editor</b> › step past the last hole › <b>Receive tuning</b>.</li>
<li>On the Organelle: low C♯ (LIBRARY). Knob 2 picks a folder — <i>All</i>, then each subfolder of <code>tunings/</code> (Ambient, Chromatic, Richter, World); line 1 shows the folder and how many tunings it holds. Knob 1 picks the tuning, <b>Aux</b> sends it. Line 5 says <i>Sent!</i>.</li>
<li>On the DM48X: hold the round button for 2 s on the Tuning page to save it to a slot.</li></ol>
<div class="warn">First time: send <b>Order test</b> and check in the Tuning editor that hole 1 blow = C3 (MIDI 48), hole 1 draw = C4 (60),
hole 1 blow + slider = C5 (72) and hole 12 draw + slider = B6 (95). The 48-note order was read from the DM48X firmware; this confirms it on your
instrument. Nothing is stored until you save on the DM48X.</div>
<p><b>Key follows the tuning.</b> If the tuning's name ends in a key (<i>Richter Low D</i>, <i>… Bb</i>, <i>… F#</i>), sending it also sets the TUNE page Key, so the synth's just intonation is built on the same key as the harp. Line 5 shows <i>Sent! Synth key D</i>. You can still change Key afterwards. The DM48X itself only stores ordinary note numbers; the pure tuning happens in the synth.</p>
<p>To add your own, record the DM48X's <b>Send tuning</b> as a MIDI file and put it in <code>tunings/</code> or any folder inside it (a new folder appears on knob 2 the next time the patch loads). Format 0 and 1 files work; only the notes are sent.</p>
<div class="note">The Organelle has one MIDI output, so tuning notes also reach anything on the hardware MIDI Out jack. MIDI echo pauses while a tuning is sent, and MIDI coming <i>from</i> the DM48X is ignored until 0.6 s after it ends, so the instrument's replies can't trigger notes or a pop.</div>

<h2>11. MIDI</h2>
<p><b>MPE</b> (default): channels 2–16 are notes (each with its own bend, breath and timbre); a bend on channel 1 bends every note.
<b>Standard</b>: all channels merge into one, for a DM48X in single-channel mode.</p>
<p><b>Bend ranges</b>: the DM48X's breath bends and ribbon send pitch bend. Either set <i>Note Bend</i> (SETUP knob 2) to the range the DM48X expects
(often 2), or keep 48 (MPE standard) and lower the DM48X's <i>Bend range</i> so its bends stay small.</p>
<p>Messages read: notes, pitch bend, channel pressure, poly pressure, CC 2 / 7 / 11 (breath), CC 74 (timbre), CC 1 (vibrato depth), CC 120 / 123 (all notes off).</p>
<p><b>MIDI out</b> (ENGINE knob 4): <i>Echo</i> repeats everything the engine plays — live and looped, on the original channels — to the Organelle's MIDI out.
<i>Echo+Clock</i> adds 24-per-beat MIDI clock at the tap tempo (following the loop speed), Start when a loop starts playing, and Stop when it stops or is cleared.
The Organelle's own MIDI out (knob CCs, key notes) is switched off while this patch runs.</p>
<div class="note">The Organelle's System › MIDI Setup › <i>MIDI In Ch.</i> only affects the Organelle's built-in MIDI functions. If the DM48X sends program changes,
set it to a channel the DM48X never uses (e.g. 16) so the Organelle doesn't switch patches.</div>

<h2 class="pb">12. Making your own engine</h2>
<p>Copy an engine in <code>engines/</code>, rename it and change it. It appears on the ENGINE page after a reload. An engine is one voice:</p>
<pre>inlet 1 (left)  pitch   "note ms"   MIDI note, fractional (bend, tuning, octave included) — feed it to [line~]
inlet 2         level   "level ms"  0..1 breath/velocity, already curved; 0 with the release time at note-off
inlet 3         timbre  "value ms"  0..1, 0.5 = neutral (CC 74)
outlet~         mono audio

Shared:  [r~ $1-p1~] .. [r~ $1-p4~]  PLAY knobs (0..1, smoothed)   [r $1-p1] .. control rate
         (every engine in the folder is created once at start-up and switched off until selected)
         [r~ eng-bamt~]  Breath&gt;Tone    [r~ eng-body~]  Body    [r~ eng-vib]  vibrato (semitones)
         [r~ eng-sawk]   for lib/bsaw (band-limited saw)

engines/NAME.txt   line 1: four knob names    line 2: four default values</pre>
<p>Any Pd synth voice can be wrapped this way: connect pitch to its frequency (via <code>[mtof~]</code>), level to its amplitude, and send its output to the outlet.
Let breath change several things a little rather than one thing a lot. Keep it light — eight copies run at once.</p>

<h2>13. Performance on the Organelle M</h2>
<p>The Organelle M runs on a Raspberry Pi Compute Module 3 (four ARM Cortex-A53 cores at 1.2 GHz). Pure Data computes all audio on one of those cores,
so that single core is the budget. The patch is built for it:</p>
<ul><li>Each voice switches its DSP off when silent, so only sounding voices cost anything. The audio looper's DSP is off until you first record; its 6 × 45 s of stereo buffers take about 95 MB of the M's 1 GB, reserved when the patch loads.</li>
<li>Saws are band-limited without oversampling; filters are cheap 2-pole designs (Velvet cascades two for 4-pole warmth).</li>
<li>All control logic is message-based; the arpeggiator, looper and screen run at control rate.</li></ul>
<p>Measured offline with all 8 voices sounding, the engines use 2.7–4.9 % of one 2.1 GHz Xeon core (Halo and Feral are the heaviest, Under the lightest; Steel 3.7 %, Lyra 3.0 %).
A Cortex-A53 core is very roughly 8–10× slower for this kind of work, so expect around 25–50 % of the Pd core on the Organelle M with eight
voices held — less in normal playing. If you hear clicks, play fewer notes at once with Halo or Feral, or lower Reverb.</p>

<h2>14. Saving, files and troubleshooting</h2>
<p>Settings <b>save themselves</b> two seconds after you change something (page settings to <code>settings.txt</code>, each engine's PLAY knobs to <code>engines.txt</code>, in the patch folder). <b>System › Save Patch</b> still works too. Loops are not saved. To go back to the defaults, delete <code>settings.txt</code>.</p>
<pre>DM48 Engine/
  main.pd  voice.pd  README.txt  settings.txt  engines.txt
  engines/   feral volt halo under velvet steel lyra (.pd + .txt)  lib/bsaw.pd  README.txt
  tunings/   *.mid  TUNINGS.txt</pre>
<table><tr><th>Problem</th><th>Check</th></tr>
<tr><td>No sound</td><td>MIDI Setup › Device is the DM48X; reload the patch after plugging in; ENGINE line 4 shows incoming MIDI.</td></tr>
<tr><td>Breath does nothing</td><td>DM48X Breath sens not Off; Breath CC# 11 / 2 / 7 or Aftertouch; the strip's breath meter should move.</td></tr>
<tr><td>Bends far too wide</td><td>SETUP Note Bend vs the DM48X Bend range (§11).</td></tr>
<tr><td>Knob does nothing</td><td>A key may still count as held — press and release any low-octave key.</td></tr>
<tr><td>A sound keeps going</td><td>Press low D♯ (<b>Panic</b>): all notes off, both loopers stop (nothing is erased; start them again
as usual), freeze, throw and the arpeggiator switch off, and the delay and reverb are emptied. Then please note what you did just
before, so it can be fixed.</td></tr>
<tr><td>Pop from the speaker when sending</td><td>Should be gone in this version (the DM48X's replies are now ignored while sending). If it persists, it is likely the USB power draw of the DM48X saving — try the headphone/line out, or a powered USB hub.</td></tr>
<tr><td>Tuning didn't arrive</td><td>DM48X must be in Receive tuning before you press Aux; check line 5 says Sent!.</td></tr></table>
<div class="warn">Tested offline in Pure Data 0.54 (the Organelle runs 0.53, and only objects available in 0.53 are used) with recorded test
input — not yet on an Organelle with a DM48X. Sounds, levels and CPU will need a round of tuning on the real hardware.</div>

<h2 class="pb">Appendix A: scales (TUNE page)</h2>
{scale_html}
<h2 class="pb">Appendix B: DM48X tunings included</h2>
<p>Holes 1–12 left to right; middle C = C4 = MIDI 60. Groups: <i>Richter Low</i>, <i>Country</i>, <i>Paddy Richter</i> and <i>Harmonic Minor</i> are diatonic harps in the low octave (slider = +1 octave; Richter Low in all 12 keys); <i>Chromatic</i> tunings use the slider for the semitone above, like a chromatic harmonica; <i>Ambient</i> tunings are open, chordal layouts; <i>World</i> tunings walk a scale (blow, then draw one step up). A name ending in a key sets the TUNE Key when sent: choose Just (or the matching world scale, e.g. Pelog or Slendro) on the TUNE page for the true pitches.</p>
<div>{tun_html}</div>
</body></html>"""

open("manual.html", "w").write(html)
subprocess.run([os.environ.get("CHROME", "/opt/pw-browsers/chromium"), "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={OUT_PDF}", "file://" + os.path.abspath("manual.html")], check=True,
               capture_output=True)
print("wrote", OUT_PDF)
