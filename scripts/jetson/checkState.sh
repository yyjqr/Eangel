#!/bin/bash
# @author:yang.j
# @date:2024.08
your_gnss_check_command='timeout 5 gnss --start'

get_route_info='route -n'


#GET Current time
time=$(date "+%Y-%m-%d_%H%M%S")
echo $time
path="/mnt/sdcard/rcuLog"
logFile="$path/rcu$time.log"
echo "logFile:$logFile"
mkdir -p $path
# 假设的函数来检查各种状态
function check_gnss {
    # 这里添加检查GNSS状态的命令
    $your_gnss_check_command
    echo $your_gnss_check_commandy
    #echo "GNSS Status: $(${your_gnss_check_command})"
    echo $1+"GNSS Status: $($your_gnss_check_command)"
}
function check_v2x {
    # 检查V2X状态令
   
   output=$(cv2x-config --get-v2x-status|grep V2X)
   echo "get output:"+$output
   

   if echo $output |grep "rx_status=1";then
      echo "v2x ok"+$logFile
      echo $1:$output >> $logFile
   else
      echo "v2x error"
      echo $1:$output >> $logFile
   fi
   echo $1+"V2X Status: $your_v2x_check_command"
}

function get_Dev_state
{
    # 获取要监控的本地服务器 IP 地址
IP=`ifconfig | grep inet | grep -vE 'inet6|127.0.0.1' | awk -F ' ' '{print $2}'`
echo "IP 地址："$IP

# 获取 cpu 总核数
cpu_num=`grep -c "model name" /proc/cpuinfo`
echo "cpu 总核数："$cpu_num

# 1、获取 CPU 利用率
################################################
#us 用户空间占用 CPU 百分比
#sy 内核空间占用 CPU 百分比
#ni 用户进程空间内改变过优先级的进程占用 CPU 百分比
#id 空闲 CPU 百分比
#wa 等待输入输出的 CPU 时间百分比
#hi 硬件中断
#si 软件中断
#################################################
# 获取用户空间占用 CPU 百分比
cpu_user=`top -b -n 1 | grep Cpu | awk '{print $2}' | cut -f 1 -d "%"`
echo "用户空间占用 CPU 百分比："$cpu_user

# 获取内核空间占用 CPU 百分比
cpu_system=`top -b -n 1 | grep Cpu | awk '{print $4}' | cut -f 1 -d "%"`
echo "内核空间占用 CPU 百分比："$cpu_system

# 获取空闲 CPU 百分比
cpu_idle=`top -b -n 1 | grep Cpu | awk '{print $8}' | cut -f 1 -d "%"`
echo "空闲 CPU 百分比："$cpu_idle

# 获取等待输入输出占 CPU 百分比
cpu_iowait=`top -b -n 1 | grep Cpu | awk '{print $10}' | cut -f 1 -d "%"`
echo "等待输入输出占 CPU 百分比："$cpu_iowait


#3、获取 CPU 负载信息
# 获取 CPU15 分钟前到现在的负载平均值
cpu_load_15min=`uptime | awk '{print $11}' | cut -f 1 -d ','`
echo "CPU 15 分钟前到现在的负载平均值："$cpu_load_15min

# 获取 CPU5 分钟前到现在的负载平均值
cpu_load_5min=`uptime | awk '{print $10}' | cut -f 1 -d ','`
echo "CPU 5 分钟前到现在的负载平均值："$cpu_load_5min

# 获取 CPU1 分钟前到现在的负载平均值
cpu_load_1min=`uptime | awk '{print $9}' | cut -f 1 -d ','`
echo "CPU 1 分钟前到现在的负载平均值："$cpu_load_1min

#4、获取内存信息
# 获取物理内存总量
mem_total=`free | grep Mem | awk '{print $2}'`
echo "物理内存总量："$mem_total

# 获取操作系统已使用内存总量
mem_sys_used=`free | grep Mem | awk '{print $3}'`
echo "已使用内存总量(操作系统)："$mem_sys_used

# 获取操作系统未使用内存总量
mem_sys_free=`free | grep Mem | awk '{print $4}'`
echo $1+"剩余内存总量(操作系统)："$mem_sys_free

# 获取应用程序已使用的内存总量
mem_user_used=`free | sed -n 3p | awk '{print $3}'`
}
# 以此类推，为其他状态添加函数 主循环或一次性检查

while true; do  
    # 在这里执行你的命令，比如：  
    echo "run check state操作"  
    # 然后等待600秒（即10分钟）
    #GET Current time
    date_time=$(date "+%Y-%m-%d_%H%M%S")
    date_hour=$(date "+%Y-%m-%d_%H")
    echo "touch log"+$date_time
    check_gnss $date_time>> $path/gnss$date_hour.log
    #check_v2x >> /mnt/sdcard/gnss$date_time.log
    check_v2x $date_time
    get_Dev_state $date_time  >> $path/gnss$date_hour.log  
    echo "sleep 4mins++++++"
    sleep 200  
done

