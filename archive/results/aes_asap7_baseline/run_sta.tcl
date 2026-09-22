read_lef /home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /home/boson4/diffusion/external/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /home/boson4/OpenROAD/src/sta/examples/asap7_small_ff.lib.gz
read_verilog /home/boson4/OpenROAD/src/sta/examples/reg1_asap7.v
link_design top
read_spef /home/boson4/shyam/therm_fm_pact/v_01/data/aes_asap7_baseline.spef
create_clock -name clk1 -period 10.0 [get_ports clk1]
create_clock -name clk3 -period 10.0 [get_ports clk3]
report_checks -path_delay max -digits 4
exit