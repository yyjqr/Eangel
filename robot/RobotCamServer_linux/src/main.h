#ifndef MAIN_H
#define MAIN_H
#include "camdata.h"
#include <time.h>
#include <deque>
#include <mutex>

using namespace std;
deque <st_CamData> cam_deque;
st_CamData st_oneFrame,st_sendFrame,st_tmpFrame;

unsigned int timeDuration=10;
// cam  frame info
int frame_width=1280, frame_height=720;
const int channel=3;
int total_len=2764800;  //1280*720*3的字节数
bool  b_recvStatus=false;
bool  b_socketRecvError=false;


time_t timep,t,tOne;
tm*    local;
std::mutex camMutex;



#endif // MAIN_H
