/*
 * Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */
 
#include "logging.h"
#include <stdio.h>
#include <string.h>

#include <iostream>
#include <QDateTime>

// set default logging options
Log::Level Log::mLevel = Log::DEFAULT;
//FILE* Log::mFile = stdout;
FILE* Log::mFile = stdout;
std::string Log::mFilename = "stdout";




Log::Log()
{

}

Log::~Log()
{
    fflush(GetFile());
    fclose(GetFile());
}

// SetFile
void Log::SetFile( FILE* file )
{
	if( !file || mFile == file )
		return;

	mFile = file;

	if( mFile == stdout )
		mFilename = "stdout";
	else if( mFile == stderr )
		mFilename = "stderr";
}


// SetFilename
void Log::SetFile( const char* filename )
{
	if( !filename )
        return ;

    if( stricmp(filename, "stdout") == 0 )
		SetFile(stdout);

    else if( stricmp(filename, "stderr") == 0 )
		SetFile(stderr);
	else
	{
        if( stricmp(filename, mFilename.c_str()) == 0 )
            return ;

       FILE* file = fopen(filename, "w+");
       
		if( file != NULL )  
		{
			SetFile(file);
			mFilename = filename;
            //return file;   //ADD  JACK
            std::cout<<"filename:"<<filename<<std::endl;//<<" save file* "<<file
            LogInfo("filename is %s \n",filename);

            //fprintf(Log::GetFile(), "filename is %s \n",filename);

		}
		else
		{
			LogError("failed to open '%s' for logging\n", filename);
            return ;
		}

	}	
}

// LevelToStr
const char* Log::LevelToStr( Log::Level level )
{
	switch(level)
	{
		case SILENT:	return "silent";
        case ERROR:    return "error";
		case WARNING:  return "warning";
		case SUCCESS:  return "success";
        case INFO:	   return "info";
		case VERBOSE:	return "verbose";
        case DEBUGING:	return "debug";
	}

	return "default";
}


// LevelFromStr
Log::Level Log::LevelFromStr( const char* str )
{
	if( !str )
		return DEFAULT;

    for( int n=0; n <= DEBUGING; n++ )
	{
		const Level level = (Level)n;

        if( stricmp(str, LevelToStr(level)) == 0 )
			return level;
	}

    if( stricmp(str, "disable") == 0 || stricmp(str, "disabled") == 0 || stricmp(str, "none") == 0 )
		return SILENT;

	return DEFAULT;
}

void Log::writeLogHead(){
//    string log_head=TimeUtil::getLogTime();
    QDateTime datetime;
    QString timestr=datetime.currentDateTime().toString("HH:mm:ss.zzz"); //fff为毫秒部分  202108
    std::string log_head=timestr.toStdString();
//    std::string log_head;10
    fprintf(Log::GetFile(), "%s:", log_head.c_str());
}



	
