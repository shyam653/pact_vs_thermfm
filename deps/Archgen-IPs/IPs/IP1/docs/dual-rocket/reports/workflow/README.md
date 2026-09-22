# Workflow Validation

These checks test automation behavior, not Rocket RTL functionality.

## Actual Cached Generation Invocation

After fresh synthesis and its source-integrity audit had completed, the
published generation wrapper was invoked against the real prepared checkout at
2026-09-06T13:52:34Z. Make reported that `verilog` was already up to date;
this was **not** a new elaboration or a clean build. The make, source-check,
and overall workflow statuses were all 0. All 476 source hashes and the exact
source inventory matched the published generation.

[generation-wrapper.json](generation-wrapper.json) retains the result and raw
log hashes. The original generation event remains separately documented in
[generation.json](../../artifacts/generation.json).

## Generation Wrapper Negative Controls

Four isolated checks of the published `generate.sh` passed on 2026-09-06.
The fixtures substituted fake Git, Java, firtool, and make executables. They
did not change the real Chipyard checkout or invoke real generation tools.

| Fixture | Expected behavior, observed |
| --- | --- |
| Successful make, missing RTL | Make status 0; source and overall status 1 |
| Successful make, incorrect RTL hashes | Make status 0; source and overall status 1 |
| Make failure | Process, make, and overall status 23; no source check attempted |
| Existing provenance | Refuse before invoking tools; retain all previous bytes |

[generation-negative-controls.json](generation-negative-controls.json) is a
byte-identical copy of the compact local test summary, including the wrapper
and source-manifest hashes. Its `evidence` fields identify external fixture
directories; fixture trees and logs are not committed. In the overwrite test,
the retained overall value 88 was an intentional sentinel from old evidence,
not the exit status of the new rejected invocation.

## Other Checks

The [lint report](../lint/README.md) documents malformed/missing diagnostics,
tool-error and no-overwrite checks. The [synthesis report](../synthesis/README.md)
documents memory-metadata rejection and the isolated path-handling preflight.
These infrastructure controls are separate from the actual RTL lint, SRAM
comparisons, full-SoC synthesis, and prior software simulation campaign.

`python3 scripts/dual-rocket/validate-publication.py` checks the published text
package, including local links, JSON syntax, source inventories and evidence
hashes. It does not execute a hardware simulator or synthesis tool.
