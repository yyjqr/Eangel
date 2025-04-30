#!/bin/bash

# 配置参数
LOG_FILE="/var/log/clock.log"
TEMP_LOG="/tmp/clock.log"
RESTORE_SECONDS=1  # 原脚本的恢复时间

# 初始化日志文件
init_log() {
    sudo touch "$LOG_FILE"
    sudo chmod 777 "$LOG_FILE"
}

# 获取当前时间信息
get_time_info() {
    echo "$(date '+%Y-%m-%d %H:%M:%S')"
}

# 检查是否在限制时间段内 (23:00-04:00)
is_restricted_time() {
    current_hour=$(date +%H)
    [ "$current_hour" -ge 23 ] || [ "$current_hour" -lt 4 ]
}

# 获取GPU频率信息
get_gpu_freq() {
    sudo jetson_clocks --show | grep "GPU" > "$TEMP_LOG"
    {
        cat "$TEMP_LOG" | awk '{print $3}' | sed 's/MaxFreq=//'
        cat "$TEMP_LOG" | awk '{print $4}' | sed 's/CurrentFreq=//'
        cat "$TEMP_LOG" | awk '{print $2}' | sed 's/MinFreq=//'
    } | tr '\n' ' '
}

# 主逻辑
main() {
    init_log
    curTime=$(get_time_info)

    echo "[$curTime] 脚本启动" | tee -a "$LOG_FILE"

    # 检查是否在限制时间段
    if is_restricted_time; then
        msg="当前时间 $(date +%H:%M) 处于限制时段 (23:00-04:00)，不调整频率"
        echo "$msg" | tee -a "$LOG_FILE"
        exit 0
    fi

    # 存储当前时钟设置
    jetson_clocks --store

    # 获取频率信息
    read -r MaxFreq CurrentFreq MinFreq <<< $(get_gpu_freq)

    echo "[$curTime] 初始频率 - Max:${MaxFreq} Current:${CurrentFreq} Min:${MinFreq}" | tee -a "$LOG_FILE"

    # 检查并设置最大频率
    if [ "$MinFreq" -eq "$MaxFreq" ]; then
        msg="GPU已经是最大频率"
    else
        msg="GPU未达到最大频率，正在设置..."
        echo "$msg" | tee -a "$LOG_FILE"
        sudo jetson_clocks | tee -a "$LOG_FILE"
    fi

    echo "[$curTime] $msg" | tee -a "$LOG_FILE"

    # 等待指定时间后恢复
    echo "[$curTime] 等待 ${RESTORE_SECONDS}秒后恢复..." | tee -a "$LOG_FILE"
    sleep ${RESTORE_HOURS}s

    # 恢复时钟设置
    jetson_clocks --restore
    read -r _ _ MinFreq <<< $(get_gpu_freq)

    echo "[$(get_time_info)] 频率已恢复 - MinFreq:${MinFreq}" | tee -a "$LOG_FILE"
}

# 执行主函数并处理错误
main 2>&1 | tee -a "$LOG_FILE"
exit ${PIPESTATUS[0]}
