#include <stdio.h>
#include <unistd.h>
#include <stdint.h>

typedef enum {
 kLiftStop,
 kLiftDown,
 kLiftUp,
}lift_work_cmd_t;

typedef struct Lift_Cmd_param {
  lift_work_cmd_t lift_ctl;
  // int   control_speed_value; //analog current to control speed
  uint32_t timestamp;
}lift_cmd_param_t;


int main()
{
  FILE* fp;
  char binary_file[]="stVal.bin";
//  unsigned short int num=0;
  int num=10;
  lift_cmd_param_t  cmd_value;
  cmd_value.lift_ctl=2;
  cmd_value.timestamp=4352345;
  fp=fopen(binary_file,"w+");
  if(fp!=NULL){
    //   fprintf(fp,"%b",num);
   // fwrite(&num,sizeof(short int),1,fp);
   printf("sizeof(cmd_value):%d\n",sizeof(cmd_value));
    fwrite(&cmd_value,sizeof(lift_cmd_param_t),1,fp);
  }

  close(fp);
return 0;
}
