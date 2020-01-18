//#include <stdio.h>
#ifndef SPI_INTERFACE_H
#define SPI_INTERFACE_H

//#include "bmi088_defs.h" //uint 类型定义
/**\ header files */
#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <stdint.h>   //uint8_t define header file ???
#include <stddef.h>
#include <stdbool.h>
#endif

#include "unistd.h"

int fd;

///int8_t user_spi_read(uint8_t id, uint8_t reg_addr, uint8_t *data, uint16_t len);
void user_delay_ms(uint32_t period);

int8_t user_spi_read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len);
int8_t user_spi_write(uint8_t id, uint8_t reg_addr, uint8_t *data, uint16_t len);

//add and revise ACC INTF
int8_t user_spi_readACC(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len); 
int8_t user_spi_writeACC(uint8_t id, uint8_t reg_addr, uint8_t *data, uint16_t len);


int openSPI(); 
#endif
