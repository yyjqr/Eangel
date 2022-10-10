#include <iostream>

using namespace std;
#include <unistd.h>  
//sleep func
#include <string.h>
#include <string>
typedef struct stRobotInfo
{
	int carID;
	double velocity;
	double  driveDistance;
	}st_robotInfo;
	
stRobotInfo testStruct();
int testInt();
char* testChar();


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
  stRobotInfo resultInfo;
  resultInfo=testStruct();
  cout<<"driveDistance:"<<resultInfo.driveDistance;
  cout<<"\n carID:"<<resultInfo.carID;
  int res=testInt();
  cout<<"res:"<<res;
  //返回局部地址测试
  char str[50];
  char *p_char;
  p_char=(char*)malloc(50*sizeof(char));
  p_char=testChar();
  cout<<"res:"<<p_char;
 /* if(p_char!=nullptr)
    {
	  free(p_char);
	 }*/
  return 0;
  
}

stRobotInfo testStruct()
{
	 stRobotInfo robotInfo={23,5,0};
	 robotInfo.driveDistance=robotInfo.velocity*5;
	 return robotInfo;
}

int testInt()
{
	 int a;
	 int b=3,c=7;
	 a=b+c;
	 
	 return a;
}

char* testChar()
{
	 char* arr={"hello,test return local variable pointer"};
	 
	 return arr;
}
