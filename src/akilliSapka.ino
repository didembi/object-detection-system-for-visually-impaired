#include <TimerOne.h>

const int buzzerPin = 12;
const int echoPin = 11;
const int trigPin = 10;

volatile bool olcumHazir = false; //flag

void setup() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(buzzerPin, OUTPUT);

  Serial.begin(9600);

  Timer1.initialize(500000); // Her 500 ms'de bir tetiklenecek
  Timer1.attachInterrupt(triggerUltrasonik);
}

void loop() {
  static float mesafe;

  if (olcumHazir) { //timer interrupt tarafından set edilmişse
    olcumHazir = false; //yeni ölçüm için bekle

    unsigned long sure = pulseIn(echoPin, HIGH, 30000); // 30 ms timeout
    if (sure > 0) {
      mesafe = sure / 2.0 / 29.1; // Mesafeyi cm cinsinden hesapla

      Serial.print("Ölçülen Mesafe = ");
      Serial.println(mesafe);

      int ditCount = 0;

      if (mesafe < 30) {
        ditCount = 3;   // 30 cm'den yakınsa 3 dıt
      } 
      else if (mesafe >= 30 && mesafe < 100) {
        ditCount = 2;   // 30-100 arası 2 dıt
      } 
      else if (mesafe >= 100 && mesafe <= 150) {
        ditCount = 1;   // 100-180 arası 1 dıt
      } 
      else {
        ditCount = 0;   // 150 cm üzeri ses yok
      }

      if (ditCount > 0) {
        doDits(ditCount);
      }
      else {
        noTone(buzzerPin); // Dit sayısı 0 ise buzzer'ı kapat
      }
    }
  }
}

void doDits(int count) {
  for (int i = 0; i < count; i++) {
    tone(buzzerPin, 1000);   // 1000 Hz frekanslı dıt sesi
    delay(100);              // dıt süresi
    noTone(buzzerPin);
    delay(100);              // dıt arası sessizlik
  }
  delay(300);                // grup arası sessizlik
}

void triggerUltrasonik() { // Timer interrupt fonksiyonu, her 500 ms'de bir çalışır
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  olcumHazir = true;
} 