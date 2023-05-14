#include <stdio.h>
#include <stdlib.h>  //atof
#include <string.h>

#include <unistd.h>   //sleep
#include "log.h"
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

    while (is_running) {
        sleep(1);
        
        ret = commandDfResult();
      // printf("ret is %d \n",ret);
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
    fp = popen("df | grep /dev/root|awk '{print$5}' ", "r");
    if(fp)
    {
        memset(buf, 0, sizeof(buf));
        //printf("fp addr: %x \n",fp);
//从文件指针stream中读取n-1个字符，存到以str为起始地址的空间里，直到读完一行
        if(fgets(buf, sizeof(buf) , fp) != 0)
        {
            //printf("buf: %s \n",buf);
            pclose(fp);
             double ratio;
             ratio=atof(buf);
            if(ratio>95)
             {
            printf("storage is %f,FULL!\n",ratio);
             return -1;

             }
        }
      
    }
    else{
   printf("open fp failed\n");
   }


    return 0;
}
