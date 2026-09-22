# Generated Hardware Evidence

These small files were copied byte-for-byte from the completed upstream
`DualRocketConfig` generation. `artifacts.sha256` verifies those copies;
`rtl.sha256` lists all 476 `.sv`/`.v` files relative to `gen-collateral/` in
bytewise filename order. The RTL itself remains in the external Chipyard build.
The original `.top.mems.conf` includes trailing field separators. They are
preserved, with a Git whitespace-check exception scoped to that generated
artifact; no authored source or lint warning is waived by this setting.

```bash
# From this directory:
sha256sum --check artifacts.sha256
# From the external generation's gen-collateral directory:
sha256sum --check /path/to/this/repo/docs/dual-rocket/artifacts/rtl.sha256
```

`generation.json` records the original generation event, not a fresh rebuild.
The original raw generation log and provenance file remain local; their hashes
are retained without publishing machine-local environment paths. The metadata
exporter does not alter the original hardware files or regenerate RTL.

The architecture is explained in [SOC.md](../SOC.md); the pinned source chain,
tools and commands are in [CONFIGURATION.md](../CONFIGURATION.md). Filenames
beginning `chipyard.harness.TestHarness` reflect the generator invocation. The
DUT checked by lint and synthesis is the contained `ChipTop` hierarchy.
