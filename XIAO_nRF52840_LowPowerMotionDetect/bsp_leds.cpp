#include <Arduino.h>
#include "bsp_leds.h"
#include "bsp_pins.h"

void bspLedsInit() {
    pinMode(LED_GREEN_PIN, OUTPUT);
    pinMode(LED_BLUE_PIN, OUTPUT);
    bspLedsOff();
}

// Active LOW: LED on when pin LOW
// 低电平点亮：引脚为 LOW 时 LED 亮
void bspLedsSetGreen(bool on) {
    digitalWrite(LED_GREEN_PIN, on ? LOW : HIGH);
}

void bspLedsSetBlue(bool on) {
    digitalWrite(LED_BLUE_PIN, on ? LOW : HIGH);
}

void bspLedsOff() {
    bspLedsSetGreen(false);
    bspLedsSetBlue(false);
}
