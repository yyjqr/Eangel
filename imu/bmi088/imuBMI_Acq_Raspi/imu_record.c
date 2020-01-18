/*******************************************************************************
 * Copyright (c) 2018-2019 Eangel
 *
 * All rights reserved.
 *
 * Contributors:
 *     Jack yang  201908-202001
 *******************************************************************************/

/**
 @file    main.c
  @brief  Imu accelerometer gyroscope  6轴数据100Hz采集获取，温度的读取，保存在mnt下设备号目录文件中

 **/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <time.h>
#include <errno.h>
#include <ctype.h>
#include <math.h> //计算指数等
//#include <sys/io.h> //writel 1014
//#include <unistd.h>

#include "bcm2835.h" //raspi SPI
#include "bmi088_defs.h"
#include "bmi088.h" //初始化和配置sensor函数 0813
#include "bmi088_fifo.h"

#include "imu_record.h"
#include "spi_interface.h"
#include "debug.h"
#include "log.h"

struct bmi088_dev imu0;

extern int get_device_number(char *fileName, char *dest, int dest_len);

#define STAR_OS_CONFIG "carSN.conf"
int trace_level = MSG_LEVEL_ERROR; //debug log
#define IMU_LOG_FILE "/opt/var/log/imuBMI_recorder.log"
char sn[128] = {0}; //add device SN

struct bmi088_sensor_data acc_val, gyro_val;

int initIMU(struct bmi088_dev *dev)
{
    int ret = -1;

    ret = bmi088_accel_init(dev);

    if (ret == 0)
    {
        printf("" STR_OK "Initializing the IMU ACC is OK\n");
    }
    else
    {
        printf("" STR_FAIL " the error code of initial ACC is %d \n", ret);
        log_error("failed to open /dev/imu BMI088 ACC");
    }

    /*****************GYRO INIT***************************/
    // sleep(1);                    // wait some time for IMU after POR.
    ret = bmi088_gyro_init(dev); //陀螺初始会读取相关寄存器 0911

    if (ret == 0)
    {
        printf("" STR_OK " Initializing the IMU GYRO is OK \n");
    }
    else
    {
        dprintf("" STR_FAIL " the error code of initial GYRO is %d \n", ret);
        log_error("failed to open /dev/imu BMI088 device file");
    }

    return ret;
}

int configIMU(struct bmi088_dev *dev)
{
    int ret = -1, rslt = -1;
    int8_t self_rslt;
    rslt = bmi088_accel_switch_control(dev, BMI088_ACCEL_POWER_ENABLE); //使能ACC SENSOR！！
    if (rslt == 0)
    {
        printf("Enable ACC sensor! \n");
    }
    else
    {
        printf("Enable ACC sensor failed .......\n");
        log_error("Enable ACC sensor failed .......");
    }
    ret = bmi088_set_accel_meas_conf(dev); //加计配置 1017

    if (ret == 0)
    {
        printf("config ACC is OK \n");
    }
    else
    {
        printf("" STR_FAIL "the error code of config ACC is %d \n", ret);
        log_error("failed to CONFIG /dev/imu ACC file");
    }

    //  bmi088_perform_accel_selftest(&self_rslt, dev);  //add TEST
    //  dprintf("SELF TEST ACC IS %d !!!......\n",self_rslt);

    /*****************GYRO INIT***************************/
    ret = bmi088_set_gyro_meas_conf(dev); //陀螺配置 1017

    if (ret == 0)
    {
        printf("config GYRO is OK \n");
    }
    else
    {
        printf("" STR_FAIL "the error code of CONFIG GYRO is %d \n", ret);
        log_error("failed to CONFIG /dev/imu GYRO file");
    }

    return ret;
}

struct bmi088_int_cfg gyroINT = {
    .gyro_int_type = BMI088_GYRO_DATA_RDY_INT,
    .gyro_int_channel = BMI088_INT_CHANNEL_3,

};

int bmi088_INT_config(struct bmi088_dev *dev)
{
    int ret = -1;
    //gyro INT config
    // ret = set_int_pin_config(&gyroINT, dev);  //add
    // if (ret == 0)
    // {
    //     printf(" "STR_OK" config GYRO INT PIN is OK \n");
    // }
    ret = bmi088_set_gyro_int_config(&gyroINT, dev);
    if (ret == 0)
    {
        printf(" " STR_OK " config GYRO INT is OK \n");
    }
    else
    {
        printf("the error code of CONFIG GYRO INT is %d \n", ret);
    }

    return ret;
}

int main(int argc, char **argv)
{
    int fd_imu;
    int ret = -1;
    FILE *log_file = NULL;
    char imu_module[LOG_MOD_NAME_LEN] = "[imu_recorder]";
    int b_dump = 0;
    void *thread_result;
    void *thread_resultTemp;   

    for (int i = 0; i < argc; i++)
    {
        if (argv[i][0] == '-' || argv[i][0] == '/')
        {
            switch (argv[i][1])
            {
            case 'd':
            case 'D':
                b_dump = 1;
                break;

            default:
                break;
            }
        }
    }

    log_file = fopen(IMU_LOG_FILE, "a");
    if (log_file != NULL)
    {
        log_set_fp(log_file);
        log_set_module_name(imu_module);

        if (b_dump)
        {
            log_set_level(LOG_INFO);
            log_set_quiet(0);
        }
        else
        {
            log_set_level(LOG_ERROR);
            log_set_quiet(1);
        }

        log_info("Open log file success");
    }

    log_info("MAIN func BMI088 start to acquire");

    //------imu thread---//

    pthread_t save_imu_thread_t, save_temperature_thread_t;
    //printf("Start imu acuquistion");
    printf("IMU BMI088 start to initialize\n");

    if (!bcm2835_init())
    {
        printf("bcm2835_init failed. Are you running as root??\n");
        return 1;
    }
    if (!bcm2835_spi_begin())
    {
        printf("bcm2835_spi_begin failedg. Are you running as root??\n");
        return 1;
    }

    bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);    //大小端
    bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_256); //SPI速率 1MHZ
    bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);                 //模式
    bcm2835_spi_chipSelect(BCM2835_SPI_CS0);                    //片选
    bcm2835_spi_chipSelect(BCM2835_SPI_CS1);                    //片选
    bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS0, LOW);    //使能片选
    //bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS1, LOW);//使能片选

    //初始化设备相关参数
    //#####################################//
    imu0.interface = BMI088_SPI_INTF;
    imu0.write = user_spi_write;
    imu0.read = user_spi_read;
    imu0.writeACC = user_spi_writeACC;
    imu0.readACC = user_spi_readACC;
    imu0.delay_ms = user_delay_ms;
    imu0.gyro_cfg.odr = BMI088_GYRO_BW_47_ODR_400_HZ; //add  setup 1125  BMI088_GYRO_BW_32_ODR_100_HZ---->BMI088_GYRO_BW_47_ODR_400_HZ  1203---> BMI088_GYRO_BW_116_ODR_1000_HZ
    imu0.accel_cfg.odr = BMI088_ACCEL_ODR_400_HZ;     //add

    ret = initIMU(&imu0);

    ret = configIMU(&imu0);
    printf("config status  is %d \n", ret); //test

    bmi088_INT_config(&imu0);

    if (pthread_create(&save_imu_thread_t, NULL, save_imu_thread, NULL))
    {
        printf("Create imu thread error \n");
    }
    //printf("Start Temperature acuquistion \n");

    //sleep(2); //open imu,then can go to read temperature!!So wait 0128

    /*  if (pthread_create(&save_temperature_thread_t, NULL, save_temperature_thread, NULL))
    {
        printf("Create temp thread error");
    }*/
    ret = pthread_join(save_imu_thread_t, &thread_result);
    if (ret != 0) {
    perror("Thread join failed");
    exit(EXIT_FAILURE);
    }
    
    /*ret = pthread_join(save_temperature_thread_t, &thread_resultTemp);
    if (ret != 0) {
    perror("Thread temp join failed");
    exit(EXIT_FAILURE);
    }*/

    return 0;
}

void *save_imu_thread()
{

    int ret = 1;
    int leastBit = 0;
    int rdyByte = 0;
    double acc_x_in_mg = 0, acc_y_in_mg = 0, acc_z_in_mg = 0;
    double gyro_x_in_deg = 0, gyro_y_in_deg = 0, gyro_z_in_deg = 0; //0824
    uint8_t reg_addr;
    uint8_t data;
    // initialize imu
    //ret=initIMU(&imu0);

    time_t timep;

    struct tm *p;

    time(&timep);

    p = localtime(&timep); //取得当地时间

    FILE *imu_fp;

    char imu_path[100]; //注意数组短，造成错误！！

    struct timespec begin_write_tp, cur_tp, tv;
    struct timespec tim, tim2;

    unsigned char acc_status;

    memset(sn, '\0', 128);
    ret = command_SN_Parse(sn);
    if (0 == ret)
    {
        log_info("sn:%s length:%d", sn, strlen(sn));
    }
    else
    {
        log_error("failed to get_device_number from %s, ret:%d ", STAR_OS_CONFIG, ret);
        return ret;
    }
    sprintf(imu_path, "%s/%d%02d%02d_%02d%02d%02d_imu.txt", sn,(1900 + p->tm_year), (1 + p->tm_mon), p->tm_mday, p->tm_hour, p->tm_min, p->tm_sec);
    printf("open file %s \n", imu_path);
    imu_fp = fopen(imu_path, "w+");
    if (imu_fp != NULL)
    {
        log_info("open %s success, fp:%ld ", imu_path, imu_fp);

        fsync(imu_fp);
    }
    else
    {
        log_error("failed to open %s", imu_path);
    }

    clock_gettime(CLOCK_REALTIME, &begin_write_tp);

    while (1)
    {

        //ret =bmi088_get_accel_fifo_data(&imu0);
        //ret_gyro = bmi088_get_gyro_fifo_data(&imu0);

        if (imu_fp != NULL)
        {

            ret = bmi088_get_accel_status(&acc_status, &imu0);
            //如果读到的数据是FF ，是否是数据OK？？？？ 1205
            if (ret == 0)
            {
                leastBit = acc_status & 0x80; //最高第7位acc_drdy为1；
            }
            // if (leastBit == 0x80)
            // {
            //     printf("ACC Interupt status data is 0x%02X ,leastBit is 0x%02X \n", acc_status, leastBit);
            // }
            
            /* Read gyro INT_STAT_1 */
            reg_addr = BMI088_GYRO_INT_STAT_1_REG; //BMI088_ACCEL_INT_STAT_1_REG

            ret |= bmi088_get_gyro_regs(reg_addr, &data, BMI088_ONE, &imu0);

            rdyByte = data & 0x80; //最高第7位acc_drdy为1；
            if (rdyByte == 0x80)
            {
                // printf(" " STR_OK " GYRO  GYRO_INT_STAT is 0x%x -----\n", data); //test
                log_trace(" " STR_OK " GYRO  GYRO_INT_STAT is 0x%x -----\n", data);
            }
            /* else
                    {
                        
                        //printf(" "STR_FAIL" GYRO  GYRO_INT_STAT is 0x%x -----\n", data);
                    }*/

            //判断条件不是rdyByte==1 !!!
            if (rdyByte == 0x80 && leastBit == 0x80)
            //if (leastBit == 0x80)
            //if (rdyByte == 0x80)
            {

                //ACC data read
                //printf("Interupt status data is %d.Data Ready\n",rdyByte);
                //uint16_t bmi088_extract_accel(struct bmi088_sensor_data *accel_data, uint16_t *accel_length, const struct bmi088_dev *dev)
                bmi088_get_accel_data(&acc_val, &imu0);       //
                acc_x_in_mg = acc_val.x / 32768.0 * 1000 * 3; //3g 量程     0x01   2^(0+1)*1.5=3 新版已解决0915
                acc_y_in_mg = acc_val.y / 32768.0 * 1000 * 3; //3g 量程     0x01
                acc_z_in_mg = acc_val.z / 32768.0 * 1000 * 3; //3g 量程     0x016
                log_info("the READ ACC_x_INT16 is %d,    ax is %f mg\n", acc_val.x, acc_x_in_mg);
                log_info("the READ ACC_y_INT16 is %d,    ay is %f mg\n", acc_val.y, acc_y_in_mg);
                log_info("the READ ACC_z_INT16 is %d,    az is %f mg\n", acc_val.z, acc_z_in_mg);

                //gyro data read
                bmi088_get_gyro_data(&gyro_val, &imu0);
                gyro_x_in_deg = gyro_val.x / 32767.0 * 2000; //量程 +- 2000deg/s
                gyro_y_in_deg = gyro_val.y / 32767.0 * 2000;
                gyro_z_in_deg = gyro_val.z / 32767.0 * 2000;
                log_info("the READ gyro_val.x is %d,   gyro_x_in_deg is %f deg/s\n", gyro_val.x, gyro_x_in_deg);
                log_info("the READ gyro_val.y is %d,   gyro_y_in_deg is %f deg/s\n", gyro_val.y, gyro_y_in_deg);
                log_info("the READ gyro_val.z is %d,   gyro_z_in_deg is %f deg/s\n", gyro_val.z, gyro_z_in_deg);


                // struct timezone tz;

                clock_gettime(CLOCK_REALTIME, &tv);                          //CLOCK_MONOTONIC --->CLOCK_REALTIME
                double imu_utc_time = tv.tv_sec + tv.tv_nsec / 1000000000.0; //REVISE 0130  clock_gettime(CLOCK_MONOTONIC, ...) provides nanosecond resolution, is monotonic.
                                                                             //I believe the 'seconds' and 'nanoseconds' are stored separately, each in 32-bit counters.
                                                                             // printf("board system is %lf\n",imu_utc_time);  //test                //1541472902.070,$IMU,CHIP,0,RESULT,IMU,ax,0.069580,ay,0.060059,az,1.026611,gx,0.610352,gy,-0.122070,gz,1.327515,*FF
                fprintf(imu_fp, "%.3lf,$IMU,BMI,0,RESULT,IMU,ax,%f,ay,%f,az,%f,gx,%f,gy,%f,gz,%f,*FF\n", imu_utc_time,

                        acc_x_in_mg,
                        acc_y_in_mg,
                        acc_z_in_mg,
                        gyro_x_in_deg,
                        gyro_y_in_deg,
                        gyro_z_in_deg);
                // 先加速度，再角速度0911 --->增加一个%f 0128

                //user_delay_ms(1); //100Hz读取   1130
                tim.tv_sec = 0;
                tim.tv_nsec = 9000000; //10ms

                if (nanosleep(&tim, &tim2) < 0)
                {
                    printf("Nano sleep system call failed \n");
                    return -1;
                }
            }
            clock_gettime(CLOCK_REALTIME, &cur_tp); //%lf
            if ((cur_tp.tv_sec - begin_write_tp.tv_sec) > 60 * 60)
            { //每次录制60分钟 0122
                printf("cur_tp.tv_sec is %ld,  begin_write_tp.tv_sec is %ld  /n", cur_tp.tv_sec, begin_write_tp.tv_sec);
                begin_write_tp = cur_tp;

                fflush(stdout);

                fclose(imu_fp);

                imu_fp = NULL;
            }
        }
        else
        {
            sleep(5);
            time(&timep);

            p = localtime(&timep); //取得当地时间

            printf("Create a new file to record imu data\n");

            sprintf(imu_path, "%s/%d%02d%02d_%02d%02d%02d_imu.txt", sn, (1900 + p->tm_year), (1 + p->tm_mon), p->tm_mday, p->tm_hour, p->tm_min, p->tm_sec);
            printf("Record new imu %s \n", imu_path);

            imu_fp = fopen(imu_path, "w+");

            if (imu_fp == NULL)
            {

                printf("fail to open IMU file:%s\n", imu_path);

                exit(-4);
            }
        }
    }
}

void *save_temperature_thread()
{
    FILE *imuTemp_fp;
    char imuTemp_path[64];
    float imuMeasureTemp;
    snprintf(imuTemp_path, 14, "%s", "/tmp/temp.txt"); //printf--->snprintf

    imuTemp_fp = fopen(imuTemp_path, "w"); //w+ 打开可读写文件，若文件存在则文件长度清为零，即该文件内容会消失。若文件不存在则建立该文件。
    //wb 二进制文件
    if (imuTemp_fp == NULL)
    {

        printf("Fail to open imu temperature file:%s\n", imuTemp_path);

        exit(-4);
    }
    else
    {
        printf(" Open imu temperature file:%s\n", imuTemp_path);
    }
    while (1)
    {
        if (imuTemp_fp != NULL)
        {

            bmi088_get_sensor_temperature(&imu0, &imuMeasureTemp);
            //printf("Read IMU  Temperature %f ℃  ——>——>——>——>****************\n", imuMeasureTemp);
            if (imuMeasureTemp <= 85 && imuMeasureTemp >= -40)
            {
                fprintf(imuTemp_fp, "%f\n", imuMeasureTemp); //
            }
            else
            {
                log_error("Read Temperature ERROR");
            }

            fflush(NULL); //ADD  清除缓冲流，否则一直无输出！！
            sleep(5);     //UPDATE every 1.28S
        }
    }
}
