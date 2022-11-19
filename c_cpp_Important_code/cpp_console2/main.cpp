/*
 * @Descripttion: 
 * @version: 
 * @Author: Jack
 * @Date: 2022-03-29 11:10:09
 * @LastEditors: Jack
 * @LastEditTime: 2022-07-12 19:15:18
 */
#include <iostream>
#include <unistd.h>

#include <string.h>
#include <string>
using namespace std;

//sleep func
void  fun(){

    cout << "递归" <<endl;
    static int i=0;
    i++;
    cout <<i<< endl;
    sleep(1);
    fun();
    //sleep(2000);

}
typedef struct stRobotInfo
{
    int carID;
    double veloctity;
    double  driveDistance;
}st_robotInfo;

class robot{
    public:
    void robotControl();
    private:
    double veloctity;
};
int main(int argc,char** argv)
{
    cout << "Please input your username!" << endl;
    string username;
    getline(cin,username);
    cout <<username<<endl;
    sleep(2);
    //int a=atoi(argv[1]);
    //cout << "output the argument " <<a<<endl;
    string  gnss="[73944.60][113.294307][23.093303][0.0000]";
    cout<<"gnss len" <<strlen(gnss.c_str())<<endl;
    string str="";
    string str1="\0";
    string str2="0";
    char  name[5]={'a','b','c','d','e'};
    str+=name[0];
    cout <<"str:" <<str<<str.length();

    cout <<"str1:" <<str1<<str1.length()<<endl;
    int num=std::stoi(str2);
    cout << "num "<<num<<endl;
    
#ifndef MAX
#define MAX 20
#endif
    cout<<"MAX:"<<MAX;
    char *saveFormat=nullptr;
    if(saveFormat==nullptr)
    {
        saveFormat=(char*)malloc(3);
    }

//错误用法：
//    saveFormat="jpg";  //栈内存和堆内存的区别，赋值
//正确用法：
//    char format[5]="jpg";
//    memcpy(saveFormat,format,3);
    printf("saveFormat addr %x,saveFormat value %c\n",saveFormat,*saveFormat);
    cout<<"saveFormat "<<saveFormat<<endl;
    if(saveFormat!=nullptr)
    {
        cout<<"test free buffer "<<endl;
        free(saveFormat);
        saveFormat=nullptr;
    }
    //fun();
   std::size_t len=gnss.length();
   cout<<"size_t:"<<typeid(len).name()<<endl;
    // robot* robotOne=new robot();
    robot robotOne;
    cout<<"typeid robotOne:"<<typeid(robotOne).name()<<endl;
    return 0;
}
