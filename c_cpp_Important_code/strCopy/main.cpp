#include <iostream>

using namespace std;


typedef union {
    short i;
    int k[5];
    char c;
} Mat;

typedef struct {
    int i;
    Mat j;
    double k;
}Like;


class A{
    char* a;
    public:
    A():a(0){}
    A(char*aa) {//把aa所指字符串拷贝到a所指向的存储空间
        cout<<"strlen(aa):"<<strlen(aa)<<endl;
//        cout<<"*aa:"<<*aa<<endl;
        printf("aa str :%s \n",aa);
    a=new char(strlen(aa)+1);
    strcpy_s(a,strlen(aa)+1,aa);
    }
    ~A(){delete [] a;}
};


void getmem(char* p)
{
    p=(char*)malloc(100);
    strcpy(p,"hello world");
    printf("test *p:%s\n",p);
}

int main()
{
    char *str=NULL;
    getmem(str);
    //测试内存分配，与字符串拷贝 0316
    printf("%s\n",str);
    free(str);
    cout << "Hello World!" << endl;
    printf("sizeof(Like)+sizeof(Mat):%d \n",sizeof(Like)+sizeof(Mat));
//    char names[]="dog is a lovely animal";
    char names[23]="dog is a lovely animal";
    char* ptr_str;
    ptr_str=names;

//    ptr_str=(char*) malloc(10*sizeof(char));
//    memcpy(ptr_str,names,sizeof(names));
    A tmp_str(ptr_str);
    return 0;
}
