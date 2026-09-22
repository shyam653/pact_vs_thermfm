module check(input logic clk, input logic bad);
 always @(posedge clk) begin
 if (bad) $error("PROC_ERROR");
 if (bad) $fatal(1,"PROC_FATAL");
 assert (!bad) else $error("ASSERT_ERROR");
 end
endmodule
