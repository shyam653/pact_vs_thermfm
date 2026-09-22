# RTL generation and simulator build

The initial RTL-generation command completed successfully and is retained as
`initial-generation.log` with its exit code. The final build wrapper completed
with exit zero for generation, simulator make, and the overall workflow.
Those final make checks reused the matching generated RTL and compiled native
objects; their brief logs must not be presented as a clean rebuild benchmark.
The exact simulator used by the subsequent tests is identified by SHA-256.

Source pins, the intentional Scala configuration, worktree status, tool versions
and timestamps are in `provenance.txt`. The FFT generator patch is empty because
upstream generator code was not edited. Initial elaboration retains the existing
serial-PHY/device-tree warnings, deprecated verification-operation warnings, and
FFT vector-index width warnings. The empty simulation-memory metadata check
reported an ignored make status before the normal empty-model-memory handling;
the generated DUT memory configuration is nonempty and separately validated.

Paths in these exported logs use `${REPO_ROOT}` and `${CHIPYARD_ROOT}`.
`export-hashes.json` records both the original bytes and the normalized exports.
RTL-source hashes and original metadata are in `../../artifacts/`.
