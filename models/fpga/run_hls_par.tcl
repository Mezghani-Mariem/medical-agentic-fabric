# Variante parallele. Env : HLS_TOP (p1_forward...), HLS_PAR (8 ou 16, defaut 16)
set here [file dirname [file normalize [info script]]]
set top p1_forward
if {[info exists ::env(HLS_TOP)]} { set top $::env(HLS_TOP) }
set par 16
if {[info exists ::env(HLS_PAR)]} { set par $::env(HLS_PAR) }
set part xc7z020clg400-1

open_project -reset hls_par${par}_$top
set_top $top
add_files $here/mlp_hls_par.cpp -cflags "-I$here/../partitions/hls -DPAR=$par"
add_files -tb $here/tb_mlp.cpp -cflags "-I$here/../partitions/hls -I$here"
open_solution -reset sol1
set_part $part
create_clock -period 10 -name default

csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
exit