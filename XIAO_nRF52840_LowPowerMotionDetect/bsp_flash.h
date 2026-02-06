#pragma once

#include <stdint.h>
#include <stddef.h>

bool bspFlashErasePage(uint32_t pageAddr);
bool bspFlashWrite(uint32_t destAddr, const void* src, size_t len);
bool bspFlashRead(uint32_t srcAddr, void* dest, size_t len);
