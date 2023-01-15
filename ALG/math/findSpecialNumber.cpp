#include <stdio.h>
#include <stdint.h>
#include <math.h>
#include <limits.h>  //INT_MAX
#include <unistd.h>
#include <iostream>
#include <fstream>
using namespace std;



int main()
{
  long int a;
   int baseNumber=2;
  unsigned long int MAX_Number=pow(2,32)-1;
   const double  kValue_gap=1e-8;
 int count=0; 
 bool b_not_a_special_number=false;
  printf("max int number:%llu\n",ULLONG_MAX);
  string filePath="./";
  string fileName="numberSP2023.txt";
  ofstream  fin;
  fin.open(fileName);
  if(!fin.is_open()){
   cerr<<"open file failed!\n";
  }

for(unsigned long int i=3; i<ULLONG_MAX;i+=2)
 {
   //if(i%2!=0 )
  { 
   if (i<32)
   {
    a=pow(baseNumber,i)-baseNumber;
    if(a%i ==0){
   count++;
   cout<<">>>>find a special number:"<<i<<"***index"<<count<<endl<<endl;
    }
   }
  else if( (i%3 !=0) &&  (i%5 !=0) && (i%7 !=0) ){
      if(i%11 !=0 && i%17 !=0 && i%13 !=0 && i%19 !=0 && i%31 != 0)
     {
    double number_sqrt_value = sqrt(i*1.0);
    int  number_sqrt =sqrt(i);
    if(number_sqrt_value-number_sqrt <kValue_gap){
       //printf("number_sqrt_value is %f\n",number_sqrt_value);
       //cout<<i<<",Not a special number ,sqrt value:"<<number_sqrt_value<<endl;
       continue;
    }
    if(i>1000){
    /* if(i%23 !=0 && i%31 !=0 && i%47 !=0 && i%59 !=0)
     {
       printf("number_sqrt_value is %f\n",number_sqrt_value);
       continue;
     } */
 //从3到根号x,每个做除，看是否有解来判断
     for(int  j=3; j <number_sqrt;j+=2)
       {
         if(i%j==0){
          b_not_a_special_number=true;
          break;
           }
         else{
          b_not_a_special_number=false;  // need keep flag false!
          }
       }
    }
    if(!b_not_a_special_number){
    count++;  
    cout<<"maybe a special  number:"<<i<<"***index"<<count<<endl;
    fin<<"count:"<<count<<"number:"<<i<<endl; 
    if(count%500==0){
    sleep(1);
     }
    } 
     }
    }
  }
  
 }

}
