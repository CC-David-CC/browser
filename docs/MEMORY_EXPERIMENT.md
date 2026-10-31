# Gecko initial-memory experiment

The shipping engine imports a shared WebAssembly memory with an encoded minimum
of 8,192 64-KiB pages (512 MiB). An isolated non-release link on r730 changed
only `-sINITIAL_MEMORY=536870912` to `-sINITIAL_MEMORY=268435456` in a copy
of the pinned, already patched `gecko.js/build-lib.sh`. It reused the same
`obj-full-emscripten`, Firefox and patched Emscripten inputs through symlinks;
its output and build directory were separate. `GECKO_RELEASE=` and
`GECKO_DATA_ZSTD_LEVEL=3` were used, with the pinned Node and Emscripten paths
explicitly added to PATH. The first attempt failed because Node was not on
PATH; the retry linked successfully. `wasm-objdump` reported an imported
minimum of 4,096 pages (256 MiB). Output SHA-256 values were:

- `gecko.js`: `26ecdf841da2fd5e4519b9e82469d4e450a874051ee3f47b7c0c4f452d09c22c`
- `gecko.wasm`: `a6071973216038ca692dce82806a175fffb4d362fbf0f9ddcada838226d1465b`
- `gecko.data`: `db3dccc65715d273a52d2bda06a4c5159e6cf28646d420cdc187229e115161d5`

This was an experiment, not a staged or shipped engine. The candidate's real
Gecko worker rendered a 128 MiB HTML file, refused a file one byte over,
opened a 3 MiB My files document, and completed a signed relay and URL-save
workflow. A McMaster page rendered after five navigations. A single headless
Moonpie startup sample showed a largest Chrome process of about 1,011 MiB RSS
at ready, versus 1,463 MiB in the earlier 512 MiB baseline; after loading
example.com the samples were 1,114 and 1,081 MiB respectively. These are
individual RSS snapshots on different origins and cache states, not peak or
unique resident-memory measurements; they do not prove a persistent saving.

For a separate local comparison, the worker was instrumented to log the
actual shared `WebAssembly.Memory.buffer.byteLength` after native commands.
The 256 MiB candidate had grown to 477,560,832 bytes by its first sample and
to 2,154,823,680 bytes after the 128 MiB HTML test. The shipping 512 MiB
engine showed 536,870,912 and 2,137,980,928 bytes in the same test. These
numbers describe WebAssembly address-space size, not physical RAM. The test
file was mostly a large HTML comment, and results are not representative of
all documents or devices. Both candidates handled it on the development
machine, not on a physical phone or Moonpie.

Lowering the initial reservation alone did not demonstrate lower sustained
memory, while it introduces a newly linked engine and additional qualification
and license-source work. The live engine remains unchanged. Follow-up work
should measure resident and peak memory under a controlled, repeatable workload
and investigate native parsing/allocation of large documents before choosing a
new default. Temporary generated binaries and the isolated build were removed.
