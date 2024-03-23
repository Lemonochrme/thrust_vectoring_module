  #include <Arduino.h>
  #include <Wire.h>   
  #include <ESP32Servo.h>
  #include "SparkFun_MMA8452Q.h"    

  MMA8452Q accel;    
  Servo myservoX;
  Servo myservoY;
  int pos = 0;  
  int servoPinY = 16;
  int servoPinX = 17;             

  void setup() {
    Serial.begin(9600);
    Wire.begin();

    if (accel.begin() == false) {
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

  // Circular motion parameter
  float radius = 50; 
  float centerX = 90; 
  float centerY = 90; 
  float speed = 1;   
  
  for (float angle = 0; angle < 360; angle += speed) {
    float radians = angle * PI / 180;
    int xPos = centerX + radius * cos(radians);
    int yPos = centerY + radius * sin(radians);

    // Map the X and Y positions to servo angles
    int servoXAngle = map(xPos, 0, 180, 0, 180);
    int servoYAngle = map(yPos, 0, 180, 0, 180);

    // Move the servos to the calculated positions
    myservoX.write(servoXAngle);
    myservoY.write(servoYAngle);

    delay(15);
  }
}