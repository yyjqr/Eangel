#ifndef BASE64UTIL_H
#define BASE64UTIL_H

/*
 * @file    Base64Util.h
 * @brief   Package the base64 encode and decode as a util class.
 * @author
 * @date    2021.08.02
 */

#include <iostream>

using namespace std;

class Base64Util
{
public:

    // Encode data function
    static string Encode(const unsigned char *byte_data, int byte_len)
    {
        string base64_data;
        const unsigned char *curr;
        curr = byte_data;

        while(byte_len > 2)
        {
            base64_data += base64_char_set[curr[0] >> 2];
            base64_data += base64_char_set[((curr[0] & 0x03) << 4) + (curr[1] >> 4)];
            base64_data += base64_char_set[((curr[1] & 0x0f) << 2) + (curr[2] >> 6)];
            base64_data += base64_char_set[curr[2] & 0x3f];

            curr += 3;
            byte_len -= 3;
        }
        if(byte_len > 0)
        {
            base64_data += base64_char_set[curr[0] >> 2];
            if(byte_len % 3 == 1)
            {
                base64_data += base64_char_set[(curr[0] & 0x03) << 4];
                base64_data += "==";
            }
            else if(byte_len % 3 == 2)
            {
                base64_data += base64_char_set[((curr[0] & 0x03) << 4) + (curr[1] >> 4)];
                base64_data += base64_char_set[(curr[1] & 0x0f) << 2];
                base64_data += "=";
            }
        }

        return base64_data;
    }

    // Decode data function
    static string Decode(const char *base64_data, int byte_len)
    {
        // decode table
        char ch_1 = (char)-1;
        char ch_2 = (char)-2;
        const char DecodeTable[] =
        {
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_1, ch_1, ch_2, ch_2, ch_1, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_1, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, 62,   ch_2, ch_2, ch_2, 63,
            52,   53,   54,   55,   56,   57,   58,   59,   60,   61,   ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, 0,    1,    2,    3,    4,    5,    6,    7,    8,    9,    10,   11,   12,   13,   14,
            15,   16,   17,   18,   19,   20,   21,   22,   23,   24,   25,   ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, 26,   27,   28,   29,   30,   31,   32,   33,   34,   35,   36,   37,   38,   39,   40,
            41,   42,   43,   44,   45,   46,   47,   48,   49,   50,   51,   ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
            ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2, ch_2,
        };

        string decode_data;
        const char *curr = base64_data;

        char tmp_ch;
        int i = 0;
        int bin = 0;
        while((tmp_ch = *curr++) != '\0' && byte_len-- > 0)
        {
            if(tmp_ch == base64_pad)
            {
                if(*curr != '=' && (i % 4) == 1)
                {
                    return NULL;
                }
                continue;
            }

            tmp_ch = DecodeTable[tmp_ch];

            if(tmp_ch < 0)
            {
                continue;
            }
            switch(i % 4)
            {
            case 0:
                bin = tmp_ch << 2;
                break;
            case 1:
                bin |= tmp_ch >> 4;
                decode_data += bin;
                bin = (tmp_ch & 0x0f) << 4;
                break;
            case 2:
                bin |= tmp_ch >> 2;
                decode_data += bin;
                bin = (tmp_ch & 0x03) << 6;
                break;
            case 3:
                bin |= tmp_ch;
                decode_data += bin;
                break;
            }

            ++i;
        }

        return decode_data;
    }

private:

    // base64 Encode and Decode using the base char set
    static const string base64_char_set;

    static const char base64_pad = '=';
};

const string Base64Util::base64_char_set = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

#endif // BASE64UTIL_H
