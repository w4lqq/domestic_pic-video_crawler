from pathlib import Path
from PIL import Image
import torch
import clip
import shutil
import csv
from collections import Counter

# ==========================================
# 配置
# ==========================================
INPUT_DIR  = "D:/vs workspace/scheme 2/bilibili_frames_with_person/【校园自制短片】浙江省一等奖作品 初中学生自制！学生低成本制作能拍成什么样？"
OUTPUT_DIR = "D:/vs workspace/scheme 2/bilibili_frames_clipped"
CONF_THRESHOLD = 0.2  # 最高分低于此则归入 uncertain，说明图片语义不明确

# 每个职业的文字描述，可以写多个描述增加召回率
# 描述越具体效果越好，中英文都支持（英文通常效果更好）
CATEGORIES = {
    "学生": [
        "a student wearing school uniform",
        "a middle school student in uniform",
        "a teenager in school uniform in classroom",
        "a young teenager at school",                          # 去掉 uniform 限制
        "a middle school student with a backpack",             # 书包是更可靠的视觉线索
        "a young person studying or walking in school campus", # 校园场景
        "teenagers playing or running on a school playground", # 操场场景
        "a young student sitting at a desk in a classroom",    # 课桌场景
    ],
   
    "老师": [
        "a teacher standing in front of a blackboard",
        "a teacher giving a lecture in classroom",
        "an adult teaching students in a classroom",
        "an adult woman or man in a Chinese school setting",          # 成年人在校园
        "a teacher sitting at a desk reviewing papers with glasses",  # 对应 frame_000068
        "an adult supervising students in a classroom",
    ],
}
# ==========================================


def classify_frames(input_dir, output_dir, categories, conf_threshold):
    print("加载 CLIP 模型中...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # 官方 clip 库，接口固定不受 transformers 版本影响
    model, preprocess = clip.load("ViT-B/32", device=device)
    model.eval()
    print(f"模型加载完成，使用设备: {device}\n")

    # 展开所有描述
    texts, labels = [], []
    for category, descs in categories.items():
        for desc in descs:
            texts.append(desc)
            labels.append(category)

    # 预编码所有文字（只算一次）
    with torch.no_grad():
        text_tokens = clip.tokenize(texts).to(device)
        text_features = model.encode_text(text_tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    frame_paths = list(Path(input_dir).rglob("*.jpg"))
    total = len(frame_paths)
    if total == 0:
        print(f"[!] 在 {input_dir} 中未找到任何 jpg 帧")
        return

    print(f"共 {total} 帧待分类\n")
    log_rows = []

    for i, frame_path in enumerate(frame_paths, 1):
        image = preprocess(Image.open(frame_path).convert("RGB")).unsqueeze(0).to(device)

        with torch.no_grad():
            image_features = model.encode_image(image)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            sims = (image_features @ text_features.T).squeeze(0).cpu().tolist()

        # 每个类别取旗下所有描述的最高分
        category_scores = {}
        for label, sim in zip(labels, sims):
            category_scores[label] = max(category_scores.get(label, -1), sim)

        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        final_label = best_category if best_score >= conf_threshold else "uncertain"

        dest_dir = Path(output_dir) / final_label
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(frame_path, dest_dir / frame_path.name)

        log_rows.append({
            "file": frame_path.name,
            "label": final_label,
            "score": round(best_score, 4),
            **{k: round(v, 4) for k, v in category_scores.items()}
        })

        if i % 50 == 0 or i == total:
            print(f"  进度: {i}/{total}  |  {frame_path.name} -> {final_label} ({best_score:.3f})")

    # 保存日志
    log_path = Path(output_dir) / "classification_log.csv"
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=log_rows[0].keys())
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"\n========== 分类完成 ==========")
    counts = Counter(r["label"] for r in log_rows)
    for cat, cnt in sorted(counts.items()):
        print(f"  {cat}: {cnt} 帧")
    print(f"日志: {log_path}")


if __name__ == "__main__":
    classify_frames(INPUT_DIR, OUTPUT_DIR, CATEGORIES, CONF_THRESHOLD)