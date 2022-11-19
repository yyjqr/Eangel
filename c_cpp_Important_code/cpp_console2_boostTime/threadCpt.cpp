/*
 * @Descripttion: 
 * @version: 
 * @Author: Jack
 * @Date: 2022-09-07 14:06:01
 * @LastEditors: Jack
 * @LastEditTime: 2022-09-07 14:28:15
 */
#include <iostream>
#include <vector>
// #include <algorithm>
#include <numeric>  //accumulate c++20
#include <thread>
using namespace std;
 
//线程要做的事情就写在这个线程函数中
void GetSumT(vector<int>::iterator first,vector<int>::iterator last,long  int &result)
{
    result = accumulate(first,last,0); //调用C++标准库算法
}

// void GetSumT(vector<long int>::iterator first,vector<long  int>::iterator last,long  int &result)
// {
//     result = accumulate(first,last,0); //调用C++标准库算法
// }

int main() //主线程
{
    long int result1,result2,result3,result4,result5;
    vector<int> largeArrays;
    for(int i=0;i<100000000;i++)
    {
        if(i%2==0)
            largeArrays.push_back(i);
        else
            largeArrays.push_back(-1*i);
    }
    // thread first(GetSumT,largeArrays.begin(),
    //     largeArrays.begin()+20000000,std::ref(result1)); //子线程1
        thread first(GetSumT,largeArrays.begin(),
        largeArrays.begin()+200,std::ref(result1)); //子线程1
        cout<<"result1:"<<result1<<endl;
    thread second(GetSumT,largeArrays.begin()+2000,
        largeArrays.begin()+4000,std::ref(result2)); //子线程2
        cout<<"result2:"<<result2<<endl;
    thread third(GetSumT,largeArrays.begin()+40000000,
        largeArrays.begin()+60000000,std::ref(result3)); //子线程3
        cout<<"result3:"<<result3<<endl;
    thread fouth(GetSumT,largeArrays.begin()+60000000,
        largeArrays.begin()+80000000,std::ref(result4)); //子线程4
        cout<<"result4:"<<result4<<endl;
    thread fifth(GetSumT,largeArrays.begin()+80000000,
        largeArrays.end(),std::ref(result5)); //子线程5
 
    first.join(); //主线程要等待子线程执行完毕
    second.join();
    third.join();
    fouth.join();
    fifth.join();
    cout<<"final result2:"<<result2<<endl;
    cout<<"final  result3:"<<result3<<endl;
    cout<<"final  result4:"<<result4<<endl;
    int resultSum = result1+result2+result3+result4+result5; //汇总各个子线程的结果
 
    return 0;
}
