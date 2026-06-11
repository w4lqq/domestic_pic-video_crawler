import shutil
from pathlib import Path
from ultralytics import YOLO

# ==========================================
# 配置
# ==========================================
FRAMES_DIR  = "D:/vs workspace/scheme 2/bilibili_frames"
OUTPUT_DIR  = "D:/vs workspace/scheme 2/bilibili_frames_with_person"
MODEL_PATH  = "yolov8n-pose.pt"  # 首次运行自动下载，pose 模型专门检测人体关键点
CONF        = 0.6                # 置信度阈值，调高可减少误检
# ==========================================

# YOLOv8-pose 的 17 个关键点索引（COCO 定义）：
#   0:鼻子  1:左眼  2:右眼  3:左耳  4:右耳
#   5:左肩  6:右肩  7:左肘  8:右肘  9:左腕  10:右腕
#  11:左髋 12:右髋 13:左膝 14:右膝 15:左踝 16:右踝
#
# 判定"上半身可见"：至少检测到 鼻子/肩膀/肘部 中的若干个关键点
UPPER_BODY_KEYPOINTS = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # 鼻子、眼、耳、肩、肘
MIN_VISIBLE_KEYPOINTS = 3   # 至少有几个上半身关键点可见才算正样本，可按需调整
KP_CONF_THRESHOLD = 0.5     # 单个关键点的置信度，低于此视为不可见


def has_upper_body(result) -> bool:
    """
    判断检测结果中是否存在至少一个人拥有可见的上半身关键点。
    result: 单张图片的 YOLO 推理结果
    """
    if result.keypoints is None:
        return False

    # keypoints.data shape: (num_persons, 17, 3)  — x, y, conf
    kps_data = result.keypoints.data  # tensor

    for person_kps in kps_data:
        # person_kps shape: (17, 3)
        visible_count = 0
        for kp_idx in UPPER_BODY_KEYPOINTS:
            kp_conf = float(person_kps[kp_idx][2])
            if kp_conf >= KP_CONF_THRESHOLD:
                visible_count += 1
        if visible_count >= MIN_VISIBLE_KEYPOINTS:
            return True

    return False


def filter_person_frames(frames_dir, output_dir, model_path, conf):
    model = YOLO(model_path)

    frame_paths = list(Path(frames_dir).rglob("*.jpg"))
    total = len(frame_paths)
    if total == 0:
        print(f"[!] 在 {frames_dir} 中未找到任何 jpg 帧")
        return

    print(f"共 {total} 帧待检测")
    print(f"判定条件：上半身关键点（鼻/眼/耳/肩/肘）中至少 {MIN_VISIBLE_KEYPOINTS} 个可见\n")

    kept = 0
    for i, frame_path in enumerate(frame_paths, 1):
        results = model(str(frame_path), verbose=False, conf=conf)
        result = results[0]

        if has_upper_body(result):
            relative = frame_path.relative_to(frames_dir)
            dest = Path(output_dir) / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(frame_path, dest)
            kept += 1

        if i % 100 == 0 or i == total:
            print(f"  进度: {i}/{total}  |  已保留: {kept} 帧")

    print(f"\n筛选完成：{total} 帧中保留了 {kept} 帧")
    print(f"保存在: {output_dir}")


if __name__ == "__main__":
    filter_person_frames(FRAMES_DIR, OUTPUT_DIR, MODEL_PATH, CONF)