#include <Arduino.h>
#include "leds.h"
#include "pins.h"

void ledsInit() {
    pinMode(LED_GREEN_PIN, OUTPUT);
    pinMode(LED_BLUE_PIN, OUTPUT);
    ledsOff();
}

// Active LOW: LED on when pin LOW
// 低电平点亮：引脚为 LOW 时 LED 亮
void ledsSetGreen(bool on) {
    digitalWrite(LED_GREEN_PIN, on ? LOW : HIGH);
}

void ledsSetBlue(bool on) {
    digitalWrite(LED_BLUE_PIN, on ? LOW : HIGH);
}

void ledsOff() {
    ledsSetGreen(false);
    ledsSetBlue(false);
}
