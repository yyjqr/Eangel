	 #include <stdio.h>
        #include <opencv2/opencv.hpp> 
	#include <time.h> 
	#include <string> //add 20180904
	
	#include <stdlib.h>
      #include <pthread.h>  //pthread create
	using namespace cv;  
	using namespace std; 
	
    char buf[50]={0}; //全局变量，用于获取文件名的时间

void* record_thread(void *args);

  int main()  
	{  
	string str[20]={"cam0"}; //数组设置过小，导致只能拍摄100张图片，现已修改为2000
	time_t timep,t,NOW;
	tm* local;
	//char buf[30]={0};  
	double elapsedseconds;
	VideoCapture videoCapturer(0);//如果是笔记本，0打开的是自带的摄像头，1 打开外接的相机  
	//char play_cmd[80];
        //double rate = capture.get(CV_CAP_PROP_FPS);//视频的帧率  
	/**
	* Get some information of the video and print them
	*/
        videoCapturer.set(CV_CAP_PROP_FOURCC,CV_FOURCC('M', 'P','4', '2'));
        videoCapturer.set(CV_CAP_PROP_FRAME_WIDTH, 1280);
        videoCapturer.set(CV_CAP_PROP_FRAME_HEIGHT, 720);
	if(videoCapturer.isOpened())
	{
	//double totalFrameCount = videoCapturer.get(CV_CAP_PROP_FRAME_COUNT);  //这个参数获取会报错！！ VIDEOIO ERROR: V4L2: getting property #7 is not supported
	unsigned int width = videoCapturer.get(CV_CAP_PROP_FRAME_WIDTH),
	height = videoCapturer.get(CV_CAP_PROP_FRAME_HEIGHT);
	
	cout << "video info"<<"[Width:" << width << ", Height:" << height
	<< ", FPS: " << videoCapturer.get(CV_CAP_PROP_FPS)
	<< ", FrameCount: " << " " << "]" << std::endl;  //from Github
	
	}
	else
	{
	cout<<"Capture not OK";
	return -1;
	}
	//Mat frame;  
	t=time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
	//local=asctime(localtime(&timep));    //gmtime(WRONG)--->localtime(0903)
	local = localtime(&t); //转为本地时间
	strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
	str[0]=buf;
	str[0]+=".avi"; //gmtime
	//const char *pImageFileName = "webcam20170830.jpg";
	
	pthread_t record_thread_t;
	string pVideoFileName;
	pVideoFileName=str[0];  
	cout<<str[0]<<endl;
	cout<<"FileName:"<<pVideoFileName<<endl;
	VideoWriter writer(pVideoFileName, CV_FOURCC('M', 'P','4', '2'), videoCapturer.get(CV_CAP_PROP_FPS),Size(videoCapturer.get(CV_CAP_PROP_FRAME_WIDTH),
	videoCapturer.get(CV_CAP_PROP_FRAME_HEIGHT)));//AVI 0901   avi格式 MJPG编码
	 
        pthread_create(&record_thread_t,NULL,record_thread,NULL);

	while (videoCapturer.isOpened())  
	{
		Mat frame;  
		//frame=cvQueryFrame(capture); //首先取得摄像头中的一帧     add 
		elapsedseconds=difftime(time(&NOW),t);  //比较前后时间差 0912
		/*if ((frame.rows==0)||(frame.cols==0))
		{
		printf("frame capture failed\n");
		//system("pause");//linux不支持
		system("read -p 'Press Enter to continue...' var");
		exit(0);
		}*/  //这里运行提示捕获失败！！
		videoCapturer >> frame;  
		
		writer << frame;  
		//imshow("EangelUSBVideo", frame); 
		if(elapsedseconds>10*60) //录制10分钟左右的视频
		{
		//cout<<"recording time is over"<<endl;
		printf("Recording time is %f  minutes,finished!", elapsedseconds/60);		
		exit(0);
		//break;
		}
		
		/*if (char(waitKey(5)) == 27||char(waitKey(5)) == 'q')//27是键盘摁下esc时，计算机接收到的ascii码值  
// ----->如果waitKey函数不进行数据格式转换为char类型，则该程序在VS中可以正常运行，但是在linux系统不能运行，主要是由于数据格式的问题linux char() 1118
		{  
		break;  
		} */ 
	}
	writer.release();
	//videoCapturer.release();
	return 0;  
}  
	


void* record_thread(void *args)
{
   char play_cmd[80];
/*
 -f --format=FORMAT
		设置格式.格式包括:S8  U8  S16_LE  S16_BE  U16_LE
              U16_BE  S24_LE S24_BE U24_LE U24_BE S32_LE S32_BE U32_LE U32_BE
              FLOAT_LE  FLOAT_BE  FLOAT64_LE  FLOAT64_BE   IEC958_SUBFRAME_LE
              IEC958_SUBFRAME_BE MU_LAW A_LAW IMA_ADPCM MPEG GSM

       -r, --rate=#<Hz>
		设置频率.
 -D, --device=NAME
		指定PCM设备名称.
*/
   sprintf(play_cmd,"arecord  -f cd -t wav -r 10000 -D plughw:1,0 %s.wav",buf); 
        system(play_cmd); //增加录音 20190601
   return 0;    
}

