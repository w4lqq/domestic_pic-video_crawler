import time
from pathlib import Path
from DrissionPage import ChromiumPage

# ==========================================
# 配置
# ==========================================
KEYWORDS_FILE = "D:/vs workspace/scheme 2/keywords/delivery man.txt"
OUTPUT_FILE   = "D:/vs workspace/scheme 2/dy_link/douyin_links.txt"
TARGET        = 50
# ==========================================

def load_keywords(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def crawl_keyword(page, keyword, target):
    url = f"https://www.douyin.com/search/{keyword}?type=video"
    page.get(url)
    time.sleep(8)  # 抖音加载慢，等久一点

    links = set()
    scroll = 0

    while len(links) < target and scroll < 20:
        all_a = page.eles("tag:a")
        for a in all_a:
            href = a.attr("href") or ""
            if "/video/" in href:
                clean = href.split("?")[0]
                if not clean.startswith("http"):
                    clean = "https://www.douyin.com" + clean
                links.add(clean)

        print(f"  已收集 {len(links)}/{target} 个链接")
        if len(links) >= target:
            break

        page.scroll.to_bottom()
        time.sleep(3)
        scroll += 1

    return list(links)[:target]

if __name__ == "__main__":
    keywords = load_keywords(KEYWORDS_FILE)
    print(f"共读取到 {len(keywords)} 个关键词\n")

    if Path(OUTPUT_FILE).exists():
        Path(OUTPUT_FILE).unlink()

    # 直接接管本机 Chrome，第一次运行手动登录抖音即可
    page = ChromiumPage()

    for i, keyword in enumerate(keywords, 1):
        print(f"[{i}/{len(keywords)}] 关键词: {keyword}")
        links = crawl_keyword(page, keyword, TARGET)

        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(f"# === {keyword} ===\n")
            for link in links:
                f.write(link + "\n")
            f.write("\n")

        print(f"  已追加 {len(links)} 条\n")
        time.sleep(2)

    print(f"========== 完成，结果保存在 {OUTPUT_FILE} ==========")