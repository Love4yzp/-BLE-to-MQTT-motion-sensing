#include <Arduino.h>
#include <LSM6DS3.h>
#include <Wire.h>
#include "imu.h"
#include "pins.h"
#include "isr_events.h"

static LSM6DS3 myIMU(I2C_MODE, 0x6A);

bool imuInit() {
    pinMode(IMU_INT1_PIN, INPUT);
    return (myIMU.begin() == 0);
}

void imuConfigureWake(uint8_t threshold) {
    // Accelerometer: 26Hz, 2g | 加速度计：26Hz, 2g
    // 12.5Hz = 0x10, 26Hz = 0x20, 52Hz = 0x30
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL1_XL, 0x20);

    // Disable gyroscope | 关闭陀螺仪
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL2_G, 0x00);

    // Enable interrupts with latching (LIR)
    // Bit 7: INTERRUPTS_ENABLE=1, Bit 0: LIR=1
    // 启用中断并锁存 (LIR)
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_TAP_CFG1, 0x81);

    // Wake-up threshold — no activity state machine
    // Bit 6: SLEEP_ON_OFF=0 (wake-up pulse only)
    // 唤醒阈值 — 不启用活动状态机
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_WAKE_UP_THS, threshold & 0x3F);

    // Wake-up duration | 唤醒持续时间
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_WAKE_UP_DUR, 0x00);

    // Route wake-up to INT1 | 将唤醒路由到 INT1
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_MD1_CFG, 0x20);

    // Clear interrupt | 清除中断
    uint8_t reg;
    myIMU.readRegister(&reg, LSM6DS3_ACC_GYRO_WAKE_UP_SRC);
}

void imuAttachInterrupt() {
    attachInterrupt(digitalPinToInterrupt(IMU_INT1_PIN), imuInt1Isr, RISING);
}

void imuDetachInterrupt() {
    detachInterrupt(digitalPinToInterrupt(IMU_INT1_PIN));
}

uint8_t imuClearLatchedInterrupt() {
    uint8_t reg;
    myIMU.readRegister(&reg, LSM6DS3_ACC_GYRO_WAKE_UP_SRC);
    return reg;
}

void imuShutdown() {
    Wire.end();
}
