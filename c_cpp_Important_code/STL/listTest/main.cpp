//使用list对整数进行升序排序
//对double进行排序
#include <iostream>
#include  <vector>
#include <list>
using namespace std;

int main()
{
    cout << "Hello World!" << endl;
    vector<int> vec={1,3,5};
    list<int> Lis_int;
    cout<< vec.capacity()<<endl;

    int result[]={1,3,4,7,8,10,2,6,7,8,5,9,11};
    cout<<"sizeof(result):"<<sizeof(result)<<endl;
    for(int i=0;i<sizeof(result)/4;i++){
    Lis_int.push_back(result[i]);
    }

    Lis_int.sort();//直接对元素进行升序排序！！
    for(auto iter=Lis_int.begin();iter!=Lis_int.end();++iter)
    {
        cout<<"After sort,list output: "<<*iter<<endl;
    }

    list<double> lis_double;
    double rate_value[]={1.4,3.2, 3.14159, 4.0, 7.2, 8,10,2,6.0,7.88};
    cout<<"sizeof(result):"<<sizeof(rate_value)<<endl;
    lis_double.insert(lis_double.begin(),rate_value,rate_value+10);

    lis_double.sort();//直接对元素进行升序排序！！
    for(auto iter=lis_double.begin();iter!=lis_double.end();++iter)
    {
        cout<<"After sort,list output: "<<*iter<<endl;
    }
    return 0;
}
