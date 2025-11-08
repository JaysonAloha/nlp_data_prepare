
import time
import random
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


def get_finance_calendar_image(breakfast_url, max_retries=3, delay_range=(1, 3)):
    """
    从财经早餐链接中提取财经日历图片的URL

    Args:
        breakfast_url: 财经早餐页面的URL
        max_retries: 最大重试次数
        delay_range: 随机延迟范围(秒)

    Returns:
        财经日历图片的URL，若未找到则返回None
    """
    ua = UserAgent()
    session = requests.Session()
    session.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })

    def validate_image_url(url):
        """验证图片URL有效性"""
        if not url.startswith(('http://', 'https://')):
            return False
        valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        if any(url.lower().endswith(ext) for ext in valid_extensions):
            return True
        if 'np-newspic.dfcfw.com' in url:  # 东方财富网图片域名
            return True
        return False

    def fetch_with_retry(retry_count=0):
        try:
            # 随机延迟避免反爬
            time.sleep(random.uniform(*delay_range))

            # 构建请求头
            headers = {
                'User-Agent': ua.random,
                'Referer': 'https://finance.eastmoney.com/'
            }

            # 发送请求
            response = session.get(breakfast_url, headers=headers, timeout=15)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}")
                if retry_count < max_retries:
                    return fetch_with_retry(retry_count + 1)
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # 策略1: 优先从正文区域查找可能的日历图片
            content_body = soup.find('div', id='ContentBody')
            if content_body:
                # 查找中心对齐的图片（通常重要图片会居中）
                center_tag = content_body.find('center')
                if center_tag:
                    img_tag = center_tag.find('img')
                    if img_tag:
                        src = img_tag.get('src') or img_tag.get('original')
                        if src and validate_image_url(src):
                            return src

                # 查找正文区域内的大尺寸图片
                large_images = []
                for img in content_body.find_all('img', src=True):
                    src = img.get('src')
                    width = img.get('width', '0')
                    if src and width.isdigit() and int(width) > 500:  # 更大尺寸阈值
                        large_images.append((src, int(width)))

                if large_images:
                    return max(large_images, key=lambda x: x[1])[0]

            # 策略2: 查找特定图片域名（东方财富网专用图片域名）
            target_img = soup.find('img', src=lambda s: s and 'np-newspic.dfcfw.com' in s)
            if target_img:
                src = target_img.get('src')
                if validate_image_url(src):
                    return src

            # 策略3: 查找包含"日历"关键词的图片
            calendar_imgs = soup.find_all('img', alt=lambda s: s and '日历' in s)
            if calendar_imgs:
                for img in calendar_imgs:
                    src = img.get('src')
                    if src and validate_image_url(src):
                        return src

            print("未找到符合条件的财经日历图片")
            return None

        except requests.exceptions.RequestException as e:
            print(f"请求异常: {e}")
            if retry_count < max_retries:
                print(f"第{retry_count + 1}次重试...")
                return fetch_with_retry(retry_count + 1)
            return None
        except Exception as e:
            print(f"提取图片时发生错误: {e}")
            return None

    return fetch_with_retry()


