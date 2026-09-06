"""
20 个标准测试用例定义
覆盖：VI / VENC / VIDEO / AI / SVP / AUDIO / 多目同步 / 鲁棒性
每个用例是一个字典，由 test_runner.py 动态调度执行
"""

# ─── 用例类型说明 ──────────────────────────────────────────
# type: vi | venc | video | audio | ai | svp | multicam | stress | robustness
# sdk_cmd: 板端执行的 sample 程序命令（需提前编译好，放在板端 /usr/bin/ 或项目 bin/ 目录）
# capture_cmd: 同时触发 v4l2/arecord 采集（用于质量断言）
# assert_fn: 字符串，对应 test_executor.py 中的断言函数名
# cameras: 用于多目用例，指定参与的 camera id 列表

TEST_CASES = [

    # ══════════════════════════════════════════
    # 【VI】视频输入采集 - 单目基础
    # ══════════════════════════════════════════
    {
        "id"       : "TC_VI_01",
        "group"    : "VI",
        "name"     : "单目 2MP@30fps VI 采集与帧质量",
        "type"     : "vi",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 30,
        "duration_s": 3,
        "sdk_cmd"  : "sample_vi 0 1920 1080 30 /tmp/vi_tc01.yuv",
        "assert_fn": "assert_yuv_quality",
        "tags"     : ["smoke", "vi"],
    },
    {
        "id"       : "TC_VI_02",
        "group"    : "VI",
        "name"     : "单目 5MP@15fps 高分辨率 VI 采集",
        "type"     : "vi",
        "camera_id": 0,
        "width"    : 2592, "height": 1944, "fps": 15,
        "duration_s": 3,
        "sdk_cmd"  : "sample_vi 0 2592 1944 15 /tmp/vi_tc02.yuv",
        "assert_fn": "assert_yuv_quality",
        "tags"     : ["vi", "highres"],
    },
    {
        "id"       : "TC_VI_03",
        "group"    : "VI",
        "name"     : "单目 1080P@60fps 高帧率 VI 采集",
        "type"     : "vi",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 60,
        "duration_s": 3,
        "sdk_cmd"  : "sample_vi 0 1920 1080 60 /tmp/vi_tc03.yuv",
        "assert_fn": "assert_yuv_quality",
        "tags"     : ["vi", "highfps"],
    },

    # ══════════════════════════════════════════
    # 【VENC】视频编码
    # ══════════════════════════════════════════
    {
        "id"       : "TC_VENC_01",
        "group"    : "VENC",
        "name"     : "H.264 CBR 编码 码率精度校验",
        "type"     : "venc",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 30,
        "codec"    : "h264",
        "bitrate_kbps": 4000,
        "duration_s"  : 10,
        "sdk_cmd"  : "sample_venc 0 h264 1920 1080 30 4000 /tmp/venc_tc01.h264",
        "assert_fn": "assert_encoded_stream",
        "tags"     : ["venc", "h264"],
    },
    {
        "id"       : "TC_VENC_02",
        "group"    : "VENC",
        "name"     : "H.265 VBR 编码 质量校验",
        "type"     : "venc",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 30,
        "codec"    : "h265",
        "bitrate_kbps": 2000,
        "duration_s"  : 10,
        "sdk_cmd"  : "sample_venc 0 h265 1920 1080 30 2000 /tmp/venc_tc02.h265",
        "assert_fn": "assert_encoded_stream",
        "tags"     : ["venc", "h265"],
    },
    {
        "id"       : "TC_VENC_03",
        "group"    : "VENC",
        "name"     : "MJPEG 编码截图质量",
        "type"     : "venc",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 1,
        "codec"    : "mjpeg",
        "bitrate_kbps": 8000,
        "duration_s"  : 3,
        "sdk_cmd"  : "sample_venc 0 mjpeg 1920 1080 1 8000 /tmp/venc_tc03.jpg",
        "assert_fn": "assert_encoded_stream",
        "tags"     : ["venc", "jpeg"],
    },

    # ══════════════════════════════════════════
    # 【VIDEO】完整视频流（采集+编码+封装）
    # ══════════════════════════════════════════
    {
        "id"       : "TC_VIDEO_01",
        "group"    : "VIDEO",
        "name"     : "VI→VENC 全链路 H.264 流畅度",
        "type"     : "video",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 30,
        "codec"    : "h264",
        "bitrate_kbps": 4000,
        "duration_s"  : 15,
        "sdk_cmd"  : "sample_video 0 1920 1080 30 h264 4000 /tmp/video_tc01.mp4",
        "assert_fn": "assert_video_stream",
        "tags"     : ["video", "fullpipeline", "smoke"],
    },
    {
        "id"       : "TC_VIDEO_02",
        "group"    : "VIDEO",
        "name"     : "首帧出图延迟 < 3s",
        "type"     : "video",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 30,
        "codec"    : "h264",
        "bitrate_kbps": 4000,
        "duration_s"  : 5,
        "sdk_cmd"  : "sample_video_firstframe 0 /tmp/video_tc02_firstframe.txt",
        "assert_fn": "assert_first_frame_latency",
        "tags"     : ["video", "latency"],
    },
    {
        "id"       : "TC_VIDEO_03",
        "group"    : "VIDEO",
        "name"     : "低码率 360P 编码（弱网/低功耗场景）",
        "type"     : "video",
        "camera_id": 0,
        "width"    : 640, "height": 360, "fps": 15,
        "codec"    : "h264",
        "bitrate_kbps": 512,
        "duration_s"  : 10,
        "sdk_cmd"  : "sample_video 0 640 360 15 h264 512 /tmp/video_tc03.mp4",
        "assert_fn": "assert_video_stream",
        "tags"     : ["video", "lowbitrate"],
    },

    # ══════════════════════════════════════════
    # 【AUDIO】音频采集与编码
    # ══════════════════════════════════════════
    {
        "id"       : "TC_AUDIO_01",
        "group"    : "AUDIO",
        "name"     : "Line-in 1kHz 正弦波 SNR/THD 测试",
        "type"     : "audio",
        "alsa_dev" : "hw:0,0",
        "sample_rate": 16000,
        "channels" : 1,
        "duration_s": 3,
        "expected_freq": 1000,
        "sdk_cmd"  : "sample_audio_cap hw:0,0 16000 1 3 /tmp/audio_tc01.wav",
        "assert_fn": "assert_audio_sine",
        "tags"     : ["audio", "smoke"],
    },
    {
        "id"       : "TC_AUDIO_02",
        "group"    : "AUDIO",
        "name"     : "AAC 编码码流音质验证",
        "type"     : "audio",
        "alsa_dev" : "hw:0,0",
        "sample_rate": 48000,
        "channels" : 2,
        "duration_s": 5,
        "expected_freq": 1000,
        "sdk_cmd"  : "sample_audio_aac hw:0,0 48000 2 5 /tmp/audio_tc02.aac",
        "assert_fn": "assert_audio_sine",
        "tags"     : ["audio", "aac"],
    },
    {
        "id"       : "TC_AUDIO_03",
        "group"    : "AUDIO",
        "name"     : "音视频 A/V Sync 同步误差 < 100ms",
        "type"     : "av_sync",
        "camera_id": 0,
        "alsa_dev" : "hw:0,0",
        "width"    : 1920, "height": 1080, "fps": 30,
        "duration_s": 10,
        "sdk_cmd"  : "sample_av_sync 0 hw:0,0 /tmp/audio_tc03_av.mp4",
        "assert_fn": "assert_av_sync",
        "tags"     : ["audio", "avsync"],
    },

    # ══════════════════════════════════════════
    # 【多目同步】双目 / 三目 / 四目
    # ══════════════════════════════════════════
    {
        "id"       : "TC_MCAM_01",
        "group"    : "MultiCAM",
        "name"     : "双目帧同步误差 < 2ms",
        "type"     : "multicam",
        "camera_ids": [0, 1],
        "width"    : 1920, "height": 1080, "fps": 30,
        "duration_s": 5,
        "sdk_cmd"  : "sample_multicam 2 1920 1080 30 /tmp/mcam_tc01",
        "assert_fn": "assert_multicam_sync",
        "tags"     : ["multicam", "stereo"],
    },
    {
        "id"       : "TC_MCAM_02",
        "group"    : "MultiCAM",
        "name"     : "四目高负载 5MP@30fps 带宽测试",
        "type"     : "multicam",
        "camera_ids": [0, 1, 2, 3],
        "width"    : 2592, "height": 1944, "fps": 30,
        "duration_s": 10,
        "sdk_cmd"  : "sample_multicam 4 2592 1944 30 /tmp/mcam_tc02",
        "assert_fn": "assert_multicam_sync",
        "tags"     : ["multicam", "stress", "bandwidth"],
    },

    # ══════════════════════════════════════════
    # 【AI】AI 推理（ISP + NPU/SVP 协同）
    # ══════════════════════════════════════════
    {
        "id"       : "TC_AI_01",
        "group"    : "AI",
        "name"     : "人脸检测帧率 >= 15fps（NPU 协同）",
        "type"     : "ai",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 25,
        "duration_s": 10,
        "sdk_cmd"  : "sample_ai_detect 0 face /tmp/ai_tc01_result.json",
        "assert_fn": "assert_ai_perf",
        "expected_fps": 15.0,
        "tags"     : ["ai", "face", "npu"],
    },
    {
        "id"       : "TC_AI_02",
        "group"    : "AI",
        "name"     : "目标检测（行人）推理延迟 < 100ms",
        "type"     : "ai",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 25,
        "duration_s": 10,
        "sdk_cmd"  : "sample_ai_detect 0 person /tmp/ai_tc02_result.json",
        "assert_fn": "assert_ai_latency",
        "expected_latency_ms": 100,
        "tags"     : ["ai", "detection"],
    },
    {
        "id"       : "TC_AI_03",
        "group"    : "AI",
        "name"     : "VI→ISP→AI 全链路帧率不跌帧",
        "type"     : "ai",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 25,
        "duration_s": 15,
        "sdk_cmd"  : "sample_ai_pipeline 0 /tmp/ai_tc03_log.txt",
        "assert_fn": "assert_ai_pipeline",
        "tags"     : ["ai", "pipeline", "smoke"],
    },

    # ══════════════════════════════════════════
    # 【SVP】Smart Vision Processing
    # ══════════════════════════════════════════
    {
        "id"       : "TC_SVP_01",
        "group"    : "SVP",
        "name"     : "SVP 图像缩放 Bilinear 精度",
        "type"     : "svp",
        "width"    : 1920, "height": 1080, "fps": 30,
        "duration_s": 5,
        "sdk_cmd"  : "sample_svp_resize /tmp/input_1080p.yuv 1920 1080 960 540 /tmp/svp_tc01_out.yuv",
        "assert_fn": "assert_svp_output",
        "tags"     : ["svp", "resize"],
    },
    {
        "id"       : "TC_SVP_02",
        "group"    : "SVP",
        "name"     : "SVP IVE 运动检测（背景建模）",
        "type"     : "svp",
        "camera_id": 0,
        "width"    : 1280, "height": 720, "fps": 25,
        "duration_s": 10,
        "sdk_cmd"  : "sample_svp_ive 0 1280 720 /tmp/svp_tc02_result.json",
        "assert_fn": "assert_svp_ive",
        "tags"     : ["svp", "ive", "motion"],
    },

    # ══════════════════════════════════════════
    # 【鲁棒性/容错】Robustness
    # ══════════════════════════════════════════
    {
        "id"       : "TC_ROBUST_01",
        "group"    : "Robustness",
        "name"     : "CIS 热插拔自恢复（模拟 MIPI 断流）",
        "type"     : "robustness",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 30,
        "duration_s": 30,
        "sdk_cmd"  : "sample_vi_hotplug 0 30 /tmp/robust_tc01_log.txt",
        "assert_fn": "assert_self_healing",
        "tags"     : ["robustness", "hotplug"],
    },
    {
        "id"       : "TC_ROBUST_02",
        "group"    : "Robustness",
        "name"     : "长稳 72h（Mini 版 10min）内存泄漏检测",
        "type"     : "stress",
        "camera_id": 0,
        "width"    : 1920, "height": 1080, "fps": 30,
        "duration_s": 600,   # 实际长稳请改为 72*3600
        "sdk_cmd"  : "sample_vi 0 1920 1080 30 /dev/null",
        "assert_fn": "assert_no_memory_leak",
        "tags"     : ["stress", "memcheck"],
    },
]

# 用于快速冒烟测试（只跑 smoke 标签）
SMOKE_CASES = [tc for tc in TEST_CASES if "smoke" in tc.get("tags", [])]
