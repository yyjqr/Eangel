/*
 * Linux userspace  code, simple and refer to 
 * osdrv/tools/board/reg-tools-1.0.0/source/tools/ssp_rw.c
 * Revise :Jack yang
 * COMPANY :StarCart.cn
 * Use like: 
 */
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#ifdef __KERNEL__
#include <linux/spi-dev.h>
#include <sys/ioctl.h>
#endif
#include <sys/types.h>
#include <fcntl.h>

#include "spi_interface.h"
#include "hi_spi.h"

#include <sys/stat.h>
#include <sys/ioctl.h>

#include <unistd.h>
#include <ctype.h>

#include <linux/fb.h> //__u64

static void pabort(const char *s)
{
	perror(s);
	abort();
}

void user_delay_ms(uint32_t period)
{
	usleep(period * 1000);
}

void reverse8(unsigned char *buf, unsigned int len)
{
	unsigned int i;

	for (i = 0; i < len; i++)
	{
		buf[i] = (buf[i] & 0x55) << 1 | (buf[i] & 0xAA) >> 1;
		buf[i] = (buf[i] & 0x33) << 2 | (buf[i] & 0xCC) >> 2;
		buf[i] = (buf[i] & 0x0F) << 4 | (buf[i] & 0xF0) >> 4;
	}
}
int openSPI()
{

	int fd;
	int ret = -1;
	int tmp = 0;
	int retval = 0;

	fd = open("/dev/spidev6.1", O_RDWR);
	if (fd < 0)
	{
		printf("failed to open spidev6.1\n");
	}
	else
	{
		printf("open spidev6.1\n");
	}
	tmp = SPI_MODE_3; //| SPI_LSB_FIRST

	retval = ioctl(fd, SPI_IOC_WR_MODE, &tmp);
	if (retval)
	{
		printf("set spi mode fail!\n");
		retval = -1;
		goto end1;
	}

	return retval;

end1:
	close(fd);
}

//UINT32 ssp_write(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len)
int8_t user_spi_read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len)
{
	//printf("Read address is 0x%02x \n", reg_addr);

	int retval = 0;
	int i = 0, index = 0;
	int tmp = 0;
	int fd = -1;
	char file_name[0x20];
	unsigned char buf[0x20] = {0};
	struct spi_ioc_transfer mesg[1];
	unsigned int spi_num = 0, csn = 1, cur_reg_addr; // dev_addr = 0, reg_addr = 0, cur_reg_addr = 0;
	unsigned int num_reg = 1, dev_width = 1, reg_width = 1, data_width = 1, reg_order = 1, data_order = 1;
	uint8_t tempValue[6];

	num_reg = len; //add  data_width=len ----》num_reg=len  读取长度，即读取的寄存器个数  1123！！！
				   /* printf("spi_num:%u, csn:%u\n"
			"dev_addr:0x%04x, reg_addr:0x%04x, num_reg:%d, "
			"dev_width:%d, reg_width:%d, data_width:%d, reg_order: %d, data_order: %d\n",
			spi_num, csn, dev_addr, reg_addr, num_reg,
			dev_width, reg_width, data_width, reg_order, data_order);*/

	sprintf(file_name, "/dev/spidev%u.%u", spi_num, csn);

	fd = open(file_name, 0);
	if (fd < 0)
	{
		printf("Open %s error!\n", file_name);
		retval = -1;
		goto end0;
	}

	tmp = SPI_MODE_3;
	retval = ioctl(fd, SPI_IOC_WR_MODE, &tmp);
	if (retval)
	{
		printf("set spi mode fail!\n");
		retval = -1;
		goto end1;
	}

	memset(mesg, 0, sizeof mesg);

	mesg[0].tx_buf = (__u64)buf;
	mesg[0].rx_buf = (__u64)buf;
	mesg[0].len = reg_width + data_width; //  去掉 dev_width +   1130!!
	mesg[0].speed_hz = 2000000;			  //默认2000000
	mesg[0].bits_per_word = 8;
	mesg[0].cs_change = 1;
	//usleep(2000); //add test

	memset(buf, 0, sizeof buf);
	memset(tempValue, 0, sizeof tempValue); //add

	//printf("====reg_addr:0x%04x====\n", reg_addr);

	for (cur_reg_addr = reg_addr, i = 0; cur_reg_addr < reg_addr + num_reg; cur_reg_addr++, i++)
	{
		index = 0; //test

		if (reg_width == 1)
		{
			*(__u8 *)(&buf[index]) = cur_reg_addr & 0xff;
			index++;
		}
		else
		{
			if (reg_order)
				*(__u16 *)(&buf[index]) = cur_reg_addr & 0xffff;
			else
			{
				*(__u8 *)(&buf[index]) = (cur_reg_addr >> 8) & 0xff;
				*(__u8 *)(&buf[index + 1]) = cur_reg_addr & 0xff;
			}
			index += 2;
		}

		if (data_width == 1)
		{
			*(__u8 *)(&buf[index]) = 0x00;
		}
		else
		{
			*(__u16 *)(&buf[index]) = 0x0000;
		}

		//reverse8(buf, mesg[0].len);

		retval = ioctl(fd, SPI_IOC_MESSAGE(1), mesg);
		//usleep(2000); //add test

		if (retval != (int)mesg[0].len)
		{
			printf("SPI_IOC_MESSAGE error \n");
			retval = -1;
			goto end1;
		}

		retval = 0;
		if (data_width == 1)
		{
			tmp = *(__u8 *)(&buf[index]);
			//*data= buf[index];
			//*(data++) = buf[index];	//test

			tempValue[i] = tmp; //使用i,跟着循环一起增加！！！！ 1202
					//printf("index is %d, tmp is %d,data  addr is %x,data is %u \n\n",index, tmp, data, *data); //add test
				
		}

		else
		{
			if (data_order)
				tmp = *(__u16 *)(&buf[index]);
			else
			{
				tmp = *(__u8 *)(&buf[index]) << 8;
				tmp += (*(__u8 *)(&buf[index + 1]));
			}
		}

		*data = tempValue[0]; //add  数组的首地址返回给单字节读取  或多字节数据读取。

			// if ((i % 0x10) == 0)
		// {
		// 	printf("\ni is  0x%04x:  ", i);
		// }
		//printf("0x%04x  ", tmp);  //注释掉，避免每次打印
	}

	if (i > 2)
	{
		
		for (int j = 0; j < 6; j++)
		{

			*(data + j) = tempValue[j];
			//printf("Test :data[%d] is  %d  ,tempValue[%d] is  %d \n", j,*(data+j) ,j,tempValue[j]);  //*data++ data[j]
		}
	}

	usleep(1000); // test for CS 1212

	//printf("data  addr is %x,data is %u \n\n",data, *data);

	//printf("\n[END]\n");
	// close(fd);
	// return 0;

end1:
	close(fd);
	//printf("\nclose fd\n");

end0:
	return retval;
}

int8_t user_spi_write(uint8_t id, uint8_t reg_addr, uint8_t *data, uint16_t len)
{

	int retval = 0;
	int i = 0, index = 0;
	int tmp = 0;
	int fd = -1;
	char file_name[0x20];
	unsigned char buf[0x10] = {0};
	struct spi_ioc_transfer mesg[1];
	unsigned int spi_num = 0, csn = 1, dev_addr = 0; //reg_addr = 0 , data =0;
	unsigned int dev_width = 1, reg_width = 1, data_width = 1, reg_order = 1, data_order = 1;

	/*printf("spi_num:%u, csn:%u\n"
			"dev_addr:0x%04x, reg_addr:0x%04x, data:0x%04x, "
			"dev_width:%d, reg_width:%d, data_width:%d, reg_order: %d, data_order: %d\n",
			spi_num, csn, dev_addr, reg_addr, data,
			dev_width, reg_width, data_width, reg_order, data_order);*/

	sprintf(file_name, "/dev/spidev%u.%u", spi_num, csn);

	fd = open(file_name, 0);
	if (fd < 0)
	{
		printf("Open %s error!\n", file_name);
		retval = -1;
		goto end0;
	}

	tmp = SPI_MODE_3;
	retval = ioctl(fd, SPI_IOC_WR_MODE, &tmp);
	if (retval)
	{
		printf("set spi mode fail!\n");
		retval = -1;
		goto end1;
	}

	memset(mesg, 0, sizeof mesg);

	mesg[0].tx_buf = (__u64)buf;
	mesg[0].rx_buf = (__u64)buf;
	mesg[0].len = reg_width + data_width; //dev_width +
	mesg[0].speed_hz = 2000000;			  //2000000
	mesg[0].bits_per_word = 8;
	mesg[0].cs_change = 1;
	//usleep(2000); //add test
	memset(buf, 0, sizeof buf);

	// if (dev_width == 1) {
	// 	*(__u8*)(&buf[index]) = dev_addr & 0xff;
	// 	index++;
	// } else {
	// 	*(__u16*)(&buf[index]) = dev_addr & 0xffff;
	// 	index += 2;
	// }

	if (reg_width == 1)
	{
		*(__u8 *)(&buf[index]) = reg_addr & 0xff;
		index++;
	}
	else
	{
		if (reg_order)
			*(__u16 *)(&buf[index]) = reg_addr & 0xffff;
		else
		{
			*(__u8 *)(&buf[index]) = (reg_addr >> 8) & 0xff;
			*(__u8 *)(&buf[index + 1]) = reg_addr & 0xff;
		}
		index += 2;
	}

	if (data_width == 1)
		//*(__u8 *)(&buf[index]) = data & 0xff;
		*(uint8_t *)(&buf[index]) = (*data) & 0xff;
	else
	{
		if (data_order)
			*(__u16 *)(&buf[index]) = (*data) & 0xffff;

		else
		{
			*(__u8 *)(&buf[index]) = (*data >> 8) & 0xff;
			*(__u8 *)(&buf[index + 1]) = (*data) & 0xff;
		}
	}

	// reverse8(buf, mesg[0].len);

	retval = ioctl(fd, SPI_IOC_MESSAGE(1), mesg);
	if (retval != (int)mesg[0].len)
	{
		printf("SPI_IOC_MESSAGE error \n");
		retval = -1;
		goto end1;
	}
	retval = 0;

	//printf("\n[END]\n");
	//close(fd);
end1:
	close(fd);
end0:
	return retval;
}

int8_t user_spi_readACC(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len)
{
	int fd;
	int ret = -1;
	int tmp = 0;
	unsigned char buf[0x10] = {0};
	struct spi_ioc_transfer tr[1];

	fd = open("/dev/spidev0.0", O_RDWR);
	if (fd < 0)
	{
		printf("failed to open spidev0.0\n");
	}

	tmp = SPI_MODE_3; //  | SPI_LSB_FIRST;

	ret = ioctl(fd, SPI_IOC_WR_MODE, &tmp);
	if (ret)
	{
		printf("set spi mode fail!\n");
		ret = -1;
		goto end_spi_read;
	}

	memset(tr, 0, sizeof tr);
	tr[0].tx_buf = (__u64)buf;
	tr[0].rx_buf = (__u64)buf;
	tr[0].len = 2; //dev_width + reg_width + data_width;
	tr[0].speed_hz = 2000000;
	tr[0].bits_per_word = 8;
	tr[0].cs_change = 1;
	//usleep(1000); //add test


	memset(buf, 0, sizeof buf); //add Test 1210

	buf[0] = reg_addr;
	for (size_t i = 0; i < len; i++)
	{
		buf[0] = (reg_addr + i);
		ret = ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
		*(data + i) = buf[1];
		//printf("Test Data %d ,buf[1] is 0x%x \n",*(data+i),buf[1]);
		//usleep(1000);
	}

	if (ret != tr[0].len)
	{
		printf("SPI_IOC_MESSAGE error \n");
		ret = -1;
		goto end_spi_read;
	}
	ret = 0;

end_spi_read:
	close(fd);
	return ret;
}

int8_t user_spi_writeACC(uint8_t id, uint8_t reg_addr, uint8_t *data, uint16_t len)
{
	int fd;
	int ret = -1;
	int tmp = 0;
	unsigned char buf[0x10] = {0};
	struct spi_ioc_transfer tr[1]; //tr---->tr[1]revise 1210

	fd = open("/dev/spidev0.0", O_RDWR);
	if (fd < 0)
	{
		printf("failed to open spidev0.0\n");
		return -1;
	}

	tmp = SPI_MODE_3; //| SPI_LSB_FIRST

	ret = ioctl(fd, SPI_IOC_WR_MODE, &tmp);
	if (ret)
	{
		printf("set spi mode fail!\n");
		ret = -1;
		goto end_spi_write;
	}

	//int ret = 0;
	memset(tr, 0, sizeof tr);
	tr[0].tx_buf = (__u64)buf;
	tr[0].rx_buf = (__u64)buf;
	tr[0].len = len + 1; //dev_width + reg_width + data_width;
	tr[0].speed_hz = 2000000;
	tr[0].bits_per_word = 8;
	tr[0].cs_change = 1;
	//usleep(2000); //add test

	memset(buf, 0, sizeof buf); //add Test 1210
	buf[0] = reg_addr;
	for (size_t i = 0; i < len; i++)
	{
		buf[i + 1] = *(data + i);
	}

	ret = ioctl(fd, SPI_IOC_MESSAGE(1), &tr);
	if (ret != tr[0].len)
	{
		printf("SPI_IOC_MESSAGE error \n");
		ret = -1;
		goto end_spi_write;
	}
	ret = 0; //

end_spi_write:
	close(fd);

	return ret;
}

