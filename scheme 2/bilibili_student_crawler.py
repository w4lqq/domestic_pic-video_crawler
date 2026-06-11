import asyncio
import os
from bilibili_api import search

# ==========================================
# 配置
# ==========================================
KEYWORDS_FILE = "D:/vs workspace/scheme 2/keywords/student.txt"
OUTPUT_FILE = "D:/vs workspace/scheme 2/bilibili_link/student_link.txt"   # 所有关键词的链接统一写入这一个文件
TARGET_PER_KEYWORD = 50
# ==========================================

def load_keywords(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def append_links(keyword, links, output_file):
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"# === {keyword} ===\n")
        for link in links:
            f.write(link + "\n")
        f.write("\n")
    print(f"  已追加 {len(links)} 条链接到 {output_file}")

async def crawl_keyword(keyword, target_num=50):
    collected = []
    seen = set()
    page = 1

    while len(collected) < target_num:
        try:
            result = await search.search_by_type(
                keyword,
                search_type=search.SearchObjectType.VIDEO,
                page=page
            )
        except Exception as e:
            print(f"  [!] 第 {page} 页请求失败: {e}")
            break

        videos = result.get("result", [])
        if not videos:
            print(f"  第 {page} 页无结果，停止")
            break

        for video in videos:
            if len(collected) >= target_num:
                break
            bvid = video.get("bvid")
            if bvid and bvid not in seen:
                seen.add(bvid)
                collected.append(f"https://www.bilibili.com/video/{bvid}")

        print(f"  第 {page} 页，已收集 {len(collected)}/{target_num}")
        page += 1
        await asyncio.sleep(1)

    return collected

async def main():
    keywords = load_keywords(KEYWORDS_FILE)
    print(f"共读取到 {len(keywords)} 个关键词\n")

    # 每次运行前清空旧文件，避免重复追加
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    for i, keyword in enumerate(keywords, 1):
        print(f"[{i}/{len(keywords)}] 关键词: {keyword}")
        links = await crawl_keyword(keyword, TARGET_PER_KEYWORD)
        append_links(keyword, links, OUTPUT_FILE)
        print()
        await asyncio.sleep(2)

    print(f"========== 全部完成，结果保存在 {OUTPUT_FILE} ==========")

if __name__ == "__main__":
    asyncio.run(main())