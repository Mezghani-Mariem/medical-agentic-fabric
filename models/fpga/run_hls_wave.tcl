# Relance la co-simulation RTL avec chronogrammes (projet deja synthetise)
set par 16
if {[info exists ::env(HLS_PAR)]} { set par $::env(HLS_PAR) }
set top p1_forward
if {[info exists ::env(HLS_TOP)]} { set top $::env(HLS_TOP) }
open_project hls_par${par}_$top
open_solution sol1
cosim_design -rtl verilog -tool xsim -wave_debug -trace_level all
exit