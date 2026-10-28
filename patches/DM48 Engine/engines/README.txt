MAKING AN ENGINE
================
An engine is one Pd patch in this folder: engines/NAME.pd. It is ONE voice; the host
loads a copy into each of its 8 voices. Copy an existing engine and change it.

Inlets (left to right) - each receives "value ms" pairs, ready for [line~]:
  1 pitch    MIDI note number, fractional (bends, tuning and octave already included)
  2 level    0..1 - breath (or velocity), already curved. 0 with the release time at note-off.
  3 timbre   0..1, 0.5 = neutral (MPE CC74 / slide)
  (A pitch message with time 0 marks the start of a new note - e.g. reset a phase or pluck on it.
   With glide (VOICE page) a new note sends "source 0" then "pitch glide-ms"; a legato change in
   Mono mode only sends "pitch glide-ms": no new attack.)
Outlet: one [outlet~], mono.

Shared values you can read anywhere in the engine:
  [r~ eng-p1~] .. [r~ eng-p4~]  the 4 PLAY knobs, 0..1, smoothed   ([r eng-p1] .. control rate)
                 (the bundled engines write this as [r~ $1-p1~]: the host creates every engine with
                  the argument "eng", so it is the same thing)
  Every engine in the folder is created once when the patch loads and switched off until selected,
  so keep idle engines cheap: nothing runs while another engine is selected.
  [r~ eng-bamt~]  SHAPE Breath>Tone, 0..1: scale your breath-to-timbre effects by this
  [r~ eng-body~]  SHAPE Body, 0..1: suggested sub / fundamental level
  [r~ eng-vib]    vibrato in semitones - add it to the pitch
  [r~ eng-sawk]   sample rate / 2.5, for lib/bsaw (band-limited saw)
Helpers: lib/bsaw.pd (band-limited saw: [lib/bsaw] inlets freq~, [r~ eng-sawk] / freq~).

engines/NAME.txt (optional):
  line 1: the 4 knob names shown on the PLAY page (one word each)
  line 2: their default values 0..1
e.g.   Fold Grit Detune Tone;
       0.3 0.2 0.4 0.5;

Tips: keep it light (8 copies run at once). Prefer native signal objects (+~ *~ min~ mtof~ ...)
over [expr~]: expr~ is several times slower on the Organelle's ARM CPU. Let breath (the level inlet) shape several
things a little - brightness, harmonics, noise, detune - rather than one thing a lot.
After adding a file, reload the patch; the new engine appears on the ENGINE page.
