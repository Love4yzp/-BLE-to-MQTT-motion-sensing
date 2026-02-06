#include "app_config_store.h"
#include "bsp_flash.h"

bool configLoad(RuntimeConfig& cfg) {
    RuntimeConfig stored;
    bspFlashRead(CONFIG_ADDR, &stored, sizeof(RuntimeConfig));
    if (stored.magic == CONFIG_MAGIC) {
        cfg = stored;
        return true;
    }
    return false;
}

bool configSave(const RuntimeConfig& cfg) {
    bspFlashErasePage(CONFIG_ADDR);
    return bspFlashWrite(CONFIG_ADDR, &cfg, sizeof(RuntimeConfig));
}
