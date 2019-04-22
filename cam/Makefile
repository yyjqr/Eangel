#g++ -std=c++11  -I/usr/include/opencv/ -I/usr/include/opencv2/  cam18minHD201807V1.4.cpp 
#   -o camFS18m  `pkg-config --cflags opencv --libs opencv` 
#目标（要生成的文件名）
TARGET     := camFS18m
#编译器的选择（在Linux中其实可以忽略，因为cc指向的本来就是gcc）   
CC	   := g++  
#编译的参数
#CFLAG	   := -g -Wall  
CFLAGS = -g -Wall 
OPENCV=`pkg-config --cflags opencv --libs opencv` 
LIBS = $(OPENCV)

#编译包含的头文件所在目录 
INCLUDES   := -I /usr/include/opencv/  -I /usr/include/opencv2/  
 #所有用到的源文件，注意：非当前目录的要+上详细地址
SRCS    =  cam_flexSave18minHD2019V1.8.cpp
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
