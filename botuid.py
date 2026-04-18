"""
TIKTOK UID TOOL BETA - TELEGRAM BOT VERSION
Author: Long Ng Văn
Version: 3.2.0 - Premium Edition với mua gói bằng số dư
"""

import requests
import json
import time
import os
import sys
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import telebot
from telebot import types
import threading
import hashlib
import re
import random
import string
from collections import defaultdict

# ==================== CẤU HÌNH ====================
class Config:
    """Cấu hình chung"""
    # Thông tin Developer
    DEV_NAME = "Long Ng Văn"
    DEV_FB = "facebook.com/longngvan.it"
    DEV_ZALO = "033.406.3029"
    DEV_EMAIL = "longngvanmmo@gmail.com"
    DEV_GITHUB = "github.com/longngvan"
    DEV_WEBSITE = "smmboost.id.vn"
    
    # Thông tin Bot - THAY ĐỔI CÁI NÀY
    BOT_TOKEN = "8456385484:AAGwIMMR4HmFS4kppN7xZxJaeQRr1zO5Yqk"  # Thay token của bạn vào đây
    ADMIN_IDS = [5444123544]  # Thay bằng ID Telegram của admin
    
    VERSION = "3.2.0"
    APP_NAME = "TIKTOK UID TOOL BOT - ULTIMATE"
    RELEASE_DATE = "14/03/2024"
    
    # Cấu hình gói dịch vụ
    FREE_DAILY_LIMIT = 5
    FREE_BATCH_LIMIT = 3
    
    # Cấu hình Referral
    REFERRAL_BONUS = 500  # Thưởng 500đ cho người giới thiệu
    REFERRAL_EXTRA_REQUESTS = 3  # Tặng thêm 3 lượt cho người mới
    
    # Tự động gia hạn
    AUTO_RENEW_DAYS_BEFORE = 3  # Nhắc nhở trước 3 ngày
    
    # Giới hạn
    MAX_USERNAME_LENGTH = 50
    MAX_BATCH_SIZE = 100
    REQUEST_DELAY = 1
    MAX_RESULTS_HISTORY = 100
    MAX_CODES_PER_PAGE = 10
    
    # Đường dẫn
    DATA_DIR = "data"
    AVATARS_DIR = "avatars"
    TEMP_DIR = "temp"
    BACKUP_DIR = "backups"
    LOGS_DIR = "logs"
    
    # API
    TIKTOK_API = "https://www.tikwm.com/api/"
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # Cổng thanh toán
    MOMO_PHONE = "0334063029"
    MOMO_NAME = "LONG NV"
    BANK_ACCOUNT = "123456789"
    BANK_NAME = "Vietcombank"
    
    # Giá các gói
    PRICES = {
        "basic": 50000,
        "premium": 100000,
        "vip": 200000,
        "enterprise": 500000
    }

# ==================== DATABASE CLASS ====================
class Database:
    def __init__(self):
        self._ensure_directories()
        self.users = self._load_json("users.json", {})
        self.transactions = self._load_json("transactions.json", [])
        self.codes = self._load_json("codes.json", {})
        self.support_tickets = self._load_json("support_tickets.json", [])
        self.broadcast_history = self._load_json("broadcast_history.json", [])
        
    def _ensure_directories(self):
        for dir_name in [Config.DATA_DIR, Config.AVATARS_DIR, Config.TEMP_DIR, 
                         Config.BACKUP_DIR, Config.LOGS_DIR]:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
    
    def _load_json(self, filename, default):
        filepath = f"{Config.DATA_DIR}/{filename}"
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Lỗi đọc file {filename}: {e}")
                return default
        return default
    
    def _save_json(self, filename, data):
        filepath = f"{Config.DATA_DIR}/{filename}"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Lỗi ghi file {filename}: {e}")
            return False
    
    # ============ USER MANAGEMENT ============
    
    def add_user(self, user_id, username=None, first_name=None, referrer_id=None):
        """Thêm user mới, có hỗ trợ referral"""
        user_id = str(user_id)
        now = datetime.now().isoformat()
        
        is_new = False
        if user_id not in self.users:
            is_new = True
            self.users[user_id] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'registered_at': now,
                'last_active': now,
                'package': 'free',
                'package_expiry': None,
                'total_requests': 0,
                'daily_requests': 0,
                'last_reset': now,
                'history': [],
                'balance': 0,
                'referrals': [],
                'referred_by': None,
                'support_tickets': [],
                'notifications': True,
                'notes': ''  # Ghi chú của admin
            }
        else:
            self.users[user_id]['last_active'] = now
            self.users[user_id]['username'] = username
            self.users[user_id]['first_name'] = first_name
        
        # Xử lý referral nếu có
        if is_new and referrer_id and str(referrer_id) != user_id:
            self.process_referral(user_id, str(referrer_id))
        
        self._save_json("users.json", self.users)
        return self.users[user_id]
    
    def process_referral(self, new_user_id, referrer_id):
        """Xử lý khi có người dùng mới từ giới thiệu"""
        if referrer_id in self.users:
            # Thưởng cho người giới thiệu
            self.users[referrer_id]['balance'] = self.users[referrer_id].get('balance', 0) + Config.REFERRAL_BONUS
            self.users[referrer_id]['referrals'] = self.users[referrer_id].get('referrals', []) + [new_user_id]
            
            # Tặng thêm lượt check cho người mới
            self.users[new_user_id]['daily_requests'] = Config.REFERRAL_EXTRA_REQUESTS
            self.users[new_user_id]['referred_by'] = referrer_id
            
            # Ghi log transaction
            self.add_transaction(
                user_id=referrer_id,
                amount=Config.REFERRAL_BONUS,
                package='referral_bonus',
                method='system',
                status='completed',
                description=f'Thưởng giới thiệu user {new_user_id}'
            )
    
    def get_user(self, user_id):
        return self.users.get(str(user_id), {})
    
    def update_user(self, user_id, **kwargs):
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id].update(kwargs)
            self._save_json("users.json", self.users)
            return True
        return False
    
    # ============ BALANCE MANAGEMENT ============
    
    def add_balance(self, user_id, amount, admin_id=None, note=''):
        """Cộng tiền cho user (có thể do admin cộng thủ công)"""
        user_id = str(user_id)
        if user_id not in self.users:
            return False, "User không tồn tại!"
        
        if amount <= 0:
            return False, "Số tiền phải lớn hơn 0!"
        
        # Cộng tiền
        self.users[user_id]['balance'] = self.users[user_id].get('balance', 0) + amount
        
        # Ghi log giao dịch
        method = 'admin_manual' if admin_id else 'system'
        description = f'Nạp tiền thủ công' + (f' bởi admin {admin_id}' if admin_id else '')
        if note:
            description += f' - {note}'
        
        self.add_transaction(
            user_id=user_id,
            amount=amount,
            package='deposit',
            method=method,
            status='completed',
            description=description
        )
        
        self._save_json("users.json", self.users)
        
        # Ghi log admin action
        if admin_id:
            self.add_admin_log(admin_id, f"Đã cộng {amount}đ cho user {user_id}" + (f" - {note}" if note else ""))
        
        return True, f"Đã cộng {amount:,}đ thành công!"
    
    def deduct_balance(self, user_id, amount, admin_id=None, note=''):
        """Trừ tiền của user (khi mua gói hoặc admin trừ)"""
        user_id = str(user_id)
        if user_id not in self.users:
            return False, "User không tồn tại!"
        
        current_balance = self.users[user_id].get('balance', 0)
        if current_balance < amount:
            return False, f"Số dư không đủ! Hiện có {current_balance:,}đ, cần {amount:,}đ"
        
        # Trừ tiền
        self.users[user_id]['balance'] = current_balance - amount
        
        # Ghi log giao dịch
        method = 'admin_manual_deduct' if admin_id else 'system'
        description = f'Trừ tiền thủ công' + (f' bởi admin {admin_id}' if admin_id else '')
        if note:
            description += f' - {note}'
        
        self.add_transaction(
            user_id=user_id,
            amount=-amount,  # Số âm để biết là trừ
            package='withdrawal',
            method=method,
            status='completed',
            description=description
        )
        
        self._save_json("users.json", self.users)
        
        if admin_id:
            self.add_admin_log(admin_id, f"Đã trừ {amount}đ của user {user_id}" + (f" - {note}" if note else ""))
        
        return True, f"Đã trừ {amount:,}đ thành công!"
    
    def get_balance(self, user_id):
        """Lấy số dư của user"""
        user_id = str(user_id)
        return self.users.get(user_id, {}).get('balance', 0)
    
    # ============ PURCHASE WITH BALANCE ============
    
    def purchase_package_with_balance(self, user_id, package):
        """Mua gói bằng số dư trong tài khoản"""
        user_id = str(user_id)
        if user_id not in self.users:
            return False, "User không tồn tại!"
        
        # Kiểm tra gói có tồn tại không
        if package not in Config.PRICES:
            return False, "Gói không hợp lệ!"
        
        price = Config.PRICES[package]
        current_balance = self.users[user_id].get('balance', 0)
        
        # Kiểm tra số dư
        if current_balance < price:
            return False, f"Số dư không đủ! Cần {price:,}đ, hiện có {current_balance:,}đ"
        
        # Trừ tiền
        self.users[user_id]['balance'] = current_balance - price
        
        # Kích hoạt gói (30 ngày)
        self.activate_package(user_id, package, 30)
        
        # Ghi log giao dịch
        self.add_transaction(
            user_id=user_id,
            amount=price,
            package=package,
            method='balance',
            status='completed',
            description=f'Mua gói {package} bằng số dư'
        )
        
        self._save_json("users.json", self.users)
        
        return True, f"Đã mua gói {package} thành công!"
    
    # ============ ADMIN LOGS ============
    
    def add_admin_log(self, admin_id, action):
        """Ghi log hành động của admin"""
        log_file = f"{Config.LOGS_DIR}/admin_actions.log"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] Admin {admin_id}: {action}\n")
        except:
            pass
    
    # ============ PACKAGE MANAGEMENT ============
    
    def get_package_info(self, package):
        packages = {
            "free": {
                "name": "Miễn phí",
                "daily_limit": Config.FREE_DAILY_LIMIT,
                "batch_limit": Config.FREE_BATCH_LIMIT,
                "can_download_avatar": False,
                "can_export": False,
                "price": 0,
                "features": ["5 lượt/ngày", "Batch 3 user"]
            },
            "basic": {
                "name": "Cơ bản",
                "daily_limit": 50,
                "batch_limit": 20,
                "can_download_avatar": True,
                "can_export": True,
                "price": Config.PRICES["basic"],
                "features": ["50 lượt/ngày", "Batch 20 user", "Tải avatar", "Xuất file"]
            },
            "premium": {
                "name": "Cao cấp",
                "daily_limit": 200,
                "batch_limit": 50,
                "can_download_avatar": True,
                "can_export": True,
                "price": Config.PRICES["premium"],
                "features": ["200 lượt/ngày", "Batch 50 user", "Avatar HD", "Xuất Excel"]
            },
            "vip": {
                "name": "VIP",
                "daily_limit": 500,
                "batch_limit": 100,
                "can_download_avatar": True,
                "can_export": True,
                "price": Config.PRICES["vip"],
                "features": ["500 lượt/ngày", "Batch 100 user", "Ưu tiên", "Hỗ trợ 24/7"]
            },
            "enterprise": {
                "name": "Doanh nghiệp",
                "daily_limit": 2000,
                "batch_limit": 200,
                "can_download_avatar": True,
                "can_export": True,
                "price": Config.PRICES["enterprise"],
                "features": ["2000 lượt/ngày", "Batch 200 user", "API riêng", "Custom"]
            }
        }
        return packages.get(package, packages["free"])
    
    def check_limit(self, user_id):
        user_id = str(user_id)
        if user_id not in self.users:
            return True, "OK"
        
        user = self.users[user_id]
        
        # Reset daily nếu cần
        last_reset = user.get('last_reset')
        if last_reset:
            try:
                reset_date = datetime.fromisoformat(last_reset)
                if reset_date.date() < datetime.now().date():
                    user['daily_requests'] = 0
                    user['last_reset'] = datetime.now().isoformat()
                    self._save_json("users.json", self.users)
            except:
                pass
        
        # Kiểm tra giới hạn
        package = user.get('package', 'free')
        package_info = self.get_package_info(package)
        daily_limit = package_info['daily_limit']
        
        if user.get('daily_requests', 0) >= daily_limit:
            return False, f"Bạn đã đạt giới hạn {daily_limit} lượt/ngày!"
        
        return True, "OK"
    
    def increment_requests(self, user_id):
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id]['daily_requests'] = self.users[user_id].get('daily_requests', 0) + 1
            self.users[user_id]['total_requests'] = self.users[user_id].get('total_requests', 0) + 1
            self._save_json("users.json", self.users)
    
    def activate_package(self, user_id, package, duration=30):
        """Kích hoạt gói cho user"""
        user_id = str(user_id)
        if user_id not in self.users:
            return False
        
        now = datetime.now()
        
        # Tính ngày hết hạn
        current_expiry = self.users[user_id].get('package_expiry')
        if current_expiry and self.users[user_id]['package'] != 'free':
            try:
                current = datetime.fromisoformat(current_expiry)
                if current > now:
                    expiry = current + timedelta(days=duration)
                else:
                    expiry = now + timedelta(days=duration)
            except:
                expiry = now + timedelta(days=duration)
        else:
            expiry = now + timedelta(days=duration)
        
        self.users[user_id]['package'] = package
        self.users[user_id]['package_expiry'] = expiry.isoformat()
        self.users[user_id]['daily_requests'] = 0
        
        self._save_json("users.json", self.users)
        return True
    
    def check_expiring_packages(self):
        """Kiểm tra các gói sắp hết hạn"""
        expiring_users = []
        now = datetime.now()
        
        for user_id, user in self.users.items():
            if user.get('package') != 'free' and user.get('package_expiry'):
                try:
                    expiry = datetime.fromisoformat(user['package_expiry'])
                    days_left = (expiry - now).days
                    
                    if 0 < days_left <= Config.AUTO_RENEW_DAYS_BEFORE:
                        expiring_users.append({
                            'user_id': user_id,
                            'package': user['package'],
                            'days_left': days_left,
                            'expiry': expiry
                        })
                except:
                    pass
        
        return expiring_users
    
    def auto_renew_package(self, user_id):
        """Tự động gia hạn gói nếu có đủ tiền"""
        user_id = str(user_id)
        if user_id not in self.users:
            return False, "User không tồn tại"
        
        user = self.users[user_id]
        current_package = user.get('package', 'free')
        
        if current_package == 'free':
            return False, "User đang dùng gói free"
        
        package_info = self.get_package_info(current_package)
        price = package_info['price']
        balance = user.get('balance', 0)
        
        if balance >= price:
            # Trừ tiền
            user['balance'] = balance - price
            
            # Gia hạn thêm 30 ngày
            current_expiry = user.get('package_expiry')
            if current_expiry:
                try:
                    expiry = datetime.fromisoformat(current_expiry)
                    new_expiry = expiry + timedelta(days=30)
                except:
                    new_expiry = datetime.now() + timedelta(days=30)
            else:
                new_expiry = datetime.now() + timedelta(days=30)
            
            user['package_expiry'] = new_expiry.isoformat()
            
            # Ghi log
            self.add_transaction(
                user_id=user_id,
                amount=price,
                package=current_package,
                method='auto_renew',
                status='completed',
                description=f'Tự động gia hạn gói {current_package}'
            )
            
            self._save_json("users.json", self.users)
            return True, f"Đã gia hạn gói {current_package} thành công!"
        else:
            return False, f"Không đủ tiền! Cần {price:,}đ, hiện có {balance:,}đ"
    
    # ============ CODE MANAGEMENT ============
    
    def generate_code(self, package, duration=30, quantity=1, created_by=None):
        """Tạo nhiều mã kích hoạt cùng lúc"""
        codes = []
        
        for i in range(quantity):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            self.codes[code] = {
                'code': code,
                'package': package,
                'duration': duration,
                'created_by': str(created_by) if created_by else 'system',
                'created_at': datetime.now().isoformat(),
                'used_by': None,
                'used_at': None,
                'status': 'active'  # active, used, inactive
            }
            codes.append(code)
        
        self._save_json("codes.json", self.codes)
        return codes
    
    def activate_code(self, code, user_id):
        """Kích hoạt mã"""
        code = code.upper().strip()
        
        if code not in self.codes:
            return False, "Mã không tồn tại!"
        
        code_data = self.codes[code]
        
        # Kiểm tra trạng thái
        if code_data.get('status') != 'active':
            return False, "Mã đã được sử dụng hoặc vô hiệu!"
        
        if code_data.get('used_by'):
            return False, "Mã đã được sử dụng!"
        
        # Kích hoạt
        code_data['used_by'] = str(user_id)
        code_data['used_at'] = datetime.now().isoformat()
        code_data['status'] = 'used'
        
        # Kích hoạt gói
        self.activate_package(user_id, code_data['package'], code_data.get('duration', 30))
        
        self._save_json("codes.json", self.codes)
        return True, f"Kích hoạt thành công gói {code_data['package']}!"
    
    def delete_code(self, code, admin_id):
        """Xóa mã (admin only)"""
        code = code.upper().strip()
        
        if code not in self.codes:
            return False, "Mã không tồn tại!"
        
        # Xóa khỏi danh sách
        del self.codes[code]
        self._save_json("codes.json", self.codes)
        
        self.add_admin_log(admin_id, f"Đã xóa mã {code}")
        return True, f"Đã xóa mã {code}"
    
    def deactivate_code(self, code, admin_id):
        """Vô hiệu hóa mã (không xóa)"""
        code = code.upper().strip()
        
        if code not in self.codes:
            return False, "Mã không tồn tại!"
        
        self.codes[code]['status'] = 'inactive'
        self._save_json("codes.json", self.codes)
        
        self.add_admin_log(admin_id, f"Đã vô hiệu hóa mã {code}")
        return True, f"Đã vô hiệu hóa mã {code}"
    
    def get_codes(self, status=None, package=None, page=1):
        """Lấy danh sách mã có phân trang"""
        codes_list = []
        
        for code, data in self.codes.items():
            # Lọc theo trạng thái
            if status and data.get('status') != status:
                continue
            # Lọc theo gói
            if package and data.get('package') != package:
                continue
            
            codes_list.append(data)
        
        # Sắp xếp theo thời gian tạo mới nhất
        codes_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Phân trang
        start = (page - 1) * Config.MAX_CODES_PER_PAGE
        end = start + Config.MAX_CODES_PER_PAGE
        paginated = codes_list[start:end]
        
        return paginated, len(codes_list)
    
    # ============ TRANSACTION MANAGEMENT ============
    
    def add_transaction(self, user_id, amount, package, method, status='pending', description=''):
        """Thêm giao dịch mới"""
        transaction = {
            'id': self._generate_id(),
            'user_id': str(user_id),
            'amount': amount,
            'package': package,
            'method': method,
            'status': status,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.transactions.append(transaction)
        self._save_json("transactions.json", self.transactions)
        return transaction
    
    def update_transaction(self, trans_id, status, notes=''):
        """Cập nhật trạng thái giao dịch"""
        for trans in self.transactions:
            if trans['id'] == trans_id:
                trans['status'] = status
                trans['updated_at'] = datetime.now().isoformat()
                if notes:
                    trans['notes'] = notes
                
                # Nếu thành công và là nạp tiền, cập nhật balance
                if status == 'completed' and trans['method'] != 'auto_renew' and trans['amount'] > 0:
                    user_id = trans['user_id']
                    if user_id in self.users:
                        self.users[user_id]['balance'] = self.users[user_id].get('balance', 0) + trans['amount']
                        self._save_json("users.json", self.users)
                
                self._save_json("transactions.json", self.transactions)
                return True
        return False
    
    def get_user_transactions(self, user_id, limit=10):
        """Lấy lịch sử giao dịch của user"""
        user_id = str(user_id)
        user_trans = [t for t in self.transactions if t['user_id'] == user_id]
        user_trans.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return user_trans[:limit]
    
    def get_all_transactions(self, limit=50):
        """Lấy tất cả giao dịch (cho admin)"""
        sorted_trans = sorted(self.transactions, key=lambda x: x.get('created_at', ''), reverse=True)
        return sorted_trans[:limit]
    
    # ============ SUPPORT TICKETS ============
    
    def create_ticket(self, user_id, message, message_id):
        """Tạo ticket hỗ trợ mới"""
        ticket = {
            'id': self._generate_id(),
            'user_id': str(user_id),
            'message': message,
            'message_id': message_id,
            'status': 'open',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'responses': [],
            'assigned_to': None
        }
        
        self.support_tickets.append(ticket)
        self._save_json("support_tickets.json", self.support_tickets)
        
        # Cập nhật user's tickets
        if str(user_id) in self.users:
            if 'support_tickets' not in self.users[str(user_id)]:
                self.users[str(user_id)]['support_tickets'] = []
            self.users[str(user_id)]['support_tickets'].append(ticket['id'])
            self._save_json("users.json", self.users)
        
        return ticket
    
    def reply_ticket(self, ticket_id, admin_id, message):
        """Admin trả lời ticket"""
        for ticket in self.support_tickets:
            if ticket['id'] == ticket_id:
                ticket['responses'].append({
                    'admin_id': str(admin_id),
                    'message': message,
                    'created_at': datetime.now().isoformat()
                })
                ticket['status'] = 'answered'
                ticket['updated_at'] = datetime.now().isoformat()
                self._save_json("support_tickets.json", self.support_tickets)
                return True
        return False
    
    def close_ticket(self, ticket_id):
        """Đóng ticket"""
        for ticket in self.support_tickets:
            if ticket['id'] == ticket_id:
                ticket['status'] = 'closed'
                ticket['updated_at'] = datetime.now().isoformat()
                self._save_json("support_tickets.json", self.support_tickets)
                return True
        return False
    
    def get_open_tickets(self):
        """Lấy danh sách ticket đang mở"""
        return [t for t in self.support_tickets if t['status'] in ['open', 'answered']]
    
    # ============ BROADCAST MANAGEMENT ============
    
    def add_broadcast(self, admin_id, message, total_sent, success, failed):
        """Ghi log broadcast"""
        broadcast = {
            'id': self._generate_id(),
            'admin_id': str(admin_id),
            'message': message[:100],  # Lưu 100 ký tự đầu
            'total_sent': total_sent,
            'success': success,
            'failed': failed,
            'created_at': datetime.now().isoformat()
        }
        
        self.broadcast_history.append(broadcast)
        
        # Giữ 100 broadcast gần nhất
        if len(self.broadcast_history) > 100:
            self.broadcast_history = self.broadcast_history[-100:]
        
        self._save_json("broadcast_history.json", self.broadcast_history)
        return broadcast
    
    # ============ HISTORY MANAGEMENT ============
    
    def add_to_history(self, user_id, username, uid):
        """Thêm vào lịch sử tra cứu"""
        user_id = str(user_id)
        if user_id in self.users:
            history_item = {
                'username': username,
                'uid': uid,
                'time': datetime.now().isoformat()
            }
            
            self.users[user_id]['history'].append(history_item)
            
            # Giữ 50 lịch sử gần nhất
            if len(self.users[user_id]['history']) > 50:
                self.users[user_id]['history'] = self.users[user_id]['history'][-50:]
            
            self._save_json("users.json", self.users)
    
    def get_detailed_history(self, user_id, days=7):
        """Lấy lịch sử chi tiết theo ngày"""
        user = self.get_user(user_id)
        history = user.get('history', [])
        
        if not history:
            return None
        
        # Lọc theo số ngày
        cutoff = datetime.now() - timedelta(days=days)
        recent = [h for h in history if datetime.fromisoformat(h['time']) > cutoff]
        
        # Thống kê theo ngày
        from collections import Counter
        dates = [datetime.fromisoformat(h['time']).strftime('%d/%m') for h in recent]
        daily_count = Counter(dates)
        
        # Thống kê theo user
        top_users = Counter()
        for h in recent:
            top_users[h['username']] += 1
        
        return {
            'total': len(recent),
            'daily': dict(sorted(daily_count.items(), reverse=True)),
            'top_users': dict(top_users.most_common(5)),
            'recent': recent[-10:]  # 10 gần nhất
        }
    
    # ============ STATISTICS ============
    
    def get_stats(self):
        """Lấy thống kê tổng quan"""
        total_users = len(self.users)
        
        # Active hôm nay
        today = datetime.now().date()
        active_today = sum(1 for u in self.users.values() 
                          if datetime.fromisoformat(u.get('last_active', '2000-01-01')).date() == today)
        
        total_requests = sum(u.get('total_requests', 0) for u in self.users.values())
        
        # Thống kê gói
        package_count = defaultdict(int)
        for u in self.users.values():
            package_count[u.get('package', 'free')] += 1
        
        # Doanh thu
        completed_trans = [t for t in self.transactions if t['status'] == 'completed' and t['amount'] > 0]
        total_revenue = sum(t['amount'] for t in completed_trans)
        
        # Tổng số dư users
        total_balance = sum(u.get('balance', 0) for u in self.users.values())
        
        # Referral stats
        total_referrals = sum(len(u.get('referrals', [])) for u in self.users.values())
        total_bonus_paid = sum(t['amount'] for t in self.transactions 
                              if t.get('method') == 'system' and 'referral' in t.get('description', '').lower())
        
        # Code stats
        active_codes = sum(1 for c in self.codes.values() if c.get('status') == 'active')
        used_codes = sum(1 for c in self.codes.values() if c.get('status') == 'used')
        
        # Support stats
        open_tickets = len(self.get_open_tickets())
        
        return {
            'total_users': total_users,
            'active_today': active_today,
            'total_requests': total_requests,
            'package_count': dict(package_count),
            'total_revenue': total_revenue,
            'total_balance': total_balance,
            'total_referrals': total_referrals,
            'total_bonus_paid': total_bonus_paid,
            'active_codes': active_codes,
            'used_codes': used_codes,
            'open_tickets': open_tickets,
            'total_transactions': len(self.transactions)
        }
    
    def _generate_id(self):
        """Tạo ID ngẫu nhiên"""
        return datetime.now().strftime('%Y%m%d%H%M%S') + ''.join(random.choices(string.digits, k=4))

# ==================== TIKTOK TOOL ====================
class TikTokTool:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': Config.USER_AGENT})
        self.cache = {}
    
    def get_user_info(self, username):
        try:
            username = username.replace('@', '').strip()
            
            if len(username) > Config.MAX_USERNAME_LENGTH:
                return None
            
            # Check cache
            if username in self.cache:
                cache_time, data = self.cache[username]
                if time.time() - cache_time < 300:
                    return data
            
            url = f"{Config.TIKTOK_API}user/info?unique_id=@{username}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    user_data = data.get('data', {})
                    user_info = user_data.get('user', {})
                    stats = user_data.get('stats', {})
                    
                    # Xử lý thời gian tạo
                    create_time = user_info.get('createTime', 0)
                    if create_time:
                        created_date = datetime.fromtimestamp(create_time).strftime('%d/%m/%Y %H:%M:%S')
                    else:
                        created_date = 'N/A'
                    
                    # Xử lý bio
                    bio = user_info.get('signature', '') or user_info.get('bio', '') or 'Chưa có tiểu sử'
                    
                    # Format số
                    follower_count = stats.get('followerCount', 0)
                    following_count = stats.get('followingCount', 0)
                    video_count = stats.get('videoCount', 0)
                    heart_count = stats.get('heartCount', 0) or stats.get('diggCount', 0)
                    
                    result = {
                        'UID': user_info.get('id', ''),
                        'USERNAME': user_info.get('uniqueId', username),
                        'NICKNAME': user_info.get('nickname', ''),
                        'FOLLOWERS': follower_count,
                        'FOLLOWING': following_count,
                        'VIDEOS': video_count,
                        'HEARTS': heart_count,
                        'BIO': bio,
                        'VERIFIED': user_info.get('verified', False),
                        'PRIVATE': user_info.get('privateAccount', False),
                        'CREATED': created_date,
                        'AVATAR': user_info.get('avatarLarger', '') or user_info.get('avatarMedium', ''),
                        'SEC_UID': user_info.get('secUid', ''),
                        'LIKES': stats.get('heartCount', 0) or stats.get('diggCount', 0),
                        'REGION': user_info.get('region', 'N/A'),
                        'LANGUAGE': user_info.get('language', 'N/A')
                    }
                    
                    if result['UID']:
                        self.cache[username] = (time.time(), result)
                        return result
                        
        except Exception as e:
            logging.error(f"Lỗi API: {e}")
        
        return None
    
    def search_users(self, keyword, count=10):
        try:
            url = f"{Config.TIKTOK_API}user/search?keywords={keyword}&count={count}"
            response = self.session.get(url)
            data = response.json()
            
            if data.get('code') == 0:
                users = data.get('data', [])
                results = []
                for user in users:
                    results.append({
                        'USERNAME': user.get('unique_id', ''),
                        'NICKNAME': user.get('nickname', ''),
                        'FOLLOWERS': user.get('follower_count', 0)
                    })
                return results
        except Exception as e:
            logging.error(f"Lỗi tìm kiếm: {e}")
        return []
    
    def download_avatar(self, user_info, user_id):
        if not user_info.get('AVATAR'):
            return None
        
        try:
            filename = f"{Config.AVATARS_DIR}/{user_id}_{user_info['USERNAME']}_{int(time.time())}.jpg"
            response = self.session.get(user_info['AVATAR'], stream=True, timeout=10)
            
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return filename
        except Exception as e:
            logging.error(f"Lỗi tải avatar: {e}")
        return None

# ==================== TELEGRAM BOT ====================
class TikTokBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token, parse_mode='HTML')
        self.db = Database()
        self.tool = TikTokTool()
        self.user_states = {}
        self.user_data = {}
        
        # Register handlers
        self.register_handlers()
        
        # Start background tasks
        self.start_background_tasks()
    
    def register_handlers(self):
        """Đăng ký tất cả handlers"""
        
        # User commands
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.handle_start(message)
        
        @self.bot.message_handler(commands=['help'])
        def help(message):
            self.handle_help(message)
        
        @self.bot.message_handler(commands=['info'])
        def info(message):
            self.handle_info(message)
        
        @self.bot.message_handler(commands=['search'])
        def search(message):
            self.handle_search(message)
        
        @self.bot.message_handler(commands=['batch'])
        def batch(message):
            self.handle_batch(message)
        
        @self.bot.message_handler(commands=['profile'])
        def profile(message):
            self.handle_profile(message)
        
        @self.bot.message_handler(commands=['packages'])
        def packages(message):
            self.show_packages(message)
        
        @self.bot.message_handler(commands=['buy'])
        def buy(message):
            self.handle_buy(message)
        
        @self.bot.message_handler(commands=['code'])
        def code(message):
            self.handle_code(message)
        
        @self.bot.message_handler(commands=['balance'])
        def balance(message):
            self.show_balance(message)
        
        @self.bot.message_handler(commands=['history'])
        def history(message):
            self.show_history(message)
        
        @self.bot.message_handler(commands=['referral'])
        def referral(message):
            self.show_referral(message)
        
        @self.bot.message_handler(commands=['support'])
        def support(message):
            self.handle_support(message)
        
        # Admin commands
        @self.bot.message_handler(commands=['admin'])
        def admin(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.handle_admin(message)
        
        @self.bot.message_handler(commands=['stats'])
        def stats(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.show_stats(message)
        
        @self.bot.message_handler(commands=['users'])
        def users(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.show_users(message)
        
        @self.bot.message_handler(commands=['userinfo'])
        def userinfo(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.handle_userinfo(message)
        
        @self.bot.message_handler(commands=['addbalance'])
        def add_balance(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.handle_add_balance(message)
        
        @self.bot.message_handler(commands=['deductbalance'])
        def deduct_balance(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.handle_deduct_balance(message)
        
        @self.bot.message_handler(commands=['generate'])
        def generate(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.handle_generate(message)
        
        @self.bot.message_handler(commands=['codes'])
        def codes(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.list_codes(message)
        
        @self.bot.message_handler(commands=['deletecode'])
        def deletecode(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.delete_code(message)
        
        @self.bot.message_handler(commands=['deactivate'])
        def deactivate(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.deactivate_code(message)
        
        @self.bot.message_handler(commands=['broadcast'])
        def broadcast(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.handle_broadcast(message)
        
        @self.bot.message_handler(commands=['tickets'])
        def tickets(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.show_tickets(message)
        
        @self.bot.message_handler(commands=['reply'])
        def reply(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.handle_reply_ticket(message)
        
        @self.bot.message_handler(commands=['transactions'])
        def transactions(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.show_all_transactions(message)
        
        @self.bot.message_handler(commands=['backup'])
        def backup(message):
            if message.from_user.id in Config.ADMIN_IDS:
                self.create_backup(message)
        
        # Callback query handler
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            self.handle_callback(call)
        
        # Text handler
        @self.bot.message_handler(func=lambda message: True)
        def text(message):
            self.handle_text(message)
    
    # ============ USER HANDLERS ============
    
    def handle_start(self, message):
        user = message.from_user
        text = message.text
        
        # Check if has referral
        referrer_id = None
        if len(text.split()) > 1:
            try:
                referrer_id = int(text.split()[1])
            except:
                pass
        
        self.db.add_user(user.id, user.username, user.first_name, referrer_id)
        
        welcome_text = f"""
🎉 <b>CHÀO MỪNG ĐẾN VỚI TIKTOK UID TOOL!</b>

👤 <b>Thông tin của bạn:</b>
• ID: <code>{user.id}</code>
• Username: @{user.username if user.username else 'Chưa có'}
• Gói hiện tại: <b>{self.get_package_name(user.id)}</b>
• Số dư: <b>{self.db.get_user(user.id).get('balance', 0):,}đ</b>

📱 <b>Các lệnh chính:</b>
• /info [username] - Tra cứu chi tiết 1 user
• /search [từ khóa] - Tìm kiếm user
• /batch - Tra cứu nhiều user
• /profile - Xem thông tin tài khoản
• /balance - Xem số dư và lịch sử giao dịch
• /history - Xem lịch sử tra cứu
• /referral - Giới thiệu bạn bè
• /support - Hỗ trợ trực tuyến
• /packages - Xem các gói dịch vụ
• /buy - Mua gói bằng số dư
• /code [mã] - Kích hoạt mã

⚡ Dùng /help để xem hướng dẫn chi tiết!
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("📱 Tra cứu", callback_data="cmd_info")
        btn2 = types.InlineKeyboardButton("💰 Số dư", callback_data="show_balance")
        btn3 = types.InlineKeyboardButton("💎 Mua gói", callback_data="show_packages")
        btn4 = types.InlineKeyboardButton("🤝 Giới thiệu", callback_data="show_referral")
        markup.add(btn1, btn2, btn3, btn4)
        
        self.bot.reply_to(message, welcome_text, reply_markup=markup)
    
    def handle_help(self, message):
        text = f"""
📚 <b>HƯỚNG DẪN SỬ DỤNG CHI TIẾT</b>

<b>🔹 Lệnh tra cứu:</b>
• <code>/info username</code> - Tra cứu 1 user
• <code>/search từ khóa</code> - Tìm kiếm user
• <code>/batch</code> - Tra cứu nhiều user

<b>🔹 Lệnh tài khoản:</b>
• /profile - Xem thông tin tài khoản
• /balance - Xem số dư và lịch sử giao dịch
• /history - Xem lịch sử tra cứu
• /referral - Xem link giới thiệu và hoa hồng

<b>🔹 Lệnh mua gói:</b>
• /packages - Xem các gói dịch vụ
• /buy - Mua gói bằng số dư trong tài khoản
• /code [mã] - Kích hoạt mã
• /support - Gửi yêu cầu hỗ trợ

<b>🔹 Tính năng mới:</b>
• 🤝 Giới thiệu bạn bè nhận ngay {Config.REFERRAL_BONUS:,}đ
• 💰 Mua gói trực tiếp bằng số dư
• 📊 Xem thống kê chi tiết theo ngày
• 🎫 Hỗ trợ trực tuyến qua ticket

<b>⚡ Giới hạn hiện tại:</b>
• Gói Free: {Config.FREE_DAILY_LIMIT} lượt/ngày
• Batch Free: {Config.FREE_BATCH_LIMIT} user/lần
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("💎 Mua gói", callback_data="show_packages")
        btn2 = types.InlineKeyboardButton("🤝 Giới thiệu", callback_data="show_referral")
        markup.add(btn1, btn2)
        
        self.bot.reply_to(message, text, reply_markup=markup)
    
    def handle_info(self, message):
        user_id = message.from_user.id
        self.db.add_user(user_id, message.from_user.username, message.from_user.first_name)
        
        # Check limit
        can_proceed, msg = self.db.check_limit(user_id)
        if not can_proceed:
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton("💎 Mua gói", callback_data="show_packages")
            markup.add(btn)
            self.bot.reply_to(message, f"⚠️ {msg}", reply_markup=markup)
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            markup = types.ForceReply(selective=False)
            self.bot.reply_to(message, "📝 Nhập username TikTok cần tra cứu:", reply_markup=markup)
            self.user_states[user_id] = {'state': 'waiting_username'}
            return
        
        username = parts[1].strip()
        
        wait_msg = self.bot.reply_to(message, f"🔍 Đang tra cứu @{username}...\n⏳ Vui lòng chờ trong giây lát!")
        
        result = self.tool.get_user_info(username)
        
        self.bot.delete_message(message.chat.id, wait_msg.message_id)
        
        if result:
            self.db.increment_requests(user_id)
            self.db.add_to_history(user_id, result['USERNAME'], result['UID'])
            
            text = self.format_user_info_full(result)
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn1 = types.InlineKeyboardButton("💾 Lưu kết quả", callback_data=f"save_{result['UID']}")
            buttons = [btn1]
            
            user_data = self.db.get_user(user_id)
            package_info = self.db.get_package_info(user_data.get('package', 'free'))
            if package_info['can_download_avatar'] and result['AVATAR']:
                btn2 = types.InlineKeyboardButton("🖼️ Tải Avatar", callback_data=f"avatar_{result['UID']}")
                buttons.append(btn2)
            
            btn3 = types.InlineKeyboardButton("🔄 Tra cứu khác", callback_data="cmd_info")
            buttons.append(btn3)
            
            markup.add(*buttons)
            
            self.bot.reply_to(message, text, reply_markup=markup)
            
            if user_id not in self.user_data:
                self.user_data[user_id] = {}
            self.user_data[user_id][result['UID']] = result
        else:
            self.bot.reply_to(message, f"❌ Không tìm thấy thông tin cho @{username}")
    
    def handle_search(self, message):
        user_id = message.from_user.id
        self.db.add_user(user_id, message.from_user.username, message.from_user.first_name)
        
        can_proceed, msg = self.db.check_limit(user_id)
        if not can_proceed:
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton("💎 Mua gói", callback_data="show_packages")
            markup.add(btn)
            self.bot.reply_to(message, f"⚠️ {msg}", reply_markup=markup)
            return
        
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            markup = types.ForceReply(selective=False)
            self.bot.reply_to(message, "🔤 Nhập từ khóa cần tìm kiếm:", reply_markup=markup)
            self.user_states[user_id] = {'state': 'waiting_search'}
            return
        
        keyword = parts[1].strip()
        
        if len(keyword) < 2:
            self.bot.reply_to(message, "❌ Từ khóa phải có ít nhất 2 ký tự!")
            return
        
        wait_msg = self.bot.reply_to(message, f"🔍 Đang tìm kiếm '{keyword}'...\n⏳ Vui lòng chờ!")
        results = self.tool.search_users(keyword)
        self.bot.delete_message(message.chat.id, wait_msg.message_id)
        
        if results:
            self.db.increment_requests(user_id)
            
            text = f"🔍 <b>KẾT QUẢ TÌM KIẾM '{keyword}':</b>\n\n"
            for i, u in enumerate(results[:10], 1):
                text += f"{i}. <b>@{u['USERNAME']}</b>\n"
                text += f"   📝 {u['NICKNAME'][:50]}\n"
                text += f"   👥 {u['FOLLOWERS']:,} followers\n\n"
            
            if len(results) > 10:
                text += f"<i>...và {len(results)-10} kết quả khác</i>\n"
            
            text += f"\n📊 Tổng số: {len(results)} kết quả"
            
            self.bot.reply_to(message, text)
        else:
            self.bot.reply_to(message, f"❌ Không tìm thấy kết quả cho '{keyword}'")
    
    def handle_batch(self, message):
        user_id = message.from_user.id
        self.db.add_user(user_id, message.from_user.username, message.from_user.first_name)
        
        user_data = self.db.get_user(user_id)
        package_info = self.db.get_package_info(user_data.get('package', 'free'))
        batch_limit = package_info['batch_limit']
        
        text = f"""
📝 <b>NHẬP DANH SÁCH USERNAME</b>

• Gói hiện tại: <b>{self.get_package_name(user_id)}</b>
• Giới hạn: <b>{batch_limit} users/lần</b>
• Delay: {Config.REQUEST_DELAY}s

Mỗi dòng 1 username, ví dụ:
therock
charlidamelio
addisonre

✏️ Nhập danh sách của bạn:
        """
        
        markup = types.ForceReply(selective=False)
        self.bot.reply_to(message, text, reply_markup=markup)
        self.user_states[user_id] = {'state': 'waiting_batch', 'limit': batch_limit}
    
    def handle_profile(self, message):
        user_id = message.from_user.id
        user_data = self.db.get_user(user_id)
        
        if not user_data:
            self.bot.reply_to(message, "❌ Không tìm thấy thông tin!")
            return
        
        package = user_data.get('package', 'free')
        expiry = user_data.get('package_expiry', 'N/A')
        if expiry != 'N/A':
            try:
                expiry_date = datetime.fromisoformat(expiry)
                expiry = expiry_date.strftime('%d/%m/%Y %H:%M')
                days_left = (expiry_date - datetime.now()).days
                if days_left < 0:
                    expiry = f"{expiry} (Đã hết hạn)"
                else:
                    expiry = f"{expiry} (Còn {days_left} ngày)"
            except:
                pass
        
        package_info = self.db.get_package_info(package)
        daily_limit = package_info['daily_limit']
        used = user_data.get('daily_requests', 0)
        remaining = max(0, daily_limit - used)
        
        history = user_data.get('history', [])[-5:]
        
        text = f"""
📊 <b>THÔNG TIN TÀI KHOẢN</b>

👤 <b>Thông tin cơ bản:</b>
• User ID: <code>{user_id}</code>
• Username: @{user_data.get('username', 'N/A')}
• Ngày đăng ký: {self.format_date(user_data.get('registered_at'))}
• Số dư: <b>{user_data.get('balance', 0):,}đ</b>

💎 <b>Gói dịch vụ:</b>
• Gói hiện tại: <b>{self.get_package_name(user_id)}</b>
• Hết hạn: {expiry}
• Đã dùng hôm nay: {used}/{daily_limit}
• Còn lại: {remaining} lượt
• Tổng lượt: {user_data.get('total_requests', 0)}

🤝 <b>Giới thiệu:</b>
• Số người giới thiệu: {len(user_data.get('referrals', []))}
• Hoa hồng: {user_data.get('balance', 0):,}đ

📋 <b>Lịch sử gần đây:</b>
"""
        if history:
            for item in history[-3:]:
                text += f"• @{item.get('username')} - {item.get('uid')}\n"
        else:
            text += "• Chưa có lịch sử\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("💰 Xem số dư", callback_data="show_balance")
        btn2 = types.InlineKeyboardButton("💎 Mua gói", callback_data="show_packages")
        btn3 = types.InlineKeyboardButton("🤝 Giới thiệu", callback_data="show_referral")
        btn4 = types.InlineKeyboardButton("📊 Lịch sử", callback_data="show_history")
        markup.add(btn1, btn2, btn3, btn4)
        
        self.bot.reply_to(message, text, reply_markup=markup)
    
    def show_balance(self, message):
        user_id = message.from_user.id
        user_data = self.db.get_user(user_id)
        
        balance = user_data.get('balance', 0)
        transactions = self.db.get_user_transactions(user_id)
        
        text = f"""
💰 <b>THÔNG TIN SỐ DƯ</b>

• Số dư hiện tại: <b>{balance:,}đ</b>
• Có thể mua: {balance//50000} lượt Basic hoặc {balance//100000} lượt Premium

📋 <b>Lịch sử giao dịch gần đây:</b>
"""
        if transactions:
            for t in transactions[:5]:
                status_emoji = '✅' if t['status'] == 'completed' else '⏳' if t['status'] == 'pending' else '❌'
                amount_display = f"+{t['amount']:,}đ" if t['amount'] > 0 else f"{t['amount']:,}đ"
                text += f"\n{status_emoji} {amount_display} - {t['package']}\n   {self.format_date(t['created_at'])}"
                if t.get('description'):
                    text += f"\n   📝 {t['description']}"
        else:
            text += "\nChưa có giao dịch nào!"
        
        text += "\n\n💳 <b>Nạp tiền:</b>\n"
        text += f"• Momo: <code>{Config.MOMO_PHONE}</code>\n"
        text += f"• Bank: <code>{Config.BANK_ACCOUNT}</code>\n"
        text += f"• Nội dung: <code>NAP{user_id}</code>\n\n"
        text += "⚠️ Sau khi chuyển, vui lòng chờ admin xác nhận!"
        
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("💎 Mua gói bằng số dư", callback_data="show_packages")
        markup.add(btn)
        
        self.bot.reply_to(message, text, reply_markup=markup)
    
    def show_history(self, message):
        user_id = message.from_user.id
        history_data = self.db.get_detailed_history(user_id)
        
        if not history_data:
            self.bot.reply_to(message, "📭 Bạn chưa có lịch sử tra cứu nào!")
            return
        
        text = f"""
📊 <b>LỊCH SỬ TRA CỨU CHI TIẾT</b>

📈 <b>Thống kê 7 ngày qua:</b>
• Tổng số lượt: {history_data['total']}

<b>Theo ngày:</b>
"""
        for date, count in list(history_data['daily'].items())[:7]:
            text += f"• {date}: {count} lượt\n"
        
        if history_data['top_users']:
            text += "\n<b>Top user tra cứu:</b>\n"
            for username, count in list(history_data['top_users'].items())[:3]:
                text += f"• @{username}: {count} lần\n"
        
        text += "\n<b>5 gần nhất:</b>\n"
        for item in history_data['recent'][-5:]:
            text += f"• @{item['username']} - {item['uid']}\n"
        
        self.bot.reply_to(message, text)
    
    def show_referral(self, message):
        user_id = message.from_user.id
        user_data = self.db.get_user(user_id)
        
        referrals = user_data.get('referrals', [])
        balance = user_data.get('balance', 0)
        
        # Tạo link giới thiệu
        bot_username = self.bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        text = f"""
🤝 <b>CHƯƠNG TRÌNH GIỚI THIỆU</b>

🎁 <b>Lợi ích:</b>
• Giới thiệu bạn bè nhận ngay <b>{Config.REFERRAL_BONUS:,}đ</b>
• Bạn của bạn được tặng thêm <b>{Config.REFERRAL_EXTRA_REQUESTS} lượt</b> check

📊 <b>Thống kê của bạn:</b>
• Số người đã giới thiệu: {len(referrals)}
• Tổng hoa hồng: {balance:,}đ

🔗 <b>Link giới thiệu của bạn:</b>
<code>{referral_link}</code>

📝 <b>Hướng dẫn:</b>
1. Gửi link trên cho bạn bè
2. Họ click vào link và start bot
3. Bạn nhận ngay {Config.REFERRAL_BONUS:,}đ vào tài khoản

📋 <b>Danh sách người đã giới thiệu:</b>
"""
        if referrals:
            for i, ref in enumerate(referrals[-5:], 1):
                user_info = self.db.get_user(ref)
                username = user_info.get('username', 'N/A')
                text += f"{i}. @{username}\n"
        else:
            text += "Chưa có ai! Hãy giới thiệu ngay!"
        
        self.bot.reply_to(message, text)
    
    def handle_support(self, message):
        user_id = message.from_user.id
        
        text = """
🎫 <b>HỖ TRỢ TRỰC TUYẾN</b>

Bạn cần hỗ trợ về vấn đề gì?
Hãy gửi tin nhắn mô tả chi tiết vấn đề của bạn.

Admin sẽ phản hồi trong thời gian sớm nhất!
        """
        
        markup = types.ForceReply(selective=False)
        self.bot.reply_to(message, text, reply_markup=markup)
        self.user_states[user_id] = {'state': 'waiting_support'}
    
    def show_packages(self, message):
        user_id = message.from_user.id
        balance = self.db.get_balance(user_id)
        
        text = f"""
💎 <b>CÁC GÓI DỊCH VỤ PREMIUM</b>
💰 <b>Số dư của bạn: {balance:,}đ</b>

<b>🎁 Gói MIỄN PHÍ</b> - 0đ
• {Config.FREE_DAILY_LIMIT} lượt/ngày
• Batch {Config.FREE_BATCH_LIMIT} user
• Tính năng cơ bản

<b>⚡ Gói CƠ BẢN</b> - {Config.PRICES['basic']:,}đ/tháng
• 50 lượt/ngày
• Batch 20 user
• Tải avatar
• Xuất file

<b>🚀 Gói CAO CẤP</b> - {Config.PRICES['premium']:,}đ/tháng
• 200 lượt/ngày
• Batch 50 user
• Avatar HD
• Xuất Excel
• Lưu lịch sử

<b>👑 Gói VIP</b> - {Config.PRICES['vip']:,}đ/tháng
• 500 lượt/ngày
• Batch 100 user
• Ưu tiên xử lý
• Hỗ trợ 24/7

<b>🏢 Gói DOANH NGHIỆP</b> - {Config.PRICES['enterprise']:,}đ/tháng
• 2000 lượt/ngày
• Batch 200 user
• API riêng
• Custom features

<i>👉 Chọn gói bên dưới để mua bằng số dư!</i>
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("⚡ Mua Basic", callback_data=f"buy_balance_basic")
        btn2 = types.InlineKeyboardButton("🚀 Mua Premium", callback_data=f"buy_balance_premium")
        btn3 = types.InlineKeyboardButton("👑 Mua VIP", callback_data=f"buy_balance_vip")
        btn4 = types.InlineKeyboardButton("🏢 Mua Enterprise", callback_data=f"buy_balance_enterprise")
        markup.add(btn1, btn2, btn3, btn4)
        
        # Thêm nút chuyển khoản nếu không đủ tiền
        if balance < min(Config.PRICES.values()):
            markup.add(types.InlineKeyboardButton("💳 Nạp tiền", callback_data="show_balance"))
        
        self.bot.reply_to(message, text, reply_markup=markup)
    
    def handle_buy(self, message):
        """Xử lý lệnh /buy - chuyển đến packages"""
        self.show_packages(message)
    
    def handle_code(self, message):
        parts = message.text.split()
        
        if len(parts) < 2:
            markup = types.ForceReply(selective=False)
            self.bot.reply_to(message, "🔑 Nhập mã kích hoạt của bạn:", reply_markup=markup)
            self.user_states[message.from_user.id] = {'state': 'waiting_code'}
            return
        
        code = parts[1].strip().upper()
        success, msg = self.db.activate_code(code, message.from_user.id)
        
        if success:
            self.bot.reply_to(message, f"✅ {msg}\n\nChúc mừng bạn đã kích hoạt thành công! 🎉")
        else:
            self.bot.reply_to(message, f"❌ {msg}")
    
    # ============ MUA GÓI BẰNG SỐ DƯ ============
    
    def process_purchase_with_balance(self, call, package):
        """Xử lý mua gói bằng số dư"""
        user_id = call.from_user.id
        price = Config.PRICES.get(package, 0)
        
        if price == 0:
            self.bot.answer_callback_query(call.id, "❌ Gói không hợp lệ!")
            return
        
        # Kiểm tra số dư
        balance = self.db.get_balance(user_id)
        
        if balance < price:
            markup = types.InlineKeyboardMarkup()
            btn = types.InlineKeyboardButton("💰 Nạp tiền", callback_data="show_balance")
            markup.add(btn)
            
            self.bot.edit_message_text(
                f"❌ <b>KHÔNG ĐỦ SỐ DƯ!</b>\n\n"
                f"Gói {package}: {price:,}đ\n"
                f"Số dư hiện tại: {balance:,}đ\n"
                f"Còn thiếu: {price - balance:,}đ\n\n"
                f"Vui lòng nạp thêm tiền để mua gói!",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            return
        
        # Xác nhận mua
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_purchase_{package}")
        btn2 = types.InlineKeyboardButton("❌ Hủy", callback_data="cancel_purchase")
        markup.add(btn1, btn2)
        
        self.bot.edit_message_text(
            f"📝 <b>XÁC NHẬN MUA GÓI</b>\n\n"
            f"Gói: <b>{package.upper()}</b>\n"
            f"Giá: {price:,}đ\n"
            f"Số dư sau khi mua: {balance - price:,}đ\n\n"
            f"Xác nhận mua gói này?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    def confirm_purchase(self, call, package):
        """Xác nhận mua gói"""
        user_id = call.from_user.id
        
        success, msg = self.db.purchase_package_with_balance(user_id, package)
        
        if success:
            # Thông báo thành công
            self.bot.edit_message_text(
                f"✅ <b>MUA GÓI THÀNH CÔNG!</b>\n\n"
                f"Gói {package.upper()} đã được kích hoạt!\n"
                f"Số dư còn lại: {self.db.get_balance(user_id):,}đ\n\n"
                f"Cảm ơn bạn đã sử dụng dịch vụ!",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            self.bot.edit_message_text(
                f"❌ <b>LỖI:</b> {msg}",
                call.message.chat.id,
                call.message.message_id
            )
    
    # ============ ADMIN HANDLERS ============
    
    def handle_admin(self, message):
        stats = self.db.get_stats()
        
        text = f"""
👑 <b>ADMIN PANEL</b>

📊 <b>Thống kê hệ thống:</b>
• Tổng users: {stats['total_users']}
• Active hôm nay: {stats['active_today']}
• Tổng requests: {stats['total_requests']}
• Doanh thu: {stats['total_revenue']:,}đ
• Tổng số dư users: {stats['total_balance']:,}đ
• Mã active: {stats['active_codes']}
• Ticket mở: {stats['open_tickets']}

<b>📋 Menu Admin:</b>
• /stats - Xem thống kê chi tiết
• /users - Danh sách users
• /userinfo [ID] - Xem thông tin user
• /addbalance [ID] [số tiền] [ghi chú] - Cộng tiền
• /deductbalance [ID] [số tiền] [ghi chú] - Trừ tiền
• /transactions - Xem giao dịch
• /generate [gói] [ngày] [số lượng] - Tạo mã
• /codes - Xem danh sách mã
• /deletecode [mã] - Xóa mã
• /deactivate [mã] - Vô hiệu hóa mã
• /broadcast [tin nhắn] - Gửi thông báo
• /tickets - Xem ticket hỗ trợ
• /reply [ID] [nội dung] - Trả lời ticket
• /backup - Backup dữ liệu
        """
        self.bot.reply_to(message, text)
    
    def show_stats(self, message):
        stats = self.db.get_stats()
        
        text = f"""
📊 <b>THỐNG KÊ CHI TIẾT</b>

<b>📈 Tổng quan:</b>
• Users: {stats['total_users']}
• Active hôm nay: {stats['active_today']}
• Tổng requests: {stats['total_requests']}

<b>💎 Theo gói:</b>
"""
        for package, count in stats['package_count'].items():
            text += f"• {self.get_package_name_by_key(package)}: {count}\n"
        
        text += f"""
<b>💰 Tài chính:</b>
• Doanh thu: {stats['total_revenue']:,}đ
• Tổng số dư users: {stats['total_balance']:,}đ
• Giao dịch: {stats['total_transactions']}
• Hoa hồng đã trả: {stats['total_bonus_paid']:,}đ

<b>🔑 Mã kích hoạt:</b>
• Đang active: {stats['active_codes']}
• Đã dùng: {stats['used_codes']}

<b>🎫 Hỗ trợ:</b>
• Ticket mở: {stats['open_tickets']}
• Tổng referrals: {stats['total_referrals']}
        """
        
        self.bot.reply_to(message, text)
    
    def show_users(self, message):
        users = self.db.users
        text = "👥 <b>DANH SÁCH USERS (20 mới nhất)</b>\n\n"
        
        sorted_users = sorted(users.values(), 
                            key=lambda x: x.get('last_active', ''), 
                            reverse=True)[:20]
        
        for u in sorted_users:
            package = u.get('package', 'free')
            package_icon = {
                'free': '🆓',
                'basic': '⚡',
                'premium': '🚀',
                'vip': '👑',
                'enterprise': '🏢'
            }.get(package, '🆓')
            
            balance = u.get('balance', 0)
            referrals = len(u.get('referrals', []))
            
            text += f"{package_icon} <code>{u['user_id']}</code> - @{u.get('username', 'N/A')}\n"
            text += f"  Gói: {package} | {u.get('total_requests', 0)} reqs | 💰{balance:,}đ | 👥{referrals}\n"
            text += f"  Lần cuối: {self.format_date(u.get('last_active'))}\n\n"
        
        text += f"📊 Tổng: {len(users)} users"
        self.bot.reply_to(message, text)
    
    def handle_userinfo(self, message):
        """Xem thông tin chi tiết user (admin)"""
        parts = message.text.split()
        
        if len(parts) < 2:
            self.bot.reply_to(message, "📝 Cú pháp: /userinfo [user_id]\nVí dụ: /userinfo 123456789")
            return
        
        try:
            target_id = int(parts[1])
        except:
            self.bot.reply_to(message, "❌ User ID không hợp lệ!")
            return
        
        user_data = self.db.get_user(target_id)
        
        if not user_data:
            self.bot.reply_to(message, f"❌ Không tìm thấy user {target_id}")
            return
        
        package = user_data.get('package', 'free')
        expiry = user_data.get('package_expiry', 'N/A')
        if expiry != 'N/A':
            try:
                expiry_date = datetime.fromisoformat(expiry)
                expiry = expiry_date.strftime('%d/%m/%Y %H:%M')
                days_left = (expiry_date - datetime.now()).days
                expiry += f" (còn {days_left} ngày)"
            except:
                pass
        
        balance = user_data.get('balance', 0)
        total_requests = user_data.get('total_requests', 0)
        daily_requests = user_data.get('daily_requests', 0)
        referrals = len(user_data.get('referrals', []))
        referred_by = user_data.get('referred_by', 'Không')
        if referred_by != 'Không':
            referred_by = f"<code>{referred_by}</code>"
        
        transactions = self.db.get_user_transactions(target_id, 5)
        
        text = f"""
👤 <b>THÔNG TIN USER CHI TIẾT</b>

🆔 <b>User ID:</b> <code>{target_id}</code>
📛 <b>Username:</b> @{user_data.get('username', 'N/A')}
📝 <b>Tên:</b> {user_data.get('first_name', 'N/A')}
📅 <b>Ngày đăng ký:</b> {self.format_date(user_data.get('registered_at'))}
⏰ <b>Hoạt động cuối:</b> {self.format_date(user_data.get('last_active'))}

💎 <b>Gói dịch vụ:</b>
• Gói: {self.get_package_name_by_key(package)}
• Hết hạn: {expiry}
• Đã dùng hôm nay: {daily_requests}
• Tổng lượt: {total_requests}

💰 <b>Số dư:</b> {balance:,}đ

🤝 <b>Giới thiệu:</b>
• Đã giới thiệu: {referrals} người
• Được giới thiệu bởi: {referred_by}

📋 <b>5 giao dịch gần nhất:</b>
"""
        if transactions:
            for t in transactions:
                amount_display = f"+{t['amount']:,}đ" if t['amount'] > 0 else f"{t['amount']:,}đ"
                text += f"\n• {amount_display} - {t['package']} - {t['status']}\n  {self.format_date(t['created_at'])}"
        else:
            text += "\n• Chưa có giao dịch"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("💰 Cộng tiền", callback_data=f"admin_add_{target_id}")
        btn2 = types.InlineKeyboardButton("💳 Lịch sử", callback_data=f"admin_trans_{target_id}")
        markup.add(btn1, btn2)
        
        self.bot.reply_to(message, text, reply_markup=markup)
    
    def handle_add_balance(self, message):
        """Cộng tiền cho user (admin)"""
        parts = message.text.split(maxsplit=3)
        
        if len(parts) < 3:
            self.bot.reply_to(message, "📝 Cú pháp: /addbalance [user_id] [số tiền] [ghi chú]\nVí dụ: /addbalance 123456789 50000 Nạp qua Momo")
            return
        
        try:
            target_id = int(parts[1])
            amount = int(parts[2])
        except:
            self.bot.reply_to(message, "❌ User ID hoặc số tiền không hợp lệ!")
            return
        
        note = parts[3] if len(parts) > 3 else ""
        
        # Xác nhận
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_add_{target_id}_{amount}_{note}")
        btn2 = types.InlineKeyboardButton("❌ Hủy", callback_data="cancel_action")
        markup.add(btn1, btn2)
        
        self.bot.reply_to(
            message,
            f"📝 <b>XÁC NHẬN CỘNG TIỀN</b>\n\n"
            f"User ID: <code>{target_id}</code>\n"
            f"Số tiền: <b>{amount:,}đ</b>\n"
            f"Ghi chú: {note if note else 'Không có'}\n\n"
            f"Xác nhận?",
            reply_markup=markup
        )
    
    def process_add_balance(self, call, target_id, amount, note):
        """Xử lý cộng tiền sau khi xác nhận"""
        admin_id = call.from_user.id
        
        success, msg = self.db.add_balance(target_id, amount, admin_id, note)
        
        if success:
            # Thông báo cho user
            try:
                self.bot.send_message(
                    target_id,
                    f"💰 <b>NẠP TIỀN THÀNH CÔNG!</b>\n\n"
                    f"Số tiền: <b>{amount:,}đ</b>\n"
                    f"Số dư mới: <b>{self.db.get_balance(target_id):,}đ</b>\n"
                    f"Ghi chú: {note if note else 'Nạp tiền qua admin'}\n\n"
                    f"Cảm ơn bạn đã sử dụng dịch vụ!",
                    parse_mode='HTML'
                )
            except:
                pass
            
            self.bot.answer_callback_query(call.id, "✅ Đã cộng tiền thành công!")
            self.bot.edit_message_text(
                f"✅ <b>ĐÃ CỘNG TIỀN THÀNH CÔNG!</b>\n\n"
                f"User ID: <code>{target_id}</code>\n"
                f"Số tiền: <b>{amount:,}đ</b>\n"
                f"Ghi chú: {note if note else 'Không có'}",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            self.bot.answer_callback_query(call.id, f"❌ {msg}")
            self.bot.edit_message_text(
                f"❌ <b>LỖI:</b> {msg}",
                call.message.chat.id,
                call.message.message_id
            )
    
    def handle_deduct_balance(self, message):
        """Trừ tiền của user (admin)"""
        parts = message.text.split(maxsplit=3)
        
        if len(parts) < 3:
            self.bot.reply_to(message, "📝 Cú pháp: /deductbalance [user_id] [số tiền] [ghi chú]\nVí dụ: /deductbalance 123456789 50000 Hoàn tiền")
            return
        
        try:
            target_id = int(parts[1])
            amount = int(parts[2])
        except:
            self.bot.reply_to(message, "❌ User ID hoặc số tiền không hợp lệ!")
            return
        
        note = parts[3] if len(parts) > 3 else ""
        
        # Kiểm tra số dư
        current_balance = self.db.get_balance(target_id)
        if current_balance < amount:
            self.bot.reply_to(
                message,
                f"❌ Số dư user không đủ!\n"
                f"Hiện có: {current_balance:,}đ\n"
                f"Cần trừ: {amount:,}đ"
            )
            return
        
        # Xác nhận
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_deduct_{target_id}_{amount}_{note}")
        btn2 = types.InlineKeyboardButton("❌ Hủy", callback_data="cancel_action")
        markup.add(btn1, btn2)
        
        self.bot.reply_to(
            message,
            f"📝 <b>XÁC NHẬN TRỪ TIỀN</b>\n\n"
            f"User ID: <code>{target_id}</code>\n"
            f"Số tiền: <b>{amount:,}đ</b>\n"
            f"Số dư hiện tại: {current_balance:,}đ\n"
            f"Số dư sau khi trừ: {current_balance - amount:,}đ\n"
            f"Ghi chú: {note if note else 'Không có'}\n\n"
            f"Xác nhận?",
            reply_markup=markup
        )
    
    def process_deduct_balance(self, call, target_id, amount, note):
        """Xử lý trừ tiền sau khi xác nhận"""
        admin_id = call.from_user.id
        
        success, msg = self.db.deduct_balance(target_id, amount, admin_id, note)
        
        if success:
            # Thông báo cho user
            try:
                self.bot.send_message(
                    target_id,
                    f"💰 <b>TRỪ TIỀN TỪ TÀI KHOẢN</b>\n\n"
                    f"Số tiền: <b>{amount:,}đ</b>\n"
                    f"Số dư mới: <b>{self.db.get_balance(target_id):,}đ</b>\n"
                    f"Lý do: {note if note else 'Giao dịch admin'}\n\n"
                    f"Mọi thắc mắc vui lòng liên hệ admin!",
                    parse_mode='HTML'
                )
            except:
                pass
            
            self.bot.answer_callback_query(call.id, "✅ Đã trừ tiền thành công!")
            self.bot.edit_message_text(
                f"✅ <b>ĐÃ TRỪ TIỀN THÀNH CÔNG!</b>\n\n"
                f"User ID: <code>{target_id}</code>\n"
                f"Số tiền: <b>{amount:,}đ</b>\n"
                f"Ghi chú: {note if note else 'Không có'}",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            self.bot.answer_callback_query(call.id, f"❌ {msg}")
            self.bot.edit_message_text(
                f"❌ <b>LỖI:</b> {msg}",
                call.message.chat.id,
                call.message.message_id
            )
    
    def show_all_transactions(self, message):
        """Hiển thị tất cả giao dịch (admin)"""
        transactions = self.db.get_all_transactions(30)
        
        text = "💰 <b>30 GIAO DỊCH GẦN NHẤT</b>\n\n"
        
        for t in transactions:
            status_emoji = {
                'pending': '⏳',
                'completed': '✅',
                'cancelled': '❌',
                'rejected': '❌',
                'failed': '⚠️'
            }.get(t['status'], '❓')
            
            amount_display = f"+{t['amount']:,}đ" if t['amount'] > 0 else f"{t['amount']:,}đ"
            
            text += f"{status_emoji} <code>{t['id']}</code>\n"
            text += f"  User: <code>{t['user_id']}</code>\n"
            text += f"  {amount_display} - {t['package']}\n"
            text += f"  {self.format_date(t['created_at'])}\n"
            if t.get('description'):
                text += f"  📝 {t['description']}\n"
            text += f"  Trạng thái: {t['status']}\n\n"
        
        self.bot.reply_to(message, text)
    
    def handle_generate(self, message):
        """Tạo mã kích hoạt với số lượng tùy chọn"""
        parts = message.text.split()
        
        if len(parts) < 3:
            self.bot.reply_to(message, "📝 Cú pháp: /generate [gói] [ngày] [số lượng]\nVí dụ: /generate premium 30 10\n\nCác gói: basic, premium, vip, enterprise")
            return
        
        package = parts[1].lower()
        if package not in Config.PRICES:
            self.bot.reply_to(message, "❌ Gói không hợp lệ! Chọn: basic, premium, vip, enterprise")
            return
        
        try:
            days = int(parts[2])
            if days <= 0 or days > 365:
                self.bot.reply_to(message, "❌ Số ngày từ 1-365!")
                return
        except:
            self.bot.reply_to(message, "❌ Số ngày không hợp lệ!")
            return
        
        # Xử lý số lượng
        quantity = 1
        if len(parts) >= 4:
            try:
                quantity = int(parts[3])
                if quantity <= 0 or quantity > 100:
                    self.bot.reply_to(message, "❌ Số lượng từ 1-100!")
                    return
            except:
                self.bot.reply_to(message, "❌ Số lượng không hợp lệ!")
                return
        
        codes = self.db.generate_code(package, days, quantity, message.from_user.id)
        
        if quantity == 1:
            text = f"""
✅ <b>ĐÃ TẠO MÃ THÀNH CÔNG!</b>

📦 Gói: <b>{package}</b>
📅 Thời hạn: {days} ngày
🔑 Mã: <code>{codes[0]}</code>

📝 User dùng lệnh: <code>/code {codes[0]}</code>
            """
        else:
            text = f"""
✅ <b>ĐÃ TẠO {quantity} MÃ THÀNH CÔNG!</b>

📦 Gói: <b>{package}</b>
📅 Thời hạn: {days} ngày

🔑 <b>Danh sách mã:</b>
"""
            for i, code in enumerate(codes, 1):
                text += f"{i}. <code>{code}</code>\n"
        
        self.bot.reply_to(message, text)
    
    def list_codes(self, message):
        """Hiển thị danh sách mã kích hoạt"""
        parts = message.text.split()
        
        page = 1
        status = None
        package = None
        
        if len(parts) > 1:
            try:
                page = int(parts[1])
            except:
                if parts[1] in ['active', 'used', 'inactive']:
                    status = parts[1]
                elif parts[1] in Config.PRICES:
                    package = parts[1]
        
        codes, total = self.db.get_codes(status, package, page)
        total_pages = (total + Config.MAX_CODES_PER_PAGE - 1) // Config.MAX_CODES_PER_PAGE
        
        text = f"🔑 <b>DANH SÁCH MÃ KÍCH HOẠT</b> (Trang {page}/{total_pages})\n\n"
        
        if codes:
            for code in codes:
                # Xác định trạng thái
                if code.get('used_by'):
                    status_display = '✅ Đã dùng'
                    status_emoji = '✔️'
                elif code.get('status') == 'inactive':
                    status_display = '❌ Vô hiệu'
                    status_emoji = '❌'
                else:
                    status_display = '🟢 Active'
                    status_emoji = '🟢'
                
                used_by = code.get('used_by', 'Chưa dùng')
                if used_by != 'Chưa dùng':
                    used_by = f"<code>{used_by}</code>"
                
                text += f"{status_emoji} <code>{code['code']}</code>\n"
                text += f"  📦 Gói: {code.get('package', 'N/A')} | {code.get('duration', 30)} ngày\n"
                text += f"  ⏰ Tạo: {self.format_date(code.get('created_at'))}\n"
                text += f"  📌 {status_display} | Người dùng: {used_by}\n\n"
        else:
            text += "Không có mã nào!"
        
        # Tạo nút phân trang
        if total_pages > 1:
            markup = types.InlineKeyboardMarkup()
            if page > 1:
                markup.add(types.InlineKeyboardButton("◀️ Trước", callback_data=f"codes_page_{page-1}"))
            if page < total_pages:
                markup.add(types.InlineKeyboardButton("Sau ▶️", callback_data=f"codes_page_{page+1}"))
            self.bot.reply_to(message, text, reply_markup=markup)
        else:
            self.bot.reply_to(message, text)
    
    def delete_code(self, message):
        """Xóa mã kích hoạt"""
        parts = message.text.split()
        
        if len(parts) < 2:
            self.bot.reply_to(message, "📝 Cú pháp: /deletecode [mã]\nVí dụ: /deletecode ABC123XYZ")
            return
        
        code = parts[1].strip().upper()
        success, msg = self.db.delete_code(code, message.from_user.id)
        
        self.bot.reply_to(message, f"{'✅' if success else '❌'} {msg}")
    
    def deactivate_code(self, message):
        """Vô hiệu hóa mã"""
        parts = message.text.split()
        
        if len(parts) < 2:
            self.bot.reply_to(message, "📝 Cú pháp: /deactivate [mã]\nVí dụ: /deactivate ABC123XYZ")
            return
        
        code = parts[1].strip().upper()
        success, msg = self.db.deactivate_code(code, message.from_user.id)
        
        self.bot.reply_to(message, f"{'✅' if success else '❌'} {msg}")
    
    def handle_broadcast(self, message):
        """Gửi thông báo hàng loạt"""
        parts = message.text.split(maxsplit=1)
        
        if len(parts) < 2:
            self.bot.reply_to(message, "📝 Cú pháp: /broadcast [nội dung]\nVí dụ: /broadcast Chào mừng các bạn!")
            return
        
        content = parts[1].strip()
        
        # Xác nhận
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("✅ Gửi ngay", callback_data="broadcast_confirm")
        btn2 = types.InlineKeyboardButton("❌ Hủy", callback_data="broadcast_cancel")
        markup.add(btn1, btn2)
        
        self.user_data[message.from_user.id] = {'broadcast_content': content}
        
        self.bot.reply_to(
            message,
            f"📢 <b>XÁC NHẬN GỬI THÔNG BÁO</b>\n\n"
            f"Nội dung:\n{content}\n\n"
            f"Sẽ gửi đến {len(self.db.users)} users.\n"
            f"Tiếp tục?",
            reply_markup=markup
        )
    
    def process_broadcast(self, call, content):
        """Xử lý gửi broadcast"""
        status_msg = self.bot.send_message(
            call.message.chat.id,
            "📢 Đang gửi thông báo...\n0%"
        )
        
        success = 0
        failed = 0
        total = len(self.db.users)
        
        for i, user_id in enumerate(self.db.users.keys(), 1):
            try:
                self.bot.send_message(
                    int(user_id),
                    f"📢 <b>THÔNG BÁO TỪ ADMIN</b>\n\n{content}",
                    parse_mode='HTML'
                )
                success += 1
            except:
                failed += 1
            
            # Cập nhật tiến trình mỗi 10%
            if i % max(1, total // 10) == 0:
                percent = int(i / total * 100)
                try:
                    self.bot.edit_message_text(
                        f"📢 Đang gửi thông báo...\n{percent}%",
                        call.message.chat.id,
                        status_msg.message_id
                    )
                except:
                    pass
            
            time.sleep(0.05)  # Tránh spam
        
        # Ghi log
        self.db.add_broadcast(call.from_user.id, content, total, success, failed)
        
        # Kết quả
        result = f"""
📊 <b>KẾT QUẢ GỬI THÔNG BÁO</b>

✅ Thành công: {success}
❌ Thất bại: {failed}
📊 Tổng số: {total}
        """
        
        self.bot.edit_message_text(
            result,
            call.message.chat.id,
            status_msg.message_id
        )
    
    def show_tickets(self, message):
        """Hiển thị danh sách ticket"""
        tickets = self.db.get_open_tickets()
        
        if not tickets:
            self.bot.reply_to(message, "✅ Không có ticket nào đang mở!")
            return
        
        text = "🎫 <b>DANH SÁCH TICKET ĐANG MỞ</b>\n\n"
        
        for ticket in tickets[:10]:
            user = self.db.get_user(ticket['user_id'])
            username = user.get('username', 'N/A')
            
            text += f"🆔 <code>{ticket['id']}</code>\n"
            text += f"👤 User: @{username} | {ticket['user_id']}\n"
            text += f"📝 {ticket['message'][:100]}\n"
            text += f"⏰ {self.format_date(ticket['created_at'])}\n"
            text += f"📌 Trạng thái: {ticket['status']}\n"
            text += f"💬 Phản hồi: {len(ticket.get('responses', []))}\n\n"
        
        text += f"\n📊 Tổng: {len(tickets)} tickets"
        
        self.bot.reply_to(message, text)
    
    def handle_reply_ticket(self, message):
        """Admin trả lời ticket"""
        parts = message.text.split(maxsplit=2)
        
        if len(parts) < 3:
            self.bot.reply_to(message, "📝 Cú pháp: /reply [ID] [nội dung]\nVí dụ: /reply 20240315123045 Cảm ơn bạn!")
            return
        
        ticket_id = parts[1]
        content = parts[2]
        
        success = self.db.reply_ticket(ticket_id, message.from_user.id, content)
        
        if success:
            # Lấy thông tin ticket để gửi cho user
            for ticket in self.db.support_tickets:
                if ticket['id'] == ticket_id:
                    try:
                        self.bot.send_message(
                            int(ticket['user_id']),
                            f"📬 <b>PHẢN HỒI HỖ TRỢ</b>\n\n"
                            f"Admin đã phản hồi ticket #{ticket_id}:\n\n{content}",
                            parse_mode='HTML'
                        )
                    except:
                        pass
                    break
            
            self.bot.reply_to(message, f"✅ Đã gửi phản hồi cho ticket {ticket_id}")
        else:
            self.bot.reply_to(message, f"❌ Không tìm thấy ticket {ticket_id}")
    
    def create_backup(self, message):
        """Tạo backup dữ liệu"""
        status_msg = self.bot.reply_to(message, "⏳ Đang tạo backup...")
        
        # Tạo tên file backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{Config.BACKUP_DIR}/backup_{timestamp}.zip"
        
        import zipfile
        
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Thêm các file JSON
            for file in ['users.json', 'transactions.json', 'codes.json', 'support_tickets.json', 'broadcast_history.json']:
                filepath = f"{Config.DATA_DIR}/{file}"
                if os.path.exists(filepath):
                    zipf.write(filepath, f"data/{file}")
            
            # Thêm file log
            log_file = f"{Config.LOGS_DIR}/bot.log"
            if os.path.exists(log_file):
                zipf.write(log_file, 'logs/bot.log')
        
        self.bot.edit_message_text(
            f"✅ Đã tạo backup thành công!",
            message.chat.id,
            status_msg.message_id
        )
        
        # Gửi file backup
        with open(backup_file, 'rb') as f:
            self.bot.send_document(
                message.chat.id,
                f,
                caption=f"📦 Backup {timestamp}"
            )
    
    # ============ CALLBACK HANDLER ============
    
    def handle_callback(self, call):
        user_id = call.from_user.id
        data = call.data
        
        if data == "cmd_info":
            self.bot.answer_callback_query(call.id, "📱 Nhập username cần tra cứu")
            markup = types.ForceReply(selective=False)
            self.bot.send_message(call.message.chat.id, "📝 Nhập username TikTok:", reply_markup=markup)
            self.user_states[user_id] = {'state': 'waiting_username'}
            
        elif data == "show_balance":
            self.bot.answer_callback_query(call.id, "💰 Xem số dư")
            self.show_balance(call.message)
            
        elif data == "show_packages":
            self.bot.answer_callback_query(call.id, "💎 Các gói dịch vụ")
            self.show_packages(call.message)
            
        elif data == "show_referral":
            self.bot.answer_callback_query(call.id, "🤝 Giới thiệu bạn bè")
            self.show_referral(call.message)
            
        elif data == "show_history":
            self.bot.answer_callback_query(call.id, "📊 Lịch sử tra cứu")
            self.show_history(call.message)
            
        # Mua gói bằng số dư
        elif data.startswith("buy_balance_"):
            package = data.replace("buy_balance_", "")
            self.process_purchase_with_balance(call, package)
            
        elif data.startswith("confirm_purchase_"):
            package = data.replace("confirm_purchase_", "")
            self.confirm_purchase(call, package)
            
        elif data == "cancel_purchase":
            self.bot.answer_callback_query(call.id, "❌ Đã hủy")
            self.bot.edit_message_text(
                "✅ Đã hủy giao dịch!",
                call.message.chat.id,
                call.message.message_id
            )
            
        elif data.startswith("save_"):
            uid = data.replace("save_", "")
            self.save_result(call, uid)
            
        elif data.startswith("avatar_"):
            uid = data.replace("avatar_", "")
            self.download_avatar(call, uid)
            
        elif data.startswith("confirm_"):
            # Xử lý các confirm khác
            if data.startswith("confirm_add_"):
                if user_id in Config.ADMIN_IDS:
                    parts = data.replace("confirm_add_", "").split("_")
                    if len(parts) >= 2:
                        target_id = int(parts[0])
                        amount = int(parts[1])
                        note = "_".join(parts[2:]) if len(parts) > 2 else ""
                        self.process_add_balance(call, target_id, amount, note)
                        
            elif data.startswith("confirm_deduct_"):
                if user_id in Config.ADMIN_IDS:
                    parts = data.replace("confirm_deduct_", "").split("_")
                    if len(parts) >= 2:
                        target_id = int(parts[0])
                        amount = int(parts[1])
                        note = "_".join(parts[2:]) if len(parts) > 2 else ""
                        self.process_deduct_balance(call, target_id, amount, note)
            
        elif data.startswith("admin_add_"):
            if user_id in Config.ADMIN_IDS:
                target_id = int(data.replace("admin_add_", ""))
                # Gửi form nhập số tiền
                markup = types.ForceReply(selective=False)
                self.bot.send_message(
                    call.message.chat.id,
                    f"📝 Nhập số tiền cần cộng cho user <code>{target_id}</code> và ghi chú (cách nhau bằng dấu cách):\nVí dụ: 50000 Nạp qua Momo",
                    reply_markup=markup
                )
                self.user_states[user_id] = {'state': 'waiting_add_amount', 'target_id': target_id}
                
        elif data.startswith("admin_trans_"):
            if user_id in Config.ADMIN_IDS:
                target_id = int(data.replace("admin_trans_", ""))
                # Hiển thị giao dịch của user
                transactions = self.db.get_user_transactions(target_id, 10)
                text = f"💰 <b>GIAO DỊCH CỦA USER {target_id}</b>\n\n"
                if transactions:
                    for t in transactions:
                        amount_display = f"+{t['amount']:,}đ" if t['amount'] > 0 else f"{t['amount']:,}đ"
                        text += f"• {amount_display} - {t['package']}\n"
                        text += f"  {self.format_date(t['created_at'])}\n"
                        text += f"  {t['status']}\n\n"
                else:
                    text += "Chưa có giao dịch nào!"
                self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
                
        elif data.startswith("codes_page_"):
            if user_id in Config.ADMIN_IDS:
                page = int(data.replace("codes_page_", ""))
                message = call.message
                # Tạo message mới để gọi list_codes
                class FakeMessage:
                    def __init__(self, text, chat):
                        self.text = text
                        self.chat = chat
                        self.from_user = type('obj', (object,), {'id': user_id})
                
                fake_msg = FakeMessage(f"/codes {page}", call.message.chat)
                self.list_codes(fake_msg)
                
        elif data == "broadcast_confirm":
            if user_id in Config.ADMIN_IDS and user_id in self.user_data:
                content = self.user_data[user_id].get('broadcast_content')
                if content:
                    self.process_broadcast(call, content)
                    del self.user_data[user_id]
                    
        elif data == "broadcast_cancel":
            if user_id in Config.ADMIN_IDS:
                self.bot.answer_callback_query(call.id, "❌ Đã hủy broadcast")
                self.bot.edit_message_text(
                    "✅ Đã hủy gửi thông báo!",
                    call.message.chat.id,
                    call.message.message_id
                )
        
        elif data == "cancel_action":
            self.bot.answer_callback_query(call.id, "❌ Đã hủy")
            self.bot.edit_message_text(
                "✅ Đã hủy thao tác!",
                call.message.chat.id,
                call.message.message_id
            )
    
    # ============ TEXT HANDLER ============
    
    def handle_text(self, message):
        user_id = message.from_user.id
        text = message.text.strip()
        
        if user_id in self.user_states:
            state = self.user_states[user_id]
            
            if state['state'] == 'waiting_username':
                del self.user_states[user_id]
                message.text = f"/info {text}"
                self.handle_info(message)
                
            elif state['state'] == 'waiting_search':
                del self.user_states[user_id]
                message.text = f"/search {text}"
                self.handle_search(message)
                
            elif state['state'] == 'waiting_batch':
                self.process_batch(message, text, state['limit'])
                del self.user_states[user_id]
                
            elif state['state'] == 'waiting_code':
                del self.user_states[user_id]
                message.text = f"/code {text}"
                self.handle_code(message)
                
            elif state['state'] == 'waiting_support':
                del self.user_states[user_id]
                self.create_support_ticket(message)
                
            elif state['state'] == 'waiting_add_amount':
                if user_id in Config.ADMIN_IDS:
                    target_id = state.get('target_id')
                    parts = text.split(maxsplit=1)
                    try:
                        amount = int(parts[0])
                        note = parts[1] if len(parts) > 1 else ""
                        
                        # Xác nhận
                        markup = types.InlineKeyboardMarkup()
                        btn1 = types.InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_add_{target_id}_{amount}_{note}")
                        btn2 = types.InlineKeyboardButton("❌ Hủy", callback_data="cancel_action")
                        markup.add(btn1, btn2)
                        
                        self.bot.reply_to(
                            message,
                            f"📝 <b>XÁC NHẬN CỘNG TIỀN</b>\n\n"
                            f"User ID: <code>{target_id}</code>\n"
                            f"Số tiền: <b>{amount:,}đ</b>\n"
                            f"Ghi chú: {note if note else 'Không có'}\n\n"
                            f"Xác nhận?",
                            reply_markup=markup
                        )
                    except:
                        self.bot.reply_to(message, "❌ Số tiền không hợp lệ!")
                    
                    del self.user_states[user_id]
    
    # ============ PROCESS FUNCTIONS ============
    
    def process_batch(self, message, text, limit):
        user_id = message.from_user.id
        usernames = [u.strip() for u in text.split('\n') if u.strip()]
        
        if len(usernames) > limit:
            self.bot.reply_to(message, f"⚠️ Gói của bạn chỉ được batch tối đa {limit} user/lần!\nBạn đã nhập {len(usernames)} user.\n💎 Mua gói để tăng giới hạn!")
            return
        
        if len(usernames) < 1:
            self.bot.reply_to(message, "❌ Vui lòng nhập ít nhất 1 username!")
            return
        
        status_msg = self.bot.reply_to(message, f"🔄 Đang xử lý {len(usernames)} users...\n⏳ Thời gian dự kiến: ~{len(usernames) * Config.REQUEST_DELAY}s")
        
        results = []
        failed = []
        
        for i, username in enumerate(usernames, 1):
            try:
                self.bot.edit_message_text(
                    f"🔄 Đang xử lý: {i}/{len(usernames)}\n👤 Username: @{username}",
                    message.chat.id,
                    status_msg.message_id
                )
            except:
                pass
            
            result = self.tool.get_user_info(username)
            if result:
                results.append(result)
                self.db.increment_requests(user_id)
                self.db.add_to_history(user_id, result['USERNAME'], result['UID'])
            else:
                failed.append(username)
            
            if i < len(usernames):
                time.sleep(Config.REQUEST_DELAY)
        
        self.bot.delete_message(message.chat.id, status_msg.message_id)
        
        report = f"📊 <b>KẾT QUẢ XỬ LÝ BATCH</b>\n\n"
        report += f"✅ Thành công: {len(results)}/{len(usernames)}\n"
        report += f"❌ Thất bại: {len(failed)}/{len(usernames)}\n\n"
        
        if results:
            report += "<b>📋 Danh sách thành công:</b>\n"
            for r in results[:10]:
                report += f"• @{r['USERNAME']} - {r['FOLLOWERS']:,} followers\n"
            
            if len(results) > 10:
                report += f"<i>...và {len(results)-10} kết quả khác</i>\n"
        
        if failed:
            report += f"\n<b>⚠️ Thất bại:</b>\n"
            for f in failed[:5]:
                report += f"• @{f}\n"
        
        self.bot.reply_to(message, report)
        
        # Save file if premium
        user_data = self.db.get_user(user_id)
        package_info = self.db.get_package_info(user_data.get('package', 'free'))
        
        if results and package_info['can_export']:
            filename = self.save_batch_results(results, user_id)
            with open(filename, 'rb') as f:
                self.bot.send_document(message.chat.id, f, caption=f"📁 Kết quả batch {len(results)} users")
            os.remove(filename)
    
    def create_support_ticket(self, message):
        """Tạo ticket hỗ trợ mới"""
        user_id = message.from_user.id
        content = message.text
        
        ticket = self.db.create_ticket(user_id, content, message.message_id)
        
        self.bot.reply_to(
            message,
            f"✅ <b>ĐÃ GỬI YÊU CẦU HỖ TRỢ</b>\n\n"
            f"Mã ticket: <code>{ticket['id']}</code>\n"
            f"Nội dung: {content[:100]}\n\n"
            f"Admin sẽ phản hồi trong thời gian sớm nhất!"
        )
        
        # Thông báo cho admin
        for admin_id in Config.ADMIN_IDS:
            try:
                user = self.db.get_user(user_id)
                username = user.get('username', 'N/A')
                
                self.bot.send_message(
                    admin_id,
                    f"🎫 <b>TICKET MỚI</b>\n\n"
                    f"ID: <code>{ticket['id']}</code>\n"
                    f"User: @{username} (<code>{user_id}</code>)\n"
                    f"Nội dung: {content}\n\n"
                    f"Dùng /reply {ticket['id']} [nội dung] để trả lời",
                    parse_mode='HTML'
                )
            except:
                pass
    
    def save_result(self, call, uid):
        user_id = call.from_user.id
        
        if user_id in self.user_data and uid in self.user_data[user_id]:
            result = self.user_data[user_id][uid]
            filename = f"{Config.TEMP_DIR}/result_{user_id}_{int(time.time())}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 50 + "\n")
                f.write("THÔNG TIN TIKTOK USER\n")
                f.write(f"Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"UID: {result['UID']}\n")
                f.write(f"Username: @{result['USERNAME']}\n")
                f.write(f"Nickname: {result['NICKNAME']}\n")
                f.write(f"Followers: {result['FOLLOWERS']:,}\n")
                f.write(f"Following: {result['FOLLOWING']:,}\n")
                f.write(f"Videos: {result['VIDEOS']:,}\n")
                f.write(f"Hearts: {result['HEARTS']:,}\n")
                f.write(f"Verified: {'Có' if result['VERIFIED'] else 'Không'}\n")
                f.write(f"Private: {'Có' if result['PRIVATE'] else 'Không'}\n")
                f.write(f"Ngày tạo: {result['CREATED']}\n")
                f.write(f"Region: {result['REGION']}\n")
                f.write(f"Language: {result['LANGUAGE']}\n")
                f.write(f"Bio: {result['BIO']}\n")
            
            with open(filename, 'rb') as f:
                self.bot.send_document(call.message.chat.id, f, caption=f"📁 Thông tin @{result['USERNAME']}")
            
            os.remove(filename)
            self.bot.answer_callback_query(call.id, "✅ Đã lưu kết quả!")
        else:
            self.bot.answer_callback_query(call.id, "❌ Không tìm thấy kết quả!")
    
    def download_avatar(self, call, uid):
        user_id = call.from_user.id
        
        if user_id in self.user_data and uid in self.user_data[user_id]:
            result = self.user_data[user_id][uid]
            
            self.bot.answer_callback_query(call.id, "🖼️ Đang tải avatar...")
            
            filename = self.tool.download_avatar(result, user_id)
            
            if filename:
                with open(filename, 'rb') as f:
                    self.bot.send_photo(call.message.chat.id, f, caption=f"🖼️ Avatar @{result['USERNAME']}")
                os.remove(filename)
                self.bot.answer_callback_query(call.id, "✅ Tải avatar thành công!")
            else:
                self.bot.answer_callback_query(call.id, "❌ Không thể tải avatar!")
        else:
            self.bot.answer_callback_query(call.id, "❌ Không tìm thấy kết quả!")
    
    def save_batch_results(self, results, user_id):
        filename = f"{Config.TEMP_DIR}/batch_{user_id}_{int(time.time())}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"KẾT QUẢ BATCH - {len(results)} USERS\n")
            f.write(f"Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, r in enumerate(results, 1):
                f.write(f"USER {i}:\n")
                f.write(f"UID: {r['UID']}\n")
                f.write(f"Username: @{r['USERNAME']}\n")
                f.write(f"Nickname: {r['NICKNAME']}\n")
                f.write(f"Followers: {r['FOLLOWERS']:,}\n")
                f.write(f"Following: {r['FOLLOWING']:,}\n")
                f.write(f"Videos: {r['VIDEOS']:,}\n")
                f.write(f"Hearts: {r['HEARTS']:,}\n")
                f.write(f"Verified: {'Có' if r['VERIFIED'] else 'Không'}\n")
                f.write(f"Private: {'Có' if r['PRIVATE'] else 'Không'}\n")
                f.write(f"Ngày tạo: {r['CREATED']}\n")
                f.write(f"Bio: {r['BIO'][:200]}\n")
                f.write("-" * 40 + "\n\n")
        
        return filename
    
    # ============ HELPER FUNCTIONS ============
    
    def format_user_info_full(self, info):
        followers = f"{info['FOLLOWERS']:,}"
        following = f"{info['FOLLOWING']:,}"
        videos = f"{info['VIDEOS']:,}"
        hearts = f"{info['HEARTS']:,}"
        
        verified = "✅ Có" if info['VERIFIED'] else "❌ Không"
        private = "🔒 Riêng tư" if info['PRIVATE'] else "🌐 Công khai"
        
        bio = info['BIO']
        if len(bio) > 200:
            bio = bio[:200] + "..."
        
        text = f"""
📱 <b>THÔNG TIN TIKTOK USER</b>

🆔 <b>UID:</b> <code>{info['UID']}</code>
📛 <b>Username:</b> @{info['USERNAME']}
📝 <b>Nickname:</b> {info['NICKNAME']}

📊 <b>THỐNG KÊ CHI TIẾT:</b>
👥 Followers: <b>{followers}</b>
👤 Following: <b>{following}</b>
🎥 Videos: <b>{videos}</b>
❤️ Hearts: <b>{hearts}</b>

🔰 <b>TRẠNG THÁI TÀI KHOẢN:</b>
✅ Verified: {verified}
🔒 Private: {private}
🌍 Region: {info['REGION']}
🗣️ Language: {info['LANGUAGE']}
📅 Ngày tạo: {info['CREATED']}

📖 <b>TIỂU SỬ:</b>
<i>{bio}</i>

⚡ <i>Dữ liệu từ TikTok API</i>
        """
        return text
    
    def get_package_name(self, user_id):
        user = self.db.get_user(user_id)
        package = user.get('package', 'free')
        names = {
            'free': 'Miễn phí',
            'basic': 'Cơ bản',
            'premium': 'Cao cấp',
            'vip': 'VIP',
            'enterprise': 'Doanh nghiệp'
        }
        return names.get(package, 'Miễn phí')
    
    def get_package_name_by_key(self, key):
        names = {
            'free': 'Miễn phí',
            'basic': 'Cơ bản',
            'premium': 'Cao cấp',
            'vip': 'VIP',
            'enterprise': 'Doanh nghiệp'
        }
        return names.get(key, key)
    
    def format_date(self, date_str):
        if not date_str:
            return 'N/A'
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime('%d/%m/%Y %H:%M')
        except:
            return date_str
    
    # ============ BACKGROUND TASKS ============
    
    def start_background_tasks(self):
        """Khởi động các tác vụ nền"""
        
        # Reset daily limits
        def reset_daily():
            while True:
                now = datetime.now()
                next_reset = datetime(now.year, now.month, now.day) + timedelta(days=1)
                sleep_seconds = (next_reset - now).total_seconds()
                time.sleep(sleep_seconds)
                
                for user_id, user_data in self.db.users.items():
                    user_data['daily_requests'] = 0
                    user_data['last_reset'] = datetime.now().isoformat()
                
                self.db._save_json("users.json", self.db.users)
                logging.info("✅ Đã reset daily limits cho tất cả users")
        
        # Check expiring packages
        def check_expiring():
            while True:
                time.sleep(3600)  # Check mỗi giờ
                
                expiring = self.db.check_expiring_packages()
                for user in expiring:
                    try:
                        self.bot.send_message(
                            int(user['user_id']),
                            f"⚠️ <b>NHẮC NHỞ GIA HẠN</b>\n\n"
                            f"Gói {user['package']} của bạn sẽ hết hạn sau {user['days_left']} ngày.\n"
                            f"Vui lòng gia hạn để tiếp tục sử dụng dịch vụ!\n\n"
                            f"Dùng /balance để nạp tiền và gia hạn tự động.",
                            parse_mode='HTML'
                        )
                    except:
                        pass
                    
                    # Tự động gia hạn nếu có đủ tiền
                    if user['days_left'] <= 1:
                        success, msg = self.db.auto_renew_package(user['user_id'])
                        if success:
                            try:
                                self.bot.send_message(
                                    int(user['user_id']),
                                    f"✅ {msg}",
                                    parse_mode='HTML'
                                )
                            except:
                                pass
        
        # Auto backup hàng ngày
        def auto_backup():
            while True:
                time.sleep(86400)  # 24 giờ
                
                timestamp = datetime.now().strftime('%Y%m%d')
                backup_file = f"{Config.BACKUP_DIR}/auto_backup_{timestamp}.zip"
                
                import zipfile
                with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in ['users.json', 'transactions.json', 'codes.json', 'support_tickets.json']:
                        filepath = f"{Config.DATA_DIR}/{file}"
                        if os.path.exists(filepath):
                            zipf.write(filepath, f"data/{file}")
                
                logging.info(f"✅ Đã tạo auto backup: {backup_file}")
        
        # Start threads
        threading.Thread(target=reset_daily, daemon=True).start()
        threading.Thread(target=check_expiring, daemon=True).start()
        threading.Thread(target=auto_backup, daemon=True).start()
    
    def run(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{Config.LOGS_DIR}/bot.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        logging.info(f"🚀 Starting {Config.APP_NAME} v{Config.VERSION}")
        logging.info(f"👤 Developer: {Config.DEV_NAME}")
        logging.info(f"🤖 Bot token: {Config.BOT_TOKEN[:10]}...")
        logging.info(f"👑 Admin IDs: {Config.ADMIN_IDS}")
        
        try:
            bot_info = self.bot.get_me()
            logging.info(f"✅ Bot @{bot_info.username} is running!")
            self.bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            logging.error(f"❌ Bot error: {e}")
            raise

# ==================== MAIN ====================
def main():
    print("=" * 60)
    print(f"{Config.APP_NAME} v{Config.VERSION}")
    print(f"Developer: {Config.DEV_NAME}")
    print(f"Email: {Config.DEV_EMAIL}")
    print("=" * 60)
    print()
    
    if Config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ CHƯA CẤU HÌNH BOT TOKEN!")
        print("📝 Mở file và thay YOUR_BOT_TOKEN_HERE bằng token của bạn")
        return
    
    if Config.ADMIN_IDS == [123456789]:
        print("⚠️ CẢNH BÁO: Chưa cấu hình Admin IDs!")
        print("📝 Thêm Telegram ID của bạn vào Config.ADMIN_IDS")
    
    bot = TikTokBot(Config.BOT_TOKEN)
    
    try:
        print("✅ Bot đang chạy...")
        print("🔄 Nhấn Ctrl+C để dừng bot")
        print()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Đã dừng bot!")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")

if __name__ == "__main__":
    main()