read_lef archive/design_inputs/aes_asap7/asap7_tech_1x_201209.lef
read_lef archive/design_inputs/aes_asap7/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty archive/design_inputs/aes_asap7/asap7_small_ff.lib.gz
read_verilog archive/design_inputs/aes_asap7/reg1_asap7.v
link_design top
initialize_floorplan -die_area {0 0 120 120} -core_area {10 10 110 110} -site asap7sc7p5t
global_placement -density 0.5 -skip_io
detailed_placement
write_def /home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip1/post_pnr.def
write_db /home/boson4/shyam/therm_fm_pact/v_01/archive/pnr/archgen_ip1/post_pnr.odb
exit