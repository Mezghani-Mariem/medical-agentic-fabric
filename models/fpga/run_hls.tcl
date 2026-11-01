# Usage : vitis_hls -f run_hls.tcl            (partition P1 par defaut)
#   Windows PowerShell : $env:HLS_TOP="p2_forward"; vitis_hls -f run_hls.tcl
# Tops possibles : p1_forward, p2_forward, p3_forward, mlp_forward
set here [file dirname [file normalize [info script]]]
set top p1_forward
if {[info exists ::env(HLS_TOP)]} { set top $::env(HLS_TOP) }
set part xc7z020clg400-1
if {[info exists ::env(HLS_PART)]} { set part $::env(HLS_PART) }

open_project -reset hls_$top
set_top $top
add_files $here/mlp_hls.cpp -cflags "-I$here/../partitions/hls"
add_files -tb $here/tb_mlp.cpp -cflags "-I$here/../partitions/hls -I$here"
open_solution -reset sol1 -flow_target vivado
set_part $part
create_clock -period 10 -name default

csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
# export_design -format ip_catalog   ;# optionnel : genere l'IP pour Vivado
exit