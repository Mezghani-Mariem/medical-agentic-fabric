// Banc de test : compare chaque partition aux sorties du moteur Python (tb_vectors.h).
#include <stdio.h>
#include <stdint.h>
#include "mlp_hls.h"
#include "tb_vectors.h"

int main() {
    int errors = 0;
    for (int n = 0; n < TB_N; n++) {
        int8_t y1[P1_OUT], y2[P2_OUT];
        int32_t y3[P3_OUT], yc[P3_OUT];
        p1_forward(TB_X[n], y1);
        p2_forward(TB_P1[n], y2);   // chaque partition est testee avec la vraie entree attendue
        p3_forward(TB_P2[n], y3);
        mlp_forward(TB_X[n], yc);
        for (int i = 0; i < P1_OUT; i++) if (y1[i] != TB_P1[n][i]) errors++;
        for (int i = 0; i < P2_OUT; i++) if (y2[i] != TB_P2[n][i]) errors++;
        for (int i = 0; i < P3_OUT; i++) if (y3[i] != TB_Z[n][i] || yc[i] != TB_Z[n][i]) errors++;
    }
    printf("%d vecteurs, %d erreurs\n", TB_N, errors);
    printf(errors == 0 ? "TEST PASSED\n" : "TEST FAILED\n");
    return errors == 0 ? 0 : 1;
}