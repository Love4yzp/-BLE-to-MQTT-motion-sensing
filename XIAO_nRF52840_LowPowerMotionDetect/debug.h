#pragma once

/**
 * Debug Macros | 调试宏
 *
 * Conditionally compiled serial output controlled by DEBUG_ENABLED in config.h.
 * 通过 config.h 中的 DEBUG_ENABLED 条件编译串口输出。
 */

#include "config.h"

#if DEBUG_ENABLED
  #define DEBUG_PRINT(x)    Serial.print(x)
  #define DEBUG_PRINTLN(x)  Serial.println(x)
  #define DEBUG_PRINTF(...) Serial.printf(__VA_ARGS__)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
  #define DEBUG_PRINTF(...)
#endif
