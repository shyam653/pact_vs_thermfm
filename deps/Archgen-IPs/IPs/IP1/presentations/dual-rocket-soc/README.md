# Dual-Rocket SoC Presentation

A 24-slide editable technical introduction for the `sainadh812` project,
prepared on September 8, 2026 from the recorded September 6 evidence.

- [PowerPoint](Dual_Rocket_SoC_Overview.pptx)
- [PDF for phone viewing](Dual_Rocket_SoC_Overview.pdf)
- [Speaker notes and source references](speaker-notes.md)
- [Slide manifest and source hashes](slide-manifest.json)

The deck covers the existing upstream configuration, build process, logical
SoC block diagram, core features, caches and memory, interfaces, memory map,
multicore behavior, hardware versus simulation scope, test results, lint,
SRAM adaptation, synthesis, limitations, and possible next configurations.
Diagrams and charts use editable PowerPoint shapes. The PDF preserves the
rendered slides but does not include the PowerPoint speaker notes.

No RTL, simulation, lint, or synthesis was rerun or modified to prepare the
presentation. The deck is a derivative explanation, not a replacement for
the [detailed reports](../../docs/dual-rocket/README.md). The current design
does not contain an FFT accelerator. Area is library cell area, not die area;
500 MHz is nominal configuration intent, not a verified CPU frequency.

## Rebuild

From this directory, using Python 3.10 or later:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build_deck.py
libreoffice --headless --convert-to pdf --outdir . Dual_Rocket_SoC_Overview.pptx
.venv/bin/python validate_deck.py
```

LibreOffice must be installed separately. The recorded render used a user-local
LibreOffice 7.3.7.2 installation and DejaVu Sans / DejaVu Sans Mono fonts.
The builder expects those fonts in `/usr/share/fonts/truetype/dejavu` by default;
set `DEJAVU_FONT_DIR` to their directory on another system. Install the fonts
for LibreOffice too. No rendering binaries or font files are bundled here.

The builder checks the reported simulation counts, key synthesis/lint values,
and the generated RTL inventory; it hashes all 18 cited local source files.
The validator checks those hashes, all 24 notes pages, PDF page count, missing
rendered words, text overlaps and page bounds. It writes slide PNGs and
contact sheets under the ignored `qa/` directory for visual review.

Rebuilding these presentation files does not run an EDA tool or perform a
new processor verification campaign.
