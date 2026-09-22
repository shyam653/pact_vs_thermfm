# Upstream NVDLA test applicability

Inventory inspected at wrapper revision
`d99ffdc79bbf9b86c6cad0c278a785d5802c8209`, hardware revision
`8e06b1b9d85aab65b40d43d08eec5ea4681ff715`.

| Bundled test(s) | Engine(s) | Applicability to this nv_small SoC |
| --- | --- | --- |
| Chipyard `tests/nvdla.c` | CDP DMA/LUT | Adapted into bounded, checked jobs; original addresses `0x90000000` and `0x90080000` are outside IP1/IP3's `0x80000000`–`0x8fffffff` memory window. Original has no data/output checks and returns success even after polling expires. |
| `sanity0`, `sanity1`, `sanity2` | BDMA | BDMA is absent in nv_small. |
| `sanity1_cvsram`, `sanity2_cvsram` | BDMA/CVSRAM | BDMA and the secondary CVSRAM interface are absent. |
| `sanity3`, `conv_8x8_fc_int16` | Convolution/SDP | Large INT16 traces; nv_small is INT8-only with C=K=8. A new INT8 dot-product workload uses the same engine programming sequence with supported dimensions. |
| `sanity3_cvsram`, `cc_alexnet_conv5_relu5_int16_dtest_cvsram` | Convolution/SDP/CVSRAM | INT16 and CVSRAM requirements do not match this implementation. |
| `googlenet_conv2_3x3_int16` | Convolution/SDP | INT16 trace, incompatible numeric mode. |
| `sdp_relu_int16` | SDP/RDMA | INT16 trace; replaced by independent checked INT8 ReLU and arithmetic jobs. |
| `pdp_max_pooling_int16` | PDP/RDMA | INT16 trace; not directly applicable. Independent INT8 max/min 2x2 pooling jobs use supported dimensions and precision. |

The traceplayer's `0xffff....` register addresses are word-index encodings
for its older trace interface, not direct CPU MMIO addresses. Porting a
trace requires mapping named registers through the selected nv_small decode,
repacking tensors for eight-byte memory atoms, adapting dimensions/precision,
and respecting the real SoC memory map. Changing only an address prefix is
not sufficient.

Upstream traces are smoke/sanity examples, not an exhaustive test suite.
Unsupported configurations are listed as inapplicable, never reported as
passing IP3 tests. Physical SRAM replacement, asynchronous clock crossings,
Linux driver/compiler integration, large networks and all precision modes
are outside the numerical jobs in this package.
