/****定时拍摄10分钟的图片，并以当前时间+字符的形式命名***by YJ20170908----》201907 --->202005 */
// 基于opencv3,4 c++的函数写法，重写摄像头拍摄图片的程序。硬件基于树莓派。

#include <stdio.h>
#include <stdlib.h>
#include <opencv2/core/core.hpp>   //writer 0306 ---> //change to the first order 202004
#include <opencv2/highgui/highgui.hpp>

#include "iostream"
#include <time.h>
#include <string>
#include <sstream>
using namespace std;

using namespace cv;
int main(int argc, char **argv) {
    /* init camera */
    VideoCapture pCapture;
    pCapture.open(-1); //从摄像头读入视频 0表示从摄像头读入 -1 表示任意摄像头 2020
     //double rate=25.0;//fps

    pCapture.set(CAP_PROP_FRAME_WIDTH, 1280);
    pCapture.set(CAP_PROP_FRAME_HEIGHT, 960);

    string str[2000]={"cam0"}; //数组设置过小，导致只能拍摄100张图片，现已修改为2000
    string strTemp="/tmp/";//间隔一段时间缓存到tmp目录下一张图片 20190217 ！！
    time_t timep,t;
    tm* local;
    char buf[2000]={0};
    unsigned int timeDuration=10;  //18--->10min 不需要保存过多的图片  20190613
    Mat frame;
    unsigned int j;

    if (!pCapture.isOpened())
    {
        cout << "can not open";
        cin.get();
        return -1;
    }
    cout<<"Video capture time(minutes)拍摄时间（分钟）:10分钟"<<endl;
    //cin >>timeDuration;
    //cvNamedWindow("Eangel cam",0);  //chuanjian  0 window can be changed!0312
    int count=0;//add 0807
    const char *pImageFileName;
    for(unsigned int i=0;i<timeDuration*42;i++)   //*60/5*4  (20180807yj)------------>*60/5.5*4 (1121)
    {
        pCapture >>frame;
        if(frame.empty()){
        printf("cam is NG,frame is empty\n");
        exit(-1);

         }

        //writer  <<frame;
        //imshow("Eangel cam",frame);
        waitKey(900); //延时5s
        j=i%4;
        if(i==10)   //初始保存一张，一般每次开机拍摄能快速获取最新的照片  前面几张比较暗，获取的第10次的，第三张左右的图片20181012
        {
            t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
            local = localtime(&t); //转为本地时间
            strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
            strTemp+=buf;
            cout<<strTemp<<endl;

            strTemp+=".jpg"; //gmtime

            pImageFileName=strTemp.c_str();

            //pImageFileName = "/tmp/EangelCam2019.jpg";
            printf("%s\n",pImageFileName);
            imwrite(pImageFileName,frame);  //c++ func 201907
        }
        if(j==0)
        {
            t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
            local = localtime(&t); //转为本地时间
            strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
            str[j]=buf;
            cout<<str[j]<<endl;
            //tempStr=asctime(gmtime(&timep))+".jpg";
            str[j]+="_";

            std::string s=std::to_string(count);
            str[j]+=s;
            count++;


            str[j]+=".jpg"; //gmtime

            pImageFileName=str[j].c_str();

            //sprintf(pImageFileName,"%d.jpg",i);
            printf("%s\n",pImageFileName);
            //cvGetImage(pImageFileName, pFrame);
            imwrite(pImageFileName,frame);
            waitKey(1500); //延时2.5s---------------->1.5s （20181015减少拍摄时间，周期5.5s，但系统实际可能达6s，这样保证拍摄时长10分钟，并间隔较小！！！
        }
    }

    return 0;
}

