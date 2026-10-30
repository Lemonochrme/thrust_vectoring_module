# Firmware

À écrire. Cible : ESP32-C3 Super Mini, MPU6050, 2 servos MG90S.

## Câblage prévu

| ESP32-C3 | Vers |
|---|---|
| 5V | +5 V de la carte de distribution |
| GND | GND commun (servos, IMU, banc) |
| 3V3 | VCC du GY-521 |
| GPIO6 | SDA du GY-521 |
| GPIO7 | SCL du GY-521 |
| GPIO3 | Signal servo X |
| GPIO4 | Signal servo Y |

GPIO2, 8 et 9 sont évitées (broches de démarrage).

Alimentation : 5 V du banc sur le bornier de la carte de distribution, 2 A minimum
(environ 0,7 A en pointe par servo). L'USB-C reste disponible pour la programmation.

## Commande des servos

La relation entre l'angle du cardan et l'angle des servos n'est pas linéaire et les deux axes sont
légèrement couplés. Le firmware doit reprendre la cinématique inverse du modèle CAO (fonction
`solve_servo` dans `cad/tvc_module.py`) ou une table générée à partir de celle-ci.

| Cardan | −10° | −5° | −1° | +1° | +5° | +10° |
|---|---|---|---|---|---|---|
| Servo X (θx) | −27,4° | −12,6° | −2,39° | +2,33° | +11,1° | +20,7° |
| Servo Y (θy) | +20,7° | +11,1° | +2,33° | −2,39° | −12,6° | −27,4° |
