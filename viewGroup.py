'''
使用 PyQt5 实现的群成员列表可视化界面
增强版：优化配色方案和添加导出功能
'''

import sys
import os
import csv
from datetime import datetime
import json
import requests
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGroupBox, QMessageBox, QFrame, QFileDialog,
                             QComboBox, QStyleFactory, QDialog, QGridLayout,
                             QScrollArea, QSizePolicy, QRadioButton,
                             QListWidget, QListWidgetItem, QToolBar,
                             QAction, QMenu, QMenuBar, QStatusBar, QSplitter,
                             QTabWidget, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QSettings, QSize
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon, QPixmap, QCursor


class SignalBridge(QObject):
    """用于线程间通信的信号桥"""
    update_data_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str)
    enable_button_signal = pyqtSignal(bool)
    update_user_detail_signal = pyqtSignal(dict)  # 更新用户详情信号
    update_group_info_signal = pyqtSignal(dict)  # 更新群详情信号
    ban_result_signal = pyqtSignal(bool, str)  # 禁言结果信号，参数为是否成功和消息
    update_group_list_signal = pyqtSignal(list)  # 新增：更新群列表信号


class UserDetailDialog(QDialog):
    """用户详细信息对话框"""
    
    # 添加禁言信号
    ban_user_signal = pyqtSignal(dict)
    
    def __init__(self, parent=None, user_detail=None, theme=None):
        super().__init__(parent)
        self.user_detail = user_detail
        self.theme = theme
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("用户详细信息")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)
        
        # 创建滚动区域的内容窗口
        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        scroll.setWidget(content_widget)
        
        # 数据项标签样式
        label_style = "font-weight: bold; color: #404040;"
        value_style = "color: #000000;"
        
        if self.theme == "深色主题":
            label_style = "font-weight: bold; color: #cccccc;"
            value_style = "color: #ffffff;"
        
        # 填充用户信息
        if self.user_detail:
            # 获取所有字段
            fields = [
                ("QQ号", "user_id"),
                ("昵称", "nickname"),
                ("群名片", "card"),
                ("性别", "sex"),
                ("年龄", "age"),
                ("地区", "area"),
                ("群等级", "level"),
                ("QQ等级", "qq_level"),
                ("加群时间", "join_time"),
                ("最后发言时间", "last_sent_time"),
                ("头衔到期时间", "title_expire_time"),
                ("是否不良记录成员", "unfriendly"),
                ("是否允许修改群名片", "card_changeable"),
                ("是否机器人", "is_robot"),
                ("禁言到期时间", "shut_up_timestamp"),
                ("角色", "role"),
                ("头衔", "title")
            ]
            
            # 转换和格式化数据
            row = 0
            for field_name, field_key in fields:
                # 创建标签
                label = QLabel(f"{field_name}:")
                label.setStyleSheet(label_style)
                content_layout.addWidget(label, row, 0)
                
                # 获取并处理值
                value = self.user_detail.get(field_key, "")
                
                # 特殊字段的格式化
                if field_key in ["join_time", "last_sent_time", "shut_up_timestamp", "title_expire_time"]:
                    if value and value > 0:
                        try:
                            value = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            value = f"{value} (无法转换为时间)"
                    else:
                        value = "无"
                elif field_key == "sex":
                    sex_map = {'male': '男', 'female': '女', 'unknown': '未知'}
                    value = sex_map.get(value, '未知')
                elif field_key == "role":
                    role_map = {'owner': '群主', 'admin': '管理员', 'member': '成员'}
                    value = role_map.get(value, '未知')
                elif field_key in ["unfriendly", "card_changeable", "is_robot"]:
                    value = "是" if value else "否"
                elif value == "":
                    value = "无"
                
                # 创建值标签
                value_label = QLabel(str(value))
                value_label.setStyleSheet(value_style)
                value_label.setWordWrap(True)  # 允许长文本换行
                content_layout.addWidget(value_label, row, 1)
                
                row += 1
            
            # 添加按钮布局
            button_box = QHBoxLayout()
            
            # 添加禁言按钮 - 只对普通成员显示
            role = self.user_detail.get("role", "")
            if role == 'member':
                ban_button = QPushButton("设置禁言")
                ban_button.clicked.connect(self.on_ban_clicked)
                button_box.addWidget(ban_button)
            
            # 添加确定按钮
            ok_button = QPushButton("确定")
            ok_button.clicked.connect(self.accept)
            
            button_box.addStretch()
            button_box.addWidget(ok_button)
            main_layout.addLayout(button_box)
        else:
            # 如果没有用户数据
            error_label = QLabel("未能获取用户详细信息")
            error_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(error_label, 0, 0)
        
        # 如果是深色主题，设置对话框背景色
        if self.theme == "深色主题":
            self.setStyleSheet("background-color: #353535; color: #cccccc;")
    
    def on_ban_clicked(self):
        """处理禁言按钮点击事件"""
        if self.user_detail:
            self.ban_user_signal.emit(self.user_detail)
            self.accept()  # 关闭当前对话框

    
class CollapsibleBox(QWidget):
    """可折叠框组件，用于显示可展开/收起的内容"""
    
    # 添加信号，用于通知折叠状态变化
    collapse_state_changed = pyqtSignal(str, bool)
    
    def __init__(self, title="", parent=None, name=""):
        super().__init__(parent)
        # 创建标题按钮，使用更美观的样式
        self.toggle_button = QPushButton(f"▼ {title}")
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                font-weight: bold;
                border-radius: 4px;
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.toggle_button.clicked.connect(self.on_toggle)
        
        # 存储组件名称，用于标识
        self.name = name or title
        
        # 内容区域
        self.content_area = QWidget()
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 允许垂直扩展
        
        # 内容区域的布局
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(2, 10, 2, 2)
        
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)  # 减少间距
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)
        
        # 默认展开
        self.collapsed = False
        self.collapse(self.collapsed)
        
    def on_toggle(self):
        """切换折叠状态"""
        # 如果要折叠，发出信号，让外部决定是否可以折叠
        if not self.collapsed:
            # 要折叠时，先通知外部
            self.collapse_state_changed.emit(self.name, True)
        else:
            # 如果是要展开，则直接展开
            self.collapsed = not self.collapsed
            self.collapse(self.collapsed)
            # 通知外部状态已改变
            self.collapse_state_changed.emit(self.name, False)
        
    def collapse(self, collapsed):
        """设置折叠状态"""
        self.collapsed = collapsed
        if self.collapsed:
            self.content_area.setVisible(False)
            self.toggle_button.setText(f"► {self.toggle_button.text()[2:]}")  # 更改图标为右箭头
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)  # 收起时最小化高度
        else:
            self.content_area.setVisible(True)
            self.toggle_button.setText(f"▼ {self.toggle_button.text()[2:]}")  # 更改图标为下箭头
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 展开时允许扩展
    
    def setContentLayout(self, layout):
        """设置内容区域的布局"""
        # 清除现有布局中的所有项目
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        # 添加新的布局
        self.content_layout.addLayout(layout)
    
    def setTitle(self, title):
        """设置标题"""
        current_state = "► " if self.collapsed else "▼ "
        self.toggle_button.setText(f"{current_state}{title}")
        
    def updateStyle(self, theme):
        """根据主题更新样式"""
        if theme == "深色主题":
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                    background-color: #404040;
                    color: #ffffff;
                    border: 1px solid #505050;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)
        elif theme == "蓝色主题":
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                    background-color: #d0e0f5;
                    border: 1px solid #b0c0e0;
                }
                QPushButton:hover {
                    background-color: #c0d0e8;
                }
            """)
        elif theme == "浅绿色主题":
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                    background-color: #d0f5d0;
                    border: 1px solid #b0e0b0;
                }
                QPushButton:hover {
                    background-color: #c0e8c0;
                }
            """)
        else:  # 默认主题
            self.toggle_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    font-weight: bold;
                    border-radius: 4px;
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)


class BanUserDialog(QDialog):
    """禁言用户对话框"""
    
    def __init__(self, parent=None, user_info=None, theme=None):
        super().__init__(parent)
        self.user_info = user_info
        self.theme = theme
        self.duration = 300  # 默认禁言时长5分钟
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("设置禁言")
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        
        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 用户信息区域
        if self.user_info:
            info_layout = QGridLayout()
            
            # 数据项标签样式
            label_style = "font-weight: bold; color: #404040;"
            value_style = "color: #000000;"
            
            if self.theme == "深色主题":
                label_style = "font-weight: bold; color: #cccccc;"
                value_style = "color: #ffffff;"
            
            # 用户昵称和QQ号
            nickname = self.user_info.get("nickname", "")
            user_id = self.user_info.get("user_id", "")
            card = self.user_info.get("card", "")
            
            display_name = card if card else nickname
            
            info_layout.addWidget(QLabel("用户:"), 0, 0)
            user_label = QLabel(f"{display_name} ({user_id})")
            user_label.setStyleSheet(value_style)
            info_layout.addWidget(user_label, 0, 1)
            
            # 用户角色
            role_map = {'owner': '群主', 'admin': '管理员', 'member': '成员'}
            role = role_map.get(self.user_info.get("role", ""), "成员")
            info_layout.addWidget(QLabel("角色:"), 1, 0)
            role_label = QLabel(role)
            role_label.setStyleSheet(value_style)
            info_layout.addWidget(role_label, 1, 1)
            
            main_layout.addLayout(info_layout)
        
        # 禁言时长选择
        duration_group = QGroupBox("禁言时长")
        duration_layout = QVBoxLayout()
        duration_group.setLayout(duration_layout)
        
        # 预定义的禁言时长选项
        predefined_options = [
            ("5分钟", 5 * 60),
            ("30分钟", 30 * 60),
            ("1小时", 60 * 60),
            ("12小时", 12 * 60 * 60),
            ("1天", 24 * 60 * 60),
            ("7天", 7 * 24 * 60 * 60),
            ("30天", 30 * 24 * 60 * 60)  # 最长30天
        ]
        
        # 创建单选按钮组
        self.duration_radio_group = []
        for i, (label, seconds) in enumerate(predefined_options):
            radio = QRadioButton(label)
            if i == 0:  # 默认选择第一个
                radio.setChecked(True)
            radio.clicked.connect(lambda checked, s=seconds: self.set_duration(s))
            duration_layout.addWidget(radio)
            self.duration_radio_group.append(radio)
        
        # 自定义时长输入
        custom_layout = QHBoxLayout()
        self.custom_radio = QRadioButton("自定义:")
        self.custom_radio.clicked.connect(self.enable_custom_duration)
        custom_layout.addWidget(self.custom_radio)
        
        self.custom_value = QLineEdit("5")
        self.custom_value.setFixedWidth(60)
        self.custom_value.setEnabled(False)  # 初始禁用
        self.custom_value.textChanged.connect(self.custom_duration_changed)
        custom_layout.addWidget(self.custom_value)
        
        self.custom_unit = QComboBox()
        self.custom_unit.addItems(["分钟", "小时", "天"])
        self.custom_unit.setEnabled(False)  # 初始禁用
        self.custom_unit.currentIndexChanged.connect(self.custom_duration_changed)
        custom_layout.addWidget(self.custom_unit)
        
        custom_layout.addStretch()
        duration_layout.addLayout(custom_layout)
        
        main_layout.addWidget(duration_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.confirm_btn = QPushButton("确定")
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.confirm_btn)
        
        main_layout.addLayout(button_layout)
        
        # 如果是深色主题，设置对话框背景色
        if self.theme == "深色主题":
            self.setStyleSheet("background-color: #353535; color: #cccccc;")
    
    def set_duration(self, seconds):
        """设置禁言时长（秒）"""
        self.duration = seconds
        self.custom_value.setEnabled(False)
        self.custom_unit.setEnabled(False)
    
    def enable_custom_duration(self):
        """启用自定义禁言时长"""
        self.custom_value.setEnabled(True)
        self.custom_unit.setEnabled(True)
        self.custom_duration_changed()
    
    def custom_duration_changed(self):
        """自定义禁言时长变更"""
        try:
            value = float(self.custom_value.text())
            unit_index = self.custom_unit.currentIndex()
            
            # 根据单位转换为秒
            if unit_index == 0:  # 分钟
                self.duration = int(value * 60)
            elif unit_index == 1:  # 小时
                self.duration = int(value * 60 * 60)
            else:  # 天
                self.duration = int(value * 24 * 60 * 60)
        except ValueError:
            self.duration = 300  # 默认5分钟
    
    def get_duration(self):
        """返回选择的禁言时长（秒）"""
        return self.duration


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None, settings=None, theme=None):
        super().__init__(parent)
        self.parent = parent
        self.settings = settings or {}
        self.theme = theme
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("设置")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 创建标签页
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # API设置标签页
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        
        # URL设置
        url_group = QGroupBox("服务器设置")
        url_layout = QVBoxLayout()
        url_group.setLayout(url_layout)
        
        # URL输入
        url_input_layout = QHBoxLayout()
        url_label = QLabel("服务器URL:")
        self.url_entry = QLineEdit(self.settings.get('url', 'http://192.168.10.8:3000/'))
        url_input_layout.addWidget(url_label)
        url_input_layout.addWidget(self.url_entry)
        
        # Token输入
        token_input_layout = QHBoxLayout()
        token_label = QLabel("Token:")
        self.token_entry = QLineEdit(self.settings.get('token', 'token666'))
        token_input_layout.addWidget(token_label)
        token_input_layout.addWidget(self.token_entry)
        
        # 将输入布局添加到URL组
        url_layout.addLayout(url_input_layout)
        url_layout.addLayout(token_input_layout)
        
        # 自动刷新设置
        refresh_group = QGroupBox("数据刷新")
        refresh_layout = QVBoxLayout()
        refresh_group.setLayout(refresh_layout)
        
        # 缓存时间设置
        cache_layout = QHBoxLayout()
        cache_label = QLabel("群列表缓存时间(分钟):")
        self.cache_time_entry = QLineEdit(str(self.settings.get('cache_time', 30)))
        self.cache_time_entry.setMaximumWidth(80)
        cache_layout.addWidget(cache_label)
        cache_layout.addWidget(self.cache_time_entry)
        cache_layout.addStretch()
        
        refresh_layout.addLayout(cache_layout)
        
        # 添加到API标签页
        api_layout.addWidget(url_group)
        api_layout.addWidget(refresh_group)
        api_layout.addStretch()
        
        # 外观设置标签页
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        
        # 主题选择
        theme_group = QGroupBox("主题")
        theme_layout = QVBoxLayout()
        theme_group.setLayout(theme_layout)
        
        # 主题下拉框
        theme_select_layout = QHBoxLayout()
        theme_label = QLabel("选择主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认主题", "蓝色主题", "深色主题", "浅绿色主题"])
        current_theme = self.settings.get('theme', '蓝色主题')
        self.theme_combo.setCurrentText(current_theme)
        theme_select_layout.addWidget(theme_label)
        theme_select_layout.addWidget(self.theme_combo)
        theme_layout.addLayout(theme_select_layout)
        
        # 表格设置
        table_group = QGroupBox("表格显示")
        table_layout = QVBoxLayout()
        table_group.setLayout(table_layout)
        
        # 分页大小设置
        page_layout = QHBoxLayout()
        page_label = QLabel("每页显示成员数:")
        self.page_size_entry = QLineEdit(str(self.settings.get('page_size', 50)))
        self.page_size_entry.setMaximumWidth(80)
        page_layout.addWidget(page_label)
        page_layout.addWidget(self.page_size_entry)
        page_layout.addStretch()
        
        table_layout.addLayout(page_layout)
        
        # 添加到外观标签页
        appearance_layout.addWidget(theme_group)
        appearance_layout.addWidget(table_group)
        appearance_layout.addStretch()
        
        # 将标签页添加到标签组件
        tabs.addTab(api_tab, "API设置")
        tabs.addTab(appearance_tab, "外观")
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(button_layout)
        
        # 如果是深色主题，设置对话框背景色
        if self.theme == "深色主题":
            self.setStyleSheet("background-color: #353535; color: #cccccc;")
    
    def get_settings(self):
        """获取设置值"""
        settings = {
            'url': self.url_entry.text().strip(),
            'token': self.token_entry.text().strip(),
            'theme': self.theme_combo.currentText(),
            'cache_time': int(self.cache_time_entry.text() or 30),
            'page_size': int(self.page_size_entry.text() or 50)
        }
        return settings


class GroupListItem(QListWidgetItem):
    """自定义群列表项，用于存储群信息"""
    
    def __init__(self, group_data):
        # 显示名称: 群名称 (成员数/最大成员数)
        display_text = f"{group_data['group_name']} ({group_data['member_count']}/{group_data['max_member_count']})"
        super().__init__(display_text)
        
        # 存储完整的群信息
        self.group_data = group_data
        
        # 设置工具提示，显示更多信息
        tooltip = f"群ID: {group_data['group_id']}\n群名称: {group_data['group_name']}\n成员数: {group_data['member_count']}/{group_data['max_member_count']}"
        if group_data.get('group_remark'):
            tooltip += f"\n群备注: {group_data['group_remark']}"
        
        self.setToolTip(tooltip)


class GroupMemberGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 加载用户设置
        self.load_settings()
        
        # 设置基本配置
        self.api = '/get_group_member_list'
        self.api_user_detail = '/get_group_member_info'  # 用户详情API
        self.api_group_info = '/get_group_info'  # 群信息API
        self.api_ban = '/set_group_ban'  # 禁言API
        self.api_group_list = '/get_group_list'  # 新增：群列表API
        
        self.member_data = []  # 用于存储成员数据，便于导出
        self.group_info = None  # 用于存储群信息
        self.group_list = []  # 新增：用于存储群列表
        self.group_list_last_update = 0  # 新增：群列表最后更新时间
        
        # 分页控制
        self.current_page = 0  # 当前页码(从0开始)
        self.total_pages = 0  # 总页数
        
        # 信号桥接器
        self.signal_bridge = SignalBridge()
        self.signal_bridge.update_data_signal.connect(self.update_ui_with_data)
        self.signal_bridge.error_signal.connect(self.show_error)
        self.signal_bridge.status_signal.connect(self.update_status)
        self.signal_bridge.enable_button_signal.connect(self.set_button_state)
        self.signal_bridge.update_user_detail_signal.connect(self.show_user_detail)
        self.signal_bridge.update_group_info_signal.connect(self.update_group_info)
        self.signal_bridge.ban_result_signal.connect(self.handle_ban_result)
        self.signal_bridge.update_group_list_signal.connect(self.update_group_list)  # 新增：连接群列表信号
        
        # 初始化 UI
        self.init_ui()
        self.apply_theme(self.settings.get('theme', '蓝色主题'))
        
        # 自动加载群列表
        self.fetch_group_list()
        
    def load_settings(self):
        """加载用户设置"""
        # 创建 QSettings 对象
        settings = QSettings("QQBot", "GroupManager")
        
        # 读取设置值，如果不存在则使用默认值
        self.settings = {
            'url': settings.value("url", "http://192.168.10.8:3000/"),
            'token': settings.value("token", "token666"),
            'theme': settings.value("theme", "蓝色主题"),
            'page_size': int(settings.value("page_size", 50)),
            'cache_time': int(settings.value("cache_time", 30))
        }
    
    def save_settings(self):
        """保存用户设置"""
        settings = QSettings("QQBot", "GroupManager")
        
        # 保存当前设置值
        for key, value in self.settings.items():
            settings.setValue(key, value)
    
    def init_ui(self):
        self.setWindowTitle("QQ群成员管理")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.status_label = QLabel("就绪")
        self.statusBar.addWidget(self.status_label)
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建左侧群列表面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 群列表标题
        group_list_header = QHBoxLayout()
        group_list_label = QLabel("我的群聊")
        group_list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.setToolTip("刷新群列表")
        refresh_btn.clicked.connect(self.fetch_group_list)
        refresh_btn.setMaximumWidth(60)
        
        group_list_header.addWidget(group_list_label)
        group_list_header.addStretch()
        group_list_header.addWidget(refresh_btn)
        
        left_layout.addLayout(group_list_header)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索群聊...")
        self.search_input.textChanged.connect(self.filter_group_list)
        search_layout.addWidget(self.search_input)
        
        left_layout.addLayout(search_layout)
        
        # 群聊列表
        self.group_list_widget = QListWidget()
        self.group_list_widget.itemClicked.connect(self.on_group_selected)
        left_layout.addWidget(self.group_list_widget)
        
        # 将左侧面板添加到分割器
        splitter.addWidget(left_panel)
        
        # 创建右侧内容面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建可折叠区域
        self.collapsible_container = QWidget()
        self.collapsible_layout = QVBoxLayout(self.collapsible_container)  # 修改为垂直布局
        self.collapsible_layout.setSpacing(10)
        
        # 群信息区域 - 使用可折叠容器
        self.group_info_box = CollapsibleBox("群信息", name="group_info")
        group_info_layout = QVBoxLayout()
        
        # 创建群信息网格
        group_info_grid = QGridLayout()
        self.group_info_labels = {
            "群名称": QLabel("未获取"),
            "群号": QLabel("未获取"),
            "群备注": QLabel("未获取"),
            "成员数": QLabel("未获取"),
            "最大成员数": QLabel("未获取")
        }
        
        # 定义样式
        label_style = "font-weight: bold;"
        value_style = ""  # 默认样式
        
        # 添加到布局
        row = 0
        for key, value_label in self.group_info_labels.items():
            name_label = QLabel(f"{key}:")
            name_label.setStyleSheet(label_style)
            value_label.setStyleSheet(value_style)
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 允许选择文本
            
            group_info_grid.addWidget(name_label, row, 0)
            group_info_grid.addWidget(value_label, row, 1)
            row += 1
        
        # 将网格添加到群信息布局
        group_info_layout.addLayout(group_info_grid)
        group_info_layout.addStretch()
        
        # 设置群信息的内容布局
        self.group_info_box.setContentLayout(group_info_layout)
        
        # 成员列表区域 - 使用可折叠容器
        self.member_list_box = CollapsibleBox("群成员列表", name="member_list")
        member_list_layout = QVBoxLayout()
        
        # 创建一个可滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建内容区域
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # 表格设置
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["QQ号", "昵称", "群名片", "加群时间", "最后发言时间", "角色"])
        
        # 表格样式设置
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        
        # 设置调整模式
        for i in range(6):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        
        # 为空表格添加10行占位行
        self.table.setRowCount(10)
        for i in range(10):
            for j in range(6):
                self.table.setItem(i, j, QTableWidgetItem(""))
        
        # 设置文字自动换行
        self.table.setWordWrap(True)
        
        # 连接双击事件
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        # 添加表格到容器
        table_layout.addWidget(self.table)
        
        # 将容器设置为滚动区域的内容
        scroll_area.setWidget(table_container)
        
        # 添加滚动区域到成员列表布局
        member_list_layout.addWidget(scroll_area)
        
        # 分页控制区域
        pagination_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(self.next_page)
        self.page_info_label = QLabel("第 1 页 / 共 1 页")
        
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.next_page_btn)
        pagination_layout.addStretch()
        
        member_list_layout.addLayout(pagination_layout)
        
        # 设置成员列表的内容布局
        self.member_list_box.setContentLayout(member_list_layout)
        
        # 将可折叠组件添加到布局中
        self.collapsible_layout.addWidget(self.group_info_box)
        self.collapsible_layout.addWidget(self.member_list_box)
        
        # 连接折叠信号处理函数
        self.group_info_box.collapse_state_changed.connect(self.handle_collapse_change)
        self.member_list_box.collapse_state_changed.connect(self.handle_collapse_change)
        
        # 添加到右侧面板
        right_layout.addWidget(self.collapsible_container)
        
        # 将右侧面板添加到分割器
        splitter.addWidget(right_panel)
        
        # 设置左右面板的初始比例
        splitter.setSizes([300, 900])  # 左侧占1/4，右侧占3/4
        
        # 初始折叠设置 - 根据需求修改
        self.group_info_box.collapse(True)  # 默认折叠群信息
        self.member_list_box.collapse(False)  # 默认展开成员列表
        
        self.show()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        # 导出成员信息
        export_action = QAction("导出成员信息", self)
        export_action.triggered.connect(self.export_members)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menu_bar.addMenu("视图")
        
        # 刷新
        refresh_action = QAction("刷新群成员", self)
        refresh_action.triggered.connect(self.refresh_members)
        view_menu.addAction(refresh_action)
        
        # 设置菜单
        settings_menu = menu_bar.addMenu("设置")
        
        # 首选项
        preferences_action = QAction("首选项", self)
        preferences_action.triggered.connect(self.show_settings)
        settings_menu.addAction(preferences_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 刷新按钮
        refresh_action = QAction("刷新成员", self)
        refresh_action.triggered.connect(self.refresh_members)
        toolbar.addAction(refresh_action)
        
        # 添加分隔符
        toolbar.addSeparator()
        
        # 导出按钮
        export_action = QAction("导出", self)
        export_action.triggered.connect(self.export_members)
        toolbar.addAction(export_action)
        
        # 添加伸缩空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        # 设置按钮
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
    
    def show_settings(self):
        """显示设置对话框"""
        # 获取当前主题
        current_theme = self.settings.get('theme', '蓝色主题')
        
        # 创建并显示设置对话框
        dialog = SettingsDialog(self, self.settings, current_theme)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # 用户点击了保存，获取新设置
            new_settings = dialog.get_settings()
            
            # 检查设置是否有变化
            theme_changed = new_settings['theme'] != self.settings.get('theme')
            url_changed = new_settings['url'] != self.settings.get('url')
            token_changed = new_settings['token'] != self.settings.get('token')
            page_size_changed = new_settings['page_size'] != self.settings.get('page_size')
            
            # 更新设置
            self.settings = new_settings
            
            # 保存设置
            self.save_settings()
            
            # 如果主题改变了，应用新主题
            if theme_changed:
                self.apply_theme(self.settings['theme'])
            
            # 如果URL或Token改变，刷新群列表
            if url_changed or token_changed:
                self.fetch_group_list()
            
            # 如果页面大小改变，更新表格
            if page_size_changed and self.member_data:
                self.update_table()
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 QQ群成员管理",
                          "QQ群成员管理工具 v1.2\n\n"
                          "© 2025 QQbot. 保留所有权利。\n\n"
                          "本软件通过连接API接口获取QQ群信息，提供群成员列表的查看、排序、导出等功能。\n"
                          "使用请开启NapCat的http服务。")
    
    def fetch_group_list(self, force=False):
        """获取群列表
        
        Args:
            force: 是否强制刷新，忽略缓存
        """
        # 检查缓存
        current_time = time.time()
        cache_time_seconds = self.settings.get('cache_time', 30) * 60  # 转换为秒
        
        if not force and self.group_list and (current_time - self.group_list_last_update) < cache_time_seconds:
            # 使用缓存数据
            self.update_group_list(self.group_list)
            return
        
        # 更新状态
        self.signal_bridge.status_signal.emit("正在获取群列表...")
        
        # 后台线程获取群列表
        thread = threading.Thread(target=self.do_fetch_group_list)
        thread.daemon = True
        thread.start()
    
    def do_fetch_group_list(self):
        """在后台线程中获取群列表数据"""
        try:
            # 获取URL和Token
            url = self.settings.get('url')
            token = self.settings.get('token')
            
            # 构建请求
            full_url = url + self.api_group_list
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            # 发送请求
            response = requests.post(full_url, json={}, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应数据
            if 'data' in result and isinstance(result['data'], list):
                # 更新缓存时间
                self.group_list_last_update = time.time()
                # 保存群列表数据
                self.group_list = result['data']
                # 发送信号更新UI
                self.signal_bridge.update_group_list_signal.emit(result['data'])
                # 恢复状态
                self.signal_bridge.status_signal.emit("就绪")
            else:
                self.signal_bridge.error_signal.emit("错误", "返回的群列表格式不正确")
        
        except requests.exceptions.RequestException as e:
            self.signal_bridge.error_signal.emit("请求错误", str(e))
        except json.JSONDecodeError:
            self.signal_bridge.error_signal.emit("解析错误", "响应不是有效的JSON格式")
        except Exception as e:
            self.signal_bridge.error_signal.emit("错误", str(e))
    
    def update_group_list(self, data):
        """更新群列表UI显示"""
        # 保存当前选中的项目
        current_row = self.group_list_widget.currentRow()
        current_group_id = None
        if current_row >= 0:
            item = self.group_list_widget.item(current_row)
            if isinstance(item, GroupListItem):
                current_group_id = item.group_data.get('group_id')
        
        # 清空列表
        self.group_list_widget.clear()
        
        # 填充群列表
        for group in data:
            item = GroupListItem(group)
            self.group_list_widget.addItem(item)
        
        # 如果之前有选中的项目，尝试恢复选中状态
        if current_group_id:
            for i in range(self.group_list_widget.count()):
                item = self.group_list_widget.item(i)
                if isinstance(item, GroupListItem) and item.group_data.get('group_id') == current_group_id:
                    self.group_list_widget.setCurrentRow(i)
                    break
    
    def filter_group_list(self):
        """根据搜索框内容过滤群列表"""
        search_text = self.search_input.text().lower()
        
        # 如果搜索框为空，显示所有群
        if not search_text:
            for i in range(self.group_list_widget.count()):
                self.group_list_widget.item(i).setHidden(False)
            return
        
        # 否则根据搜索内容过滤
        for i in range(self.group_list_widget.count()):
            item = self.group_list_widget.item(i)
            if isinstance(item, GroupListItem):
                group_data = item.group_data
                # 在群名称、群ID或群备注中搜索
                name_match = search_text in group_data.get('group_name', '').lower()
                id_match = search_text in str(group_data.get('group_id', '')).lower()
                remark_match = search_text in group_data.get('group_remark', '').lower()
                
                # 如果匹配则显示，否则隐藏
                item.setHidden(not (name_match or id_match or remark_match))
    
    def on_group_selected(self, item):
        """处理群列表项目点击事件"""
        if isinstance(item, GroupListItem):
            group_data = item.group_data
            group_id = group_data.get('group_id')
            
            if group_id:
                # 更新状态栏
                self.signal_bridge.status_signal.emit(f"正在加载群 {group_data.get('group_name')} 的数据...")
                
                # 获取群信息和成员列表
                self.fetch_all_info(str(group_id))
    
    def fetch_all_info(self, group_id=None):
        """获取所有群相关信息"""
        # 如果没有提供群ID，则获取当前选中的群
        if not group_id:
            current_row = self.group_list_widget.currentRow()
            if current_row >= 0:
                item = self.group_list_widget.item(current_row)
                if isinstance(item, GroupListItem):
                    group_id = str(item.group_data.get('group_id'))
            
        if not group_id:
            self.show_error("错误", "请先选择一个群")
            return
        
        # 禁用按钮
        self.signal_bridge.enable_button_signal.emit(False)
        self.signal_bridge.status_signal.emit("查询中...")
        
        # 清空表格
        self.table.setRowCount(0)
        
        # 创建两个后台线程分别获取群信息和成员信息
        group_info_thread = threading.Thread(target=self.fetch_group_info, args=(group_id,))
        group_info_thread.daemon = True
        group_info_thread.start()
        
        members_thread = threading.Thread(target=self.do_fetch_request, args=(group_id,))
        members_thread.daemon = True
        members_thread.start()
    
    def refresh_members(self):
        """刷新当前群的成员列表"""
        # 获取当前选中的群
        current_row = self.group_list_widget.currentRow()
        if (current_row >= 0):
            item = self.group_list_widget.item(current_row)
            if isinstance(item, GroupListItem):
                group_id = str(item.group_data.get('group_id'))
                self.fetch_all_info(group_id)
        else:
            self.show_error("错误", "请先选择一个群")
    
    def apply_theme(self, theme_name):
        """应用不同的主题样式"""
        app = QApplication.instance()
        
        if theme_name == "默认主题":
            app.setStyle(QStyleFactory.create("Fusion"))
            # 重置调色板为默认
            app.setPalette(app.style().standardPalette())
            self.table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #d0d0d0;
                    color: #000000;
                    font-size: 12px;
                }
                QTableWidget::item {
                    border-bottom: 1px solid #e0e0e0;
                    padding: 5px;
                }
                QHeaderView::section {
                    background-color: #404040;
                    color: white;
                    padding: 5px;
                    border: 1px solid #606060;
                    font-weight: bold;
                }
                alternate-background-color: #f0f0f0;
            """)
            
        elif theme_name == "蓝色主题":
            app.setStyle(QStyleFactory.create("Fusion"))
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(240, 245, 255))
            palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(230, 235, 250))
            palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
            palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
            palette.setColor(QPalette.Text, QColor(0, 0, 0))
            palette.setColor(QPalette.Button, QColor(210, 225, 250))
            palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            app.setPalette(palette)
            self.table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #d0d0d0;
                    color: #000000;
                    font-size: 12px;
                }
                QTableWidget::item {
                    border-bottom: 1px solid #e0e0e0;
                    padding: 5px;
                }
                QHeaderView::section {
                    background-color: #404040;
                    color: white;
                    padding: 5px;
                    border: 1px solid #606060;
                    font-weight: bold;
                }
                alternate-background-color: #e6ebfa;
                selection-background-color: #2a82da;
            """)
            
        elif theme_name == "深色主题":
            app.setStyle(QStyleFactory.create("Fusion"))
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(35, 35, 35))
            palette.setColor(QPalette.AlternateBase, QColor(55, 55, 55))
            palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            app.setPalette(palette)
            self.table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #505050;
                    color: #cccccc;  /* 更改为淡灰色，而不是纯白色，减轻视觉疲劳 */
                    font-size: 12px;
                    background-color: #303030;  /* 表格背景稍微深一点 */
                }
                QTableWidget::item {
                    border-bottom: 1px solid #505050;
                    padding: 5px;
                }
                QHeaderView::section {
                    background-color: #202020;
                    color: #dcdcdc;
                    padding: 5px;
                    border: 1px solid #404040;
                    font-weight: bold;
                }
                alternate-background-color: #383838;  /* 交替行颜色调整 */
                selection-background-color: #1a5591;  /* 选择颜色调暗一点 */
                selection-color: #ffffff;
            """)
            
        elif theme_name == "浅绿色主题":
            app.setStyle(QStyleFactory.create("Fusion"))
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(240, 250, 240))
            palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(230, 250, 230))
            palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
            palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
            palette.setColor(QPalette.Text, QColor(0, 0, 0))
            palette.setColor(QPalette.Button, QColor(210, 250, 210))
            palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
            palette.setColor(QPalette.Highlight, QColor(0, 160, 0))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            app.setPalette(palette)
            self.table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #d0d0d0;
                    color: #000000;
                    font-size: 12px;
                }
                QTableWidget::item {
                    border-bottom: 1px solid #e0e0e0;
                    padding: 5px;
                }
                QHeaderView::section {
                    background-color: #404040;
                    color: white;
                    padding: 5px;
                    border: 1px solid #606060;
                    font-weight: bold;
                }
                alternate-background-color: #e6fae6;
                selection-background-color: #00a000;
            """)
    
    def fetch_group_members(self):
        # 获取用户输入配置
        self.url = self.url_entry.text().strip()
        self.token = self.token_entry.text().strip()
        group_id = self.group_id_entry.text().strip()
        
        # 禁用查询按钮
        self.signal_bridge.enable_button_signal.emit(False)
        self.signal_bridge.status_signal.emit("查询中...")
        
        # 清空表格
        self.table.setRowCount(0)
        
        # 后台线程发送请求
        thread = threading.Thread(target=self.do_fetch_request, args=(group_id,))
        thread.daemon = True
        thread.start()
    
    def do_fetch_request(self, group_id):
        try:
            # 构建请求
            url = self.settings.get('url')
            token = self.settings.get('token')
            full_url = url + self.api
            body_json = {
                "group_id": group_id,
                "no_cache": False
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            # 发送请求
            response = requests.post(full_url, json=body_json, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应数据
            if 'data' in result and isinstance(result['data'], list):
                self.member_data = result['data']  # 保存数据以便导出
                
                # 更新UI
                self.signal_bridge.update_data_signal.emit(result['data'])
            else:
                self.signal_bridge.error_signal.emit("错误", "返回数据格式不正确")
        
        except requests.exceptions.RequestException as e:
            self.signal_bridge.error_signal.emit("请求错误", str(e))
        except json.JSONDecodeError:
            self.signal_bridge.error_signal.emit("解析错误", "响应不是有效的JSON格式")
        except Exception as e:
            self.signal_bridge.error_signal.emit("错误", str(e))
        
        # 恢复按钮状态
        self.signal_bridge.enable_button_signal.emit(True)
        self.signal_bridge.status_signal.emit("就绪")
    
    def update_ui_with_data(self, data):
        # 按角色排序：先群主，然后管理员，最后普通成员
        # 定义角色优先级（数字越小优先级越高）
        role_priority = {
            'owner': 0,    # 群主最高
            'admin': 1,    # 管理员其次
            'member': 2    # 普通成员最低
        }
        
        # 对数据进行排序
        sorted_data = sorted(data, key=lambda x: (
            role_priority.get(x.get('role', 'member'), 2),  # 首先按角色排序
            x.get('join_time', 0)  # 同一角色内按加群时间排序
        ))
        
        # 保存排序后的数据
        self.member_data = sorted_data
        
        # 更新分页信息
        self.total_pages = (len(self.member_data) + self.settings.get('page_size', 50) - 1) // self.settings.get('page_size', 50)
        self.current_page = 0  # 重置为第一页
        self.update_table()
    
    def update_table(self):
        """更新表格显示当前页的数据"""
        # 获取分页大小
        page_size = self.settings.get('page_size', 50)
        
        start_index = self.current_page * page_size
        end_index = min(start_index + page_size, len(self.member_data))
        current_page_data = self.member_data[start_index:end_index]
        
        # 清除占位数据
        self.table.setRowCount(0)
        
        # 设置表格行数
        self.table.setRowCount(max(10, len(current_page_data)))  # 最少显示10行，保持美观
        
        # 定义角色的颜色标记
        role_colors = {
            '群主': QColor(255, 200, 200),  # 浅红色
            '管理员': QColor(200, 200, 255),  # 浅蓝色
            '成员': None  # 默认颜色
        }
        
        # 获取当前主题，以便正确处理深色模式下的颜色
        current_theme = self.settings.get('theme', '蓝色主题')
        
        # 填充表格数据
        for i, member in enumerate(current_page_data):
            # 处理时间戳为可读格式
            join_time = datetime.fromtimestamp(member.get('join_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('join_time') else "未知"
            last_sent_time = datetime.fromtimestamp(member.get('last_sent_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('last_sent_time') else "未知"
            
            # 角色转换为中文
            role_map = {
                'owner': '群主',
                'admin': '管理员',
                'member': '成员'
            }
            role = role_map.get(member.get('role', ''), '成员')
            
            # 创建表格项 - 使用自定义的表格项以支持换行
            nickname_item = QTableWidgetItem(member.get('nickname', ''))
            nickname_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            card_item = QTableWidgetItem(member.get('card', ''))
            card_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            # 创建表格项
            self.table.setItem(i, 0, QTableWidgetItem(str(member.get('user_id', ''))))
            self.table.setItem(i, 1, nickname_item)
            self.table.setItem(i, 2, card_item)
            self.table.setItem(i, 3, QTableWidgetItem(join_time))
            self.table.setItem(i, 4, QTableWidgetItem(last_sent_time))
            self.table.setItem(i, 5, QTableWidgetItem(role))
            
            # 设置不同角色的背景色
            bg_color = role_colors.get(role)
            
            if bg_color:
                # 深色主题下调整颜色，减少对比度
                if current_theme == "深色主题":
                    if role == '群主':
                        bg_color = QColor(120, 60, 60)  # 深红色
                    elif role == '管理员':
                        bg_color = QColor(60, 60, 120)  # 深蓝色
                
                # 设置背景色
                for j in range(6):
                    self.table.item(i, j).setBackground(bg_color)
            
            # 设置项目不可编辑
            for j in range(6):
                item = self.table.item(i, j)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        
        # 如果数据行数少于10，填充剩余的空行
        if len(current_page_data) < 10:
            for i in range(len(current_page_data), 10):
                for j in range(6):
                    self.table.setItem(i, j, QTableWidgetItem(""))
        
        # 调整行高以适应内容
        self.table.resizeRowsToContents()
        
        # 调整表格各列比例
        self.adjust_column_ratios()
        
        # 计算总页数
        page_size = self.settings.get('page_size', 50)
        self.total_pages = (len(self.member_data) + page_size - 1) // page_size
        
        # 更新成员数量信息到群成员列表标题栏
        self.member_list_box.setTitle(f"群成员列表 ({len(self.member_data)}人)")
        
        # 更新分页信息标签
        self.page_info_label.setText(f"第 {self.current_page + 1} 页 / 共 {self.total_pages} 页")
        
        # 更新分页按钮状态
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
        
        # 恢复按钮状态
        self.signal_bridge.enable_button_signal.emit(True)
    
    def prev_page(self):
        """显示上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_table()
    
    def next_page(self):
        """显示下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_table()
    
    def export_members(self):
        """导出成员信息到CSV或JSON文件"""
        if not self.member_data:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        # 获取当前选中的群ID，而不是从已移除的group_id_entry获取
        group_id = None
        current_row = self.group_list_widget.currentRow()
        if current_row >= 0:
            item = self.group_list_widget.item(current_row)
            if isinstance(item, GroupListItem):
                group_id = str(item.group_data.get('group_id', '未知'))
                group_name = item.group_data.get('group_name', '未知群')
        
        if not group_id:
            QMessageBox.warning(self, "警告", "未选择群，请先选择一个群")
            return
        
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"群{group_id}_{group_name}_{current_time}"
        
        # 创建导出选项对话框
        export_dialog = QDialog(self)
        export_dialog.setWindowTitle("导出选项")
        export_dialog.setMinimumWidth(450)
        export_dialog.setMinimumHeight(500)
        
        dialog_layout = QVBoxLayout()
        export_dialog.setLayout(dialog_layout)
        
        # 导出格式选项
        format_group = QGroupBox("导出格式")
        format_layout = QVBoxLayout()
        format_group.setLayout(format_layout)
        
        csv_radio = QRadioButton("CSV 格式 (.csv)")
        csv_radio.setChecked(True)  # 默认选中
        json_radio = QRadioButton("JSON 格式 (.json)")
        
        format_layout.addWidget(csv_radio)
        format_layout.addWidget(json_radio)
        
        # 导出范围选项
        scope_group = QGroupBox("导出成员范围")
        scope_layout = QVBoxLayout()
        scope_group.setLayout(scope_layout)
        
        all_members_radio = QRadioButton("所有成员")  # 改用单选按钮而不是复选框
        all_members_radio.setChecked(True)  # 默认选中
        only_admin_radio = QRadioButton("仅管理员和群主")
        only_active_radio = QRadioButton("仅活跃成员(最近30天有发言)")
        
        scope_layout.addWidget(all_members_radio)
        scope_layout.addWidget(only_admin_radio)
        scope_layout.addWidget(only_active_radio)
        
        # 新增：导出字段选项
        fields_group = QGroupBox("导出字段")
        fields_layout = QVBoxLayout()
        fields_group.setLayout(fields_layout)
        
        # 定义可以导出的字段
        available_fields = [
            {"name": "QQ号", "key": "user_id", "default": True},
            {"name": "昵称", "key": "nickname", "default": True},
            {"name": "群名片", "key": "card", "default": True},
            {"name": "加群时间", "key": "join_time", "default": True},
            {"name": "最后发言时间", "key": "last_sent_time", "default": True},
            {"name": "角色", "key": "role", "default": True},
            {"name": "性别", "key": "sex", "default": True},
            {"name": "年龄", "key": "age", "default": False},
            {"name": "地区", "key": "area", "default": False},
            {"name": "QQ等级", "key": "qq_level", "default": False},
            {"name": "群等级", "key": "level", "default": False}
        ]
        
        # 创建全选/全不选按钮
        select_buttons_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_none_btn = QPushButton("全不选")
        select_basic_btn = QPushButton("选择基本字段")
        
        select_buttons_layout.addWidget(select_all_btn)
        select_buttons_layout.addWidget(select_none_btn)
        select_buttons_layout.addWidget(select_basic_btn)
        fields_layout.addLayout(select_buttons_layout)
        
        # 创建字段复选框
        field_checkboxes = {}
        for field in available_fields:
            checkbox = QCheckBox(field["name"])
            checkbox.setChecked(field["default"])  # 默认选中状态
            field_checkboxes[field["key"]] = checkbox
            fields_layout.addWidget(checkbox)
        
        # 连接全选/全不选/基本字段按钮
        def select_all():
            for checkbox in field_checkboxes.values():
                checkbox.setChecked(True)
        
        def select_none():
            for checkbox in field_checkboxes.values():
                checkbox.setChecked(False)
        
        def select_basic():
            # 基本字段：QQ号、昵称、群名片、角色
            basic_fields = ["user_id", "nickname", "card", "role"]
            for key, checkbox in field_checkboxes.items():
                checkbox.setChecked(key in basic_fields)
        
        select_all_btn.clicked.connect(select_all)
        select_none_btn.clicked.connect(select_none)
        select_basic_btn.clicked.connect(select_basic)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        cancel_button = QPushButton("取消")
        export_button = QPushButton("导出")
        export_button.setDefault(True)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(export_button)
        
        # 将所有组件添加到对话框
        dialog_layout.addWidget(format_group)
        dialog_layout.addWidget(scope_group)
        dialog_layout.addWidget(fields_group)
        dialog_layout.addStretch()
        dialog_layout.addLayout(button_layout)
        
        # 连接按钮事件
        cancel_button.clicked.connect(export_dialog.reject)
        export_button.clicked.connect(export_dialog.accept)
        
        # 应用当前主题
        current_theme = self.settings.get('theme')
        if current_theme == "深色主题":
            export_dialog.setStyleSheet("background-color: #353535; color: #cccccc;")
        
        # 显示对话框
        result = export_dialog.exec_()
        if result != QDialog.Accepted:
            return  # 用户取消了导出
        
        # 处理导出选项
        export_format = "csv" if csv_radio.isChecked() else "json"
        
        # 筛选数据
        filtered_data = self.member_data.copy()
        
        # 根据选择筛选数据
        if only_admin_radio.isChecked():
            filtered_data = [m for m in filtered_data if m.get('role') in ['owner', 'admin']]
        elif only_active_radio.isChecked():
            # 计算30天前的时间戳
            thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
            filtered_data = [m for m in filtered_data if m.get('last_sent_time', 0) > thirty_days_ago]
        # all_members_radio选中时使用所有数据，不需要额外处理
        
        # 如果筛选后没有数据
        if not filtered_data:
            QMessageBox.warning(self, "警告", "根据选择的筛选条件，没有数据可导出")
            return
        
        # 获取选中的字段
        selected_fields = []
        selected_field_names = []
        for field in available_fields:
            if field_checkboxes[field["key"]].isChecked():
                selected_fields.append(field["key"])
                selected_field_names.append(field["name"])
        
        # 如果没有选择任何字段
        if not selected_fields:
            QMessageBox.warning(self, "警告", "请至少选择一个导出字段")
            return
        
        # 设置文件后缀
        extension = ".csv" if export_format == "csv" else ".json"
        default_filename = default_filename + extension
        
        # 获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出成员信息", default_filename, 
            f"{'CSV Files (*.csv)' if export_format == 'csv' else 'JSON Files (*.json)'}")
        
        if not file_path:
            return  # 用户取消了导出
        
        try:
            # 根据格式导出
            if export_format == "csv":
                self.export_to_csv(file_path, filtered_data, selected_fields, selected_field_names)
            else:
                self.export_to_json(file_path, filtered_data, selected_fields, selected_field_names)
            
            QMessageBox.information(self, "导出成功", f"成员信息已成功导出到:\n{file_path}")
        except Exception as e:
            self.show_error("导出错误", f"导出成员信息时发生错误:\n{str(e)}")
    
    def export_to_json(self, file_path, data=None, selected_fields=None, selected_field_names=None):
        """将成员数据导出为JSON文件
        
        Args:
            file_path: 导出文件路径
            data: 要导出的数据，如果为None则使用self.member_data
            selected_fields: 选中的字段列表
            selected_field_names: 选中的字段名称列表
        """
        export_data = []
        
        # 如果没有提供数据，使用全部数据
        data = data if data is not None else self.member_data
        
        for member in data:
            # 处理时间戳
            join_time = datetime.fromtimestamp(member.get('join_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('join_time') else "未知"
            last_sent_time = datetime.fromtimestamp(member.get('last_sent_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('last_sent_time') else "未知"
            
            # 角色转换
            role_map = {'owner': '群主', 'admin': '管理员', 'member': '成员'}
            role = role_map.get(member.get('role', ''), '普通成员')
            
            # 性别转换
            sex_map = {'male': '男', 'female': '女', 'unknown': '未知'}
            sex = sex_map.get(member.get('sex', ''), '未知')
            
            # 构建导出数据
            export_member = {}
            for field, name in zip(selected_fields, selected_field_names):
                if field == "join_time":
                    export_member[name] = join_time
                elif field == "last_sent_time":
                    export_member[name] = last_sent_time
                elif field == "role":
                    export_member[name] = role
                elif field == "sex":
                    export_member[name] = sex
                else:
                    export_member[name] = member.get(field, '')
            
            export_data.append(export_member)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    def export_to_csv(self, file_path, data=None, selected_fields=None, selected_field_names=None):
        """将成员数据导出为CSV文件
        
        Args:
            file_path: 导出文件路径
            data: 要导出的数据，如果为None则使用self.member_data
            selected_fields: 选中的字段列表
            selected_field_names: 选中的字段名称列表
        """
        # 如果没有提供数据，使用全部数据
        data = data if data is not None else self.member_data
        
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            # 写入CSV头部
            writer.writerow(selected_field_names)
            
            # 写入成员数据
            for member in data:
                row = []
                for field in selected_fields:
                    if field == "join_time":
                        value = datetime.fromtimestamp(member.get('join_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('join_time') else "未知"
                    elif field == "last_sent_time":
                        value = datetime.fromtimestamp(member.get('last_sent_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('last_sent_time') else "未知"
                    elif field == "role":
                        role_map = {'owner': '群主', 'admin': '管理员', 'member': '成员'}
                        value = role_map.get(member.get('role', ''), '普通成员')
                    elif field == "sex":
                        sex_map = {'male': '男', 'female': '女', 'unknown': '未知'}
                        value = sex_map.get(member.get('sex', ''), '未知')
                    else:
                        value = member.get(field, '')
                    row.append(value)
                writer.writerow(row)
    
    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def set_button_state(self, enabled):
        """设置按钮状态
        
        在新UI设计中，没有单独的查询按钮，这个方法现在用于启用/禁用工具栏按钮
        """
        # 获取工具栏的所有动作
        toolbar = self.findChild(QToolBar)
        if (toolbar):
            for action in toolbar.actions():
                action.setEnabled(enabled)

    def on_resize(self, event):
        """窗口大小改变时调整表格比例"""
        # 调用父类的 resizeEvent
        super().resizeEvent(event)
        
        # 调整表格各列的宽度比例
        self.adjust_column_ratios()
    
    def adjust_column_ratios(self):
        """根据设定的比例调整表格列宽"""
        # 相对宽度比例（总和为100）
        column_ratios = [15, 25, 25, 15, 15, 5]  # QQ号，昵称，群名片，加群时间，最后发言时间，角色
        
        # 计算表格可用宽度
        total_width = self.table.viewport().width()
        
        # 根据比例设置每列宽度
        for i, ratio in enumerate(column_ratios):
            col_width = int(total_width * ratio / 100)
            self.table.setColumnWidth(i, col_width)
    
    def handle_collapse_change(self, name, want_collapse):
        """处理折叠状态变化，确保不会同时折叠两个区域"""
        if want_collapse:  # 如果要折叠
            # 检查另一个是否已经折叠
            if name == "group_info" and self.member_list_box.collapsed:
                # 如果要折叠群信息，但成员列表已经折叠，则先展开成员列表
                self.member_list_box.collapse(False)
                # 然后才折叠群信息
                self.group_info_box.collapse(True)
            elif name == "member_list" and self.group_info_box.collapsed:
                # 如果要折叠成员列表，但群信息已经折叠，则先展开群信息
                self.group_info_box.collapse(False)
                # 然后才折叠成员列表
                self.member_list_box.collapse(True)
            else:
                # 另一个没有折叠，可以直接折叠当前的
                if name == "group_info":
                    self.group_info_box.collapse(True)
                else:
                    self.member_list_box.collapse(True)
        else:  # 如果要展开，直接展开即可
            if name == "group_info":
                self.group_info_box.collapse(False)
            else:
                self.member_list_box.collapse(False)
    
    def on_cell_double_clicked(self, row, column):
        """处理表格单元格双击事件"""
        # 检查是否有有效数据
        if not self.member_data or row >= len(self.member_data):
            return
            
        # 获取用户QQ号
        user_id = self.table.item(row, 0).text()
        if not user_id:
            return
            
        # 获取当前选中的群ID
        group_id = None
        current_row = self.group_list_widget.currentRow()
        if current_row >= 0:
            item = self.group_list_widget.item(current_row)
            if isinstance(item, GroupListItem):
                group_id = str(item.group_data.get('group_id'))
        
        if not group_id:
            self.show_error("错误", "无法获取当前群号")
            return
            
        # 更新状态
        self.status_label.setText(f"正在获取用户 {user_id} 的详细信息...")
        
        # 在后台线程中请求详细信息
        thread = threading.Thread(target=self.fetch_user_detail, args=(group_id, user_id))
        thread.daemon = True
        thread.start()
    
    def fetch_user_detail(self, group_id, user_id):
        """获取群成员的详细信息"""
        try:
            # 构建请求
            url = self.settings.get('url')
            token = self.settings.get('token')
            full_url = url + self.api_user_detail
            body_json = {
                "group_id": group_id,
                "user_id": user_id,
                "no_cache": False
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            # 发送请求
            response = requests.post(full_url, json=body_json, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应数据
            if 'data' in result and isinstance(result['data'], dict):
                self.signal_bridge.update_user_detail_signal.emit(result['data'])
            else:
                self.signal_bridge.error_signal.emit("错误", "返回的用户详细信息格式不正确")
        
        except requests.exceptions.RequestException as e:
            self.signal_bridge.error_signal.emit("请求错误", str(e))
        except json.JSONDecodeError:
            self.signal_bridge.error_signal.emit("解析错误", "响应不是有效的JSON格式")
        except Exception as e:
            self.signal_bridge.error_signal.emit("错误", str(e))
            
        # 恢复状态
        self.signal_bridge.status_signal.emit("就绪")
    
    def show_user_detail(self, user_data):
        """显示用户详细信息对话框"""
        # 获取当前主题
        current_theme = self.settings.get('theme', '蓝色主题')
        
        # 创建并显示对话框
        dialog = UserDetailDialog(self, user_data, current_theme)
        # 连接禁言信号
        dialog.ban_user_signal.connect(self.show_ban_dialog)
        dialog.exec_()
    
    def show_ban_dialog(self, user_info):
        """显示禁言设置对话框"""
        # 获取当前主题
        current_theme = self.settings.get('theme')
        
        # 获取当前选中的群ID
        group_id = None
        current_row = self.group_list_widget.currentRow()
        if current_row >= 0:
            item = self.group_list_widget.item(current_row)
            if isinstance(item, GroupListItem):
                group_id = str(item.group_data.get('group_id'))
        
        if not group_id:
            self.show_error("错误", "无法获取当前群号")
            return
        
        # 创建并显示禁言对话框
        dialog = BanUserDialog(self, user_info, current_theme)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            # 用户点击了确定，获取禁言时长
            duration = dialog.get_duration()
            # 获取用户ID
            user_id = user_info.get("user_id", "")
            
            # 执行禁言
            if group_id and user_id:
                self.ban_user(group_id, user_id, duration)
            else:
                self.show_error("错误", "无法获取群号或用户ID")
    
    def ban_user(self, group_id, user_id, duration):
        """禁言用户"""
        # 更新状态
        self.signal_bridge.status_signal.emit(f"正在设置禁言...")
        
        # 禁用按钮，防止重复操作
        self.signal_bridge.enable_button_signal.emit(False)
        
        # 后台线程执行禁言
        thread = threading.Thread(target=self.do_ban_request, args=(group_id, user_id, duration))
        thread.daemon = True
        thread.start()
    
    def do_ban_request(self, group_id, user_id, duration):
        """执行禁言请求"""
        try:
            # 构建请求
            url = self.settings.get('url')
            token = self.settings.get('token')
            full_url = url + self.api_ban
            body_json = {
                "group_id": group_id,
                "user_id": user_id,
                "duration": duration
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            # 发送请求
            response = requests.post(full_url, json=body_json, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应结果
            if 'status' in result:
                if result['status'] == 'ok':
                    # 禁言成功
                    self.signal_bridge.ban_result_signal.emit(True, self.format_duration(duration))
                else:
                    # 禁言失败
                    message = result.get('message', '未知错误')
                    self.signal_bridge.ban_result_signal.emit(False, message)
            else:
                self.signal_bridge.error_signal.emit("错误", "返回的禁言结果格式不正确")
        
        except requests.exceptions.RequestException as e:
            self.signal_bridge.error_signal.emit("请求错误", str(e))
        except json.JSONDecodeError:
            self.signal_bridge.error_signal.emit("解析错误", "响应不是有效的JSON格式")
        except Exception as e:
            self.signal_bridge.error_signal.emit("错误", str(e))
        
        # 恢复按钮状态
        self.signal_bridge.enable_button_signal.emit(True)
        self.signal_bridge.status_signal.emit("就绪")
    
    def handle_ban_result(self, success, message):
        """处理禁言结果"""
        if success:
            QMessageBox.information(self, "禁言成功", f"已成功设置禁言，时长: {message}")
        else:
            if message == "ERR_NOT_GROUP_ADMIN":
                QMessageBox.warning(self, "禁言失败", "您不是群管理员，无法设置禁言")
            else:
                QMessageBox.warning(self, "禁言失败", f"设置禁言失败: {message}")
    
    def format_duration(self, seconds):
        """格式化时长为易读的格式"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}小时{minutes}分钟"
            else:
                return f"{hours}小时"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            if hours > 0:
                return f"{days}天{hours}小时"
            else:
                return f"{days}天"
                
    def fetch_group_info(self, group_id):
        """获取群基本信息"""
        try:
            # 构建请求
            url = self.settings.get('url')
            token = self.settings.get('token')
            full_url = url + self.api_group_info
            body_json = {
                "group_id": group_id,
                "no_cache": False
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            # 发送请求
            response = requests.post(full_url, json=body_json, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应数据
            if 'data' in result and isinstance(result['data'], dict):
                self.group_info = result['data']  # 保存群信息
                self.signal_bridge.update_group_info_signal.emit(result['data'])
            else:
                self.signal_bridge.error_signal.emit("错误", "返回的群信息格式不正确")
        
        except requests.exceptions.RequestException as e:
            self.signal_bridge.error_signal.emit("请求错误", str(e))
        except json.JSONDecodeError:
            self.signal_bridge.error_signal.emit("解析错误", "响应不是有效的JSON格式")
        except Exception as e:
            self.signal_bridge.error_signal.emit("错误", str(e))
    
    def update_group_info(self, group_data):
        """更新群信息显示"""
        if group_data:
            # 更新群信息标签
            self.group_info_labels["群名称"].setText(group_data.get("group_name", "未知"))
            self.group_info_labels["群号"].setText(str(group_data.get("group_id", "未知")))
            self.group_info_labels["群备注"].setText(group_data.get("group_memo", "无"))
            self.group_info_labels["成员数"].setText(str(group_data.get("member_count", 0)))
            self.group_info_labels["最大成员数"].setText(str(group_data.get("max_member_count", 0)))
            
            # 如果有头像信息，可以在这里添加显示逻辑
            
            # 更新窗口标题，加入群名称
            self.setWindowTitle(f"QQ群成员管理 - {group_data.get('group_name', '')}")
            
            # 更新折叠框标题
            self.group_info_box.setTitle(f"群信息 - {group_data.get('group_name', '')}")
    
    def closeEvent(self, event):
        """程序关闭时保存设置"""
        self.save_settings()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = GroupMemberGUI()
    sys.exit(app.exec_())