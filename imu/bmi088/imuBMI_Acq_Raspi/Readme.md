  树莓派B+使用的是BCM 2835的芯片，官方或开源的驱动都支持的很好：

                http://www.airspayce.com/mikem/bcm2835/bcm2835-1.50.tar.gz
bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);//大小端
    	bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_256);//SPI速率 1MHZ
	bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);//模式
    	bcm2835_spi_chipSelect(BCM2835_SPI_CS0);//片选
	bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS0, LOW);//使能片选   
#版权声明：部分参考： 本文为CSDN博主「一点晴」的原创文章，遵循 CC 4.0 BY-SA 版权协议，转载请附上原文出处链接及本声明。
#原文链接：https://blog.csdn.net/ikevin/article/details/52335308
