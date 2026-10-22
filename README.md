# Organelle development

Pure Data patches for the **Critter & Guitari Organelle M** (Raspberry Pi CM3, Organelle OS 5, Pd 0.53),
built for the **Lekholm DM48X** MIDI harmonica (MPE + breath).

## Patches (`patches/`)

Copy a folder into the Organelle's `Patches` folder (USB stick or SD card).

| Patch | What it is |
|---|---|
| **DM48 Engine** | The main project. An 8-voice MPE breath synth host with plug-in engines (Volt, Halo, Under, Velvet, Steel, Lyra). Includes an MPE MIDI looper (reverse/speed), a breath arpeggiator, delay, an FDN reverb with freeze and a limiter, MIDI echo and clock with tap tempo, 78 scales in 10 families (just intonation, world tunings) and a DM48X tuning librarian. Manual: `docs/DM48 Engine Manual.pdf`. |
| MPE Reed | First MPE breath patch (PLAY-style). |
| MPE Super | Electronic, Colossus-style MPE patch. |
| MPE Super JI A / Bb / C / D | MPE Super in just intonation in four keys. |
| DM48X Tunings | Standalone tuning-table sender for the DM48X (`.mid` files). |

## Source (`tools/`)

The patches are **generated** by Python scripts, so they can be rebuilt and tested. The Organelle itself only runs the `.pd` files.

- `tools/dm48-engine/`: generator for DM48 Engine.
  - `./build.sh` rebuilds `patches/DM48 Engine` and the manual.
  - `gen_all.py` assembles the patch; `gen_engines.py` holds the engines and `engines/README.txt` (the engine contract); `sec_*.py` are the host sections (MIDI, keys, looper, UI, library, audio FX, MIDI out, arpeggiator, OLED); `make_scales.py` and `astral_scales.json` hold the scale data.
  - Tests: `t_*.py` with `harness.py`, which runs the patch offline in Pd with timed events and records audio. `tload.sh` is a quick load check.
  - `gen_hybrid.py` is a **work in progress** (Hybrid engine, see NOTES.md).
- `tools/early-patches/`: generators for MPE Reed, MPE Super, the DM48X Tunings sender and the tuning `.mid` files.

Requirements for building and testing: Python 3, numpy, Pure Data 0.53+ (`pd -batch`), and Chromium for the manual PDF.

## Notes

See **[NOTES.md](NOTES.md)** for design decisions, Pd and Organelle gotchas, the DM48X tuning format, what we learned from reference patches, and the roadmap.

## Credits

- Scale data adapted from the **Astral** patch's scale library.
- **Steel** is after *Steelie* by gur_shulman (WTFPL).
- **Lyra** is after *LIRA-8* by Miguel Moreno (BSD).
- The reverb design follows *VerbRack* (an 8-line FDN). It is a reimplementation; no code was copied.
- Other reference patches were studied for ideas only, and none of their files are included.
