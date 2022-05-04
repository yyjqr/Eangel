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
#include "logging.h"
#include "file.h"

using namespace std;

using namespace cv;
string Absolute_exec_path=""; //定义执行程序绝对路径的变量

int main(int argc, char **argv) {

    time_t timep,t;
    tm* local;
    char buf[100]={0};
    unsigned int timeDuration=2;
    const int width=1280, height=720;
    const int channel=3;
    Mat frame;

    Log camlog;
    FILESAVE file_get_exec_absolute_path;
    Absolute_exec_path=file_get_exec_absolute_path.get_cur_executeProgram_path();
    string timestr;
    //取出执行程序绝对路径的上一层路径！！  0124
    string::size_type pos=Absolute_exec_path.find_last_of("/");
    if(pos!=string::npos){
        Absolute_exec_path=Absolute_exec_path.substr(0,pos); //pos为字符数
//        cout<<"get exec UP path:"<<Absolute_exec_path<<endl;
    }
    string log_Path=Absolute_exec_path+"/log";
//    cout<<" log path:"<<log_Path<<endl;
    string logDir="mkdir -p "+ log_Path;
    system(logDir.c_str());
    std::string log_file=log_Path+"/robot";   //日志在打开cam之前创建。
    t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
    local = localtime(&t); //转为本地时间
    strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
    timestr=buf;
    log_file+=timestr;
    log_file+=".log";
    camlog.SetFile(log_file.c_str());

    int count=0;//add 0807
    const char *pImageFileName;
    vector<uchar> array(1280*960);
    uchar camData[width*height*channel]={'0'};
    char recvCMD[3]={'\0'};

    /* init camera */
    VideoCapture pCapture;
    pCapture.open(-1); //从摄像头读入视频 0表示从摄像头读入  -1表示任意摄像头 202003
    //double rate=25.0;//fps

    pCapture.set(CAP_PROP_FRAME_WIDTH, 1280);
    pCapture.set(CAP_PROP_FRAME_HEIGHT, 720);

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


    for(unsigned int i=0;i<timeDuration*42;i++)   //
    {
        t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
        local = localtime(&t); //转为本地时间
        strftime(buf, 64, "%H:%M:%S", local);//%Y-%m-%d_
        string cur_time_str="";
        cur_time_str=buf;
        pCapture >>frame;
        imshow("RobotCam",frame);
        waitKey(100); //延时0.1s
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
        cout<<"cur_time:"<<cur_time_str<<endl;
        cout<<"\n recvStatus:"<<recvStatus<<" CMD:"<<recvCMD<<endl;
        if(recvStatus)
        {

            if(strcasecmp(recvCMD,"PIC")==0)
            {
                //        cout<<"recv CMD"<<recvCMD<<;
                int ret=camSocket.sendData((char*)camData,frame.rows*frame.cols*channel);
                //        cout<<"send Status:"<<ret<<"pics:"<<i<<endl;
                cout<<"send pics:"<<i<<endl;
                LogInfo("Send pics:%d\n",i);
            }
        }
        else{
            LogError("recvStatus:%d,recvCMD:%s\n",recvStatus,recvCMD);
        }

    }
    return 0;
}



