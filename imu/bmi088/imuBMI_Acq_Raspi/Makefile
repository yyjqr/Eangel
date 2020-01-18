#CC=aarch64-himix100-linux-gcc  
#64位 V8 ？？
#CC=arm-linux-gnueabi-gcc

SRCS = $(wildcard imu_record.c )
TARGET := $(SRCS:%.c=%)

LIB=libbcm2835.a  #ADD LIB 202001
#add 
SRCS += $(wildcard spi_interface.c )

SRCS += $(wildcard bmi088_accel.c )
SRCS += $(wildcard bmi088_gyro.c )
SRCS += $(wildcard log.c )
SRCS += $(wildcard device_sn.c )
#SRCS += $(wildcard config.c )
#SRCS += $(wildcard list.c )
TARGET :=imuBMI_record

##线程编译  加上-lpthread
default:
	#$(CC) -Wall -O2  -I../../drv/extdrv/imu_recorder/ $(SRCS) -o $(TARGET) -lpthread
	$(CC) -Wall -O2   $(SRCS) $(LIB) -o $(TARGET) -lpthread
	

clean:
	rm -rf $(TARGET) *.o



# compile linux or HuaweiLite
#include $(PWD)/../Make.$(OSTYPE)
