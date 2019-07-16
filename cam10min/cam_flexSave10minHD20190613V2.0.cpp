	/****定时拍摄100张图片，并以当前时间+字符的形式命名***by YJ20170908  */
	#include <stdio.h>
	#include <stdlib.h>
	//#include "highgui_c.h"  //opencv4 文件名有变动
	#include "videoio/videoio_c.h"    //revise the header file
        #include <opencv2/highgui/highgui.hpp>
	#include <opencv2/core/core.hpp>   //writer 0306
	//#include "opencv.hpp"
	#include "iostream"
	#include <time.h>
	#include <string>
	#include <sstream>
	using namespace std;
	
	using namespace cv;
	int main(int argc, char **argv) {
	/* init camera */
	CvCapture* pCapture = cvCreateCameraCapture(-1);
	//VideoCapture capture(0);
	//double rate=25.0;//fps
	cvSetCaptureProperty(pCapture, CV_CAP_PROP_FRAME_WIDTH, 1280);//revise1225------>0317RE 1280 
	cvSetCaptureProperty(pCapture, CV_CAP_PROP_FRAME_HEIGHT, 960);
	//cvSetCaptureProperty(pCapture, CV_CAP_PROP_FPS, 5);
	
	IplImage *pFrame = 0;
	string str[2000]={"cam0"}; //数组设置过小，导致只能拍摄100张图片，现已修改为2000
	string strTemp="/tmp/";//间隔一段时间缓存到tmp目录下一张图片 20190217 ！！
	//stringstream ss;
	time_t timep,t;
	tm* local;
	char buf[2000]={0};
	unsigned int timeDuration=10;  //18--->10min 不需要保存过多的图片  20190613
	Mat frame;
	unsigned int j;
	
	/*if (NULL == pCapture) {
	fprintf(stderr, "Can't initialize webcam!\n");
	return 1;
	}*/
	cout<<"Video capture time(minutes)拍摄时间（分钟）:18分钟";
	//cin >>timeDuration;
	//cvNamedWindow("Eangel cam",0);  //chuanjian  0 window can be changed!0312
	int count=0;//add 0807
           const char *pImageFileName;	
      for(unsigned int i=0;i<timeDuration*42;i++)   //*60/5*4  (20180807yj)------------>*60/5.5*4 (1121)
	{
			if (NULL == pCapture)
			{
			fprintf(stderr, "Can't initialize webcam!\n");
			return 1;
			}
			
			pFrame = cvQueryFrame(pCapture);  // query a frame 
			//capture >>frame;
			//writer  <<frame;
			if(NULL == pFrame) {
			fprintf(stderr, "Can't get a frame!\n" );
			//return 1;
			break;
			}
			//imshow("Eangel cam",frame);	
			//cvShowImage("Eangel cam",pFrame);	//add 20180312
			waitKey(900); //延时5s
			j=i%4;
                        if(i==10)   //初始保存一张，一般每次开机拍摄能快速获取最新的照片  前面几张比较暗，获取的第10次的，第三张左右的图片20181012
                        {
                         t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
                                //local=asctime(localtime(&timep));    //gmtime(WRONG)--->localtime(0903)
                                //t = time(NULL); //获取目前秒时间
                                local = localtime(&t); //转为本地时间
                                strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
                                strTemp+=buf;
                                cout<<strTemp<<endl;
                                //str[j]+="_";

                                //std::string s=std::to_string(count);
                                //str[j]+=s;
                             
                                strTemp+=".jpg"; //gmtime

                                pImageFileName=strTemp.c_str();
 
				//pImageFileName = "/tmp/EangelCam2019.jpg";
        	                printf("%s\n",pImageFileName);
				cvSaveImage(pImageFileName, pFrame);  
                         }
			if(j==0)
			{
				t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
				//local=asctime(localtime(&timep));    //gmtime(WRONG)--->localtime(0903)
				//t = time(NULL); //获取目前秒时间  
				local = localtime(&t); //转为本地时间  
				strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);   
				//str[i]=timename.to_string("yyyyMMddHHmmss");  //add 20171224 保存图片，然后下载有问题，前面存储的时间格式有空格导致的！！！！！！！！！！！！！！
				str[j]=buf;
				cout<<str[j]<<endl;
				//tempStr=asctime(gmtime(&timep))+".jpg";
				str[j]+="_";
				
				std::string s=std::to_string(count); 
				str[j]+=s;
                                count++;
				
				
				str[j]+=".jpg"; //gmtime 
				
				//const char *pImageFileName = "webcam20170830.jpg";
				
				
				pImageFileName=str[j].c_str();
				     // char name[100];
                                /*if(i>=1&&(i%25==0))   //这里使用i， 如果使用j,每次已经为零了，有问题！ 由于摄像头第一次拍摄的图片可能不清楚，故从大于1开始 20180627
                                {
                                pImageFileName = "EangelCam2019.jpg";
                                }*/

				//sprintf(pImageFileName,"%d.jpg",i);
				printf("%s\n",pImageFileName);
				cvSaveImage(pImageFileName, pFrame);
				waitKey(1500); //延时2.5s--------------------->2s 20180623 T=6S---------------->1.5s （20181015减少拍摄时间，周期5.5s，但系统实际可能达6s，这样保证拍摄时长18分钟，并间隔较小！！！
			 }
	}  
	cvReleaseCapture(&pCapture);  // free memory
	
	return 0;
	}
	
