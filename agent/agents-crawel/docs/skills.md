# 科技与编程技能知识库

## 人工智能与机器学习

### 大语言模型 (LLM)
- Transformer架构：自注意力机制、多头注意力、位置编码、KV Cache
- 预训练与微调：RLHF、LoRA、QLoRA、PEFT、DPO
- 主流模型：GPT-4/4o、LLaMA3、Qwen/通义千问、DeepSeek-V3、Claude 3.5、Gemini
- 推理框架：vLLM、llama.cpp、ollama、TensorRT-LLM、SGLang
- 量化技术：INT4/INT8量化、GPTQ、AWQ、BitsAndBytes、GGUF格式
- 上下文长度扩展：RoPE、YaRN、LongRoPE、Sliding Window Attention
- MoE架构：稀疏混合专家、路由机制、DeepSeek MoE

### RAG 检索增强生成
- 向量数据库：ChromaDB、Faiss、Milvus、Weaviate、Qdrant、PGVector
- Embedding模型：text-embedding-v3(阿里)、bge-m3、e5-mistral、nomic-embed-text
- 分块策略：固定大小分块、语义分块、层级分块、父子文档检索
- 检索策略：余弦相似度检索、MMR最大边际相关、混合检索（BM25+向量）、重排序
- LangChain框架：Chain、Agent、Memory、Retriever
- LlamaIndex框架：Index、Query Engine、Node Parser
- GraphRAG：知识图谱增强检索、实体抽取

### 深度学习框架
- PyTorch：张量操作、autograd、自定义算子、torch.compile、FlashAttention
- TensorFlow/Keras：SavedModel、TFLite推理
- JAX/Flax：函数变换、vmap、jit、pmap分布式训练
- ONNX：模型导出、跨框架互操作、onnxruntime推理
- Triton：GPU内核编写、融合算子优化

### 计算机视觉
- 目标检测：YOLOv8/v9/v10、RT-DETR、Grounding DINO
- 图像分割：SAM/SAM2、Mask2Former、语义分割、实例分割
- 多模态模型：CLIP、LLaVA、Qwen-VL、InternVL、MiniCPM-V
- 生成模型：Stable Diffusion、SDXL、DiT、ControlNet

### 机器学习经典算法
- 监督学习：线性/逻辑回归、SVM、决策树、随机森林、XGBoost、LightGBM
- 无监督学习：K-Means、层次聚类、PCA、t-SNE、UMAP、DBSCAN
- 强化学习：PPO、DQN、SAC、TD3、MCTS、AlphaZero风格

## 编程语言

### Python
- 异步编程：asyncio事件循环、aiohttp、async/await、异步上下文管理器
- 类型系统：typing模块、pydantic v2数据验证、dataclasses、Protocol
- 性能优化：Cython、Numba JIT、multiprocessing、concurrent.futures
- 包管理：pip、uv（极速包管理器）、poetry、conda/mamba
- 测试：pytest、unittest.mock、hypothesis属性测试
- 元编程：装饰器、描述符、metaclass、__slots__

### C/C++
- 现代C++特性：C++17结构化绑定、if constexpr、C++20 concept、range、协程
- C++23：std::expected、std::mdspan、std::print、std::flat_map
- 内存管理：RAII、unique_ptr/shared_ptr/weak_ptr、自定义分配器
- 并发：std::thread、std::atomic、std::mutex、std::jthread（C++20）
- 模板元编程：SFINAE、CRTP、可变参数模板、折叠表达式
- 嵌入式C++：裸机编程、HAL库、CMSIS、newlib
- 构建系统：CMake（target-based）、Makefile、Ninja、Bazel、vcpkg/conan
- 性能分析：perf、valgrind/callgrind、AddressSanitizer、ThreadSanitizer

### Rust
- 所有权系统：借用检查器、生命周期标注、内存安全保证
- 异步Rust：tokio运行时、async-std、Future特征、Pin
- 错误处理：Result/Option、anyhow、thiserror
- 嵌入式Rust：embedded-hal、RTIC实时中断、probe-rs调试
- 常用crates：serde（序列化）、rayon（并行）、clap（CLI）、axum（web）、sqlx

### Go
- 并发：goroutine、channel、select、sync.WaitGroup、sync.Mutex
- 标准库：net/http、database/sql、encoding/json、context传播
- 微服务：gRPC、protobuf、Connect协议
- 工具链：go modules、go generate、pprof性能分析

### TypeScript/JavaScript
- Node.js运行时：libuv事件循环、Stream、Worker Threads
- 前端框架：React、Vue 3（Composition API）、Next.js
- 类型系统：泛型、条件类型、infer、映射类型

## 嵌入式与边缘AI

### 嵌入式系统基础
- 实时操作系统：FreeRTOS任务调度、RT-Thread、Zephyr RTOS、NuttX
- ARM架构：Cortex-M0/M4/M7/M33（微控制器）、Cortex-A（应用处理器）、AArch64
- 外设通信协议：UART/USART、SPI（主从模式）、I2C、CAN/CANFD、USB CDC/HID
- 低功耗设计：Sleep/Stop/Standby模式、RTC唤醒、动态电压频率调节
- 调试工具：JTAG/SWD调试、OpenOCD、J-Link、逻辑分析仪

### NVIDIA Jetson平台
- JetPack SDK：CUDA工具包、cuDNN、TensorRT、DeepStream
- 硬件加速：GPU（Ampere/Volta）、DLA深度学习加速器、VIC视频编解码
- 性能监控：jtop、tegrastats、nvpmodel功耗模式、jetson-clocks
- DeepStream SDK：GStreamer流水线、nvstreammux、nvinfer插件
- Triton推理服务器：多模型管理、动态批处理、gRPC/HTTP接口

### 边缘AI推理优化
- TensorRT：网络解析、FP16/INT8量化、校准数据集、引擎序列化/反序列化
- ONNX Runtime：执行提供者（CUDA、TensorRT、OpenVINO EP）
- OpenVINO：Intel神经计算棒、模型优化器、推理引擎
- 模型轻量化：剪枝（结构化/非结构化）、知识蒸馏、神经架构搜索（NAS）
- MobileNet、EfficientNet、MobileViT等轻量模型

## Linux系统编程

### 内核与系统机制
- 进程管理：fork/exec/wait、信号处理（sigaction）、进程组与会话
- 进程间通信：管道、命名管道、消息队列、共享内存（mmap）、信号量
- 文件系统：VFS层、ext4/xfs、inotify文件监控、overlayfs（容器基础）
- 网络编程：TCP/UDP socket、epoll/kqueue IO多路复用、非阻塞IO
- eBPF：内核可编程、网络过滤、性能追踪、安全策略

### Shell脚本与工具链
- Bash：变量展开、函数、条件判断[[ ]]、数组、here document
- 文本处理：awk字段处理、sed流编辑、grep/ripgrep、jq JSON处理
- 系统监控：htop、iotop、ss/netstat、strace系统调用追踪、lsof
- 定时任务：cron/crontab、systemd timer单元

### 容器与虚拟化
- Docker：Dockerfile多阶段构建、layer缓存、network模式、volume挂载
- Docker Compose：服务编排、依赖管理、健康检查
- Kubernetes：Pod、Service（ClusterIP/NodePort/LoadBalancer）、Deployment、ConfigMap/Secret、Helm包管理
- 容器运行时：containerd、runc、kata containers
- ARM容器：QEMU仿真、buildx多架构构建

## 数据结构与算法

### 基础数据结构
- 线性结构：动态数组、链表（单/双/循环）、栈（单调栈应用）、队列（双端队列）
- 哈希：开放寻址、链式法、一致性哈希、布隆过滤器
- 树形结构：BST、AVL树、红黑树、B+树（数据库索引）、Trie字典树、线段树
- 堆：二叉堆、斐波那契堆、优先队列
- 图：邻接矩阵/表、稀疏图表示

### 算法设计与分析
- 时间/空间复杂度：大O记法、摊销分析
- 排序：快排（三路划分）、归并排序、堆排序、基数排序
- 动态规划：0/1背包、完全背包、最长公共子序列、最长递增子序列、区间DP
- 图算法：BFS/DFS、Dijkstra（优先队列优化）、Bellman-Ford、Floyd-Warshall、Kruskal/Prim最小生成树
- 字符串算法：KMP、Rabin-Karp滚动哈希、Aho-Corasick多模式匹配、后缀数组

### 系统设计
- 分布式：CAP理论、BASE原则、Raft共识算法、分布式事务（2PC/Saga）
- 缓存策略：LRU/LFU缓存、Redis持久化（RDB/AOF）、缓存击穿/雪崩/穿透
- 消息队列：Kafka分区/副本机制、RabbitMQ Exchange类型、消息幂等性

## 开发工具与DevOps

### 版本控制 Git/GitHub
- 分支策略：Git Flow、GitHub Flow、trunk-based development
- 高级操作：rebase（交互式）、cherry-pick、bisect二分查找bug、stash
- GitHub功能：Pull Request审查流程、Code Review、Branch Protection Rules
- GitHub Actions：workflow YAML语法、matrix构建策略、自定义Action、Secrets管理
- GitHub API：REST API、GraphQL API、Octokit SDK
- GitHub搜索：高级搜索语法（language:、stars:、fork:、topic:）

### CI/CD流水线
- GitHub Actions：触发器（push/PR/schedule）、job依赖、artifact传递
- 代码质量：SonarQube、pre-commit hooks、ruff/black代码格式化
- 安全扫描：Dependabot依赖更新、CodeQL静态分析、Trivy容器扫描

### 调试与性能分析
- GDB/LLDB：断点、watchpoint、core dump分析、反向调试
- Python调试：pdb/ipdb、py-spy采样分析、memory_profiler内存分析
- 火焰图：perf + flamegraph.pl、async-profiler（JVM）、py-spy火焰图
- 分布式追踪：OpenTelemetry、Jaeger、Zipkin

## 网络爬虫与数据采集

### 爬虫框架与技术
- Scrapy：Spider类、ItemPipeline、Middleware（代理/UA轮换）、CrawlSpider规则
- Playwright：page.goto、screenshot、selector、network拦截
- crawl4ai：AsyncWebCrawler、bypass_cache、markdown提取、AI辅助结构化

### 数据存储
- 关系型：MySQL/MariaDB（pymysql、SQLAlchemy）、PostgreSQL（asyncpg）
- 向量存储：ChromaDB（PersistentClient、collection.add/query）
- 全文检索：Elasticsearch、Meilisearch

### 数据处理
- pandas：read_csv/json、groupby聚合、merge/join、时间序列重采样
- 数据清洗：正则表达式、HTML解析（BeautifulSoup、lxml）

## 机器人与自动驾驶

### ROS/ROS2
- 核心概念：节点（Node）、话题（Topic）、服务（Service）、动作（Action）、参数（Parameter）
- 构建系统：colcon、ament_cmake/ament_python
- 导航栈Nav2：AMCL定位、costmap、路径规划（NavFn、DWB）
- 运动规划MoveIt2：运动学求解、碰撞检测、轨迹规划

### 传感器与感知
- 激光雷达：点云格式（PCD/ROS PointCloud2）、PCL库、点云滤波/分割/配准
- 相机：立体视觉（视差计算）、深度相机（RealSense/ZED）、鱼眼相机去畸变
- IMU：卡尔曼/扩展卡尔曼滤波、互补滤波、IMU预积分

### 自动驾驶算法
- 定位：激光SLAM（LOAM/LeGO-LOAM）、视觉SLAM（ORB-SLAM3）、NDT点云匹配
- 规划：A*路径规划、Hybrid A*、Frenet坐标系轨迹规划
- 控制：PID控制器调参、模型预测控制（MPC）、纯追踪算法（Pure Pursuit）

## GitHub 资源检索

### GitHub高级搜索技巧
- 代码搜索：`language:python stars:>1000 topic:llm`
- 组织搜索：`org:huggingface`, `org:microsoft`, `org:google-deepmind`
- 文件搜索：`filename:requirements.txt langchain`
- 时间筛选：`created:>2024-01-01 pushed:>2025-01-01`

### 热门技术资源库
- LLM推理：vllm-project/vllm、ggerganov/llama.cpp、lm-sys/FastChat
- RAG框架：langchain-ai/langchain、run-llama/llama_index、chroma-core/chroma
- 边缘AI：dusty-nv/jetson-inference、NVIDIA-AI-IOT/deepstream_python_apps
- 机器人：ros-navigation/navigation2、ros-planning/moveit2
- 嵌入式：zephyrproject-rtos/zephyr、FreeRTOS/FreeRTOS-Kernel

### 代码搜索API（规划接入）
- GitHub REST API：`GET /search/repositories`、`GET /search/code`
- 搜索限制：未认证30次/小时，Token认证5000次/小时
- PyGithub库：`Github(token).search_repositories(query)`

---

## C语言编程规范体系

### C99 标准 (ISO/IEC 9899:1999)
- 变量声明：允许在代码块中间声明变量（不再限定于块开头）
- 指定初始化器：`struct Point p = {.x = 1, .y = 2};`、数组 `int a[5] = {[2]=3, [4]=7}`
- 复合字面量：`(struct Point){.x=1, .y=2}` 可直接传参
- 可变长数组 VLA：`int buf[n]`（栈上动态大小，嵌入式慎用）
- `_Bool`类型 / `<stdbool.h>`：`bool`、`true`、`false`
- `<stdint.h>`：`int8_t`、`uint32_t`、`int64_t`、`uintptr_t` 固定宽度类型
- `<inttypes.h>`：`PRId32`、`PRIu64` 跨平台格式化宏
- `restrict` 关键字：告知编译器指针无别名，辅助向量化优化
- 内联函数 `inline`：替代函数式宏，类型安全
- 行尾注释 `//`：正式纳入标准
- 嵌入式最佳实践：禁用 VLA（`-Wvla`），强制 `<stdint.h>` 类型，`static inline` 替代宏

### C11 标准 (ISO/IEC 9899:2011)
- `_Generic`：编译期泛型选择，实现类型安全的宏重载
- 原子操作：`<stdatomic.h>`，`atomic_int`、`atomic_fetch_add`，无锁编程基础
- 线程支持：`<threads.h>`，`thrd_create`、`mtx_lock`（可选特性，嵌入式多用 POSIX pthread）
- `_Static_assert`：编译期断言，常用于检查结构体对齐、大小：`_Static_assert(sizeof(Header)==8, "...") `
- 匿名结构体/联合体：嵌套 `struct`/`union` 无需命名，简化访问
- `_Noreturn`：标记不返回函数（如 `abort`、错误处理跳转）
- `_Alignas` / `_Alignof`：显式控制对齐，DMA 缓冲区场景关键
- `gets()` 废除：全面用 `fgets()` 或 `getline()`
- 边界检查接口（附件K）：`memcpy_s`、`strcpy_s`（MSVC 支持，gcc 需第三方）

### C17 标准 (ISO/IEC 9899:2018)
- 定位：C11 的缺陷修复版（TC），无新语法特性
- 关键修复：VLA 行为澄清、原子操作语义修正、`tgmath.h` 类型泛型数学修正
- 实践意义：嵌入式项目推荐默认使用 `-std=c17`，兼顾稳定性

### C23 标准 (ISO/IEC 9899:2024)
- `bool`、`true`、`false` 升为关键字（不再需要 `<stdbool.h>`）
- `nullptr`：类型安全的空指针常量（类型 `nullptr_t`），替代 `NULL`/`0`
- `typeof` / `typeof_unqual`：类似 `__typeof__` 的标准化类型推导
- `#embed`：直接将二进制文件内嵌为数组，替代 `xxd` 转换
- `constexpr`：编译期常量变量（有别于 C++ constexpr，仅限标量和聚合）
- 属性语法 `[[]]`：`[[nodiscard]]`、`[[deprecated]]`、`[[maybe_unused]]`、`[[noreturn]]`
- `_BitInt(N)`：任意宽度整数类型，密码学/嵌入式位操作
- 二进制整数字面量：`0b1010_1111`（`_` 数字分隔符）
- `<stdbit.h>`：位操作标准库，`stdc_leading_zeros`、`stdc_popcount`
- `<stdckdint.h>`：带溢出检测的整数运算，`ckd_add(&r, a, b)`
- 废弃 K&R 函数声明、废弃隐式函数声明
- 编译器支持：GCC 13+（`-std=c23`）、Clang 17+（`-std=c2x`）

### C2y 未来趋势 (C标准委员会规划中)
- 反射（Reflection）提案：编译期访问类型元信息
- 改进模块化/接口声明机制
- 更强的 SIMD/向量化内置支持
- 安全编码强制化（受 NSA/CISA 安全编程倡议推动）

### 嵌入式C编码规范
- **MISRA C:2012**：汽车电子安全编码规则，134条强制/建议规则，ISO 26262功能安全
  - 禁止动态内存分配（`malloc`/`free`）
  - 禁止递归调用
  - 函数不超过60行，循环体不超过4层嵌套
  - 所有分支必须有 `default`，`switch` 每个 `case` 必须有 `break`
- **CERT C 编码标准**：Carnegie Mellon SEI，安全关键系统规范
  - MEM：内存安全（边界检查、越界读写防护）
  - INT：整数安全（溢出、截断、符号错误）
  - STR：字符串安全（缓冲区溢出防护）
- **嵌入式通用规范**：
  - 所有公共API函数返回值必须检查
  - 中断服务程序 ISR 保持最短执行路径，禁止阻塞调用
  - 共享资源访问必须使用原子操作或互斥保护
  - `volatile` 修饰硬件寄存器指针和 ISR 共享变量
  - 使用 `__attribute__((packed))` 控制通信协议结构体布局
  - 编译时开启 `-Wall -Wextra -Werror -Wformat=2 -Wshadow`

---

## 嵌入式Linux开发规范

### 驱动开发
- 字符设备驱动：`file_operations`、`cdev_init/add`、`copy_to/from_user`
- 平台驱动模型：`platform_driver`、设备树 DTS 解析、`of_get_property`
- V4L2框架：视频采集驱动，`v4l2_subdev`、`v4l2_async_register_subdev`
- Media Controller：媒体实体链路管理，pipeline配置
- DMA-BUF：零拷贝跨驱动缓冲区共享，`dmabuf_export/import`
- MIPI CSI-2 驱动：`D-PHY`/`C-PHY`、Lane 配置、虚拟通道、数据类型解析
- I2C 从设备驱动：传感器寄存器读写，`i2c_transfer`、`regmap`

### 设备树与板级支持
- DTS 语法：节点、属性、`compatible`、`#address-cells`、`reg`
- 常用 binding：GPIO、Clock、Pinctrl、Regulator、Reset、IOMMU
- 覆盖层 DTBO：模块化硬件描述，运行时叠加
- 内核配置：menuconfig、Kconfig 依赖树、defconfig 管理

### 嵌入式构建系统
- Yocto Project：Layer 架构、BitBake、recipe（`.bb`）、`MACHINE`/`DISTRO` 配置
- Buildroot：`make menuconfig`、BR2_EXTERNAL、包配置脚本
- OpenWrt：feeds 包管理、UCI 系统配置、LUCI Web界面
- U-Boot：SPL 二级引导、环境变量、fastboot、`distro_boot` 启动流程
- 根文件系统：BusyBox、systemd/s6 init、overlayfs 只读+可写层

### 内存管理与性能
- CMA 连续内存分配器：大块物理连续内存，用于 ISP/编解码 DMA
- ION 内存管理：Android/嵌入式跨进程共享缓冲区（新版用 DMA-BUF heap）
- 大页内存 HugePage：2MB/1GB 页，减少 TLB miss，视频处理加速
- CPU 亲和性绑定：`taskset`、`pthread_setaffinity_np`、实时线程 `SCHED_FIFO`
- Lockdep 死锁检测：`CONFIG_PROVE_LOCKING`、锁依赖图分析
- ftrace/tracepoint：函数级内核追踪，延迟分析

---

## 相机ISP SDK开发

### ISP Pipeline 架构
```
传感器RAW数据 → BLC(黑电平校正) → PDPC(坏点修复) → LSC(镜头阴影校正)
→ Demosaic(去马赛克) → CCM(色彩矩阵) → Gamma → WDR/HDR合成
→ NR(降噪:时域TNR+空域SNR) → Sharpening → CSC(色彩空间转换)
→ YUV输出 → 编码器(H.264/H.265/H.266)
```
- RAW格式：Bayer RGGB/GRBG/BGGR/GBRG，10/12/14/16bit packed/unpacked
- HDR模式：线性合成、多帧合成（SEF+LEF）、Staggered HDR、Zigzag HDR
- WDR压缩：Tone Mapping，局部/全局色调映射，Reinhard、ACES曲线
- 降噪算法：BM3D、NLM 非局部均值，时域帧间 Motion-Compensated TNR
- 去马赛克：双线性、AHD 自适应同质检测、MLCD 机器学习去马赛克

### 3A 算法

#### AE 自动曝光 (Auto Exposure)
- 测光模式：全局平均、中央重点加权、点测光、矩阵测光（分区权重）
- 曝光参数三角：曝光时间（Shutter）× 模拟增益（AGain）× 数字增益（DGain）
- 亮度目标：Y均值目标（如 128/255），直方图目标百分位控制
- 收敛算法：PID 控制器调节，步长自适应（大误差大步，小误差小步）
- 抗闪烁：50Hz/60Hz 市电频率，曝光时间锁定为 1/100s / 1/120s 整数倍
- ROI 感兴趣区域：人脸区域 AE 锁定，中心权重动态调整
- 宽动态 AE：双曝光（长+短）增益分配，HDR 场景保留高光细节

#### AF 自动对焦 (Auto Focus)
- 对比度检测 CDAF：Laplacian/Sobel 梯度，爬山法 Hill-Climbing，Fibonacci 搜索
- 相位差检测 PDAF：像面相位差传感器，双 PD 像素，快速精确对焦
- 激光对焦 LDAF：TOF 激光测距辅助，近距场景增强
- 运动检测：场景突变检测触发重新对焦，防止对焦拉锯
- 镜头驱动：VCM（音圈马达）驱动，步进电机，位置闭环控制
- 多区域 AF：9/15/25 点对焦区域，人脸/眼部优先

#### AWB 自动白平衡 (Auto White Balance)
- 色温范围：2800K（钨丝灯）～ 7500K（阴天），Planckian 轨迹
- 灰度世界假设：R/G/B 通道均值相等即为白平衡
- 完美反射假设：图像中最亮区域为白色参考
- 统计映射法：UV 色度平面上，光源聚类落点与色温映射表
- 机器学习AWB：CNN 预测色温，Intel OpenCV AWB Net，训练集覆盖多光源
- 增益计算：R_gain = G_mean / R_mean，B_gain = G_mean / B_mean
- 色彩矩阵 CCM：3×3 矩阵，随色温插值，标准光源（D65/A/TL84）标定

### 海思 HiSilicon ISP SDK
- 主要芯片：Hi3519DV500、Hi3516DV500（IPC/NVR旗舰）、Hi3403（车载）
- SDK 组件：HiISP（ISP驱动+算法）、Hi_MPI（媒体处理接口）、HiAI（神经网络加速）
- MPI框架：`HI_MPI_ISP_Init`、`HI_MPI_VI_CreatePipe`、`HI_MPI_VPSS_StartGrp`
- ISP算法库：AE/AF/AWB 以 `.so` 形式提供，支持自定义算法注册
- 自定义算法注册：`ALG_LIB_S`、`ISP_AE_REGISTER_S`，通过回调钩子接入
- V4L2适配：部分平台提供标准 V4L2 接口层
- 开源参考：`github.com/openhisilicon/HIVIEW`（社区维护的HiSilicon视图库）
- 编译工具链：`arm-himix200-linux-gcc`（Cortex-A53），`aarch64-mix210-linux-gcc`

### 联发科 MediaTek ISP SDK
- 主要芯片：MT6985（Dimensity 9200）、MT6897、MT8195（车载/平板）
- ISP架构：Imagiq 890，支持 320MP 处理能力，多摄融合
- 相机HAL：基于 Android Camera HAL3，`ICameraDevice`、`ICameraDeviceSession`
- 3A框架：MTK 3A Coordinator，AE/AF/AWB 协调控制，`IHal3A`接口
- AI相机：APU（AI处理单元）加速场景识别，`MTKDetector`、`MTKFaceBeauty`
- 调试工具：AaaBridge 调试桥，LogView 3A日志分析，RAW dump工具
- 开源参考：`github.com/MediaTek-Labs`、AOSP MTK BSP分支

### 瑞芯微 Rockchip ISP SDK
- 主要芯片：RK3588（8nm，6T NPU）、RV1126（IPC专用）、RK3562、RK3576
- ISP版本：RKISPv1（RK3399）、RKISPv2（RV1126/RK356x）、RKISPv3（RK3588）
- 开源驱动：`drivers/media/platform/rockchip/isp/`（已入 Linux 主线）
- RKAiq 算法库：开源！`github.com/airockchip/rkaiq`
  - 完整 3A 实现（AE/AF/AWB/DPCC/LSC/BLC/Gamma/NR/Sharp）
  - XML 参数配置文件（IQ文件），支持运行时调参
  - RkiqCam 标定工具，色卡/棋盘格标定
- V4L2 + Media Controller：标准Linux接口，`media-ctl`配置pipeline
- MPP（媒体处理平台）：H.264/H.265/VP9/AV1编解码，`mpp_create`、`mpi_encode`
- 编译工具链：`aarch64-rockchip-linux-gnu-gcc`

### Sony Sensor + ISP SDK
- 主流传感器：IMX678（4K安防）、IMX585（8MP星光）、IMX664（5MP HDR）、IMX334（4K消费）
- STARVIS/STARVIS2：背照式堆叠传感器，超低照度，0.001 lux 级别
- 接口规格：MIPI CSI-2（1/2/4 Lane），SLVS-EC（高速：最高8 Lane×10Gbps）
- DOL-HDR：数字重叠HDR，1帧内长短曝光交错，无运动模糊
- 配套ISP：Sony ISX021（车载ISP）、第三方 ISP 搭配使用
- 评估套件：EVAL-SEN-IMX678、配套 Raspberry Pi CSI 接入
- 参数调整：I2C 寄存器直接配置（曝光、增益、黑电平），参考 Datasheet Register Map
- 开源驱动：`github.com/torvalds/linux` - `drivers/media/i2c/imx*.c`

### 高通 Qualcomm Spectra ISP SDK
- 主要平台：Snapdragon 8 Gen 3/4（Spectra 100 ISP）、SM8750
- Spectra 架构：双ISP双处理器，最高320MP处理能力，支持8K视频
- Camera HAL：CAMX（Camera Adaptive eXtensible），`CamxContext`、`Pipeline`、`Node`
- Chi（Camera Hardware Interface）：CAMX扩展层，`ChiModule`、`ChiNode`
- QCamera SDK：高通Hexagon DSP加速，AI相机特性，`QCameraParameters`
- Kernel Driver：`drivers/media/platform/qcom/camera`（MSM Camera）
- Snapdragon Camera App SDK：高通开放SDK，场景检测、HDR、夜景增强
- 调试工具：Camera IQ、Chi-CDK Dump工具、Spectra RQMD调试器

### ISP 标定与调试工具链
- 色彩标定：Macbeth ColorChecker（24色卡），`dcraw`/`LibRaw` RAW处理
- 镜头标定：OpenCV `calibrateCamera`，畸变系数 k1/k2/k3/p1/p2，重投影误差<0.3px
- NR 标定：均匀照明灰板，SNR曲线，不同 ISO 下噪声模型（高斯+泊松）
- IQ 文件格式：XML/JSON配置，Rockchip `.aiq`，海思 `.ini`，高通 `.camx`
- 图像质量测试：ISO12233分辨率图，SFR/MTF测量，`imatest`/`Multicharts`
- RAW 分析工具：`rawpy`（Python）、`dcraw`、`darktable`、`RawDigger`

---

## 监控相机芯片与安防开发

### 主流安防SoC芯片
- 海思安防系列：Hi3519DV500（4K60fps AI IPC）、Hi3516CV610（2MP低功耗）
- 瑞芯微安防：RV1126B（双核A7+RISC-V，2T NPU，IPC专用）、RV1109
- 富士微电子：FH8856（4K H.265 NVR SoC）、FH8852
- 安霸 Ambarella：CV25（4K AI摄像机）、S6LM（低功耗 IoT 摄像机）
- 信芯/格科微：GC4663（1/2.9寸 400万CMOS）

### ONVIF 协议开发
- ONVIF Profile S/T/G/C：视频流、PTZ控制、事件、访问控制
- WSDL/SOAP：使用 `gSOAP` 生成桩代码，实现 `GetCapabilities`、`GetStreamUri`
- RTSP/RTP：`librtsp`、`live555`，SDP 媒体描述，H.264 RTP打包（RFC 6184）
- 发现协议：WS-Discovery，`onvif_discovery_probe`，组播 239.255.255.250:3702

### 视频编解码
- H.265/HEVC：CTU 64×64、CU/PU/TU树、CABAC熵编码，比H.264节省50%码率
- H.266/VVC：支持360°视频、HDR/WCG、感兴趣区域编码，2023年产品落地
- 码率控制：CBR恒定码率、VBR可变码率、CVBR约束可变、AVBR自适应
- 关键帧策略：IDR帧间隔（GOP大小）、场景切换强制IDR
- 低延迟模式：零延迟（no-delay）、实时流 RTP/RTSP/SRT/RTMP

### AI 安防算法
- 人脸识别：RetinaFace检测 + ArcFace/CosFace特征提取，底库检索1:N
- 越线/区域入侵：多边形ROI配置，逐帧目标轨迹，事件触发告警
- 客流统计：顶视角摄像机，人头检测，进出线统计
- 车牌识别 LPR：检测（YOLO）+ 超分 + OCR（CRNN+CTC）
- 行为分析：遗留物检测、奔跑检测、摔倒检测，骨骼关键点 (OpenPose/HRNet)

---

## 自动化测试框架

### 嵌入式单元测试
- **Unity**：C89兼容，单头文件，嵌入式首选，`TEST_ASSERT_EQUAL_INT`
- **CmockaC**：支持 mock 对象，模拟硬件外设接口，`will_return`/`expect_value`
- **CppUTest**：C/C++ 混用项目，内存泄漏检测，`CHECK_EQUAL`、`STRCMP_EQUAL`
- **GoogleTest**：`TEST_F`夹具、`MOCK_METHOD`、参数化测试 `TEST_P`
- **Catch2**：C++17 BDD 风格，`GIVEN`/`WHEN`/`THEN`，表达式驱动断言

### ISP/图像质量自动化测试
- 图像质量指标：PSNR（峰值信噪比）、SSIM（结构相似度）、LPIPS（感知相似度）
- 3A收敛测试：自动化灯箱控制（色温切换），AE收敛帧数、AWB色温误差ΔE
- 噪声一致性测试：多帧标准差统计，ISO vs NR强度回归测试
- 坏点检测测试：暗帧热点计数，光场均匀性测试
- 测试工具：`imatest`（商业）、`PIL/Pillow` + `scikit-image`（开源）、`OpenCV`

### 硬件在环测试 HIL
- FPGA 模拟传感器：生成 MIPI CSI-2 测试序列，注入标准测试图案
- 自动化灯箱：颜色恒定光源，D65/A/TL84 光源切换，程控辉度
- 测试管理：Jenkins Pipeline 触发，固件自动烧录（`fastboot`/`tftp`），测试报告生成
- 回归框架：Golden image 对比，差异超阈值报警，历史趋势图

### Python 测试自动化
- pytest 生态：`conftest.py` 夹具共享，`@pytest.fixture(scope="session")`，`pytest-xdist` 并行
- 接口测试：`requests` + `jsonschema`，ONVIF SOAP 接口自动化
- 性能测试：`locust` 压力测试，`timeit`/`cProfile` 微基准，`pytest-benchmark`
- 硬件控制：`pyserial` 串口、`smbus2` I2C、`spidev` SPI、`RPi.GPIO` / `gpiod`
- 镜像对比：`numpy` 像素差异统计，`cv2.PSNR`，`skimage.metrics.structural_similarity`

---

## Agent 智能检索系统（嵌入式/ISP方向）

### RAG 知识库构建
```python
# 基于 inquiry_chroma_llm.py 模式
# ChromaDB 持久化 + 嵌入式/ISP 专属知识库
client = chromadb.PersistentClient(path="./my_chroma_db")
ef = embedding_functions.DefaultEmbeddingFunction()
collection = client.get_or_create_collection(
    name="embedded_isp_docs", embedding_function=ef
)
# 分域 collection：embedded_dev / isp_sdk / camera_chip / autotest
```
- 文档分类导入：嵌入式规范、芯片手册、ISP算法文档、测试规范分别建 collection
- 元数据标注：`{"chip": "hi3519", "domain": "isp", "lang": "C", "standard": "C23"}`
- 混合检索：向量相似度 + BM25 关键词，`chromadb.utils.query_utils`
- 重排序：BGE-Reranker-v2-M3，Cross-Encoder 精排，提升检索精度

### Agent 工具设计（嵌入式方向）
- `query_chip_doc(chip, keyword)`：检索特定芯片的SDK文档
- `query_3a_algorithm(algo_type, scenario)`：AE/AF/AWB 算法检索
- `query_coding_standard(standard, rule_id)`：C99/C23/MISRA规则查询
- `search_github_isp(vendor, feature)`：GitHub开源ISP仓库检索
- `run_image_quality_test(image_path, metrics)`：触发图像质量评估
- `check_misra_violation(code_snippet)`：MISRA C规则违规检查

### LLM 集成（通义千问/Qwen）
- 模型选择：`qwen3-max-2026-01-23`（复杂推理）、`qwen-turbo`（快速响应）
- System Prompt 工程：注入领域知识角色（嵌入式ISP专家），限制幻觉
- Function Calling：工具调用 JSON Schema，支持 `parallel_tool_calls`
- 流式输出：`stream=True`，`response.iter_lines()`，提升用户体验
- 上下文管理：120KB context 限制，RAG 截断策略（`truncate_utf8_text`）

### 多 Collection 检索策略
```python
DOMAIN_COLLECTIONS = {
    "isp":       "isp_sdk_docs",
    "embedded":  "embedded_linux_docs",
    "camera":    "camera_chip_docs",
    "test":      "autotest_docs",
    "standard":  "coding_standard_docs",
}

def route_query(query: str) -> str:
    """基于关键词路由到对应 collection"""
    if any(k in query for k in ["3A", "AE", "AWB", "ISP", "demosaic"]):
        return DOMAIN_COLLECTIONS["isp"]
    if any(k in query for k in ["MISRA", "C99", "C23", "规范", "编码"]):
        return DOMAIN_COLLECTIONS["standard"]
    return DOMAIN_COLLECTIONS["embedded"]
```

---

## GitHub 开源 ISP 资源检索

### 搜索关键词策略
```
# ISP 通用
topic:isp language:c stars:>100
topic:camera-isp language:cpp
"3A algorithm" language:c
"auto exposure" "auto white balance" language:c

# 芯片厂商
org:airockchip isp
org:openhisilicon
"hi3519" OR "hi3516" ISP SDK
"rv1126" rkaiq
"qualcomm" "spectra" camera

# 算法专项
"tone mapping" HDR language:c stars:>50
"demosaic" bayer language:c
"lens shading correction" ISP
"noise reduction" TNR SNR embedded
```

### 核心开源仓库
| 仓库 | 芯片/平台 | 说明 |
|------|-----------|------|
| `airockchip/rkaiq` | Rockchip RK/RV系列 | 完整开源3A库，含AE/AF/AWB/NR，XML IQ配置 |
| `torvalds/linux` `drivers/media/` | 通用 | V4L2/Media Controller，IMX*传感器驱动 |
| `openhisilicon/HIVIEW` | HiSilicon Hi3519/Hi3516 | 社区逆向SDK，MPI接口封装 |
| `LibRaw/LibRaw` | 通用 RAW | 工业级RAW解码，支持1000+相机型号 |
| `darktable-org/darktable` | 通用 | 开源暗室，完整ISP流程参考实现 |
| `rawpy/rawpy` | Python | LibRaw Python封装，RAW后处理 |
| `19AI/awesome-isp` | 综合 | ISP论文/项目精选列表 |
| `MVTec/halcon` | 工业视觉 | 工业相机标定，IQ评估参考 |
| `OpenCV/opencv` | 通用 | `createCalibrateDebevec` HDR标定，色彩校正 |
| `google-research/isp-net` | AI ISP | Google AI ISP神经网络，端到端RAW→RGB |
| `megvii-research/CameraISP` | AI ISP | 旷视AI ISP，深度学习3A |
| `Qualcomm-AI-research/aimet` | 高通 AI | 模型量化，Snapdragon部署优化 |
| `intel-iot-devkit/sample-videos` | Intel | 测试视频序列，VPP/ISP验证 |
| `cisco/openh264` | 编解码 | H.264开源编码器，监控流媒体参考 |

### ISP 算法论文资源
- AE：《Perceptual Quality-Aware Exposure Control》ICCV 2023
- AWB：《Improving Auto White-Balance by Learning from RAW Images》ICCV 2019
- 去马赛克：《Deep Demosaicking》，《NTIRE2024 RAW Reconstruction Challenge》
- 降噪：《CBDNet》、《NAFNet》、《Restormer》 — 均有开源代码
- AI ISP：《Learning to See in the Dark》（陈晨，CVPR 2018）`github.com/cchen156/Learning-to-See-in-the-Dark`

### GitHub API 自动检索代码示例
```python
import requests

def search_isp_repos(vendor: str, feature: str, token: str) -> list:
    """检索特定厂商ISP相关仓库"""
    queries = {
        "hisilicon": f"hi3519 OR hi3516 {feature} language:c",
        "rockchip":  f"rkaiq OR rv1126 OR rk3588 {feature}",
        "sony":      f"imx678 OR imx585 {feature} sensor",
        "mediatek":  f"mtk OR mediatek isp {feature}",
        "qualcomm":  f"camx OR spectra {feature} camera",
    }
    query = queries.get(vendor.lower(), f"{vendor} isp {feature}")
    resp = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": query, "sort": "stars", "per_page": 10},
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])
```

---

## 未来编程趋势与能力建设

### AI 辅助开发趋势
- AI Coding Agent：GitHub Copilot Workspace、Cursor、Devin，从需求直接生成可运行代码
- 代码审查 AI：自动 MISRA/CERT C 合规检查，安全漏洞扫描（CodeQL + LLM解释）
- AI 调试：自然语言描述 Bug，LLM 定位 ISP pipeline 中的色彩/噪声问题
- 测试生成：LLM 自动生成边界条件测试用例，覆盖率导向的 Fuzzing（LibFuzzer + AI）

### 安全编程趋势（2025-2030）
- 内存安全优先：NSA/CISA 建议用 Rust/Go 替代 C/C++ 新项目
- C 语言安全扩展：C23 `<stdckdint.h>` 溢出检测，`[[nodiscard]]` 属性强制
- 供应链安全：SBOM（软件物料清单）强制要求，`syft`/`cyclonedx` 生成工具
- 形式化验证：Frama-C（C代码形式化分析）、SPARK（Ada子集，航空电子）

### 嵌入式AI 发展方向
- NPU 异构计算：ARM Ethos-U85（MCU级NPU）、RISC-V AI 扩展（RVV向量指令）
- TinyML：TensorFlow Lite Micro，模型 < 256KB，运行于 Cortex-M 裸机
- 神经ISP：端到端RAW→RGB CNN，替代传统pipeline，NPU加速推理
- 持续学习边缘推断：On-device fine-tuning，联邦学习（Federated Learning）
- RISC-V 生态：SiFive P670、玄铁C910，开源ISA，定制AI加速扩展

### 视频与图像处理趋势
- AV1/VVC 主流化：开源编解码（dav1d/SVT-AV1），比H.265再省30%码率
- 计算摄影：多帧降噪（Google Night Sight），语义HDR（场景感知曝光合并）
- 生成式图像增强：扩散模型超分辨率（Real-ESRGAN）、AI去雾、AI去雨
- 裸眼3D与光场相机：微透镜阵列，Lytro相机原理，重聚焦后处理
- 量子点CMOS传感器：近红外增强，ToF与RGB传感器集成

### Agent 开发范式演进
- 多智能体协同：Orchestrator-Worker 模式，专用领域 Agent（ISP调试Agent + 测试Agent）
- Memory 外置：向量知识库（ChromaDB）+ 关系数据库 + KV缓存三层记忆
- 工具调用标准化：MCP（Model Context Protocol），Agent 工具即服务
- 持续学习Agent：用户反馈强化，RAG 知识库增量更新，在线学习适配

### 编程语言生态预测
- C语言：嵌入式/内核永续，C23普及（2026-2028），AI辅助MISRA合规
- Rust：内核模块（Linux 6.x Rust驱动）、嵌入式安全关键系统、Android系统服务
- Python：AI/测试脚本不可替代，GIL 移除（3.13+），性能接近C扩展
- Zig：C的现代替代候选，嵌入式友好，编译期内存安全，C互操作无缝
- Carbon：Google C++继承者，与C++双向互操作，2027年前生产就绪预期
