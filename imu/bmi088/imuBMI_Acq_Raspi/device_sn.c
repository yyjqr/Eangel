#include <sys/types.h>
#include <stdio.h>
#include <string.h>
//#include "imu_record.h"

 int command_SN_Parse( char *p_sn){
   char buf_sn[100],temp[20];
    FILE *fp = NULL;
  
    fp = popen("cat carSN.conf |grep sn", "r");
    if(fp)
    {
        memset(buf_sn, '\0', sizeof(buf_sn));
        if(fgets(buf_sn, sizeof(buf_sn) - 1, fp) != 0)
        {
          //sn=TMCxxxx
            // printf("the SN is %s ",buf_sn);

            for (int i=0;i<14;i++){

                if(buf_sn[i+3]!=NULL){
                  temp[i]=buf_sn[i+3];
                  //printf("%c",temp[i]);
                  
                }
               
            }
			memcpy(p_sn,temp,14);
			
			printf("p_sn is %s \n",p_sn);
		}
	}
	else{
		printf("NO useful SN number!\n");
		return -1;
	}

	 return 0;
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
