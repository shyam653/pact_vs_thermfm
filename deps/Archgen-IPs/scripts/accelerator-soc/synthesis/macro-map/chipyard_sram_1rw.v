// Preserve generated registered-read-address behavior, including writes to the
// held address. Wrappers are derived from each generated memory inventory.
module chipyard_sram_1rw #(
    parameter ABITS = 9,
    parameter WIDTH = 64,
    parameter MASK_BITS = 8
) (
    input [ABITS-1:0] RW0_addr,
    input RW0_clk,
    input [WIDTH-1:0] RW0_wdata,
    output [WIDTH-1:0] RW0_rdata,
    input RW0_en,
    input RW0_wmode,
    input [MASK_BITS-1:0] RW0_wmask
);
    localparam DEPTH_BANKS = ABITS > 9 ? (1 << (ABITS - 9)) : 1;
    localparam WIDTH_BANKS = (WIDTH + 63) / 64;
    localparam PAD_WIDTH = WIDTH_BANKS * 64;
    localparam LANE_WIDTH = WIDTH / MASK_BITS;
    reg [ABITS-1:0] last_read_addr;
    reg last_cycle_read;
    reg [WIDTH-1:0] held_data;
    wire read_request = RW0_en && !RW0_wmode;
    wire write_request = RW0_en && RW0_wmode;
    wire [WIDTH-1:0] bit_mask;
    wire [PAD_WIDTH-1:0] padded_data = {{(PAD_WIDTH-WIDTH){1'b0}}, RW0_wdata};
    wire [PAD_WIDTH-1:0] padded_mask = {{(PAD_WIDTH-WIDTH){1'b0}}, bit_mask};
    wire [8:0] macro_addr = RW0_addr;
    wire [31:0] expanded_addr = RW0_addr;
    wire [31:0] expanded_last_read_addr = last_read_addr;
    wire [PAD_WIDTH-1:0] bank_data [0:DEPTH_BANKS-1];
    wire [PAD_WIDTH-1:0] selected_data = bank_data[expanded_last_read_addr >> 9];

    assign RW0_rdata = last_cycle_read ? selected_data[WIDTH-1:0] : held_data;

    genvar lane, depth_bank, width_bank;
    generate
        for (lane = 0; lane < MASK_BITS; lane = lane + 1) begin: expand_mask
            assign bit_mask[lane*LANE_WIDTH +: LANE_WIDTH] = {LANE_WIDTH{RW0_wmask[lane]}};
        end
        for (depth_bank = 0; depth_bank < DEPTH_BANKS; depth_bank = depth_bank + 1) begin: depth_banks
            for (width_bank = 0; width_bank < WIDTH_BANKS; width_bank = width_bank + 1) begin: width_banks
                fakeram45_512x64 ram (
                    .clk(RW0_clk),
                    .ce_in(1'b1),
                    .we_in(write_request && ((expanded_addr >> 9) == depth_bank)),
                    .addr_in(macro_addr),
                    .wd_in(padded_data[width_bank*64 +: 64]),
                    .w_mask_in(padded_mask[width_bank*64 +: 64]),
                    .rd_out(bank_data[depth_bank][width_bank*64 +: 64])
                );
            end
        end
    endgenerate

    always @(posedge RW0_clk) begin
        last_cycle_read <= read_request;
        if (read_request)
            last_read_addr <= RW0_addr;
        if (write_request && (RW0_addr == last_read_addr))
            held_data <= (RW0_rdata & ~bit_mask) | (RW0_wdata & bit_mask);
        else if (last_cycle_read)
            held_data <= RW0_rdata;
    end
endmodule
