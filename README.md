# Thrust Vectoring Module

Module de poussée vectorielle (TVC) pour fusée de modélisme. Première étape : un prototype de banc
qui oriente un moteur D9 factice sur deux axes.

![Démo](docs/img/tvc_demo.gif)

## Matériel

- ESP32-C3 Super Mini
- MPU6050 (module GY-521)
- 2 servos MG90S
- Cardan 2 axes sur roulements MR63ZZ, pièces imprimées en 3D
- Encombrement Ø76 × 89 mm, débattement ±10° par axe

## Organisation

```
cad/        modèle FreeCAD paramétrique, scripts de rendu
  exports/  fichiers générés : FCStd, STEP, STL, rapport
firmware/   code de l'ESP32-C3 (à venir)
docs/img/   rendus
```

- Mécanique : voir [cad/README.md](cad/README.md)
- Firmware et câblage : voir [firmware/README.md](firmware/README.md)

## Licence

MIT, voir [LICENSE](LICENSE).
