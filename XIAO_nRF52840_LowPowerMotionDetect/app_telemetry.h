#pragma once

#include "core_types.h"

void appTelemetryReset(Telemetry& t, unsigned long nowMs, RunState initialState);
void appTelemetryOnTransition(Telemetry& t, RunState nextState, unsigned long nowMs);
void appTelemetryPrintIfDue(AppContext& ctx, unsigned long nowMs);
