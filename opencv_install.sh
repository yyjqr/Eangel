sudo mkdir /home/opencv
sudo apt-get install -y wget build-essential cmake libgtk2.0-dev pkg-config \
libavcodec-dev libavformat-dev libswscale-dev python-dev \
python-numpy  libtbb2 libtbb-dev libjpeg-dev

sudo apt-get install -y libtiff-dev libjasper-dev libdc1394-22-dev
libopenexr-dev

cd /home/opencv
wget -O opencv4.1.0.zip https://github.com/opencv/opencv/archive/4.1.0.zip
pwd
sudo unzip opencv4.1.0.zip
sudo mkdir -p /home/opencv/opencv4.1.0/build
wget -O opencv_contrib-4.1.0.tar.gz https://github.com/opencv/opencv_contrib/archive/4.1.0.tar.gz
tar -zxf opencv_contrib-4.1.0.tar.gz
cd /home/opencv/opencv4.1.0/build
#以下cmake命令可选[不支持xfeatures2d]
cmake  -DBUILD_opencv_xfeatures2d=OFF  ..
#带gpu支持[不可用]
cmake  -DWITH_CUDA=ON -DBUILD_opencv_xfeatures2d=OFF  ..
#带pkgconfig[不可用]
cmake  -DOPENCV_GENERATE_PKGCONFIG=ON  ..
#带xfeatures2d全带[可用]
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/home/opencv4.1.0/ \
-DOPENCV_EXTRA_MODULES_PATH=/home/opencv/opencv_contrib-4.1.0/modules/ -DWITH_CUDA=ON  \
-DOPENCV_GENERATE_PKGCONFIG=ON -DBUILD_opencv_xfeatures2d=ON OPENCV_ENABLE_NONFREE=NO \
-DWITH_TBB = ON -DBUILD_TBB = ON ..
make -j4
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

#pkg-config --modversion opencv4
# 4.0.1
#pkg-config --libs opencv4
#pkg-config --cflags opencv4

#原文链接：https://blog.csdn.net/weixin_43299649/article/details/93995444
