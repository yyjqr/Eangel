
#include <unistd.h>  
//sleep func
#include <string.h>
#include <string>
#include <stdio.h>
#include <iostream>
using namespace std;

void  fun(){

cout << "递归" <<endl;
static int i=0;
i++;
cout <<i<< endl;
sleep(1);
fun();
//sleep(2000);

}

int main(int argc,char** argv)
{
    //cout << "Please input your username!" << endl;
  //  string username;
//    getline(cin,username);
   // cout <<username<<endl;
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
    char *saveFormat=nullptr;
     if(saveFormat==nullptr)
        {
            saveFormat=(char*)malloc(3);
        }
//saveFormat="jpg";
char format[]="jpg";
memcpy(saveFormat,format,sizeof(format));
printf("saveFormat addr %x,saveFormat value %c\n",saveFormat,*saveFormat);
   cout<<"saveFormat "<<saveFormat<<endl;
if(saveFormat!=nullptr)
    {
            free(saveFormat);
     saveFormat=nullptr;
        }
    //fun();
  srand((unsigned)time(NULL));
    int c=random();
    cout<<"number c="<<c<<endl;
    return 0;
}
