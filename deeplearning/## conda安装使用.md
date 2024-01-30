<!--
 * @Descripttion: 
 * @Author: Jack
 * @Date: 2024-01-24 21:43:31
 * @LastEditors: Jack
 * @LastEditTime: 2024-01-24 21:52:01
-->
## conda安装
ARM版本
https://blog.csdn.net/d597797974/article/details/119821585
官网链接
https://docs.conda.io/projects/miniconda/en/latest/

 1840  conda config --set auto_activate_base false
 1841  cd .conda
 1844  conda config --show channels
 1845  conda install -c conda-forge python
 1846  conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
 1847  conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
 1848  conda config --set show_channel_urls yes
 1850  conda env list
 1852  sudo conda create -n python39 python=3.9

 1891  conda update -n base -c defaults conda
 1927  conda create --name python39 python==3.9
 1935  conda create -n Python37 python=3.7
 1936  conda activate Python37
 1937  conda info --envs
  sudo chmod a+w .conda
 conda create -n Python39 python=3.9
  conda activate Python39


X86-64版本
bash Anaconda3-5.0.1-Linux-x86_64.sh
//此处的版本与下载的anaconda版本保持一致
https://blog.csdn.net/qq_53564294/article/details/120535377