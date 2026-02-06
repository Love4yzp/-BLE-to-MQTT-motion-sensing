#include <Arduino.h>
#include "cli_at.h"
#include "app_types.h"
#include "flash_store.h"

static char cmdBuffer[64] = {0};
static uint8_t cmdIndex = 0;

static void printHelp() {
    Serial.println();
    Serial.println(F("=== SeeedUA CLI Commands ==="));
    Serial.println(F("AT+HELP              - Show this help"));
    Serial.println(F("AT+INFO              - Show current config"));
    Serial.println(F("AT+THRESHOLD=xx      - Set threshold (hex, 02-3F)"));
    Serial.println(F("AT+TAILWINDOW=xxxx   - Set tail window (ms, 1000-10000)"));
    Serial.println(F("AT+TXPOWER=x         - Set TX power (dBm, -40 to 4)"));
    Serial.println(F("AT+SAVE              - Save config to flash"));
    Serial.println(F("AT+DEFAULT           - Reset to defaults"));
    Serial.println(F("AT+REBOOT            - Reboot device"));
    Serial.println();
}

static void printInfo(AppContext& ctx) {
    Serial.println();
    Serial.println(F("=== Device Info ==="));
    Serial.print(F("MAC: ")); Serial.println(ctx.macStr);
    Serial.print(F("Name: ")); Serial.println(ctx.deviceName);
    Serial.println();
    Serial.println(F("=== Current Config ==="));
    Serial.print(F("THRESHOLD=0x"));
    if (ctx.config.threshold < 0x10) Serial.print("0");
    Serial.print(ctx.config.threshold, HEX);
    Serial.print(F(" (~")); Serial.print(ctx.config.threshold * 31.25); Serial.println(F(" mg)"));
    Serial.print(F("TAILWINDOW=")); Serial.print(ctx.config.tailWindow); Serial.println(F(" ms"));
    Serial.print(F("TXPOWER=")); Serial.print(ctx.config.txPower); Serial.println(F(" dBm"));
    Serial.println();
}

static void processCommand(AppContext& ctx, const char* cmd) {
    char upperCmd[64];
    strncpy(upperCmd, cmd, 63);
    upperCmd[63] = '\0';
    for (int i = 0; upperCmd[i]; i++) {
        if (upperCmd[i] >= 'a' && upperCmd[i] <= 'z') {
            upperCmd[i] -= 32;
        }
    }

    if (strncmp(upperCmd, "AT+HELP", 7) == 0) {
        printHelp();
    }
    else if (strncmp(upperCmd, "AT+INFO", 7) == 0) {
        printInfo(ctx);
    }
    else if (strncmp(upperCmd, "AT+THRESHOLD=", 13) == 0) {
        uint8_t val = strtol(cmd + 13, NULL, 16);
        if (val >= 0x02 && val <= 0x3F) {
            ctx.config.threshold = val;
            Serial.print(F("OK THRESHOLD=0x"));
            Serial.println(val, HEX);
        } else {
            Serial.println(F("ERROR: Range 0x02-0x3F"));
        }
    }
    else if (strncmp(upperCmd, "AT+TAILWINDOW=", 14) == 0) {
        uint16_t val = atoi(cmd + 14);
        if (val >= 1000 && val <= 10000) {
            ctx.config.tailWindow = val;
            Serial.print(F("OK TAILWINDOW="));
            Serial.println(val);
        } else {
            Serial.println(F("ERROR: Range 1000-10000"));
        }
    }
    else if (strncmp(upperCmd, "AT+TXPOWER=", 11) == 0) {
        int8_t val = atoi(cmd + 11);
        if (val >= -40 && val <= 4) {
            ctx.config.txPower = val;
            Serial.print(F("OK TXPOWER="));
            Serial.println(val);
        } else {
            Serial.println(F("ERROR: Range -40 to 4"));
        }
    }
    else if (strncmp(upperCmd, "AT+SAVE", 7) == 0) {
        flashSaveConfig(ctx.config);
        Serial.println(F("OK Config saved to flash"));
    }
    else if (strncmp(upperCmd, "AT+DEFAULT", 10) == 0) {
        ctx.config.threshold = IMU_WAKEUP_THRESHOLD;
        ctx.config.tailWindow = TAIL_WINDOW_MS;
        ctx.config.txPower = BLE_TX_POWER;
        Serial.println(F("OK Defaults restored (use AT+SAVE to persist)"));
    }
    else if (strncmp(upperCmd, "AT+REBOOT", 9) == 0) {
        Serial.println(F("OK Rebooting..."));
        delay(100);
        NVIC_SystemReset();
    }
    else if (strlen(cmd) > 0) {
        Serial.print(F("ERROR: Unknown command: "));
        Serial.println(cmd);
        Serial.println(F("Type AT+HELP for available commands"));
    }
}

void cliInit(AppContext& ctx) {
    Serial.println(F("CLI ready. Type AT+HELP for commands."));
    Serial.println();
}

void cliPoll(AppContext& ctx) {
    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\r' || c == '\n') {
            if (cmdIndex > 0) {
                cmdBuffer[cmdIndex] = '\0';
                processCommand(ctx, cmdBuffer);
                cmdIndex = 0;
            }
        } else if (cmdIndex < sizeof(cmdBuffer) - 1) {
            cmdBuffer[cmdIndex++] = c;
        }
    }
}
