# 嵌入式开发与芯片验证最佳实践

> 汇总：Git/Gerrit 协作、开发效率平衡、分层架构、多媒体通路测试、Sensor 适配、调试技巧

---

## 一、Git 与 Gerrit 工作流

### 1.1 关系模型

```
┌─────────────────────────────────────────┐
│  Gerrit (代码审查服务器)                  │
│  ┌─────────┐    ┌──────────┐            │
│  │ refs/for │◄───│ 你的提交  │ (待审查)   │
│  └─────────┘    └──────────┘            │
│       ↓ review +2 / submit              │
│  ┌──────────┐                           │
│  │ refs/heads│ (正式合入)                │
│  └──────────┘                           │
└──────────┬──────────────────────────────┘
           │ git clone / git pull
┌──────────▼──────────┐
│  本地 Git 仓库       │
│  git commit         │
│  git push HEAD:refs/for/master  │
└─────────────────────┘
```

Gerrit 是 Git 上层加的代码审查。push 时推到 `refs/for/<分支>`，Gerrit 拦截等待 review，+2 通过后才合入 `refs/heads/`。

### 1.2 日常命令速查

```bash
# 开工
git fetch --prune && git rebase origin/master

# 小块提交
git add -p && git commit -m "描述"

# 推送审查
git push origin HEAD:refs/for/master

# review 被打回 → 修改后推送同一个 Change-Id
git commit --amend && git push origin HEAD:refs/for/master

# 解决冲突
git fetch origin && git rebase origin/master
# 解决冲突文件 → git add → git rebase --continue
# 乱套了 → git rebase --abort
```

### 1.3 常用别名

```bash
git config --global alias.fp  'fetch --prune'
git config --global alias.rbm 'rebase origin/master'
git config --global alias.p4r 'push origin HEAD:refs/for/master'
git config --global alias.st  'status -sb'
```

### 1.4 铁律

| 规则 | 原因 |
|------|------|
| 用 `rebase` 不用 `merge` | merge commit 在 Gerrit 上很难看 |
| 勤拉勤推 | 一天 rebase 三次，冲突追不上你 |
| 小提交 | 拆成独立变更，review 快、回滚易 |
| 不要用 `git pull`（默认 merge） | 会产生无意义 merge 节点 |

---

## 二、开发效率平衡

### 2.1 分开脑力模式

| 模式 | 做什么 | 最佳时段 |
|------|--------|----------|
| 🟢 理解模式 | 读代码、看文档、理逻辑 | 上午头脑清醒 |
| 🟡 制造模式 | 写代码、修 bug | 下午/晚上 |
| 🔵 操作模式 | Git 操作、编译、烧录、硬件调试 | 穿插 |
| ⚪ 收尾模式 | rebase、push、写 commit message | 下班前 30 分钟 |

> 一次只在一个模式里。上下文切换是最大的时间杀手。

### 2.2 修 Bug：缩小包围圈

```
1. 复现  →  确定触发条件
2. 二分  →  git bisect 或手动二分注释，锁定范围
3. 假设  →  猜一个根因
4. 验证  →  改一行，跑一次，看结果
5. 收工  →  修好立刻 commit，写清楚原因
```

> 不要同时追两只 bug。修 A 时发现 B，记 TODO 便签，修完 A 再碰 B。

### 2.3 代码理解：接口切入法

```
入口（API/中断/消息）→ 核心数据结构 → 关键函数 → 出口
         ↑
    先搞懂这个结构体是谁的、谁改它、改完去哪
```

用笔和纸画调用链，别在脑子里硬记。

### 2.4 黄金法则

| 法则 | 说明 |
|------|------|
| 一次一件事 | 上下文切换是最大的时间杀手 |
| 15 分钟卡住法则 | 15 分钟没进展 → 站起来走走 / 问人 / 换角度 |
| 提交要小 | commit 粒度 = 一个可描述的逻辑变更 |
| 代码即笔记 | commit message 写清楚**为什么**改，不是改了什么 |
| 硬件调试要记录 | 测了什么、改了什么、结果怎样，当场写 |

### 2.5 一天节奏参考

```
09:00   git fp + rbm，看 Gerrit 评论，回复 review    (15min)
09:15   理解模式：读代码/看文档                        (90min)
10:45   休息
11:00   制造模式：写新功能                             (60min)
12:00   午饭
13:00   制造模式：继续写 / 修 bug                      (90min)
14:30   硬件调试                                       (60min)
15:30   穿插 Git 操作、编译测试                         (30min)
16:00   代码审查别人的提交                              (30min)
16:30   收尾：rebase → commit --amend → push           (30min)
17:00   回顾今天改了啥，记两行笔记                       (10min)
```

---

## 三、嵌入式开发方法论

### 3.1 分层架构（防芯片绑架）

```
┌──────────────────────────────────┐
│  应用层 (业务逻辑)                 │  ← 和硬件无关，可跨平台
│  例如: 人脸识别流程、自动曝光策略    │
├──────────────────────────────────┤
│  中间层 (算法/协议)                │  ← 和硬件无关，纯 C/C++
│  例如: PID、滤波、RTSP 栈          │
├──────────────────────────────────┤
│  HAL 接口层 (统一 API)             │  ← 关键分界线
│  camera_init / i2c_write / gpio_set│
├──────────────────────────────────┤
│  驱动层 (芯片相关)                  │  ← 唯一换芯要改的地方
│  IMX415 / OV5640 / Hi3516 / RK3588 │
└──────────────────────────────────┘
```

核心原则：上面三层不知道下面是什么芯片。换芯片只换驱动层。

```c
// HAL 接口——所有芯片实现同一套
typedef struct {
    int (*init)(void *cfg);
    int (*start_stream)(int w, int h, int fps);
    int (*get_frame)(uint8_t *buf, int *len);
    int (*stop)(void);
} camera_ops_t;

// 换芯片 = 换一个实现
camera_ops_t *cam = &imx415_ops;  // 或 &ov5640_ops
// 上层代码一行不动
```

### 3.2 策略-机制分离（防需求反复）

| | 机制 (Mechanism) | 策略 (Policy) |
|------|------|------|
| 是什么 | 怎么做到的 | 什么时候做、做什么 |
| 谁写 | 一次写好，长期不变 | 经常调整 |
| 举例 | `I2C 读写函数` | `曝光时间 = 当前亮度 × 0.8` |
| 存放 | 驱动层 / HAL 层 | 应用层 / 配置文件 |

调参数放配置文件，别硬编码。改策略不重新编译。

### 3.3 相机/图像管线

#### 帧处理流水线

```
传感器 → ISP → 缩放 → 颜色转换 → 编码 → 推流
  ↓       ↓      ↓        ↓        ↓       ↓
 帧到达  自动   GPU/    CSC    H.264/  RTSP/
 中断   处理   RGA    矩阵    MJPEG  WebRTC
```

#### 零拷贝 DMA 链

```c
// 帧 buf 不 memcpy，用指针传递所有权
frame_t *f = dequeue_frame();   // DMA 直接写入的 buf
process(f);                      // 原地处理
encoder_feed(f);                 // 编码器也读同一块
enqueue_frame(f);                // 用完归还
```

#### ISP 调优文件外置

```
imx415_default.bin   → 白天
imx415_night.bin     → 夜晚
imx415_indoor.bin    → 室内
```

运行时加载，不用重新编译。换 sensor 只重新标定 ISP 参数。

---

## 四、嵌入式测试体系

### 4.1 测试三层法

| 层 | 在哪跑 | 测什么 | 工具 |
|------|------|------|------|
| 单元测试 | PC (x86) | 算法、协议栈、纯逻辑 | Unity / CppUTest / Ceedling |
| HAL 模拟测试 | PC | 业务逻辑 + Mock 硬件 | CMock + 自己写的 mock |
| 硬件在环 | 真实板子 | 完整链路 | 自动化测试脚本 + 串口 |

```c
// 一模一样的代码，PC 上测
#ifdef UNIT_TEST
  #define i2c_write(addr, reg, val) mock_i2c_write(addr, reg, val)
#else
  #define i2c_write(addr, reg, val) hal_i2c_write(addr, reg, val)
#endif
```

> 能在 PC 上跑完的别上板子跑。板子调试时间是 PC 的 10 倍。

---

## 五、嵌入式调试利器

### 5.1 比 printf 更好的三板斧

| 方法 | 用途 | 优点 |
|------|------|------|
| GPIO 翻转 + 示波器 | 测函数耗时、中断频率 | 纳秒级精度，不影响时序 |
| Segger RTT | 高速日志 | 不占 UART，CPU 开销极小 |
| Core dump + 离线分析 | 死机/硬错误现场 | 不需要在线调试器 |

```c
// 测 ISP 中断处理时间
#define PROFILE_PIN   GPIO_PIN_12
void isp_irq_handler() {
    gpio_set(PROFILE_PIN);      // 拉高
    process_frame();
    gpio_clear(PROFILE_PIN);    // 拉低
}
// 示波器量脉冲宽度 → 精确到微秒
```

### 5.2 HardFault 三板斧

```c
void HardFault_Handler(void) {
    uint32_t pc = __get_MSP();
    printf("PC=0x%08X LR=0x%08X\n", *(pc+24), *(pc+20));
    // 拿 PC 去 addr2line 或反汇编文件定位
    while(1);
}
```

### 5.3 编译加速

```bash
# ccache —— 改一行重编译从 5 分钟变 10 秒
export CC="ccache arm-none-eabi-gcc"
export CXX="ccache arm-none-eabi-g++"

# 分模块编译 —— 只改驱动层时别重编应用层
make sensor    # 只编传感器驱动
make app       # 只编应用层
```

---

## 六、芯片验证：多媒体通路测试

> 适用场景：IC 设计公司，多规格芯片 × 多媒体模块 (VI/VENC/VPSS) × 多种 Sensor

### 6.1 抽象"测试通路"而非"测试用例"

测试脚本一份，芯片和 sensor 的差异全部外置到配置文件。

```json
{
  "chip": "GK7205V300",
  "pipe": {
    "sensor": "imx415",       "i2c_bus": 2, "mipi_lane": 2,
    "vi":    {"dev": 0, "pipe": 0, "w": 1920, "h": 1080},
    "vpss":  {"grp": 0, "chn": 0, "w": 1920, "h": 1080},
    "venc":  {"type": "h265", "grp": 0, "bitrate": 4096}
  },
  "capture": {"frames": 300, "output": "/mnt/test_1080p.h265"}
}
```

```bash
./media_test --config gk7205_imx415.json
./media_test --config gk7605_ov5640.json
```

### 6.2 模块级原子测试（先拆开，再串起来）

```
Phase 1: 单模块
  VI 环回测试    →  抓 raw 帧，算 CRC，比对已知值
  VPSS 通帧测试  →  喂一张图，输出尺寸/格式对不对
  VENC 编码测试  →  喂 YUV，出码流，ffprobe 验参数

Phase 2: 两两联调
  VI → VPSS      →  抓 VPSS 输出帧，肉眼 + PSNR
  VPSS → VENC    →  确认编码参数不丢帧

Phase 3: 全链路
  Sensor → VI → VPSS → VENC → 长时间压力测试
```

每个模块测试完打标签：

```c
typedef enum {
    MOD_NOT_TESTED,
    MOD_PASS_BASIC,     // 单模块 basic 功能过
    MOD_PASS_STRESS,    // 压力测试过
    MOD_FAIL,           // 挂了，附 log
} module_status_t;
```

### 6.3 Sensor 适配：最小启动序列法

每个 sensor 抽象三层：

| 层 | 内容 | 通用性 |
|------|------|------|
| 上电时序 | AVDD/DVDD/IOVDD + reset + mclk | 每个 sensor 不同 |
| 初始化序列 | 寄存器表（I2C 下发） | 每个 sensor 不同 |
| 出图验证 | 读 MIPI 帧头 + dump 一帧 raw | **通用逻辑** |

```bash
./sensor_probe --sensor imx415 --i2c 2 --lane 2
# 内部：
#   1. 加载 imx415_init.h (寄存器表)
#   2. 上电 → 写 init 序列 → 读 chip_id → 启动 streaming
#   3. VI 抓一帧算锐度/亮度 → 报告 "OK" 或 "NG"
```

### 6.4 正交表压制组合爆炸

全组合 = 5 芯片 × 8 sensor × 3 分辨率 × 2 编码 = 240 条用例。用正交表选出代表性子集（~24 条），覆盖全部因子两两组合。发现失败再补测。

| # | 芯片 | Sensor | 分辨率 | 编码 |
|------|------|------|------|------|
| 1 | A | imx415 | 1080p | H265 |
| 2 | A | ov5640 | 4K | H264 |
| 3 | B | imx415 | 4K | H264 |
| 4 | B | gc2053 | 1080p | H265 |
| 5 | C | ov5640 | 1080p | H265 |
| ... | ... | ... | ... | ... |

### 6.5 回归自动化

```
┌──────────┐      ┌──────────────┐      ┌────────────┐
│ 新芯片    │  →   │ Jenkins/GitLab│  →   │ 测试板集群  │
│ SDK 推代码 │      │ 触发测试      │      │ 自动烧录测试 │
└──────────┘      └──────────────┘      └────────────┘
                                                 ↓
                    ┌───────────────┐
                    │ 报告：         │
                    │ VI ✓ VPSS ✓   │
                    │ VENC ✗ (码率异常)│
                    └───────────────┘
```

```bash
#!/bin/bash
BOARDS=("board1:192.168.1.101" "board2:192.168.1.102")

for b in "${BOARDS[@]}"; do
    name=$(echo $b | cut -d: -f1)
    ip=$(echo $b | cut -d: -f2)
    scp media_test root@$ip:/tmp/ &&
    ssh root@$ip "/tmp/media_test --config ${name}.json" &&
    echo "$name PASS" || echo "$name FAIL"
done
```

---

## 七、文档与日报

### 7.1 芯片幸存者手册

每颗芯片写一页备忘，一个坑不踩两次：

```markdown
# IMX415 开发备忘
## 坑
- I2C 地址: 0x1A (不是 0x34，数据手册写错了)
- 上电时序: AVDD → DVDD → IOVDD，间隔 >5ms
- mipi lane 数检测失败 → 先写 0x3F02 再读 0x3F03
## 最小寄存器序列
write 0x3000 0x0F  // 软复位
write 0x3002 0x00  // standby off
...
## 已验证的分辨率
1920x1080@30fps: mipi 594Mbps, 2 lane ✓
```

### 7.2 验证日报模板

```
2024-xx-xx 芯片验证日报
─────────────────────────
芯片: GK7205V300  | 版本: SDK_v2.1.0

| 模块 | 状态 | 覆盖率 | 备注 |
|------|------|------|------|
| VI   | ✅   | 3/3 sensor | ov5640 需降频到 297Mbps |
| VPSS | ✅   | 5/5 规格   | 4K→1080p 缩放 OK |
| VENC | ⚠️   | 2/3 规格   | H265+I帧间隔=1 码率异常，待复现 |
| 全链路 | 🔄 | 1/3 sensor | 压测中 (已跑 2h 无丢帧) |

今日坑:
- ov5640 默认 594Mbps → GK7205 只支持到 400M，需降频
- VENC 码率异常看起来是固件版本问题，等 FAE 回复
```

---

## 八、总结

### 嵌入式高效开发七条

| # | 原则 | 一句话 |
|------|------|--------|
| 1 | 分层架构 | 换芯片不改上层代码 |
| 2 | 策略配置化 | 调参数不重新编译 |
| 3 | 零拷贝 | 帧 buf 只传指针，不 memcpy |
| 4 | PC 上测 | 能在 x86 跑的不上板子 |
| 5 | GPIO 测时序 | printf 太慢，用 GPIO + 示波器 |
| 6 | 写芯片手册 | 一个坑不踩两次 |
| 7 | 小提交 | 改一个功能推一次，板子坏了能回滚 |

### 芯片验证核心原则

| 原则 | 做法 |
|------|------|
| 配置外置 | 芯片差异、sensor init 表、分辨率全部 json/yaml |
| 模块原子化 | VI / VPSS / VENC 一个一个验，别串着测 |
| 正交裁剪 | 全排列跑不完，用正交表选代表性子集 |
| 自动回归 | SDK 更新自动触发，板子集群并行跑 |
| 日报一张表 | 状态 + 覆盖率 + 坑，三列讲清楚 |

> 验证不是把所有组合跑一遍，是用最少的时间找到最可能坏的地方，然后盯着它揍。
> 嵌入式最高效率：让 PC 干 PC 的事，让板子只干板子的事，让自己不重复踩同一个坑。
