"""
Bulk Video Editor & Remixer Engine
Specially optimized for Facebook & Instagram Reels, YouTube Shorts, and TikTok.
Transforms repurposed videos to defeat duplicate content detection and boost reach.
"""

import os
import re
import json
import subprocess
import shutil
import threading
from typing import Dict, Any, Optional, Callable

SUPPORTED_EXTENSIONS = (
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv",
    ".ts", ".m4v", ".wmv", ".3gp", ".mts", ".m2ts"
)

def is_video_file(path: str) -> bool:
    """Check if file path has a supported video extension."""
    if not path:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in SUPPORTED_EXTENSIONS

def sanitize_filename(name: str) -> str:
    """Sanitize name for Windows file systems."""
    clean = re.sub(r'[<>:"/\\|?*]', '_', name)
    clean = clean.strip().strip('.')
    return clean if clean else "edited_video"

def format_duration(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    try:
        s = int(round(seconds))
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{sec:02d}"
        return f"{m:02d}:{sec:02d}"
    except Exception:
        return "00:00"

def format_size(bytes_num: int) -> str:
    """Format bytes into readable size."""
    try:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_num < 1024.0:
                return f"{bytes_num:.1f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.1f} TB"
    except Exception:
        return "0 B"

def check_ffmpeg() -> Dict[str, Any]:
    """Verify FFmpeg and FFprobe availability."""
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ffprobe_ok = shutil.which("ffprobe") is not None
    return {
        "ffmpeg": ffmpeg_ok,
        "ffprobe": ffprobe_ok,
        "all_ready": ffmpeg_ok and ffprobe_ok
    }

def get_video_info(video_path: str) -> Dict[str, Any]:
    """Retrieve video and audio stream information using ffprobe."""
    info = {
        "path": video_path,
        "name": os.path.basename(video_path),
        "size": 0,
        "size_str": "0 B",
        "duration": 0.0,
        "duration_str": "00:00",
        "width": 0,
        "height": 0,
        "resolution": "Unknown",
        "fps": 30.0,
        "has_audio": False,
        "audio_codec": "",
        "video_codec": "",
        "valid": False
    }

    try:
        info["size"] = os.path.getsize(video_path)
        info["size_str"] = format_size(info["size"])
    except Exception:
        pass

    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,duration:format=duration",
            "-of", "json",
            video_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            format_info = data.get("format", {})
            try:
                info["duration"] = float(format_info.get("duration", 0.0))
            except Exception:
                info["duration"] = 0.0

            streams = data.get("streams", [])
            for stream in streams:
                codec_type = stream.get("codec_type")
                if codec_type == "video" and info["width"] == 0:
                    info["width"] = int(stream.get("width", 0))
                    info["height"] = int(stream.get("height", 0))
                    info["video_codec"] = stream.get("codec_name", "")
                    
                    # FPS calculation
                    fps_str = stream.get("r_frame_rate", "30/1")
                    try:
                        if "/" in fps_str:
                            num, den = fps_str.split("/")
                            den_val = float(den)
                            info["fps"] = round(float(num) / den_val, 2) if den_val != 0 else 30.0
                        else:
                            info["fps"] = round(float(fps_str), 2)
                    except Exception:
                        info["fps"] = 30.0

                    if info["duration"] == 0.0:
                        try:
                            info["duration"] = float(stream.get("duration", 0.0))
                        except Exception:
                            pass
                elif codec_type == "audio":
                    info["has_audio"] = True
                    info["audio_codec"] = stream.get("codec_name", "")

            if info["width"] > 0 and info["height"] > 0:
                info["resolution"] = f"{info['width']}x{info['height']}"
                info["duration_str"] = format_duration(info["duration"])
                info["valid"] = True
    except Exception as e:
        print(f"Error probing video {video_path}: {e}")

    return info

def build_ffmpeg_command(
    input_path: str,
    output_path: str,
    config: Dict[str, Any],
    video_info: Dict[str, Any]
) -> tuple[list[str], float]:
    """
    Constructs the complete FFmpeg command line with anti-duplicate transforms,
    canvas sizing, color grading, audio tweaks, and metadata stripping.
    Returns (cmd_args, expected_output_duration).
    """
    speed = float(config.get("speed", 1.0))
    if speed <= 0.1:
        speed = 1.0
    
    expected_duration = video_info["duration"] / speed if video_info["duration"] > 0 else 0.0

    zoom_pct = float(config.get("zoom_percent", 0.0)) / 100.0  # e.g. 0.03 for 3%
    flip_h = bool(config.get("flip_h", False))
    color_grade = bool(config.get("color_grade", True))
    vignette = bool(config.get("vignette", False))
    aspect_mode = config.get("aspect_mode", "9_16_blur_95")  # "keep", "9_16_blur_95", "9_16_blur", "9_16_crop", "1_1_blur", "16_9_blur"
    border = config.get("border", "none")  # "none", "white_3px", "black_3px", "gold_3px"
    text_overlay = config.get("text_overlay", "").strip()
    text_position = config.get("text_position", "top")  # "top", "bottom", "center"
    text_color = config.get("text_color", "yellow")
    text_fontsize = config.get("text_fontsize", 54)
    text_box_bg = config.get("text_box_bg", "black_box")
    text_custom_x = config.get("text_custom_x", None)
    text_custom_y = config.get("text_custom_y", None)
    watermark_path = config.get("watermark_path", "")
    watermark_pos = config.get("watermark_pos", "top_right")
    custom_bg_path = config.get("custom_bg_path", "").strip()
    enable_box_frame = bool(config.get("enable_box_frame", False))
    bg_video_pos = config.get("bg_video_pos", "lower_center")  # "lower_center", "center", "upper_center", "top", "bottom", "below_header", "custom"
    custom_y = config.get("custom_y", 500)
    bg_video_pos_x = config.get("bg_video_pos_x", "center")  # "center", "right", "left", "right_flush", "left_flush", "custom"
    custom_x = config.get("custom_x", 0)
    box_scale = float(config.get("box_scale", 0.95 if aspect_mode == "9_16_blur_95" else 0.82))  # e.g. 0.95, 0.82, 0.60
    box_height_scale = float(config.get("box_height_scale", 0.85 if bg_video_pos_x in ("right", "left", "right_flush", "left_flush") else 0.58))
    box_fit_mode = config.get("box_fit_mode", "fit")  # "fit", "crop_fill", "crop_1_1", "crop_4_5"
    box_border_color = config.get("box_border_color", "white")  # "white", "gold", "black", "red", "cyan", "none"
    box_border_width = int(config.get("box_border_width", 6))  # pixels
    
    has_audio = video_info.get("has_audio", False)
    volume_boost = float(config.get("volume_boost", 1.15))
    anti_audio_hash = bool(config.get("anti_audio_hash", True))
    bgm_path = config.get("bgm_path", "").strip()
    bgm_volume = float(config.get("bgm_volume", 0.10))
    strip_metadata = bool(config.get("strip_metadata", True))
    crf = int(config.get("crf", 20))
    preset = config.get("preset", "fast")

    cmd = ["ffmpeg", "-y"]

    # Main Input
    cmd.extend(["-i", input_path])
    input_index = 1

    # Top/Bottom Split (Reaction / Meme Split) config
    enable_split = bool(config.get("enable_top_bottom_split", False))
    split_meme_path = config.get("split_meme_path", "").strip()
    split_layout = config.get("split_layout", "top_video")  # "top_video", "bottom_video", "split_50_50"
    split_bg_style = config.get("split_bg_style", "black")  # "black", "blur", "custom"
    split_custom_bg_path = config.get("split_custom_bg_path", "").strip()
    split_crop_align = config.get("split_crop_align", "center")  # "center", "top", "bottom", "manual"
    split_crop_y_pct = float(config.get("split_crop_y_pct", 50.0))  # 0.0 to 100.0%
    split_video_h_scale = float(config.get("split_video_h_scale", 0.50))
    split_meme_h_scale = float(config.get("split_meme_h_scale", 0.40))
    split_box_w_scale = float(config.get("split_box_w_scale", 0.96))
    split_video_fit = config.get("split_video_fit", "fit")  # "fit" (original aspect ratio) or "crop_fill"
    split_border_color = config.get("split_border_color", "white")  # "white", "gold", "black", "red", "cyan", "none"
    split_border_width = int(config.get("split_border_width", 6))
    split_border_target = config.get("split_border_target", "video_only")  # "video_only", "both", "between"
    split_audio_source = config.get("split_audio_source", "reel")

    # Top/Bottom Split Reaction Media Input
    has_split_meme = bool(enable_split and split_meme_path and os.path.exists(split_meme_path))
    split_meme_index = -1
    is_split_meme_video = False
    has_meme_audio = False
    if has_split_meme:
        is_split_meme_video = is_video_file(split_meme_path)
        if is_split_meme_video:
            cmd.extend(["-stream_loop", "-1", "-i", split_meme_path])
            try:
                m_info = get_video_info(split_meme_path)
                has_meme_audio = bool(m_info.get("has_audio", False))
            except Exception:
                has_meme_audio = False
        else:
            cmd.extend(["-loop", "1", "-i", split_meme_path])
        split_meme_index = input_index
        input_index += 1

    # Top/Bottom Split Custom Background Image Input
    has_split_bg = bool(enable_split and split_bg_style == "custom" and split_custom_bg_path and os.path.exists(split_custom_bg_path))
    split_bg_index = -1
    if has_split_bg:
        if is_video_file(split_custom_bg_path):
            cmd.extend(["-stream_loop", "-1", "-i", split_custom_bg_path])
        else:
            cmd.extend(["-loop", "1", "-i", split_custom_bg_path])
        split_bg_index = input_index
        input_index += 1

    # Custom background image or video template input
    has_custom_bg = bool(custom_bg_path and os.path.exists(custom_bg_path)) and not has_split_meme
    bg_img_index = -1
    is_custom_bg_vid = False
    if has_custom_bg:
        is_custom_bg_vid = is_video_file(custom_bg_path)
        if is_custom_bg_vid:
            # Video template: loop continuously
            cmd.extend(["-stream_loop", "-1", "-i", custom_bg_path])
        else:
            # Image template: loop static frame
            cmd.extend(["-loop", "1", "-i", custom_bg_path])
        bg_img_index = input_index
        input_index += 1

    # Watermark input
    wm_index = -1
    if watermark_path and os.path.exists(watermark_path):
        cmd.extend(["-i", watermark_path])
        wm_index = input_index
        input_index += 1

    # Background music input
    bgm_index = -1
    if bgm_path and os.path.exists(bgm_path):
        cmd.extend(["-stream_loop", "-1", "-i", bgm_path])
        bgm_index = input_index
        input_index += 1

    # 1. Base Video Filters (applied to source frames)
    base_v_filters = []

    # Speed
    if abs(speed - 1.0) > 0.001:
        base_v_filters.append(f"setpts={1.0 / speed:.6f}*PTS")

    # Flip horizontal (Mirror)
    if flip_h:
        base_v_filters.append("hflip")

    # Manual Edge / Margin Crop (to remove watermarks, borders, black bars)
    crop_top_pct = max(0.0, min(80.0, float(config.get("crop_top_pct", 0.0))))
    crop_bot_pct = max(0.0, min(80.0, float(config.get("crop_bot_pct", 0.0))))
    crop_left_pct = max(0.0, min(80.0, float(config.get("crop_left_pct", 0.0))))
    crop_right_pct = max(0.0, min(80.0, float(config.get("crop_right_pct", 0.0))))
    if (crop_top_pct + crop_bot_pct + crop_left_pct + crop_right_pct) > 0.001:
        w_factor = max(0.1, 1.0 - (crop_left_pct + crop_right_pct) / 100.0)
        h_factor = max(0.1, 1.0 - (crop_top_pct + crop_bot_pct) / 100.0)
        x_factor = crop_left_pct / 100.0
        y_factor = crop_top_pct / 100.0
        base_v_filters.append(
            f"crop=w=trunc(iw*{w_factor:.4f}/2)*2:h=trunc(ih*{h_factor:.4f}/2)*2:x=trunc(iw*{x_factor:.4f}/2)*2:y=trunc(ih*{y_factor:.4f}/2)*2"
        )

    # Zoom / Smart Crop
    if zoom_pct > 0.005:
        # Scale up slightly and crop back to original bounds to eliminate borders/signatures
        scale_factor = 1.0 + zoom_pct
        base_v_filters.append(f"scale=ceil(iw*{scale_factor:.4f}/2)*2:ceil(ih*{scale_factor:.4f}/2)*2")
        base_v_filters.append("crop=w=min(iw\\,ceil(iw/(1.0+0.001)/2)*2):h=min(ih\\,ceil(ih/(1.0+0.001)/2)*2)")

    # Color grading (alter frame hash and enhance visual appeal)
    if color_grade:
        # Slight boost in contrast (+4%), brightness (+1%), and saturation (+8%)
        base_v_filters.append("eq=contrast=1.04:brightness=0.01:saturation=1.08")

    # Vignette
    if vignette:
        base_v_filters.append("vignette=PI/7")

    # Assemble filter complex
    filter_complex_parts = []
    
    # Label for base modified video
    if base_v_filters:
        filter_complex_parts.append(f"[0:v]{','.join(base_v_filters)}[v_base]")
        current_v = "[v_base]"
    else:
        current_v = "[0:v]"

    # Aspect Ratio & Canvas Box Framing
    # Determine target canvas size
    if aspect_mode == "1_1_blur":
        canvas_w, canvas_h = 1080, 1080
    elif aspect_mode == "16_9_blur":
        canvas_w, canvas_h = 1920, 1080
    else:
        # Default to 9:16 Vertical Reel (1080x1920)
        canvas_w, canvas_h = 1080, 1920

    col_map = {
        "white": "white",
        "gold": "#ffcc00",
        "black": "black",
        "red": "#dc3545",
        "cyan": "#00e5ff"
    }

    fg_box_filters = []

    if enable_box_frame:
        # Calculate Box Frame parameters (Template/Custom Frame Box)
        target_box_w = max(160, (int(canvas_w * box_scale) // 2) * 2)
        target_box_h = max(160, (int(canvas_h * box_height_scale) // 2) * 2)

        box_crop_y_pct = max(0.0, min(100.0, float(config.get("box_crop_y_pct", 50.0))))
        box_crop_x_pct = max(0.0, min(100.0, float(config.get("box_crop_x_pct", 50.0))))
        fit_str = str(box_fit_mode).lower()

        if "1_1_fit" in fit_str or ("1:1" in fit_str or "square" in fit_str) and ("fit" in fit_str or "full" in fit_str or "পুরু" in fit_str or "পুরো" in fit_str or "নো" in fit_str):
            # 1:1 Square Box with Full 9:16 Video Fit (NO CROPPING)
            target_box_h = target_box_w
            fg_box_filters.append(
                f"scale={target_box_w}:{target_box_w}:force_original_aspect_ratio=decrease,"
                f"scale=trunc(iw/2)*2:trunc(ih/2)*2,"
                f"pad={target_box_w}:{target_box_w}:(ow-iw)/2:(oh-ih)/2:color=black"
            )
        elif "1_1" in fit_str or "1:1" in fit_str or "square" in fit_str:
            target_box_h = target_box_w
            fg_box_filters.append(
                f"scale={target_box_w}:{target_box_h}:force_original_aspect_ratio=increase,"
                f"crop={target_box_w}:{target_box_h}:(iw-ow)*{box_crop_x_pct/100.0:.3f}:(ih-oh)*{box_crop_y_pct/100.0:.3f}:exact=1"
            )
        elif "4_5" in fit_str or "4:5" in fit_str or "portrait" in fit_str:
            target_box_h = (int(target_box_w * 1.25) // 2) * 2
            fg_box_filters.append(
                f"scale={target_box_w}:{target_box_h}:force_original_aspect_ratio=increase,"
                f"crop={target_box_w}:{target_box_h}:(iw-ow)*{box_crop_x_pct/100.0:.3f}:(ih-oh)*{box_crop_y_pct/100.0:.3f}:exact=1"
            )
        elif "16_9" in fit_str or "16:9" in fit_str or "landscape" in fit_str:
            target_box_h = (int(target_box_w * 9 / 16) // 2) * 2
            fg_box_filters.append(
                f"scale={target_box_w}:{target_box_h}:force_original_aspect_ratio=increase,"
                f"crop={target_box_w}:{target_box_h}:(iw-ow)*{box_crop_x_pct/100.0:.3f}:(ih-oh)*{box_crop_y_pct/100.0:.3f}:exact=1"
            )
        elif "manual_fit" in fit_str or "custom_fit" in fit_str or ("fit" in fit_str and ("manual" in fit_str or "custom" in fit_str)):
            # Manual Custom Box with Full Video Fit inside (no video crop)
            fg_box_filters.append(
                f"scale={target_box_w}:{target_box_h}:force_original_aspect_ratio=decrease,"
                f"scale=trunc(iw/2)*2:trunc(ih/2)*2,"
                f"pad={target_box_w}:{target_box_h}:(ow-iw)/2:(oh-ih)/2:color=black"
            )
        elif "manual" in fit_str or "custom" in fit_str or "crop" in fit_str or "fill" in fit_str:
            # Manual / Fill Box: uses explicit target_box_w and target_box_h
            fg_box_filters.append(
                f"scale={target_box_w}:{target_box_h}:force_original_aspect_ratio=increase,"
                f"crop={target_box_w}:{target_box_h}:(iw-ow)*{box_crop_x_pct/100.0:.3f}:(ih-oh)*{box_crop_y_pct/100.0:.3f}:exact=1"
            )
        else:
            # Default: fit inside keeping video ratio
            fg_box_filters.append(f"scale={target_box_w}:{target_box_h}:force_original_aspect_ratio=decrease")

        fg_box_filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

        # Outer frame border (like the white box in screenshot)
        if box_border_color != "none" and box_border_width > 0:
            b_width = max(2, (box_border_width // 2) * 2)
            col_val = col_map.get(box_border_color, "white")
            fg_box_filters.append(f"pad=w=iw+{b_width*2}:h=ih+{b_width*2}:x={b_width}:y={b_width}:color={col_val}")

        pos_y_map = {
            "lower_center": "(H-h)*0.70",
            "center": "(H-h)/2",
            "upper_center": "(H-h)*0.30",
            "top_third": "(H-h)*0.35",
            "bottom_third": "(H-h)*0.65",
            "top": "40",
            "bottom": "H-h-40",
            "below_header": "H*0.13",
            "galaxy_hook": "648"
        }
        y_pos_str = str(int(custom_y)) if bg_video_pos == "custom" else pos_y_map.get(bg_video_pos, "(H-h)*0.53")

        # Horizontal (X) position
        if bg_video_pos_x == "right":
            x_pos_str = "W-w-20"
        elif bg_video_pos_x == "right_flush":
            x_pos_str = "W-w"
        elif bg_video_pos_x == "left":
            x_pos_str = "20"
        elif bg_video_pos_x == "left_flush":
            x_pos_str = "0"
        elif bg_video_pos_x == "custom":
            x_pos_str = str(int(custom_x))
        else:
            x_pos_str = "(W-w)/2"

    else:
        # Standard Canvas Fit (Box Frame is OFF)
        if aspect_mode == "9_16_blur_95":
            # 95% Video width & height, with remaining ambient blurred canvas acting as border (+ optional inner border)
            w_95 = (int(canvas_w * 0.95) // 2) * 2
            h_95 = (int(canvas_h * 0.95) // 2) * 2
            fg_box_filters.append(f"scale={w_95}:{h_95}:force_original_aspect_ratio=decrease")
            fg_box_filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

            # Border around the 95% video if chosen
            if box_border_color != "none" and box_border_width > 0:
                b_width = max(2, (box_border_width // 2) * 2)
                col_val = col_map.get(box_border_color, "white")
                fg_box_filters.append(f"pad=w=iw+{b_width*2}:h=ih+{b_width*2}:x={b_width}:y={b_width}:color={col_val}")

            y_pos_str = "(H-h)/2"
            x_pos_str = "(W-w)/2"

        elif aspect_mode in ("9_16_blur", "1_1_blur", "16_9_blur"):
            fg_box_filters.append(f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease")
            fg_box_filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
            y_pos_str = "(H-h)/2"
            x_pos_str = "(W-w)/2"

        else:
            fg_box_filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
            y_pos_str = "(H-h)/2"
            x_pos_str = "(W-w)/2"

    fg_box_str = ",".join(fg_box_filters)
    if fg_box_str:
        fg_box_str = f"{fg_box_str},"

    if has_split_meme:
        box_w = max(160, (int(canvas_w * split_box_w_scale) // 2) * 2)
        top_h = max(160, (int(canvas_h * split_video_h_scale) // 2) * 2)
        bot_h = max(160, (int(canvas_h * split_meme_h_scale) // 2) * 2)
        total_h = top_h + bot_h
        split_custom_y = config.get("split_custom_y", None)
        if split_custom_y is not None and str(split_custom_y).strip().isdigit():
            y_start = max(0, int(str(split_custom_y).strip()))
        else:
            y_start = max(0, (canvas_h - total_h) // 2)

        if has_split_bg:
            filter_complex_parts.append(
                f"[{split_bg_index}:v]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,crop={canvas_w}:{canvas_h}[canvas_bg]"
            )
            v_fg_source = current_v
        elif split_bg_style == "blur":
            filter_complex_parts.append(
                f"{current_v}split=2[v_split_bg][v_split_fg];"
                f"[v_split_bg]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,crop={canvas_w}:{canvas_h},boxblur=25:5[canvas_bg]"
            )
            v_fg_source = "[v_split_fg]"
        else:
            filter_complex_parts.append(
                f"color=c=black:s={canvas_w}x{canvas_h}:r={video_info.get('fps', 30.0)}[canvas_bg]"
            )
            v_fg_source = current_v

        has_b = (split_border_color != "none") and (split_border_width > 0)
        b_width = max(2, (split_border_width // 2) * 2) if has_b else 0
        b_col_val = col_map.get(split_border_color, "white")
        vw = video_info.get("width", 1080)
        vh = video_info.get("height", 1920)
        is_fill_or_manual = split_video_fit in ("crop_fill", "manual") or "manual" in str(split_video_fit).lower() or "crop" in str(split_video_fit).lower()
        if is_fill_or_manual:
            actual_v_h = top_h
        else:
            avail_w = max(100, box_w - (b_width * 2 if (has_b and split_border_target in ("video_only", "both")) else 0))
            avail_h = max(100, top_h - (b_width * 2 if (has_b and split_border_target in ("video_only", "both")) else 0))
            s = min(avail_w / max(1, vw), avail_h / max(1, vh))
            scaled_h = (int(vh * s) // 2) * 2
            actual_v_h = scaled_h + (b_width * 2 if (has_b and split_border_target in ("video_only", "both")) else 0)

        # Crop anchor y expression (top, center, bottom, or manual percentage slider)
        if split_crop_align == "top":
            y_mult = 0.0
        elif split_crop_align == "bottom":
            y_mult = 1.0
        elif split_crop_align == "manual" or "manual" in str(split_crop_align).lower() or "manual" in str(split_video_fit).lower():
            y_mult = min(1.0, max(0.0, split_crop_y_pct / 100.0))
        else:
            y_mult = 0.5
        crop_y_expr = f"(ih-oh)*{y_mult:.3f}"

        # Top Video filtering (Fit vs Crop + optional border)
        if has_b and split_border_target in ("video_only", "both"):
            v_inner_w = max(100, box_w - b_width * 2)
            v_inner_h = max(100, top_h - b_width * 2)
            if is_fill_or_manual:
                v_filter = (
                    f"{v_fg_source}scale={v_inner_w}:{v_inner_h}:force_original_aspect_ratio=increase,"
                    f"crop={v_inner_w}:{v_inner_h}:(iw-ow)/2:{crop_y_expr}:exact=1,"
                    f"pad=w=iw+{b_width*2}:h=ih+{b_width*2}:x={b_width}:y={b_width}:color={b_col_val}[top_v];"
                )
            else:
                # "fit" - keep original size / aspect ratio
                v_filter = (
                    f"{v_fg_source}scale={v_inner_w}:{v_inner_h}:force_original_aspect_ratio=decrease,"
                    f"scale=trunc(iw/2)*2:trunc(ih/2)*2,"
                    f"pad=w=iw+{b_width*2}:h=ih+{b_width*2}:x={b_width}:y={b_width}:color={b_col_val}[top_v];"
                )
        else:
            if is_fill_or_manual:
                v_filter = f"{v_fg_source}scale={box_w}:{top_h}:force_original_aspect_ratio=increase,crop={box_w}:{top_h}:(iw-ow)/2:{crop_y_expr}:exact=1[top_v];"
            else:
                # "fit" - keep original size / aspect ratio
                v_filter = f"{v_fg_source}scale={box_w}:{top_h}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2[top_v];"

        # Meme filtering (optional border if 'both')
        if has_b and split_border_target == "both":
            m_inner_w = max(100, box_w - b_width * 2)
            m_inner_h = max(100, bot_h - b_width * 2)
            m_filter = (
                f"[{split_meme_index}:v]scale={m_inner_w}:{m_inner_h}:force_original_aspect_ratio=increase,"
                f"crop={m_inner_w}:{m_inner_h}:exact=1,"
                f"pad=w=iw+{b_width*2}:h=ih+{b_width*2}:x={b_width}:y={b_width}:color={b_col_val}[bot_m]"
            )
        else:
            m_filter = f"[{split_meme_index}:v]scale={box_w}:{bot_h}:force_original_aspect_ratio=increase,crop={box_w}:{bot_h}:exact=1[bot_m]"

        filter_complex_parts.append(v_filter + m_filter)

        # Overlay positioning: video and meme touch directly with ZERO gap
        if split_layout == "bottom_video":
            filter_complex_parts.append(
                f"[canvas_bg][bot_m]overlay=(W-w)/2:{y_start}:shortest=1[tmp_split];"
                f"[tmp_split][top_v]overlay=(W-w)/2:{y_start + bot_h}:shortest=1[v_canvas]"
            )
        else:
            # Default: Top Video + Bottom Meme directly attached
            filter_complex_parts.append(
                f"[canvas_bg][top_v]overlay=(W-w)/2:{y_start}:shortest=1[tmp_split];"
                f"[tmp_split][bot_m]overlay=(W-w)/2:{y_start + actual_v_h}:shortest=1[v_canvas]"
            )

        if has_b and split_border_target == "between":
            y_div = y_start + (bot_h if split_layout == "bottom_video" else actual_v_h)
            filter_complex_parts.append(
                f"[v_canvas]drawbox=x={(canvas_w - box_w) // 2}:y={y_div - b_width//2}:w={box_w}:h={b_width}:color={b_col_val}:t=fill[v_canvas_div]"
            )
            current_v = "[v_canvas_div]"
        else:
            current_v = "[v_canvas]"

    elif has_custom_bg:
        filter_complex_parts.append(
            f"[{bg_img_index}:v]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,crop={canvas_w}:{canvas_h}[bg_canvas];"
            f"{current_v}{fg_box_str}null[fg_boxed];"
            f"[bg_canvas][fg_boxed]overlay={x_pos_str}:{y_pos_str}:shortest=1[v_canvas]"
        )
        current_v = "[v_canvas]"

    elif aspect_mode in ("9_16_blur", "9_16_blur_95"):
        filter_complex_parts.append(
            f"{current_v}split=2[b_bg][b_fg];"
            f"[b_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg_canvas];"
            f"[b_fg]{fg_box_str}null[fg_boxed];"
            f"[bg_canvas][fg_boxed]overlay={x_pos_str}:{y_pos_str}[v_canvas]"
        )
        current_v = "[v_canvas]"

    elif aspect_mode == "1_1_blur":
        filter_complex_parts.append(
            f"{current_v}split=2[sq_bg][sq_fg];"
            f"[sq_bg]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,boxblur=25:5[sq_canvas];"
            f"[sq_fg]{fg_box_str}null[fg_boxed];"
            f"[sq_canvas][fg_boxed]overlay=(W-w)/2:{y_pos_str}[v_canvas]"
        )
        current_v = "[v_canvas]"

    elif aspect_mode == "16_9_blur":
        filter_complex_parts.append(
            f"{current_v}split=2[ls_bg][ls_fg];"
            f"[ls_bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=25:5[ls_canvas];"
            f"[ls_fg]{fg_box_str}null[fg_boxed];"
            f"[ls_canvas][fg_boxed]overlay=(W-w)/2:{y_pos_str}[v_canvas]"
        )
        current_v = "[v_canvas]"

    elif aspect_mode == "9_16_crop":
        filter_complex_parts.append(
            f"{current_v}crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9),scale=1080:1920:flags=lanczos[v_crop]"
        )
        current_v = "[v_crop]"

    # Border filter
    if border != "none":
        border_color_map = {
            "white_3px": ("white", 3),
            "black_3px": ("black", 3),
            "gold_3px": ("#ffcc00", 3),
            "white_5px": ("white", 5),
            "gold_5px": ("#ffcc00", 5)
        }
        color_val, width_val = border_color_map.get(border, ("white", 3))
        filter_complex_parts.append(
            f"{current_v}drawbox=x=0:y=0:w=iw:h=ih:color={color_val}@0.9:t={width_val}[v_border]"
        )
        current_v = "[v_border]"

    # Watermark overlay (if present)
    if wm_index >= 0:
        pos_map = {
            "top_left": "20:20",
            "top_right": "W-w-20:20",
            "bottom_left": "20:H-h-20",
            "bottom_right": "W-w-20:H-h-20",
            "center": "(W-w)/2:(H-h)/2"
        }
        pos_str = pos_map.get(watermark_pos, "W-w-20:20")
        filter_complex_parts.append(
            f"[{wm_index}:v]scale=iw*0.25:-1[wm_scaled];"
            f"{current_v}[wm_scaled]overlay={pos_str}[v_wm]"
        )
        current_v = "[v_wm]"

    # Text Overlay / Hook banner
    if text_overlay:
        # Safe escape for FFmpeg drawtext
        clean_text = text_overlay.replace(":", "\:").replace("'", "\'").replace("%", "\%")
        local_font = os.path.join(os.path.dirname(__file__), "templates", "arial.ttf")
        if os.path.exists(local_font):
            font_full = local_font.replace("\\", "/")
        else:
            windir = os.environ.get("WINDIR", "C:/Windows").replace("\\", "/")
            font_full = f"{windir}/Fonts/arial.ttf"
        font_path = font_full.replace(":", "\\:")

        # Color mapping
        t_col_raw = str(text_color).lower()
        if "yellow" in t_col_raw or "হলুদ" in t_col_raw:
            fontcolor_val = "yellow"
        elif "white" in t_col_raw or "সাদা" in t_col_raw:
            fontcolor_val = "white"
        elif "red" in t_col_raw or "লাল" in t_col_raw:
            fontcolor_val = "red"
        elif "cyan" in t_col_raw or "আকাশি" in t_col_raw:
            fontcolor_val = "cyan"
        elif "green" in t_col_raw or "সবুজ" in t_col_raw:
            fontcolor_val = "#00ff66"
        elif "black" in t_col_raw or "কালো" in t_col_raw:
            fontcolor_val = "black"
        else:
            fontcolor_val = "yellow"

        # Fontsize
        try:
            f_size = int(str(text_fontsize).split("px")[0].split()[0].strip())
        except Exception:
            f_size = 54

        # Box background style
        t_box_raw = str(text_box_bg).lower()
        if "none" in t_box_raw or "ছাড়া" in t_box_raw:
            box_param = "box=0"
        elif "white" in t_box_raw or "সাদা" in t_box_raw:
            box_param = "box=1:boxcolor=white@0.90:boxborderw=14"
            if fontcolor_val == "white":
                fontcolor_val = "black"
        elif "red" in t_box_raw or "লাল" in t_box_raw:
            box_param = "box=1:boxcolor=red@0.85:boxborderw=14"
        else:
            box_param = "box=1:boxcolor=black@0.75:boxborderw=14"

        # Coordinates
        if text_custom_x is not None and str(text_custom_x).strip().lstrip("-").isdigit():
            cx = int(str(text_custom_x).strip())
            x_expr = f"{cx}-text_w/2"
        else:
            x_expr = "(w-text_w)/2"

        if text_custom_y is not None and str(text_custom_y).strip().lstrip("-").isdigit():
            cy = int(str(text_custom_y).strip())
            y_expr = f"{cy}-text_h/2"
        else:
            if has_split_meme:
                if y_start > 40:
                    y_expr = f"{y_start // 2}-text_h/2"
                else:
                    y_expr = "H*0.06"
            else:
                y_expr = "H*0.06" if text_position == "top" else ("H*0.88" if text_position == "bottom" else "(H-text_h)/2")

        filter_complex_parts.append(
            f"{current_v}drawtext=fontfile='{font_path}':text='{clean_text}':fontcolor={fontcolor_val}:"
            f"fontsize={f_size}:{box_param}:x={x_expr}:y={y_expr}[v_text]"
        )
        current_v = "[v_text]" 

    # Ensure even dimensions (required by libx264)
    filter_complex_parts.append(f"{current_v}scale=trunc(iw/2)*2:trunc(ih/2)*2[v_out]")

    # 2. Audio Processing Filters
    has_final_audio = False
    
    # Audio speed factor via atempo
    audio_filters = []
    if abs(speed - 1.0) > 0.001:
        # atempo only accepts values between 0.5 and 2.0
        s = speed
        while s > 2.0:
            audio_filters.append("atempo=2.0")
            s /= 2.0
        while s < 0.5:
            audio_filters.append("atempo=0.5")
            s /= 0.5
        audio_filters.append(f"atempo={s:.4f}")

    if volume_boost != 1.0:
        audio_filters.append(f"volume={volume_boost:.2f}")

    if anti_audio_hash:
        # Subtle parametric equalizer adjustment breaks automated audio fingerprinting
        audio_filters.append("equalizer=f=1200:t=q:w=1:g=0.6")

    audio_chain_str = ",".join(audio_filters) if audio_filters else "anull"

    # Normalize split_audio_source: 'reel', 'meme', 'mix', or 'mute'
    sp_audio_mode = str(split_audio_source).lower()
    if "mute" in sp_audio_mode or "মিউট" in sp_audio_mode:
        aud_choice = "mute"
    elif "meme" in sp_audio_mode or "মেম" in sp_audio_mode:
        aud_choice = "meme"
    elif "mix" in sp_audio_mode or "both" in sp_audio_mode or "মিক্স" in sp_audio_mode:
        aud_choice = "mix"
    else:
        aud_choice = "reel"

    if aud_choice == "mute":
        has_final_audio = False
        audio_map = None

    elif aud_choice == "meme" and has_meme_audio:
        # User explicitly requested Meme audio and Meme video has audio stream
        if bgm_index >= 0:
            filter_complex_parts.append(
                f"[{split_meme_index}:a]{audio_chain_str}[a_meme];"
                f"[{bgm_index}:a]volume={bgm_volume:.2f}[a_bgm];"
                f"[a_meme][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
        else:
            filter_complex_parts.append(f"[{split_meme_index}:a]{audio_chain_str}[a_out]")
        has_final_audio = True
        audio_map = "[a_out]"

    elif aud_choice == "mix" and has_audio and has_meme_audio:
        # Mix Reel + Meme audio
        if bgm_index >= 0:
            filter_complex_parts.append(
                f"[0:a]{audio_chain_str}[a_reel];"
                f"[{split_meme_index}:a]volume=1.0[a_meme];"
                f"[{bgm_index}:a]volume={bgm_volume:.2f}[a_bgm];"
                f"[a_reel][a_meme][a_bgm]amix=inputs=3:duration=first:dropout_transition=2[a_out]"
            )
        else:
            filter_complex_parts.append(
                f"[0:a]{audio_chain_str}[a_reel];"
                f"[{split_meme_index}:a]volume=1.0[a_meme];"
                f"[a_reel][a_meme]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
        has_final_audio = True
        audio_map = "[a_out]"

    elif aud_choice == "mix" and has_meme_audio and not has_audio:
        # Reel has no audio, but meme video has audio
        if bgm_index >= 0:
            filter_complex_parts.append(
                f"[{split_meme_index}:a]{audio_chain_str}[a_meme];"
                f"[{bgm_index}:a]volume={bgm_volume:.2f}[a_bgm];"
                f"[a_meme][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
        else:
            filter_complex_parts.append(f"[{split_meme_index}:a]{audio_chain_str}[a_out]")
        has_final_audio = True
        audio_map = "[a_out]"

    elif has_audio:
        # Reel sound (or fallback if meme was requested but meme is static image / silent)
        if bgm_index >= 0:
            filter_complex_parts.append(
                f"[0:a]{audio_chain_str}[a_orig];"
                f"[{bgm_index}:a]volume={bgm_volume:.2f}[a_bgm];"
                f"[a_orig][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
        else:
            filter_complex_parts.append(f"[0:a]{audio_chain_str}[a_out]")
        has_final_audio = True
        audio_map = "[a_out]"

    elif bgm_index >= 0:
        filter_complex_parts.append(f"[{bgm_index}:a]volume={bgm_volume:.2f}[a_out]")
        has_final_audio = True
        audio_map = "[a_out]"

    elif has_meme_audio:
        # Reel has no audio, but meme video has audio
        filter_complex_parts.append(f"[{split_meme_index}:a]{audio_chain_str}[a_out]")
        has_final_audio = True
        audio_map = "[a_out]"

    else:
        has_final_audio = False
        audio_map = None

    # Add filter complex to command
    full_filter_str = ";".join(filter_complex_parts)
    cmd.extend(["-filter_complex", full_filter_str])
    cmd.extend(["-map", "[v_out]"])
    if has_final_audio and audio_map:
        cmd.extend(["-map", audio_map])

    # Video Encoding Options
    cmd.extend([
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart"
    ])

    # Audio Encoding Options
    if has_final_audio:
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100"
        ])
    else:
        cmd.append("-an")

    # Strip metadata completely to erase original camera/software footprints
    if strip_metadata:
        cmd.extend(["-map_metadata", "-1"])

    if has_custom_bg or has_split_meme:
        cmd.append("-shortest")

    # Output file
    cmd.append(output_path)

    return cmd, expected_duration

def process_single_video(
    input_path: str,
    output_path: str,
    config: Dict[str, Any],
    progress_callback: Optional[Callable[[float, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None
) -> Dict[str, Any]:
    """
    Executes FFmpeg on a single video file, tracking progress in real-time.
    """
    result = {
        "success": False,
        "error": "",
        "input_path": input_path,
        "output_path": output_path,
        "duration": 0.0,
        "size": 0,
        "size_str": "0 B"
    }

    if cancel_check and cancel_check():
        result["error"] = "Process cancelled by user."
        return result

    # Check input
    if not os.path.exists(input_path):
        result["error"] = "Input file not found."
        return result

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Probe input
    video_info = get_video_info(input_path)
    if not video_info.get("valid"):
        result["error"] = "Invalid or unreadable video file."
        return result

    # Build command
    cmd, expected_duration = build_ffmpeg_command(input_path, output_path, config, video_info)
    
    # Insert progress tracking args & suppress stats deadlock
    progress_cmd = list(cmd)
    progress_cmd.insert(1, "-nostats")
    progress_cmd.insert(2, "-loglevel")
    progress_cmd.insert(3, "error")
    progress_cmd.insert(4, "-progress")
    progress_cmd.insert(5, "pipe:1")

    total_us = expected_duration * 1_000_000.0 if expected_duration > 0 else 1.0

    try:
        # Launch FFmpeg process with hidden console window on Windows
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            progress_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            startupinfo=startupinfo,
            bufsize=1
        )

        stderr_lines = []
        err_thread = threading.Thread(
            target=lambda: [stderr_lines.append(l) for l in process.stderr],
            daemon=True
        )
        err_thread.start()

        last_percent = 0.0
        while True:
            if cancel_check and cancel_check():
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except Exception:
                    process.kill()
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except Exception:
                        pass
                result["error"] = "Processing cancelled."
                return result

            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue

            line = line.strip()
            if line.startswith("out_time_us="):
                try:
                    time_us = float(line.split("=")[1].strip())
                    pct = min(99.0, max(0.0, (time_us / total_us) * 100.0))
                    if pct - last_percent >= 1.0:
                        last_percent = pct
                        if progress_callback:
                            progress_callback(pct, f"Encoding: {pct:.0f}%")
                except Exception:
                    pass
            elif line.startswith("progress=end"):
                break

        process.wait()
        err_thread.join(timeout=1.0)
        return_code = process.returncode

        if return_code == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            result["success"] = True
            result["size"] = os.path.getsize(output_path)
            result["size_str"] = format_size(result["size"])
            result["duration"] = expected_duration
            if progress_callback:
                progress_callback(100.0, "Completed 100%")
        else:
            result["success"] = False
            err_snippet = "".join(stderr_lines)[-800:] if stderr_lines else "Unknown FFmpeg error"
            result["error"] = f"FFmpeg failed with code {return_code}: {err_snippet}"
            try:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_render_error.log"), "w", encoding="utf-8") as f_err:
                    f_err.write(f"Return code: {return_code}\n\nStderr:\n" + "".join(stderr_lines))
            except Exception:
                pass
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass

    except Exception as e:
        import traceback
        result["success"] = False
        result["error"] = str(e)
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_render_error.log"), "w", encoding="utf-8") as f_err:
                f_err.write("Exception:\n" + traceback.format_exc())
        except Exception:
            pass

    return result

def _draw_preview_text(canvas_im, config, canvas_w=1080, canvas_h=1920, enable_split=False, y_start=0):
    from PIL import Image, ImageDraw, ImageFont
    text_overlay = config.get("text_overlay", "").strip()
    if not text_overlay:
        return canvas_im

    t_size = 54
    try:
        t_size = int(str(config.get("text_fontsize", 54)).split("px")[0].split()[0].strip())
    except Exception:
        t_size = 54

    font = None
    local_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "arial.ttf")
    font_candidates = [
        local_font,
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    for fc in font_candidates:
        if os.path.exists(fc):
            try:
                font = ImageFont.truetype(fc, t_size)
                break
            except Exception:
                pass
    if not font:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    t_cx = config.get("text_custom_x", None)
    t_cy = config.get("text_custom_y", None)

    if t_cx is not None and str(t_cx).strip().lstrip("-").isdigit():
        cx = int(str(t_cx).strip())
    else:
        cx = canvas_w // 2

    if t_cy is not None and str(t_cy).strip().lstrip("-").isdigit():
        cy = int(str(t_cy).strip())
    else:
        if enable_split and y_start > 40:
            cy = y_start // 2
        else:
            t_pos = config.get("text_position", "top")
            cy = int(canvas_h * 0.08) if t_pos == "top" else (int(canvas_h * 0.90) if t_pos == "bottom" else canvas_h // 2)

    try:
        bbox = font.getbbox(text_overlay)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw = len(text_overlay) * (t_size // 2)
        th = t_size

    pad_x, pad_y = 22, 14
    x0 = cx - tw // 2 - pad_x
    y0 = cy - th // 2 - pad_y
    x1 = cx + tw // 2 + pad_x
    y1 = cy + th // 2 + pad_y

    box_bg_raw = str(config.get("text_box_bg", "black_box")).lower()
    if "none" in box_bg_raw or "ছাড়া" in box_bg_raw:
        bg_rgba = None
    elif "white" in box_bg_raw or "সাদা" in box_bg_raw:
        bg_rgba = (255, 255, 255, 235)
    elif "red" in box_bg_raw or "লাল" in box_bg_raw:
        bg_rgba = (220, 20, 40, 225)
    else:
        bg_rgba = (0, 0, 0, 210)

    if bg_rgba:
        overlay = Image.new("RGBA", canvas_im.size, (0, 0, 0, 0))
        d_over = ImageDraw.Draw(overlay)
        d_over.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=bg_rgba)
        canvas_im.paste(overlay, (0, 0), overlay)

    t_col_raw = str(config.get("text_color", "yellow")).lower()
    col_map = {
        "yellow": (255, 240, 0),
        "white": (255, 255, 255),
        "red": (255, 50, 50),
        "cyan": (0, 235, 255),
        "green": (0, 255, 100),
        "black": (0, 0, 0),
    }
    fill_col = (255, 240, 0)
    for k, v in col_map.items():
        if k in t_col_raw:
            fill_col = v
            break
    if bg_rgba and bg_rgba[0] > 200 and bg_rgba[1] > 200 and bg_rgba[2] > 200 and fill_col == (255, 255, 255):
        fill_col = (0, 0, 0)

    draw = ImageDraw.Draw(canvas_im)
    draw.text((cx, cy), text_overlay, font=font, fill=fill_col, anchor="mm")
    return canvas_im

def generate_layout_preview(
    config: Dict[str, Any],
    video_path: Optional[str] = None,
    preview_size: tuple[int, int] = (360, 640)
) -> Any:
    """
    Generates a PIL Image composite preview of the background template and video box.
    Used for instant layout verification in GUI before bulk processing.
    """
    from PIL import Image, ImageDraw

    canvas_w, canvas_h = 1080, 1920
    enable_split = bool(config.get("enable_top_bottom_split", False))
    split_meme_path = config.get("split_meme_path", "").strip()

    if enable_split and split_meme_path and os.path.exists(split_meme_path):
        split_layout = config.get("split_layout", "top_video")
        split_bg_style = config.get("split_bg_style", "black")
        split_video_h_scale = float(config.get("split_video_h_scale", 0.50))
        split_meme_h_scale = float(config.get("split_meme_h_scale", 0.40))
        split_box_w_scale = float(config.get("split_box_w_scale", 0.96))

        box_w = max(160, (int(canvas_w * split_box_w_scale) // 2) * 2)
        top_h = max(160, (int(canvas_h * split_video_h_scale) // 2) * 2)
        bot_h = max(160, (int(canvas_h * split_meme_h_scale) // 2) * 2)
        total_h = top_h + bot_h
        split_custom_y = config.get("split_custom_y", None)
        if split_custom_y is not None and str(split_custom_y).strip().isdigit():
            y_start = max(0, int(str(split_custom_y).strip()))
        else:
            y_start = max(0, (canvas_h - total_h) // 2)
        x_pos = (canvas_w - box_w) // 2

        # Base canvas
        split_custom_bg_path = config.get("split_custom_bg_path", "").strip()
        split_crop_align = config.get("split_crop_align", "center")
        split_crop_y_pct = float(config.get("split_crop_y_pct", 50.0))

        if split_bg_style == "custom" and split_custom_bg_path and os.path.exists(split_custom_bg_path):
            try:
                raw_bg = Image.open(split_custom_bg_path).convert("RGB")
                s_bg = max(canvas_w / raw_bg.width, canvas_h / raw_bg.height)
                nw, nh = int(raw_bg.width * s_bg), int(raw_bg.height * s_bg)
                raw_bg = raw_bg.resize((nw, nh), Image.Resampling.LANCZOS)
                xc, yc = (nw - canvas_w) // 2, (nh - canvas_h) // 2
                canvas_im = raw_bg.crop((xc, yc, xc + canvas_w, yc + canvas_h))
            except Exception:
                canvas_im = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        elif split_bg_style == "blur" and video_path and os.path.exists(video_path):
            try:
                import tempfile
                tmp_bg = os.path.join(tempfile.gettempdir(), f"prev_bg_{os.getpid()}.png")
                cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", video_path, "-vframes", "1", tmp_bg]
                subprocess.run(cmd, timeout=3.0)
                if os.path.exists(tmp_bg):
                    raw_bg = Image.open(tmp_bg).convert("RGB")
                    os.remove(tmp_bg)
                    from PIL import ImageFilter
                    canvas_im = raw_bg.resize((canvas_w, canvas_h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=25))
                else:
                    canvas_im = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
            except Exception:
                canvas_im = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        else:
            canvas_im = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))

        split_video_fit = config.get("split_video_fit", "fit")
        split_border_color = config.get("split_border_color", "white")
        split_border_width = int(config.get("split_border_width", 6))
        split_border_target = config.get("split_border_target", "video_only")

        has_b = (split_border_color != "none") and (split_border_width > 0)
        b_w = max(2, (split_border_width // 2) * 2) if has_b else 0
        b_rgb_map = {
            "white": (255, 255, 255),
            "gold": (255, 204, 0),
            "black": (0, 0, 0),
            "red": (220, 53, 69),
            "cyan": (0, 229, 255)
        }
        b_col_rgb = b_rgb_map.get(split_border_color, (255, 255, 255))

        # Top Video Frame
        fg_frame = None
        if video_path and os.path.exists(video_path):
            import tempfile
            tmp_fg = os.path.join(tempfile.gettempdir(), f"prev_fg_{os.getpid()}.png")
            try:
                cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", video_path, "-vframes", "1", tmp_fg]
                subprocess.run(cmd, timeout=3.0)
                if os.path.exists(tmp_fg):
                    fg_frame = Image.open(tmp_fg).convert("RGB")
                    os.remove(tmp_fg)
            except Exception:
                pass

        avail_w = box_w - (b_w * 2 if (has_b and split_border_target in ("video_only", "both")) else 0)
        avail_h = top_h - (b_w * 2 if (has_b and split_border_target in ("video_only", "both")) else 0)

        if fg_frame is None:
            fg_frame = Image.new("RGB", (avail_w, avail_h), (50, 75, 120))
            d_s = ImageDraw.Draw(fg_frame)
            d_s.text((avail_w//2, avail_h//2), "[ Top Video Frame ]", fill='white', anchor='mm')
        else:
            # Edge margin trimming
            crop_top_pct = max(0.0, min(45.0, float(config.get("crop_top_pct", 0.0))))
            crop_bot_pct = max(0.0, min(45.0, float(config.get("crop_bot_pct", 0.0))))
            crop_left_pct = max(0.0, min(45.0, float(config.get("crop_left_pct", 0.0))))
            crop_right_pct = max(0.0, min(45.0, float(config.get("crop_right_pct", 0.0))))
            if (crop_top_pct + crop_bot_pct + crop_left_pct + crop_right_pct) > 0.001:
                cur_w, cur_h = fg_frame.width, fg_frame.height
                c_l = int(cur_w * (crop_left_pct / 100.0))
                c_r = int(cur_w * (crop_right_pct / 100.0))
                c_t = int(cur_h * (crop_top_pct / 100.0))
                c_b = int(cur_h * (crop_bot_pct / 100.0))
                fg_frame = fg_frame.crop((c_l, c_t, max(c_l + 10, cur_w - c_r), max(c_t + 10, cur_h - c_b)))

            is_fill_or_manual = split_video_fit in ("crop_fill", "manual") or "manual" in str(split_video_fit).lower() or "crop" in str(split_video_fit).lower()
            if is_fill_or_manual:
                s_fg = max(avail_w / fg_frame.width, avail_h / fg_frame.height)
                n_w, n_h = max(avail_w, int(fg_frame.width * s_fg)), max(avail_h, int(fg_frame.height * s_fg))
                fg_frame = fg_frame.resize((n_w, n_h), Image.Resampling.LANCZOS)
                x_c = (n_w - avail_w) // 2

                if split_crop_align == "top":
                    y_mult = 0.0
                elif split_crop_align == "bottom":
                    y_mult = 1.0
                elif split_crop_align == "manual" or "manual" in str(split_crop_align).lower() or "manual" in str(split_video_fit).lower():
                    y_mult = min(1.0, max(0.0, split_crop_y_pct / 100.0))
                else:
                    y_mult = 0.5

                y_c = int(max(0, n_h - avail_h) * y_mult)
                y_c = min(max(0, y_c), max(0, n_h - avail_h))
                fg_frame = fg_frame.crop((x_c, y_c, x_c + avail_w, y_c + avail_h))
            else:
                s_fg = min(avail_w / fg_frame.width, avail_h / fg_frame.height)
                n_w, n_h = max(2, int(fg_frame.width * s_fg)), max(2, int(fg_frame.height * s_fg))
                fg_frame = fg_frame.resize((n_w, n_h), Image.Resampling.LANCZOS)

        if has_b and split_border_target in ("video_only", "both"):
            from PIL import ImageOps
            fg_frame = ImageOps.expand(fg_frame, border=b_w, fill=b_col_rgb)

        # Meme Frame
        meme_frame = None
        if is_video_file(split_meme_path):
            import tempfile
            tmp_m = os.path.join(tempfile.gettempdir(), f"prev_m_{os.getpid()}.png")
            try:
                cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", split_meme_path, "-vframes", "1", tmp_m]
                subprocess.run(cmd, timeout=3.0)
                if os.path.exists(tmp_m):
                    meme_frame = Image.open(tmp_m).convert("RGB")
                    os.remove(tmp_m)
            except Exception:
                pass
        else:
            try:
                meme_frame = Image.open(split_meme_path).convert("RGB")
            except Exception:
                pass

        if meme_frame is None:
            meme_frame = Image.new("RGB", (box_w, bot_h), (180, 50, 70))
            d_m = ImageDraw.Draw(meme_frame)
            d_m.text((box_w//2, bot_h//2), "[ Reaction Meme Frame ]", fill='white', anchor='mm')
        else:
            s_m = max(box_w / meme_frame.width, bot_h / meme_frame.height)
            n_w2, n_h2 = max(box_w, int(meme_frame.width * s_m)), max(bot_h, int(meme_frame.height * s_m))
            meme_frame = meme_frame.resize((n_w2, n_h2), Image.Resampling.LANCZOS)
            x_c2, y_c2 = (n_w2 - box_w) // 2, (n_h2 - bot_h) // 2
            meme_frame = meme_frame.crop((x_c2, y_c2, x_c2 + box_w, y_c2 + bot_h))

        if has_b and split_border_target == "both":
            from PIL import ImageOps
            meme_frame = ImageOps.expand(meme_frame, border=b_w, fill=b_col_rgb)

        # Centered paste for top_v inside top_h slot
        fg_x = x_pos + (box_w - fg_frame.width) // 2
        m_x = x_pos + (box_w - meme_frame.width) // 2

        if split_layout == "bottom_video":
            canvas_im.paste(meme_frame, (m_x, y_start))
            fg_y = y_start + bot_h
            canvas_im.paste(fg_frame, (fg_x, fg_y))
        else:
            fg_y = y_start
            canvas_im.paste(fg_frame, (fg_x, fg_y))
            canvas_im.paste(meme_frame, (m_x, fg_y + fg_frame.height))

        if has_b and split_border_target == "between":
            d_line = ImageDraw.Draw(canvas_im)
            y_div = y_start + (bot_h if split_layout == "bottom_video" else fg_frame.height)
            d_line.rectangle([x_pos, y_div - b_w // 2, x_pos + box_w, y_div - b_w // 2 + b_w], fill=b_col_rgb)

        canvas_im = _draw_preview_text(canvas_im, config, canvas_w=canvas_w, canvas_h=canvas_h, enable_split=True, y_start=y_start)

        if preview_size:
            return canvas_im.resize(preview_size, Image.Resampling.LANCZOS)
        return canvas_im

    custom_bg = config.get("custom_bg_path", "").strip()

    if custom_bg and os.path.exists(custom_bg):
        try:
            if is_video_file(custom_bg):
                import tempfile
                tmp_bg_png = os.path.join(tempfile.gettempdir(), f"preview_bg_frame_{os.getpid()}.png")
                cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", custom_bg, "-vframes", "1", tmp_bg_png]
                subprocess.run(cmd, timeout=4.0)
                if os.path.exists(tmp_bg_png) and os.path.getsize(tmp_bg_png) > 500:
                    bg_im = Image.open(tmp_bg_png).convert("RGB")
                    try:
                        os.remove(tmp_bg_png)
                    except Exception:
                        pass
                else:
                    bg_im = Image.new("RGB", (canvas_w, canvas_h), (252, 182, 175))
            else:
                bg_im = Image.open(custom_bg).convert("RGB")

            bg_w, bg_h = bg_im.size
            scale = max(canvas_w / bg_w, canvas_h / bg_h)
            new_w, new_h = int(bg_w * scale), int(bg_h * scale)
            bg_scaled = bg_im.resize((new_w, new_h), Image.Resampling.LANCZOS)
            x_crop = max(0, (new_w - canvas_w) // 2)
            y_crop = max(0, (new_h - canvas_h) // 2)
            canvas_im = bg_scaled.crop((x_crop, y_crop, x_crop + canvas_w, y_crop + canvas_h))
        except Exception:
            canvas_im = Image.new("RGB", (canvas_w, canvas_h), (252, 182, 175))
    else:
        # Fallback stylish dark canvas
        canvas_im = Image.new("RGB", (canvas_w, canvas_h), (24, 28, 36))

    box_scale = float(config.get("box_scale", 0.60))
    box_h_scale = float(config.get("box_height_scale", 0.85))
    target_w = max(160, int(canvas_w * box_scale))

    fit_mode = str(config.get("box_fit_mode", "crop_fill")).lower()
    if "1:1" in fit_mode or "square" in fit_mode or "1_1" in fit_mode:
        target_h = target_w
    elif "4:5" in fit_mode or "4_5" in fit_mode or "portrait" in fit_mode:
        target_h = (int(target_w * 1.25) // 2) * 2
    elif "16:9" in fit_mode or "16_9" in fit_mode or "landscape" in fit_mode:
        target_h = (int(target_w * 9 / 16) // 2) * 2
    elif "manual_fit" in fit_mode or "custom_fit" in fit_mode or ("fit" in fit_mode and ("manual" in fit_mode or "custom" in fit_mode)):
        target_h = max(160, (int(canvas_h * box_h_scale) // 2) * 2)
    elif "manual" in fit_mode or "custom" in fit_mode:
        target_h = max(160, (int(canvas_h * box_h_scale) // 2) * 2)
    elif "crop" in fit_mode or "fill" in fit_mode:
        target_h = max(160, (int(canvas_h * box_h_scale) // 2) * 2)
    elif "fit" in fit_mode and "full" not in fit_mode:
        target_h = max(160, (int(canvas_h * box_h_scale) // 2) * 2) if "box_height_scale" in config else min(canvas_h - 40, (int(target_w * 16 / 9) // 2) * 2)
    else:
        target_h = max(160, int(canvas_h * box_h_scale))

    pos_x = config.get("bg_video_pos_x", "center")
    if pos_x == "right":
        x = canvas_w - target_w - 20
    elif pos_x == "right_flush":
        x = canvas_w - target_w
    elif pos_x == "left":
        x = 20
    elif pos_x == "left_flush":
        x = 0
    elif pos_x == "custom":
        x = int(config.get("custom_x", 0))
    else:
        x = (canvas_w - target_w) // 2

    pos_y = config.get("bg_video_pos", "below_header")
    pos_y_map = {
        "below_header": int(canvas_h * 0.13),
        "center": (canvas_h - target_h) // 2,
        "lower_center": int((canvas_h - target_h) * 0.70),
        "upper_center": int((canvas_h - target_h) * 0.30),
        "top": 40,
        "bottom": max(0, canvas_h - target_h - 40),
        "galaxy_hook": 648
    }
    if pos_y == "custom":
        y = int(config.get("custom_y", 0))
    else:
        y = pos_y_map.get(pos_y, (canvas_h - target_h) // 2)

    # Frame extraction or placeholder
    fg_frame = None
    if video_path and os.path.exists(video_path):
        import tempfile
        tmp_png = os.path.join(tempfile.gettempdir(), f"preview_frame_{os.getpid()}.png")
        try:
            cmd = ["ffmpeg", "-y", "-v", "error", "-ss", "0.5", "-i", video_path, "-vframes", "1", tmp_png]
            subprocess.run(cmd, timeout=4.0)
            if os.path.exists(tmp_png) and os.path.getsize(tmp_png) > 500:
                fg_frame = Image.open(tmp_png).convert("RGB")
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_png):
                try:
                    os.remove(tmp_png)
                except Exception:
                    pass

    if fg_frame is None:
        fg_frame = Image.new("RGB", (target_w, target_h), (35, 45, 65))
        d_sample = ImageDraw.Draw(fg_frame)
        d_sample.rectangle([10, 10, target_w - 10, target_h - 10], outline=(70, 130, 240), width=3)
        d_sample.text((target_w // 2, target_h // 2), "[ Sample Video Frame ]", fill=(255, 255, 255), anchor="mm")
    else:
        # Apply manual edge / margin crop (crop_top_pct, crop_bot_pct, crop_left_pct, crop_right_pct)
        c_top = max(0.0, min(80.0, float(config.get("crop_top_pct", 0.0))))
        c_bot = max(0.0, min(80.0, float(config.get("crop_bot_pct", 0.0))))
        c_left = max(0.0, min(80.0, float(config.get("crop_left_pct", 0.0))))
        c_right = max(0.0, min(80.0, float(config.get("crop_right_pct", 0.0))))
        if (c_top + c_bot + c_left + c_right) > 0.001:
            cw, ch = fg_frame.size
            cl = int(cw * (c_left / 100.0))
            cr = int(cw * (c_right / 100.0))
            ct = int(ch * (c_top / 100.0))
            cb = int(ch * (c_bot / 100.0))
            fg_frame = fg_frame.crop((cl, ct, max(cl + 10, cw - cr), max(ct + 10, ch - cb)))

        fit_mode = str(config.get("box_fit_mode", "crop_fill")).lower()
        fw, fh = fg_frame.size
        box_crop_y_pct = max(0.0, min(100.0, float(config.get("box_crop_y_pct", 50.0))))
        box_crop_x_pct = max(0.0, min(100.0, float(config.get("box_crop_x_pct", 50.0))))

        if "1_1_fit" in fit_mode or ("1:1" in fit_mode or "square" in fit_mode) and ("fit" in fit_mode or "full" in fit_mode or "পুরু" in fit_mode or "পুরো" in fit_mode or "নো" in fit_mode):
            target_h = target_w  # 1:1 Square Box
            s = min(target_w / fw, target_h / fh)
            nw, nh = max(2, int(fw * s)), max(2, int(fh * s))
            fg_resized = fg_frame.resize((nw, nh), Image.Resampling.LANCZOS)
            sq_frame = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            sq_frame.paste(fg_resized, ((target_w - nw) // 2, (target_h - nh) // 2))
            fg_frame = sq_frame

        elif "1_1" in fit_mode or "square" in fit_mode:
            target_h = target_w
            s = max(target_w / fw, target_h / fh)
            nw, nh = max(target_w, int(fw * s)), max(target_h, int(fh * s))
            fg_frame = fg_frame.resize((nw, nh), Image.Resampling.LANCZOS)
            xc = int(max(0, nw - target_w) * (box_crop_x_pct / 100.0))
            xc = min(max(0, xc), max(0, nw - target_w))
            yc = int(max(0, nh - target_h) * (box_crop_y_pct / 100.0))
            yc = min(max(0, yc), max(0, nh - target_h))
            fg_frame = fg_frame.crop((xc, yc, xc + target_w, yc + target_h))

        elif "4_5" in fit_mode or "4:5" in fit_mode or "portrait" in fit_mode:
            target_h = (int(target_w * 1.25) // 2) * 2
            s = max(target_w / fw, target_h / fh)
            nw, nh = max(target_w, int(fw * s)), max(target_h, int(fh * s))
            fg_frame = fg_frame.resize((nw, nh), Image.Resampling.LANCZOS)
            xc = int(max(0, nw - target_w) * (box_crop_x_pct / 100.0))
            xc = min(max(0, xc), max(0, nw - target_w))
            yc = int(max(0, nh - target_h) * (box_crop_y_pct / 100.0))
            yc = min(max(0, yc), max(0, nh - target_h))
            fg_frame = fg_frame.crop((xc, yc, xc + target_w, yc + target_h))

        elif "manual_fit" in fit_mode or "custom_fit" in fit_mode or ("fit" in fit_mode and ("manual" in fit_mode or "custom" in fit_mode)):
            s = min(target_w / fw, target_h / fh)
            nw, nh = max(2, int(fw * s)), max(2, int(fh * s))
            fg_resized = fg_frame.resize((nw, nh), Image.Resampling.LANCZOS)
            bg_pad = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            bg_pad.paste(fg_resized, ((target_w - nw) // 2, (target_h - nh) // 2))
            fg_frame = bg_pad

        elif "manual" in fit_mode or "custom" in fit_mode or "crop" in fit_mode or "fill" in fit_mode:
            s = max(target_w / fw, target_h / fh)
            nw, nh = max(target_w, int(fw * s)), max(target_h, int(fh * s))
            fg_frame = fg_frame.resize((nw, nh), Image.Resampling.LANCZOS)
            xc = int(max(0, nw - target_w) * (box_crop_x_pct / 100.0))
            xc = min(max(0, xc), max(0, nw - target_w))
            yc = int(max(0, nh - target_h) * (box_crop_y_pct / 100.0))
            yc = min(max(0, yc), max(0, nh - target_h))
            fg_frame = fg_frame.crop((xc, yc, xc + target_w, yc + target_h))

        else:
            s = min(target_w / fw, target_h / fh)
            nw, nh = max(2, int(fw * s)), max(2, int(fh * s))
            fg_frame = fg_frame.resize((nw, nh), Image.Resampling.LANCZOS)
            target_w, target_h = nw, nh

    border_col = config.get("box_border_color", "none")
    border_w = int(config.get("box_border_width", 0))
    if border_col != "none" and border_w > 0:
        d_b = ImageDraw.Draw(fg_frame)
        col_rgb = (255, 255, 255) if border_col == "white" else ((255, 204, 0) if border_col == "gold" else (0, 0, 0))
        d_b.rectangle([0, 0, fg_frame.width - 1, fg_frame.height - 1], outline=col_rgb, width=border_w)

    canvas_im.paste(fg_frame, (x, y))

    canvas_im = _draw_preview_text(canvas_im, config, canvas_w=canvas_w, canvas_h=canvas_h, enable_split=False, y_start=y)

    if preview_size:
        return canvas_im.resize(preview_size, Image.Resampling.LANCZOS)
    return canvas_im
