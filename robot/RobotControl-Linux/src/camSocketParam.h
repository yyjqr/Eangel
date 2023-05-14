#ifndef CAMSOCKETPARAM_H
#define CAMSOCKETPARAM_H
#include <stdint.h>
//1280*720=921600 像素或传输图像的大小 *3
//640*480*3=1280*720
//#define IMAGESIZE (921600*3)
//const int IMAGESIZE=921600;
const int CAM_ResolutionRatio=3;
<<<<<<< HEAD:robot/RobotControl-ThreadSocketOptQueue/src/camSocketParam.h
const int MAX_LEN=2764800;
enum CAM_TYPE{ Common_Type720p,Small_480p=1,Common_Type1080p};
=======
enum CAM_TYPE{ Small_480p=0,Common_Type720p,Common_Type1080p};
>>>>>>> master:robot/RobotControl-Linux/src/camSocketParam.h
struct camInfo
{
    uint8_t *imageBuf=NULL;
    int imageWidth;
    int imageHeight;
    int type;
};

#endif // CAMSOCKETPARAM_H
