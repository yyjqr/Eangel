#include <stdio.h>
#include <unistd.h>


int main()
{
  FILE* fp;
  char binary_file[]="intValue.bin";
//  unsigned short int num=0;
  int num=10;
  fp=fopen(binary_file,"w+");
  if(fp!=NULL){
    //   fprintf(fp,"%b",num);
   // fwrite(&num,sizeof(short int),1,fp);
   printf("sizeof(int):%d\n",sizeof(int));
    fwrite(&num,sizeof(int),1,fp);
  }

  close(fp);
return 0;
}
