// Variante parallele (PAR MAC par cycle) des partitions P1/P2/P3. Meme arithmetique entiere que mlp_hls.cpp.
#include "mlp_hls.h"
#include "p1_weights.h"
#include "p2_weights.h"
#include "p3_weights.h"

#ifndef PAR
#define PAR 16
#endif

template <int IN, int OUT>
static void dense_relu(const int8_t x[IN], const int8_t W[IN][OUT], const int32_t b[OUT],
                       int64_t m0, int shift, int8_t y[OUT]) {
#pragma HLS INLINE
    constexpr int P = (PAR < IN) ? PAR : IN;
    constexpr int CH = IN / P;
    int8_t xl[IN];
#pragma HLS ARRAY_PARTITION variable=xl complete
COPY_X:
    for (int i = 0; i < IN; i++) {
#pragma HLS PIPELINE II=1
        xl[i] = x[i];
    }
OUT_LOOP:
    for (int o = 0; o < OUT; o++) {
#pragma HLS PIPELINE
        int32_t acc = b[o];
        for (int c = 0; c < CH; c++) {
            int32_t part = 0;
            for (int k = 0; k < P; k++) {
                part += (int32_t)xl[c * P + k] * (int32_t)W[c * P + k][o];
            }
            acc += part;
        }
        if (acc < 0) acc = 0;
        int64_t v = (((int64_t)acc * m0) + ((int64_t)1 << (shift - 1))) >> shift;
        if (v > 127) v = 127;
        if (v < -128) v = -128;
        y[o] = (int8_t)v;
    }
}

template <int IN, int OUT>
static void dense_logits(const int8_t x[IN], const int8_t W[IN][OUT], const int32_t b[OUT], int32_t y[OUT]) {
#pragma HLS INLINE
    constexpr int P = (PAR < IN) ? PAR : IN;
    constexpr int CH = IN / P;
    int8_t xl[IN];
#pragma HLS ARRAY_PARTITION variable=xl complete
COPY_X:
    for (int i = 0; i < IN; i++) {
#pragma HLS PIPELINE II=1
        xl[i] = x[i];
    }
OUT_LOOP:
    for (int o = 0; o < OUT; o++) {
#pragma HLS PIPELINE
        int32_t acc = b[o];
        for (int c = 0; c < CH; c++) {
            int32_t part = 0;
            for (int k = 0; k < P; k++) {
                part += (int32_t)xl[c * P + k] * (int32_t)W[c * P + k][o];
            }
            acc += part;
        }
        y[o] = acc;
    }
}

void p1_forward(const int8_t x[SEG_LEN], int8_t y[P1_OUT]) {
#pragma HLS ARRAY_PARTITION variable=p1_l0_W cyclic factor=PAR dim=1
    dense_relu<SEG_LEN, P1_OUT>(x, p1_l0_W, p1_l0_b, P1_L0_M0, P1_L0_SHIFT, y);
}

void p2_forward(const int8_t x[P1_OUT], int8_t y[P2_OUT]) {
#pragma HLS ARRAY_PARTITION variable=p2_l0_W cyclic factor=PAR dim=1
    dense_relu<P1_OUT, P2_OUT>(x, p2_l0_W, p2_l0_b, P2_L0_M0, P2_L0_SHIFT, y);
}

void p3_forward(const int8_t x[P2_OUT], int32_t y[P3_OUT]) {
#pragma HLS ARRAY_PARTITION variable=p3_l0_W cyclic factor=PAR dim=1
    dense_logits<P2_OUT, P3_OUT>(x, p3_l0_W, p3_l0_b, y);
}

void mlp_forward(const int8_t x[SEG_LEN], int32_t y[P3_OUT]) {
    int8_t h1[P1_OUT];
    int8_t h2[P2_OUT];
    p1_forward(x, h1);
    p2_forward(h1, h2);
    p3_forward(h2, y);
}