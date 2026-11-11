#pragma once
#include <stdint.h>

#define SEG_LEN 64
#define P1_OUT 32
#define P2_OUT 16
#define P3_OUT 2

// Un "top" Vitis HLS par partition + la chaine complete.
void p1_forward(const int8_t x[SEG_LEN], int8_t y[P1_OUT]);
void p2_forward(const int8_t x[P1_OUT], int8_t y[P2_OUT]);
void p3_forward(const int8_t x[P2_OUT], int32_t y[P3_OUT]);
void mlp_forward(const int8_t x[SEG_LEN], int32_t y[P3_OUT]);