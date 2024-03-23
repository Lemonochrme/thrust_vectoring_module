#include <Arduino.h>
#include <Wire.h>   
#include <ESP32Servo.h>
#include "SparkFun_MMA8452Q.h"    

MMA8452Q accel;    
Servo myservoX;
Servo myservoY;
int servoPinY = 16;
int servoPinX = 17;             

void setup() {
  Serial.begin(9600);
  Wire.begin();

  if (!accel.begin()) {
    Serial.println("Connection Error");
    while (1);
  }

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  
  myservoX.setPeriodHertz(50);    // standard 50 hz servo
  myservoX.attach(servoPinX, 1000, 2000);
  myservoY.setPeriodHertz(50);    // standard 50 hz servo
  myservoY.attach(servoPinY, 1000, 2000);
}

void loop() {
  // Read the acceleration values
  float AccX = accel.getCalculatedX();
  float AccY = accel.getCalculatedY();
  float AccZ = accel.getCalculatedZ();

  // Calculate the angle based on accelerometer readings
  float angleX = atan2(AccY, AccZ) * 180 / PI;
  float angleY = atan2(-AccX, sqrt(AccY * AccY + AccZ * AccZ)) * 180 / PI;

  // Convert angles to servo positions
  int servoXAngle = map(angleX, -90, 90, 0, 180);
  int servoYAngle = map(angleY, -90, 90, 0, 180);

  // Move the servos to the corrected positions
  myservoX.write(servoXAngle);
  myservoY.write(servoYAngle);

  delay(15);
}
