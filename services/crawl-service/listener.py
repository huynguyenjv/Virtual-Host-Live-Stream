import time
import random
import tiktoklive

def connect():
    print("Connected to TikTok Live")


def listen():
    """
    Generator giả lập comment live
    (thay bằng TikTok Live SDK khi triển khai thật)
    """
    while True:
        yield {
            "type": "COMMENT",
            "user_id": random.randint(1, 1000),
            "username": "viewer_" + str(random.randint(1, 100)),
            "content": random.choice([
                "shop ơi giá bao nhiêu",
                "còn hàng không",
                "chào shop",
                "xin tư vấn"
            ])
        }
        time.sleep(1)
