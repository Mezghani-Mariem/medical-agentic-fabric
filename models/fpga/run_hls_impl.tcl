# Implementation Vivado (synthese + placement + routage, circuit seul) de la variante parallele
# Prerequis : le projet hls_par16_<top> existe deja (csynth fait avec run_hls_par.tcl)
set par 16
if {[info exists ::env(HLS_PAR)]} { set par $::env(HLS_PAR) }
set top mlp_forward
if {[info exists ::env(HLS_TOP)]} { set top $::env(HLS_TOP) }
open_project hls_par${par}_$top
open_solution sol1
export_design -flow impl -rtl verilog -format ip_catalog
exit