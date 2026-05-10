#!/bin/bash
# 每周热点产品功能 - 快速入门指南

echo "========================================"
echo "每周热点产品功能 - 快速入门"
echo "========================================"

cd /home/nvidia/valueSearch/value-test2026/crawler

echo ""
echo "1️⃣  测试当前功能状态"
echo "----------------------------------------"
python3 test_hot_products.py

echo ""
echo ""
echo "2️⃣  手动更新热点产品（分析最近7天）"
echo "----------------------------------------"
read -p "是否立即更新？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    python3 manage.py update_hot_products --days=7 --top=5
    echo ""
    echo "✅ 更新完成！"
fi

echo ""
echo ""
echo "3️⃣  设置定时任务（可选）"
echo "----------------------------------------"
echo "建议每2天自动更新一次。可通过以下方式设置："
echo ""
echo "方式1: 使用 crontab（推荐）"
echo "  crontab -e"
echo "  添加: 0 2 */2 * * $PWD/update_hot_products.sh >> /var/log/hot_products.log 2>&1"
echo ""
echo "方式2: 查看详细配置"
echo "  cat crontab_setup.sh"
echo ""

read -p "是否查看crontab配置示例？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    cat crontab_setup.sh
fi

echo ""
echo ""
echo "4️⃣  验证数据库"
echo "----------------------------------------"
python3 manage.py shell -c "from news.models import HotProduct; hp = HotProduct.objects.order_by('rank').first(); print(f'最新排名第1: {hp.title if hp else \"无数据\"}'); print(f'总记录数: {HotProduct.objects.count()}')"

echo ""
echo ""
echo "========================================"
echo "🎉 快速入门完成！"
echo "========================================"
echo ""
echo "📚 更多信息："
echo "  - 详细文档: cat HOT_PRODUCTS_README.md"
echo "  - 功能总结: cat HOT_PRODUCTS_SUMMARY.md"
echo "  - 测试脚本: python3 test_hot_products.py"
echo ""
echo "💡 提示："
echo "  - 主页会自动显示热点产品"
echo "  - Django管理后台可查看所有排名历史"
echo "  - 建议每2天更新一次排名"
echo ""
