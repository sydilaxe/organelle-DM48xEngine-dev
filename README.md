# Organelle development

Pure Data patches for the **Critter & Guitari Organelle M** (Raspberry Pi CM3, Organelle OS 5, Pd 0.53),
built for the **Lekholm DM48X** MIDI harmonica (MPE + breath).

## Patches (`patches/`)

Copy a folder into the Organelle's `Patches` folder (USB stick or SD card).

| Patch | What it is |
|---|---|
| **DM48 Engine** | The main project. An 8-voice MPE breath synth host with plug-in engines (Volt, Halo, Under, Velvet, Steel, Lyra). Includes an MPE MIDI looper (reverse/speed), a breath arpeggiator, delay, an FDN reverb with freeze and a limiter, MIDI echo and clock with tap tempo, 78 scales in 10 families (just intonation, world tunings) and a DM48X tuning librarian. Manual: `docs/DM48 Engine Manual.pdf`. |

## Source (`tools/`)

The patches are **generated** by Python scripts, so they can be rebuilt and tested. The Organelle itself only runs the `.pd` files.

- `tools/dm48-engine/`: generator for DM48 Engine.
  - `./build.sh` rebuilds `patches/DM48 Engine` and the manual.
  - `gen_all.py` assembles the patch; `gen_engines.py` holds the engines and `engines/README.txt` (the engine contract); `sec_*.py` are the host sections (MIDI, keys, looper, UI, library, audio FX, MIDI out, arpeggiator, OLED); `make_scales.py` and `astral_scales.json` hold the scale data.
  - Tests: `t_*.py` with `harness.py`, which runs the patch offline in Pd with timed events and records audio. `tload.sh` is a quick load check.
  - `gen_hybrid.py` is a **work in progress** (Hybrid engine, see NOTES.md).

Requirements for building and testing: Python 3, numpy, Pure Data 0.53+ (`pd -batch`), and Chromium for the manual PDF.

## Releases

Ready-to-install zips are on the **Releases** page. They are built by `.github/workflows/release.yml`.

To make a release:

```
git tag v1.0
git push origin v1.0
```

The workflow then:

1. Rebuilds DM48 Engine and its manual from `tools/`.
2. Fails if the committed `patches/` folder doesn't match the source.
3. Runs `ci_check.py`, which plays the patch offline in Pure Data and checks engines, engine switching, both loopers, undo and the tuning library.
4. Publishes the zips and the manual as a GitHub Release.

You can also run it by hand from **Actions › Release build › Run workflow**. That gives the zips as a download, without making a release. Tick **publish** (with a version such as `v1.2`) to create the tag and the release from that run instead. A release drafted on GitHub's Releases page works too: its new tag runs the workflow, which attaches the zips.

To build locally: `tools/dm48-engine/build.sh`, then `tools/package.sh v1.0`. The zips go to `dist/`.

## Notes

See **[NOTES.md](NOTES.md)** for design decisions, Pd and Organelle gotchas, the DM48X tuning format, what we learned from reference patches, and the roadmap.

## Credits

- Scale data adapted from the **Astral** patch's scale library.
- **Steel** is after *Steelie* by gur_shulman (WTFPL).
- **Lyra** is after *LIRA-8* by Miguel Moreno (BSD).
- The reverb design follows *VerbRack* (an 8-line FDN). It is a reimplementation; no code was copied.
- Other reference patches were studied for ideas only, and none of their files are included.
