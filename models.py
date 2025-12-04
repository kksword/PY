import sqlite3
from datetime import datetime
import json


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path) #创建数据库连接
        cursor = conn.cursor() #创建游标

        # 交换机表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS switches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ip TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT DEFAULT 'unknown',
                last_seen TIMESTAMP
            )
        ''')

        # 端口状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                switch_id INTEGER,
                port_index INTEGER,
                port_name TEXT,
                admin_status TEXT,
                oper_status TEXT,
                in_errors INTEGER DEFAULT 0,
                out_errors INTEGER DEFAULT 0,
                in_broadcast_pkts INTEGER DEFAULT 0,
                out_broadcast_pkts INTEGER DEFAULT 0,
                last_change TIMESTAMP,
                collected_at TIMESTAMP,
                FOREIGN KEY (switch_id) REFERENCES switches (id)
            )
        ''')

        # 告警记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                switch_id INTEGER,
                port_index INTEGER,
                alert_type TEXT,
                description TEXT,
                severity TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (switch_id) REFERENCES switches (id)
            )
        ''')

        # 自动化操作记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                switch_id INTEGER,
                port_index INTEGER,
                operation_type TEXT,
                command TEXT,
                result TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (switch_id) REFERENCES switches (id)
            )
        ''')

        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)


class SwitchMonitor:
    def __init__(self, db_path):
        self.db = Database(db_path) #这里调用database类创建数据库连接，并设计数据库结构

    def save_port_data(self, switch_ip, port_data):
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # 获取交换机ID
        cursor.execute("SELECT id FROM switches WHERE ip = ?", (switch_ip,))
        switch = cursor.fetchone()
        if not switch:
            return
        switch_id = switch[0]

        # 保存端口数据
        for port in port_data:
            cursor.execute('''
                INSERT INTO ports 
                (switch_id, port_index, port_name, admin_status, oper_status, 
                 in_errors, out_errors, in_broadcast_pkts, out_broadcast_pkts, 
                 last_change, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                switch_id, port['index'], port.get('name', ''),
                port.get('admin_status', ''), port.get('oper_status', ''),
                port.get('in_errors', 0), port.get('out_errors', 0),
                port.get('in_broadcast_pkts', 0), port.get('out_broadcast_pkts', 0),
                port.get('last_change'), datetime.now()
            ))

        conn.commit()
        conn.close()