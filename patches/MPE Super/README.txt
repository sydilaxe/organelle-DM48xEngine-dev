MPE Super - big detuned-saw MPE synth for the Organelle (OS 5, M / S / S2)
Made for the Lekholm DM48 / DM48X MIDI harmonica. Breath opens the filter.

SETUP
1. Copy the "MPE Super" folder into your Patches folder (USB drive or SD card),
   or upload it with the OS 5 web editor.
2. Plug the DM48 into the Organelle's USB port.
3. System > MIDI Setup > Device: pick the DM48, then Save.
4. Load MPE Super. (If you plug the DM48 in after loading, reload the patch.)
5. On the DM48: use multichannel / MPE output. Breath can be sent as
   channel pressure, poly pressure, or CC 2 / 7 / 11 - all are understood.

SOUND
  Per note: three band-limited saws (detuned against each other) + a sine sub
  one octave down -> Moog-style ladder filter (Pd's bob~) -> amp.
  Breath sets loudness AND sweeps the filter open. Stereo chorus + reverb.

Aux cycles the knob pages (LED: off / color / other color):

PLAY
  Knob 1  Cutoff          filter base
  Knob 2  Resonance       filter peak / squelch
  Knob 3  Detune          saw spread: 0 = one clean saw, up = huge
  Knob 4  Space           chorus + reverb

SHAPE
  Knob 1  Breath>Filter   how far breath opens the filter
  Knob 2  Sub Osc         sine one octave down
  Knob 3  Release         fade after a note ends
  Knob 4  Breath Curve    below 1 = easier to get loud, above 1 = needs more air

SETUP
  Knob 1  Octave          -2 .. +2
  Knob 2  Note Bend       bend range for channels 2-16 (MPE default 48)
  Knob 3  Ch1 Bend        bend range on channel 1, bends every note (default 2)
  Knob 4  Vibrato Rate    speed of the CC 1 vibrato

  On SHAPE and SETUP a knob only changes its setting once you move it.
  System > Save Patch keeps SHAPE and SETUP values (settings.txt).

HOW IT HANDLES MIDI
  - Every note keeps its own channel, so bend, breath and CC74 on that
    channel shape only that note (MPE). CC74 also moves that note's cutoff.
  - Pitch bend on channel 1 bends all notes (MPE master channel).
  - CC 1 adds vibrato. CC 120 / 123 = all notes off.
  - The Organelle keys still play.
  - Bottom screen line shows what is arriving: "ch 3 E5 vel 90", "ch 3 CC2 87".

6 voices. Pure Data vanilla only (bob~ ships with Pd), no other externals.
