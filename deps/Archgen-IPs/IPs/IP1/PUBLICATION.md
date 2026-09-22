# Publication Provenance

Prepared for `sainadh812/2coreriscv_chipyard1` on September 9, 2026.

## Sources

- Configuration, compact evidence, and workflow scripts were copied unchanged
  from `sainadh812/chipyard_rocketconfig`, commit
  `bc5f9e9de44b0a3c198df6f92c3b068fdcfd5421`.
- Chipyard source commit:
  `e602d917dcc495c58cabe906535e411707096c9c`.
- Rocket Chip source commit:
  `55bcad0f59436de98ea510334121de8546b9e9d7`.
- The generated `DualRocketConfig` snapshot contains the exact 476 Verilog and
  SystemVerilog sources listed in
  [the recorded SHA-256 inventory](docs/dual-rocket/artifacts/rtl.sha256).
- The 24-slide presentation and its editable source were prepared separately
  on September 8 from the preserved reports. Its source hashes are recorded in
  [the slide manifest](presentations/dual-rocket-soc/slide-manifest.json).
- Original environment patches are retained under [patches](patches/README.md).
  They are historical setup material, not new RTL changes.
- The [original build reference](docs/CHIPYARD_SOC_BUILD_REFERENCE.txt) is
  retained for those historical environment notes. Its single-core results
  are not the dual-core results linked from this repository's README.

## Publication Method

The destination is a new private repository, with its initial commit preserved.
The approved GitHub connection is used to upload Git objects and advance `main`
without a force update. This is a content snapshot, not an import of all Git
history from the original repository. Publication does not claim to have run
terminal `git push`, nor does it rerun the recorded verification campaigns.

The publication inventory `publication-manifest.json` records each included
file's size, SHA-256, Git blob SHA, and executable mode, except the inventory
itself. Remote Git tree entries can be compared against these blob SHAs after
upload. Credentials, local tool installations, scratch output, and presentation
preview images are excluded.

## Scope and Reproduction

The original compact reports intentionally store source hashes instead of a
full source tree. This new repository additionally supplies the matching
generated RTL in `rtl/dual-rocket/`; those historical report descriptions are
retained unchanged to preserve their evidence hashes.

The complete generated source inventory includes simulation-only modules.
Lint and synthesis select the full hardware `ChipTop`, not `TestHarness`.
Generating or rebuilding the native simulator still requires pinned Chipyard
and its external dependencies. The included source snapshot is not a bundled
toolchain, foundry kit, standalone simulator, or physical-design result.

See [RTL snapshot usage](rtl/README.md) for source-integrity checks and the
synthesis snapshot override. Do not point `CHIPYARD_ROOT` at this publication
repository: it must identify the upstream Chipyard checkout.
