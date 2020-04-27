#include <stdio.h>
#include <string.h>

//#include "config.h"
#include "log.h"
#include "debug.h"

#include <unistd.h>   //sleep

extern char sn[128];
extern int bCapture;

int commandDfResult();
/*
 * get device no from 'const char* fileName'
 * put device no to global param char sn[64]
 * return 0 success
 * return -1 fail
 */




void* monitor_mem_thread_proc(void* arg) {
  
    
	//static int bCapture=1;
    int ret;
	int is_running=1;
//add 对采集中途拔掉U盘做检测  0326
        // if(commandDfResult()<0){
        //         printf("SD card or usb disk is not mount,NOT RECORD IMU \n");
        //         log_error("SD card or usb disk is not mount,NOT RECORD IMU  ###\n");
      
        // }
    while (is_running) {
        sleep(1);
        
        ret = commandDfResult();
        if (ret == 0) {
				bCapture=1;
        }
        else{
				
				bCapture=0;
				printf("SD card or usb disk is not mount,NOT RECORD video \n");
                log_error("SD card or usb disk is not mount,NOT RECORD video  ###\n");
                sleep(10);


       
        }
    }

    return NULL;
}

int commandDfResult()
{
    char buf[100];
    FILE *fp = NULL;
    fp = popen("df | grep /mnt", "r");
    if(fp)
    {
        memset(buf, 0, sizeof(buf));
        if(fgets(buf, sizeof(buf) - 1, fp) != 0)
        {
            pclose(fp);
            return 0;
        }
    }
    pclose(fp);

    return -1;
}