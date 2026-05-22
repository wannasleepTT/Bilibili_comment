import requests
import re
from setting import COOKIES, HEADERS

def get_aid(url: str) -> int:
    '从视频链接中提取 aid'
    # bvid -> aid 的转换接口    
    bvid = re.search(r'BV\w+', url).group(0)
    api = 'https://api.bilibili.com/x/web-interface/wbi/view'
    params = {
        'bvid': bvid
    }
    resp = requests.get(api, params=params, headers=HEADERS, cookies=COOKIES)

    return resp.json()['data']['aid']


def get_info(url: str) -> dict:
    bvid = re.search(r'BV\w+', url).group(0)
    api = 'https://api.bilibili.com/x/web-interface/wbi/view'
    params = {
        'bvid': bvid
    }
    resp = requests.get(api, params=params, headers=HEADERS, cookies=COOKIES)
    video_data = resp.json()

    # 安全提取 data 主体，防止传入的是完整响应
    data = video_data.get('data', video_data)

    # 提取各个模块
    owner = data.get('owner', {})
    stat = data.get('stat', {})

    # 构建干净的信息字典
    info = {
        # ----- 基本信息 -----
        'aid': data.get('aid'),
        'bvid': data.get('bvid'),
        'title': data.get('title'),
        'desc': data.get('desc'),
        'pubdate': data.get('pubdate'),      # 秒级时间戳
        'duration': data.get('duration'),    # 单位: 秒

        # ----- UP主信息 -----
        'owner_mid': owner.get('mid'),
        'owner_name': owner.get('name'),
        'owner_face': owner.get('face'),

        # ----- 统计信息 -----
        'view': stat.get('view'),            # 播放量
        'danmaku': stat.get('danmaku'),      # 弹幕数
        'reply': stat.get('reply'),          # 评论数
        'favorite': stat.get('favorite'),    # 收藏数
        'coin': stat.get('coin'),            # 投币数
        'share': stat.get('share'),          # 分享数
        'like': stat.get('like'),            # 点赞数
    }
    return info
