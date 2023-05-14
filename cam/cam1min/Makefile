#目标（要生成的文件名）
TARGET     := cam1min
#编译器的选择（在Linux中其实可以忽略，因为cc指向的本来就是gcc）   
CC	   := g++  
#编译的参数
#CFLAG	   := -g -Wall  
CFLAGS = -g -Wall 
#OPENCV=`pkg-config --cflags opencv --libs opencv` 
OPENCV=`pkg-config --cflags opencv4 --libs ` 
#OPENCV=`pkg-config --cflags --libs opencv`
LIBS = $(OPENCV)

#编译包含的头文件所在目录 

# OPENCV3---->OPENCV4 库文件有所不同 201907
#INCLUDES   := -I /usr/local/include/opencv4/opencv2/ 
#CI/CD DEPLOY .CHANGE INCLUDES, doesn't have /local dir!! 202004
INCLUDES   := -I /usr/include/opencv4/
 #所有用到的源文件，注意：非当前目录的要+上详细地址
SRCS    =  cam1min.cpp
#把源文件SRCS字符串的后缀.c改为.o 
#OBJS    = $(SRCS:.c=.o)  
default:
	$(CC)   $(CFLAGS) $(INCLUDES) $(SRCS)  -o $(TARGET) $(LIBS)
#清空除源文件外的所有生成文件 
#clean:     rm -rf $(basename $(TARGET)) $(SRCS:.c=.o)
clean:  
	rm -rf $(TARGET) 
