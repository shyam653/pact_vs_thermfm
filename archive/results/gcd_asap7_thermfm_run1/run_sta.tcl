
read_liberty /home/boson4/OpenROAD/src/sta/examples/reg1_asap7.lib
read_verilog /home/boson4/OpenROAD/src/sta/examples/reg1.v
link_design reg1
read_spef /home/boson4/shyam/therm_fm_pact/v_01/outputs/gcd_asap7_thermfm_run1/adjusted.spef
create_clock -name clk -period 100.0 [get_ports clk1]

puts "=== STA REPORT START ==="
report_checks -path_delay max -digits 4
report_worst_slack -max
report_tns
puts "=== STA REPORT END ==="
