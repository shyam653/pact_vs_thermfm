# Shared hardware workflows

These tools operate on a provisioned Chipyard checkout at the revision pinned
by each IP. Generated RTL, native simulators, test binaries and large synthesis
intermediates are built outside the published source snapshots.

| Tool | Purpose |
| --- | --- |
| `build-soc.sh` | Check the accelerator pin and recorded patches; generate RTL and build the native simulator |
| `export-soc.py` | Copy unchanged generated sources, metadata, component pins and upstream notices |
| [CPU regression](cpu-regression/README.md) | Rebuild and run the applicable 422-test RV64 inventory; retain diagnostics and retries |
| [Lint and synthesis](accelerator-soc/README.md) | Check the complete ChipTop hierarchy and report the actual memory-mapping scope |
| [Checkpoint mapping](checkpoint-synthesis/README.md) | Independently map a verified pre-ABC design with explicit ABC commands and full mapped-design/link checks |
| `validate-ip.py` | Check publication evidence, hashes, documentation links and staged Git contents |

The IP's own `tests/README.md` describes accelerator workloads, numerical
references and required negative controls. CPU, accelerator and build reports
must identify the same simulator. Configured CPU tests must pass, and a
previously passing CPU test becoming nonpassing blocks publication. Unsupported
instruction probes and inherited legacy test defects remain explicit raw
diagnostic outcomes.

After all reports and documentation are complete, create the publication
manifest, stage the intended files and verify their actual staged bytes:

```bash
python3 scripts/validate-ip.py IPs/IP2 --write-manifest
git add IPs/IP2 scripts README.md .gitignore
python3 scripts/validate-ip.py IPs/IP2 --check-index
```

Select `IPs/IP3` for the subsequent NVDLA package. The index check rejects
ignored or omitted evidence, extra staged files within the selected IP or
shared tools, and staged bytes that differ from the validated files. The
manifest retains shared-tool hashes from publication; later IPs can evolve
those tools without changing an earlier IP's original evidence.

Original generated RTL, upstream licenses and archived logs may contain
whitespace flagged by `git diff --check`. Preserve their recorded bytes.
Review authored changes separately and resolve their relevant diagnostics.
