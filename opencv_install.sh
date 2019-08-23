mkdir /home/opencv4.1.0
apt-get install -y wget
apt-get install -y build-essential
apt-get install -y git
apt-get install -y libgtk2.0-dev
apt-get install -y pkg-config
apt-get install -y libavcodec-dev
apt-get install -y libavformat-dev
apt-get install -y libswscale-dev
apt-get install -y python-dev
apt-get install -y python-numpy
apt-get install -y libtbb2
apt-get install -y libtbb-dev
apt-get install -y libjpeg-dev
apt-get install -y libpng-dev
apt-get install -y libtiff-dev
apt-get install -y libjasper-dev
apt-get install -y libdc1394-22-dev

cd /home/opencv
wget -o opencv4.1.0.zip https://github.com/opencv/opencv/archive/4.1.0.zip
unzip opencv4.1.0.zip
mkdir /home/opencv/opencv4.1.0/build
wget -o opencv_contrib-4.1.0.tar.gz https://github.com/opencv/opencv_contrib/archive/4.1.0.tar.gz
tar -zxf opencv_contrib-4.1.0.tar.gz
cd /home/opencv/opencv4.1.0/build
#以下cmake命令可选[不支持xfeatures2d]
cmake  -DBUILD_opencv_xfeatures2d=OFF  ..
#带gpu支持[不可用]
cmake  -DWITH_CUDA=ON -DBUILD_opencv_xfeatures2d=OFF  ..
#带pkgconfig[不可用]
cmake  -DOPENCV_GENERATE_PKGCONFIG=ON  ..
#带xfeatures2d全带[可用]
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/home/opencv4.1.0/ -DOPENCV_EXTRA_MODULES_PATH=/home/opencv/opencv_contrib-4.1.0/modules/ -DWITH_CUDA=ON  -DOPENCV_GENERATE_PKGCONFIG=ON -DBUILD_opencv_xfeatures2d=ON OPENCV_ENABLE_NONFREE=NO -DWITH_TBB = ON -DBUILD_TBB = ON ..
make -j4
make install

echo "/home/opencv/opencv4.1.0/lib" >/etc/ld.so.conf.d/opencv.conf
ldconfig


nano ~/.bashrc
在文件最后边输入
export PKG_CONFIG_PATH=/home/opencv4.1.0/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=/home/opencv4.1.0/lib:$LD_LIBRARY_PATH
ctrl+o 回车保存  ctrl+x 退出
source ~/.bashrc


echo"opencv版本及库信息："

pkg-config --modversion opencv4
# 4.0.1
pkg-config --libs opencv4
pkg-config --cflags opencv4
 ———————————————— 
版权声明：本文为CSDN博主「CMDjava123」的原创文章，遵循CC 4.0 by-sa版权协议，转载请附上原文出处链接及本声明。
原文链接：https://blog.csdn.net/weixin_43299649/article/details/93995444
