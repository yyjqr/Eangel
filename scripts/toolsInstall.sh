sudo apt-get install qt5-default qtcreator -y
sudo apt install qtmultimedia5-dev
#工具
sudo apt install nano tree scrot -y
sudo apt install python-pip
sudo apt install python3-pip
sudo pip install numpy
# 英伟达工具 jtop
 sudo -H pip3 install -U jetson-stats
# CUDA LIB路径配置
nano ~/.bashrc
export PATH=/usr/local/cuda-10.2/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-10.2/lib64:$LD_LIBRARY_PATH
## cmake 安装
 sudo ./cmake-3.19.6-Linux-aarch64.sh --prefix=/usr/local  --exclude-subdir
 
 ##libTorch 及相关依赖
 sudo pip3 install torch-1.8.0-cp36-cp36m-linux_aarch64.whl
 sudo apt-get install libopenblas-dev
 sudo apt install libopenmpi2
 
 ##json解析
 sudo apt  install libjsoncpp-dev
#安装硬件温度检测工具sensors
sudo apt install lm-sensors
#sudo apt install htop -y
