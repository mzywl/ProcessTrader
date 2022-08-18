# -*- coding: utf-8 -*-
import imp
import os
import re
import sys
import time
import psutil
import pandas as pd
import win32com.client as win32
from pathlib import Path
from datetime import datetime
from pandas import DataFrame
from PySide6 import QtCore, QtGui
from PySide6.QtCharts import QChart
from PySide6.QtCore import QEventLoop, QStringListModel, QTimer, QDir, QPropertyAnimation
from PySide6.QtGui import QCursor, QStandardItem, QStandardItemModel, Qt, QPixmap, QImage, QMouseEvent
from PySide6.QtUiTools import loadUiType
from PySide6.QtWidgets import QApplication, QFrame, QMainWindow, QTableWidgetItem, QWidget, QFileDialog, QFileSystemModel, QTreeView
import webbrowser
from dtview import DonutWidget
from read_write_file import ReadWriteCsv
import strategys


class EmittingStr(QtCore.QObject):      # 发射信号类
    textWritten = QtCore.Signal(str)    # 发射信号

    def write(self, text):
        self.textWritten.emit(str(text))    # 发射信号
        loop = QEventLoop() # 创建事件循环
        QTimer.singleShot(1, loop.quit) # 延时1ms后退出事件循环
        loop.exec() # 开始事件循环
        QApplication.processEvents()    # 处理事件

    def flush(self):  # 不加这个函数会报错，不要问为什么，我也不知道
        pass


class Main_Process_Function:    # 主进程函数类，该类由主进程窗口类继承并调用

    def outputWritten(self, text):  # 发射信号
        cursor = self.textBrowser_terminal.textCursor() # 获取光标
        cursor.movePosition(QtGui.QTextCursor.End)  # 光标移动到最后
        cursor.insertText(text) # 插入文本
        self.textBrowser_terminal.setTextCursor(cursor) # 设置光标
        self.textBrowser_terminal.ensureCursorVisible() # 光标可见

    def add_paramer_to_container(self):   # 将参数添加到面板各容器中

        self.label_runing_process_quantity.setText(str(len(self.get_alive_process_pid_list())))  # 获取当前活着的子进程数(只有子进程，没有父进程和协程)
        self.label_current_time.setText(time.strftime('%Y-%m-%d    %H:%M:%S', time.localtime()))
        self.label_frame_runing_time.setText(self.get_frame_runing_time())
        self.label_tq_account_quantity.setText(str(self.get_tq_account_quantity()))
        self.label_cpu_occupancy.setText(str(psutil.cpu_percent()) + ' %')
        self.label_total_profit.setText(str(self.get_total_profit()))
        self.process_dict_update()
        self.load_process_config()

        account_model = QStringListModel()
        self.clients_list = self.get_clients_list()
        account_model.setStringList(self.clients_list)
        self.clients_listview.setModel(account_model)
        self.clients_listview2.setModel(account_model)

        tq_account_model = QStringListModel()
        self.tq_account_list = self.get_tq_account_list()
        tq_account_model.setStringList(self.tq_account_list)
        self.tq_account_listview.setModel(tq_account_model)
        self.tq_account_listview2.setModel(tq_account_model)

        qoute_model = QStringListModel()
        self.qoute_list = self.get_qoute_list()
        qoute_model.setStringList(self.qoute_list)
        self.qoute_listview.setModel(qoute_model)

        strategy_model = QStringListModel()
        self.strategy_list = self.get_strategy_list(path='./strategys')
        strategy_model.setStringList(self.strategy_list)
        self.strategy_listview.setModel(strategy_model)

        process_model = QStringListModel()
        self.process_list = self.get_process_list()
        process_model.setStringList(self.process_list)
        self.process_listview.setModel(process_model)

    def show_clients_info(self, qModelIndex):   # 显示客户信息
        row = qModelIndex.row()    
        data = self.ioModal.read_csv_file(path='./data/clients.csv')
        self.textBrowser_clients_details.clear()
        self.textBrowser_clients_details.append('\n' + '客户姓名：   ' + str(data.iloc[row]['clients_name']))
        self.textBrowser_clients_details.append('\n' + '身份证号：   ' + str(data.iloc[row]['clients_id']))
        self.textBrowser_clients_details.append('\n' + '电话号码：   ' + str(data.iloc[row]['clients_tel']))
        self.textBrowser_clients_details.append('\n' + '联系地址：   ' + str(data.iloc[row]['clients_address']))
        self.textBrowser_clients_details.append('\n' + '照片位置：   ' + str(data.iloc[row]['clients_photo_address']))

        photo_path = './clients_photo/' + data.iloc[row, 0] + '.jpg'
        if os.path.exists(photo_path):
            self.show_client_photo(photo_path)
        else:
            self.show_client_photo('./logo/logo.png')

    def show_tq_account_info(self, qModelIndex):    # 显示天勤账户信息
        row = qModelIndex.row()    
        data = self.ioModal.read_csv_file(path='./data/tq_account.csv')
        self.textBrowser_tq_account_details.clear()
        self.textBrowser_tq_account_details.append('\n'   + '天勤帐户： ' + '\n\n' + '        ' + str(data.iloc[row]['tq_account']))
        self.textBrowser_tq_account_details.append('\n\n' + '该帐户所属客户： ' + '\n\n' + '        ' + str(data.iloc[row]['clients_name']))
        self.textBrowser_tq_account_details.append('\n\n' + '天勤密码： ' + '\n\n' + '        ' + str(data.iloc[row]['tq_psd']))
        self.textBrowser_tq_account_details.append('\n\n' + '该帐户绑定的期货公司： ' + '\n\n' + '        ' + str(data.iloc[row]['futures_company']))
        self.textBrowser_tq_account_details.append('\n\n' + '期货实盘资金帐户： ' + '\n\n' + '        ' + str(data.iloc[row]['futures_account']))
        self.textBrowser_tq_account_details.append('\n\n' + '期货实盘资金密码： ' + '\n\n' + '        ' + str(data.iloc[row]['futures_psd']))

    
    def show_file_in_treeview(self):    # 以树状结构显示 log 文件夹和文件
        # 在self.treeView_log中显示./log/ 下的文件和文件夹
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath('./log')
        self.treeview_log.setModel(self.file_system_model)
        self.treeview_log.setRootIndex(self.file_system_model.index('./log'))
        self.treeview_log.setColumnHidden(1, True)  
        self.treeview_log.setColumnHidden(2, True)
        self.treeview_log.setColumnHidden(3, True)
        
    def on_tree_licked(self, qmodelindex):  # 当点击树状结构时，显示文件内容
        # 当点击treeview_log中的文件时，在textBrowser_log显示文件的内容
        if qmodelindex.column() == 0:
            file_name = self.file_system_model.fileName(qmodelindex)    # 获取当前选中的文件名
            file_path = self.file_system_model.filePath(qmodelindex)    # 获取当前选中的文件路径

            if os.path.isfile(file_path):   # 如果是文件
                self.textBrowser_log.clear()
                with open(file_path, 'r', encoding='utf-8') as f:

                    self.textBrowser_log.setText(f.read())      # 将文件内容显示在textBrowser_log中
                    # 显示文本的最底部
                    cursor = self.textBrowser_log.textCursor() # 获取光标
                    cursor.movePosition(QtGui.QTextCursor.End)  # 光标移动到最后
                    self.textBrowser_log.setTextCursor(cursor) # 设置光标
                    self.textBrowser_log.ensureCursorVisible() # 光标可见

                    f.close()                                   # 关闭文件
            
            self.label_log_file_name.setText(file_name)         # 显示文件名
            
            self.label_log_file_address.setText(file_path)      # 显示文件地址
        else:
            pass            
   
    def kill_process(self, pid):    # 杀死单个进程
        try:
            parent_proc = psutil.Process(pid)
            for child_proc in parent_proc.children(recursive=True):
                child_proc.kill()
            parent_proc.kill()
            print('pid为 ' + str(pid) + ' 的子进程 关闭成功 ！！！\n')
        except Exception as e:
            print('pid为 ' + str(pid) + ' 的子进程 关闭失败 ！！！\n')
            print(e)
            print('\n')

    def kill_all_process(self):   # 杀死所有进程
        # 关闭所有进程
        for pid in self.get_alive_process_pid_list():
            self.kill_process(pid)
        print('所有子进程都已关闭!\n')

    def process_dict_update(self):  # 更新进程字典
        path = './data/config.csv'
        data = self.ioModal.read_csv_file(path)

        for index, item in data.iterrows():
            if item['whether_self_start'] == True:
                # 判断self.Process_dict中是否有该进程，如果有，则不再添加
                if item['process_name'] in self.Process_dict.keys():
                    pass
                else:
                    self.Process_dict[item['process_name']] = ''

    def get_clients_list(self):   # 获取用户列表
        clients_list = []
        data = self.ioModal.read_csv_file(path='./data/clients.csv')
        if data.empty:
            clients_list = []
        else:
            for account in data['clients_name']:
                clients_list.append(str(account))

        return clients_list

    def get_tq_account_list(self):  # 获取天勤账号列表
        tq_account_list = []
        data = self.ioModal.read_csv_file(path='./data/tq_account.csv')
        if data.empty:
            clients_list = []
        else:
            for index, item in data.iterrows():
                tq_account_list.append(str(item['tq_account']))

        return tq_account_list

    def get_alive_process_pid_list(self):   # 获取运行着的子进程 pid列表
        p = psutil.Process(os.getpid())        

        # 获取p.children()中的所有子进程pid，并生成一个列表
        living_pid_list = [x.pid for x in p.children()]
        
        return living_pid_list

    def get_process_list(self):  # 获取活着的进程名列表
        process_list = []
        pid_list = self.get_alive_process_pid_list()
        # 判断self.Process_dict中每一项的值是否在pid_list中，如果在，则添加到process_list中
        for key, value in self.Process_dict.items():
            if value in pid_list:
                process_list.append(key)
        return process_list

    def get_qoute_list(self):   # 获取行情引用列表
        qoute_list = []
        data = self.ioModal.read_csv_file(path='./data/config.csv')
        if data.empty:
            qoute_list = []
        else:
            for index, item in data.iterrows():
                qoute_list.append(str(item['symbol']) + '-->' + str(item['symbol_period']) + ' min')

        return qoute_list

    def get_strategy_list(self, path):  # 从策略文件中自动搜索并获取策略类名 列表
        class_name_list = []
        try:
            file_list = os.listdir(path)
        except:
            file_list = []
            print('the path is not dir')
        if file_list:
            for file in file_list:
                file = os.path.join(path, file)
                if os.path.isdir(file):
                    self.get_strategy_list(file)
                else:
                    if file.endswith('.py'):
                        with open(file, encoding='utf-8') as f:
                            for line in f.readlines():
                                cls_match = re.match(r'class\s(.*?)[\(:]', line)        # 用正则表达式寻找class关键字之后的类名
                                if cls_match:
                                    cls_name = cls_match.group(1)    

                                    #判断cls_name是否是和文件名相同的类
                                    if cls_name == file.split('\\')[-1].split('.')[0]:
                                        class_name_list.append(cls_name)                                        
                                    else:
                                        pass                                    
        return class_name_list


    def switch_left_panel(self, enable):    # 左侧面板开关切换
        if enable:            
            width = self.left_panel.width()
            max_with = 350
            min_with = 0            
            if width > 100:
                widthExtended = min_with
            else:
                widthExtended = max_with
            # 动画效果
            self.animation = QPropertyAnimation(self.left_panel, b"maximumWidth")
            self.animation.setDuration(500)
            self.animation.setStartValue(width)
            self.animation.setEndValue(widthExtended)
            self.animation.setEasingCurve(QtCore.QEasingCurve.InOutQuart)  # 设置动画的缓动效果
            self.animation.start()

    def maxmize_normalmize(self):   # 窗口最大化和还原
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
            self.left_panel.setMaximumWidth(350)

    def previous_page(self):    # 向前翻页
        t = self.stackedWidget.currentIndex()
        self.stackedWidget.setCurrentIndex(t - 1)

    def next_page(self):    # 向后翻页
        t = self.stackedWidget.currentIndex()
        self.stackedWidget.setCurrentIndex(t + 1)

    def choose_client_photo_File(self): # 选择客户头像
        fileName_choose, filetype = QFileDialog.getOpenFileName(self, '选取文件', self.cwd, # 起始路径 
                                    'All Files (*);;Text Files (*.txt)')   # 设置文件扩展名过滤,用双分号间隔

        if fileName_choose == '':
            print('\n没有选择任何文件')
            return

        self.clients_photo_address.setText(fileName_choose)
        print('\n已选择用户照片，  图片文件为:')
        print(fileName_choose)
        print('文件筛选器类型: ',filetype)
        self.show_client_photo(fileName_choose)

    def show_client_photo(self, file):  # 显示客户头像
        img = QImage()

        if img.load(file):
            
            width = img.width()
            height = img.height()

            if width >= height:
                ratio = width/500
            else:
                ratio = height/500
            new_width = width/ratio
            new_height = height/ratio
            
            self.label_client_photo_show.setFixedSize(new_width, new_height)
            self.label_client_photo_show.setPixmap(QPixmap(file).scaled(new_width, new_height))

    def get_clients(self):  # 获取并保存输入的用户信息

        clients_dict = {}

        clients_dict['clients_name'] = self.clients_name.text()
        clients_dict['clients_id'] = self.clients_id.text()
        clients_dict['clients_tel'] = self.clients_tel.text()
        clients_dict['clients_address'] = self.clients_address.text()

        # 判断是否存在clients_photo文件夹，如果不存在，则创建
        if not os.path.exists('./clients_photo'):
            os.makedirs('./clients_photo')
            
        # 将clients_photo_address.text()的图片复制到clients_photo文件夹中
        #打开源图片
        f_src = open(self.clients_photo_address.text(), 'rb')
        #self.clients_photo_address.text()表示图片路径，为字符串。
        
        #读取图片内容并存储到content临时变量
        content = f_src.read()
        
        #以二进制格式打开复制后的图片（只写）
        #wb一般用于非文本文件如图片等。
        #如果该文件已存在则打开文件，并从开头开始编辑，即原有内容会被删除。
        #如果该文件不存在，创建新文件。
        photo_name = './clients_photo/' + self.clients_name.text() + '.jpg'
        f_copy = open(photo_name, 'wb')
        
        #源图片的内容以二进制形式写入新图片
        f_copy.write(content)
        #关闭文件（原则：先打开的后关闭）
        f_copy.close()
        f_src.close()
        

        clients_dict['clients_photo_address'] = photo_name

        df = pd.DataFrame(clients_dict, index=[0])
        path = './data/clients.csv'
        self.ioModal.judge_config_exist(path)
        self.ioModal.add_dict_to_csv(df, path)
        time.sleep(0.1)
        self.clients_input_clear()
        self.add_paramer_to_container()
        self.add_paramer_to_combobox()

    def clients_input_clear(self):  # 清空客户信息输入框
        self.add_paramer_to_combobox()
        self.clients_name.clear()
        self.clients_id.clear()
        self.clients_tel.clear()
        self.clients_address.clear()

    def get_tq_account(self):   # 获取天勤账号信息

        tq_account_dict = {}
        tq_account_dict['clients_name'] = self.comboBox_select_clients_name.currentText()
        tq_account_dict['tq_account'] = self.tq_account.text()
        tq_account_dict['tq_psd'] = self.tq_psd.text()
        tq_account_dict['futures_company'] = self.futures_company.text()
        tq_account_dict['futures_account'] = self.futures_account.text()
        tq_account_dict['futures_psd'] = self.futures_psd.text()
        
        df = pd.DataFrame(tq_account_dict, index=[0])
        path = './data/tq_account.csv'
        self.ioModal.judge_config_exist(path)
        self.ioModal.add_dict_to_csv(df, path)
        time.sleep(0.1)
        self.tq_account_input_clear()
        self.add_paramer_to_container()
        self.add_paramer_to_combobox()

    def tq_account_input_clear(self):   # 清空天勤账号信息输入框
        self.add_paramer_to_combobox()
        self.tq_account.clear()
        self.tq_psd.clear()
        self.futures_company.clear()
        self.futures_account.clear()
        self.futures_psd.clear()

    def add_paramer_to_combobox(self):  # 将参数添加到combobox中
        self.comboBox_select_clients_name.clear()     
        self.add_clients_list_to_combobox()

    def add_clients_list_to_combobox(self): # 将用户列表添加到combobox中
        clients_list = self.get_clients_list()
        for item in clients_list:            
            self.comboBox_select_clients_name.addItem(item)


    def get_inactivated_process_quantity(self): # 获取可自启动但还未启动的策略进程数量
        path = './data/config.csv'
        data = self.ioModal.read_csv_file(path)
        quantity = 0
        if data.empty:
            pass
        else:
            for index, item in data.iterrows():
                if item['whether_self_start'] == True:
                    quantity += 1
        return quantity

    def get_tq_account_quantity(self):  # 获取天勤账户数量
        path = './data/tq_account.csv'
        data = self.ioModal.read_csv_file(path)
        quantity = 0
        if data.empty:
            pass
        else:
            for index, item in data.iterrows():
                if item['tq_account']:
                    quantity += 1
        return quantity

    def get_total_profit(self): # 计算总盈亏
        path = './data/config.csv'
        data = self.ioModal.read_csv_file(path)
        total_profit = 0
        if data.empty:
            pass
        else:
            for index, item in data.iterrows():
                try:               
                    # 如果item['initial_capital']和item['final_capital']都存在且不为NaN
                    if item['initial_capital'] and item['final_capital'] :
                        if item['initial_capital'] != 'NaN' and item['final_capital'] != 'NaN':
                            #判断item['initial_capital']和item['final_capital']是否为字符型
                            if isinstance(item['initial_capital'],str) and isinstance(item['final_capital'],str):
                                pass
                            else:                                               

                                profit = float(item['final_capital']) - float(item['initial_capital'])
                                total_profit += profit
                        else:
                            pass
                    
                    else:
                        pass
                except:
                    pass
        return total_profit

    def get_frame_runing_time(self):    # 计算框架运行时间
        start_time = self.start_time
        current_time = datetime.now()

        gap = current_time - start_time
        days = gap.days
        hours = gap.seconds // 3600
        minutes = (gap.seconds % 3600) // 60
        seconds = (gap.seconds % 3600) % 60

        time_interval = str(days) + ' 天   ' + str(hours) + ' 小时 \n' + str(minutes) + ' 分   ' + str(seconds) + ' 秒 '
        return time_interval

    def open_file_with_excel(self, path):   # 用 excel 打开文件

        out_file = Path.cwd() / path
        excel = win32.gencache.EnsureDispatch('Excel.Application')
        excel.Visible = True       
        excel.Workbooks.Open(out_file)

    def draw_dount_chart(self): # 画饼图
        chart = QChart()
        pi = self.pieCard
        cd = DonutWidget(pi)
        cd.add_donut()

    def load_deal_detials_data(self):   # 加载交易明细数据
        dirs = './data/'
        if not os.path.exists(dirs):
            os.makedirs(dirs)
        if os.path.exists('./data/deal_detials.csv'):
            df = pd.read_csv('./data/deal_detials.csv')
            table = self.tableWidget_deal_detials
            table.setColumnCount(len(df.columns))
            table.setHorizontalHeaderLabels(df.columns)
            table.setRowCount(len(df.index))

            for rn, row in enumerate(df.index):
                for cn, col in enumerate(df.columns):
                    item = QTableWidgetItem(str(df.loc[row, col]))
                    table.setItem(rn, cn, item)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)  # 文字具中显示
        else:
            path = './data/deal_detials.csv'
            self.ioModal.judge_config_exist(path)
            print('文件不存在，已创建空文件')

    def load_process_config(self):  # 加载策略进程配置
        dirs = './data/'
        if not os.path.exists(dirs):
            os.makedirs(dirs)
        if os.path.exists('./data/config.csv'):
            df = pd.read_csv('./data/config.csv')
            table = self.tableWidget_process
            table.setColumnCount(len(df.columns))
            table.setHorizontalHeaderLabels(df.columns)
            table.setRowCount(len(df.index))

            for rn, row in enumerate(df.index):
                for cn, col in enumerate(df.columns):
                    item = QTableWidgetItem(str(df.loc[row, col]))
                    table.setItem(rn, cn, item)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)  # 文字具中显示
        else:
            path = './data/config.csv'
            self.ioModal.judge_config_exist(path)
            print('文件不存在，已创建空文件')