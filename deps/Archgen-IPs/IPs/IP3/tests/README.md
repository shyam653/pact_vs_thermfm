# NVDLA tests

Build the exact SoC first with the repository's `scripts/build-soc.sh` and the
`IPs/IP3` configuration directory. The script installs the recorded NVDLA
patches and captures generator/compiler provenance.

Build accelerator programs using the generated DTS:

```bash
python3 IPs/IP3/scripts/build-nvdla-tests.py \
  --chipyard-root "$CHIPYARD_ROOT" \
  --dts /path/to/chipyard.harness.TestHarness.DualRocketNVDLAConfig.dts \
  --output /path/to/new-nvdla-test-build
```

Run the positive manifest with the shared regression runner:

```bash
python3 IPs/IP2/scripts/run-regression.py \
  /path/to/new-nvdla-test-build/manifest.tsv \
  /path/to/new-nvdla-campaign \
  --chipyard-root "$CHIPYARD_ROOT" \
  --simulator "$CHIPYARD_ROOT/sims/verilator/simulator-chipyard.harness-DualRocketNVDLAConfig" \
  --max-cycles 3000000 --timeout 2400 --jobs 1 --seed 1
```

Repeat normal campaigns with seeds 2 and 3 in fresh output directories. The
firmware also checks `nv_small`'s SDP capability, zero data readback after a
nonzero write to its absent SDP LUT, and all five zero LUT counters after
each completed SDP job. These checks are separate from the supported CDP LUT
identity/doubling jobs. Numerical results, guards and the 22-job completion
sequence remain mandatory.

Also run the supported ISA, CPU benchmark and two-hart software manifests
against this same IP3 simulator. Run the two negative-control binaries
separately, retaining their failure logs and checking the intended failure
markers. A simulator exit alone is not sufficient to establish the expected
negative-control behavior.

`nvdla.h` is copied unchanged from the pinned Chipyard `tests/nvdla.h` and
retains its NVIDIA copyright/license notice. `start.S` and `link.ld` use the
same freestanding two-hart startup as IP2. No Linux, driver, proxy kernel or
libgloss runtime is required.

See [integration and coverage](../docs/INTEGRATION.md) and
[upstream test inventory](../docs/UPSTREAM_TESTS.md) for the scope of these
programs and why the large upstream INT16 traces are not directly runnable
on nv_small.
