
/** @brief
 * c服务器,获取USB相机图像，另外一个线程通过socket发送出去***
 * 基于opencv4 c++，摄像头拍摄图片。硬件基于树莓派/Jetson。
 * @author Jack
 * @date 20170908--->201907 -->
   202003 -->202203
 *

*/

#include "main.h"
#include <stdio.h>
#include <stdlib.h>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/core/core.hpp>   //writer 0306
#include <opencv2/imgproc.hpp>
#include <iostream>
#include <time.h>
#include <string>
#include <sstream>
#include <vector>
#include <deque>
#include "tcpsocket.h"
#include "logging.h"
#include "file.h"
#include <thread>
#include <boost/date_time/posix_time/posix_time.hpp> //ms
#include <boost/date_time/gregorian/gregorian.hpp>
using namespace std;

using namespace cv;
string Absolute_exec_path=""; //定义执行程序绝对路径的变量
const int total_len=2764800;//1280*720*3的字节数

void camReadFunc();
void threadFunc();


int main(int argc, char **argv) {
    char buf[100]={0};

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

    t=time(&timep);
    local = localtime(&t); //转为本地时间
    strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
    timestr=buf;
    log_file+=timestr;
    log_file+=".log";
    camlog.SetFile(log_file.c_str());

    int count=0;//add 0807


    //cin >>timeDuration;
    std::thread camReadThread(camReadFunc);
    std::thread camSendThread(threadFunc);

    camReadThread.join();

    camSendThread.join();


    return 0;
}

void camReadFunc()
{

    Mat frame,rgbFrame;

    char buf[100]={0};
    string cur_time_str="";
    /* init camera */
    VideoCapture pCapture;
    pCapture.open(-1); //从摄像头读入视频 0表示从摄像头读入  -1表示任意摄像头 202003
    //double rate=25.0;//fps

    pCapture.set(CAP_PROP_FRAME_WIDTH, 1280);
    pCapture.set(CAP_PROP_FRAME_HEIGHT, 720);

    if (!pCapture.isOpened())
    {
        cerr << "can not open camera"<<endl;
        exit(0);
        return ;
    }


    cout<<"Video capture 拍摄交互"<<endl;
    if(pCapture.isOpened())  //revise 202205
    {
      for(;;)
      {
        tOne=time(&timep); //放在循环里面才行
        local = localtime(&tOne); //转为本地时间
        strftime(buf, 64, "%H-%M-%S", local);//
        cur_time_str=buf;
        pCapture >>frame;
  //      imshow("RobotCam",frame);

//        waitKey(100); //延时0.1s
        if(frame.isContinuous())
        {
            std::unique_lock<std::mutex> locker(camMutex);

            cvtColor(frame,rgbFrame,COLOR_BGR2RGB);//CV_BGR2RGB
            //            imshow("RobotCamRGB",rgbFrame);
            st_oneFrame.camPtr=(uint8_t*)malloc(height*width*channel*sizeof(uint8_t));
            if(st_oneFrame.camPtr!=nullptr){
               memcpy(st_oneFrame.camPtr,rgbFrame.data,rgbFrame.rows*rgbFrame.cols*channel);
               cam_deque.push_back(st_oneFrame);
            }
            else{
                cerr<<"malloc cam mem failed"<<endl;
            }
            

            cout<<cur_time_str<<":cam deque size:"<<cam_deque.size()<<endl;
            if(cam_deque.size()>8){

                usleep(500);
                if(cam_deque.size()>25){
                    cout<<"cam size is big:"<<cam_deque.size()<<endl;
                    st_tmpFrame=cam_deque.front();
                    //尝试把相关相机数据内存释放出去！！！0314
                    cam_deque.pop_front();
                    free(st_tmpFrame.camPtr);
                    sleep(1);

                }
            }
        }


        //客户端网络连接断开，跳出循环
        if(b_socketRecvError){
            break;
        }
        //        if(i<3){
        //            for(int knum=0;knum<frame.rows*frame.cols*channel;knum++)
        //       	 {
        //        	// cout<<camData[i];
        //          	if( (knum>4000&&knum<5000) || knum%50000==0){
        //            	printf("camData %d Value:%d\n",knum,camData[knum]);

        //             }
        //          }
        //       }
    }
     cerr<<"pCapture.isOpened()"<<"failed"<<endl;
     LogError("Cam Open failed ");
  }

}



void threadFunc()
{
    tcpSocket  camSocket;
    camSocket.connectSocket();

    char recvCMD[3]={'\0'};
    int send_num=0;
    int notGetCmd_times=0;
    char buf[100]={'0'};
    std::string strTimeOfDay;

    while (1)
    {

            boost::posix_time::ptime startTime = boost::posix_time::microsec_clock::local_time();
//    boost::posix_time::time_duration now_time_of_day = boost::posix::microsec_clock::local_time().;
//    cout<<"start time:"<<pTime<<endl;
//    std::string strTimeOfDay = boost::posix_time::to_simple_string(startTime.time_of_day()); // 当前时间：15:03:55
//    cout<<"day time:"<<strTimeOfDay<<endl;

        memset(recvCMD,'\0',sizeof(recvCMD));
        b_recvStatus =   camSocket.recvData(recvCMD,sizeof(recvCMD));
     boost::posix_time::ptime secondTime = boost::posix_time::microsec_clock::local_time();
     strTimeOfDay = boost::posix_time::to_simple_string(secondTime.time_of_day()); // 当前时间：15:03:55

           //cout<<"\n after receive,cur_time:"<<strTimeOfDay<<endl;

        cout<<"Recv state:"<<b_recvStatus<<" CMD:"<<recvCMD<<endl;
        //cout<<"In socket thread,recv CMD:"<<recvCMD<<endl;
        if(b_recvStatus)
        {
         cout<<"\n Receive CMD,cur_time:"<<strTimeOfDay<<endl;
            if(strcasecmp(recvCMD,"PIC")==0)
            {
                //判断size的大小，避免为0时，还在取数据0310
                std::unique_lock<std::mutex> camDataUseLocker(camMutex);
                if(cam_deque.size()>0){
                    st_sendFrame=cam_deque.front();
                    int ret=camSocket.sendData((char*)st_sendFrame.camPtr,total_len);
                    if(ret==total_len){
                        send_num++;
                       // cout<<cur_time_str<<" send pics:"<<send_num<<endl;
                        cout<<strTimeOfDay<<" send pics:"<<send_num<<endl;
                        LogInfo("Send pics:%d\n",send_num);
                    }
                    else{
                        //cout<<cur_time_str<<"部分发送,长度"<<ret<<"图片数:"<<send_num<<endl;
                        LogError("Send len:%d\n",ret);
                    }
                   boost::posix_time::ptime endTime = boost::posix_time::microsec_clock::local_time();
                   boost::posix_time::time_duration td = endTime - startTime;
                   uint64_t  send_time =td.total_milliseconds();
                   cout<<"duration time:"<<send_time<<endl;
                   if(send_time>1500){
                      cerr<<"\n Duration time BIG:"<<send_time<<endl;
                      LogWarning("send time takes much:%d ms\n",send_time);           
                      } 
                   cam_deque.pop_front();
                    free(st_sendFrame.camPtr);//add 分析内存增长未释放的问题 0314
                    cout<<"After send and free,cam deque size:"<<cam_deque.size()<<endl;
                }


            }
        }
        else{
            cerr<<"Not get right cmd,b_recvStatus"<<b_recvStatus<<endl;
            LogError("b_recvStatus:%d,recvCMD:%s\n",b_recvStatus,recvCMD);
            notGetCmd_times++;
            if(notGetCmd_times>5){
                b_socketRecvError=true;
                break;
            }

        }
    }

}


