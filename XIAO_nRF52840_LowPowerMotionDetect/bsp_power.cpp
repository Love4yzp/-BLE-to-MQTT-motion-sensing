#include <Arduino.h>
#include "bsp_power.h"
#include "config.h"

bool bspPowerIsUsb() {
#if FORCE_BATTERY_MODE
    return false;
#else
    return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk);
#endif
}

void bspPowerEnableDCDC() {
    NRF_POWER->DCDCEN = 1;
}

void bspPowerSystemOff(uint8_t wakePin) {
    nrf_gpio_cfg_sense_input(wakePin, NRF_GPIO_PIN_PULLDOWN, NRF_GPIO_PIN_SENSE_HIGH);
    sd_power_system_off();
    while (1) { __WFE(); }
}
