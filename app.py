from flask import Flask, render_template, request, jsonify, redirect
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import os
import secrets
import json
from datetime import datetime
import logging
import time

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 添加 CORS 支持
app.config['SECRET_KEY'] = secrets.token_hex(16)

# 配置 SocketIO - 关键修改
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',  # 依然使用 threading，但添加后续改进
    ping_timeout=120,        # 增加 ping 超时
    ping_interval=5,         # 减小 ping 间隔，保持连接活跃
    max_http_buffer_size=50 * 1024 * 1024,  # 50MB 缓冲区
    logger=True,
    engineio_logger=True
)

# 存储传输会话信息
transfer_sessions = {}
# 存储文件分片信息
file_chunks = {}

# 重要：降低分片大小！
CHUNK_SIZE = 2 * 1024 * 1024  # 2MB 而不是 10MB
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CHUNK_TIMEOUT = 60000  # 增加到60秒


def generate_transfer_code():
    """生成6位数字字母组合的传输码"""
    return secrets.token_urlsafe(4)[:6].upper()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload')
def upload():
    return render_template('upload.html')


@app.route('/download')
def download():
    return render_template('download.html')


@app.route('/create_transfer', methods=['POST'])
def create_transfer():
    """创建新的传输会话"""
    transfer_code = generate_transfer_code()
    while transfer_code in transfer_sessions:
        transfer_code = generate_transfer_code()

    transfer_sessions[transfer_code] = {
        'sender_id': None,
        'receiver_id': None,
        'files': [],
        'created_at': datetime.now().isoformat()
    }

    return jsonify({
        'status': 'success',
        'transfer_code': transfer_code
    })


@app.route('/join_transfer/<transfer_code>')
def join_transfer(transfer_code):
    """接收方加入传输会话"""
    if transfer_code not in transfer_sessions:
        return redirect('/download')

    return render_template('download.html', transfer_code=transfer_code)


@socketio.on('connect')
def handle_connect():
    logger.info(f'Client connected: {request.sid}')
    # 可选：存储客户端连接时间，用于监控连接寿命


@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f'Client disconnected: {request.sid}')
    # 不要立即清理会话，给重连留时间
    for code, session in list(transfer_sessions.items()):
        if session['sender_id'] == request.sid:
            logger.info(f'Sender for session {code} disconnected')
            emit('sender_disconnected', room=session['receiver_id'])
            # 在实际环境中，我们可能希望延迟更久
            session['sender_reconnect_time'] = datetime.now().timestamp() + 60  # 给60秒时间重连
        elif session['receiver_id'] == request.sid:
            logger.info(f'Receiver for session {code} disconnected')
            emit('receiver_disconnected', room=session['sender_id'])


@socketio.on('initialize_sender')
def initialize_sender(data):
    """初始化发送方的WebSocket连接"""
    transfer_code = data['transfer_code']
    logger.info(f'Initializing sender for transfer {transfer_code}')
    if transfer_code in transfer_sessions:
        transfer_sessions[transfer_code]['sender_id'] = request.sid
        join_room(transfer_code)
        emit('sender_initialized', {'status': 'success'})
        logger.info(f'Sender initialized for transfer {transfer_code}')


@socketio.on('join_transfer_room')
def on_join_transfer_room(data):
    """处理用户加入传输房间"""
    transfer_code = data['transfer_code']
    logger.info(f'Receiver joining transfer {transfer_code}')
    if transfer_code in transfer_sessions:
        join_room(transfer_code)
        transfer_sessions[transfer_code]['receiver_id'] = request.sid
        emit('receiver_joined', {'status': 'success'}, room=transfer_code)
        logger.info(f'Receiver joined transfer {transfer_code}')


@socketio.on('start_file_transfer')
def handle_file_transfer(data):
    """处理文件传输开始请求"""
    transfer_code = data['transfer_code']
    file_info = data['file_info']
    logger.info(f'Starting file transfer for {file_info["name"]} in transfer {transfer_code}')

    if transfer_code in transfer_sessions:
        transfer_sessions[transfer_code]['files'].append(file_info)
        emit('file_transfer_ready', file_info, room=transfer_code)
        logger.info(f'File transfer ready signal sent for {file_info["name"]}')


@socketio.on('file_chunk')
def handle_file_chunk(data):
    """处理文件分片传输"""
    transfer_code = data['transfer_code']
    chunk_data = data['chunk_data']
    chunk_index = data['chunk_index']
    file_id = data['file_id']
    total_chunks = data['total_chunks']

    if transfer_code in transfer_sessions:
        try:
            # 将数据块转发给接收方
            emit('file_chunk', {
                'file_id': file_id,
                'chunk_index': chunk_index,
                'chunk_data': chunk_data,
                'total_chunks': total_chunks
            }, room=transfer_sessions[transfer_code]['receiver_id'])
            logger.debug(f'Chunk {chunk_index}/{total_chunks} sent for file {file_id}')
        except Exception as e:
            logger.error(f'Error sending chunk: {str(e)}')
            emit('transfer_error', {'message': str(e)}, room=transfer_code)


@socketio.on('chunk_received')
def handle_chunk_received(data):
    """处理文件分片接收确认"""
    transfer_code = data['transfer_code']
    chunk_index = data['chunk_index']
    file_id = data['file_id']

    if transfer_code in transfer_sessions:
        emit('chunk_received', {
            'file_id': file_id,
            'chunk_index': chunk_index
        }, room=transfer_sessions[transfer_code]['sender_id'])
        logger.debug(f'Chunk {chunk_index} received confirmation for file {file_id}')


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)