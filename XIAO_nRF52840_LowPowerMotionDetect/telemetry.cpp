#include <Arduino.h>
#include "telemetry.h"
#include "app_types.h"
#include "pins.h"
#include "isr_events.h"

void telemetryReset(Telemetry& t, unsigned long nowMs, RunState initialState) {
    t.runState = initialState;
    t.lastStateChangeMs = nowMs;
    t.lastStatusMs = nowMs;
    t.motionCount = 0;
    t.advertiseMs = 0;
    t.tailWindowMs = 0;
    t.idleMs = 0;
}

void telemetryOnTransition(Telemetry& t, RunState nextState, unsigned long nowMs) {
    if (t.runState != nextState) {
        unsigned long delta = nowMs - t.lastStateChangeMs;
        if (t.runState == RunState::Broadcasting) {
            t.advertiseMs += delta;
        } else if (t.runState == RunState::TailWindow) {
            t.tailWindowMs += delta;
        } else {
            t.idleMs += delta;
        }
        t.runState = nextState;
        t.lastStateChangeMs = nowMs;
    }
}

void telemetryPrintIfDue(AppContext& ctx, unsigned long nowMs) {
    if (!ctx.loop.usbMode) return;
    if (nowMs - ctx.telem.lastStatusMs <= 5000) return;

    ctx.telem.lastStatusMs = nowMs;
    unsigned long delta = nowMs - ctx.telem.lastStateChangeMs;
    unsigned long advertiseMs = ctx.telem.advertiseMs;
    unsigned long tailWindowMs = ctx.telem.tailWindowMs;
    unsigned long idleMs = ctx.telem.idleMs;

    if (ctx.telem.runState == RunState::Broadcasting) {
        advertiseMs += delta;
    } else if (ctx.telem.runState == RunState::TailWindow) {
        tailWindowMs += delta;
    } else {
        idleMs += delta;
    }

    Serial.print(F("[STATUS] INT1="));
    Serial.print(digitalRead(IMU_INT1_PIN) ? "HIGH" : "LOW");
    Serial.print(F(" cnt="));
    Serial.print(isrGetInterruptCount());
    Serial.print(F(" motion="));
    Serial.print(ctx.telem.motionCount);
    Serial.print(F(" tail="));
    Serial.print(ctx.loop.runState == RunState::TailWindow ? "Y" : "N");
    Serial.print(F(" adv_ms="));
    Serial.print(advertiseMs);
    Serial.print(F(" tail_ms="));
    Serial.print(tailWindowMs);
    Serial.print(F(" idle_ms="));
    Serial.println(idleMs);
}
