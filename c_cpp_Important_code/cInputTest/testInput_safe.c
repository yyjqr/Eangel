#include <stdio.h>

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

  int a=(0x1 << 0);
   int b=(0x1 << 1);
 int c=(0x1 << 2);
printf("a:%d,b:%d,c:%d\n",a,b,c);  

  unsigned int stateOff=0x00;
  unsigned int stateOn=0x01;
printf("a:%d,b:%d\n",stateOff,stateOn);
printf("a:%u,b:%u\n",stateOff,stateOn);  

return 0;
}
