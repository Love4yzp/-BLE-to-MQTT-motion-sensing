#pragma once

#include "app_types.h"

// Initialize CLI (called once in setup)
// 初始化 CLI（在 setup 中调用一次）
void cliInit(AppContext& ctx);

// Poll serial for incoming AT commands
// 轮询串口接收 AT 命令
void cliPoll(AppContext& ctx);
