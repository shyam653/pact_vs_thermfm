// Simulation-only 512x64 bit-masked SRAM contract: synchronous read-before-write.
// This behavioral model is not a physical library or a timing model.
module fakeram45_512x64 (
    input clk, input ce_in, input we_in,
    input [8:0] addr_in,
    input [63:0] wd_in, input [63:0] w_mask_in,
    output reg [63:0] rd_out
);
    reg [63:0] storage [0:511];
    integer bit_index;
    always @(posedge clk) begin
        if (ce_in) begin
            rd_out <= storage[addr_in];
            if (we_in)
                for (bit_index = 0; bit_index < 64; bit_index = bit_index + 1)
                    if (w_mask_in[bit_index])
                        storage[addr_in][bit_index] <= wd_in[bit_index];
        end else begin
            rd_out <= 64'bx;
        end
    end
endmodule
