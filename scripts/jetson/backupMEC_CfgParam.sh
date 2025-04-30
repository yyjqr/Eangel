#/bin/bash
# A very useful backup script
# 2023.06

#创建备份文件存放目录
Dir=/tmp/cfg
sudo mkdir $Dir

curTime=`date '+%Y-%m-%d_%H%M%S'`
echo $curTime

#备份没激光雷达的MEC配置文件
backupBasicCfg()
{
	#备份ire.ini文件
        sudo cp /var/GoMEC/cfg_0/emec/ini/ire.ini $Dir

        #备份rtspIpcDev.ini文件
        sudo cp /mnt/rtspIpcDev.ini $Dir

        #备份rayVideo文件
        sudo cp /var/GoMEC/cfg_0/emec/ini/rayVideo.ini $Dir

        #备份devConfig.ini文件
        sudo cp /var/GoMEC/app/GoEMEC/devConfig.ini $Dir

        #备份License.dat文件
        sudo cp /var/GoMEC/app/GoEMEC/License.dat $Dir
       
	sudo cp /etc/ntp.conf  $Dir
}


backupWithoutLidar()
{
	#备份ire.ini文件
	sudo cp /var/GoMEC/cfg_0/emec/ini/ire.ini $Dir

	#备份rtspIpcDev.ini文件
	sudo cp /mnt/rtspIpcDev.ini $Dir

	#备份rayVideo文件
	sudo cp /var/GoMEC/cfg_0/emec/ini/rayVideo.ini $Dir

	#备份devConfig.ini文件
	sudo cp /var/GoMEC/app/GoEMEC/devConfig.ini $Dir

	#备份License.dat文件
	sudo cp /var/GoMEC/app/GoEMEC/License.dat $Dir

	#备份configure、model、run_configure文件夹
	sudo cp -r /var/GoMEC/app/GoEMEC/configure/ $Dir/configure
	sudo cp -r /var/GoMEC/app/GoEMEC/model/ $Dir/model
	sudo cp -r /var/GoMEC/app/GoEMEC/run_configure/ $Dir/run_configure

	#备份数据库和config.toml文件
	sudo cp /home/nvidia/mec/mec.sqlite /home/nvidia/mec/config.toml $Dir
}

backupWithLidar()
{
	#激光雷达配置文件
	sudo cp -r /home/nvidia/release/config/ $Dir/release_config
	sudo cp -r /home/nvidia/rs_post_fusion_ros_src_gaoxinxing/src/config $Dir/src_config
}

  getconfig()
  {
    SECTION=$1

    CONFILE=$2
    #ENDPRINT="crossId"
    ENDPRINT=$3
    #echo "CONFILE:" $CONFILE
    for loop in `echo $ENDPRINT|tr '\t' ' '`
    do
         #这里面的的SECTION的变量需要先用双引号，再用单引号，我想可以这样理解，
         #单引号标示是awk里面的常量，因为$为正则表达式的特殊字符，双引号，标示取变量的值
         #{gsub(/[[:blank:]]*/,"",$2)去除值两边的空格内容

         #echo $loop
         #RESULT=`awk -F '=' '/\['"$SECTION"'\]/{a=1}a==1&&$1~/'"$loop"'/{gsub(/[[:blank:]]*/,"",$2);printf("%s\t",$2) ;exit}' $CONFILE`
	 ## 去掉空格，去掉\t
         RESULT=`awk -F '=' '/\['"$SECTION"'\]/{a=1}a==1&&$1~/'"$loop"'/{gsub(/ /,"",$2);printf("%s",$2) ;exit}' $CONFILE`
	 echo $RESULT
    done
  }
   getRoadNameFromConfig()
  {
    SECTION=$1

    CONFILE=$2
    ENDPRINT=$3
    echo "CONFILE:" $CONFILE
    for loop in `echo $ENDPRINT|tr '\t' ' '`
    do
         ## 去掉空格，去掉\t
         MECName=`awk -F '=' '/\['"$SECTION"'\]/{a=1}a==1&&$1~/'"$loop"'/{gsub(/ /,"",$2);printf("%s",$2) ;exit}' $CONFILE`
	 echo $MECName
    done
  }

  ## 找出配置路段编号和MEC编号
  #getconfig gxx /var/GoMEC/app/GoEMEC/devConfig.ini  crossId
  getconfig V2XOBJ_0  /var/GoMEC/cfg_0/emec/ini/ire.ini  V2XOBJ_INTERSECTIONID
  RoadID=$RESULT
  getRoadNameFromConfig devAttr /var/GoMEC/app/GoEMEC/devConfig.ini  name
  RoadName=$MECName
  echo $RoadID$RoadName


case "$1" in
        #MEC备份MEC基本配置
	"0")
	        backupBasicCfg
	        ;;
        "1")
                backupWithoutLidar
                ;;
        "2")
                backupWithoutLidar
                backupWithLidar
                ;;
        *)
                echo "unsupport this order to back config!"
                ;;
esac

#打包cfg文件夹

sudo tar -zcvf mec-appCfg$1-$RoadName-$RoadID-$curTime.tar.gz /tmp/cfg
## 删除备份文件，避免将多余的文件备份，或上次备份的算法参数文件！！
sudo rm -rf $Dir
exit 0
