#include <Arduino.h>
#include "core_isr_events.h"

static volatile uint32_t g_events = 0;
static volatile uint8_t g_interruptCount = 0;

void isrMotionHandler() {
    g_events |= EVT_MOTION;
    g_interruptCount++;
}

uint32_t isrFetchAndClearEvents() {
    noInterrupts();
    uint32_t e = g_events;
    g_events = 0;
    interrupts();
    return e;
}

uint8_t isrGetInterruptCount() {
    return g_interruptCount;
}
