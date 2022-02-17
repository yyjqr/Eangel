#include <iostream>

#include <vector>
#include <list>
using namespace std;

int main()
{


//    vector<int>tempVec;
//    tempVec.push_back(1);
//    tempVec.push_back(2);
//    tempVec.push_back(2);
//    tempVec.push_back(2);
//    tempVec.push_back(3);
//    tempVec.push_back(4);
//    tempVec.push_back(5);


//    for(auto itr=tempVec.begin();
//        itr!=tempVec.end();++itr){
//        if((*itr)==2){
//            itr=tempVec.erase(itr);
//            itr--;
//        }
//    }



//    for(auto itr=tempVec.begin();
//        itr!=tempVec.end();++itr){
//        cout<<*itr<<endl;

//    }


//    return 0;


    cout << "Hello World!" << endl;
    vector<int> a={1,2,2,2,3,5,7,8};
    int array[6]={1,3,5,7,9,11};
    int recordIndex[8]={0};
    list<int> A(array,array+5);
    int index=0;
    int len=a.size();
    int count=0;
    for (auto iter=a.begin();iter<a.end();iter++){


        if(*iter==2)
        {

            cout<<"find the num,delete it"<<endl;
            cout<<"idex:"<<index<<endl;
            recordIndex[count]=index;
            count++;

        }
        index++;
    }

    for(int i=0;i<count;i++){
        a.erase(a.begin()+recordIndex[i],a.begin()+recordIndex[i]+1);
        recordIndex[i+1]-=1;//删除一个后，元素位置就挪动了一个 0216
        cout<<"recordIndex[i]:"<<recordIndex[i]<<endl;
        cout<<"After delete,a.size():"<<a.size()<<endl;
    }
    for (auto iter=a.begin();iter<a.end();iter++){

        cout<<*iter<<endl;
    }



    //     int newValue[8];
    //     for(int i=0;i<a.size();i++){
    //         if(a.at(i)!=2){

    //             newValue[index]=a.at(i);
    //             index++;
    //         }
    //     }
    //     for(int i=0;i<8;i++){
    //         cout<<newValue[i]<<endl;
    //     }
    return 0;
}
