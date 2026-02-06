#include <Arduino.h>
#include "flash_store.h"
#include "app_types.h"

bool flashLoadConfig(RuntimeConfig& cfg) {
    RuntimeConfig stored;
    uint32_t* src = (uint32_t*)CONFIG_ADDR;
    uint32_t* dst = (uint32_t*)&stored;

    for (size_t i = 0; i < sizeof(RuntimeConfig) / 4; i++) {
        dst[i] = src[i];
    }

    if (stored.magic == CONFIG_MAGIC) {
        cfg = stored;
        return true;
    }
    return false;
}

bool flashSaveConfig(const RuntimeConfig& cfg) {
    // Erase page first
    // 先擦除页
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Een;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    NRF_NVMC->ERASEPAGE = CONFIG_ADDR;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);

    // Write config
    // 写入配置
    NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Wen;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);

    uint32_t* src = (uint32_t*)&cfg;
    uint32_t* dst = (uint32_t*)CONFIG_ADDR;

    for (size_t i = 0; i < sizeof(RuntimeConfig) / 4; i++) {
        dst[i] = src[i];
        while (NRF_NVMC->READY == NVMC_READY_READY_Busy);
    }

    NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Ren;
    while (NRF_NVMC->READY == NVMC_READY_READY_Busy);

    return true;
}
