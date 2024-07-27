#include <iostream>
#include <cmath>
#include <fstream>
using namespace std;
 ofstream  finCube;

bool is_perfect_square(long long n) {
    long long sqrt_n = static_cast<long long>(std::sqrt(n));
    return sqrt_n * sqrt_n == n;
}

void find_cuboid(long long max_length) {
    static long long searchTimes =0;
    for (long long a = 1; a <= max_length; a++) {
 //a,b,c不可能相等
        for (long long b = a+1; b <= max_length; b++) {
            long long c2 = a * a + b * b;
            long long c = static_cast<long long>(std::sqrt(c2));
            searchTimes++;
// a+b+c必定是偶数，根据a^2+b^2+c^2=p^2等推出
            //if((a+b+c)%2 !=0) continue;

            if((a+b) < c) continue;
            if((a+c) < b) continue;
              //b+c>a+1>a
            if(searchTimes%10000==0)
             {cout <<"searchTimes:"<<searchTimes<<endl;
             finCube <<"searchTimes:"<<searchTimes<< "step,try a cube" <<"a|b|c:" <<a<<","<<b <<","<<c<<endl;
                     }
            if(b%2000==0){printf("b is %lld\n",b);}
            if (c * c != c2) continue;  // 剪枝
            if(c%2000 ==0 || (a+b+c)%30 ==0)
            {
               finCube << "step,try a cube" <<"a|b|c:" <<a<<","<<b <<","<<c<<endl;
             }
            long long sum2 = a * a + b * b + c * c;
            if (is_perfect_square(sum2)) {
                 finCube << "find a cube" <<"a|b|c:" <<a<<""<<b <<""<<c<<endl;
                std::cout << "长方体的边长为: a = " << a << ", b = " << b << ", c = " << c << std::endl;
            }
        }
    }
}

int main() 
{
    long long max_length = 1000000000;
     string fileName="numberCube2024.txt";
  //ofstream  finCube;
  finCube.open(fileName);
  if(!finCube.is_open()){
   cerr<<"open file failed!\n";
   return -1;
  }

    find_cuboid(max_length);
    return 0;
}
