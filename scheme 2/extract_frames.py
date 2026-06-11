import subprocess
from pathlib import Path

# ==========================================
# 配置
# ==========================================
# VIDEO_INPUT 可以是：
#   1. 单个视频文件路径，如 "D:/videos/abc.mp4"
#   2. 视频文件夹路径，如 "D:/videos/"（会处理文件夹内所有视频）
VIDEO_INPUT = "D:/vs workspace/scheme 2/bilibili_link/【校园自制短片】浙江省一等奖作品 初中学生自制！学生低成本制作能拍成什么样？.mp4"
FRAMES_DIR  = "D:/vs workspace/scheme 2/bilibili_frames"
FRAME_RATE  = 1   # 每秒抽几帧（0.5 = 每2秒1帧，2 = 每秒2帧）
# ==========================================

VIDEO_EXTENSIONS = {".mp4", ".flv", ".mkv", ".avi", ".mov"}


def get_video_files(input_path: Path):
    """兼容单文件和文件夹两种输入"""
    if input_path.is_file():
        if input_path.suffix.lower() in VIDEO_EXTENSIONS:
            return [input_path]
        else:
            print(f"[!] {input_path} 不是支持的视频格式")
            return []
    elif input_path.is_dir():
        files = [p for p in input_path.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS]
        if not files:
            print(f"[!] 在 {input_path} 中未找到视频文件")
        return files
    else:
        print(f"[!] 路径不存在: {input_path}")
        return []


def extract_frames(video_input, frames_dir, frame_rate=1):
    input_path = Path(video_input)
    video_files = get_video_files(input_path)

    if not video_files:
        return

    for video_path in video_files:
        out_dir = Path(frames_dir) / video_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        out_pattern = str(out_dir / "frame_%06d.jpg")
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-vf", f"fps={frame_rate}",
            "-q:v", "2",
            out_pattern,
            "-hide_banner", "-loglevel", "error"
        ]

        print(f"抽帧: {video_path.name}")
        print(f"  -> {out_dir}")
        subprocess.run(cmd, check=True)
        print(f"  完成\n")

    print(f"全部抽帧完成，帧保存在: {frames_dir}")


if __name__ == "__main__":
    extract_frames(VIDEO_INPUT, FRAMES_DIR, FRAME_RATE)