#pragma once

#include "app_types.h"

void telemetryReset(Telemetry& t, unsigned long nowMs, RunState initialState);
void telemetryOnTransition(Telemetry& t, RunState nextState, unsigned long nowMs);
void telemetryPrintIfDue(AppContext& ctx, unsigned long nowMs);
