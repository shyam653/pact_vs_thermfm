# Upstream notices

The RTL is generated from Chipyard and its pinned dependencies. Original
license texts are copied unchanged into `licenses/`; the component commits
and license hashes are recorded in
[`generation.json`](../docs/artifacts/generation.json). Generated source
comments and notices are retained. `LICENSE.SiFive` accompanies the RTL
resources that reference it.

The pinned NVDLA wrapper repository contains no top-level standalone
`LICENSE`, `COPYING` or `NOTICE` file, although some source headers refer to
one. Its existing file headers are preserved. The nested NVIDIA hardware
repository does supply a license, and that text is included here. This is
not a claim that a missing wrapper-wide license was supplied or that the
nested license grants blanket rights to every wrapper file.

`tests/nvdla.h` preserves the upstream NVIDIA notice in the original Chipyard
header. No new blanket license is assigned to upstream code. Tool binaries
and technology libraries are external and are not redistributed.
