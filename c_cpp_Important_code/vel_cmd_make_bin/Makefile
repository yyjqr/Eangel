#CC = aarch64-himix100-linux-gcc 
CC =gcc
# CC =g++





SRCS := $(wildcard produceStructBinaryData.c )

TARGET :=produceVelStBinaryData

libs:=-std=c11

default:

	$(CC)  -Wall -O2   $(SRCS) $(libs) -o $(TARGET)
