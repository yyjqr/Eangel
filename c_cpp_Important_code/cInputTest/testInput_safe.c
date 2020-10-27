#include <stdio.h>

int main()
{
   char username[20];
    printf ("Enter your username: ");
/* Read a line of input. */
gets (username);
/* Do other things here... */
   printf("your Input is %s\n",username);
return 0;
}
