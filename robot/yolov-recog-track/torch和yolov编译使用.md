<!--
 * @Descripttion:
 * @Author: Jack
 * @Date: 2025-08-30 21:10:14
 * @LastEditors: Jack
 * @LastEditTime: 2025-08-31 22:17:53
-->
torch和yolov编译使用
## python 版本和路径
系统路径和conda路径的python

http://pypi.jetson-ai-lab.io/

 1886  apt install python3.10-venv
 1887  sudo apt install python3.10-venv
 1888  python3 -m venv yolov5_env
 1889  pip install numpy==2.2.5 pandas==1.3.5
 1890  python3 -c "import numpy; print('NumPy Version:', numpy.__version__)"
 1891  python3 -c "import pandas; print('Pandas Version:', pandas.__version__)"
 1892  python -c "import pandas; print(pandas.__version__)"
 1893  python3 -m venv yolov5_env
 1894  source yolov5_env/bin/activate
 1895  pip install --upgrade pip
 1896  python3 -c "import pandas; print('Pandas Version:', pandas.__version__)"
 1897  pip install numpy==1.23.5 pandas==1.3.5
 1898  history |grep export
 1899  python3  export.py --weights yolov5s.pt --img 640 --batch 1 --dynamic --simplify --include onnx
 1900  exit
 1901  cd ~/Documents/yolov5
 1902  python3  export.py --weights yolov5s.pt --img 640 --batch 1 --dynamic --simplify --include onnx
 1903  python3
 1904  history |grep export
 1905  sudo vim ~/.bashrc
 1906  python3  export.py --weights yolov5s.pt --img 640 --batch 1 --dynamic --simplify --include onnx
 1907  source ~/.bashrc
 1908  python3  export.py --weights yolov5s.pt --img 640 --batch 1 --dynamic --simplify --include onnx
 1909  python -c "import numpy; print(numpy.__version__)"
 1910  python -c "import pandas; print(pandas.__version__)"
 1911  python -c "import numpy; print(numpy.__version__)"
 1912  python -c "import pandas; print(pandas.__version__)"
 1913  pip install pandas=2.1.2
 1914  pip install pandas==2.1.2
 1915  python -c "import numpy; print(numpy.__version__)"
 1916  python -c "import pandas; print(pandas.__version__)"
 1917  python3  export.py --weights yolov5s.pt --img 640 --batch 1 --dynamic --simplify --include onnx
 1918  ls -alh
 1919  python3 -m torch.distributed.run --weights yolov5s.pt


## torch版本
JP6.2的torch下载安装

https://pytorch.org/get-started/locally/
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu126

## 尝试安装JP6.1对应的版本 09.14
(yolov5envPY3.10) nvidia@ubuntu:~/Documents/yolov5$ pip3 install --no-cache https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl
Looking in indexes: https://pypi.org/simple, https://pypi.ngc.nvidia.com
Collecting torch==2.5.0a0+872d972e41.nv24.8.17622132
  Downloading https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl (807.0 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 807.0/807.0 MB 8.8 MB/s  0:01:26
Requirement already satisfied: filelock in /home/nvidia/archiconda3/envs/yolov5envPY3.10/lib/python3.10/site-packages (from torch==2.5.0a0+872d972e41.nv24.8.17622132) (3.18.0)
Requirement already satisfied: typing-extensions>=4.8.0 in /home/nvidia/archiconda3/envs/yolov5envPY3.10/lib/python3.10/site-packages (from torch==2.5.0a0+872d972e41.nv24.8.17622132) (4.13.0)
Requirement already satisfied: networkx in /home/nvidia/archiconda3/envs/yolov5envPY3.10/lib/python3.10/site-packages (from torch==2.5.0a0+872d972e41.nv24.8.17622132) (3.4.2)
Requirement already satisfied: jinja2 in /home/nvidia/archiconda3/envs/yolov5envPY3.10/lib/python3.10/site-packages (from torch==2.5.0a0+872d972e41.nv24.8.17622132) (3.1.6)
Requirement already satisfied: fsspec in /home/nvidia/archiconda3/envs/yolov5envPY3.10/lib/python3.10/site-packages (from torch==2.5.0a0+872d972e41.nv24.8.17622132) (2025.3.0)
Requirement already satisfied: sympy==1.13.1 in /home/nvidia/.local/lib/python3.10/site-packages (from torch==2.5.0a0+872d972e41.nv24.8.17622132) (1.13.1)
Requirement already satisfied: mpmath<1.4,>=1.1.0 in /home/nvidia/.local/lib/python3.10/site-packages (from sympy==1.13.1->torch==2.5.0a0+872d972e41.nv24.8.17622132) (1.3.0)
Requirement already satisfied: MarkupSafe>=2.0 in /home/nvidia/archiconda3/envs/yolov5envPY3.10/lib/python3.10/site-packages (from jinja2->torch==2.5.0a0+872d972e41.nv24.8.17622132) (3.0.2)
Installing collected packages: torch
  Attempting uninstall: torch
    Found existing installation: torch 2.6.0+cu126
    Uninstalling torch-2.6.0+cu126:
      Successfully uninstalled torch-2.6.0+cu126
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
torchvision 0.21.0 requires torch==2.6.0, but you have torch 2.5.0a0+872d972e41.nv24.8 which is incompatible.
Successfully installed torch-2.5.0


##yolov5.cpp tensort修改
cat /usr/include/aarch64-linux-gnu/NvInfer.h |grep "ResizeMode"
 1398  cat /usr/include/aarch64-linux-gnu/NvInfer.h |grep "interpolationMode"

## conda里import tensorRT报错
 系统已经通过 apt 安装了 TensorRT 的 Python 绑定（python3-libnvinfer 等）

但是你 在 Conda 虚拟环境 yolov5envPY3.10 里，Python 并没有看到系统的 site‑packages，所以 import tensorrt 会报 ModuleNotFoundError

也就是说 Python 绑定是装好了的，但 路径没对上虚拟环境。

🔑 解决方法
方法 A：在虚拟环境里让 Python 能看到系统包

编辑 yolov5envPY3.10 的 site-packages 搜索路径：

# 查看 Conda 虚拟环境的 site-packages
python -m site


通常会在类似：

/home/nvidia/archiconda3/envs/yolov5envPY3.10/lib/python3.10/site-packages


把系统的 tensorrt 路径加进去（假设 TensorRT 安装在 /usr/lib/python3.10/dist-packages）：

export PYTHONPATH=$PYTHONPATH:/usr/lib/python3.10/dist-packages


然后再试：

python -c "import tensorrt as trt; print(trt.__version__)"


(yolov5envPY3.10) nvidia@ubuntu:~/Documents/yolov5$ ls -alh /usr/lib/python3.10/dist-packages
total 60K
drwxr-xr-x 10 root root 4.0K  3月 29 20:21 .
drwxr-xr-x 34 root root  20K  8月 31 20:40 ..
drwxr-xr-x  7 root root 4.0K  3月 29 20:21 cv2
drwxr-xr-x  6 root root 4.0K  4月 20  2023 numpy
drwxr-xr-x  2 root root 4.0K  3月 29 20:20 tensorrt
drwxr-xr-x  2 root root 4.0K  3月 29 20:20 tensorrt-10.3.0.dist-info
drwxr-xr-x  2 root root 4.0K  3月 29 20:20 tensorrt_dispatch
drwxr-xr-x  2 root root 4.0K  3月 29 20:20 tensorrt_dispatch-10.3.0.dist-info
drwxr-xr-x  2 root root 4.0K  3月 29 20:20 tensorrt_lean
drwxr-xr-x  2 root root 4.0K  3月 29 20:20 tensorrt_lean-10.3.0.dist-info
