# Project notes

This is the working memory for this project: read it first in any new session.

## Setup
- **Hardware:** Organelle M (grey), Raspberry Pi CM3 (4× Cortex-A53, 1.2 GHz). Pd audio runs on one core.
- **Software:** Organelle OS 5 with Pd 0.53. Only use objects that exist in 0.53, and **vanilla only** (no externals).
- **Controller:** Lekholm DM48X with firmware 1.20, connected over USB.
  - DM48X settings: Multich 2-13, Poly, Double notes Allow, Breath CC 11 (or Aftertouch).
- **The player:** uses only the DM48X to play. The Organelle keys are function keys, combined with knobs for combos. Music is ambient and experimental.

## Organelle / mother.pd conventions
- **Audio:** send out with `[throw~ outL/outR]`; input with `[r~ inL/inR]`.
- **Controls:**
  - Knobs: `[r knob1..4]` give 0..1.
  - Keys: `[r notesRaw]` gives notes 60..83, velocity 0/100.
  - Buttons: `[r aux]` and `[r fs]`.
  - LED: `[s led]`. Colours: 0 off, 1 red, 2 orange, 3 green, 4 cyan, 5 blue, 6 purple, 7 white.
- **Screen:**
  - Text lines: `[s screenLine1..5]`.
  - Graphics: `[s oscOut]` with `/oled/gFillArea 3 x y w h c`, `gPrintln 3 x y 8 1 text`, `gInvertArea`, `gFlip 3` and `gShowInfoBar 3 0`.
  - Text line N sits at y = 9 + (N-1)·11. The top 8 rows are the info bar.
- **MIDI:**
  - patch_loaded.sh connects the chosen MIDI device to Pd port 1.
  - `[s midiOutGate] 0` stops mother's own MIDI out.
- **Saving:** `saveState` → write to `/tmp/state/` and the OS copies it. DM48 Engine also auto-saves into the patch folder.

## Pd gotchas (all learned the hard way)
- **Values and triggers:**
  - `[v name]` does **not** output when it gets a float. Use `[t b f]` to store the value, then bang.
  - Fan-out order is undefined, so always use `[t ...]`. Trigger outlets fire right to left.
  - For `[pack]`, the hot inlet is the left one: feed it last.
- **Dynamically created abstractions** (engines) do **not** get `loadbang`. Read shared values with `[r~ eng-...]` or global `[value]`s instead.
- **`[switch~]` starts switched off.** Each mode subpatch needs an explicit `1`.
- **Signal objects:**
  - `vcf~`: the lowpass goes silent when cf/q exceeds about sr/2π. Keep q and cf in range.
  - `bob~` at oversample 1 is unstable above about 8 kHz.
  - A `delwrite~`/`vd~` feedback loop can't be shorter than one block (64 samples); use `block~ 16` for short loops.
- **`expr`:**
  - No `wrap()`; use `fmod(x + 4, 1)`.
  - Up to 16 outlets with `;` works. Inside a `.pd` file the `;` must be escaped as `\;`.
- **Text and lists:**
  - `[text define]`: writing an empty text fails. Check `text size` first.
  - A message box receiving a list uses `$1` for the first element.
- **lib/bsaw:** the right inlet takes `eng-sawk / freq` (sample rate / (2.5·f)). Multiplying instead of dividing gives aliased saws. That bug was fixed in Volt and Velvet.

## DM48X tuning format
- A tuning is 48 notes in this order: blow 1-12, draw 1-12, blow+slider 1-12, draw+slider 1-12. In the firmware the table is at 0xAB28.
- Send/Receive tuning: the notes go as plain MIDI notes, recorded or played as a `.mid` file. All files in `tunings/` are format 0, channel 1, with 48 note-on/off pairs.
- The DM48X only stores note numbers. Just intonation and other microtuning are done in the synth (TUNE page scale + Key).
- In DM48 Engine, a tuning whose name ends in a key ("Richter Low D") also sets the TUNE Key when sent.
- While a tuning is being sent, DM48X input is ignored, plus 0.6 s afterwards. This fixed a reported "pop".

## DM48 Engine design (short)
- **Engine contract** (`engines/README.txt`):
  - One voice per file, with inlets pitch, level (breath) and timbre, each taking "value ms" pairs. One `outlet~`.
  - A pitch message with ms 0 means a new note.
  - Knobs are shared as `[r~ eng-p1~..p4~]`.
- **MPE:**
  - Internal channel = 17·layer + MIDI ch.
  - Each voice is keyed by ch·128 + note.
  - Per-voice just intonation reads `engjust[(note-key+120)%12]`.
- **Engine morphing:**
  - Every voice has two engine slots, `pd $0-slotA` and `pd $0-slotB`.
  - Loading sends `eng-load A|B symbol engines/NAME`. The engine is created with the argument `eng-A` or `eng-B`, so it reads its knobs as `[r~ $1-p1~]`.
  - `engbus` says which slot is current; PLAY knob values go to `eng-<bus>-p<k>`.
  - The new slot replays the voice's current pitch (with ms 0, i.e. a new note), level and timbre.
  - `eng-xfade "target ms"` drives `[r~ eng-xf~]`, an equal-power cos/sin crossfade in each voice.
  - When the fade is done, the old slot's switch~ goes off (`engslA`/`engslB` plus `eng-slupd`).
  - A choice made during a morph waits (`engpend`). The engine knob is debounced by 350 ms.
  - Morph time is `engmorphms` (hold low A + knob).
- **Voice allocation:** one voice per key. A repeated note-on first releases the key, and orphan note-offs are dropped (`engkeyon`). This fixed stuck notes after clearing the looper.
- **Loudness:** engines are level-matched within about 1.5 dB (`t_loud.py`).
- **Settings:** defaults are used only when `settings.txt` is missing. The harness resets settings before each test run, because auto-save writes into the patch folder.
- **Knob pickup:** the continuous knobs move relative to their current value (the `REL_CUR` table in `sec_ui.py`). Selector knobs jump.
- **Reverb:** 8-line Hadamard FDN with 4 input diffusers, modulated `delread4~` lines, two-band damping (bass decays 1.3× longer) and freeze.
- **CPU** (offline x86 benchmark, 8 voices sounding): engines use 2.8-6.3 % of one core. The CM3 is roughly 8-10× slower.

## What we learned from reference patches (ideas only, not code)
| Source | Idea | Status |
|---|---|---|
| VerbRack | 8-line FDN reverb, knob pickup modes, auto-save | done |
| SuperSynth | each oscillator shape in its own `switch~` subpatch | used in Hybrid (WIP) |
| vcs.cc (CC BY-NC-SA) | pitch-dependent caps on folding and drive (anti-alias), STK reed, sr/8 control block, CZ phase distortion | caps done; CZ in Hybrid |
| KnightSky | soft limiter inside the feedback loop, re-pitched freeze, exciter, OLED dirty-row redraw | ideas |
| Big Bottom (WTFPL) | wavetable band-limited saws, shared modulation bus, drift | ideas |
| Wave Folds | `pd~` for multi-core voices, crossfaded mode switches | ideas |
| DOOM_SYNTH (BSD + Commons Clause) | breath-ducked dirty parallel chains, rational tanh, pitched noise grit, spring reverb | planned: Doom × Lyra hybrid |
| Elements / Rings / Braids / Clouds (MI ports, externals) | modal tuning f·n·(1+g·n²), sympathetic strings, vowel formants, Clouds-lite granular | in Hybrid / roadmap |
| Juno-104, NESWave, DUST, Mellotron, PLAY | delayed vibrato, PWM sub, tape wow, breath-gated tape | ideas |

## Roadmap
0. **Audio looper** (`tools/dm48-engine/sec_aloop.py`, WIP, not wired in yet):
   - 6 undoable stereo layers.
   - Hold high A + knob: speed and reverse, pitch shift, level, layer fade.
   - Pre/Post recording point.
   - Syncs to the MIDI loop.
   - Scope / loop-waveform OLED view on high G#.
1. **Hybrid engine** (`tools/dm48-engine/gen_hybrid.py`, WIP). Two mode knobs:
   - SOURCE: CZ Phase, Vowel formant, Juno Pulse+sub, Breath noise.
   - BODY: Filter, Modal (Elements), Sympathetic Strings (Rings), Tube.
   - Each mode is its own `switch~` subpatch.
   - Knob 3 is Color (source) and knob 4 is Shape (body).
2. **Doom × Lyra hybrid:**
   - Lyra's cross-modulated triangles feed DOOM-style chains (RIP dist/bitcrush, TEAR phaser, METAL spring, FLESH feedback distortion), as `switch~` modes.
   - Breath moves from clean to dirty, ducked as in DOOM's sidecomp.
3. **Ideas to evaluate:**
   - Clouds-lite granular master stage, breath-driven.
   - A sympathetic-strings bus.
   - OLED dirty-row redraw.
4. **Test on the real hardware:** MIDI out, clock, CPU and the speaker pop.
