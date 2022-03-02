/****定时拍摄1分钟的图片，并以当前时间+字符的形式命名***
by YJ
20170908----》201907 ---》
202003 -->202202 c服务器*/
// 基于opencv3,4 c++的函数写法，重写摄像头拍摄图片的程序。硬件基于树莓派。

#include <stdio.h>
#include <stdlib.h>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/core/core.hpp>   //writer 0306
#include "iostream"
#include <time.h>
#include <string>
#include <sstream>
#include <vector>
#include "tcpsocket.h"

using namespace std;

using namespace cv;
int main(int argc, char **argv) {
    /* init camera */
    VideoCapture pCapture;
    pCapture.open(-1); //从摄像头读入视频 0表示从摄像头读入  -1表示任意摄像头 202003
    //double rate=25.0;//fps

    pCapture.set(CAP_PROP_FRAME_WIDTH, 1280);
    pCapture.set(CAP_PROP_FRAME_HEIGHT, 720);

    string str[200]={"cam0"}; //数组设置过小，导致只能拍摄100张图片，现已修改为2000
    string strTemp="/tmp/";//间隔一段时间缓存到tmp目录下一张图片 20190217 ！！
    //stringstream ss;
    time_t timep,t;
    tm* local;
    char buf[1000]={0};
    unsigned int timeDuration=2;
    const int width=1280, height=720;
    const int channel=3;
    Mat frame;
    unsigned int j;

    if (!pCapture.isOpened())
    {
        cerr << "can not open camera"<<endl;
        //cin.get();
        return -1;
    }

    tcpSocket  camSocket;
    camSocket.connectSocket();

    cout<<"Video capture 拍摄交互"<<endl;
    //cin >>timeDuration;
    //cvNamedWindow("Eangel cam",0);  //chuanjian  0 window can be changed!0312
    int count=0;//add 0807
    const char *pImageFileName;
    vector<uchar> array(1280*960);
        uchar camData[width*height*channel]={'0'};
    char recvCMD[3]={'\0'};


        for(unsigned int i=0;i<timeDuration*42;i++)   //
    {
        pCapture >>frame;
        if(frame.isContinuous())
         {
          //array=frame.data;
           memcpy(camData,frame.data,frame.rows*frame.cols*channel);
         }
    
  /*    for(int i=0;i<frame.rows*frame.cols*channel;i++)
        {
        // cout<<camData[i];
          if(i%500000==0){
            printf("camData %d Value:%d\n",i,camData[i]);
          
             }
          } */

    bool  recvStatus=false;
    memset(camData,'\0',sizeof(recvCMD));
    recvStatus =   camSocket.recvData(recvCMD,sizeof(recvCMD));
    //printf("recvStatus %d,recv  CMD :%s\n",recvStatus,recvCMD);
    cout<<"\n recvStatus:"<<recvStatus<<" CMD:"<<recvCMD<<endl;
    if(recvStatus)
    {
    // cout<<"recvCMD==\"PIC\" " <<(recvCMD=="PIC")<<endl;
     if(strcasecmp(recvCMD,"PIC")==0)
    	{ 
//        cout<<"recv CMD"<<recvCMD<<;
 //       cout<<"Start to send Data"<<endl;
      	int ret=camSocket.sendData((char*)camData,frame.rows*frame.cols*channel); 
        cout<<"send Status:"<<ret<<"pics:"<<i<<endl;
     	}
   };

  }
    return 0;
}
