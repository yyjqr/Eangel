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


## X86-64版本  
bash Anaconda3-5.0.1-Linux-x86_64.sh
//此处的版本与下载的anaconda版本保持一致
https://blog.csdn.net/qq_53564294/article/details/120535377

## 解决conda jetson 创建环境的错误  01.13
 1962  sudo chmod a+w .conda
 1963  conda create -n Python39 python=3.9
 1964  conda activate Python39

## 解决解决英伟达Jetson平台使用Python时的出现“Illegal instruction(cpre dumped)”错误
需要使用 sudo 运行程序！！！
##
Command “python setup.py egg_info“ failed with error code 1 in /tmp/pip-build-*
升级pip 


(Python39) ai@ai-desktop:~/AI$  conda install -c conda-forge imgaug
Retrieving notices: ...working... done
Collecting package metadata (current_repodata.json): done
Solving environment: done


==> WARNING: A newer version of conda exists. <==
  current version: 23.3.1
  latest version: 23.11.0

Please update conda by running

    $ conda update -n base -c conda-forge conda

Or to minimize the number of packages updated during conda update use

     conda install conda=23.11.0



## Package Plan ##

  environment location: /home/ai/.conda/envs/Python39

  added / updated specs:
    - imgaug


The following packages will be downloaded:

    package                    |            build
    ---------------------------|-----------------
    blas-1.0                   |         openblas           8 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    blosc-1.21.3               |       h419075a_0          47 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    brotli-1.0.9               |       h01db608_4         396 KB  conda-forge
    brunsli-0.1                |       h01db608_0         196 KB  conda-forge
    c-ares-1.19.1              |       h998d150_0         123 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    ca-certificates-2023.11.17 |       hcefe29a_0         151 KB  conda-forge
    cairo-1.16.0               |       h537eab0_5         1.2 MB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    cfitsio-3.470              |       h152aa4d_7         1.3 MB  conda-forge
    charls-2.2.0               |       h7c1a80f_0         127 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    click-8.1.7                |unix_pyh707e725_0          82 KB  conda-forge
    cloudpickle-3.0.0          |     pyhd8ed1ab_0          24 KB  conda-forge
    contourpy-1.2.0            |   py39hb8fdbf2_0         250 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    cycler-0.12.1              |     pyhd8ed1ab_0          13 KB  conda-forge
    cyrus-sasl-2.1.28          |       h647bc0d_1         255 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    cytoolz-0.12.2             |   py39h998d150_0         393 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    dask-core-2024.1.0         |     pyhd8ed1ab_0         850 KB  conda-forge
    dbus-1.13.18               |       h821dc26_0         544 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
    eigen-3.4.0                |       hd62202e_0         1.2 MB  conda-forge
    expat-2.5.0                |       h419075a_0         151 KB  https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
