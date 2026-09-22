# Final-source buffer-helper equivalence

The exact aligned fill/check helper definitions occur unchanged in the final numerical source containing the SDP readback sanity checks. They are byte-identical to the helpers in the earlier [firmware optimization](../firmware-history/README.md).

A fresh C11 and C++17 build/run of the byte-level probe passed: every poison byte, equal buffers, a single corrupt byte at every one of 4096 indices with varied bit positions, and the first of multiple mismatches. This is not every index-by-bit combination. Captured diagnostics retain the exact hart, job, first byte index and actual/expected values.

[Metadata](summary.json) records the final C source hash, exact helper hash, fresh capture time, commands and results. [Helper definitions](helpers.inc), [probe source](probe.c), compiler logs and run logs are included. Paths use `${HELPER_BUILD}` and `${REPO_ROOT}`; executables remain in the external build directory. [Export hashes](export-hashes.json) distinguish original and portable bytes.

This focused probe tests buffer helper equivalence. The actual new absent-SDP-LUT checks and all numerical jobs are validated separately by the fresh standalone and full-SoC campaigns.
