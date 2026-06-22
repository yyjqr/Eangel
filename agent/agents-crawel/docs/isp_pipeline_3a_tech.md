# ISP Pipeline 与 3A 算法技术参考

## ISP Pipeline 标准流程

```
Sensor RAW → BLC(黑电平校正) → LSC(镜头阴影校正)
→ Demosaic(去马赛克) → AWB(自动白平衡) → CCM(色彩校正矩阵)
→ Gamma(伽马校正) → WDR/HDR(宽动态合成) → NR(降噪)
→ EE(边缘增强) → CSM(色彩空间转换) → Scale/Crop → YUV/RGB Output
```

## 3A 算法详解

### AE (Auto Exposure) 自动曝光
- **亮度统计**: 分区测光(256区), 中心权重/点测光/平均测光
- **收敛算法**: PID控制, 目标亮度128±10 (8bit)
- **抗闪烁**: 50Hz/60Hz 检测, 曝光时间=1/100s整数倍
- **增益控制**: Analog Gain + Digital Gain, ISO分级
- **HDR AE**: 长短帧曝光比自动调节 (1:4 ~ 1:16)
- **海思接口**: HI_MPI_ISP_AE_GetStatistics, ISP_AE_ATTR_S

### AF (Auto Focus) 自动对焦
- **CDAF** (反差对焦): Sobel/Laplacian 锐度统计, 爬山搜索算法
- **PDAF** (相位对焦): 遮罩像素相位差, 单次推算镜片位移量
- **激光对焦**: ToF传感器辅助暗光场景
- **VCM驱动**: DAC电流→镜片位移, 阻尼系数调节
- **对焦窗口**: 多窗口优先级 (人脸>中心>全局)
- **海思接口**: HI_MPI_AF_GetStatistics, AF_CTRL_ATTR_S

### AWB (Auto White Balance) 自动白平衡
- **色温估计**: 灰度世界法, 完美反射法, 色温曲线法
- **白点检测**: R/G ≈ B/G ≈ 1.0 区域提取
- **色温范围**: 2000K(烛光) ~ 10000K(阴天)
- **混合光源**: 多光源分割, 区域独立AWB
- **CCM计算**: 3×3色彩校正矩阵, ΔE<3
- **海思接口**: HI_MPI_ISP_AWB_GetStatistics, ISP_WB_ATTR_S

## 关键 ISP 算法

### Demosaic (去马赛克)
- **Bayer Pattern**: RGGB/GRBG/GBRG/BGGR
- **算法**: 双线性插值 → Malvar-He-Cutler → HQLI → 深度学习法
- **伪色抑制**: 色彩比恒定性检测, 中值滤波

### Noise Reduction (降噪)
- **2D NR**: 空域降噪, BM3D/NLM → 保留纹理
- **3D NR**: 时空域降噪(TNR), 运动补偿 + 多帧融合
- **Raw域NR**: 噪声建模(泊松+高斯), 自适应阈值
- **YUV域NR**: 亮度+色度分离, Y降噪弱/UV降噪强

### HDR/WDR (宽动态)
- **DOL-HDR**: 长短帧交替曝光, 运动补偿融合
- **Stagger HDR**: 3帧合成(超短/短/长)
- **Tone Mapping**: 全局/局部色调映射, Reinhard/ACES
- **LED闪烁补偿**: PWM调光LED频闪消除

## ISP 调试工具

- **海思 HiPQ Tools**: ISP参数实时调节, PC端预览
- **瑞芯微 RKAIQ**: 3A tuning tool, xml参数导出
- **Imatest/eSFR**: MTF/SFR解析, 色彩还原, 动态范围
- **D65/D50标准光源箱**: 色温校准, 色彩标定

## 参考标准

- ISO 12233: 分辨率测试(SFR/MTF)
- ISO 15739: 噪声测量
- ISO 14524: OECF光电转换
- EMVA 1288: 工业相机图像质量
- IEEE P2020: 车载ISP图像质量
