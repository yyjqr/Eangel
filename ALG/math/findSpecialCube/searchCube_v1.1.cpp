#include <iostream>
#include <cmath>
#include <fstream>
using namespace std;
 ofstream  finCube;

bool is_perfect_square(long long n) {
    long long sqrt_n = static_cast<long long>(std::sqrt(n));
    return sqrt_n * sqrt_n == n;
}

void find_cuboid(int threadId, long long start_number, long long max_length) {

    static long long searchTimes =0;
    for (long long a = start_number; a <= max_length; a++) {
 //a,b,c不可能相等
        for (long long b = a+1; b <= max_length; b++) {
            long long c2 = a * a + b * b;
            long long c = static_cast<long long>(std::sqrt(c2));
            {
              std::lock_guard<std::mutex> lock(g_time_mutex);
              searchTimes++;
            }
// a+b+c必定是偶数，根据a^2+b^2+c^2=p^2等推出
            //if((a+b+c)%2 !=0) continue;

            if((a+b) < c) continue;
            if((a+c) < b) continue;
            if(a==b||a==c||b==c) continue; //add 两边相等，不符合 08.20
              //b+c>a+1>a
            //cout <<"threadId:" <<threadId <<"searchTimes:"<<searchTimes<<endl;
            if(searchTimes%10000==0)
             {cout <<"threadId:" <<threadId <<"searchTimes:"<<searchTimes<<endl;
                 if(a>20 && b>20 && c>20){

                    cout <<"searchTimes:"<<searchTimes<< "step,try a cube" <<"a|b|c:" <<a<<","<<b <<","<<c<<endl;
                  }
               }

            if(b%2000==0){printf("b is %lld\n",b);}
            if (c * c != c2) continue;  // 剪枝
            if(c%2000 ==0 || (a+b+c)%30 ==0)
            {
                std::lock_guard<std::mutex> lock(g_time_mutex);
                    finCube << "step,try a cube" <<"a|b|c:" <<a<<","<<b <<","<<c<<endl;
             }
            long long sum2 = a * a + b * b + c * c;
            if (is_perfect_square(sum2)) {
                 std::lock_guard<std::mutex> lock(g_time_mutex);
                 finCube << "find a cube" <<"a|b|c:" <<a<<""<<b <<""<<c<<endl;

                std::cout << "长方体的边长为: a = " << a << ", b = " << b << ", c = " << c << std::endl;
            }
        }
    }
}

int main()
{
    long long max_length = pow(2,45)-1;
    long long oneStepBaseNumber=1e8;
     string fileName="numberCube202409.txt";
  //ofstream  finCube;
  finCube.open(fileName);
  if(!finCube.is_open()){
   cerr<<"open file failed!\n";
   return -1;
  }
  cout <<"start to find\n";
    const int threadCount=1;
    thread th[10];
    for(int i=0 ;i<5; i++)
    {
    th[i] = thread(find_cuboid, i, 1+oneStepBaseNumber*(i+1), max_length);
    };
    for (int i = 0; i < threadCount; i++) {
        th[i].join(); // 等待所有线程完成
    }

    finCube.close(); // 关闭文件

    return 0;
}

