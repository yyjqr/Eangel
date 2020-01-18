#ifndef IMURECORD_H
#define IMURECORD_H



void*  save_imu_thread();
void*  save_temperature_thread();
void* test_thread();

int initIMU(struct bmi088_dev *dev);


#endif // IMURECORD_H