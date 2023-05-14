#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include <limits.h> //INT_MAX
#include <unistd.h>
#include <iostream>
#include <fstream>
#include <thread>
#include <mutex>
using namespace std;

mutex mtx;
static int count = 0;

void  findSpecialNumber(int threadID, int beginNumber, int endNumber)
{
    long int a;
    int baseNumber = 2;
    const double kValue_gap = 1e-8;
    bool b_not_a_special_number = false;
    for (unsigned long long int i = beginNumber; i < endNumber; i += 2)
    {
        // if(i%2!=0 )
        {
            if (i < 32)
            {
                a = pow(baseNumber, i) - baseNumber;
                if (a % i == 0)
                {
                    count++;
                    cout << ">>>>find a special number:" << i << "***index" << count << endl
                         << endl;
                }
            }
            else if ((i % 3 != 0) && (i % 5 != 0) && (i % 7 != 0))
            {
                if (i % 11 != 0 && i % 17 != 0 && i % 13 != 0 && i % 19 != 0 && i % 31 != 0)
                {
                    double number_sqrt_value = sqrt(i * 1.0);
                    int number_sqrt = sqrt(i);
                    if (number_sqrt_value - number_sqrt < kValue_gap)
                    {
                        // printf("number_sqrt_value is %f\n",number_sqrt_value);
                        // cout<<i<<",Not a special number ,sqrt value:"<<number_sqrt_value<<endl;
                        continue;
                    }
                    if (i > 1000)
                    {
                        
                        // 从3到根号x,每个做除，看是否有解来判断
                        for (int j = 3; j < number_sqrt; j += 2)
                        {
                            if (i % j == 0)
                            {
                                b_not_a_special_number = true;
                                break;
                            }
                            else
                            {
                                b_not_a_special_number = false; // need keep flag false!
                            }
                        }
                    }
                    if (!b_not_a_special_number)
                    {
                        mtx.lock();
                        count++;
                        mtx.unlock();
                        cout << "maybe a special  number:" << i << "***index" << count << endl;
                        // fin << "count:" << count << "number:" << i << endl;
                        if (count % 500 == 0)
                        {
                            sleep(1);
                        }
                    }
                }
            }
        }
    }
    cout<< "thread id"<<threadID <<"finish..."<<endl;
   // return 0;
}

int main()
{
    int oneStepBaseNumber = 100000000;
    
    unsigned long int MAX_Number = pow(2, 32) - 1;
    
    
    
    printf("max int number:%llu\n", ULLONG_MAX);
    time_t timep, current_time;
    tm local;
    char buf[100] = {0};
    string filePath = "./";
    string fileName = "number-";
    current_time = time(&timep);
    localtime_r(&current_time, &local); // 转为本地时间   thread_safe!!
    printf("After assign ,test pointer local:0x%x\n", &local);
    strftime(buf, 64, "%Y-%m-%d_%H%M%S", &local);
    printf("time buf:%s\n", buf);
    fileName += buf;
    fileName += ".txt";

    ofstream numberStream;
    numberStream.open(fileName);
    if (!numberStream.is_open())
    {
        cerr << "open file failed!\n";
    }
    thread th[10];
    for(int i=0 ;i<10; i++){
    //    th[i] = thread(findSpecialNumber, 1+oneStepBaseNumber*i,oneStepBaseNumber*(i+1),numberStream);
    th[i] = thread(findSpecialNumber, i, 1+oneStepBaseNumber*i,oneStepBaseNumber*(i+1));
    }
    for(int i=0; i<10; i++){
        th[i].join();
    }
   
}
