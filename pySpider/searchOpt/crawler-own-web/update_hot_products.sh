#!/bin/bash
# 热点产品定时更新脚本
# 建议使用 cron 定时执行，每2天运行一次
# 例如：0 2 */2 * * /path/to/update_hot_products.sh

cd /home/nvidia/valueSearch/value-test2026/crawler

# 激活虚拟环境（如果有）
# source venv/bin/activate

# 运行更新命令
echo "[$(date)] 开始更新热点产品排名..."
python3 manage.py update_hot_products --days=2 --top=5

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "[$(date)] ✅ 热点产品排名更新成功"
else
    echo "[$(date)] ❌ 热点产品排名更新失败"
fi

echo "----------------------------------------"
