.PHONY: print-benchmarks print-configured-benchmarks
print-benchmarks:
	@printf '%s\n' $(bmarks)

print-configured-benchmarks:
	@printf '%s\n' $(rvd-bmark-tests) $(rvi-bmark-tests)
