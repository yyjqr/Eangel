/*
 * @Descripttion:
 * @version:
 * @Author: Jack
 * @Date: 2022-05-26 11:22:05
 * @LastEditors: Jack
 * @LastEditTime: 2022-08-19 18:28:05
 */
#include <stdint.h>
#include <stdio.h>
#include <iostream>
#include <cmath>
// using namespace  std;
int main() {
  int a = (0x1 << 0);
  int b = (0x1 << 1);
  int c = (0x1 << 2);
  printf("a:%d,b:%d,c:%d\n", a, b, c);

  unsigned int stateOff = 0x00;
  unsigned int stateOn = 0x01;
  printf("a:%d,b:%d\n", stateOff, stateOn);
  printf("unsigned format a:%u,b:%u\n", stateOff, stateOn);


// double and int convert analysis

  double vel = -0.1000000;
  double reduce_ratio = 0.200000;
  int16_t speed = vel * 60 * 10 * 1.000000 /reduce_ratio;
  printf("vel:%f,speed:%d\n", vel, speed);
  printf("more precise, vel:%.10lf,reduce_ratio:%.10lf,speed:%d\n", vel, reduce_ratio, speed);

  double val = 5.000;
  int test_int = (int)val;
  printf("val:%f,test_int:%d\n", val, test_int);
  double neg_val = -299.02;
  int neg_int = (int)neg_val;
  printf("val:%f,test_int:%d\n", neg_val, neg_int);
  int16_t  neg_val_convert = floor(neg_val);
  int16_t neg_int16_small = std::round(neg_val);
  printf("after using math fun,neg_val_convert:%d, neg_int16:%d\n\n",neg_val_convert,  neg_int16_small);

  neg_val = -299.92;
  neg_int = (int)neg_val;
  int16_t neg_int16 = neg_val;
  printf("val:%f,test_int:%d,neg_int16:%d\n", neg_val, neg_int, neg_int16);
  neg_val_convert=floor(neg_val);
  neg_int16 = std::round(neg_val); //revise
  printf("after using math fun,neg_val_convert:%d, neg_int16:%d\n",neg_val_convert, neg_int16);


  
  return 0;
}
