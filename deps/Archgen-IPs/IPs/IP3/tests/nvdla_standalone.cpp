/* SPDX-License-Identifier: Apache-2.0
 * Supplemental engine simulation. The PLIC is emulated here; its real routing
 * and CPU/cache coherence are verified only by nvdla_test.c in the full SoC.
 */
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <deque>
#include <stdexcept>
#include <sys/mman.h>
#include "Vnvdla_small.h"
#include "verilated.h"
#define NVDLA_STANDALONE 1
#define NVDLA_IRQ 1
#include "nvdla_test.c"

static Vnvdla_small *dut_pointer;
#define dut (*dut_pointer)
static uint64_t cycles;
static bool apb_ready;
static uint32_t apb_data;
struct burst { uint64_t address; unsigned id, remaining; };
static std::deque<burst> reads, writes;
static std::deque<unsigned> responses;
static bool r_held, b_held;

static uint8_t *checked_memory(uint64_t address, unsigned bytes) {
    uintptr_t bases[] = {(uintptr_t)src_storage, (uintptr_t)dst_storage,
                         (uintptr_t)weight_storage, 0x08000000};
    size_t sizes[] = {sizeof(src_storage), sizeof(dst_storage), sizeof(weight_storage), 65536};
    for (unsigned i = 0; i < 4; ++i)
        if (address >= bases[i] && address - bases[i] + bytes <= sizes[i])
            return (uint8_t *)(uintptr_t)address;
    fprintf(stderr, "Unexpected DMA address 0x%lx length=%u cycle=%lu\n", address, bytes, cycles);
    throw std::runtime_error("DMA outside registered test buffers");
}
static void tick() {
    if (++cycles > 20000000) throw std::runtime_error("standalone cycle timeout");
    dut.core_clk = 0;
    dut.nvdla_core2dbb_aw_awready = writes.size() < 16 && cycles % 11 != 0;
    dut.nvdla_core2dbb_w_wready = !writes.empty() && cycles % 13 != 0;
    dut.nvdla_core2dbb_ar_arready = reads.size() < 16 && cycles % 7 != 0;
    if (!b_held && !responses.empty() && cycles % 5 != 0) b_held = true;
    if (!r_held && !reads.empty() && cycles % 3 != 0) r_held = true;
    dut.nvdla_core2dbb_b_bvalid = b_held;
    dut.nvdla_core2dbb_b_bid = responses.empty() ? 0 : responses.front();
    dut.nvdla_core2dbb_r_rvalid = r_held;
    dut.nvdla_core2dbb_r_rid = reads.empty() ? 0 : reads.front().id;
    dut.nvdla_core2dbb_r_rlast = !reads.empty() && reads.front().remaining == 1;
    dut.nvdla_core2dbb_r_rdata = 0;
    if (!reads.empty()) memcpy(&dut.nvdla_core2dbb_r_rdata, checked_memory(reads.front().address, 8), 8);
    dut.eval();
    bool aw = dut.rstn && dut.nvdla_core2dbb_aw_awvalid && dut.nvdla_core2dbb_aw_awready;
    bool w = dut.rstn && dut.nvdla_core2dbb_w_wvalid && dut.nvdla_core2dbb_w_wready;
    bool ar = dut.rstn && dut.nvdla_core2dbb_ar_arvalid && dut.nvdla_core2dbb_ar_arready;
    bool b = dut.nvdla_core2dbb_b_bvalid && dut.nvdla_core2dbb_b_bready;
    bool r = dut.nvdla_core2dbb_r_rvalid && dut.nvdla_core2dbb_r_rready;
    burst next_aw{dut.nvdla_core2dbb_aw_awaddr, dut.nvdla_core2dbb_aw_awid,
                  (unsigned)dut.nvdla_core2dbb_aw_awlen + 1};
    burst next_ar{dut.nvdla_core2dbb_ar_araddr, dut.nvdla_core2dbb_ar_arid,
                  (unsigned)dut.nvdla_core2dbb_ar_arlen + 1};
    uint64_t wdata = dut.nvdla_core2dbb_w_wdata;
    unsigned wstrb = dut.nvdla_core2dbb_w_wstrb;
    bool wlast = dut.nvdla_core2dbb_w_wlast;
    apb_ready = dut.pready;
    apb_data = dut.prdata;
    dut.core_clk = 1;
    dut.eval();
    if (b) { responses.pop_front(); b_held = false; }
    if (r) {
        r_held = false;
        reads.front().address += 8;
        if (!--reads.front().remaining) reads.pop_front();
    }
    if (aw) writes.push_back(next_aw);
    if (ar) reads.push_back(next_ar);
    if (w) {
        auto &transaction = writes.front();
        if (wlast != (transaction.remaining == 1)) throw std::runtime_error("AXI WLAST disagrees with AWLEN");
        uint8_t *target = checked_memory(transaction.address, 8);
        for (unsigned i = 0; i < 8; ++i) if (wstrb & (1u << i)) target[i] = wdata >> (8u*i);
        transaction.address += 8;
        if (!--transaction.remaining) {
            responses.push_back(transaction.id);
            writes.pop_front();
        }
    }
}
static uint32_t apb(uintptr_t address, bool write, uint32_t value) {
    dut.psel = 1;
    dut.penable = 0;
    dut.pwrite = write;
    dut.paddr = address;
    dut.pwdata = value;
    tick();
    dut.penable = 1;
    unsigned count = 0;
    do {
        tick();
        if (++count == 10000) throw std::runtime_error("APB transaction timeout");
    } while (!apb_ready);
    uint32_t result = apb_data;
    dut.psel = 0;
    dut.penable = 0;
    tick();
    return result;
}
static uint32_t model_read(uintptr_t address) {
    if (address >= NVDLA_BASE && address < NVDLA_BASE + 0x40000) return apb(address, false, 0);
    tick();
    if (address == PLIC_BASE + 0x1000) return dut.dla_intr ? (1u << NVDLA_IRQ) : 0;
    if (address == PLIC_BASE + 0x200004 || address == PLIC_BASE + 0x202004) return dut.dla_intr ? NVDLA_IRQ : 0;
    throw std::runtime_error("unknown emulated peripheral read");
}
static void model_write(uintptr_t address, uint32_t value) {
    if (address >= NVDLA_BASE && address < NVDLA_BASE + 0x40000) { apb(address, true, value); return; }
    if (address >= PLIC_BASE && address < PLIC_BASE + 0x400000) { tick(); return; }
    throw std::runtime_error("unknown emulated peripheral write");
}
int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    dut_pointer = new Vnvdla_small;
    void *spad = mmap((void *)0x08000000, 65536, PROT_READ|PROT_WRITE,
                      MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE, -1, 0);
    if (spad == MAP_FAILED) { perror("scratchpad mmap"); return 1; }
    try {
        dut.psel = 0;
        dut.penable = 0;
        dut.pwrite = 0;
        dut.paddr = 0;
        dut.pwdata = 0;
        dut.rstn = 0;
        dut.csb_rstn = 0;
        for (unsigned i = 0; i < 20; ++i) tick();
        dut.rstn = 1;
        dut.csb_rstn = 1;
        for (unsigned i = 0; i < 1000; ++i) tick();
        check_small_configuration(0);
        for (unsigned j = 0; j < CASE_COUNT * 2u; ++j) run_job(j % 2, j);
        for (unsigned h = 0; h < 2; ++h) run_cdp(h, CASE_COUNT * 2u + h);
        for (unsigned h = 0; h < 2; ++h) run_conv(h, (CASE_COUNT + 1u) * 2u + h);
        for (unsigned h = 0; h < 2; ++h) run_pdp(h, (CASE_COUNT + 2u) * 2u + h);
        printf("PASS NVDLA standalone engines cycles=%lu (PLIC emulated; CPU/cache absent)\n", cycles);
        dut.final();
        delete dut_pointer;
    } catch (const std::exception &error) {
        fprintf(stderr, "FAIL standalone: %s at cycle=%lu\n", error.what(), cycles);
        return 1;
    }
    return 0;
}
