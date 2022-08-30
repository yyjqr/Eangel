/*
 * @Descripttion:
 * @version:
 * @Author: Jack
 * @Date: 2022-03-29 11:10:09
 * @LastEditors: Jack
 * @LastEditTime: 2022-08-30 14:43:36
 */
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <iostream>
#include <string>

using namespace std;
void Func(char str_arg[100]) { printf("%d\n", sizeof(str_arg)); }
int main(void) {
  char str[] = "Hello";
  printf("%d\n", sizeof(str));
  printf("%d\n", strlen(str));
  char* p = str;
  printf("%d\n", sizeof(p));

  Func(str);

  int AA[] = {1, 3};
  int BB[] = {2, 3};
  int CC[] = {4, 5, 6};
  int* ABC[] = {AA, BB, CC};
  printf("sizeof(ABC):%d,sizeof(BB):%d \n", sizeof(ABC), sizeof(BB));
  printf("sizeof(int):%d,sizeof(AA):%d,AA:0x%x,BB:0x%x  \n", sizeof(int), sizeof(AA), AA, BB);
  for (int i = 0; i < 3; i++) {
    printf("sizeof(ABC[%d]):%d,ABC[i]:0x%x \n", i, sizeof(ABC[i]), ABC[i]);
    //   int* p=ABC[i];
    //     while(true){

    //     if(p){
    //         printf("ABC[i]:%x,*ABC[i]:%d\n",ABC[i],*ABC[i]);
    //         printf("p:%x,*p:%d\n", p, *p);
    //         p++;
    //     }
    //     else{
    //         break;
    //     }
    // }
  }
  string log_Path = "./log";
  //    cout<<" log path:"<<log_Path<<endl;
  string logDir = "mkdir -p " + log_Path;
  system(logDir.c_str());
  std::string log_file = log_Path + "/servo";  //日志在之前创建。
  time_t timep, current_time;
  tm local;  // pointer ---->tm
  char buf[100] = {0};

  printf("test pointer local:0x%x\n", local);
  current_time = time(&timep);  //
                                //   local=localtime(&current_time);

  // if local define as tm*,then will has this error. 08.30
  // test pointer local:0x6
  // Segmentation fault (core dumped)
  localtime_r(&current_time, local);  // 转为本地时间   thread_safe!!
  printf("After assign ,test pointer local:0x%x\n", local);
  strftime(buf, 64, "%Y-%m-%d_%H:%M:%S", local);
  printf("time buf:%s\n", buf);
  log_file += buf;
  log_file += "-test.log";
  printf("log_file:%s\n", log_file.c_str());
  return 0;
}
