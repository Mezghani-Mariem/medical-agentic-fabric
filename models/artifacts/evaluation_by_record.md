# Evaluation par enregistrement (leave-one-record-out), MIT-BIH N vs V
Battements : 21370 (N=17313, V=4057), 9 enregistrements

Split aleatoire (meme patient dans train et test) : precision 0.9940

Par enregistrement laisse de cote :
  record 100: N= 2237 V=    1  precision=1.000
  record 101: N= 1859 V=    0  precision=1.000
  record 103: N= 2082 V=    0  precision=1.000
  record 106: N= 1507 V=  520  precision=0.976
  record 119: N= 1543 V=  444  precision=1.000
  record 200: N= 1742 V=  826  precision=0.859
  record 203: N= 2529 V=  444  precision=0.538
  record 208: N= 1585 V=  992  precision=0.997
  record 233: N= 2229 V=  830  precision=0.985

Tous enregistrements confondus (patients jamais vus) :
  matrice de confusion : vrai N -> predit N=15550, predit V=1763 ; vrai V -> predit N=74, predit V=3983
  precision globale = 0.9140
  sensibilite (V detectes) = 0.9818 ; specificite (N reconnus) = 0.8982 ; precision equilibree = 0.9400

Calibration de la confiance (avant) :
  confiance moyenne = 0.9791 ; exactitude reelle = 0.9140 ; ECE = 0.0652
  18170 predictions a confiance >= 99 % (85.0%) : exactitude reelle 0.9617
  tranche de confiance | n | confiance moyenne | exactitude reelle
    0.50-0.55 |    122 | 0.525 | 0.541
    0.55-0.60 |    134 | 0.576 | 0.500
    0.60-0.65 |    135 | 0.626 | 0.585
    0.65-0.70 |    145 | 0.676 | 0.531
    0.70-0.75 |    152 | 0.725 | 0.579
    0.75-0.80 |    183 | 0.775 | 0.574
    0.80-0.85 |    213 | 0.826 | 0.521
    0.85-0.90 |    306 | 0.878 | 0.585
    0.90-0.95 |    510 | 0.929 | 0.663
    0.95-1.00 |  19470 | 0.998 | 0.946

Temperature optimale (minimise la log-vraisemblance negative) T = 3.42
  (ajustee et evaluee sur les memes predictions : estimation un peu optimiste)
  apres calibration : confiance moyenne = 0.9200 ; exactitude reelle = 0.9140 ; ECE = 0.0143
  predictions a confiance >= 75 % apres calibration : 88.1%
  tranche de confiance | n | confiance moyenne | exactitude reelle
    0.50-0.55 |    430 | 0.525 | 0.542
    0.55-0.60 |    441 | 0.575 | 0.565
    0.60-0.65 |    446 | 0.625 | 0.549
    0.65-0.70 |    549 | 0.675 | 0.656
    0.70-0.75 |    686 | 0.727 | 0.690
    0.75-0.80 |    780 | 0.777 | 0.768
    0.80-0.85 |   1041 | 0.826 | 0.813
    0.85-0.90 |   1342 | 0.876 | 0.835
    0.90-0.95 |   1667 | 0.927 | 0.887
    0.95-1.00 |  13988 | 0.990 | 0.996
