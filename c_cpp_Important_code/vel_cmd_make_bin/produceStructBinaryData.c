/*
 * @Descripttion: 
 * @version: 
 * @Author: Jack
 * @Date: 2022-06-27 11:43:17
 * @LastEditors: Jack
 * @LastEditTime: 2022-06-27 14:58:11
 */
#include <stdio.h>
#include <unistd.h>
#include <stdint.h>
// #include <iostream>

#pragma pack(push, 1)

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

typedef struct CmdVel {
  double linear_vel;  // m/s
  double angular_vel;
  uint32_t timestamp;
} cmd_vel_t;

typedef struct CmdVelAllIn {
  double linear_vel;           // m/s
  double angular_vel;          // rad/s
  double pallet_rotation_vel;  // rad/s
  double pallet_jack_vel;      // m/s
  double telescopic_vel;       // m/s
  uint32_t timestamp;
} cmd_vel_all_t;

// typedef struct VelocityCtrl {
//   double vel;
//   bool update;
// } vel_ctrl_t;

// typedef struct CmdVelSeparateAllIn {
//   vel_ctrl_t linear_vel;           // m/s
//   vel_ctrl_t angular_vel;          // rad/s
//   vel_ctrl_t pallet_rotation_vel;  // rad/s
//   vel_ctrl_t pallet_jack_vel;      // m/s
//   vel_ctrl_t telescopic_vel[3];    // m/s. Quantity must be same as TELESCOPIC_DRIVE_QUANTITY
//   uint32_t timestamp;
// } cmd_vel_separate_all_t;

#pragma pack(pop)
int main()
{
  FILE* fp;
  char binary_file[]="stMotionAllCmd.bin";
//  unsigned short int num=0;
  int num=10;
  lift_cmd_param_t  cmd_value;
  cmd_value.lift_ctl=kLiftUp;
  cmd_value.timestamp=4352345;

  cmd_vel_t cmd_vel_lift;
  cmd_vel_lift.linear_vel=1;
   cmd_vel_lift.angular_vel=1;
    cmd_vel_lift.timestamp=4352345;


  cmd_vel_all_t cmd_vel_allMotion;
  cmd_vel_allMotion.linear_vel=1;
  cmd_vel_allMotion.angular_vel=2;
  cmd_vel_allMotion.pallet_rotation_vel=3;
  cmd_vel_allMotion.pallet_jack_vel=-0.5;//lift
  cmd_vel_allMotion.telescopic_vel=1;
  cmd_vel_allMotion.timestamp=45670000;
  

  fp=fopen(binary_file,"w+");
  if(fp!=NULL){
    //   fprintf(fp,"%b",numcmd_vel_t);
   // fwrite(&num,sizeof(short int),1,fp);

  //  printf("sizeof(uint32_t):%u\n",sizeof(uint32_t));
  //  printf("sizeof(cmd_vel_t):%u\n",sizeof(cmd_vel_t));
  //   fwrite(&cmd_vel_lift,sizeof(cmd_vel_t),1,fp);

     printf("sizeof(uint32_t):%u\n",sizeof(uint32_t));
   printf("sizeof(cmd_vel_all_t):%u\n",sizeof(cmd_vel_all_t));
    fwrite(&cmd_vel_allMotion,sizeof(cmd_vel_all_t),1,fp);
  }

  close(fp);
return 0;
}
