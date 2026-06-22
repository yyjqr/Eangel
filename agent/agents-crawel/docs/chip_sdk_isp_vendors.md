# 嵌入式 ISP 芯片厂商 SDK 参考

## 海思 HiSilicon

### 主流芯片系列
| 型号 | 用途 | ISP能力 | NPU | 编码 |
|------|------|---------|-----|------|
| hi3516DV300 | 安防/DVR | 专业ISP | 0.5T | H.265 4K30 |
| hi3516AV200 | 家用摄像头 | 基础ISP | - | H.264 |
| hi3519AV100 | 高端安防 | 专业ISP+WDR | 2T | H.265 8K |
| hi3559AV100 | AI摄像机 | ISP+AI | 4T | H.265 8K60 |

### SDK 架构
```
MPP (Media Process Platform)
├── VI (Video Input)      — 视频采集, BT.601/BT.656/MIPI/LVDS
├── VPSS (Video Process)  — 裁剪/缩放/旋转/3DNR/Dehaze
├── VENC (Video Encode)   — H.264/H.265/MJPEG
├── VDEC (Video Decode)   — 解码
├── VO (Video Output)     — HDMI/CVBS/MIPI DSI
├── AI (NPU/IVE)          — 神经网络推理/智能分析
└── ISP                    — 图像信号处理

关键API:
- HI_MPI_SYS_Init() / HI_MPI_SYS_Exit()
- HI_MPI_VI_CreatePipe() / HI_MPI_VI_StartPipe()
- HI_MPI_ISP_Run() / HI_MPI_ISP_GetFd()
- HI_MPI_VPSS_CreateGrp() / HI_MPI_VPSS_StartGrp()
- HI_MPI_VENC_CreateChn() / HI_MPI_VENC_StartRecvPic()
```

### MIPI 配置示例 (hi3516DV300)
```c
combo_dev_attr_t MIPI_4LANE_800M = {
    .devno = 0,
    .input_mode = INPUT_MODE_MIPI,
    .mipi_attr = {
        .lane_id = {0,1,2,3,-1},
        .raw_data_type = RAW_DATA_12BIT,
        .wdr_mode = HI_MIPI_WDR_MODE_DOL,
    }
};
```

## 瑞芯微 Rockchip

| 型号 | ISP | NPU | 编码 |
|------|-----|-----|------|
| RV1126 | 专业ISP, 14MP | 2T | H.265 4K30 |
| RV1109 | ISP, 5MP | 1.2T | H.264 |
| RK3588 | ISP(双) | 6T | H.265 8K60 |
| RK3568 | 基础ISP | 1T | H.265 4K |

### RKAIQ 3A Tuning
- rkaiq_3A_server: 实时调参daemon
- xml配置文件: AE/AF/AWB参数
- Camera HAL3: 对接Android camera framework

## 安霸 Ambarella

| 型号 | ISP | NPU |
|------|-----|-----|
| CV25(S) | 专业ISP, 4K | 0.5T |
| CV28(S) | 双路ISP, 4K | 2T |
| CV5(S) | 8K ISP | 4T |

## Sony 传感器

| 型号 | 分辨率 | 特性 |
|------|--------|------|
| IMX415 | 4K 1/2.8" | STARVIS星光 |
| IMX585 | 4K 1/1.2" | STARVIS 2 |
| IMX678 | 8MP 1/1.8" | STARVIS 2 |
| IMX715 | 5MP 1/2.8" | 车载 |

## 全志 Allwinner

| 型号 | ISP | 编码 |
|------|-----|------|
| V833 | 专业ISP | H.265 4K |
| V536 | ISP | H.264 |

## 星宸 SigmaStar

| 型号 | ISP | NPU |
|------|-----|-----|
| SSC338Q | 专业ISP | 0.5T |
| SSC339G | 高端ISP | 2T |

## V4L2 Linux 驱动框架

```c
// 标准V4L2采集流程
int fd = open("/dev/video0", O_RDWR);
ioctl(fd, VIDIOC_QUERYCAP, &cap);
ioctl(fd, VIDIOC_S_FMT, &fmt);       // 设置格式
ioctl(fd, VIDIOC_REQBUFS, &reqbuf);  // 申请buffer
ioctl(fd, VIDIOC_QUERYBUF, &buf);    // 查询buffer
ioctl(fd, VIDIOC_QBUF, &buf);        // 入队
ioctl(fd, VIDIOC_STREAMON, &type);   // 开启流
ioctl(fd, VIDIOC_DQBUF, &buf);       // 出队(获取帧)
ioctl(fd, VIDIOC_QBUF, &buf);        // 重新入队
```

### V4L2 ISP 控制扩展
- V4L2_CID_ISP_AE_ENABLE
- V4L2_CID_ISP_AWB_MODE
- V4L2_CID_ISP_EXPOSURE
- V4L2_CID_ISP_GAIN
- V4L2_CID_ISP_HDR_MODE
- Media Controller API: media-ctl --set-v4l2
