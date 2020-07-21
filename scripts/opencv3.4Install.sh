#!/bin/bash
#
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA Corporation and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA Corporation is strictly prohibited.
#
# TX2 CUDA_ARCH_BIN=6.2 
#

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <Install Folder>"
    exit
fi
folder="$1"
user="nvidia"
passwd="nvidia"

echo "** Install requirement"
sudo apt-get install -y build-essential cmake git libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev
sudo apt-get install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
sudo apt-get install -y python2.7-dev
sudo apt-get install -y python3.5-dev
sudo apt-get install -y python-dev python-numpy 
sudo apt-get install -y python3-dev python3-numpy
sudo apt-get install -y libtbb2 libtbb-dev libjpeg-dev libpng-dev libtiff-dev libjasper-dev libdc1394-22-dev
sudo apt-get install -y libv4l-dev v4l-utils qv4l2 v4l2ucp
sudo apt-get install -y curl
sudo apt-get update

echo "** Download opencv-3.4.0"
cd $folder
curl -L https://github.com/opencv/opencv/archive/3.4.0.zip -o opencv-3.4.0.zip
unzip opencv-3.4.0.zip 
cd opencv-3.4.0/

echo "** Building... CUDA9.0"
mkdir release
cd release/
cmake -D WITH_CUDA=ON -D CUDA_ARCH_BIN="6.2" -D CUDA_ARCH_PTX="" -D WITH_GSTREAMER=ON -D WITH_LIBV4L=ON -D BUILD_TESTS=OFF -D BUILD_PERF_TESTS=OFF -D BUILD_EXAMPLES=OFF -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=/usr/local ..

make -j8
sudo make install
##config opencv
cd /etc/ld.so.conf.d/
   sudo nano opencv.conf
      /usr/local/lib
sudo ldconfig -v

echo "** Install opencv-3.4.0 successfully"
echo "** Bye :)"

