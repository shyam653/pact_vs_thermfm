# Independent checkpoint technology mapping

`run.py` maps a verified full-SoC `ChipTop-before-abc.il` checkpoint in a fresh directory. It executes the explicit ABC sequence in `direct.abc`: `strash; &get -n; &nf; &put`. This installed Yosys does not offer `abc -fast`. This mode omits the default script’s SAT-heavy optimization passes; synthesis correctness gates still require a fully mapped design with no internal cells, unchanged SRAM count and a successful OpenROAD link with matching instance counts.

The original run remains separate. Its completed RTL hierarchy checks, SRAM simulations and pre-ABC synthesis are reused with explicit provenance. This is not a fresh RTL-to-checkpoint run or full-SoC formal equivalence. Completed historical origins must have a successful summary and matching indexed checkpoint hash. Every historical source input must still match except an explicitly named documentation-only `README.md` mismatch supplied with `--allow-changed-document`. Current observed inputs, executable scripts, libraries, checkpoints and native binary files must remain unchanged throughout the independent mapping.

To produce a fresh checkpoint, start the [original synthesis workflow](../accelerator-soc/synthesis/README.md) in its own output directory. Once its map log enters the ABC stage, the pre-ABC checkpoint has been written and the earlier checks are complete; run this helper in a second terminal against that active origin. Keep the origin's input files unchanged. After the independent run passes, the separate default optimizer may be stopped. This helper accepts active origins or successful completed origins; it deliberately rejects an already failed/stopped origin. The archived stopped IP2 attempt is provenance, so replay requires a newly generated origin or a successful compatible historical origin.

```bash
python3 scripts/checkpoint-synthesis/run.py \
  --origin "$ORIGINAL_SYNTHESIS_OUTPUT" \
  --output "$FRESH_DIRECT_MAPPING_OUTPUT" \
  --platform "$ORFS_ROOT/flow/platforms/nangate45" \
  --suite "$OSS_CAD_SUITE_ROOT" \
  --openroad "$OPENROAD" \
  --openroad-native "$OPENROAD_NATIVE_BINARY"
python3 scripts/checkpoint-synthesis/export-report.py \
  "$FRESH_DIRECT_MAPPING_OUTPUT" "$FRESH_REPORT_DIRECTORY" \
  --comparison "$COMPLETED_BASELINE_DIRECT_MAPPING_OUTPUT"
```

The optional comparison requires successful direct mapping of the baseline, identical ABC commands, identical five Liberty/LEF inputs and identical native tools. Baseline provenance should be exported to a separate sibling report directory so its RTL hash entries cannot be confused with the new SoC. Raw netlists, checkpoints and OpenROAD databases remain outside Git; compact reports preserve their hashes. These Nangate45/fakeram45 results are exploratory and have no timing constraints, placement or routing.

For a run that preserves generic accelerator memories, compare the actual ABC checkpoints with:

```bash
python3 scripts/checkpoint-synthesis/audit-memory-contracts.py \
  "$SYNTHESIS_OUTPUT/ChipTop-before-abc.il" \
  "$SYNTHESIS_OUTPUT/ChipTop-after-abc.il" \
  "$FRESH_MEMORY_CONTRACT_REPORT"
```

The audit checks every `$mem_v2` parameter exactly, including initialization and clock, transparency, collision and X masks; it rejects added, removed or changed memory cells. Its report records both checkpoint hashes, the audit script hash and per-parameter hashes. The scope is pre-ABC to post-ABC parameter preservation. It does not establish RTL-to-memory inference or formal equivalence of logic surrounding the ports.

`probe-cleanup.py ORIGIN FRESH_OUTPUT --timeout-seconds 300` is a bounded diagnostic
for an original frontend that checks before removing unused logic. It reuses the
identical frontend/hierarchy commands and inserts `opt_clean -purge` before the
same `check -assert`, retaining before/after RTLIL and statistics. Run
`audit-cleanup.py FRESH_OUTPUT` to compare every module port, memory declaration,
memory-cell type and complete parameter dictionary, and inventory output-free
TileLink monitor logic removed by cleanup. This diagnostic has its own provenance
and does not claim technology mapping or formal equivalence. The full workflow
now records early cleanup explicitly; previously consumed scripts must be
preserved when changing an active run's workflow.

The current full workflow records its own original-memory cleanup checkpoints.
Audit the actual flow without rerunning a diagnostic frontend:

```bash
python3 scripts/checkpoint-synthesis/audit-cleanup.py "$SYNTHESIS_OUTPUT" --stage elaborate
```

This report identifies `ACTUAL_FULL_FLOW_FRONTEND`, verifies current source
identities and the mandatory frontend CHECK, and compares the full recorded
contracts. Full mapping acceptance remains a separate required gate.
