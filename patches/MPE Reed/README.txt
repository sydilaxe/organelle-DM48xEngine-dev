MPE Reed - breath-driven MPE synth for the Organelle (OS 5, M / S / S2)
Made for the Lekholm DM48 / DM48X MIDI harmonica.

SETUP
1. Copy the "MPE Reed" folder into your Patches folder (USB drive or SD card),
   or upload it with the OS 5 web editor.
2. Plug the DM48 into the Organelle's USB port.
3. System > MIDI Setup > Device: pick the DM48, then Save.
4. Load MPE Reed. (If you plug the DM48 in after loading, reload the patch.)
5. On the DM48: use multichannel / MPE output. Breath can be sent as
   channel pressure, poly pressure, or CC 2 / 7 / 11 - all are understood.

PLAY PAGE (default)
  Knob 1  Tone          base brightness
  Knob 2  Breath Tone   how much harder breath brightens and growls
  Knob 3  Release       fade after a note ends
  Knob 4  Space         reverb amount

SETUP PAGE (press Aux, LED lights; press again to go back)
  Knob 1  Octave        -2 .. +2
  Knob 2  Note Bend     bend range for notes on channels 2-16 (MPE default 48)
  Knob 3  Ch1 Bend      bend range on channel 1, which bends every note (default 2)
  Knob 4  Breath Curve  below 1 = easier to get loud, above 1 = needs more air
  A knob only changes its setting once you move it.
  Use System > Save Patch to keep these settings.

HOW IT HANDLES MIDI
  - Every note keeps its own channel, so bend, breath and CC74 on that
    channel shape only that note (MPE).
  - Pitch bend on channel 1 bends all notes (MPE master channel). This also
    makes a single "global" bender work with multichannel notes.
  - CC 1 adds vibrato. CC 74 changes timbre per note. CC 120 / 123 = all notes off.
  - The Organelle keys still play.
  - Bottom screen line shows what is arriving: e.g. "ch 3 E5 vel 90",
    "ch 3 CC2 87", "ch 1 bend -0.5". Use it to check the DM48's settings.

8 voices. Pure Data vanilla only, no externals.
