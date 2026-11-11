# Co-simulation RTL de la chaine complete sur UN ECG reel (vecteur fourni par verify_case.py)
# Env : HLS_CASE_DIR (defaut ./case)
set here [file dirname [file normalize [info script]]]
set casedir [file normalize case]
if {[info exists ::env(HLS_CASE_DIR)]} { set casedir [file normalize $::env(HLS_CASE_DIR)] }
set top mlp_forward
set par 16

open_project -reset hls_case_$top
set_top $top
add_files $here/mlp_hls_par.cpp -cflags "-I$here/../partitions/hls -DPAR=$par"
add_files -tb $casedir/tb_mlp.cpp -cflags "-I$casedir -I$here -I$here/../partitions/hls"
open_solution -reset sol1
set_part xc7z020clg400-1
create_clock -period 10 -name default

csim_design
csynth_design
cosim_design -rtl verilog -tool xsim
exit