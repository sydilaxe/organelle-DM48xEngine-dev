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
- **Never put `[s~]` in a subpatch that gets switched off**: it keeps sending its last 64-sample block, which is a loud ~690 Hz tone. Use `[throw~]`/`[catch~]` (a switched-off throw~ adds nothing). This was the tone after clearing the audio loop.
- **Signal objects:**
  - `vcf~`: the lowpass goes silent when cf/q exceeds about sr/2π. Keep q and cf in range.
  - `bob~` at oversample 1 is unstable above about 8 kHz.
  - A `delwrite~`/`vd~` feedback loop can't be shorter than one block (64 samples); use `block~ 16` for short loops.
- **CPU: avoid per-sample `expr~`** in anything that always runs. The FX, the audio looper and Feral use native objects only (`+~ -~ *~ /~ max~ min~ abs~ clip~ wrap~ mtof~`); that cut 8 Feral voices + overdub from 5.8 % to 3.6 % of an x86 core. Overdub "fuzz" on the Organelle was CPU overload (offline renders were clean). The engines' `ex()` formulas are compiled to native objects at build time by `tools/dm48-engine/sigexpr.py` (+ - * /, min, max, abs, fmod(x,1), pow, exp, sqrt, mtof; constants folded; falls back to expr~ otherwise; `NO_SIGEXPR=1` builds the old way). Renders match the expr~ build to 108-177 dB. Glitches when overdubbing with the loop pitched down were CPU (offline clean); the pitch shifter adds ~10 %.
- **CPU, round 2 (per-object costs and a 1/8-rate control block):** measured per object on x86 (64-sample blocks): `*~ +~ -~ /~ min~ line~` ≈ 0.4 ns/sample, `clip~` 0.7, `phasor~ noise~ wrap~ lop~ rpole~` 1.4-1.8, `osc~ cos~ sqrt~` 2, `exp~` 3.6, `vcf~` 5.7, `mtof~` 6.6, `pow~` 8.3. A `[block~ 8 1 0.125]` subpatch's `outlet~ lin` costs 3.9, `outlet~ hold` 1.2 (inlet~ is ~free).
  - Engines compute their costly slow signals in a `pd ctl` subpatch at sr/8 (`Ctl` in `gen_engines.py`): pitch → Hz (with drift/wander), saw rates, Halo's partial `pow~` amplitudes, Volt's and Velvet's cutoffs, Feral's puff detector / wander / vactrol / gate cutoff / VCA. **Only oscillator frequencies may leave through `outlet~ hold` (`c.f()`)**: a held (stepped) amplitude, drive or cutoff crackles when breath moves fast, and it gets recorded into the audio loop (reported on the Organelle as crackly overdubs; offline `t_clicks`-style detection shows it in Velvet). Everything else leaves through `outlet~ lin` (`c.o()`), which costs ~10 `*~`, so cheap formulas stay at full rate and VCA envelopes stay a full-rate `lop~`. Steel stays fully at full rate (nearly all its signals feed the string). One-pole coefficients inside are a^8 and differentiators ×1/8 (same time constants); noise~ into a slow lowpass is ×1/√8. No `r~` inside (block size must match its `s~`). Never feed a ctl output back into the same ctl (DSP loop).
  - `lib/bsaw`: the old naive saw + step cancelled out; removed (4 fewer objects, identical output). Dropping the wrap~ too (u = phase - 0.5) gives the same waveform half a cycle later, but changes how detuned saws line up, so it was kept.
  - Audio looper: each layer is its own `switch~` subpatch, on while its gain target is not 0 (off 100 ms after a fade to 0), out via `outlet~` (a switched-off outlet~ gives zeros). Not throw~/catch~: Pd sorts a catch~ before the throw~s, which delayed the loop by one block. Pitch shifter: the two taps' delay and window are shared by L and R. Output is bit-identical to before, except clear: its fade is now really 20 ms (the old `[$1 60(` turned "0 20" into a 60 ms fade, cut off when the looper DSP stopped at 40 ms).
  - Result (x86, % of one core above the idle FX, 8 voices, best of 3): Feral 2.07 → 1.61, Halo 2.92 → 1.73, Lyra 1.31 → 1.02, Steel 1.89 (unchanged), Under 1.00 → 0.75, Velvet 2.04 → 1.74, Volt 1.49 → 1.40. Audio looper: 1 layer 0.22 → 0.14, 3 layers 0.25 → 0.24, pitch-shifted 0.45 → 0.32, overdub 0.27 → 0.15.
- **Measuring CPU offline:** child CPU time (`resource.getrusage`) of a 100 s run minus a 10 s run (cancels start-up and the 95 MB looper allocation); wall-clock timing is too noisy.
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
- Included tunings (`make_scales.py`, 54 + Order test) sit in folders (Ambient, Chromatic, Frasil, Richter, World); LIBRARY knob 2 picks the folder (0 = All). Richter Low in all 12 keys (key note G2-F#3, slider +1 octave), Country, Paddy Richter, Harmonic Minor, Chromatic (slider = +1 semitone: Solo C/G, Low C, Augmented, Diminished), Ambient and World scales.
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
- **Audio looper** (`sec_aloop.py`):
  - **Layers:** 6 stereo layers, `engaL0..5` / `engaR0..5`, 45 s each (about 95 MB, allocated at load).
  - **Playback:** one `phasor~` playhead reads every layer, and each layer has its own gain (`engag`, used for undo and fade).
  - **Speed per layer:** each layer stores its own mapping, read index = phase × A + B. A is ±(samples per pass at the recording speed) and B is 0 or the length. Overdubs at any speed or direction therefore follow later speed changes like tape (`$0-alayset j A B`). Layers stopped before a full pass are marked `engadirty` and zeroed when reused.
  - **Writing:** one writer (`tabwrite~` with `set` / `start N`) writes the newest layer as input×gate plus existing×k. k is 0 for the first pass and 1 after that. A layer always gets at least one full pass, so a reused layer never contains old audio.
  - **Wraps:** the playhead phasor runs freely and is reset only when playback (re)starts.
    - A clock (`$0-atick`) fires about 3 ms after each wrap, scheduled from the snapshot phase, so it never drifts.
    - At each tick the writer carries on across the seam: the x samples it wrote past the layer end are copied to the start, then it continues with `start x`.
    - The writer starts at playhead + 1 sample: `snapshot~` holds the last sample of the previous block, and `tabwrite~ start` begins at the next one.
    - The overdub re-reads the old sample with `tabread~` at the rounded index, because `tabread4~` would blend in the neighbour just overwritten.
    - The first take records 12 ms extra and crossfades it into its start, so the seam is click-free.
    - `t_clicks.py` measures clicks (bursts above 8 kHz); `DBG_ALOOP=1` records a sample counter for alignment checks.
  - **Speed and pitch are continuous** (the MIDI loop speed stays in 0.1 steps: it drives the MIDI clock). Speed knob = varispeed: centre 1x, right up to 4x, left slows to 0.05x at a third of the way, then reverse to -1x at full left (|speed| >= 0.05).
  - **Pitch shift:** continuous (not in semitone steps); two crossfaded `vd~` taps in a subpatch that is switched off at 0 semitones; speed and window glide (`line~`).
  - **Tap points:** Pre `eng-tap-pre` / `eng-aret-pre` (into the FX); Post `eng-tap-postL/R` / `eng-aret-L/R` (before the limiter).
  - **DSP:** switched off until the first recording (`$0-adsp`).
- **Screen views** (`scope()` in `sec_oled.py`):
  - High G# cycles the views; the page rows are gated by `$0-rowson`.
  - Waveforms are sent as `sendtyped /oled/gWaveform ib 3 <128 y>`, as the Organelle's own patches do.
  - The scope finds a rising zero crossing in a 1024-sample capture and auto-scales.
  - The loop view draws the per-layer overviews (`engov<j>`) and the playhead.
- **Engines (no morphing):**
  - Every engine in `engines/` is created once at start-up in every voice: `eng-add index engines/NAME` makes an `[ehost]` in `pd $0-eng`.
  - Only the selected engine runs (`eng-esel`). Switching fades the old engine out over 15 ms, then the new one in.
  - Nothing is created while playing. On the Organelle, creating objects while DSP runs (the old dynamic slots and the morph) made Pd rebuild its DSP graph, and that popped.
  - Engines get the argument `eng`, so `[r~ $1-p1~]` means `eng-p1~`.
- **Panic (low D#)** sends `eng-panic`: notes off, both loopers stopped (kept), freeze, wet-only and arp off, and every `delwrite~` in the FX cleared.
- **VOICE page (low F#): legato and glide.**
  - Mono legato bypasses `[poly]`: the `mono` subpatch in `process` keeps a stack of held keys (`engmono`) and sends voice 1 "key -1" for a legato change (velocity < 0 = no new attack, glide to the new key's pitch). Releasing it goes back to the top of the stack.
  - Glide: every note start goes into a 16-entry buffer (`engpbuf` pitch, `engpbuft` time, `engpbufh` held). A new note searches notes started > 30 ms ago and glides from the nearest one (+1 semitone per second of age, so the last chord wins) or the latest one (From last). Glide legato = only held notes. `[poly]` is round-robin, so a per-voice "last pitch" doesn't work for chord glides.
  - The engine gets "source 0" then "pitch ms". A bend during a glide uses the remaining glide time.
  - VOICE values are saved after the engine name in settings.txt (`SAVED_TAIL`), so older settings files still load.
- **Feral** (built from scratch, no shared parts): capacitor-charge osc (ramp blended with a sin quarter by breath²) with poly-BLEP, hard-synced slave (wrap~(phase × ratio)), half-rate square sub, puff detector (rzero~ differentiator → rpole~ hold), vactrol LPG (max~ of breath and a slow rpole~ tail; one-poles with a = 1 − w), asymmetric diode clipper. No expr~ at all: per-sample expr~ is slow, so the first version (25 expr~) cost 2.5× the other engines.
- **Hybrid / Doom** (`gen_hybrid.py`): modes are `switch~` subpatches picked by a control knob (`modes()`: int(v × n)); selecting fades in 10 ms, deselecting fades out and switches off 20 ms later. A mode's `delwrite~`s, and the Strings body's filters, are cleared when it is switched on (`[s $0-on-<mode>]`), else old contents ring out as a click; Strings is fed through a 30 ms ramp so the combs build up. Per-mode level trims (`gains=`) keep all 16 Hybrid combinations within ~2.5 dB. Knob changes made right after an engine switch are overwritten when the engine restores its saved knobs (tests wait ~1 s). Test engine knob positions with `harness.eng_knob(name)` / `ENGINE_NAMES`, never a hard-coded count.
- **Frasil / Glint** (`gen_frasil.py`, after FRASIL, MPL-2.0: reimplemented from its design, no code copied). Frasil's three layers are `switched()` subpatches, each with its own Ctl block, so a layer turned down costs nothing; drifts are slow `osc~`s (a Ctl object costs as much as a full-rate one: keep Ctl blocks small - Frasil's first version had 272 objects there and cost 4 %). Glint is breath-played: breath sets level and FM index (squared: soft is pure); Ping (default 0) is an optional strike accent.
- **Metal / String / Wind** (`gen_jaffe.py`, ported from Jaffedrone, MIT). No plucks or strikes: breath is the rub, the bow or the mouth, and harder breath adds harmonics (checked: >4th-harmonic energy rises 12-50 dB from soft to hard breath, except the reeds, which brighten ~4 dB and get louder 6 dB). A reed model speaks at one strength above its threshold, so Wind keeps the pressure in the speaking range while there is breath (as Jaffedrone's base pressure does), lets breath open the bore's wall filter, and adds a breath-following level. The double reed needs a DC blocker in its loop (Jaffedrone's has none but its ear correction). Waveguides run in `block~ 16` subpatches (delays down to 0.37 ms).
- **Frasil tunings** (`make_scales.py` `chord_walk`): blow = one chord, draw = a second chord, plain holes the lower octave, slider +12.
- **Steel** has no pluck: breath is the bow. Knob 4 Attack = minimum rise time of the breath level (5 ms – 2 s).
- **Voice allocation:** one voice per key. A repeated note-on first releases the key, and orphan note-offs are dropped (`engkeyon`). This fixed stuck notes after clearing the looper.
- **Loudness:** engines are level-matched within about 1.5 dB (`t_loud.py`).
- **Settings:** defaults are used only when `settings.txt` is missing. The harness resets settings before each test run, because auto-save writes into the patch folder.
- **Knob pickup:** the continuous knobs move relative to their current value (the `REL_CUR` table in `sec_ui.py`). Selector knobs jump.
- **Reverb:** 8-line Hadamard FDN with 4 input diffusers, modulated `delread4~` lines, two-band damping (bass decays 1.3× longer) and freeze.
- **CPU** (offline x86 benchmark, 8 voices sounding): engines use 0.75-1.9 % of one core above the FX (see CPU round 2). The CM3 is roughly 8-10× slower.

## What we learned from reference patches (ideas only, not code)
| Source | Idea | Status |
|---|---|---|
| VerbRack | 8-line FDN reverb, knob pickup modes, auto-save | done |
| SuperSynth | each oscillator shape in its own `switch~` subpatch | used in Hybrid and Doom |
| vcs.cc (CC BY-NC-SA) | pitch-dependent caps on folding and drive (anti-alias), STK reed, sr/8 control block, CZ phase distortion | caps done; CZ in Hybrid; sr/8 control block in all engines |
| KnightSky | soft limiter inside the feedback loop, re-pitched freeze, exciter, OLED dirty-row redraw | ideas |
| Big Bottom (WTFPL) | wavetable band-limited saws, shared modulation bus, drift | ideas |
| Wave Folds | `pd~` for multi-core voices, crossfaded mode switches | ideas |
| DOOM_SYNTH (BSD + Commons Clause) | breath-ducked dirty parallel chains, rational tanh, pitched noise grit, spring reverb | done: Doom engine |
| Elements / Rings / Braids / Clouds (MI ports, externals) | modal tuning f·n·(1+g·n²), sympathetic strings, vowel formants, Clouds-lite granular | modal, strings, vowel in Hybrid; Clouds-lite on the roadmap |
| Juno-104, NESWave, DUST, Mellotron, PLAY | delayed vibrato, PWM sub, tape wow, breath-gated tape | ideas |

## Roadmap
1. **Hybrid** and **Doom** engines: done (`gen_hybrid.py`).
2. **Ideas to evaluate:**
   - Clouds-lite granular master stage, breath-driven.
   - A sympathetic-strings bus.
   - OLED dirty-row redraw.
3. **Test on the real hardware:** MIDI out, clock, CPU and the speaker pop.
