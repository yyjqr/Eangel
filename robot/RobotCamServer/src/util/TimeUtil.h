#ifndef TIMEUTIL_H
#define TIMEUTIL_H

/*
 * @file    TimeUtil.h
 * @brief   Implement some time change function
 *          and package as a util class.
 * @author  zhuang.sr  yj
 * @date    2019.08.05
 */

#include <iostream>
#include <sys/time.h>

using namespace std;

#include "stringProcess.h"

class TimeUtil
{
public:

    /*
     * get current year, month and day
     * @return yyyyMMdd
     */
    static string getYearMonthDay()
    {
        time_t t_t;
        time(&t_t);
        tm *t = gmtime(&t_t);
        string month = stringProcess::to_String(t->tm_mon + 1);
        month = (month.length() == 1) ? ("0" + month) : month;
        string mday = stringProcess::to_String(t->tm_mday);
        mday = (mday.length() == 1) ? ("0" + mday) : mday;
        return stringProcess::to_String(t->tm_year + 1900) + month + mday;
    }

    /*
     * get current hour, minute and second
     * @return HHmmss
     */
    static string getHourMinuteSecond()
    {
        time_t t_t;
        time(&t_t);
        tm *t = gmtime(&t_t);
        string hour = stringProcess::to_String(t->tm_hour);
        hour = (hour.length() == 1) ? ("0" + hour) : hour;
        string minute = stringProcess::to_String(t->tm_min);
        minute = (minute.length() == 1) ? ("0" + minute) : minute;
        string second = stringProcess::to_String(t->tm_sec);
        second = (second.length() == 1) ? ("0" + second) : second;
        return hour + minute + second;
    }

    /*
     * get log format time (using Beijing Time, not UTC time)
     * @return yyyy-MM-dd HH:mm:ss
     */
    static string getLogTime()
    {
        time_t t_t;
        time(&t_t);
        t_t += 8 * 60 * 60;
        tm *t = gmtime(&t_t);
        string month = stringProcess::to_String(t->tm_mon + 1);
        month = (month.length() == 1) ? ("0" + month) : month;
        string mday = stringProcess::to_String(t->tm_mday);
        mday = (mday.length() == 1) ? ("0" + mday) : mday;
        string hour = stringProcess::to_String(t->tm_hour);
        hour = (hour.length() == 1) ? ("0" + hour) : hour;
        string minute = stringProcess::to_String(t->tm_min);
        minute = (minute.length() == 1) ? ("0" + minute) : minute;
        string second = stringProcess::to_String(t->tm_sec);
        second = (second.length() == 1) ? ("0" + second) : second;

//        return stringProcess::to_String(t->tm_year + 1900) + "-" + month + "-" + mday + " " + hour + ":" + minute + ":" + second;
        return  month + "-" + mday + " " + hour + ":" + minute + ":" + second;
    }

    /*
     * get current milisecond
     * @ return 0000000000.000
     */
    static string getCurrMiliSec()
    {
        struct timeval curr_time;
        gettimeofday(&curr_time, NULL);

        long sec = curr_time.tv_sec;
        int mili_sec = curr_time.tv_usec / 1000;
        string m_sec = stringProcess::to_String(mili_sec);
        if(m_sec.length() == 1)
        {
            m_sec = "00" + m_sec;
        }
        else if(m_sec.length() == 2)
        {
            m_sec = "0" + m_sec;
        }
        return stringProcess::to_String(sec) + "." + m_sec;
    }

    /*
     * get next full five minute time, where mm % 5 == 0, and ss == "00"
     * @param HHmmss
     * @return HHmmss
     */
    static string nextFullFiveMinTime(string curr_time)
    {
        string curr_min = curr_time.substr(2, 2);
        int min = stringProcess::Strtoint(curr_min.c_str());
        int i = min / 5;
        min = 5 * (i + 1);
        string next_min;
        if(min == 60)
        {
            next_min = "00";
        }
        else
        {
            next_min = stringProcess::to_String(min);
            next_min = (next_min.length() == 1) ? ("0" + next_min) : next_min;
        }

        string next_hour = curr_time.substr(0, 2);
        if(min == 60)
        {
            int hour = stringProcess::Strtoint(next_hour.c_str());
            hour++;
            if(hour == 24)
            {
                next_hour = "00";
            }
            else
            {
                next_hour = stringProcess::to_String(hour);
                next_hour = (next_hour.length() == 1) ? ("0" + next_hour) : next_hour;
            }
        }

        return next_hour + next_min + "00";
    }

    /*
     * compare time which format is HHmmss
     * @param time1 HHmmss
     * @param time2 HHmmss
     * @return true | time1 < time2
     *        false | time1 >= time2
     */
    static bool compareTimeHms(string hms_1, string hms_2)
    {
        string hour_1 = hms_1.substr(0, 2);
        string hour_2 = hms_2.substr(0, 2);
        int h_1 = stringProcess::Strtoint(hour_1.c_str());
        int h_2 = stringProcess::Strtoint(hour_2.c_str());
        if(h_2 == 0)
        {
            if(h_1 == 23)
            {
                return true;
            }
            else if(h_1 != 0)
            {
                return false;
            }
        }
        if(h_1 == h_2)
        {
            string min_1 = hms_1.substr(2, 2);
            string min_2 = hms_2.substr(2, 2);
            int m_1 = stringProcess::Strtoint(min_1.c_str());
            int m_2 = stringProcess::Strtoint(min_2.c_str());
            return m_1 < m_2;
        }
        else
        {
            int h_diff = h_1 - h_2;
            if(h_diff > 1 || h_diff < -1)
            {
                return false;
            }
            return h_1 < h_2;
        }
    }


};

#endif // TIMEUTIL_H
