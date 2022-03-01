#ifndef COMMONSTRINGPROCESS_H
#define COMMONSTRINGPROCESS_H

#include <stdio.h>
#include <iostream>
#include <vector>

using namespace  std;

/** @brief GNSS data process
 *  @author jack.yang
 *  @date 2020.07
 */

#define max 100
enum ret
{
    kvalid = 0,
    kinvalid
};
// 是否有非法输入的标记
static int status = kvalid;

class stringProcess{
public:

    static string to_String(int n)
    {
        int m = n;
        char s[max];
        char ss[max];
        int i = 0, j = 0;
        if(n == 0)
        {
            return "0";
        }
        if(n < 0)
        {
            // 处理负数
            m = 0 - m;
            j = 1;
            ss[0] = '-';
        }
        while(m > 0)
        {
            s[i++] = m % 10 + '0';
            m /= 10;
        }
        s[i] = '\0';
        i = i - 1;
        while(i >= 0)
        {
            ss[j++] = s[i--];
        }
        ss[j] = '\0';
        return ss;
    }

    static long long Strtointcode(const char * digit, bool minus)
    {
        long long num = 0;
        while(*digit != '\0')
        {
            if(*digit >= '0' && *digit <= '9')
            {
                int flag = minus ? -1 : 1;
                num = num * 10 + flag * (*digit - '0');
                if((!minus&&num > 0x7FFFFFFF) || (minus&&num < (signed int)0x80000000))
                {
                    num = 0;
                    break;
                }
                digit++;
            }
            else
            {
                num = 0;
                break;
            }
        }
        if(*digit == '\0')
        {
            status = kvalid;
        }
        return num;
    }

    static int Strtoint(const char * str)
    {
        status = kinvalid;
        long long num = 0;
        if(str != NULL && *str != '\0')
        {
            bool minus = false;
            if(*str == '+')
            {
                str++;
            }
            else if(*str == '-')
            {
                str++;
                minus = true;
            }
            if(*str != '\0')
            {
                num = Strtointcode(str, minus);
            }

        }
        return (int)num;
    }

    static void SplitString(const string& s, vector<string>& v, const string& c)
    {
        string::size_type pos1, pos2;
        pos2 = s.find(c);
        pos1 = 0;
        while(string::npos != pos2)
        {
            v.push_back(s.substr(pos1, pos2-pos1));

            pos1 = pos2 + c.size();
            pos2 = s.find(c, pos1);
        }
        if(pos1 != s.length())
        {
            v.push_back(s.substr(pos1));
        }
    }

    static string& replaceStr(string& str, const string& old_value, const string& new_value)
    {
        for(string::size_type pos(0); pos != string::npos; pos += new_value.length())
        {
            if((pos = str.find(old_value, pos)) != string::npos)
            {
                str.replace(pos,old_value.length(),new_value);
            }
            else
            {
                break;
            }
        }
        return str;
    }

    static bool strIsNum(string str)
    {
        for(int i = 0; i < str.size(); i++)
        {
            int tmp = (int)str[i];
            if(tmp >= 48 && tmp <= 57)
            {
                continue;
            }
            else
            {
                return false;
            }
        }
        return true;
    }

    static bool strIsFloat(string str)
    {
        if(str.size() == 0)
        {
            //return true;
            return false;
        }
        if(str[0] == '-')
        {
            if(str.size() == 1)
            {
                return false;
            }
            str = str.substr(1);
        }
        vector<string> numSplit;
        SplitString(str, numSplit, ".");
        if(numSplit.size() == 2)
        {
            if(strIsNum(numSplit[0]) && strIsNum(numSplit[1]))
            {
                return true;
            }
        }

        return false;
    }


    static string filterSerialData(string serial_data)
    {
        vector<string> nmea_type;
        serial_data = replaceStr(serial_data, "\r\n", "\n");
        serial_data = replaceStr(serial_data, "\r", "\n");
        //SplitString(serial_data, nmea_type, "\n");
        SplitString(serial_data, nmea_type, ",");  // split with "," ,to get the NMEA data segment ,LNG ,LAT
        if(nmea_type.size() == 0)
        {
            return serial_data;
        }
        // serial_data is not empty
        return nmea_type[0];
    }


    static string filterSerialData_end(string serial_data)
    {
        vector<string> nmea_type;
        serial_data = replaceStr(serial_data, "\n\n", "\n");
        serial_data = replaceStr(serial_data, "\r", "\n");

            return serial_data;

    }



};

#endif // COMMONSTRINGPROCESS_H
