
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)
##pi 3b+
##servoPin=11
##pi4  only gpio1 pwm  202205
servoPin=12
GPIO.setup(servoPin, GPIO.OUT)
pwm=GPIO.PWM(servoPin,50)
pwm.start(7)
#for i in range(0,20):
#while True:
def rotate(cycle):
	#desiredPosition=int(input("Input servo duty cycle(0-100): "))
	#DC=9./170.*(desiredPosition)+1
	#realCycle=9/170*(cycle)+1
	#realCycle=9/180*(cycle)
	realCycle=cycle
	#DC=int(desiredPosition)+1
	print("cycle:%f" %realCycle)
	pwm.ChangeDutyCycle(realCycle)	
for i in range(2,13):
   for j in range(0,10):
      num=i+j/10
      if (num<12.5 and num>2.0):
          rotate(i+j/10)
          time.sleep(2)
      elif (num>12.5):
          rotate(11)
          time.sleep(5)
          rotate(10)
          time.sleep(5)
          rotate(9)
          time.sleep(8)
          rotate(8)
          time.sleep(8)
          rotate(7.5)
          time.sleep(10)
      else:
          rotate(7.5)
      print(num)
      print("\n")
   #rotate(80)


pwm.stop()
GPIO.cleanup()
