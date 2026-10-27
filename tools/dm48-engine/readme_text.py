README = """DM48 ENGINE  -  breath synth host, MIDI looper and DM48X tuning library
for the Critter & Guitari Organelle (OS 5)  -  made for the Lekholm DM48X
(Full manual: DM48 Engine Manual.pdf)

SETUP
 1. Copy the "DM48 Engine" folder into Patches (USB drive / SD card / web editor).
 2. Plug the DM48X into USB. System > MIDI Setup > Device: DM48X > Save.
 3. DM48X: MIDI channel = Multich. 2-13, Mono/poly = Poly, Double notes = Allow,
    Breath CC# = 11 (default) or Aftertouch. Breath sens must not be Off.
 4. Load DM48 Engine. (Plugged in later? Reload the patch.)

KEYS  (the Organelle keyboard is a control surface; play the DM48X)
 Low octave:  C PLAY  C# LIBRARY  D SHAPE  D# panic  E FX  F SETUP  G TUNE  A ENGINE
              A# loop undo   B loop stop/start
 High octave: C freeze  C# delay throw (hold)  D octave down  D# octave up  E wet only
              F tap tempo  F# arpeggiator  G arp permutations
              G# screen view (pages > scope > loop waveform)
              A audio loop rec/play/dub (hold 1 s = clear)  A# audio undo  B audio stop/start
 D# PANIC: notes off, loops stop (kept), freeze/throw/arp off, delay and reverb emptied.
 Keys act when released. Hold a key and turn a knob for a combo:
   B + knob   loop speed: centre normal, left = reverse (faster further left),
              right = forward (faster further right). MIDI clock follows.
   C + knob   reverb size      C# + knob  throw feedback     E + knob  reverb amount
   F + knob   tempo 40-200     F# + knob 1 arp rate, knob 2 pattern, knob 3 octaves
   high A + knob 1 audio loop speed/reverse, 2 pitch, 3 level, 4 layer fade
   high B + knob  audio loop records Pre / Post effects
   Audio overdubs keep the speed they were recorded at (tape style): dub at 2x, play at 1x = an octave down.

AUX / FOOTSWITCH = LOOPER
 tap: record > play > overdub > play ...   hold (0.7 s): clear.  On LIBRARY, Aux sends.

PAGES (knobs 1-4)
 PLAY    the engine's four knobs           SHAPE   Breath>Tone, Body, Release, Breath Curve
 FX      Delay, Feedback, Delay Mix, Reverb (limiter always on)
 SETUP   Octave, Note Bend, Ch1 Bend, Vibrato rate (CC 1 = vibrato depth)
 TUNE    Family, Scale (78 scales in 10 families: Western, Temperament, Gamelan, African,
         Japanese, Chinese, SE-Asian, Maqam, Indian, Byzantine), Key. Scales retune each note.
 ENGINE  Engine, MIDI MPE/Standard, Level, MIDI out (Off / Echo / Echo+Clock); line 4 = MIDI in
 LIBRARY Knob 1 picks a tuning in tunings/, Aux sends it (DM48X: Tuning editor > Receive tuning)

SCREEN
 Top strip: [page tabs] [loop bar] [arp dot] [breath meter]
 Rows 1-4 (PLAY style): knob number, value bar, name and value. Line 5: page + looper.

ENGINES (engines/ folder; add your own - see engines/README.txt)
 All engines load at start-up; switching while playing is a quick, pop-free fade (held notes carry over).
 volt   raw/electric      Fold Grit Detune Tone
 halo   ethereal/resonant Shimmer Resonance Air Bloom
 under  bass/subharmonic  Subs Drive Tone Octave
 velvet lush VA pad       Cutoff Spread Swell Warmth
 steel  pedal steel string Tone Sustain Steel Bow
 lyra   LIRA-8 drone voice Mod Sharp Detune Drive

Steel is after Steelie by gur_shulman (WTFPL); Lyra is after LIRA-8 by Miguel Moreno (BSD licence).

While a tuning is sent, MIDI from the DM48X is ignored (until 0.6 s after), so its replies can't sound.\nScale data: the Astral patch (76 scales, normalised to C).
Saving: automatic, 2 s after a change (settings.txt + engines.txt in the patch folder). System > Save Patch also works.
Knobs: smooth settings pick up from their current value (no jumps when you change page).
Sending a tuning whose name ends in a key (e.g. 'Richter Low D') also sets the TUNE Key.
Reverb: 8-line feedback delay network (after VerbRack), freeze, size = decay time.
"""
