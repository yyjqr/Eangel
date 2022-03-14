#ifndef MAIN_H
#define MAIN_H
#include "camdata.h"
#include <time.h>
#include <mutex>
deque <st_CamData> cam_deque;
st_CamData st_oneFrame,st_sendFrame,st_tmpFrame;
unsigned int timeDuration=10;
const int width=1280, height=720;
const int channel=3;
bool  b_recvStatus=false;
bool  b_socketRecvError=false;

time_t timep,t,tOne;
    tm* local;
std::mutex camMutex;


#endif // MAIN_H
