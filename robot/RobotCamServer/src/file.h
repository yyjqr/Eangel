#ifndef FILE_H
#define FILE_H

#include <string>
using namespace std;


class FILESAVE{
public :
    string createDIR();
    string createDIR(string Dir);
    string createChildrenDIR(string childrenDir);
    // 根据父路径，创建子路径
    string createChildrenDIR(string parent_path,string childrenDir);

    // 获取执行程序等的绝对路径
    string get_cur_executeProgram_path();
};
#endif // FILE_H
