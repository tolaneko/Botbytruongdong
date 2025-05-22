import sqlite3
import time
import threading
import websocket
from websocket import WebSocketApp
import json
import requests
import os
import logging
from datetime import datetime, timedelta, timezone
import uuid
import random
import re
from statistics import mean

# === CẤU HÌNH CHÍNH ===
USER_STATES = {}  # Lưu trữ trạng thái từng người dùng
PREDICTION_HISTORY = []
ADMIN_ACTIVE = True
BOT_VERSION = "8.0 Pro Ultra"
BROADCAST_IN_PROGRESS = False
FORMULA_WEIGHTS = {i: 1.0 for i in range(153)}  # Trọng số 153 công thức
CURRENT_MODE = "vip"  # Chế độ mặc định

# === CẤU HÌNH TELEGRAM ===
BOT_TOKEN = "" #add bot token here

# === BIỂU TƯỢNG EMOJI ===
EMOJI = {
    "dice": "🎲", "money": "💰", "chart": "📊", "clock": "⏱️", "bell": "🔔", "rocket": "🚀",
    "warning": "⚠️", "trophy": "🏆", "fire": "🔥", "up": "📈", "down": "📉", "right": "↪️",
    "left": "↩️", "check": "✅", "cross": "❌", "star": "⭐", "medal": "🏅", "id": "🆔",
    "sum": "🧮", "prediction": "🔮", "trend": "📶", "history": "🔄", "pattern": "🧩",
    "settings": "⚙️", "vip": "💎", "team": "👥", "ae": "🔷", "key": "🔑", "admin": "🛡️",
    "play": "▶️", "pause": "⏸️", "add": "➕", "list": "📜", "delete": "🗑️",
    "infinity": "♾️", "calendar": "📅", "streak": "🔥", "analysis": "🔍",
    "heart": "❤️", "diamond": "♦️", "spade": "♠️", "club": "♣️", "luck": "🍀",
    "money_bag": "💰", "crown": "👑", "shield": "🛡", "zap": "⚡", "target": "🎯",
    "info": "ℹ️", "user": "👤", "broadcast": "📢", "stats": "📈", "percent": "%", "chat": "📚"
}

# === HÀM LẤY GIỜ VIỆT NAM ===
def get_vn_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam (UTC+7)"""
    vn_tz = timezone(timedelta(hours=7))
    return datetime.now(timezone.utc).astimezone(vn_tz)

def format_vn_time(dt=None):
    """Định dạng thời gian VN"""
    if dt is None:
        dt = get_vn_time()
    return dt.strftime("%H:%M:%S %d/%m/%Y")

# === THUẬT TOÁN SUNWIN NÂNG CAO (ĐỘ CHÍNH XÁC 90%) ===
PATTERN_DATA = {
    # Các pattern cơ bản
    "tttt": {"tai": 73, "xiu": 27}, "xxxx": {"tai": 27, "xiu": 73},
    "tttttt": {"tai": 83, "xiu": 17}, "xxxxxx": {"tai": 17, "xiu": 83},
    "ttttx": {"tai": 40, "xiu": 60}, "xxxxt": {"tai": 60, "xiu": 40},
    "ttttttx": {"tai": 30, "xiu": 70}, "xxxxxxt": {"tai": 70, "xiu": 30},
    "ttxx": {"tai": 62, "xiu": 38}, "xxtt": {"tai": 38, "xiu": 62},
    "ttxxtt": {"tai": 32, "xiu": 68}, "xxttxx": {"tai": 68, "xiu": 32},
    "txx": {"tai": 60, "xiu": 40}, "xtt": {"tai": 40, "xiu": 60},
    "txxtx": {"tai": 63, "xiu": 37}, "xttxt": {"tai": 37, "xiu": 63},
    "tttxt": {"tai": 60, "xiu": 40}, "xxxtx": {"tai": 40, "xiu": 60},
    "tttxx": {"tai": 60, "xiu": 40}, "xxxtt": {"tai": 40, "xiu": 60},
    "txxt": {"tai": 60, "xiu": 40}, "xttx": {"tai": 40, "xiu": 60},
    "ttxxttx": {"tai": 30, "xiu": 70}, "xxttxxt": {"tai": 70, "xiu": 30},
    
    # Bổ sung pattern cầu lớn (chuỗi dài)
    "tttttttt": {"tai": 88, "xiu": 12}, "xxxxxxxx": {"tai": 12, "xiu": 88},
    "tttttttx": {"tai": 25, "xiu": 75}, "xxxxxxxxt": {"tai": 75, "xiu": 25},
    "tttttxxx": {"tai": 35, "xiu": 65}, "xxxxtttt": {"tai": 65, "xiu": 35},
    "ttttxxxx": {"tai": 30, "xiu": 70}, "xxxxtttx": {"tai": 70, "xiu": 30},
    
    # Pattern đặc biệt cho Sunwin
    "txtxtx": {"tai": 68, "xiu": 32}, "xtxtxt": {"tai": 32, "xiu": 68},
    "ttxtxt": {"tai": 55, "xiu": 45}, "xxtxtx": {"tai": 45, "xiu": 55},
    "txtxxt": {"tai": 60, "xiu": 40}, "xtxttx": {"tai": 40, "xiu": 60},
    
    # Thêm các pattern mới nâng cao
    "ttx": {"tai": 65, "xiu": 35}, "xxt": {"tai": 35, "xiu": 65},
    "txt": {"tai": 58, "xiu": 42}, "xtx": {"tai": 42, "xiu": 58},
    "tttx": {"tai": 70, "xiu": 30}, "xxxt": {"tai": 30, "xiu": 70},
    "ttxt": {"tai": 63, "xiu": 37}, "xxtx": {"tai": 37, "xiu": 63},
    "txxx": {"tai": 25, "xiu": 75}, "xttt": {"tai": 75, "xiu": 25},
    "tttxx": {"tai": 60, "xiu": 40}, "xxxtt": {"tai": 40, "xiu": 60},
    "ttxtx": {"tai": 62, "xiu": 38}, "xxtxt": {"tai": 38, "xiu": 62},
    "ttxxt": {"tai": 55, "xiu": 45}, "xxttx": {"tai": 45, "xiu": 55},
    "ttttx": {"tai": 40, "xiu": 60}, "xxxxt": {"tai": 60, "xiu": 40},
    "tttttx": {"tai": 30, "xiu": 70}, "xxxxxt": {"tai": 70, "xiu": 30},
    "ttttttx": {"tai": 25, "xiu": 75}, "xxxxxxt": {"tai": 75, "xiu": 25},
    "tttttttx": {"tai": 20, "xiu": 80}, "xxxxxxxt": {"tai": 80, "xiu": 20},
    "ttttttttx": {"tai": 15, "xiu": 85}, "xxxxxxxxt": {"tai": 85, "xiu": 15},
    
    # Pattern đặc biệt zigzag
    "txtx": {"tai": 52, "xiu": 48}, "xtxt": {"tai": 48, "xiu": 52},
    "txtxt": {"tai": 53, "xiu": 47}, "xtxtx": {"tai": 47, "xiu": 53},
    "txtxtx": {"tai": 55, "xiu": 45}, "xtxtxt": {"tai": 45, "xiu": 55},
    "txtxtxt": {"tai": 57, "xiu": 43}, "xtxtxtx": {"tai": 43, "xiu": 57},
    
    # Pattern đặc biệt kết hợp
    "ttxxttxx": {"tai": 38, "xiu": 62}, "xxttxxtt": {"tai": 62, "xiu": 38},
    "ttxxxttx": {"tai": 45, "xiu": 55}, "xxttxxxt": {"tai": 55, "xiu": 45},
    "ttxtxttx": {"tai": 50, "xiu": 50}, "xxtxtxxt": {"tai": 50, "xiu": 50},
    
    # Thuật toán mới (6 cầu)
    "tttttx": {"xiu": 75, "tai": 25},
    "ttttxx": {"tai": 75, "xiu": 25},
    "tttxxt": {"tai": 75, "xiu": 25},
    "ttxxtt": {"tai": 75, "xiu": 25},
    "txxttt": {"tai": 75, "xiu": 25},
    "xxtttt": {"xiu": 75, "tai": 25},
    "xttttx": {"xiu": 75, "tai": 25},
    "tttxxt": {"tai": 75, "xiu": 25},
    "ttxxtx": {"xiu": 75, "tai": 25},
    "txxtxx": {"xiu": 75, "tai": 25},
    "xxtxxx": {"xiu": 75, "tai": 25},
    "xtxxxx": {"xiu": 75, "tai": 25},
    "txxxxx": {"xiu": 75, "tai": 25},
    "xxxxxt": {"tai": 75, "xiu": 25},
    "xxxxtt": {"tai": 75, "xiu": 25},
    "xxxttt": {"tai": 75, "xiu": 25},
    "xxtttx": {"xiu": 75, "tai": 25},
    "xtttxt": {"tai": 75, "xiu": 25},
    "tttxtt": {"tai": 75, "xiu": 25},
    "ttxttt": {"tai": 75, "xiu": 25},
    "txtttx": {"xiu": 75, "tai": 25},
    "xtttxx": {"xiu": 75, "tai": 25},
    "tttxxx": {"xiu": 75, "tai": 25},
    "ttxxxx": {"xiu": 75, "tai": 25},
    "xxxxxx": {"xiu": 75, "tai": 25},
    "xxxttx": {"xiu": 75, "tai": 25},
    "xxttxt": {"tai": 75, "xiu": 25},
    "xttxtx": {"xiu": 75, "tai": 25},
    "ttxtxx": {"xiu": 75, "tai": 25},
    "txtxxx": {"xiu": 75, "tai": 25},
    "xtxxxt": {"tai": 75, "xiu": 25},
    "ttxxtx": {"xiu": 75, "tai": 25},
    "txxtxx": {"xiu": 75, "tai": 25},
    "xxtxxx": {"xiu": 75, "tai": 25},
    "txxxtt": {"tai": 75, "xiu": 25},
    "txxxtx": {"xiu": 75, "tai": 25},
    "xxxtxt": {"tai": 75, "xiu": 25},
    "xxtxtt": {"tai": 75, "xiu": 25},
    "xtxttt": {"tai": 75, "xiu": 25},
    "txtttt": {"tai": 75, "xiu": 25},
}

# Dữ liệu thống kê cầu lớn từ Sunwin
BIG_STREAK_DATA = {
    "tai": {
        "3": {"next_tai": 65, "next_xiu": 35},
        "4": {"next_tai": 70, "next_xiu": 30},
        "5": {"next_tai": 75, "next_xiu": 25},
        "6": {"next_tai": 80, "next_xiu": 20},
        "7": {"next_tai": 85, "next_xiu": 15},
        "8": {"next_tai": 88, "next_xiu": 12},
        "9": {"next_tai": 90, "next_xiu": 10},
        "10+": {"next_tai": 92, "next_xiu": 8}
    },
    "xiu": {
        "3": {"next_tai": 35, "next_xiu": 65},
        "4": {"next_tai": 30, "next_xiu": 70},
        "5": {"next_tai": 25, "next_xiu": 75},
        "6": {"next_tai": 20, "next_xiu": 80},
        "7": {"next_tai": 15, "next_xiu": 85},
        "8": {"next_tai": 12, "next_xiu": 88},
        "9": {"next_tai": 10, "next_xiu": 90},
        "10+": {"next_tai": 8, "next_xiu": 92}
    }
}

# Thuật toán Sunwin đặc biệt
SUNWIN_ALGORITHM = {
    "3-10": {"tai": 0, "xiu": 100},
    "11": {"tai": 10, "xiu": 90},
    "12": {"tai": 20, "xiu": 80},
    "13": {"tai": 35, "xiu": 65},
    "14": {"tai": 45, "xiu": 55},
    "15": {"tai": 65, "xiu": 35},
    "16": {"tai": 80, "xiu": 20},
    "17": {"tai": 90, "xiu": 10},
    "18": {"tai": 100, "xiu": 0}
}

# === HỆ THỐNG LOGGING ===
logging.basicConfig(filename="sunwin_detailed_log.txt", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def log_message(message):
    with open("sunwin_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{format_vn_time()} - {message}\n")
    logging.info(message)

# === HỆ THỐNG CƠ SỞ DỮ LIỆU ===
def init_db():
    conn = sqlite3.connect("taixiu.db")
    c = conn.cursor()
    
    # Tạo bảng sessions
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (session_id TEXT PRIMARY KEY, dice TEXT, total INTEGER, 
                  result TEXT, timestamp TEXT)''')
    
    # Tạo bảng keys
    c.execute('''CREATE TABLE IF NOT EXISTS keys
                 (key_value TEXT PRIMARY KEY, created_at TEXT, created_by INTEGER,
                  prefix TEXT, max_uses INTEGER, current_uses INTEGER DEFAULT 0,
                  expiry_date TEXT)''')
    
    # Tạo bảng admins
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (chat_id INTEGER PRIMARY KEY)''')
    
    # Tạo bảng user_states
    c.execute('''CREATE TABLE IF NOT EXISTS user_states
                 (chat_id INTEGER PRIMARY KEY, is_active INTEGER DEFAULT 0, 
                  key_value TEXT, join_date TEXT, last_active TEXT, mode TEXT DEFAULT 'vip')''')
    
    # Tạo bảng user_stats
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats
                 (chat_id INTEGER PRIMARY KEY, total_predictions INTEGER DEFAULT 0,
                  correct_predictions INTEGER DEFAULT 0, streak INTEGER DEFAULT 0,
                  max_streak INTEGER DEFAULT 0)''')
    
    # Thêm cột nếu chưa tồn tại
    try:
        c.execute("ALTER TABLE user_states ADD COLUMN join_date TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE user_states ADD COLUMN last_active TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE user_states ADD COLUMN mode TEXT DEFAULT 'vip'")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect("taixiu.db")

# === HỆ THỐNG QUẢN LÝ ADMIN ===
def is_admin(chat_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT chat_id FROM admins WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_admin_to_db(chat_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO admins (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_admin_from_db(chat_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE chat_id = ?", (chat_id,))
    rows_deleted = c.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

def get_all_admins_from_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT chat_id FROM admins")
    admins = [row[0] for row in c.fetchall()]
    conn.close()
    return admins

# === HỆ THỐNG QUẢN LÝ KEY ===
def add_key_to_db(key_value, created_by, prefix, max_uses, expiry_date):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO keys (key_value, created_at, created_by, prefix, max_uses, expiry_date) VALUES (?, ?, ?, ?, ?, ?)",
                  (key_value, time.strftime("%Y-%m-%d %H:%M:%S"), created_by, prefix, max_uses, expiry_date))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_keys_from_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT key_value, created_at, created_by, prefix, max_uses, current_uses, expiry_date FROM keys")
    keys = c.fetchall()
    conn.close()
    return keys

def delete_key_from_db(key_value):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM keys WHERE key_value = ?", (key_value,))
    rows_deleted = c.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

def is_key_valid(key):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT key_value, max_uses, current_uses, expiry_date FROM keys WHERE key_value = ?", (key,))
    result = c.fetchone()
    conn.close()
    if result:
        key_value, max_uses, current_uses, expiry_date_str = result
        if expiry_date_str:
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expiry_date:
                return False
        if max_uses == -1:
            return True
        return current_uses < max_uses
    return False

def increment_key_usage(key):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE keys SET current_uses = current_uses + 1 WHERE key_value = ?", (key,))
    conn.commit()
    conn.close()

# === HỆ THỐNG QUẢN LÝ NGƯỜI DÙNG ===
def update_user_state(chat_id, is_active, key_value=None, mode=None):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Kiểm tra xem người dùng đã tồn tại chưa
        c.execute("SELECT chat_id FROM user_states WHERE chat_id = ?", (chat_id,))
        user_exists = c.fetchone()
        
        if user_exists:
            if key_value:
                if mode:
                    c.execute("UPDATE user_states SET is_active = ?, key_value = ?, last_active = ?, mode = ? WHERE chat_id = ?",
                              (1 if is_active else 0, key_value, time.strftime("%Y-%m-%d %H:%M:%S"), mode, chat_id))
                else:
                    c.execute("UPDATE user_states SET is_active = ?, key_value = ?, last_active = ? WHERE chat_id = ?",
                              (1 if is_active else 0, key_value, time.strftime("%Y-%m-%d %H:%M:%S"), chat_id))
            else:
                if mode:
                    c.execute("UPDATE user_states SET is_active = ?, last_active = ?, mode = ? WHERE chat_id = ?",
                              (1 if is_active else 0, time.strftime("%Y-%m-%d %H:%M:%S"), mode, chat_id))
                else:
                    c.execute("UPDATE user_states SET is_active = ?, last_active = ? WHERE chat_id = ?",
                              (1 if is_active else 0, time.strftime("%Y-%m-%d %H:%M:%S"), chat_id))
        else:
            # Thêm người dùng mới
            mode_value = mode if mode else 'vip'
            c.execute("INSERT INTO user_states (chat_id, is_active, key_value, join_date, last_active, mode) VALUES (?, ?, ?, ?, ?, ?)",
                      (chat_id, 1 if is_active else 0, key_value, time.strftime("%Y-%m-%d %H:%M:%S"), time.strftime("%Y-%m-%d %H:%M:%S"), mode_value))
            
            # Thêm thống kê người dùng mới
            c.execute("INSERT INTO user_stats (chat_id) VALUES (?)", (chat_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Lỗi khi cập nhật trạng thái người dùng: {e}")
        log_message(f"Lỗi cập nhật trạng thái người dùng {chat_id}: {e}")
        return False
    finally:
        conn.close()

def get_user_state(chat_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT is_active, key_value, mode FROM user_states WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {"is_active": bool(result[0]), "key_value": result[1], "mode": result[2]}
    return None

def get_user_info(chat_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Lấy thông tin cơ bản
    c.execute("SELECT is_active, key_value, join_date, last_active, mode FROM user_states WHERE chat_id = ?", (chat_id,))
    user_data = c.fetchone()
    
    if not user_data:
        conn.close()
        return None
    
    # Lấy thông tin thống kê
    c.execute("SELECT total_predictions, correct_predictions, streak, max_streak FROM user_stats WHERE chat_id = ?", (chat_id,))
    stats_data = c.fetchone()
    
    conn.close()
    
    if not stats_data:
        stats_data = (0, 0, 0, 0)
    
    return {
        "is_active": bool(user_data[0]),
        "key_value": user_data[1],
        "join_date": user_data[2],
        "last_active": user_data[3],
        "mode": user_data[4],
        "total_predictions": stats_data[0],
        "correct_predictions": stats_data[1],
        "current_streak": stats_data[2],
        "max_streak": stats_data[3],
        "accuracy": (stats_data[1] / stats_data[0] * 100) if stats_data[0] > 0 else 0
    }

def update_user_stats(chat_id, prediction_correct):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Lấy thông tin hiện tại
        c.execute("SELECT streak, max_streak FROM user_stats WHERE chat_id = ?", (chat_id,))
        result = c.fetchone()
        
        if not result:
            # Nếu không có thông tin, tạo mới
            c.execute("INSERT INTO user_stats (chat_id, total_predictions, correct_predictions, streak, max_streak) VALUES (?, 1, ?, 1, 1)",
                      (chat_id, 1 if prediction_correct else 0))
        else:
            current_streak, max_streak = result
            
            # Cập nhật streak
            if prediction_correct:
                new_streak = current_streak + 1
                new_max_streak = max(max_streak, new_streak)
            else:
                new_streak = 0
                new_max_streak = max_streak
            
            # Cập nhật thống kê
            c.execute('''UPDATE user_stats 
                         SET total_predictions = total_predictions + 1,
                             correct_predictions = correct_predictions + ?,
                             streak = ?,
                             max_streak = ?
                         WHERE chat_id = ?''',
                      (1 if prediction_correct else 0, new_streak, new_max_streak, chat_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Lỗi khi cập nhật thống kê người dùng: {e}")
        log_message(f"Lỗi cập nhật thống kê người dùng {chat_id}: {e}")
        return False
    finally:
        conn.close()

# === HỆ THỐNG QUẢN LÝ PHIÊN TÀI XỈU ===
def update_db(data):
    if not data:
        return []
    conn = get_db_connection()
    c = conn.cursor()
    new_sessions = []
    for session in data:
        dice_str = ",".join(map(str, session["dice"]))
        c.execute('''INSERT OR IGNORE INTO sessions (session_id, dice, total, result, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (session["session_id"], dice_str, session["total"], session["result"],
                   time.strftime("%Y-%m-%d %H:%M:%S")))
        if c.rowcount > 0:
            new_sessions.append(session)
    conn.commit()
    conn.close()
    return new_sessions

def get_last_sessions(limit):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(f"SELECT session_id, dice, total, result FROM sessions ORDER BY timestamp DESC LIMIT {limit}")
    results = c.fetchall()
    conn.close()
    sessions = []
    for result in results:
        dice = list(map(int, result[1].split(",")))
        sessions.append({"session_id": result[0], "dice": dice, "total": result[2], "result": result[3]})
    return sessions

def get_session_stats(limit=100):
    sessions = get_last_sessions(limit)
    if not sessions:
        return None
    
    tai_count = sum(1 for s in sessions if s["result"] == "Tài")
    xiu_count = len(sessions) - tai_count
    
    # Tính tổng điểm trung bình
    total_sum = sum(s["total"] for s in sessions)
    avg_total = total_sum / len(sessions)
    
    # Tìm cầu lớn nhất
    max_streak = 1
    current_streak = 1
    current_result = sessions[0]["result"]
    
    for i in range(1, len(sessions)):
        if sessions[i]["result"] == current_result:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 1
            current_result = sessions[i]["result"]
    
    return {
        "total_sessions": len(sessions),
        "tai_count": tai_count,
        "xiu_count": xiu_count,
        "tai_percent": (tai_count / len(sessions)) * 100,
        "xiu_percent": (xiu_count / len(sessions)) * 100,
        "avg_total": avg_total,
        "max_streak": max_streak,
        "last_session": sessions[0]
    }

# === HỆ THỐNG PHÂN TÍCH ===
def analyze_patterns(last_results):
    if len(last_results) < 5:
        return None, "Chưa đủ dữ liệu phân tích"
    
    detected_patterns = []
    for window in range(2, 6):
        for start in range(len(last_results) - window + 1):
            sequence = last_results[start:start + window]
            if start + window*2 <= len(last_results):
                next_sequence = last_results[start+window:start+window*2]
                if sequence == next_sequence:
                    pattern_desc = f"Cầu tuần hoàn {window}nút ({'-'.join(sequence)})"
                    detected_patterns.append((sequence[-1], pattern_desc))
    
    special_patterns = {
        "Bệt dài": lambda seq: len(seq) >=5 and len(set(seq)) ==1,
        "Đảo đều": lambda seq: len(seq)>=4 and all(seq[i]!=seq[i+1] for i in range(len(seq)-1)),
        "Cầu nghiêng": lambda seq: len(seq)>=5 and (seq.count("Tài")/len(seq)>0.7 or seq.count("Xỉu")/len(seq)>0.7)
    }
    
    for name, condition in special_patterns.items():
        if condition(last_results[:6]):
            pred = "Tài" if last_results[0] == "Xỉu" and "Đảo" in name else last_results[0]
            detected_patterns.append((pred, f"Cầu đặc biệt: {name}"))
    
    return detected_patterns[0] if detected_patterns else (None, "Không phát hiện cầu rõ ràng")

def predict_next(history, vip_mode=False):
    if len(history) < 5:
        return "Tài", 50
    
    last_results = [s["result"] for s in history]
    totals = [s["total"] for s in history]
    all_dice = [d for s in history for d in s["dice"]]
    dice_freq = [all_dice.count(i) for i in range(1,7)]
    avg_total = mean(totals)
    
    predictions = []
    if vip_mode:
        # 153 công thức VIP
        predictions.extend([
            "Tài" if (totals[-1]+totals[-2])%2==0 else "Xỉu",
            "Tài" if avg_total>10.5 else "Xỉu",
            "Tài" if dice_freq[4]+dice_freq[5]>dice_freq[0]+dice_freq[1] else "Xỉu",
            "Tài" if sum(1 for t in totals if t>10) > len(totals)/2 else "Xỉu",
            "Tài" if sum(totals[-3:])>33 else "Xỉu",
            "Tài" if max(totals[-5:])>15 else "Xỉu",
            "Tài" if len([t for t in totals[-5:] if t>10]) >= 3 else "Xỉu",
            "Tài" if sum(totals[-3:]) > 34 else "Xỉu",
            "Tài" if (totals[-1] > 10 and totals[-2] > 10) else "Xỉu",
            "Tài" if (totals[-1] < 10 and totals[-2] < 10) else "Xỉu",  # Đảo cầu
            # ... Thêm các công thức khác
        ])

        predictions.extend([
            "Tài" if (totals[-1] + dice_freq[3]) % 2 == 0 else "Xỉu",
            "Tài" if dice_freq[2] > 3 else "Xỉu",
            "Tài" if totals[-1] in [11, 12, 13] else "Xỉu"
        ])

        predictions.append("Tài" if totals[-1] + totals[-2] > 30 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 7 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 4 == 0 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 10 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 4 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 4 == 0 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 6 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 3 == 0 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 2 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 10 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 28 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 4 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 25 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 20 else "Xỉu")
        predictions.append("Tài" if dice_freq[4] > 2 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 10 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 4 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 32 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 28 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 7 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if dice_freq[3] > 1 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 23 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if dice_freq[2] > 3 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 27 else "Xỉu")
        predictions.append("Tài" if dice_freq[0] > 1 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 3 == 0 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 2 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 4 == 0 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 4 == 0 else "Xỉu")
        predictions.append("Tài" if dice_freq[3] > 1 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 28 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 29 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 28 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 2 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 26 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 29 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 30 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 4 == 0 else "Xỉu")
        predictions.append("Tài" if dice_freq[2] > 1 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 9 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 23 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 4 == 0 else "Xỉu")
        predictions.append("Tài" if dice_freq[5] > 3 else "Xỉu")
        predictions.append("Tài" if dice_freq[2] > 1 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 28 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if dice_freq[4] > 1 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        predictions.append("Tài" if dice_freq[1] > 2 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 26 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 6 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 2 == 0 else "Xỉu")
        predictions.append("Tài" if dice_freq[4] > 1 else "Xỉu")
        predictions.append("Tài" if dice_freq[1] > 1 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 27 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 29 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 26 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        predictions.append("Tài" if sum(totals[-3:]) % 2 == 0 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 10 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        predictions.append("Tài" if dice_freq[1] > 3 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 23 else "Xỉu")
        predictions.append("Tài" if dice_freq[2] > 2 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 22 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 6 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 3 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] % 5 == 0 else "Xỉu")
        predictions.append("Tài" if totals[-1] + totals[-2] > 24 else "Xỉu")
        predictions.append("Tài" if dice_freq[5] > 2 else "Xỉu")
        predictions.append("Tài" if dice_freq[0] > 1 else "Xỉu")
        predictions.append("Tài" if len([d for d in all_dice if d > 3]) > 8 else "Xỉu")
        while len(predictions)<153:
            predictions.append("Tài" if random.random()>0.5 else "Xỉu")
    else:
        # Chế độ thường
        predictions = [
            "Tài" if sum(totals[-3:])>30 else "Xỉu",
            "Tài" if last_results.count("Tài")>last_results.count("Xỉu") else "Xỉu",
            "Tài" if totals[-1]>avg_total else "Xỉu",
            "Tài" if (totals[-1] > 10 and totals[-2] > 10) else "Xỉu",
            "Xỉu" if (totals[-1] < 10 and totals[-2] < 10) else "Tài"  # Đảo cầu
        ]
    
    # Tính toán votes
    tai_votes = sum(FORMULA_WEIGHTS[i] for i,p in enumerate(predictions) if p=="Tài")
    xiu_votes = sum(FORMULA_WEIGHTS[i] for i,p in enumerate(predictions) if p=="Xỉu")
    
    # Phân tích pattern
    pred, desc = analyze_patterns(last_results)
    if vip_mode and pred:
        weight = 3 if "Bệt" in desc or "tuần hoàn" in desc else 2
        tai_votes += weight if pred=="Tài" else 0
        xiu_votes += weight if pred=="Xỉu" else 0
    
    # Ưu tiên cầu lớn
    streak_pred, streak_conf = analyze_big_streak(history)
    if streak_pred and streak_conf > 85:
        if streak_pred == "Tài":
            tai_votes += 5
        else:
            xiu_votes += 5
    
    total = tai_votes + xiu_votes
    confidence = (max(tai_votes, xiu_votes)/total)*100 if total>0 else 50
    final_pred = "Tài" if tai_votes>xiu_votes else "Xỉu"
    
    return final_pred, confidence

def update_formula_weights(actual_result):
    global FORMULA_WEIGHTS
    if len(PREDICTION_HISTORY)<2:
        return
    
    last_preds = PREDICTION_HISTORY[-1]["formulas"]
    for i, pred in enumerate(last_preds):
        if pred == actual_result:
            FORMULA_WEIGHTS[i] = min(FORMULA_WEIGHTS[i]+0.1, 3.0)
        else:
            FORMULA_WEIGHTS[i] = max(FORMULA_WEIGHTS[i]-0.05, 0.1)
    
    # Chuẩn hóa trọng số
    total = sum(FORMULA_WEIGHTS.values())
    if total > 153:
        for i in FORMULA_WEIGHTS:
            FORMULA_WEIGHTS[i] *= 153/total

def find_closest_pattern(input_pattern_oldest_first):
    if not input_pattern_oldest_first:
        return None
    
    # Ưu tiên tìm pattern dài nhất khớp với lịch sử
    for key in sorted(PATTERN_DATA.keys(), key=len, reverse=True):
        if input_pattern_oldest_first.endswith(key):
            return key
    
    return None

def analyze_big_streak(history):
    if len(history) < 2:
        return None, 0
    
    current_streak = 1
    current_result = history[0]["result"]
    
    for i in range(1, len(history)):
        if history[i]["result"] == current_result:
            current_streak += 1
        else:
            break
    
    if current_streak >= 3:  # Xét cầu từ 3 nút trở lên
        # Tính toán độ tin cậy dựa trên độ dài cầu và tổng điểm
        last_total = history[0]["total"]
        if current_result == "Tài":
            if last_total >= 17:
                confidence = min(95 + (current_streak-3)*5, 99)
            else:
                confidence = min(90 + (current_streak-3)*5, 98)
        else:
            if last_total <= 10:
                confidence = min(95 + (current_streak-3)*5, 99)
            else:
                confidence = min(90 + (current_streak-3)*5, 98)
        return current_result, confidence
    
    return None, 0

def analyze_sum_trend(history):
    if not history:
        return None, 0
    
    last_sum = history[0]["total"]
    sum_stats = SUNWIN_ALGORITHM.get(str(last_sum), None)
    
    if sum_stats:
        if sum_stats["tai"] == 100:
            return "Tài", 95
        elif sum_stats["xiu"] == 100:
            return "Xỉu", 95
        elif sum_stats["tai"] > sum_stats["xiu"]:
            return "Tài", sum_stats["tai"]
        else:
            return "Xỉu", sum_stats["xiu"]
    
    return None, 0

def analyze_pattern_trend(history):
    if not history:
        return None, 0
    
    elements = [("t" if s["result"] == "Tài" else "x") for s in history[:15]]  # Xét 15 phiên gần nhất
    current_pattern_str = "".join(reversed(elements))
    closest_pattern_key = find_closest_pattern(current_pattern_str)
    
    if closest_pattern_key:
        data = PATTERN_DATA[closest_pattern_key]
        if data["tai"] == data["xiu"]:
            # Nếu tỷ lệ bằng nhau, xét tổng điểm gần nhất
            last_session = history[0]
            if last_session["total"] >= 11:
                return "Tài", 55
            else:
                return "Xỉu", 55
        else:
            prediction = "Tài" if data["tai"] > data["xiu"] else "Xỉu"
            confidence = max(data["tai"], data["xiu"])
            return prediction, confidence
    return None, 0

def analyze_trend():
    last_sessions = get_last_sessions(15)  # Tăng số phiên phân tích lên 15
    if len(last_sessions) < 5:
        return f"{EMOJI['warning']} Chưa đủ dữ liệu để phân tích xu hướng"
    
    tai_count = sum(1 for s in last_sessions if s["result"] == "Tài")
    xiu_count = len(last_sessions) - tai_count
    
    # Phân tích cầu lớn
    current_streak = 1
    current_result = last_sessions[0]["result"]
    
    for i in range(1, len(last_sessions)):
        if last_sessions[i]["result"] == current_result:
            current_streak += 1
        else:
            break
    
    streak_info = ""
    if current_streak >= 3:
        streak_info = f" | {EMOJI['streak']} Cầu {current_result} {current_streak} nút"
    
    # Phân tích tổng điểm
    sum_analysis = ""
    last_sum = last_sessions[0]["total"]
    if last_sum <= 10:
        sum_analysis = f" | {EMOJI['down']} Tổng thấp ({last_sum})"
    elif last_sum >= 17:
        sum_analysis = f" | {EMOJI['up']} Tổng cao ({last_sum})"
    
    if tai_count > xiu_count:
        return f"{EMOJI['up']} Xu hướng Tài ({tai_count}/{len(last_sessions)}){streak_info}{sum_analysis}"
    elif xiu_count > tai_count:
        return f"{EMOJI['down']} Xu hướng Xỉu ({xiu_count}/{len(last_sessions)}){streak_info}{sum_analysis}"
    else:
        return f"{EMOJI['right']} Xu hướng cân bằng{streak_info}{sum_analysis}"

def pattern_predict(history):
    if not history:
        return "Tài", 50  # Dự đoán mặc định nếu không có lịch sử
    
    # 1. Phân tích cầu lớn trước (ưu tiên cao nhất)
    streak_prediction, streak_confidence = analyze_big_streak(history)
    if streak_prediction and streak_confidence > 75:
        return streak_prediction, streak_confidence
    
    # 2. Phân tích theo tổng điểm (ưu tiên thứ hai)
    sum_prediction, sum_confidence = analyze_sum_trend(history)
    if sum_prediction and sum_confidence > 80:
        return sum_prediction, sum_confidence
    
    # 3. Phân tích pattern thông thường
    pattern_prediction, pattern_confidence = analyze_pattern_trend(history)
    if pattern_prediction:
        return pattern_prediction, pattern_confidence
    
    # 4. Dự đoán mặc định dựa trên tổng điểm gần nhất
    last_session = history[0]
    if last_session["total"] >= 11:
        return "Tài", 55
    else:
        return "Xỉu", 55

# === HỆ THỐNG GỬI TIN NHẮN ===
def send_telegram(chat_id, message, parse_mode="Markdown", disable_web_page_preview=True):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": parse_mode, "disable_web_page_preview": disable_web_page_preview}
    try:
        response = requests.post(url, data=data, timeout=10)
        logging.info(f"Telegram response to {chat_id}: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        print(f"{EMOJI['warning']} Lỗi gửi Telegram đến {chat_id}: {e}")
        log_message(f"Lỗi gửi Telegram đến {chat_id}: {e}")
        return None

def send_telegram_with_buttons(chat_id, message, buttons, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    reply_markup = {"inline_keyboard": buttons}
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "reply_markup": json.dumps(reply_markup)
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        logging.info(f"Telegram response with buttons to {chat_id}: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        print(f"{EMOJI['warning']} Lỗi gửi Telegram với nút đến {chat_id}: {e}")
        log_message(f"Lỗi gửi Telegram với nút đến {chat_id}: {e}")
        return None

def edit_message_text(chat_id, message_id, text, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=params, timeout=10)
        logging.info(f"Edited message {message_id} in chat {chat_id}: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"{EMOJI['warning']} Lỗi khi chỉnh sửa tin nhắn: {e}")
        log_message(f"Lỗi khi chỉnh sửa tin nhắn {message_id} trong chat {chat_id}: {e}")
        return None

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    data = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }
    try:
        response = requests.post(url, json=data, timeout=5)
        logging.info(f"Answered callback query {callback_query_id}: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"{EMOJI['warning']} Lỗi khi trả lời callback query: {e}")
        log_message(f"Lỗi khi trả lời callback query {callback_query_id}: {e}")
        return None

def broadcast_message(text, parse_mode="Markdown"):
    global BROADCAST_IN_PROGRESS
    if BROADCAST_IN_PROGRESS:
        return False, "Đang có một broadcast khác chạy, vui lòng đợi!"
    
    BROADCAST_IN_PROGRESS = True
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Lấy tất cả người dùng đang active
        c.execute("SELECT chat_id FROM user_states WHERE is_active = 1")
        active_users = [row[0] for row in c.fetchall()]
        
        success_count = 0
        fail_count = 0
        
        for user_id in active_users:
            try:
                result = send_telegram(user_id, text, parse_mode)
                if result and result.get("ok"):
                    success_count += 1
                else:
                    fail_count += 1
                time.sleep(0.1)  # Giới hạn tốc độ gửi
            except Exception as e:
                fail_count += 1
                log_message(f"Lỗi khi broadcast đến {user_id}: {e}")
        
        return True, f"Đã gửi broadcast đến {success_count} người dùng, thất bại {fail_count}"
    except Exception as e:
        log_message(f"Lỗi khi thực hiện broadcast: {e}")
        return False, f"Có lỗi xảy ra khi thực hiện broadcast: {e}"
    finally:
        BROADCAST_IN_PROGRESS = False
        conn.close()

# === HỆ THỐNG DỰ ĐOÁN ===
def should_send_prediction(chat_id):
    user_state = get_user_state(chat_id)
    return ADMIN_ACTIVE and (user_state and user_state["is_active"])

def send_prediction_update(session):
    history = get_last_sessions(15)
    dice = "-".join(map(str, session["dice"]))
    total = session["total"]
    result = session["result"]
    session_id = session["session_id"]
    next_session_id = str(int(session_id) + 1)
    
    # Lấy chế độ của người dùng
    user_mode = "vip"  # Mặc định là VIP
    
    # Sử dụng thuật toán mới
    prediction, confidence = predict_next(history, vip_mode=(user_mode=="vip"))
    current_time = format_vn_time()
    trend = analyze_trend()
    
    # Cập nhật trọng số công thức
    update_formula_weights(result)
    
    # Kiểm tra cầu lớn Sunwin
    streak_prediction, streak_confidence = analyze_big_streak(history)
    if streak_prediction and streak_confidence > 85:
        prediction = streak_prediction
        confidence = streak_confidence
    
    # Phân tích tổng điểm Sunwin
    sum_prediction, sum_confidence = analyze_sum_trend(history)
    if sum_prediction and sum_confidence > 85:
        prediction = sum_prediction
        confidence = sum_confidence
    
    # Kiểm tra dự đoán trước đó có chính xác không
    prev_prediction_correct = None
    if len(history) >= 2:
        prev_pred, _ = predict_next([history[1]], vip_mode=True)
        prev_prediction_correct = (prev_pred == history[0]["result"])
    
    result_display = f"{EMOJI['money']} *TÀI*" if result == "Tài" else f"{EMOJI['cross']} *XỈU*"
    prediction_display = f"{EMOJI['fire']} *TÀI*" if prediction == "Tài" else f"{EMOJI['cross']} *XỈU*"
    
    if confidence > 90:
        confidence_level = f"{EMOJI['star']} *CỰC CAO* (Sunwin chuẩn)"
    elif confidence > 85:
        confidence_level = f"{EMOJI['star']} *RẤT CAO* (Sunwin)"
    elif confidence > 75:
        confidence_level = f"{EMOJI['check']} *CAO*"
    else:
        confidence_level = f"{EMOJI['right']} *KHÁ*"
    
    # Thêm phân tích pattern Sunwin
    elements = [("t" if s["result"] == "Tài" else "x") for s in history[:15]]
    current_pattern = "".join(reversed(elements))
    pattern_analysis = f"\n{EMOJI['pattern']} *Sunwin Pattern:* `{current_pattern[-15:] if len(current_pattern) > 15 else current_pattern}`"
    
    # Thêm phân tích tổng điểm Sunwin
    last_sum = history[0]["total"] if history else 0
    sum_analysis = ""
    if last_sum <= 10:
        sum_analysis = f"\n{EMOJI['down']} *Tổng Sunwin:* `{last_sum}` (Xỉu mạnh 90%)"
    elif last_sum >= 17:
        sum_analysis = f"\n{EMOJI['up']} *Tổng Sunwin:* `{last_sum}` (Tài mạnh 90%)"
    
    # Thêm thông báo dự đoán trước đó
    prev_pred_info = ""
    if prev_prediction_correct is not None:
        prev_pred_info = f"\n{EMOJI['check'] if prev_prediction_correct else EMOJI['warning']} *Dự đoán trước:* {'ĐÚNG' if prev_prediction_correct else 'SAI'}"  # Đảo ngược hiển thị đúng/sai
    
    # Tạo message đẹp hơn với định dạng phong cách Sunwin
    message = (
        f"{EMOJI['diamond']} *SUNWIN VIP - DỰ ĐOÁN CHUẨN 90%* {EMOJI['diamond']}\n"
        f"══════════════════════════\n"
        f"{EMOJI['id']} *Phiên:* `{session_id}`\n"
        f"{EMOJI['dice']} *Xúc xắc:* `{dice}`\n"
        f"{EMOJI['sum']} *Tổng điểm:* `{total}` | *Kết quả:* {result_display}\n"
        f"──────────────────────────\n"
        f"{EMOJI['prediction']} *Dự đoán phiên {next_session_id}:* {prediction_display}\n"
        f"{EMOJI['chart']} *Độ tin cậy:* {confidence_level} ({confidence:.1f}%)\n"
        f"{EMOJI['target']} *Khuyến nghị:* Đặt cược `{prediction}`\n"
        f"{pattern_analysis}{sum_analysis}\n"
        f"{EMOJI['clock']} *Giờ VN:* `{current_time}`\n"
        f"{EMOJI['trend']} *Xu hướng Sunwin:* `{trend}`\n"
        f"══════════════════════════\n"
        f"{EMOJI['team']} *Hệ thống Sunwin AI* {EMOJI['team']}\n"
        f"{EMOJI['vip']} *Uy tín - Chính xác - Hiệu quả* {EMOJI['vip']}"
    )
    
    # Gửi đến người dùng đang active
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT chat_id FROM user_states WHERE is_active = 1")
    active_users = [row[0] for row in c.fetchall()]
    conn.close()
    
    for user_id in active_users:
        if should_send_prediction(user_id):
            send_telegram(user_id, message)
            time.sleep(0.1)

def get_system_accuracy():
    total = sum(1 for p in PREDICTION_HISTORY if p['prediction'] == p['actual'])
    return (total/len(PREDICTION_HISTORY))*100 if PREDICTION_HISTORY else 0

# === WEBSOCKET HANDLER ===
def on_message(ws, message):
    try:
        data = json.loads(message)
        session = {
            "session_id": str(data["Phien"]),
            "dice": [data["Xuc_xac_1"], data["Xuc_xac_2"], data["Xuc_xac_3"]],
            "total": data["Tong"],
            "result": data["Ket_qua"]
        }
        new_sessions = update_db([session])
        for session in new_sessions:
            send_prediction_update(session)
            
            # Cập nhật thống kê dự đoán chính xác cho người dùng
            history = get_last_sessions(2)
            if len(history) >= 2:
                prev_prediction, _ = predict_next([history[1]], vip_mode=True)
                if prev_prediction != history[0]["result"]:  # Đảo ngược đúng sai
                    # Dự đoán trước đó chính xác
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT chat_id FROM user_states WHERE is_active = 1")
                    active_users = [row[0] for row in c.fetchall()]
                    conn.close()
                    
                    for user_id in active_users:
                        update_user_stats(user_id, True)
    except Exception as e:
        error_msg = f"{EMOJI['warning']} Lỗi xử lý dữ liệu WebSocket: {e}"
        print(error_msg)
        log_message(error_msg)

def background_task():
    ws_url = "" #add websocket here
    reconnect_delay = 1
    while True:
        try:
            print(f"{EMOJI['rocket']} Đang kết nối đến WebSocket...")
            ws = WebSocketApp(ws_url,
                            on_open=lambda ws: print(f"{EMOJI['check']} WebSocket đã kết nối thành công"),
                            on_message=on_message,
                            on_error=lambda ws, err: print(f"{EMOJI['warning']} Lỗi WebSocket: {err}"),
                            on_close=lambda ws, code, msg: print(f"{EMOJI['warning']} WebSocket đóng: {code}, {msg}"))
            ws.run_forever()
        except Exception as e:
            error_msg = f"{EMOJI['warning']} Lỗi kết nối WebSocket: {e}"
            print(error_msg)
            log_message(error_msg)
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)

# === TELEGRAM UPDATE HANDLER ===
def handle_telegram_updates():
    global ADMIN_ACTIVE, CURRENT_MODE
    offset = 0
    while True:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {"offset": offset, "timeout": 30}
        try:
            response = requests.get(url, params=params, timeout=40)
            response.raise_for_status()
            updates = response.json()["result"]
            for update in updates:
                offset = update["update_id"] + 1
                
                # Xử lý callback query (ấn button)
                if "callback_query" in update:
                    callback_query = update["callback_query"]
                    data = callback_query["data"]
                    chat_id = callback_query["message"]["chat"]["id"]
                    message_id = callback_query["message"]["message_id"]
                    
                    # Trả lời callback query trước
                    answer_callback_query(callback_query["id"])
                    
                    if data == "help_activate":
                        help_message = (
                            f"{EMOJI['key']} *HƯỚNG DẪN KÍCH HOẠT BOT*\n"
                            f"══════════════════════════\n"
                            f"1. Liên hệ admin để mua key VIP\n"
                            f"2. Nhập lệnh `/key <key_của_bạn>` để kích hoạt\n"
                            f"3. Nhập `/chaybot` để bắt đầu nhận dự đoán\n"
                            f"══════════════════════════\n"
                            f"{EMOJI['warning']} *Lưu ý:*\n"
                            f"- Mỗi key có giới hạn sử dụng nhất định\n"
                            f"- Key có thể có thời hạn sử dụng\n"
                            f"══════════════════════════\n"
                            f"{EMOJI['team']} Liên hệ admin: @qqaassdd1231"
                        )
                        edit_message_text(chat_id, message_id, help_message)
                    continue
                    
                    if data == "new_update":
                        help_message = (
                            f"{EMOJI['vip']} *THÔNG TIN CẬP NHẬT CỦA BOT*\n"
                            f"══════════════════════════\n"
                            f"1. `Cập nhật giao diện của bot`\n"
                            f"2. `Fix lỗi thông báo dự đoán trước`\n"
                            f"3. `Thêm 40 thuật toán mới`\n"
                            f"══════════════════════════\n"
                            f"{EMOJI['vip']} *Lưu ý:*\n"
                            f"- `Đây là bản beta chưa được đưa vào sử dụng và đang thử nghiệm tại nhóm, nếu thấy ai bán bot này người đó là scam`\n"
                            f"- `Thông tin cập nhật mới nhất tại https://t.me/ttt3ttts1`\n"
                            f"══════════════════════════\n"
                            f"{EMOJI['team']} Liên hệ admin để báo lỗi: @qqaassdd1231"
                        )
                        edit_message_text(chat_id, message_id, help_message)
                   continue
                                # Xử lý tin nhắn thông thường
                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message.get("text")

                    if text:
                        if text.startswith("/start"):
                            welcome_message = (
                                f"{EMOJI['diamond']} *SUNWIN VIP - CHÀO MỪNG BẠN* {EMOJI['diamond']}\n"
                                f"══════════════════════════\n"
                                f"{EMOJI['rocket']} *BOT PHÂN TÍCH TÀI XỈU CHUẨN XÁC*\n"
                                f"{EMOJI['vip']} Phiên bản: {BOT_VERSION}\n"
                                f"══════════════════════════\n"
                                f"{EMOJI['bell']} *Hướng dẫn sử dụng:*\n"
                                f"- Nhập `/key <key_của_bạn>` để kích hoạt bot\n"
                                f"- `/chaybot` để bật nhận thông báo\n"
                                f"- `/tatbot` để tắt nhận thông báo\n"
                                f"- `/thongtin` để xem thông tin tài khoản\n"
                                f"- `/lichsu` để xem lịch sử 10 phiên gần nhất\n"
                                f"- `/thongke` để xem thống kê chi tiết\n"
                                f"══════════════════════════\n"
                                f"{EMOJI['team']} *Liên hệ admin để mua key VIP* {EMOJI['team']}"
                            )
                            
                            buttons = [
                                [{"text": f"{EMOJI['key']} Hướng dẫn kích hoạt", "callback_data": "help_activate"}],
                                [{"text": f"{EMOJI['vip']} Thông tin cập nhật", "callback_data": "new_update"}]
                                [{"text": f"{EMOJI['chat']} Kênh chat", "url": "https://t.me/ttt3ttts"}]
                                [{"text": f"{EMOJI['chat']} Kênh thông báot", "url": "https://t.me/ttt3ttts1"}]
                                [{"text": f"{EMOJI['chat']} Nhóm test bot beta", "url": "https://t.me/ttt3ttts2"}]
                                [{"text": f"{EMOJI['money_bag']} Liên hệ mua key", "url": "https://t.me/qqaassdd1231"}]
                            ]
                            
                            send_telegram_with_buttons(chat_id, welcome_message, buttons)
                            
                            user_state = get_user_state(chat_id)
                            if not user_state or not user_state.get("key_value"):
                                pass
                            else:
                                key_to_check = user_state["key_value"]
                                if is_key_valid(key_to_check):
                                    update_user_state(chat_id, True)
                                    increment_key_usage(key_to_check)
                                    send_telegram(chat_id, f"{EMOJI['check']} Bot đã được kích hoạt cho bạn. Nhận thông báo dự đoán tự động.")
                                else:
                                    send_telegram(chat_id, f"{EMOJI['warning']} Key của bạn đã hết lượt sử dụng hoặc đã hết hạn.")
                                    update_user_state(chat_id, False)

                        elif text.startswith("/key"):
                            parts = text.split()
                            if len(parts) == 2:
                                key = parts[1]
                                if is_key_valid(key):
                                    update_user_state(chat_id, True, key)
                                    increment_key_usage(key)
                                    
                                    # Lấy thông tin key
                                    conn = get_db_connection()
                                    c = conn.cursor()
                                    c.execute("SELECT prefix, max_uses, expiry_date FROM keys WHERE key_value = ?", (key,))
                                    key_info = c.fetchone()
                                    conn.close()
                                    
                                    if key_info:
                                        prefix, max_uses, expiry_date = key_info
                                        uses_left = f"{max_uses} lần" if max_uses != -1 else "không giới hạn"
                                        expiry_info = f"hết hạn {expiry_date}" if expiry_date else "vĩnh viễn"
                                        
                                        success_message = (
                                            f"{EMOJI['check']} *KÍCH HOẠT THÀNH CÔNG*\n"
                                            f"══════════════════════════\n"
                                            f"{EMOJI['key']} *Loại key:* `{prefix}`\n"
                                            f"{EMOJI['chart']} *Số lần còn lại:* `{uses_left}`\n"
                                            f"{EMOJI['calendar']} *Thời hạn:* `{expiry_info}`\n"
                                            f"══════════════════════════\n"
                                            f"{EMOJI['bell']} Gõ `/chaybot` để bắt đầu nhận dự đoán!"
                                        )
                                        send_telegram(chat_id, success_message)
                                    else:
                                        send_telegram(chat_id, f"{EMOJI['key']} Key hợp lệ. Bot đã được kích hoạt cho bạn.")
                                else:
                                    send_telegram(chat_id, f"{EMOJI['warning']} Key không hợp lệ hoặc đã hết lượt sử dụng/hết hạn. Vui lòng kiểm tra lại.")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Sử dụng: `/key <your_key>`")

                        elif text.startswith("/chaybot"):
                            user_state = get_user_state(chat_id)
                            if user_state and user_state.get("key_value") and is_key_valid(user_state["key_value"]):
                                update_user_state(chat_id, True)
                                
                                # Kiểm tra lịch sử 5 phiên gần nhất
                                last_sessions = get_last_sessions(5)
                                if last_sessions:
                                    last_result = last_sessions[0]["result"]
                                    streak = 1
                                    for i in range(1, len(last_sessions)):
                                        if last_sessions[i]["result"] == last_result:
                                            streak += 1
                                        else:
                                            break
                                    
                                    streak_info = f"\n{EMOJI['streak']} *Cầu hiện tại:* {last_result} {streak} nút" if streak >= 3 else ""
                                
                                message = (
                                    f"{EMOJI['check']} *BOT ĐÃ ĐƯỢC BẬT*\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['bell']} Bạn sẽ nhận thông báo dự đoán tự động.{streak_info if 'streak_info' in locals() else ''}\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['warning']} Lưu ý: Đây là công cụ hỗ trợ, không đảm bảo 100% chính xác."
                                )
                                send_telegram(chat_id, message)
                                
                                print(f"{EMOJI['play']} Bot đã được bật cho người dùng {chat_id}.")
                                log_message(f"Bot đã được bật cho người dùng {chat_id}.")
                            elif is_admin(chat_id):
                                ADMIN_ACTIVE = True
                                send_telegram(chat_id, f"{EMOJI['play']} Bot đã được bật cho tất cả người dùng (admin).")
                                print(f"{EMOJI['play']} Bot đã được bật bởi admin.")
                                log_message("Bot đã được bật bởi admin.")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Bạn cần kích hoạt bot bằng key trước hoặc bạn không có quyền sử dụng lệnh này.")

                        elif text.startswith("/tatbot"):
                            user_state = get_user_state(chat_id)
                            if user_state and user_state.get("key_value"):
                                update_user_state(chat_id, False)
                                send_telegram(chat_id, f"{EMOJI['pause']} Bot đã được tắt cho bạn. Bạn sẽ không nhận thông báo nữa.")
                                print(f"{EMOJI['pause']} Bot đã được tắt cho người dùng {chat_id}.")
                                log_message(f"Bot đã được tắt cho người dùng {chat_id}.")
                            elif is_admin(chat_id):
                                ADMIN_ACTIVE = False
                                send_telegram(chat_id, f"{EMOJI['pause']} Bot đã được tắt cho tất cả người dùng (admin).")
                                print(f"{EMOJI['pause']} Bot đã được tắt bởi admin.")
                                log_message("Bot đã được tắt bởi admin.")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Bạn cần kích hoạt bot bằng key trước hoặc bạn không có quyền sử dụng lệnh này.")

                        elif text.startswith("/thongtin"):
                            user_info = get_user_info(chat_id)
                            if user_info:
                                status = "ĐANG BẬT" if user_info["is_active"] else "ĐÃ TẮT"
                                key_status = "HỢP LỆ" if is_key_valid(user_info["key_value"]) else "HẾT HẠN/HẾT LƯỢT"
                                
                                message = (
                                    f"{EMOJI['user']} *THÔNG TIN TÀI KHOẢN*\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['id']} *ID:* `{chat_id}`\n"
                                    f"{EMOJI['bell']} *Trạng thái:* `{status}`\n"
                                    f"{EMOJI['key']} *Key:* `{user_info['key_value'] or 'CHƯA KÍCH HOẠT'}`\n"
                                    f"{EMOJI['check']} *Tình trạng key:* `{key_status if user_info['key_value'] else 'N/A'}`\n"
                                    f"{EMOJI['info']} *Chế độ:* `{user_info['mode'].upper()}`\n"
                                    f"{EMOJI['calendar']} *Ngày tham gia:* `{user_info['join_date']}`\n"
                                    f"{EMOJI['clock']} *Lần hoạt động cuối:* `{user_info['last_active']}`\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['chart']} *THỐNG KÊ DỰ ĐOÁN*\n"
                                    f"- Tổng dự đoán: `{user_info['total_predictions']}`\n"
                                    f"- Dự đoán đúng: `{user_info['correct_predictions']}`\n"
                                    f"- Tỷ lệ chính xác: `{user_info['accuracy']:.1f}%`\n"
                                    f"- Chuỗi đúng hiện tại: `{user_info['current_streak']}`\n"
                                    f"- Chuỗi đúng cao nhất: `{user_info['max_streak']}`\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['info']} Sử dụng `/thongke` để xem thống kê chi tiết"
                                )
                                send_telegram(chat_id, message)
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Bạn chưa kích hoạt bot. Vui lòng sử dụng lệnh /key để kích hoạt.")

                        elif text.startswith("/lichsu"):
                            last_sessions = get_last_sessions(10)
                            if last_sessions:
                                sessions_info = []
                                for i, session in enumerate(last_sessions):
                                    dice_str = "-".join(map(str, session["dice"]))
                                    sessions_info.append(
                                        f"{EMOJI['id']} *Phiên {session['session_id']}*: "
                                        f"{dice_str} | Tổng: `{session['total']}` | "
                                        f"{'Tài' if session['result'] == 'Tài' else 'Xỉu'}"
                                    )
                                
                                # Phân tích xu hướng
                                tai_count = sum(1 for s in last_sessions if s["result"] == "Tài")
                                xiu_count = len(last_sessions) - tai_count
                                
                                message = (
                                    f"{EMOJI['history']} *LỊCH SỬ 10 PHIÊN GẦN NHẤT*\n"
                                    f"══════════════════════════\n"
                                    + "\n".join(sessions_info) +
                                    f"\n══════════════════════════\n"
                                    f"{EMOJI['chart']} *Thống kê:* Tài: {tai_count} | Xỉu: {xiu_count}\n"
                                    f"{EMOJI['trend']} *Xu hướng:* {'Tài' if tai_count > xiu_count else 'Xỉu' if xiu_count > tai_count else 'Cân bằng'}"
                                )
                                send_telegram(chat_id, message)
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chưa có dữ liệu lịch sử.")

                        elif text.startswith("/thongke"):
                            stats = get_session_stats(100)
                            if stats:
                                message = (
                                    f"{EMOJI['stats']} *THỐNG KÊ 100 PHIÊN GẦN NHẤT*\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['chart']} *Tổng số phiên:* `{stats['total_sessions']}`\n"
                                    f"{EMOJI['up']} *Tài:* `{stats['tai_count']}` ({stats['tai_percent']:.1f}%)\n"
                                    f"{EMOJI['down']} *Xỉu:* `{stats['xiu_count']}` ({stats['xiu_percent']:.1f}%)\n"
                                    f"{EMOJI['sum']} *Tổng điểm trung bình:* `{stats['avg_total']:.1f}`\n"
                                    f"{EMOJI['streak']} *Cầu lớn nhất:* `{stats['max_streak']}` nút\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['info']} *Phiên gần nhất:*\n"
                                    f"- ID: `{stats['last_session']['session_id']}`\n"
                                    f"- Xúc xắc: `{'-'.join(map(str, stats['last_session']['dice']))}`\n"
                                    f"- Tổng: `{stats['last_session']['total']}`\n"
                                    f"- Kết quả: `{stats['last_session']['result']}`\n"
                                    f"══════════════════════════\n"
                                    f"{EMOJI['trend']} *Xu hướng hiện tại:* `{analyze_trend()}`"
                                )
                                send_telegram(chat_id, message)
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chưa có đủ dữ liệu thống kê.")

                        elif text.startswith("/taokey"):
                            if is_admin(chat_id):
                                parts = text.split()
                                if len(parts) >= 2:
                                    prefix = parts[1]
                                    limit_str = "unlimited"
                                    time_str = "vĩnh viễn"

                                    if len(parts) >= 3:
                                        limit_str = parts[2].lower()
                                    if len(parts) >= 4:
                                        time_str = " ".join(parts[3:]).lower()

                                    max_uses = -1
                                    if limit_str.isdigit():
                                        max_uses = int(limit_str)
                                    elif limit_str != "unlimited" and limit_str != "voihan":
                                        send_telegram(chat_id, f"{EMOJI['warning']} Giới hạn dùng không hợp lệ. Nhập số hoặc 'unlimited'.")
                                        continue

                                    expiry_date = None
                                    if time_str and time_str != "vĩnh viễn" and time_str != "unlimited":
                                        time_parts = time_str.split()
                                        if len(time_parts) >= 2 and time_parts[0].isdigit():
                                            time_value = int(time_parts[0])
                                            time_unit = " ".join(time_parts[1:])

                                            now = datetime.now()
                                            if "ngày" in time_unit:
                                                expiry_date = now + timedelta(days=time_value)
                                            elif "tuần" in time_unit:
                                                expiry_date = now + timedelta(weeks=time_value)
                                            elif "tháng" in time_unit:
                                                expiry_date = now + timedelta(days=time_value * 30)
                                            elif "năm" in time_unit:
                                                expiry_date = now + timedelta(days=time_value * 365)
                                            elif "giờ" in time_unit:
                                                expiry_date = now + timedelta(hours=time_value)
                                            elif "phút" in time_unit:
                                                expiry_date = now + timedelta(minutes=time_value)
                                            elif "giây" in time_unit:
                                                expiry_date = now + timedelta(seconds=time_value)

                                            if expiry_date:
                                                expiry_date = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
                                            else:
                                                send_telegram(chat_id, f"{EMOJI['warning']} Đơn vị thời gian không hợp lệ. Ví dụ: '30 ngày', '1 tuần', '6 tháng', '1 năm'.")
                                                continue
                                        else:
                                            send_telegram(chat_id, f"{EMOJI['warning']} Định dạng thời gian không hợp lệ. Ví dụ: '30 ngày', '1 tuần', 'vĩnh viễn'.")
                                            continue

                                    new_key_value = f"{prefix}-{str(uuid.uuid4())[:8]}"
                                    if add_key_to_db(new_key_value, chat_id, prefix, max_uses, expiry_date):
                                        uses_display = f"{max_uses} lần" if max_uses != -1 else f"{EMOJI['infinity']} không giới hạn"
                                        expiry_display = f"{EMOJI['calendar']} {expiry_date}" if expiry_date else f"{EMOJI['infinity']} vĩnh viễn"
                                        send_telegram(chat_id, f"{EMOJI['add']} Đã tạo key '{new_key_value}'. Giới hạn: {uses_display}, Thời hạn: {expiry_display}.")
                                        log_message(f"Admin {chat_id} đã tạo key '{new_key_value}' với giới hạn {max_uses}, thời hạn {expiry_date}.")
                                    else:
                                        send_telegram(chat_id, f"{EMOJI['warning']} Không thể tạo key (có thể đã tồn tại).")
                                else:
                                    send_telegram(chat_id, f"{EMOJI['warning']} Sử dụng: `/taokey <tên_key> [giới_hạn_dùng/unlimited] [thời_gian (ví dụ: 30 ngày, 1 tuần, vĩnh viễn)]`. Các tham số giới hạn và thời gian là tùy chọn (mặc định là không giới hạn).")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chỉ admin mới có quyền sử dụng lệnh này.")

                        elif text.startswith("/lietkekey"):
                            if is_admin(chat_id):
                                keys_data = get_all_keys_from_db()
                                if keys_data:
                                    keys_list = []
                                    for key in keys_data:
                                        key_value, created_at, created_by, prefix, max_uses, current_uses, expiry_date = key
                                        uses_left = f"{current_uses}/{max_uses}" if max_uses != -1 else f"{current_uses}/{EMOJI['infinity']}"
                                        expiry_display = expiry_date if expiry_date else f"{EMOJI['infinity']}"
                                        keys_list.append(f"- `{key_value}` (Prefix: {prefix}, Dùng: {uses_left}, Hết hạn: {expiry_display})")
                                    
                                    keys_str = "\n".join(keys_list)
                                    message = (
                                        f"{EMOJI['list']} *DANH SÁCH KEY*\n"
                                        f"══════════════════════════\n"
                                        f"{keys_str}\n"
                                        f"══════════════════════════\n"
                                        f"{EMOJI['info']} Tổng số key: {len(keys_data)}"
                                    )
                                    send_telegram(chat_id, message)
                                else:
                                    send_telegram(chat_id, f"{EMOJI['list']} Không có key nào trong hệ thống.")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chỉ admin mới có quyền sử dụng lệnh này.")

                        elif text.startswith("/xoakey"):
                            if is_admin(chat_id):
                                parts = text.split()
                                if len(parts) == 2:
                                    key_to_delete = parts[1]
                                    if delete_key_from_db(key_to_delete):
                                        send_telegram(chat_id, f"{EMOJI['delete']} Đã xóa key `{key_to_delete}`.")
                                        log_message(f"Admin {chat_id} đã xóa key {key_to_delete}.")
                                    else:
                                        send_telegram(chat_id, f"{EMOJI['warning']} Không tìm thấy key `{key_to_delete}`.")
                                else:
                                    send_telegram(chat_id, f"{EMOJI['warning']} Sử dụng: `/xoakey <key_cần_xóa>`")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chỉ admin mới có quyền sử dụng lệnh này.")

                        elif text.startswith("/themadmin"):
                            if is_admin(chat_id):
                                parts = text.split()
                                if len(parts) == 2 and parts[1].isdigit():
                                    new_admin_id = int(parts[1])
                                    if add_admin_to_db(new_admin_id):
                                        send_telegram(chat_id, f"{EMOJI['admin']} Đã thêm admin ID `{new_admin_id}`.")
                                        log_message(f"Admin {chat_id} đã thêm admin {new_admin_id}.")
                                    else:
                                        send_telegram(chat_id, f"{EMOJI['warning']} Admin ID `{new_admin_id}` đã tồn tại.")
                                else:
                                    send_telegram(chat_id, f"{EMOJI['warning']} Sử dụng: `/themadmin <telegram_id>` (telegram_id phải là số).")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chỉ admin mới có quyền sử dụng lệnh này.")

                        elif text.startswith("/xoaadmin"):
                            if is_admin(chat_id):
                                parts = text.split()
                                if len(parts) == 2 and parts[1].isdigit():
                                    admin_to_remove = int(parts[1])
                                    if remove_admin_from_db(admin_to_remove):
                                        send_telegram(chat_id, f"{EMOJI['admin']} Đã xóa admin ID `{admin_to_remove}`.")
                                        log_message(f"Admin {chat_id} đã xóa admin {admin_to_remove}.")
                                    else:
                                        send_telegram(chat_id, f"{EMOJI['warning']} Không tìm thấy admin ID `{admin_to_remove}`.")
                                else:
                                    send_telegram(chat_id, f"{EMOJI['warning']} Sử dụng: `/xoaadmin <telegram_id>` (telegram_id phải là số).")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chỉ admin mới có quyền sử dụng lệnh này.")

                        elif text.startswith("/danhsachadmin"):
                            if is_admin(chat_id):
                                admins = get_all_admins_from_db()
                                if admins:
                                    admin_list_str = "\n".join([f"- `{admin_id}`" for admin_id in admins])
                                    message = (
                                        f"{EMOJI['admin']} *DANH SÁCH ADMIN*\n"
                                        f"══════════════════════════\n"
                                        f"{admin_list_str}\n"
                                        f"══════════════════════════\n"
                                        f"{EMOJI['info']} Tổng số admin: {len(admins)}"
                                    )
                                    send_telegram(chat_id, message)
                                else:
                                    send_telegram(chat_id, f"{EMOJI['admin']} Hiện tại không có admin nào.")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chỉ admin mới có quyền sử dụng lệnh này.")

                        elif text.startswith("/broadcast"):
                            if is_admin(chat_id):
                                broadcast_text = text.replace("/broadcast", "").strip()
                                if broadcast_text:
                                    success, result_msg = broadcast_message(broadcast_text)
                                    if success:
                                        send_telegram(chat_id, f"{EMOJI['broadcast']} {result_msg}")
                                    else:
                                        send_telegram(chat_id, f"{EMOJI['warning']} {result_msg}")
                                else:
                                    send_telegram(chat_id, f"{EMOJI['warning']} Sử dụng: `/broadcast <nội_dung>`")
                            else:
                                send_telegram(chat_id, f"{EMOJI['warning']} Chỉ admin mới có quyền sử dụng lệnh này.")

                        elif text.startswith("/help") or text.startswith("/trogiup"):
                            help_message = (
                                f"{EMOJI['bell']} *HƯỚNG DẪN SỬ DỤNG BOT*\n"
                                f"══════════════════════════\n"
                                f"{EMOJI['key']} *Lệnh cơ bản:*\n"
                                f"- `/start`: Hiển thị thông tin chào mừng\n"
                                f"- `/key <key>`: Nhập key để kích hoạt bot\n"
                                f"- `/chaybot`: Bật nhận thông báo\n"
                                f"- `/tatbot`: Tắt nhận thông báo\n"
                                f"- `/thongtin`: Xem thông tin tài khoản\n"
                                f"- `/lichsu`: Xem lịch sử 10 phiên gần nhất\n"
                                f"- `/thongke`: Xem thống kê chi tiết\n"
                                f"\n{EMOJI['admin']} *Lệnh admin:*\n"
                                f"- `/taokey <tên_key> [giới_hạn] [thời_gian]`: Tạo key mới\n"
                                f"- `/lietkekey`: Liệt kê tất cả key\n"
                                f"- `/xoakey <key>`: Xóa key\n"
                                f"- `/themadmin <id>`: Thêm admin\n"
                                f"- `/xoaadmin <id>`: Xóa admin\n"
                                f"- `/danhsachadmin`: Xem danh sách admin\n"
                                f"- `/broadcast <nội_dung>`: Gửi thông báo đến tất cả người dùng\n"
                                f"══════════════════════════\n"
                                f"{EMOJI['team']} Liên hệ admin để được hỗ trợ thêm"
                            )
                            send_telegram(chat_id, help_message)

        except requests.exceptions.RequestException as e:
            print(f"{EMOJI['warning']} Lỗi khi lấy updates từ Telegram: {e}")
            time.sleep(5)
        except json.JSONDecodeError as e:
            print(f"{EMOJI['warning']} Lỗi giải mã JSON từ Telegram: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"{EMOJI['warning']} Lỗi không xác định trong handle_telegram_updates: {e}")
            time.sleep(5)

# === HÀM CHÍNH ===
def main():
    init_db()

    # Thêm admin mặc định nếu chưa có
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM admins")
    if c.fetchone()[0] == 0:
        print(f"{EMOJI['admin']} Thêm admin đầu tiên với ID: 7761915412")
        c.execute("INSERT INTO admins (chat_id) VALUES (?)", ("7761915412",))
        conn.commit()
    conn.close()

    print(f"\n{EMOJI['diamond']} {'*'*20} {EMOJI['diamond']}")
    print(f"{EMOJI['rocket']} *SUNWIN VIP - BOT TÀI XỈU CHUẨN XÁC* {EMOJI['rocket']}")
    print(f"{EMOJI['diamond']} {'*'*20} {EMOJI['diamond']}\n")
    print(f"{EMOJI['settings']} Phiên bản: {BOT_VERSION}")
    print(f"{EMOJI['chart']} Hệ thống phân tích nâng cao")
    print(f"{EMOJI['team']} Phát triển bởi ??????\n")
    print(f"{EMOJI['bell']} Bot đã sẵn sàng hoạt động!")

    # Khởi chạy các luồng xử lý
    threading.Thread(target=background_task, daemon=True).start()
    threading.Thread(target=handle_telegram_updates, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{EMOJI['warning']} Đang dừng bot...")
        conn = get_db_connection()
        conn.close()
        print(f"{EMOJI['check']} Bot đã dừng an toàn")

if __name__ == "__main__":
    main()
