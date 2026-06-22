# 嵌入式 Linux Camera & ISP 开发实战

## Linux 相机子系统架构

```
应用层: GStreamer | FFmpeg | OpenCV | V4L2-utils
         ↓
V4L2 Framework (videobuf2 / media controller)
         ↓
内核驱动: ISP驱动 | Sensor驱动 | CSI/MIPI控制器
         ↓
硬件: Camera Sensor → MIPI CSI-2 → ISP IP核 → DMA → DDR
```

## V4L2 Media Controller 拓扑

```bash
# 查看设备拓扑
media-ctl -d /dev/media0 -p

# 典型拓扑:
# Sensor(imx415 2-001a) → CSI-2 RX → ISP Input → ISP Pipeline → Video Output
#                                   ↓
#                           ISP Parameters → 3A Statistics
```

## ISP V4L2 子设备控制

```bash
# 设置 sensor 格式
media-ctl -d /dev/media0 --set-v4l2 "'imx415 2-001a':0[fmt:SRGGB12_1X12/3840x2160]"

# 配置 ISP 输出
media-ctl --set-v4l2 "'rkisp1_mainpath':0[fmt:YUYV8_2X8/1920x1080]"

# 查看格式
v4l2-ctl -d /dev/video0 --get-fmt-video

# 设置格式
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=YUYV
```

## GStreamer ISP Pipeline

```bash
# MIPI CSI 采集 + ISP 处理
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    video/x-raw,format=YUY2,width=1920,height=1080 ! \
    videoconvert ! x264enc ! h264parse ! \
    rtph264pay ! udpsink host=192.168.1.100 port=5000

# 带 ISP 3A 的 pipeline (瑞芯微 RKISP1)
gst-launch-1.0 rkisp device=/dev/video0 io-mode=dmabuf ! \
    video/x-raw,format=NV12,width=1920,height=1080 ! \
    rkisp1_3a ! videoconvert ! autovideosink
```

## Sensor 驱动开发

### Device Tree 配置
```dts
&i2c3 {
    imx415: camera@1a {
        compatible = "sony,imx415";
        reg = <0x1a>;
        clocks = <&ext_cam_clk>;
        pinctrl-names = "default";
        pinctrl-0 = <&cam_pins>;

        port {
            imx415_ep: endpoint {
                remote-endpoint = <&csi_ep>;
                data-lanes = <1 2 3 4>;
                link-frequencies = /bits/ 64 <891000000>;
            };
        };
    };
};
```

### Sensor 驱动框架
```c
static const struct v4l2_subdev_ops imx415_subdev_ops = {
    .core = &imx415_core_ops,
    .video = &imx415_video_ops,
    .pad = &imx415_pad_ops,
};

// 关键回调
static int imx415_s_stream(struct v4l2_subdev *sd, int enable);
static int imx415_set_fmt(struct v4l2_subdev *sd, struct v4l2_subdev_format *fmt);
static int imx415_get_fmt(struct v4l2_subdev *sd, struct v4l2_subdev_format *fmt);

// 上电时序
static int imx415_power_on(struct device *dev) {
    regulator_enable(sensor->avdd);   // 2.8V 模拟
    regulator_enable(sensor->dvdd);   // 1.2V 数字
    regulator_enable(sensor->dovdd);  // 1.8V IO
    msleep(5);
    clk_prepare_enable(sensor->xclk); // XCLK 24MHz
    msleep(10);
    gpiod_set_value(sensor->reset_gpio, 0); // 拉低复位
    msleep(1);
    gpiod_set_value(sensor->reset_gpio, 1); // 释放复位
    msleep(20);
    return 0;
}
```

## ISP 调试常见问题

1. **花屏/绿屏**: MIPI lane 极性反了，CSI register错误
2. **暗图**: AE统计区域配置错误，增益范围过小
3. **偏色**: AWB白点检测阈值错误，CCM矩阵未校准
4. **拖影**: DOL-HDR运动补偿未启用，长帧曝光过长
5. **噪点**: 模拟增益过大，NR参数需要tuning
6. **紫边**: LSC校准不足，镜头色散补偿

## Libcamera (新一代Linux相机框架)

```bash
# 列出相机
cam -l
libcamera-hello --list-cameras

# 拍照 (含ISP处理)
libcamera-jpeg -o test.jpg --width 1920 --height 1080

# 预览 (含3A)
libcamera-vid -t 0 --width 1280 --height 720

# RAW 输出 (无ISP)
libcamera-raw -o test.raw --width 3840 --height 2160
```

## Jetson Argus / V4L2

```bash
# Jetson 相机框架 (使用CSI摄像头)
nvgstcapture-1.0 --mode=2 --capture-auto

# V4L2 + Tegra ISP
v4l2-ctl -d /dev/video0 \
    --set-ctrl bypass_mode=0 \
    --set-fmt-video=width=1920,height=1080,pixelformat=RG10
```

## 性能优化要点

1. **DMA-BUF 零拷贝**: ISP输出→VENC输入，避免CPU拷贝
2. **ION/DMA-Heap**: 大块连续物理内存分配
3. **ISP硬件直通**: VI→ISP→VPSS→VENC硬件链路, 不经过CPU
4. **fence同步**: DMA fence保证buffer同步
5. **Cache管理**: dma_sync_sg_for_cpu/device 保证一致性
