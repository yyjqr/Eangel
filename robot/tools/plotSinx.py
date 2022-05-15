import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
 
def update_points(num):
    point_ani.set_data(x[num], y[num])
    return point_ani,
 
x = np.linspace(0, 2*np.pi, 100)
y = np.sin(x)
 
fig = plt.figure(tight_layout=True)
plt.plot(x,y)
point_ani, = plt.plot(x[0], y[0], "ro")
plt.grid(ls="--")

ani = animation.FuncAnimation(fig, update_points, frames = np.arange(0, 100), interval=100, blit=True)
 
plt.show()

#————————————————
#版权声明：本文为CSDN博主「张海军2013」的原创文章，遵循CC 4.0 BY-SA版权协议，转载请附上原文出处链接及本声明。
#原文链接：https://blog.csdn.net/zhanghaijun2013/article/details/108308960
