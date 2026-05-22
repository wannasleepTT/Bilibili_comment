from functools import reduce
from hashlib import md5
import urllib.parse
import time
import requests

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys() -> tuple[str, str]:
    '获取最新的 img_key 和 sub_key 未登录也能获取到，直接访问导航接口即可'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://www.bilibili.com/'
    }
    cookies = {
        "SESSDATA": "ee533251%2C1793780456%2Cab932%2A51CjD3K1_-s2XcQLzw_0Q5QliIFfbhsT1Q6qdQBHnZ_X1-pUeU4Ndbft7kMRaRddQS9E0SVnFrbjNsV0tkb1NwQUk0cXNQSWFnOHZTVUY0UkxocVY4YVpqRkw3MVJJVHNwaTZXX1RfMXRrUHoxUWVrZDV6d1haeW04SS1JdjRCVk5hZ25lNVVFNVdBIIEC",
        "bili_jct": "a8aaabc62095a535e14a0da048676c25",
        "bili_ticket": "eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Nzg1NDA1NTYsImlhdCI6MTc3ODI4MTI5NiwicGx0IjotMX0.dMSu6CBVtgBmvi4CCzEesdHNXvAXTmFkOLYwOKvn9xE",
    }
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, cookies=cookies)
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

# 调用先 img_key, sub_key = getWbiKeys() img_key, sub_key 可以持续三天 然后 encWbi() 来获取签名参数

# img_key, sub_key = getWbiKeys()
# import json
# signed_params = encWbi(
#     params = {
#         'oid': 115716216919294,
#         'type': 1,
#         'mode': 3,
#         'pagination_str': json.dumps({"offset": ""}),
#         'plat': 1,
#         'seek_rpid': '',
#         'web_location': 1315875,
#     },
#     img_key=img_key,
#     sub_key=sub_key
# )
# query = urllib.parse.urlencode(signed_params)
# print(signed_params)
# print(query)