/****定时拍摄1分钟的图片，并以当前时间+字符的形式命名***by YJ20170908----》201907 ---》202003 */
// 基于opencv3,4 c++的函数写法，重写摄像头拍摄图片的程序。硬件基于树莓派。

#include <stdio.h>
#include <stdlib.h>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/core/core.hpp>   //writer 0306
#include "iostream"
#include <time.h>
#include <string>
#include <sstream>
using namespace std;

using namespace cv;
int main(int argc, char **argv) {
    /* init camera */
    VideoCapture pCapture;
    pCapture.open(-1); //从摄像头读入视频 0表示从摄像头读入  -1表示任意摄像头 202003
    //double rate=25.0;//fps

    pCapture.set(CAP_PROP_FRAME_WIDTH, 1280);
    pCapture.set(CAP_PROP_FRAME_HEIGHT, 960);

    string str[200]={"cam0"}; //数组设置过小，导致只能拍摄100张图片，现已修改为2000
    string strTemp="/tmp/";//间隔一段时间缓存到tmp目录下一张图片 20190217 ！！
    //stringstream ss;
    time_t timep,t;
    tm* local;
    char buf[1000]={0};
    unsigned int timeDuration=1;  //--->1min 20190613
    Mat frame;
    unsigned int j;

    if (!pCapture.isOpened())
    {
        cout << "can not open";
        cin.get();
        return -1;
    }
    cout<<"Video capture time(minutes)拍摄时间（分钟）:1分钟"<<endl;
    //cin >>timeDuration;
    //cvNamedWindow("Eangel cam",0);  //chuanjian  0 window can be changed!0312
    int count=0;//add 0807
    const char *pImageFileName;
    for(unsigned int i=0;i<timeDuration*42;i++)   //*60/5*4  (20180807yj)------------>*60/5.5*4 (1121)
    {
        pCapture >>frame;
        //writer  <<frame;
        //imshow("Eangel cam",frame);
        waitKey(1000); //延时1s
        j=i%4;
        
        strTemp="/tmp/";
        memset(buf,0,sizeof(buf));
        if(j==0)   //初始保存一张，一般每次开机拍摄能快速获取最新的照片  前面几张比较暗，获取的第10次的，第三张左右的图片20181012
        {
            t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
            local = localtime(&t); //转为本地时间
            strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
            strTemp+=buf;
            //cout<<strTemp<<endl;

            strTemp+=".jpg"; //gmtime

            pImageFileName=strTemp.c_str();

            //pImageFileName = "/tmp/EangelCam2019.jpg";
            printf("%s\n",pImageFileName);
            imwrite(pImageFileName,frame);  //c++ func 201907
        }
    }

    return 0;
}

