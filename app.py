import os
import uuid
import threading
import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from comment import get_all_comments

app = Flask(__name__)
CORS(app)  # 允许跨域，方便 Vue 开发

# 配置结果存储目录
RESULT_DIR = 'comments'
os.makedirs(RESULT_DIR, exist_ok=True)

# 任务状态存储（简单内存字典，生产环境请用 Redis）
tasks = {}

def run_crawler_task(aid: int, task_id: str):
    """后台运行爬虫，保存结果"""
    try:
        comments = get_all_comments(aid)
        filepath = os.path.join(RESULT_DIR, f"{task_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        tasks[task_id] = {
            'status': 'completed',
            'file': filepath,
            'total': len(comments)
        }
    except Exception as e:
        tasks[task_id] = {'status': 'failed', 'error': str(e)}

@app.route('/api/start', methods=['POST'])
def start_crawl():
    """启动爬虫任务"""
    data = request.get_json()
    video_url = data.get('video_url')
    if not video_url:
        return jsonify({'error': 'Missing video_url'}), 400
    # try:
    #     aid = int(aid)
    # except ValueError:
    #     return jsonify({'error': 'aid must be integer'}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {'status': 'running'}
    thread = threading.Thread(target=run_crawler_task, args=(video_url, task_id))
    thread.start()
    return jsonify({'task_id': task_id})

@app.route('/api/status/<task_id>')
def task_status(task_id):
    """查询任务状态"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)

@app.route('/api/download/<task_id>')
def download_result(task_id):
    """下载结果文件"""
    task = tasks.get(task_id)
    if not task or task.get('status') != 'completed':
        return jsonify({'error': 'File not ready'}), 404
    return send_file(task['file'], as_attachment=True, download_name=f'comments_{task_id}.json')

if __name__ == '__main__':
    app.run(debug=True, port=5000)