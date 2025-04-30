#!/usr/bin/python3
## -*- coding: UTF-8 -*-
import os
import subprocess
import sys
import platform

import time
import threading
from concurrent.futures import ThreadPoolExecutor
## deal with UTF-8
def safe_decode(byte_str):

    try:
        return byte_str.decode('utf-8')
    except UnicodeDecodeError:
        return byte_str.decode('gbk', errors='ignore')

def extract_frames(video_path, output_dir, interval_sec=15, frame_format='jpg'):
    
    #Ê¹ÓÃFFmpeg´ÓÊÓÆµÖĞ°´¹Ì¶¨Ê±¼ä¼ä¸ô³éÈ¡Ö¡
    
    #ÎÊı:
     #   video_path: ÊÓÆµÎÄ¼şÂ·¾¶
      #  output_dir: Êä³öÄ¿Â¼
       # interval_sec: ³éÖ¡¼ä¸ô(Ãë)
       # frame_format: Êä³öÍ¼Æ¬¸ñÊ½(jpg/png)
    
    try:
        # ´¦ÀíÖĞÎÄÂ·¾¶ÎÊÌâ
        video_path = video_path.encode('utf-8').decode('utf-8')
        output_dir = output_dir.encode('utf-8').decode('utf-8')
        
        # ´´½¨Êä³öÄ¿Â¼
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_subdir = os.path.join(output_dir, video_name)
        os.makedirs(output_subdir, exist_ok=True)
        
        # FFmpegÃüÁî
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'fps=1/{interval_sec}',
            '-q:v', '2',
            '-f', 'image2',
            os.path.join(output_subdir, f'frame_%04d.{frame_format}')
        ]
        
        # ´¦ÀíWindowsÏÂµÄÂ·¾¶·Ö¸ô·û
        if sys.platform == 'win32':
            cmd = [arg.replace('/', '\\') for arg in cmd]
        
        result = subprocess.run(cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print(f"success: {video_path}")
    except subprocess.CalledProcessError as e:
        error_msg = safe_decode(e.stderr) if e.stderr else str(e)
        print(f"fail {video_path}: {error_msg}")
    except Exception as e:
        print(f"error {video_path}: {str(e)}")

def batch_process_videos(input_dir, output_dir, interval_sec=15, max_workers=4):
    
    #MP4ÊÓÆµ
    
    #²ÎÊı:
    #    input_dir: ÊäÈëÄ¿Â¼
    #    output_dir: Êä³öÄ¿Â¼
    #    interval_sec: ³éÖ¡¼ä¸ô(Ãë)
    #    max_workers: ×î´óÏß³ÌÊı
    
    try:
        # »ñÈ¡ËùÓĞMP4ÎÄ¼ş£¨´¦ÀíÖĞÎÄÄ¿Â¼£©
        video_files = []
        for f in os.listdir(input_dir):
            try:
                if f.lower().endswith('.mp4'):
                    full_path = os.path.join(input_dir, f)
                    # ³¢ÊÔUTF-8½âÂëÎÄ¼şÃû
                    try:
                        full_path.encode('utf-8').decode('utf-8')
                    except:
                        full_path = full_path.encode('gbk').decode('utf-8', errors='replace')
                    video_files.append(full_path)
            except UnicodeDecodeError:
                print(f"warning can't decode: {f}")
                continue
        
        if not video_files:
            print("not find MP4")
            return
        
        # Ê¹ÓÃÏß³Ì³Ø²¢ĞĞ´¦Àí
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for video in video_files:
                executor.submit(extract_frames, video, output_dir, interval_sec)
    except Exception as e:
        print(f"error: {str(e)}")

if __name__ == "__main__":
    # ÅäÖÃ²ÎÊı£¨´¦ÀíÖĞÎÄÂ·¾¶£©
    try:
        INPUT_DIR = "D:\\camData-2025"       # ÊÓÆµÊäÈëÄ¿Â¼
        OUTPUT_DIR = "D:\\camData-2025\\frames"     # Í¼Æ¬Êä³öÄ¿Â¼
        INTERVAL = 15               # ³éÖ¡¼ä¸ô(Ãë) 15»ò60
        print("test ffmpeg decode")
        # ¼ì²éFFmpegÊÇ·ñ¿ÉÓÃ
        try:
            subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            print("error, no ffmpeg")
            exit(1)
        
        # ´´½¨Êä³öÄ¿Â¼£¨´¦ÀíÖĞÎÄÄ¿Â¼£©
        try:
            os.makedirs(OUTPUT_DIR, exist_ok=True)
        except Exception as e:
            print(f"mkdir dir failed: {str(e)}")
            exit(1)
        
        # ¿ªÊ¼´¦Àí
        print(f"{INPUT_DIR},{INTERVAL}...")
        batch_process_videos(INPUT_DIR, OUTPUT_DIR, INTERVAL)
        print("OUTPUT_DIR:", OUTPUT_DIR)
    except Exception as e:
        print(f"error: {str(e)}")
