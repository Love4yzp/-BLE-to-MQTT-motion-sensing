#pragma once

#include "app_types.h"

// Returns true if valid config was loaded, false if defaults should be used
// 返回 true 表示已加载有效配置，false 表示应使用默认值
bool flashLoadConfig(RuntimeConfig& cfg);
bool flashSaveConfig(const RuntimeConfig& cfg);
