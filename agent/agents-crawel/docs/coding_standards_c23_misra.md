# 嵌入式开发编码规范 C23/MISRA/CERT

## C23 新特性 (ISO 9899:2024)

### 关键新增
```c
// nullptr 常量
int *p = nullptr;  // 替代 NULL

// #embed 二进制嵌入
const unsigned char font[] = {
#embed "font.bin"
};

// constexpr
constexpr int MAX_BUFFERS = 16;
int buf[MAX_BUFFERS];

// typeof / typeof_unqual
typeof(x) y = x;
typeof_unqual(const int*) p;

// _BitInt(N) 任意位宽整数
_BitInt(24) color;
_BitInt(128) hash;

// auto 类型推导
auto x = 42;
auto *p = &x;

// 属性语法
[[nodiscard]] int get_status(void);
[[deprecated("use new_api()")]] void old_api(void);
[[fallthrough]];
[[unsequenced]];  // 无副作用函数标记
```

## MISRA C:2012 核心规则

### Rule 1.x (标准环境)
- Rule 1.3: 不得发生未定义/未指定行为
- Rule 2.1: 不得有不可达代码

### Rule 8.x (声明与定义)
- Rule 8.3: 所有声明/定义类型一致
- Rule 8.4: 外部对象使用前需可见声明

### Rule 10.x (类型系统)
- Rule 10.1: 操作数不得为不适当的基本类型
- Rule 10.4: 复合运算符操作数必须相同类型

### Rule 15.x (控制流)
- **Rule 15.5**: 每个函数末尾最多一个return
- Rule 15.3: goto只向前跳转
- Rule 15.7: if..else if 必须以else结尾

### 嵌入式关键
- Rule 21.1: #undef不得用于标准库宏
- Rule 21.2: 不得使用保留标识符
- Rule 21.6: 不得使用<stdio.h>产生输出

## CERT C 安全编码

### MEM (内存)
- MEM30-C: 不要访问已释放的内存
- MEM31-C: 动态分配后检查NULL
- MEM34-C: 只释放动态分配的内存
- MEM35-C: 分配足够的内存

### INT (整数)
- INT30-C: 无符号整数回绕
- INT32-C: 有符号整数溢出
- INT34-C: 移位不超过位宽
- INT35-C: 使用正确的整数类型

### STR (字符串)
- STR31-C: 确保字符串有足够空间
- STR32-C: 传递size参数给不安全函数
- STR38-C: 字符串截断后手动终结

### EXP (表达式)
- EXP36-C: 不要转换指向对齐要求更严格对象的指针
- EXP40-C: 不要修改常量对象

## 嵌入式编码最佳实践

```c
// 1. 固定宽度整数
#include <stdint.h>
uint32_t frame_count;    // ✓ 良好
int count;                // ✗ 大小不明确

// 2. MISRA 兼容的 for 循环
for (size_t i = 0; i < len; ++i) {  // ✓
// for (int i = 0; i < len; ++i) {  // ✗ 有符号对比
// for (i = 0; i != len; ++i) {     // ✗ 可能死循环
// for (i = 1; i >= 0; --i) {       // ✗ 无符号永远不会<0

// 3. DMA 安全 - cache 对齐
__attribute__((aligned(64))) uint8_t dma_buf[4096];

// 4. volatile 用于寄存器
volatile uint32_t *REG_ISP_CTRL = (uint32_t*)0x12000000;

// 5. ISR 安全 - 关中断临界区
__disable_irq();
critical_data++;
__enable_irq();

// 6. Bit-banding 位操作
#define BIT_SET(reg, n)   ((reg) |= (1U << (n)))
#define BIT_CLR(reg, n)   ((reg) &= ~(1U << (n)))
#define BIT_TST(reg, n)   (((reg) >> (n)) & 1U)
```

## 功能安全 ISO 26262

- ASIL分级: A/B/C/D
- 技术安全概念(TSC)
- 软件组件安全分析
- MISRA C 强制用于ASIL C/D
- 代码覆盖率: Statement/Branch/MCDC (ASIL D)
