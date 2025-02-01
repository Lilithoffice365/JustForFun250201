#百度贴吧签到，青龙面板自己用BaiDuCookie+BDUSS
#chatgpt修改版：添加wxpusher推送
#原作者github开源**

import os
import requests
import hashlib
import time
import copy
import logging
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# API 相关 URL
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"

# 贴吧环境变量
BaiDuCookie = os.getenv("BaiDuCookie", "").split("&")
BDUSS = os.getenv("BDUSS", "").split("&")

# WxPusher 环境变量
WXPUSHER_APP_TOKEN = os.getenv("WXPUSHER_APP_TOKEN", "")
WXPUSHER_TOPIC_IDS = os.getenv("WXPUSHER_TOPIC_IDS", "")
WXPUSHER_UIDS = os.getenv("WXPUSHER_UIDS", "")

# 请求头
HEADERS = {
    "Host": "tieba.baidu.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36",
}

SIGN_DATA = {
    "_client_type": "2",
    "_client_version": "9.7.8.0",
    "_phone_imei": "000000000000000",
    "model": "MI+5",
    "net_type": "1",
}

# 其他变量
SIGN_KEY = "tiebaclient!!!"
UTF8 = "utf-8"

s = requests.Session()

def send_wxpusher_message(title, content):
    """ 使用 WxPusher 发送推送 """
    if not WXPUSHER_APP_TOKEN or (not WXPUSHER_TOPIC_IDS and not WXPUSHER_UIDS):
        logger.error("WxPusher 配置缺失，无法推送签到结果")
        return

    data = {
        "appToken": WXPUSHER_APP_TOKEN,
        "content": content,
        "summary": title,
        "contentType": 1,  # 文本内容
        "topicIds": WXPUSHER_TOPIC_IDS.split(";") if WXPUSHER_TOPIC_IDS else [],
        "uids": WXPUSHER_UIDS.split(";") if WXPUSHER_UIDS else [],
    }

    response = requests.post("https://wxpusher.zjiecode.com/api/send/message", json=data)
    
    if response.status_code == 200:
        logger.info("签到结果推送成功")
    else:
        logger.error(f"签到结果推送失败: {response.text}")

def get_tbs(bduss):
    """ 获取 tbs 码 """
    logger.info("获取 TBS 码")
    headers = copy.copy(HEADERS)
    headers.update({"Cookie": f"BDUSS={bduss}"})

    try:
        tbs = s.get(url=TBS_URL, headers=headers, timeout=5).json().get("tbs", "")
    except Exception as e:
        logger.error(f"获取 tbs 失败: {e}")
        return ""

    return tbs

def get_favorite(bduss):
    """ 获取关注的贴吧列表 """
    logger.info("获取关注的贴吧列表")
    data = {
        "BDUSS": bduss,
        "_client_type": "2",
        "_client_id": "wappc_1534235498291_488",
        "_client_version": "9.7.8.0",
        "_phone_imei": "000000000000000",
        "from": "1008621y",
        "page_no": "1",
        "page_size": "200",
        "model": "MI+5",
        "net_type": "1",
        "timestamp": str(int(time.time())),
        "vcode_tag": "11",
    }
    data = encodeData(data)

    try:
        res = s.post(url=LIKIE_URL, data=data, timeout=5).json()
        return res.get("forum_list", {}).get("non-gconforum", []) + res.get("forum_list", {}).get("gconforum", [])
    except Exception as e:
        logger.error(f"获取关注贴吧失败: {e}")
        return []

def encodeData(data):
    """ 计算 sign 签名 """
    s = "".join([f"{k}={str(data[k])}" for k in sorted(data.keys())])
    sign = hashlib.md5((s + SIGN_KEY).encode(UTF8)).hexdigest().upper()
    data.update({"sign": sign})
    return data

def client_sign(bduss, tbs, fid, kw):
    """ 进行签到 """
    logger.info(f"开始签到贴吧: {kw}")
    data = copy.copy(SIGN_DATA)
    data.update({"BDUSS": bduss, "fid": fid, "kw": kw, "tbs": tbs, "timestamp": str(int(time.time()))})
    data = encodeData(data)

    res = s.post(url=SIGN_URL, data=data, timeout=5).json()
    return res

def execute_sign_in_tasks():
    """ 执行所有 BDUSS 账号的签到任务 """
    if not BDUSS:
        logger.error("未配置 BDUSS，无法执行签到")
        return

    all_results = []  # 存储所有贴吧的签到结果

    for user_index, bduss in enumerate(BDUSS):
        logger.info(f"开始签到第 {user_index + 1} 个用户")
        tbs = get_tbs(bduss)
        favorites = get_favorite(bduss)

        user_results = []  # 记录当前用户的签到情况

        for forum in favorites:
            time.sleep(random.randint(1, 5))  # 避免请求过快被封
            sign_result = client_sign(bduss, tbs, forum["id"], forum["name"])

            if sign_result.get("error_code") == "0":
                result_msg = f"【{forum['name']}】签到成功 🎉"
            else:
                error_msg = sign_result.get("error_msg", "未知错误")
                result_msg = f"【{forum['name']}】签到失败 ❌: {error_msg}"

            user_results.append(result_msg)
        
        all_results.extend(user_results)

    # 发送 WxPusher 推送
    push_content = "\n".join(all_results)
    send_wxpusher_message("贴吧签到结果", push_content)

if __name__ == "__main__":
    execute_sign_in_tasks()
