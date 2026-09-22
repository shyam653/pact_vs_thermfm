// Lower only output buffers whose enable is provably tied high.
(* techmap_celltype = "$tribuf" *)
module enabled_output_buffer #(
    parameter WIDTH = 1,
    parameter _TECHMAP_CONSTMSK_EN_ = 1'b0,
    parameter _TECHMAP_CONSTVAL_EN_ = 1'b0
) (
    input [WIDTH-1:0] A,
    input EN,
    output [WIDTH-1:0] Y
);
    wire _TECHMAP_FAIL_ = (_TECHMAP_CONSTMSK_EN_ !== 1'b1) ||
                         (_TECHMAP_CONSTVAL_EN_ !== 1'b1);
    assign Y = A;
endmodule
