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
return 0;
}
