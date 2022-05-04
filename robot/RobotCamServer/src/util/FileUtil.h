#ifndef FILEUTIL_H
#define FILEUTIL_H

/*
 * @file    FileUtil.h
 * @brief   Implement some file function.
 * @author
 * @date
 */

#include <iostream>
#include <fstream>
#include <unistd.h>
#include <sys/stat.h>

using namespace std;

class FileUtil
{
public:

    static bool createFolder(string folder_path)
    {
        if(access(folder_path.c_str(), 0) == -1)
        {
            // no this folder, should create it
            if(mkdir(folder_path.c_str(), S_IRWXU | S_IRWXG | S_IRWXO) == 0)
            {
                cout << "Create dir " << folder_path << " successful!" << endl;
            }
            else
            {
                cout << "Create dir " << folder_path << " FAILED !!" << endl;
                return false;
            }

//            if(chmod(folder_path,0777)){
//                cout <<"change mode ok!"<<endl;

//            }
//            else{
//                 cout <<"change failed or make sure the file path!"<<endl;
//                 return false;
//            }
        }

        return true;
    }

    static bool existFile(string file_path)
    {
        ifstream conf;
        conf.open(file_path);
        if(!conf)
        {
            conf.close();
            return false;
        }
        conf.close();
        return true;
    }
};

#endif // FILEUTIL_H
