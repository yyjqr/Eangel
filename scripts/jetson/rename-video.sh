#!/bin/bash
# 目标目录
mkdir process
TARGET_DIR="./process"  # 替换为你的文件目录
for file in video_*.h264; do
    if [[ -f "$file" ]]; then
        # 获取文件的创建时间
	# 使用正则表达式提取文件名中的时间部分
	echo "has video"
	# 获取文件名（不含路径）
    FILE_NAME=$(basename "$file")
    if [[ $FILE_NAME =~ ([0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}_[0-9]{5}) ]]; then
        OLD_TIMESTAMP="${BASH_REMATCH[1]}"
        echo "cur time:" ${OLD_TIMESTAMP}
        # 使用 stat 命令获取文件的创建时间
        CREATION_TIME=$(stat -c %y "$FILE_NAME" | awk '{print $1"_"$2}' | cut -d. -f1 | sed 's/://g')
        # 将结束时间转换为时间戳（秒）
	# 将时间格式转换为 date 可识别的格式（YYYY-MM-DD HH:MM:SS）
        formatted_time=$(echo "$CREATION_TIME" | sed 's/_/ /; s/\(....\)$/:\1/; s/\(..\)$/:\1/')
        end_timestamp=$(date -d "$formatted_time" +%s)
	echo "cur time seconds:" ${end_timestamp}
        # 计算开始时间（减去 10 分钟）
        start_timestamp=$((end_timestamp - 600))
        # 将开始时间转换为格式化字符串
        start_time=$(date -d "@$start_timestamp" +"%Y%m%d%H%M%S")

	NEW_TIMESTAMP="${start_time}"
        echo "creation time:" ${NEW_TIMESTAMP}
        # 替换文件名中的时间部分
        NEW_FILE_NAME=$(echo "$FILE_NAME" | sed "s/$OLD_TIMESTAMP/$NEW_TIMESTAMP/")
        NEW_FILE_PATH="$TARGET_DIR/$NEW_FILE_NAME"

        #timestamp=$(stat -c %y "$file" | awk '{print $1"-"$2}' | cut -d. -f1 | tr -d ':-' | sed 's/ /_/g')
	echo "cur time:" ${NEW_FILE_PATH}
        # 重命名文件
        #new_name="cam-${timestamp}.mp4"
        #mv "$file" "$new_name"
        #echo "Renamed $file to $new_name"
	   # 重命名文件
        mv "$FILE_NAME" "$NEW_FILE_PATH"
        echo "Renamed: $FILE_NAME -> $NEW_FILE_NAME"
    else
        echo "Skipping file (no timestamp found): $FILE_NAME"
    fi
    fi
done
