#include <Arduino.h>
#include "bsp_flash.h"

bool bspFlashErasePage(uint32_t pageAddr) {
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Een;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    NRF_NVMC->ERASEPAGE = pageAddr;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Ren;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    return true;
}

bool bspFlashWrite(uint32_t destAddr, const void* src, size_t len) {
    NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Wen;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);

    const uint32_t* s = (const uint32_t*)src;
    volatile uint32_t* d = (volatile uint32_t*)destAddr;

    for (size_t i = 0; i < (len + 3) / 4; i++) {
        d[i] = s[i];
        while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    }

    NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Ren;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    return true;
}

bool bspFlashRead(uint32_t srcAddr, void* dest, size_t len) {
    const uint32_t* s = (const uint32_t*)srcAddr;
    uint32_t* d = (uint32_t*)dest;
    for (size_t i = 0; i < (len + 3) / 4; i++) {
        d[i] = s[i];
    }
    return true;
}
