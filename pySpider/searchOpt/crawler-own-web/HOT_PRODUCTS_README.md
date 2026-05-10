# 热点产品功能使用说明

## 功能概述

为主页添加"每周热点产品"模块，从机器人、智能硬件、汽车、VR眼镜、军事设备等类别中自动筛选权重最高的3-5个产品进行展示，并将排名记录到数据库中，用于后续的每周、每月排名统计。

## 数据库变更

### 新增表：hot_products

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | AutoField | 主键 |
| title | CharField(500) | 产品标题 |
| url | CharField(500) | 链接地址 |
| category | CharField(50) | 产品类别 |
| rate | FloatField | 权重评分 |
| image_url | CharField(500) | 图片链接 |
| source | CharField(100) | 来源 |
| rank | IntegerField | 排名 |
| period_type | CharField(20) | 统计周期(daily/weekly/monthly) |
| period_start | DateField | 周期开始日期 |
| period_end | DateField | 周期结束日期 |
| created_at | DateTimeField | 创建时间 |
| updated_at | DateTimeField | 更新时间 |

### 创建数据库表

```bash
cd /home/nvidia/valueSearch/value-test2026/crawler

# 创建迁移文件
python3 manage.py makemigrations

# 执行迁移
python3 manage.py migrate
```

## 产品类别

系统会从以下类别中筛选热门产品：

1. **机器人** - 人形机器人、工业机器人、服务机器人
2. **智能硬件** - 智能家居、可穿戴设备、物联网设备
3. **汽车与自动驾驶** - 电动汽车、自动驾驶技术
4. **VR/AR/XR** - 虚拟现实、增强现实、混合现实设备
5. **军工与航天** - 无人机、卫星、航天技术
6. **产品发布** - 各类新产品发布
7. **芯片与半导体** - AI芯片、处理器等

## 使用方法

### 1. 手动更新热点产品排名

```bash
cd /home/nvidia/valueSearch/value-test2026/crawler

# 使用默认参数（分析最近2天，取前5名）
python3 manage.py update_hot_products

# 自定义参数
python3 manage.py update_hot_products --days=3 --top=10
```

参数说明：
- `--days`: 分析最近N天的数据（默认2天）
- `--top`: 保存前N个热门产品（默认5个）

### 2. 设置定时任务

#### 使用 crontab（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每2天凌晨2点执行）
0 2 */2 * * /home/nvidia/valueSearch/value-test2026/crawler/update_hot_products.sh >> /var/log/hot_products.log 2>&1
```

#### 或者直接使用命令

```bash
# 添加执行权限
chmod +x /home/nvidia/valueSearch/value-test2026/crawler/update_hot_products.sh

# 测试执行
./update_hot_products.sh
```

### 3. 查看热点产品

热点产品会自动在主页的"每周热点产品"模块中显示。

## 前端展示

在 `views.py` 中，系统会自动：

1. 从 `TechNews` 表筛选产品类别的新闻（实时数据）
2. 从 `HotProduct` 表读取最新的热点产品排名（定期更新）
3. 两种数据都会传递到模板：
   - `product_news`: 实时产品新闻（最多5条）
   - `hot_products`: 热点产品排名（最多5条）

## 后续扩展

### 每月排名

修改命令参数即可：

```bash
# 生成月度排名
python3 manage.py update_hot_products --days=30 --top=10
```

然后在代码中筛选 `period_type='monthly'` 的数据。

### 查询历史排名

```python
from news.models import HotProduct
from datetime import datetime, timedelta

# 查询本周排名
this_week = datetime.now().date() - timedelta(days=7)
weekly_hot = HotProduct.objects.filter(
    period_type='weekly',
    period_start__gte=this_week
).order_by('rank')

# 查询本月排名
this_month = datetime.now().date() - timedelta(days=30)
monthly_hot = HotProduct.objects.filter(
    period_type='monthly',
    period_start__gte=this_month
).order_by('rank')
```

### 产品趋势分析

```python
# 统计某个产品的历史排名变化
from django.db.models import Avg, Count

product_trends = HotProduct.objects.filter(
    title__icontains='特斯拉'
).values('period_start').annotate(
    avg_rank=Avg('rank'),
    count=Count('id')
).order_by('period_start')
```

## 注意事项

1. **数据库迁移**：首次使用前必须运行 `makemigrations` 和 `migrate`
2. **更新频率**：建议每2天更新一次，避免数据过于陈旧
3. **存储空间**：定期清理旧的排名数据，避免表过大
4. **分类准确性**：确保 main-spider2.py 正确分类产品新闻
5. **权重调整**：可在 tech_key_config_map.json 中调整产品关键词权重

## 故障排查

### 问题1：没有显示热点产品

- 检查是否运行了 `update_hot_products` 命令
- 检查 `HotProduct` 表是否有数据
- 检查产品新闻是否正确分类

### 问题2：排名不准确

- 调整 tech_key_config_map.json 中的权重
- 修改 `--days` 参数，扩大或缩小分析范围
- 检查产品类别是否完整

### 问题3：定时任务未执行

- 检查 crontab 配置是否正确
- 检查脚本是否有执行权限
- 查看日志文件确认错误信息

## 示例输出

```
开始更新热点产品排名...
分析周期：最近 2 天
排名数量：前 5 名

  Rank 1: [机器人] 特斯拉发布新一代人形机器人Optimus Gen 2... (权重: 2.45)
  Rank 2: [VR/AR/XR] Apple Vision Pro 2代传闻汇总... (权重: 2.31)
  Rank 3: [汽车与自动驾驶] 小鹏汽车推出全新自动驾驶系统... (权重: 2.18)
  Rank 4: [智能硬件] 华为发布新款智能手表Watch GT 5... (权重: 2.05)
  Rank 5: [军工与航天] 中国新型无人机首飞成功... (权重: 1.92)

✅ 成功更新 5 个热点产品排名
周期：2026-01-30 至 2026-02-01

各类别产品数量：
  机器人: 15 个产品
  VR/AR/XR: 12 个产品
  汽车与自动驾驶: 23 个产品
  智能硬件: 18 个产品
  军工与航天: 8 个产品
```
