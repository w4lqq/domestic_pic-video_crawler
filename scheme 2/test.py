import time
from pathlib import Path
from DrissionPage import ChromiumPage

def crawl_keyword(page, keyword, target):
    url = f"https://www.douyin.com/search/{keyword}?type=video"
    page.get(url)
    time.sleep(5)

    links = set()
    scroll = 0

    while len(links) < target and scroll < 20:
        # 先把页面所有 a 标签的 href 打印出来，看看长什么样
        all_a = page.eles("tag:a")
        for a in all_a:
            href = a.attr("href") or ""
            if href:
                print(href)  # ← 临时调试，看看抖音链接的实际格式

        break  # 先只跑一次，看输出

if __name__=="__main__":


    keyword = "快递员"
    target = 10

    page = ChromiumPage()
    crawl_keyword(page, keyword, target)
