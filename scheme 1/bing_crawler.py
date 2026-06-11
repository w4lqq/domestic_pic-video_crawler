import os
import time
import json
import requests
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

# ==========================================
# 职业类别关键词
# ==========================================
keyword_map = {
    "学生": ["中学生", "高中生", "校服学生", "社团成员"],
    "教师": ["老师", "教导主任", "讲师", "年级主任", "宿管"],
    "外卖员": ["美团骑手", "美团外卖员", "饿了么骑手", "饿了么外卖员", "京东骑手", "京东外卖员", "淘宝闪购"],
    "保洁员": ["保洁工"],
    "保安": ["安保人员"],
    "维修人员": ["维修工", "维修师傅", "电工", "水工"]
}

# ==========================================
# 全局配置参数
# ==========================================
SAVE_ROOT = "Bing_Dataset"
PER_CLASS_NUM = 500
MIN_WIDTH = 400
MIN_HEIGHT = 400

# 滚动&防卡死配置
MAX_SCROLL_TIMES = 30       # 单关键词最大滚动次数
NO_NEW_IMG_LIMIT = 8        # 连续多次无新图，判定加载完毕
EMPTY_DOWNLOAD_LIMIT = 12   # 连续无成功下载次数，触发切换关键词

# ✅ 修复：加入 Referer，减少第三方图床的 403 拒绝
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://cn.bing.com/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

# ==========================================
# 初始化浏览器
# ==========================================
def init_browser():
    options = webdriver.ChromeOptions()
    # 如需后台运行，取消下面一行注释
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--blink-settings=imagesEnabled=true")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    options.page_load_strategy = "eager"

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver

# 检查浏览器会话是否有效
def is_driver_valid(driver):
    try:
        driver.current_window_handle
        return True
    except (InvalidSessionIdException, WebDriverException):
        return False

# ==========================================
# 基础工具函数
# ==========================================
def create_dir(path):
    os.makedirs(path, exist_ok=True)

def get_ext(content_type):
    if content_type is None:
        return ".jpg"
    if "jpeg" in content_type:
        return ".jpg"
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    return ".jpg"

# ✅ 修复：原逻辑 < 15000 才保存，实际上保留了缩略图/损坏图，改为跳过小文件
def download_image(url, retries=2):
    for _ in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            if len(r.content) < 15000:  # 跳过太小的图（缩略图/损坏）
                continue
            return r.content, r.headers.get("content-type")
        except Exception:
            time.sleep(1)
    return None, None

# 图片保存：尺寸过滤
def save_image(img_content, content_type, save_dir, img_id):
    try:
        img = Image.open(BytesIO(img_content))
        width, height = img.size
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            return False

        ext = get_ext(content_type)
        save_path = os.path.join(save_dir, f"{img_id:06d}{ext}")
        img.save(save_path)
        return True
    except Exception:
        return False

# ==========================================
# 核心爬取函数
# ==========================================
def crawl_bing_keyword(driver, class_name, keyword, save_dir, target_num, start_id):
    base_url = "https://cn.bing.com/images/search"
    search_query = f"{keyword} -anime -cartoon -logo -drawing"
    url = f"{base_url}?q={search_query}"

    current_id = start_id
    scroll_count = 0
    no_new_img_count = 0
    empty_download_count = 0
    seen_urls = set()  # 避免重复下载同一 URL

    # ✅ 修复：页面只加载一次，后续仅做滚动，不再每轮重新 driver.get()
    # 先处理浏览器会话失效
    if not is_driver_valid(driver):
        print(f"[{class_name}] 浏览器会话失效，正在重启...")
        driver = init_browser()

    load_success = False
    for _ in range(2):
        try:
            driver.get(url)
            load_success = True
            break
        except (InvalidSessionIdException, WebDriverException):
            print(f"[{class_name}] 页面访问失败，重试中...")
            time.sleep(2)
            driver = init_browser()

    if not load_success:
        print(f"[{class_name}] 多次访问失败，放弃当前关键词: {keyword}")
        return current_id, driver

    time.sleep(3)

    # ✅ 修复：while 循环内只做滚动 + 解析，不重新加载页面
    while current_id < target_num and scroll_count < MAX_SCROLL_TIMES:

        # 获取当前页面所有图片容器
        try:
            img_containers = driver.find_elements(By.CSS_SELECTOR, "div.imgpt")
            if not img_containers:
                # 备用选择器，Bing 有时会改结构
                img_containers = driver.find_elements(By.CSS_SELECTOR, "li.dgControl_list_item")
        except Exception:
            print(f"[{class_name}] 获取图片容器失败，跳出")
            break

        current_page_img_num = len(img_containers)
        print(f"[{class_name}] 当前已加载 {current_page_img_num} 张图片容器")

        # 遍历解析、下载图片
        for container in img_containers:
            if current_id >= target_num:
                break

            try:
                a_tag = container.find_element(By.CSS_SELECTOR, "a.iusc")
                m_raw = a_tag.get_attribute("m")
                if not m_raw:
                    continue
                m_data = json.loads(m_raw)
                # ✅ 修复：兼容 Bing 新旧两种字段名
                img_url = m_data.get("murl") or m_data.get("imgurl")
                if not img_url:
                    continue
                # 跳过已处理过的 URL
                if img_url in seen_urls:
                    continue
                seen_urls.add(img_url)
            except Exception:
                empty_download_count += 1
                continue

            # 下载+保存图片
            img_content, content_type = download_image(img_url)
            if img_content is None:
                empty_download_count += 1
                continue

            save_ok = save_image(img_content, content_type, save_dir, current_id)
            if save_ok:
                current_id += 1
                empty_download_count = 0
                print(f"[{class_name}] 已下载 {current_id}/{target_num} | 关键词: {keyword}")
            else:
                empty_download_count += 1

        # 连续无成功下载，切换关键词
        if empty_download_count >= EMPTY_DOWNLOAD_LIMIT:
            print(f"[{class_name}] 连续 {EMPTY_DOWNLOAD_LIMIT} 次未下载到有效图片，自动切换下一个关键词")
            break

        # 分段渐进滚动，模拟真人滑动，触发懒加载
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        # 判断是否加载到了新图片
        try:
            new_containers = driver.find_elements(By.CSS_SELECTOR, "div.imgpt")
            if not new_containers:
                new_containers = driver.find_elements(By.CSS_SELECTOR, "li.dgControl_list_item")
            new_page_img_num = len(new_containers)
        except Exception:
            new_page_img_num = current_page_img_num

        if new_page_img_num <= current_page_img_num:
            no_new_img_count += 1
            print(f"[{class_name}] 未加载到新图片，累计无新图次数: {no_new_img_count}")
            if no_new_img_count >= NO_NEW_IMG_LIMIT:
                print(f"[{class_name}] 当前关键词已无更多图片，切换下一个关键词")
                break
        else:
            no_new_img_count = 0

        scroll_count += 1

    return current_id, driver

# ==========================================
# 主程序入口
# ==========================================
if __name__ == "__main__":
    # 依赖安装：pip install selenium pillow requests
    driver = init_browser()

    try:
        create_dir(SAVE_ROOT)
        for cls, keywords in keyword_map.items():
            print("\n" + "=" * 60)
            print(f"开始采集类别: {cls} | 目标数量: {PER_CLASS_NUM}")
            print("=" * 60)

            save_dir = os.path.join(SAVE_ROOT, cls)
            create_dir(save_dir)
            current_num = len(os.listdir(save_dir))  # 断点续爬

            for keyword in keywords:
                if current_num >= PER_CLASS_NUM:
                    print(f"[{cls}] 已达到目标数量，跳过剩余关键词")
                    break

                print(f"\n---------- 当前关键词: {keyword} ----------")
                current_num, driver = crawl_bing_keyword(
                    driver, cls, keyword, save_dir, PER_CLASS_NUM, current_num
                )

            print(f"\n【{cls}】本轮共采集有效图片: {current_num} 张")

    finally:
        if driver and is_driver_valid(driver):
            driver.quit()

    print("\n========== 全部采集任务结束 ==========")