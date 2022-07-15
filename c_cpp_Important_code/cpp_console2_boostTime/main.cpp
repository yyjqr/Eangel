/*
 * @Descripttion: 
 * @version: 
 * @Author: Jack
 * @Date: 2022-03-29 17:43:12
 * @LastEditors: Jack
 * @LastEditTime: 2022-07-15 18:55:24
 */
#include <iostream>
#include <unistd.h>

#include <string.h>
#include <string>
#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/date_time/gregorian/gregorian.hpp>
#include <boost/chrono.hpp>
using namespace std;
//using namespace  boost;
using namespace boost::chrono;
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

int main(int argc,char** argv)
{

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
    

    boost::posix_time::ptime pTime = boost::posix_time::microsec_clock::local_time();
//    boost::posix_time::time_duraEOKtion now_time_of_day = boost::posix::microsec_clock::local_time().;
    cout<<"start time:"<<pTime<<endl;
    std::string strTimeOfDay = boost::posix_time::to_simple_string(pTime.time_of_day()); // 当前时间：15:03:55
    cout<<"day time:"<<strTimeOfDay<<endl;
    std::cout << "system_clock::now():"<<system_clock::now() << '\n';
    std::cout << "high_resolution_clock::now():"<<high_resolution_clock::now() << '\n';
    uint64_t timestamp=boost::chrono::duration_cast<boost::chrono::milliseconds>(boost::chrono::steady_clock::now().time_since_epoch())
            .count();
        cout<<"timestamp:"<<timestamp<<endl;

    //fun();
    return 0;
}
