/**
基于opencv4.1.0，c++ 类和函数的模式，编写读取摄像头拍摄视频帧，保存为以时间命名的文件。另同时创建了录音线程。

yyjqr789@sina.com 原创，如有bug，联系上述邮箱。 
* @date:2019--->202004-->2024.01
**/

#include <stdio.h>
#include <opencv2/core.hpp> //change to the first order
#include <opencv2/opencv.hpp>
#include <opencv2/videoio.hpp>

#include <time.h>
#include <string> //add 20180904

#include <stdlib.h>
#include <pthread.h> //pthread create
#include <unistd.h>	 //getopt 202005

#include "log.h"


#define STR_OK "[\x1b[1;32m OK \x1b[0m]"
#define STR_FAIL "[\x1b[1;31mFAIL\x1b[0m]"
#define VIDEO_LOG_FILE "/var/log/video_cap.log"

using namespace cv;
using namespace std;

char buf[50] = {0}; //全局变量，用于获取文件名的时间
void *record_thread(void *args);
extern void *monitor_mem_thread_proc(void *arg); //ADD 0427
static int program_para(int argc, char **argv, int *fps);
void printHelp(void);

bool bCapture = true;
bool gb_recordFlag = true;

int MSG_LEVEL_OFF     = 0;
int MSG_LEVEL_MAX =5;
int trace_level = MSG_LEVEL_OFF;
int b_dump = 1;
const string str_saveDir="/home/pi/Videos/";


int main(int argc, char **argv)
{

	time_t timep, t, NOW;
	tm *local;
	char stop_cmd[30] = {0};
	double elapsedseconds;
	VideoCapture videoCapturer(-1); //   Numerical value 0 cv::CAP_ANY
	string str[20] = {" "};
	//int level = -1;
	int fps = -1;
	char imu_module[LOG_MOD_NAME_LEN] = "[video_cap]";
	FILE *log_file = NULL;
	if (argc >= 2)
	{
		printHelp();
                program_para(argc, argv, &fps);
	}
	else
	{
		printf("\n YOU can debug with arguments ...\n");
		//exit(1);
	}

	log_file = fopen(VIDEO_LOG_FILE, "a");
	if (log_file != NULL)
	{
		log_set_fp(log_file);
		log_set_module_name(imu_module);

		if (b_dump)
		{
			log_set_level(LOG_DEBUG);
			log_set_quiet(0);
		}
		else
		{
			log_set_level(LOG_INFO);  //将info 信息记录 202309
			log_set_quiet(1);
		}

		log_info("Open log file success");
	}
        else
       {
              printf("open log file error\n");
       }
              if(IsPathExist(str_saveDir)){
        cout << " save path exists\n";
       }
       else{
               char mkdir_cmd[20]="";
               sprintf(mkdir_cmd,"mkdir -p %s",str_saveDir.c_str());
               system(mkdir_cmd);
       }

	/**
		* Get some information of the video and print them
		*/
	//videoCapturer.set(CAP_PROP_FOURCC,CV_FOURCC('M', 'P','4', '2'));
	videoCapturer.set(CAP_PROP_FRAME_WIDTH, 1280);
	videoCapturer.set(CAP_PROP_FRAME_HEIGHT, 720);
	videoCapturer.set(CAP_PROP_FPS, 10);
	if (videoCapturer.isOpened())
	{
		//double totalFrameCount = videoCapturer.get(CAP_PROP_FRAME_COUNT);  //这个参数获取会报错！！ VIDEOIO ERROR: V4L2: getting property #7 is not supported
		unsigned int width = videoCapturer.get(CAP_PROP_FRAME_WIDTH),
					 height = videoCapturer.get(CAP_PROP_FRAME_HEIGHT);

		cout << " " STR_OK " video info"
			 << "[Width:" << width << ", Height:" << height
			 << ", FPS: " << videoCapturer.get(CAP_PROP_FPS)
			 << ", FrameCount: "
			 << " "
			 << "]" << std::endl; //from Github
             log_info("####video info =||Width:%u, Height:%u",  width , height);
	}
	else
	{
		cout << " " STR_FAIL " Capture not OK";
                log_error(" " STR_FAIL " Capture not OK");
		return -1;
	}

	t = time(&timep); //放在循环里面才行，外面的话，时间是一个固定的，不符合要求！！！0907
	local = localtime(&t); //转为本地时间
	strftime(buf, 64, "%Y-%m-%d_%H%M%S", local);
        str[0]=str_saveDir;
        str[0]+=buf;
	str[0] += ".h264"; //gmtime

	pthread_t record_thread_t;
	string pVideoFileName;
         bool b_firstCheck=true;
	pVideoFileName = str[0];
	cout << str[0] << endl;
	cout << "FileName:" << pVideoFileName << endl;
	//VideoWriter writer(pVideoFileName, CV_FOURCC('M', 'P','4', '2'), videoCapturer.get(CAP_PROP_FPS),Size(videoCapturer.get(CAP_PROP_FRAME_WIDTH),videoCapturer.get(CAP_PROP_FRAME_HEIGHT)));//AVI 0901   avi格式 MJPG编码

//	VideoWriter writer(pVideoFileName, VideoWriter::fourcc('M', 'P', '4', '2'), videoCapturer.get(CAP_PROP_FPS),
//					   Size(videoCapturer.get(CAP_PROP_FRAME_WIDTH), videoCapturer.get(CAP_PROP_FRAME_HEIGHT)));
 // X,V,I,D --- H264   DIVX -mp4
VideoWriter writer(pVideoFileName, VideoWriter::fourcc('H', '2', '6', '4'), videoCapturer.get(CAP_PROP_FPS),
                                           Size(videoCapturer.get(CAP_PROP_FRAME_WIDTH), videoCapturer.get(CAP_PROP_FRAME_HEIGHT)));
	pthread_create(&record_thread_t, NULL, record_thread, NULL);

	pthread_t card_monitor_thread;
	pthread_create(&card_monitor_thread, NULL, monitor_mem_thread_proc, NULL);
        log_info(" " STR_OK " line:%d,creat threads to record audio and monitor mem,test bCapture:%d\n", __LINE__, bCapture);
	//namedWindow("RobotCam", WINDOW_NORMAL);
    Mat frame;
        log_info(" " STR_OK " line:%d,creat threads to record audio and monitor mem,test videoCapturer.isOpened():%d\n", __LINE__, videoCapturer.isOpened());
	while (videoCapturer.isOpened())
	{
		
		//frame=cvQueryFrame(capture); //首先取得摄像头中的一帧     add
		if (bCapture)
		{
			gb_recordFlag  = true;
                        elapsedseconds = difftime(time(&NOW), t); //比较前后时间差 0912
			
			videoCapturer >> frame;
			/*if ((frame.rows==0)||(frame.cols==0))
					{
					printf("frame capture failed\n");
					exit(0);
					}*/
			if (frame.empty()){
				printf("frame capture failed\n");
                              log_error(" " STR_FAIL " line:%d,frame capture failed\n",__LINE__);
					exit(-1);
			}
                       else{
                            if (b_firstCheck||static_cast<int>(elapsedseconds) %60 ==0){
                            log_info(" " STR_OK " line:%d,frame capture going+++\n",__LINE__);
                              b_firstCheck =false;
                                 }
                        }
			//这里运行提示捕获失败！！

			writer << frame;
			//imshow("RobotCam", frame);
			if (elapsedseconds > 10 * 60) //录制10分钟左右的视频
			{
				//cout<<"recording time is over"<<endl;
				gb_recordFlag = false;
				printf("Recording time is %f  minutes,finished!\n", (elapsedseconds) / 60);
				log_info("in cam thread, Recording time is %f  minutes,finished!!\n", elapsedseconds / 60);
                                videoCapturer.release(); //增加，避免声音录制未退出 201906
				//return 0;
				//exit(0);
				break;
			}

			if (char(waitKey(5)) == 27 || char(waitKey(5)) == 'q') //27是键盘摁下esc时，计算机接收到的ascii码值
			// ----->如果waitKey函数不进行数据格式转换为char类型，则该程序在VS中可以正常运行，但是在linux系统不能运行，主要是由于数据格式的问题linux char() 1118
			{
				printf("press quit key\n");
				break;
			}
		}
		else
		{
                        gb_recordFlag = false; // add ，对存储满，录制音频线程不能结束的情况处理！！ 2014.01
			printf("DEVICE IS FULL, STOP RECORD VIDEO!\n");
			log_error("DEVICE IS FULL, STOP RECORD VIDEO!\n");
			break;
		}
	}
	sprintf(stop_cmd, "pkill -f  arecord");
	printf("in cam thread,kill arecord\n");
        log_info("in cam thread,STOP RECORD audio!\n");
	system(stop_cmd);
	writer.release();
	//videoCapturer.release();
	return 0;
}

void *record_thread(void *args)
{
	char play_cmd[80];
        char stop_cmd[80];
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
        log_info("audio save path is %s\n",str_saveDir.c_str());
	sprintf(play_cmd, "arecord  -f cd -t wav -r 10000 -D plughw:1,0 %s%s.wav",str_saveDir.c_str(), buf); //buf 为时间名称
	if (gb_recordFlag )
	{
		system(play_cmd); //增加录音 20190601
		printf("test recording+++++");
	}
	else
	{
		printf("finsh recording!");
                sprintf(stop_cmd, "pkill -f  arecord");
        log_info("in thread, STOP RECORD audio!\n");
        system(stop_cmd);

		exit(0); //结束录制进程
	}
	return 0;
}

static int program_para(int argc, char **argv, int *fps)
{
	int c;
	const char *opts;
	int level = 0;

	opts = "d:D:f"; //：后面接调试级别的数字！

	while ((c = getopt(argc, argv, opts)) != -1)
	{
		switch (c)
		{


		case 'd':
			level = atoi(optarg);
			trace_level = level;
			b_dump = 1;
			if (level < MSG_LEVEL_OFF)
				trace_level = MSG_LEVEL_OFF;
			else if (level > MSG_LEVEL_MAX)
				trace_level = MSG_LEVEL_MAX;
			log_set_level(level); //revise 根据参数来设置日志级别
			log_set_quiet(0);
			break;

		case 'D':
			level = atoi(optarg);
			trace_level = level;
			b_dump = 1;
			if (level < MSG_LEVEL_OFF)
				trace_level = MSG_LEVEL_OFF;
			else if (level > MSG_LEVEL_MAX)
				trace_level = MSG_LEVEL_MAX;
			log_set_level(level); //revise 根据参数来设置日志级别
			log_set_quiet(0);			

			break;
		case 'f':

			break;
		}
	}
      return 0;
}

void printHelp(void)
{
	printf("Usage:video_NOShow  [options]\n");
	printf("options:\n");
	printf("  -d no debug-level \t\t Increase debug verbosity level\n");
	printf("  -D Num set-debug-level \t Set the debug verbosity level\n");
	printf("      0  minimum\n");
	printf("      1  debug\n");
	printf("      2  info\n");
	printf("      3  warning\n");
	printf("      4  error\n");
	printf("      5  FATAL error\n");
	printf("      6  maximum\n");
	printf("  -s Num \t\t\t first serial number\n");
	printf("  -t Num \t\t\t second serial number\n");
	printf("  -h help \t\t\t Display this information\n");
}
