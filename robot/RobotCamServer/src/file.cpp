#include "util/FileUtil.h"
#include "file.h"   //def class
#include <string.h>   //memset

#include <sys/statfs.h>
#include <string>
#include <iostream>
#include <limits.h>

string FILESAVE::createDIR(){
    string ROOT_DIR="/mnt/";
     time_t timep,t;
     tm* local;
     char buf[64];
     memset(buf,'\0',sizeof(buf));
     t=time(&timep);
     local = localtime(&t); //转为本地时间
     strftime(buf, 64, "%Y%m%d_%H_%M",local);//"%Y-%m-%d_%H:%M:%S"
     string folder_path=ROOT_DIR+buf;
     folder_path+='/'; // need '/' for dir !!
//     cout<<"create save folder"<<folder_path<<endl;  //0209
     if( FileUtil::createFolder(folder_path)==false)
     {
         return "";
     }
     return folder_path;
}


// interactive to create DIR  根据给定的或选择的存储路径和道路信息创建文件夹
string FILESAVE::createDIR(string Dir){
    string folder_path=Dir;
     folder_path+='/'; // need '/' for dir !!
//     cout<<"create save folder"<<folder_path<<endl;
     if( FileUtil::createFolder(folder_path)==false)
     {
         return "";
     }
     return folder_path;
}

string FILESAVE::createChildrenDIR(string childrenDir){

     string root_path,folder_path;
     root_path=createDIR();
     folder_path+=root_path+childrenDir;   //add children Dir
     cout<<"create save folder"<<folder_path<<endl;

     if(FileUtil::createFolder(folder_path)==false)
     {
         return ""; //创建失败，返回空
     }

     return folder_path;
}

string FILESAVE::createChildrenDIR(string parent_path,string childrenDir){

     string folder_path;
     folder_path=parent_path+childrenDir;   //add children Dir
     cout<<"create save Final folder"<<folder_path<<endl;

     if(FileUtil::createFolder(folder_path)==false)
     {
//        qDebug()<<"\n create save Final folder failed!!";
         return ""; //创建失败，返回空
     }

     return folder_path;
}

string FILESAVE::get_cur_executeProgram_path()
{
    char *p                 = NULL;

    const int len           = 256;
    /// to keep the absolute path of executable's path
    char arr_tmp[len]       = {0};

    int n  = readlink("/proc/self/exe", arr_tmp, len);
    if (NULL != (p = strrchr(arr_tmp,'/')))
        *p = '\0';
    else
    {
        return std::string("");
    }
    cout<<"get exec dir absolute path:"<<string(arr_tmp)<<endl;
    return std::string(arr_tmp);
}
