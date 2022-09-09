#include <stdio.h>
#include <stdint.h>

typedef struct Robot_motion
{
  double velocity;
  
  double  speed; //w
  double distance;
  double  reduce_ratio;
}robot_motion_t;

int main()
{
   char username[20];
   unsigned int boardNum,servoNum; 
   printf ("Enter your username: ");
/* Read a line of input. */
   fgets (username,10,stdin);
/* Do other things here... */
   printf("your Input is %s\n",username);
   printf ("Enter board num and servo num: ");
   scanf("%d,%d",&boardNum,&servoNum);
  
  printf("input board num %d,servo num %d\n",boardNum,servoNum);
  double vel=0.1000;
  int16_t  speed=vel*10*60*1.0000/0.2000000;
  printf("vel:%f,speed:%d\n",vel,speed);  
  
  robot_motion_t  mobile_robot;
  mobile_robot.reduce_ratio=1.0000000;
  mobile_robot.distance=0.2000000;
  int16_t  speedTwo=vel*10*60*(mobile_robot.reduce_ratio)/(mobile_robot.distance);
  printf("vel:%f,speed:%d\n",vel,speedTwo);  
  return 0;
}
