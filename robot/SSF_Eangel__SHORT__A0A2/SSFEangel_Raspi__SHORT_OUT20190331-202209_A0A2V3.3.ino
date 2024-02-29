
//******************************************************************
//2012-2018 知识产权所有Eangel car  Jack YANG
//超声波和树莓派与uno通过usb的通信之间通过serial可能有冲突20161104做了修改
//******************************************************************
#include <NewPing.h>
#include <Servo.h>
int TIME = 667;     //20-->40(1126)--->改变定义-->200时间变长了，转弯没问题了20161228!!!--->267(20170101)
//#define ANGLE 120
int PWA2A = 11, PWA2B = 3, PWA0A = 6, PWA0B = 5;
int PWA1B = 10;
int DIR_CLK = 4;
int DIR_EN = 7; //Enable
int DIR_SER = 8;
int DIR_LATCH = 12; //新l293d 8次移位 四个电机转动
int  photovc = 2;
int i, j;
float Left, Middle, Right, middle1, middle2;
unsigned int startANGLE = 30;
unsigned int stopANGLE = 120; //90-->120 20180128 范围更大，避免扫描不到

float lefttemp, righttemp;  //0404 2016
int val1, val2;


float L = 45, M = 55, R = 45;
int  turnValue = 40; //1017modify  20-->30--->20   (11/17转弯已经变得更灵活了--->40   速度更快了11/19)-->50(1210)---->30(0510)
#define TRIGGER_PIN  A0  // Arduino pin tied to trigger pin on the ultrasonic sensor.
#define ECHO_PIN     A2  // Arduino pin tied to echo pin on the ultrasonic sensor.
#define MAX_DISTANCE 200 // Maximum distance we want to ping for (in centimeters). Maximum sensor distance is rated at 400-500cm.
int analogPin_Left = A4;
int analogPin_Right = A5;
unsigned int count = 0;
const int kMaxDetectDistance=60; //cm
NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE); // NewPing setup of pins and maximum distance.


Servo myservo;  // create servo object to control a servo
// a maximum of eight servo objects can be created

int pos = 0;    // variable to store the servo position
unsigned char CMD;
int countL = 0; //20180422
unsigned long runTime,runTime1,runTime2;  //20180625  ROBOT RUN TIME


void setup()
{
  pinMode(PWA2A, OUTPUT);
  pinMode(DIR_CLK, OUTPUT);
  pinMode( DIR_EN, OUTPUT);
  pinMode(DIR_SER, OUTPUT);
  pinMode(DIR_LATCH, OUTPUT);
  // pinMode(photovc,OUTPUT);
  myservo.attach(10);
  pinMode(10, OUTPUT);
  //pinMode(photoPin, INPUT);
  pinMode (A5, INPUT);
  Serial.begin(115200); // Open serial monitor at 115200 baud to see ping results.
  runTime = millis();
  delay(50);   //150-->50(20161029)
}

void loop()
{
        int val = 0;
        char command;
        float vol;
       
        digitalWrite(PWA2A, HIGH);
        digitalWrite(PWA2B, HIGH);
        digitalWrite(PWA0A, HIGH);
        digitalWrite(PWA0B, HIGH);
        digitalWrite(DIR_EN, LOW);  //不要注释掉，这样通常情况在最快速度运行！！！！！！！！！！20180303
       
        goForward();
        
        for (pos = startANGLE; pos <= stopANGLE; pos += 10) // goes from 0 degrees to 180 degrees                    1---->3      04042016 ---->6(20161117扫描更快，范围更大)
        { // in steps of 1 degree
          myservo.write(pos);              // tell servo to go to position in variable 'pos'
          //delay(10);                        // Wait 50ms between pings (about 20 pings/sec). 29ms should be the shortest delay between pings.
          unsigned int uS = sonar.ping(); // Send ping, get ping time in microseconds (μS).
          // Serial.print("Ping: ");
          delay(30);                               // Wait 50ms between pings (about 20 pings/sec). 29ms should be the shortest delay between pings.    20---->50---->40 （20180625）//1210修改，避免超声波传感器处理不过来或没检测到变化------>30 后续还有延时，1231
          Middle = sonar.convert_cm(uS);
      
          /* uS = sonar.ping(); // Send ping, get ping time in microseconds (μS).
            // Serial.print("Ping: ");
              delay(5);                              //1210修改，避免超声波传感器处理不过来或没检测到变化--->0304 add
            middle2 = sonar.convert_cm(uS);
            Middle = (middle1 + middle2) / 2;*/
            // print pos and distance test
          if (countL < 20)
          { Serial.print("Pos: ");
            Serial.print( pos);
            Serial.print( "||");
            Serial.print( Middle); // Convert ping time to distance and print result (0 = outside set distance range, no ping echo)
            Serial.println("cm");
            countL += 1;
          }
           Serial.print("distance,cm:"); 
          Serial.println( Middle);  //test
          if (Middle < kMaxDetectDistance && Middle > 0)
          {
                if (Middle < 40)             // >35改为<35,这样不会一直满足减速条件，也避免在室内，减速几次就转弯 20181209
                {
                  carSlowdown();
                  count += 1;
          
                }  //先进行减速判断
                if (Middle < 15 && Middle >5) //避免1,2cm干扰值    25--->18  直行时，有无缘故地后退现象多次出现20181202 ----->把判断条件变得更小，避免无故后退  20181231
                {
                  TIME = 1500; //ADD 20180226---->test 1000  0303 --->2000  0625 ---->1500 20181202
                  turnBack(TIME);
                  count += 1;
                   runTime1 = millis();
                   runTime1-=runTime;
                   runTime1/=1000;
                   Serial.print("Robot running time is ");
                   Serial.print(runTime1);
                   Serial.println("s");
                  break;        //55-->40(20161005)--->30(20161117)   60---->40(20170508)------------->去掉等于0的情形20171221（可能无限远，另外超声波供电有问题，导致测距过小而跳出循环，从而转角范围小！！！！！！！！！！！！！！）
                }
                if (count == 3)   //==2-------->==3 20181202 避免直线运行时，无缘无故转弯
                {
                  TIME = 400; //20180303ADD     800-----》400  避免转弯过大1209
                  turnLeft(TIME);
                  count = 0; //每次初始化为零
                  break;
                }
      
          }
        }
      
        /*****************************************************YAOKONGMOSHI20161031*/
        if ( Serial.available() )      // if data is available to read
        {
          command = Serial.read();     // read it and store it in 'val'
          switch (command)
          {
            case 'L':
              TIME = 200; //40--->60(20170106)---->70(0510)
              turnLeft(TIME);
              break;       //20161104ADD!!!
            case 'R': TIME = 100;
              turnRight(TIME);
              break;
            case 'B': TIME = 100; //80---->100(20180407)
              turnBack(TIME);
              break;
            case 'P': carStop();
              break;
            case 'F': goForward();   //QIANJIN NO OK!!
              break;
            case 'S': carSlowdown();   //QIANJIN NO OK!!
              break;
            default: 
               runTime2 = millis();
               runTime2-=runTime;
               Serial.print("Robot running time (Serial) is ");
               Serial.print(runTime2/1000);
               Serial.println("s");
              Serial.println("WHAT DO U WANT TO DO ?");   //
              break;
          }
        }
      
    
        unsigned int ANGLE = stopANGLE - startANGLE; //20180128
      
        /**********运行时再测量一次障碍物***********************/ //20180303
        unsigned int uSc = sonar.ping(); // Send ping, get ping time in microseconds (μS).
        delay(30);                              //1210修改，避免超声波传感器处理不过来或没检测到变化
        Middle = sonar.convert_cm(uSc);
      
        if (pos <= (startANGLE + ANGLE /5) && pos >= startANGLE && Middle < turnValue && Middle > 10) //转弯值不能过小min  2-->5   Middle>0----->Middle>10(20170509)
        {
          int timeL=300;
          Serial.print("Turn left for ");
          Serial.print( timeL);
          Serial.print( "ms"   );
          Serial.println( pos);
          turnLeft(timeL);
        }
      
        /*||(Left<30&&Right>40)*/
        if (pos <= stopANGLE && pos >= (startANGLE + 2 * ANGLE / 3) && Middle < turnValue && Middle > 10) //YOUZHUAN   20160404修改转弯条件  M大于一定值转弯，避免总是满足转弯条件，却转不动
        {
          Serial.print("Turn right   ");
          Serial.println( pos);
          turnRight(TIME);
        }
        /********************超声波偶尔测出值为1，实际远大于1………………………………………………………………/20170508*/
        if (Middle < 25 && Middle > 1 ) //HOUTUI 有修改  距离更小再后退  ||(val1>550&&val2>550)  0619大轮车修改为25   不能写为>=0(1029过远可能为0)   光电 20180427
        {
          int backTIME = 1200; //1000---->800避免倒退距离过长！！！！
          turnBack(backTIME);
          Serial.println("后退");
          Serial.print( Middle);
          //myservo.write(60);    //避免距离过小时，一直前进后退，让超声波旋转一个角度，从而使之左右转，退出这种状态
          carStop();                  //3.18晚增加   与库函数stop冲突
         

        }
      
      
        //旋转的方向和响应时间还有问题
        for (; pos >= startANGLE; pos -= 10) // goes from 180 degrees to 0 degrees  -1  --->  -2   20160404   >=20---->=0(20161006)
        {
          myservo.write(pos);              // tell servo to go to position in variable 'pos'
          delay(6);                       // waits 15ms for the servo to reach the position
        }

}





//信号触发！！！！
void clockFun()
{
  digitalWrite(DIR_CLK, LOW);
  delay(1);
  digitalWrite(DIR_CLK, HIGH);
  delay(1);//1
}

void goForward()
{
  CMD = 0xE4; //对应的二进制11100100  unsigned char CMD  20170915
  analogWrite(DIR_EN, 0); //20161016   0--->10(1020)
  Serial.println("CAR Eangel GO go");
  if (Middle < 60)
  {
    analogWrite(DIR_EN, 30);
  }  //20161220
  digitalWrite(DIR_LATCH, LOW);
  for (i = 0; i < 9; i++)
  {
    digitalWrite(DIR_SER, LOW);
    clockFun();
  }   //QING 0
  // Serial.println("CAR Eangel GO go000000*******************");
  for (i = 0; i < 8; i++)
  {

    if (CMD & 0x01 == 0x01)
    {
      digitalWrite(DIR_SER, HIGH);
      //Serial.print(CMD);
      //printf("%c","T");
      //Serial.println("CAR Eangel GO go1111111_________________________");//调试用0915
    }
    else
    {
      digitalWrite(DIR_SER, LOW);
      //printf("%c", "F");
      //Serial.println("F");
    }
    CMD >>= 1;
    clockFun();
  }


  digitalWrite(DIR_LATCH, HIGH);
  delay(30);  //YOU  XIU  GAI   0314     30--->50(20161118)--->30(1119)
}     //add 20161116 Android  Raspi

void turnBack(int TIME)
{
  CMD = 0x1B; //00011011
  digitalWrite(DIR_LATCH, LOW);
  analogWrite(DIR_EN, 50);
  digitalWrite(10, LOW);
  Serial.print("Turn Back,cm:");
  Serial.println( Middle); // Convert ping time to distance and print result (0 = outside set distance range, no ping echo)
//   Serial.println("cm ");
  for (i = 0; i < 9; i++)
  {
    digitalWrite(DIR_SER, LOW);
    clockFun();
  }  //QING 0
  //Serial.println(CMD);  //ASCII形式的命令--->bin二进制的形式  202209
  for (i = 0; i < 8; i++)
  {

      if (CMD & 0x01 == 0x01)
      {
        digitalWrite(DIR_SER, HIGH);
        Serial.print(1);   //得到一串0001100......
      }
      else
      {
        digitalWrite(DIR_SER, LOW);
        Serial.print(0);
      }
  
      CMD >>= 1;
      clockFun();
  }
  Serial.println("=====");

  digitalWrite(DIR_LATCH, HIGH);
  digitalWrite(photovc, HIGH);
  //TIME = 500;
  delay(TIME);     // 200------>250--->150(20161016防止倒退时间过长)--->100(faster1120)---->80(201061210)
  /*   if(digitalRead(photoPin)==LOW)
      {break;}    */
  //  }
}

void turnLeft(int TIME)
{
  CMD = 0xA9; //对应的二进制10101001
  analogWrite(DIR_EN, 20);    //2----->20--->40(三节电池，动力强劲，转弯需慢)
  if (Middle < 40)
  {
    analogWrite(DIR_EN, 60);
  }
  digitalWrite(DIR_LATCH, LOW);
  digitalWrite(10, LOW);
  Serial.print("CAR Eangel Turn Left");
  for (i = 0; i < 9; i++)
  {
    digitalWrite(DIR_SER, LOW);
    clockFun();
  }
  //QING 0

  for (i = 0; i < 8; i++)
  {
    if (CMD & 0x01 == 0x01)
    {
      digitalWrite(DIR_SER, HIGH);
      //Serial.println("Left1");
    }
    else
    {
      digitalWrite(DIR_SER, LOW);
      //Serial.println("Left0");
    }
    CMD >>= 1;
    clockFun();
  }
  digitalWrite(DIR_LATCH, HIGH);
  for (int i = 0; i < 1; i++)
  {
    unsigned int uS = sonar.ping(); // Send ping, get ping time in microseconds (μS).
    Middle = sonar.convert_cm(uS);
    Serial.println( Middle); // Convert ping time to distance and print result (0 = outside set distance range, no ping echo)
    if (Middle < 10 && Middle > 0) break; //55-->40(20161005)
    delay(TIME);            //2500---->1500    --->2500  0406  --->3500-->1500(1018避免小车过重，转向不明显)-->1000(1029)    把delay放在最开始————————>放在最后后面
  }   //add20161019
  Serial.println("=====");
  /* if(digitalRead(photoPin==LOW))
    {
     delay(1);
    }
    else
    {delay(5000);} */
}

void turnRight(int TIME)
{
  CMD = 0x56; //对应的二进制01010110
  analogWrite(DIR_EN, 20); //20161017   (100过大)
  if (Middle < 40)
  {
    analogWrite(DIR_EN, 50);
  }
  digitalWrite(DIR_LATCH, LOW);
  digitalWrite(10, LOW);
  Serial.print("CAR Eangel Turn RIGHT");
  for (i = 0; i < 9; i++)
  {
    digitalWrite(DIR_SER, LOW);
    clockFun();
  }
  //QING 0

  for (i = 0; i < 8; i++)
  {
    if (CMD & 0x01 == 0x01)
    {
      digitalWrite(DIR_SER, HIGH);
      Serial.print("1");
    }
    else
    {
      digitalWrite(DIR_SER, LOW);
      Serial.print("0");
    }
    CMD >>= 1;
    clockFun();
  }
  digitalWrite(DIR_LATCH, HIGH);
  // delay(3500);     // 0406   2500-->3500(1018避免小车过重，转向不明显)
  for (int i = 0; i < 1; i++)
  {
    unsigned int uS = sonar.ping(); // Send ping, get ping time in microseconds (μS).
    Middle = sonar.convert_cm(uS);
    Serial.print( Middle); // Convert ping time to distance and print result (0 = outside set distance range, no ping echo)
    if (Middle < 10 && Middle > 0) break; //55-->40(20161005)
    delay(TIME);            //2500---->1500    --->2500  0406  --->3500-->1500(1018避免小车过重，转向不明显)-->1000(1029)--->500(转弯已经变得更灵活了)
  }
  /* if(digitalRead(photoPin)==LOW)
    {
     delay(1);
    }
    else
    {delay(5000);} */
}

void carStop()
{
  analogWrite(DIR_EN, 255);   //1016add
  digitalWrite(DIR_LATCH, LOW);
  digitalWrite(10, LOW);
  for (i = 0; i < 9; i++)
  {
    digitalWrite(DIR_SER, LOW);
    clockFun();
  }
  Serial.println("CAR STOP");
  delay(3000);
}

void carSlowdown()
{
  digitalWrite(PWA2A, HIGH);
  digitalWrite(PWA2B, HIGH);
  digitalWrite(PWA0A, HIGH);
  digitalWrite(PWA0B, HIGH);
  analogWrite(DIR_EN, 120);   //20161120  80---》100  20180216   //120---》150  20181202
  Serial.println(" SLOW DOWN SLOW DOWN...");
  delay(500);  //2000------>500  0313
}






  
