#ifndef CAMSOCKETPARAM_H
#define CAMSOCKETPARAM_H
#include <stdint.h>
//1280*720=921600 像素或传输图像的大小 *3
//640*480*3=1280*720
//#define IMAGESIZE (921600*3)
const int IMAGESIZE=921600;

struct camInfo
{
    uint8_t *imageBuf=NULL;
    int imageWidth;
    int imageHeight;
    int type;
};

#endif // CAMSOCKETPARAM_H
