import random
import requests
import time
import json
from typing import List, Dict, Optional
import get_signed_params
import urllib.parse
import video_api
from setting import COOKIES, HEADERS, DELAY


 # 例如：{'SESSDATA': 'xxx', 'bili_jct': 'xxx'}

# 请求延迟（秒），避免请求过快

# ---------- 工具函数 ----------
def fetch_json(url: str, params: Dict = None, max_retries=5) -> Optional[Dict]:
    global DELAY
    retries = 0
    while retries < max_retries:
        try:
            resp = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                time.sleep(random.uniform(DELAY, DELAY + 0.05))
                if DELAY > 0.5:
                    DELAY = 0.5
                if data.get('code') == 0:
                    return data.get('data')
                else:
                    print(f"API 错误: {data.get('code')}, {data.get('message')}")
                    return None
            elif resp.status_code == 412:
                DELAY *= 2
                retries += 1
                print(f"412 错误，第 {retries} 次重试，等待 {DELAY} 秒")
                time.sleep(DELAY)
                continue
            else:
                print(f"HTTP 错误: {resp.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    return None

def parse_reply(reply_item: Dict) -> Dict:
    """解析单条评论（一级或子回复）"""
    member = reply_item.get('member', {})
    content_obj = reply_item.get('content', {})
    return {
        'rpid': reply_item.get('rpid'),
        'mid': reply_item.get('mid'),
        'uname': member.get('uname'),
        'avatar': member.get('avatar'),
        'sex': member.get('sex'),
        'level': member.get('level_info', {}).get('current_level'),
        'vip_type': member.get('vip', {}).get('vipType'),
        'content': content_obj.get('message'),
        'like': reply_item.get('like'),
        'ctime': reply_item.get('ctime'),
        'rcount': reply_item.get('rcount', 0),  # 子回复总数
    }

# ---------- 提取子回复（楼中楼） ----------
def fetch_sub_replies(oid: int, root: int, pn: int = 1) -> List[Dict]:
    """
    递归获取某条一级评论下的所有子回复
    :param oid: 视频 aid 或 动态 id
    :param root: 一级评论的 rpid
    :param pn: 页码，从 1 开始
    :return: 子回复列表
    params = {
        "oid": "115716216919294",
        "type": "1",
        "root": "285575140256",
        "ps": "10",
        "pn": "2",
        "web_location": "333.788"
    }
    """
    url = 'https://api.bilibili.com/x/v2/reply/reply'
    params = {
        'oid': oid,
        'type': 1,
        'root': root,
        'pn': pn,
        'ps': 20,   # 每页数量，最大20
        'web_location': 333.788,
    }
    data = fetch_json(url, params)
    if not data:
        return []
    replies = data.get('replies') or []
    sub_list = [parse_reply(r) for r in replies]
    # 检查是否有下一页,没有has_next字段了，可以根据data.get('page', {}).get('count', 0) 来判断是否还有下一页
    if len(replies) == 20:
        next_list = fetch_sub_replies(oid, root, pn + 1)
        sub_list.extend(next_list)
    return sub_list

# ---------- 提取一级评论（含子回复） ----------
def fetch_main_replies(oid: int, pagination_str: str) -> Dict:
    """
    获取一页一级评论，并附带各自的所有子回复
    :param oid: 视频 aid
    :param pagination_str: 分页字符串，用于 wbi 签名

    """
    url = 'https://api.bilibili.com/x/v2/reply/main'
    params = {
        "oid": oid,
        "type": "1",
        "mode": "3",
        "pagination_str": f"{{\"offset\":\"{pagination_str}\"}}",
        "plat": "1",
        "web_location": "1315875",
    }
    params = get_signed_params.encWbi(params=params, img_key=img_key, sub_key=sub_key)
    data = fetch_json(url, params)
    if not data:
        return {'replies': [], 'has_next': False}
    main_replies = data.get('replies', [])
    next_offset = data.get('cursor', {}).get('pagination_reply', {}).get('next_offset', '')

    result = []
    for r in main_replies:
        # 解析一级评论
        main_comment = parse_reply(r)
        # 获取该评论下的所有子回复
        if r.get('rcount', 0) > 0:
            sub_replies = fetch_sub_replies(oid, r['rpid'])
            main_comment['sub_replies'] = sub_replies
        else:
            main_comment['sub_replies'] = []
        result.append(main_comment)

    return {'replies': result, 'next_offset': next_offset}


def fetch_first_comments(aid):
    '''
    获取第一页一级评论（含子回复），并使用 wbi 签名
    '''
    url = 'https://api.bilibili.com/x/v2/reply/main'

    params = {
        'oid': aid,
        'type': 1,
        'mode': 3,
        'pagination_str': json.dumps({"offset": ""}),
        'plat': 1,
        'seek_rpid': '',
        'web_location': 1315875,
    }
    params = get_signed_params.encWbi(params=params, img_key=img_key, sub_key=sub_key)
    data = fetch_json(url, params)
    if not data:
        return {'replies': []}
    next_offset = data.get('cursor', '').get('pagination_reply', '').get('next_offset', '')
    main_replies = data.get('replies', [])

    result = []
    for r in main_replies:
        # 解析一级评论
        main_comment = parse_reply(r)
        # 获取该评论下的所有子回复
        if r.get('rcount', 0) > 0:
            sub_replies = fetch_sub_replies(aid, r['rpid'])
            main_comment['sub_replies'] = sub_replies
        else:
            main_comment['sub_replies'] = []
        result.append(main_comment)

    return {
        'replies': result,
        'next_offset': next_offset,
        }

    

def get_all_comments(video_url: int) -> List[Dict]:
    """
    获取视频所有评论（含子回复）
    :param video_url: 视频链接
    :param max_pages: 最多抓取页数（防止无限循环）
    :return: 所有一级评论列表（内含 sub_replies）
    """
    info = video_api.get_info(video_url)
    aid = info.get('aid')
    global img_key, sub_key
    img_key, sub_key = get_signed_params.getWbiKeys()
    comments = []
    ffc = fetch_first_comments(aid)
    comment, next_offset = ffc.get('replies', []), ffc.get('next_offset', '')
    comments.append(comment)

    # 爬取后续页评论，直到没有下一页为止
    # relies 如果没有值的话，说明只有一页评论了，就不需要继续fetch_main_replies了
    while next_offset:
        fmr = fetch_main_replies(aid, next_offset)
        comment, next_offset = fmr.get('replies', []), fmr.get('next_offset', '')
        comments.append(comment)
    
    return comments


# -------- - 主函数 ----------
def main(video_url: str):
    # 替换成你要爬的视频 AV 号（纯数字）
    comments = get_all_comments(video_url)
    info = video_api.get_info(video_url)

    # 保存为 JSON 文件
    with open(f'{info.get("title", "bilibili_comments_full")}.json', 'w', encoding='utf-8') as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

    print(f"评论已保存至 {info.get('title', 'bilibili_comments_full')}.json")


# ---------- 示例 ----------
if __name__ == '__main__':
    video_url = '''
        https://www.bilibili.com/video/BV1G35q6hEXT/?spm_id_from=333.1365.list.card_archive.click&vd_source=5518c333728bffce72ad1cc2babc3ace
    '''  # 替换成你要爬的视频链接
    main(video_url)