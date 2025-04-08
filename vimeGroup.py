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
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGroupBox, QMessageBox, QFrame, QFileDialog,
                             QComboBox, QStyleFactory, QDialog, QGridLayout,
                             QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QPalette, QFont


class SignalBridge(QObject):
    """用于线程间通信的信号桥"""
    update_data_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str)
    enable_button_signal = pyqtSignal(bool)
    update_user_detail_signal = pyqtSignal(dict)  # 更新用户详情信号
    update_group_info_signal = pyqtSignal(dict)  # 新增：更新群详情信号


class UserDetailDialog(QDialog):
    """用户详细信息对话框"""
    
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
            
            # 添加确定按钮
            button_box = QHBoxLayout()
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


class GroupMemberGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置基本配置
        self.url = 'http://192.168.10.8:3000/'
        self.api = '/get_group_member_list'
        self.api_user_detail = '/get_group_member_info'  # 用户详情API
        self.api_group_info = '/get_group_info'  # 群信息API
        self.token = 'token666'
        self.member_data = []  # 用于存储成员数据，便于导出
        self.group_info = None  # 用于存储群信息
        
        # 分页控制
        self.page_size = 50  # 每页显示的成员数量
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
        
        # 初始化 UI
        self.init_ui()
        self.apply_theme("蓝色主题")
        
    def init_ui(self):
        self.setWindowTitle("QQ群成员管理")
        self.setGeometry(100, 100, 1000, 700)
        
        # 主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 配置区域
        config_group = QGroupBox("配置")
        config_layout = QVBoxLayout()
        config_group.setLayout(config_layout)
        
        # URL和Token配置行
        url_layout = QHBoxLayout()
        url_label = QLabel("服务器URL:")
        self.url_entry = QLineEdit(self.url)
        token_label = QLabel("Token:")
        self.token_entry = QLineEdit(self.token)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_entry, 1)  # 1是伸展因子
        url_layout.addWidget(token_label)
        url_layout.addWidget(self.token_entry, 1)
        
        # 群号和查询按钮行
        group_layout = QHBoxLayout()
        group_label = QLabel("群号:")
        self.group_id_entry = QLineEdit("")
        self.query_btn = QPushButton("查询群信息")
        self.query_btn.clicked.connect(self.fetch_all_info)
        self.export_btn = QPushButton("导出成员信息")
        self.export_btn.clicked.connect(self.export_members)
        self.export_btn.setEnabled(False)  # 初始时禁用导出按钮
        self.status_label = QLabel("就绪")
        
        # 主题选择
        theme_label = QLabel("主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认主题", "蓝色主题", "深色主题", "浅绿色主题"])
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        
        group_layout.addWidget(group_label)
        group_layout.addWidget(self.group_id_entry)
        group_layout.addWidget(self.query_btn)
        group_layout.addWidget(self.export_btn)
        group_layout.addWidget(theme_label)
        group_layout.addWidget(self.theme_combo)
        group_layout.addWidget(self.status_label)
        group_layout.addStretch(1)  # 添加伸展空间
        
        # 添加配置行到配置布局
        config_layout.addLayout(url_layout)
        config_layout.addLayout(group_layout)
        
        # 可折叠区域容器 - 使用水平布局容纳折叠后的标题栏
        collapsible_container = QWidget()
        self.collapsible_layout = QHBoxLayout(collapsible_container)
        self.collapsible_layout.setSpacing(0)  # 设置标题栏之间没有间距，紧挨着
        self.collapsible_layout.setContentsMargins(0, 0, 0, 0)  # 减少边距
        
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
        
        # 预留区域，用于将来添加更多功能
        self.future_extension_area = QWidget()
        future_layout = QVBoxLayout(self.future_extension_area)
        future_layout.addWidget(QLabel("扩展区域 - 为未来功能预留"))
        future_layout.setContentsMargins(10, 10, 10, 10)
        self.future_extension_area.setVisible(False)  # 默认隐藏
        
        group_info_layout.addWidget(self.future_extension_area)
        group_info_layout.addStretch()  # 添加伸展空间
        
        # 设置群信息的内容布局
        self.group_info_box.setContentLayout(group_info_layout)
        
        # 成员列表区域 - 使用可折叠容器
        self.member_list_box = CollapsibleBox("群成员列表", name="member_list")
        member_list_layout = QVBoxLayout()
        
        # 创建一个可滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 允许内容区域根据需要调整大小
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 根据需要显示垂直滚动条
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 根据需要显示水平滚动条
        
        # 创建内容区域
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)  # 减少边距
        
        # 表格设置
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["QQ号", "昵称", "群名片", "加群时间", "最后发言时间", "角色"])
        
        # 表格大小设置 - 设置最大高度以确保滚动条生效
        self.table.setMaximumHeight(500)  # 设置表格最大高度
        
        # 设置表格填充整个可用空间
        self.table.horizontalHeader().setStretchLastSection(True)  # 最后一列填充剩余空间
        
        # 设置相对宽度比例（总和为100）
        column_ratios = [15, 25, 25, 15, 15, 5]  # QQ号，昵称，群名片，加群时间，最后发言时间，角色
        
        # 设置调整模式
        for i in range(6):
            self.table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        
        # 为空表格添加10行占位行，防止空表格时看起来很丑
        self.table.setRowCount(10)
        for i in range(10):
            for j in range(6):
                self.table.setItem(i, j, QTableWidgetItem(""))
        
        # 设置文字自动换行
        self.table.setWordWrap(True)
        
        # 开启交替行颜色
        self.table.setAlternatingRowColors(True)
        
        # 连接双击事件
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        # 设置表格整体UI样式
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
        """)
        
        # 窗口大小改变时重新调整列宽比例
        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        
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
        
        pagination_layout.addWidget(self.prev_page_btn)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.next_page_btn)
        
        member_list_layout.addLayout(pagination_layout)
        
        # 设置成员列表的内容布局
        self.member_list_box.setContentLayout(member_list_layout)
        
        # 将可折叠组件添加到水平布局中
        self.collapsible_layout.addWidget(self.group_info_box)
        self.collapsible_layout.addWidget(self.member_list_box)
        
        # 连接折叠信号处理函数
        self.group_info_box.collapse_state_changed.connect(self.handle_collapse_change)
        self.member_list_box.collapse_state_changed.connect(self.handle_collapse_change)
        
        # 修改原来的连接方式
        # self.group_info_box.toggle_button.clicked.connect(self.adjust_collapsible_layout)
        # self.member_list_box.toggle_button.clicked.connect(self.adjust_collapsible_layout)
        
        # 将所有组件添加到主布局
        main_layout.addWidget(config_group)
        main_layout.addWidget(collapsible_container, 1)  # 添加伸展因子1，使可折叠区域占用更多空间
        
        # 注意：这里移除了原来的状态栏区域，成员数量信息现在只在标题栏上显示
        
        # 设置窗口大小改变时的事件处理
        self.resizeEvent = self.on_resize
        
        # 初始折叠设置 - 确保至少有一个展开
        self.group_info_box.collapse(False)  # 默认展开群信息
        self.member_list_box.collapse(True)  # 默认折叠成员列表
        self.adjust_collapsible_layout()
        
        self.show()
    
    def adjust_collapsible_layout(self):
        """根据折叠状态调整布局"""
        # 根据折叠状态调整布局方向
        all_collapsed = self.group_info_box.collapsed and self.member_list_box.collapsed
        
        if all_collapsed:
            # 都已折叠，使用垂直布局
            # self.collapsible_layout.setDirection(QHBoxLayout.LeftToRight)
            self.collapsible_layout.setDirection(QHBoxLayout.TopToBottom)

        else:
            # 至少有一个展开，使用垂直布局
            self.collapsible_layout.setDirection(QHBoxLayout.TopToBottom)
            
        # 设置权重
        if not self.group_info_box.collapsed and self.member_list_box.collapsed:
            # 只有群信息展开
            self.collapsible_layout.setStretch(0, 1)
            self.collapsible_layout.setStretch(1, 0)
        elif self.group_info_box.collapsed and not self.member_list_box.collapsed:
            # 只有成员列表展开
            self.collapsible_layout.setStretch(0, 0)
            self.collapsible_layout.setStretch(1, 1)
        else:
            # 都展开或都折叠
            self.collapsible_layout.setStretch(0, 0)
            self.collapsible_layout.setStretch(1, 1)
    
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
                
        # 调整布局
        self.adjust_collapsible_layout()
        
    def fetch_all_info(self):
        """获取所有群相关信息"""
        # 获取用户输入配置
        self.url = self.url_entry.text().strip()
        self.token = self.token_entry.text().strip()
        group_id = self.group_id_entry.text().strip()
        
        if not group_id:
            self.show_error("输入错误", "请输入群号")
            return
        
        # 禁用查询按钮
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
            full_url = self.url + self.api
            body_json = {
                "group_id": group_id,
                "no_cache": False
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
            }
            
            # 发送请求
            response = requests.post(full_url, json=body_json, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应数据
            if 'data' in result and isinstance(result['data'], list):
                self.member_data = result['data']  # 保存数据以便导出
                self.total_pages = (len(self.member_data) + self.page_size - 1) // self.page_size  # 计算总页数
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
        self.total_pages = (len(self.member_data) + self.page_size - 1) // self.page_size
        self.current_page = 0  # 重置为第一页
        self.update_table()
    
    def update_table(self):
        """更新表格显示当前页的数据"""
        start_index = self.current_page * self.page_size
        end_index = min(start_index + self.page_size, len(self.member_data))
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
        current_theme = self.theme_combo.currentText()
        
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
        
        # 启用导出按钮
        self.export_btn.setEnabled(True)
        
        # 更新成员数量信息到群成员列表标题栏
        self.member_list_box.setTitle(f"群成员列表 ({len(self.member_data)}人)")
        
        # 更新分页信息标签
        self.page_info_label.setText(f"第 {self.current_page + 1} 页 / 共 {self.total_pages} 页")
        
        # 更新分页按钮状态
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
    
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
        
        group_id = self.group_id_entry.text().strip()
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"群{group_id}_成员列表_{current_time}"
        
        options = "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "导出成员信息", default_filename, options)
        
        if not file_path:
            return  # 用户取消了导出
        
        try:
            # 根据文件扩展名选择导出格式
            if file_path.endswith('.csv') or "CSV Files" in selected_filter:
                self.export_to_csv(file_path)
            elif file_path.endswith('.json') or "JSON Files" in selected_filter:
                self.export_to_json(file_path)
            else:
                # 如果没有明确的扩展名，默认使用CSV
                if not (file_path.endswith('.csv') or file_path.endswith('.json')):
                    file_path += '.csv'
                self.export_to_csv(file_path)
            
            QMessageBox.information(self, "导出成功", f"成员信息已成功导出到:\n{file_path}")
        except Exception as e:
                
            self.show_error("导出错误", f"导出成员信息时发生错误:\n{str(e)}")
    
    def export_to_json(self, file_path):
        """将成员数据导出为JSON文件"""
        export_data = []
        
        for member in self.member_data:
            # 处理时间戳
            join_time = datetime.fromtimestamp(member.get('join_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('join_time') else "未知"
            last_sent_time = datetime.fromtimestamp(member.get('last_sent_time', 0)).strftime('%Y-%m-%d %H:%M:%S') if member.get('last_sent_time') else "未知"
            
            # 角色转换
            role_map = {'owner': '群主', 'admin': '管理员', 'member': '成员'}
            role = role_map.get(member.get('role', ''), '普通成员')
            
            # 性别转换
            sex_map = {'male': '男', 'female': '女', 'unknown': '未知'}
            sex = sex_map.get(member.get('sex', ''), '未知')
            
            export_data.append({
                "QQ号": member.get('user_id', ''),
                "昵称": member.get('nickname', ''),
                "群名片": member.get('card', ''),
                "加群时间": join_time,
                "最后发言时间": last_sent_time,
                "角色": role,
                "性别": sex,
                "原始数据": member  # 保留原始数据以备完整参考
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def set_button_state(self, enabled):
        self.query_btn.setEnabled(enabled)

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
    
    def on_cell_double_clicked(self, row, column):
        """处理表格单元格双击事件"""
        # 检查是否有有效数据
        if not self.member_data or row >= len(self.member_data):
            return
            
        # 获取用户QQ号
        user_id = self.table.item(row, 0).text()
        if not user_id:
            return
            
        # 获取群号
        group_id = self.group_id_entry.text().strip()
        if not group_id:
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
            full_url = self.url + self.api_user_detail
            body_json = {
                "group_id": group_id,
                "user_id": user_id,
                "no_cache": False
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
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
        current_theme = self.theme_combo.currentText()
        
        # 创建并显示对话框
        dialog = UserDetailDialog(self, user_data, current_theme)
        dialog.exec_()
    
    def fetch_group_info(self, group_id):
        """获取群详细信息"""
        try:
            # 构建请求
            full_url = self.url + self.api_group_info
            body_json = {
                "group_id": group_id
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
            }
            
            # 发送请求
            response = requests.post(full_url, json=body_json, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 处理响应数据
            if 'data' in result and isinstance(result['data'], dict):
                self.group_info = result['data']  # 保存数据
                self.signal_bridge.update_group_info_signal.emit(result['data'])
            else:
                self.signal_bridge.error_signal.emit("错误", "返回的群详细信息格式不正确")
        
        except requests.exceptions.RequestException as e:
            self.signal_bridge.error_signal.emit("请求错误", str(e))
        except json.JSONDecodeError:
            self.signal_bridge.error_signal.emit("解析错误", "响应不是有效的JSON格式")
        except Exception as e:
            self.signal_bridge.error_signal.emit("错误", str(e))
    
    def update_group_info(self, group_info):
        """更新群信息显示"""
        if not group_info:
            return
            
        # 更新群信息标签
        self.group_info_labels["群名称"].setText(group_info.get("group_name", "未知"))
        self.group_info_labels["群号"].setText(str(group_info.get("group_id", "未知")))
        self.group_info_labels["群备注"].setText(group_info.get("group_remark", "无") or "无")
        self.group_info_labels["成员数"].setText(str(group_info.get("member_count", "未知")))
        self.group_info_labels["最大成员数"].setText(str(group_info.get("max_member_count", "未知")))
        
        # 更新标题
        self.member_list_box.setTitle(f"群成员列表 ({group_info.get('member_count', 0)}人)")
        
        # 更新群信息框的标题
        group_name = group_info.get("group_name", "")
        group_id = group_info.get("group_id", "")
        self.group_info_box.setTitle(f"群信息 - {group_name} ({group_id})")
        
        # 展开群信息框，确保信息可见
        self.group_info_box.collapse(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = GroupMemberGUI()
    sys.exit(app.exec_())