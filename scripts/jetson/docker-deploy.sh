#!/bin/bash
installDocker()
{
   ##安装最新的docker：

$ curl -fsSL get.docker.com -o get-docker.sh
$ sudo sh get-docker.sh
}
copyFiles()
{
  mkdir -p ~/docker_libs/usr/lib/aarch64-linux-gnu
  mkdir -p ~/docker_libs/usr/include
  mkdir -p ~/docker_libs/opt/ros

  rsync  /usr/lib/aarch64-linux-gnu/*so*   /home/nvidia/docker_libs/usr/lib/aarch64-linux-gnu -rv
 #cp -r /usr/lib/aarch64-linux-gnu/libopencv* ~/docker_libs/usr/lib/aarch64-linux-gnu/
  cp /usr/lib/aarch64-linux-gnu/tegra/ /home/nvidia/docker_libs/usr/lib/aarch64-linux-gnu/ -rv
 cp -r /usr/include/opencv* ~/docker_libs/usr/include/
 rsync -l /usr/lib/lib*so*   /home/nvidia/docker_libs/usr/lib/ -v
 cp -r /opt/ros/$ROS_DISTRO/lib ~/docker_libs/opt/ros/$ROS_DISTRO/
}

filesToDocker()
{
sudo docker pull nvcr.io/nvidia/l4t-cuda:11.4.19-runtime
# 定义你想查找的镜像名称
IMAGE_NAME="nvcr.io/nvidia/l4t-cuda:11.4.19-runtime"

# 获取使用该镜像的容器ID
CONTAINER_ID=$(sudo docker ps -qf "ancestor=$IMAGE_NAME")

if [ -z "$CONTAINER_ID" ]; then
    echo "没有找到使用镜像 $IMAGE_NAME 的运行中容器"
else
    echo "使用 $IMAGE_NAME 的容器ID: $CONTAINER_ID"
fi

 sudo docker cp    /var/GoMEC  -L  $CONTAINER_ID:/var/
 sudo docker cp  ~/docker_libs/usr/lib/  -L $CONTAINER_ID:/var/GoMEC/lib/systemLib/
 sudo docker cp  ~/docker_libs/usr/lib/aarch64-linux-gnu/  -L $CONTAINER_ID:/var/GoMEC/lib/systemLib/
 sudo docker cp  ~/docker_libs/usr/bin/command_link  -L $CONTAINER_ID:/usr/bin/

}  
 
  ## vim mec-libs-docker.md5
case "$1" in
        #MEC出厂初始化
        "0")
                echo "Get order '0':deploy ALL mec app to docker..."
                copyFiles
				filesToDocker
        ;;
        #安装雷达算法和自启服务
        "1")
                echo "Get order '1': upgrade GXX_LIDAR*.tar.gz"
                copyFiles
        ;;
        "2")
	        echo "Get order '2': files:libs and mec-app To Docker "
		filesToDocker	
		;;
	"3")	
                #sudo docker run -it --rm --net=host --runtime nvidia -e DISPLAY=$DISPLAY -v /tmp/.X11-unix/:/tmp/.X11-unix nvcr.io/nvidia/l4t-cuda:11.4.19-runtime
                sudo docker run -it  --net=host --runtime nvidia -e DISPLAY=$DISPLAY -v /tmp/.X11-unix/:/tmp/.X11-unix nvcr.io/nvidia/l4t-cuda:11.4.19-runtime-mec
		;;
esac

exit 0
