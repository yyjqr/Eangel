#!/bin/bash
 sudo apt-get update
 sudo apt-get upgrade
 sudo apt-get install cmake gfortran
 sudo apt-get install python3-dev python3-numpy
 sudo apt-get install libjpeg-dev libtiff-dev libgif-dev
 sudo apt-get install libgstreamer1.0-dev gstreamer1.0-gtk3
 sudo apt-get install libgstreamer-plugins-base1.0-dev gstreamer1.0-gl
 sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev
 sudo apt-get install libgtk2.0-dev libcanberra-gtk*
 sudo apt-get install libxvidcore-dev libx264-dev libgtk-3-dev
 sudo apt-get install libtbb2 libtbb-dev libdc1394-22-dev libv4l-dev
 sudo apt-get install libopenblas-dev libatlas-base-dev libblas-dev
 sudo apt-get install libjasper-dev liblapack-dev libhdf5-dev

 sudo apt-get install protobuf-compiler

echo "是否有opencv相关的代码?"
#git clone https://github.com/opencv/opencv.git
#git clone https://github.com/opencv/opencv_contrib.git

cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local  \
-DOPENCV_EXTRA_MODULES_PATH=/home/pi/opencv/opencv_contrib/modules/ \ 
-DWITH_CUDA=OFF  -DOPENCV_GENERATE_PKGCONFIG=ON -DBUILD_opencv_xfeatures2d=ON \
OPENCV_ENABLE_NONFREE=NO -DWITH_TBB=ON -DBUILD_TBB=ON
 -D BUILD_TESTS=OFF -D WITH_EIGEN=OFF -D WITH_GSTREAMER=ON -D WITH_V4L=ON -D WITH_LIBV4L=ON -D WITH_VTK=OFF 
-D WITH_QT=OFF -D OPENCV_ENABLE_NONFREE=ON -D INSTALL_C_EXAMPLES=OFF -D INSTALL_PYTHON_EXAMPLES=ON 
-D PYTHON3_PACKAGES_PATH=/usr/lib/python3/dist-packages -D OPENCV_GENERATE_PKGCONFIG=ON -D BUILD_EXAMPLES=OFF ..

##
make -j6
##
sudo make install

echo "/home/opencv/opencv4.1.0/lib" >/etc/ld.so.conf.d/opencv.conf
ldconfig


#nano ~/.bashrc
#在文件最后边输入
#export PKG_CONFIG_PATH=/home/opencv/lib/pkgconfig:$PKG_CONFIG_PATH
#export LD_LIBRARY_PATH=/home/opencv/lib:$LD_LIBRARY_PATH
#ctrl+o 回车保存  ctrl+x 退出
#source ~/.bashrc


echo "opencv版本及库信息："

pkg-config --modversion opencv4
# 4.0.1
