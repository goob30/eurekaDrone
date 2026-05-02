#include <Servo.h>

Servo myServo;
int waitTime = 15;
bool sweeping = false;

void setup() {
  Serial.begin(9600);
  myServo.attach(9);
  myServo.write(90);
}

void loop() {
  // Check for incoming serial command
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "SWEEP") sweeping = true;
    if (cmd == "STOP")  sweeping = false;
  }

  if (sweeping) {
    for (int pos = 90; pos <= 130; pos++) {
      myServo.write(pos);
      delay(waitTime);
      // Check for STOP mid-sweep
      if (Serial.available() > 0) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "STOP") { sweeping = false; break; }
      }
    }
    for (int pos = 130; pos >= 90; pos--) {
      myServo.write(pos);
      delay(waitTime);
      if (Serial.available() > 0) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();
        if (cmd == "STOP") { sweeping = false; break; }
      }
    }
  }
}
