set platform $::env(PLATFORM_ROOT)
set results $::env(OUTPUT_ROOT)
read_lef [file join $platform lef NangateOpenCellLibrary.tech.lef]
read_lef [file join $platform lef NangateOpenCellLibrary.macro.lef]
read_lef [file join $platform lef fakeram45_512x64.lef]
read_liberty [file join $platform lib NangateOpenCellLibrary_typical.lib]
read_liberty [file join $platform lib fakeram45_512x64.lib]
read_verilog [file join $results ChipTop-mapped.v]
link_design ChipTop
set block [ord::get_db_block]
set macros 0
foreach instance [$block getInsts] {
    if {[[$instance getMaster] getName] eq "fakeram45_512x64"} {
        incr macros
    }
}
if {$macros != $::env(EXPECTED_SRAM_MACROS)} {
    error "Expected $::env(EXPECTED_SRAM_MACROS) SRAM macro instances, found $macros"
}
report_design_area
set report [open [file join $results openroad-link.json] w]
puts $report [format { {"top":"ChipTop","linked":true,"instances":%d,"sram_macros":%d} } [llength [$block getInsts]] $macros]
close $report
write_db [file join $results ChipTop.odb]
puts "Full $::env(CONFIG) ChipTop netlist and $macros SRAM macros linked successfully"
exit
