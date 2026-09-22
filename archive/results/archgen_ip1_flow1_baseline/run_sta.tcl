read_lef archive/design_inputs/aes_asap7/asap7_tech_1x_201209.lef
read_lef archive/design_inputs/aes_asap7/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty archive/design_inputs/aes_asap7/asap7_small_ff.lib.gz
read_verilog archive/design_inputs/aes_asap7/reg1_asap7.v
link_design top
read_spef /home/boson4/shyam/therm_fm_pact/v_01/archive/design_inputs/archgen_ip1/baseline.spef
create_clock -name clk1 -period 10.0 [get_ports clk1]
create_clock -name clk3 -period 10.0 [get_ports clk3]
report_checks -path_delay max -digits 4
exit