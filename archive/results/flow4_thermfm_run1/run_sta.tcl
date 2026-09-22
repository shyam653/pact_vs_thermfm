
read_liberty /home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_lef /home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef
read_lef /home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef
read_verilog /home/boson4/OpenROAD/src/sta/examples/gcd_sky130hd.v
link_design gcd
read_spef /home/boson4/shyam/therm_fm_pact/v_01/outputs/flow4_thermfm_run1/adjusted.spef
create_clock -name clk -period 10.0 [get_ports clk]

puts "=== STA REPORT START ==="
report_checks -path_delay max -digits 4
report_worst_slack -max
report_tns
puts "=== STA REPORT END ==="
