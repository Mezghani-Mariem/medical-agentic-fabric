# Benchmark des plans — modèle v2-int8-p3-ebe0997a

200 inférences par plan. Latence mesurée sur la machine hôte ; latence FPGA = estimation (MAC / (16 PE × 100 MHz)), pas une mesure.

| Plan | Sorties identiques à ARM seul | Latence hôte (ms/inférence) | Latence FPGA estimée des partitions FPGA (µs) |
| --- | --- | --- | --- |
| arm/arm/arm | oui | 0.039 | 0.00 |
| arm/arm/fpga | oui | 0.040 | 0.02 |
| arm/fpga/arm | oui | 0.040 | 0.32 |
| arm/fpga/fpga | oui | 0.040 | 0.34 |
| fpga/arm/arm | oui | 0.040 | 1.28 |
| fpga/arm/fpga | oui | 0.040 | 1.30 |
| fpga/fpga/arm | oui | 0.042 | 1.60 |
| fpga/fpga/fpga | oui | 0.042 | 1.62 |
