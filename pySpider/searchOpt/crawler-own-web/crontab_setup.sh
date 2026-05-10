#!/bin/bash
# Crontab 配置示例 - 每2天更新一次热点产品排名

# 1. 编辑 crontab
# crontab -e

# 2. 添加以下任一配置：

# 方案1：每2天凌晨2点执行（推荐）
# 0 2 */2 * * /home/nvidia/valueSearch/value-test2026/crawler/update_hot_products.sh >> /var/log/hot_products.log 2>&1

# 方案2：每周一和周四凌晨2点执行
# 0 2 * * 1,4 /home/nvidia/valueSearch/value-test2026/crawler/update_hot_products.sh >> /var/log/hot_products.log 2>&1

# 方案3：每天凌晨3点执行（如果需要更频繁更新）
# 0 3 * * * cd /home/nvidia/valueSearch/value-test2026/crawler && python3 manage.py update_hot_products --days=1 --top=5 >> /var/log/hot_products.log 2>&1

# 3. 查看已配置的定时任务
# crontab -l

# 4. 查看执行日志
# tail -f /var/log/hot_products.log

# 时间格式说明：
# * * * * * command
# │ │ │ │ │
# │ │ │ │ └─── 星期几 (0-7, 0和7都代表周日)
# │ │ │ └───── 月份 (1-12)
# │ │ └─────── 日期 (1-31)
# │ └───────── 小时 (0-23)
# └─────────── 分钟 (0-59)

# 特殊符号：
# * - 每个时间单位
# */n - 每n个时间单位
# , - 列举多个值
# - - 范围

echo "请根据需要选择合适的方案，然后执行："
echo "1. crontab -e"
echo "2. 复制上面合适的配置行"
echo "3. 保存退出"
