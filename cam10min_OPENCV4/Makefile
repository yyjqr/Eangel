#g++ -std=c++11  -I/usr/include/opencv/ -I/usr/include/opencv2/  cam18minHD201807V1.4.cpp 
#   -o camFS18m  `pkg-config --cflags opencv --libs opencv` 
#目标（要生成的文件名）
TARGET     := camFS10m_opt
#编译器的选择（在Linux中其实可以忽略，因为cc指向的本来就是gcc）   
CC	   := g++  
#编译的参数
#CFLAG	   := -g -Wall  
CFLAGS = -g -Wall 
# OPENCV3---->OPENCV4 库文件有所不同 201907
OPENCV=`pkg-config --cflags opencv --libs opencv` 
#OPENCV=`pkg-config --cflags --libs opencv`
LIBS = $(OPENCV)

#编译包含的头文件所在目录 
#INCLUDES   := -I /usr/local/include/opencv4/opencv2/  
INCLUDES   := -I /usr/include/opencv4/opencv2/
 #所有用到的源文件，注意：非当前目录的要+上详细地址
SRCS    =  cam_NewflexSave10minHD_opencv4.1_V2.2.cpp
#把源文件SRCS字符串的后缀.c改为.o 
#OBJS    = $(SRCS:.c=.o)  
#匹配所有的伪目标依赖，即执行目标myhello.o & ./common/abc.c & ./common/test/test.c 
#.PHONY:al)$(l     
#all为伪目标all:$(OBJS) 
    #当所有依赖目标都存在后，链接，即链接myhello.o & ./common/abc.c & ./commontest/test.c
   #$(CC) $(LDFLAG) -o $(TARGET) $^
#重定义隐藏规则，匹配上述目标：myhello.o & ./common/abc.c & ./common/test/test.c
#%.o:%.c 
default:
	$(CC)   $(CFLAGS) $(INCLUDES) $(SRCS)  -o $(TARGET) $(LIBS)
#清空除源文件外的所有生成文件 
#clean:     rm -rf $(basename $(TARGET)) $(SRCS:.c=.o)
clean:  
	rm -rf $(TARGET) 
