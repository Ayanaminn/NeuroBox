import NeuroBox_UI
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTreeWidgetItem,QPlainTextEdit,QMessageBox,QFileDialog,QMenu,QVBoxLayout,QGroupBox
from PyQt5.QtGui import QColor,QBrush
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread, QObject, QMutex, QMutexLocker,QTimer
import time
import serial
import logging
import pandas as pd
from openpyxl import load_workbook
import numpy as np

import serial.tools.list_ports

class MainWindow(QtWidgets.QMainWindow, NeuroBox_UI.Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.log_box = LogBox(self)
        self.log_box.setTitle('Log Messages')
        self.log_box.setGeometry(QtCore.QRect(50, 360, 1020, 110))
        self.log_box.display_info('Welcome!')

        self.available_ports = []
        self.active_device = None
        self.init_port()
        self.port_refresh_button.clicked.connect(self.refresh_port)
        self.port_connect_button.clicked.connect(self.connect_port)
        self.port_disconnect_button.clicked.connect(self.disconnect_port)

        self.condition_a.addItems(['ON', 'OFF'])
        self.condition_b.addItems(['ON', 'OFF'])
        self.condition_c.addItems(['ON', 'OFF'])

        self.rule_index = 0 # first rule index is 1
        self.rule_list = []

        heads = ['Step','Channel A','Time(s)', 'Channel B', 'Time(s)', 'Channel C', 'Time(s)']
        self.treeWidget.setHeaderLabels(heads)
        self.treeWidget.setAlternatingRowColors(True)
        self.treeWidget.setColumnWidth(0,20)
        self.treeWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(self.rule_menu)

        self.add_rule_button.clicked.connect(self.add_rule)
        self.clear_rule_button.clicked.connect(self.clear_rule)
        self.apply_setting_button.clicked.connect(self.apply_setting)

        self.channel_a_thread = ChannelAThread()
        self.channel_a_thread.signals.on.connect(self.channel_a_on)
        self.channel_a_thread.signals.off.connect(self.channel_a_off)
        self.channel_a_thread.signals.finish.connect(self.loop_a_finish)

        self.channel_b_thread = ChannelBThread()
        self.channel_b_thread.signals.b_on.connect(self.channel_b_on)
        self.channel_b_thread.signals.b_off.connect(self.channel_b_off)
        self.channel_b_thread.signals.b_finish.connect(self.loop_b_finish)

        self.channel_c_thread = ChannelCThread()
        self.channel_c_thread.signals.c_on.connect(self.channel_c_on)
        self.channel_c_thread.signals.c_off.connect(self.channel_c_off)
        self.channel_c_thread.signals.c_finish.connect(self.loop_c_finish)

        self.start_button.clicked.connect(self.start)
        self.stop_button.clicked.connect(self.stop)

        self.action_load.triggered.connect(self.load_para)
        self.action_save.triggered.connect(self.save_para)

        self.light_A.setStyleSheet('background-color:grey')
        self.light_B.setStyleSheet('background-color:grey')
        self.light_C.setStyleSheet('background-color:grey')
        self.light_loop.setStyleSheet('background-color:grey')


    def get_all_items(self):
        i = 0
        item_num = self.treeWidget.topLevelItemCount()
        while i<item_num:
            all_items = self.treeWidget.topLevelItem(i)
            i+=1
            print(all_items)

    def init_port(self):

        self.port_comboBox.addItem('')
        ports = serial.tools.list_ports.comports()

        for p in ports:
            self.available_ports.append([p.description, p.device])
            # print(str(p.description)) # device name + port name
            # print(str(p.device)) # port name

        for info in self.available_ports:
            self.port_comboBox.addItem(info[0])

        print(f'List of available ports {self.available_ports}')
        self.log_box.display_info(f'List of available ports {self.available_ports}')

    def refresh_port(self):
        self.available_ports.clear()
        self.port_comboBox.clear()
        self.init_port()
        print(f'List of available ports {self.available_ports}')
        self.log_box.display_info(f'List of available ports {self.available_ports}')

    def connect_port(self):

        # selected_port_index = self.select_port()
        selected_port_index = self.port_comboBox.currentIndex() -1
        print(f'selected port index is {selected_port_index}')
        if self.available_ports and selected_port_index != -1:
            try:
                # portOpen = True
                self.active_device = serial.Serial(self.available_ports[selected_port_index][1], 9600, timeout=1)
                print(f'Connected to port {self.available_ports[selected_port_index][1]}!')
                self.log_box.display_info(f'Connected to port {self.available_ports[selected_port_index][1]}!')
                time.sleep(0.5)
                # start all channels at off state
                self.active_device.write('10\n'.encode()) #pin5
                self.active_device.write('20\n'.encode()) #pin6
                self.active_device.write('30\n'.encode()) #pin7
                print(f'device is open : {self.active_device.isOpen()}')
                self.log_box.display_info(f'Device is open : {self.active_device.isOpen()}')

                self.port_comboBox.setEnabled(False)
                self.port_connect_button.setEnabled(False)
                self.port_refresh_button.setEnabled(False)
                self.port_disconnect_button.setEnabled(True)

                self.condition_a.setEnabled(True)
                self.condition_b.setEnabled(True)
                self.condition_c.setEnabled(True)
                self.time_a.setEnabled(True)
                self.time_b.setEnabled(True)
                self.time_c.setEnabled(True)

                self.action_load.setEnabled(True)

                self.add_rule_button.setEnabled(True)

            except Exception as e:
                error = str(e)
                self.error_msg = QMessageBox()
                self.error_msg.setWindowTitle('Error')
                self.error_msg.setText('Cannot connect to selected port.')
                self.error_msg.setInformativeText('Please select a valid port')
                self.error_msg.setIcon(QMessageBox.Warning)
                self.error_msg.setDetailedText(error)
                self.error_msg.exec()
                self.refresh_port()

        elif not self.available_ports:
            self.error_msg = QMessageBox()
            self.error_msg.setWindowTitle('Error')
            self.error_msg.setText('Cannot read available ports of the system.')
            self.error_msg.setInformativeText('Please try reload port.')
            self.error_msg.setIcon(QMessageBox.Warning)
            self.error_msg.exec()
            self.refresh_port()

        elif selected_port_index == -1:
            self.error_msg = QMessageBox()
            self.error_msg.setWindowTitle('Error')
            self.error_msg.setText('Please select a valid port.')
            self.error_msg.setInformativeText('selected_port_index is empty.')
            self.error_msg.setIcon(QMessageBox.Warning)
            self.error_msg.exec()
            self.refresh_port()

    def disconnect_port(self):
        try:
            # set all channels at off state when disconnect
            self.active_device.write('10\n'.encode())
            self.active_device.write('20\n'.encode())
            self.active_device.write('30\n'.encode())
            self.active_device.close()

        except Exception as e:
            error = str(e)
            self.error_msg = QMessageBox()
            self.error_msg.setWindowTitle('Error')
            self.error_msg.setText('Cannot disconnect from selected port.')
            self.error_msg.setInformativeText('disconnect_port() failed.')
            self.error_msg.setIcon(QMessageBox.Warning)
            self.error_msg.setDetailedText(error)
            self.error_msg.exec()

        if not self.active_device.isOpen():
            print('Connection now closed')
            print(f'device is open : {self.active_device.isOpen()}')
            self.log_box.display_info('Connection now closed')
            self.log_box.display_info(f'Device is open : {self.active_device.isOpen()}')

            self.port_comboBox.setEnabled(True)
            self.port_connect_button.setEnabled(True)
            self.port_disconnect_button.setEnabled(False)

            self.clear_rule()
            self.condition_a.setEnabled(False)
            self.condition_b.setEnabled(False)
            self.condition_c.setEnabled(False)
            self.time_a.setEnabled(False)
            self.time_b.setEnabled(False)
            self.time_c.setEnabled(False)
            self.total_cycle.setEnabled(False)
            self.action_load.setEnabled(False)
            self.action_save.setEnabled(False)
            self.add_rule_button.setEnabled(False)
            self.apply_setting_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.refresh_port()

    def add_rule(self):
        # create a rule from current input and append to rule list
        self.rule_index += 1
        condition_a = self.condition_a.currentText()
        time_a = self.time_a.value()
        condition_b = self.condition_b.currentText()
        time_b = self.time_b.value()
        condition_c = self.condition_c.currentText()
        time_c = self.time_c.value()

        new_rule = Rules(self.rule_index, condition_a,time_a,condition_b,time_b,condition_c,time_c)

        current_rule_text = []
        for attr, value in new_rule.__dict__.items():
            current_rule_text.append(str(value))

        current_rule_display = QTreeWidgetItem(self.treeWidget, current_rule_text)
        self.treeWidget.addTopLevelItem(current_rule_display)

        self.rule_list.append(new_rule)

        if self.treeWidget.topLevelItemCount() > 1:
            self.treeWidget.itemAbove(current_rule_display).setDisabled(True)

        self.action_save.setEnabled(True)
        self.total_cycle.setEnabled(True)
        self.clear_rule_button.setEnabled(True)
        self.apply_setting_button.setEnabled(True)

    def rule_menu(self,point):
        rule_item = self.treeWidget.indexAt(point)
        # print(rule_item)
        if not rule_item.isValid():
            return
        else:
            selected_rule = self.treeWidget.itemAt(point)
            if not selected_rule.isDisabled():
                # print(selected_rule.isSelected())
                selected_index = self.treeWidget.indexOfTopLevelItem(selected_rule)
                # print(f'selected index is {selected_index}')
                self.rule_menu = QMenu(self.treeWidget)
                self.rule_menu.addAction("Delete",lambda :self.delete_rule(selected_index))
                self.rule_menu.exec_(self.treeWidget.mapToGlobal(point))

    def delete_rule(self, rule_index):
        # print('delete')
        self.treeWidget.takeTopLevelItem(rule_index)
        self.rule_list.pop(-1)
        self.rule_index -= 1
        # for i in self.rule_list:
        #     print(f'rule {i.rule_index} after delete last item {i.time_a}')
        if self.treeWidget.topLevelItemCount() >= 1:
            self.treeWidget.topLevelItem(rule_index-1).setDisabled(False)
        if rule_index == 0:
            self.clear_rule()

    def clear_rule(self):
        self.rule_list.clear()
        self.rule_index = 0
        self.treeWidget.clear()
        self.add_rule_button.setEnabled(True)
        self.total_cycle.setEnabled(False)
        self.apply_setting_button.setEnabled(False)
        self.clear_rule_button.setEnabled(False)

    def apply_setting(self):

        reply = QMessageBox.question(self,'Apply settings',
                                     'Use current settings?\n'
                                     'You will not be able to edit again once apply.',
                                     QMessageBox.Apply,QMessageBox.Cancel)
        if reply == QMessageBox.Apply:
            self.start_button.setEnabled(True)
            self.total_cycle.setEnabled(False)
            self.add_rule_button.setEnabled(False)
            self.apply_setting_button.setEnabled(False)
            self.clear_rule_button.setEnabled(False)
            step_time_a = []
            step_condition_a = []
            step_time_b = []
            step_condition_b = []
            step_time_c = []
            step_condition_c = []

            for i in self.rule_list:
                # seconds to milliseconds
                step_time_a.append(i.time_a * 1000)
                step_time_b.append(i.time_b * 1000)
                step_time_c.append(i.time_c * 1000)
            self.channel_a_thread.step_time = step_time_a
            self.channel_b_thread.step_time = step_time_b
            self.channel_c_thread.step_time = step_time_c

            total_time = [sum(step_time_a),
                          sum(step_time_b),
                          sum(step_time_c)]
            max_index = total_time.index(max(total_time))
            if max_index == 0:
                self.channel_a_thread.signals.update_loop.connect(self.update_counter)
            elif max_index == 1:
                self.channel_b_thread.signals.update_loop.connect(self.update_counter)
            elif max_index == 2:
                self.channel_c_thread.signals.update_loop.connect(self.update_counter)
            else:
                self.channel_a_thread.signals.update_loop.connect(self.update_counter)

            for i in self.rule_list:
                if i.condition_a == 'ON':
                    step_condition_a.append(1)
                elif i.condition_a == 'OFF':
                    step_condition_a.append(0)
            self.channel_a_thread.step_state = step_condition_a

            for i in self.rule_list:
                if i.condition_b == 'ON':
                    step_condition_b.append(1)
                elif i.condition_b == 'OFF':
                    step_condition_b.append(0)
            self.channel_b_thread.step_state = step_condition_b

            for i in self.rule_list:
                if i.condition_c == 'ON':
                    step_condition_c.append(1)
                elif i.condition_c == 'OFF':
                    step_condition_c.append(0)
            self.channel_c_thread.step_state = step_condition_c

            self.channel_a_thread.total_steps = self.rule_list[-1].rule_index
            self.channel_b_thread.total_steps = self.rule_list[-1].rule_index
            self.channel_c_thread.total_steps = self.rule_list[-1].rule_index
            print(f'total steps passed to thread is {self.channel_a_thread.total_steps}')
            print(f'total steps passed to thread b is {self.channel_b_thread.total_steps}')
            print(f'total steps passed to thread c is {self.channel_c_thread.total_steps}')

            self.channel_a_thread.cycles = self.total_cycle.value()
            self.channel_b_thread.cycles = self.total_cycle.value()
            self.channel_c_thread.cycles = self.total_cycle.value()
        else:
            return

    def load_para(self):
        try:
            # set default directory for load files and set file type that only shown
            file = QFileDialog.getOpenFileName(directory='C:/Users/Public/Desktop',
                                               filter='Excel(*.xlsx)')
            # if no file selected
            if file[0] == '':
                return
            else:
                self.para_file = file
                # print(self.para_file)
                df_read = pd.read_excel(self.para_file[0], sheet_name='para')
                path = self.para_file[0]
                book = load_workbook(path)
                # print(df_read)
                for row in df_read.itertuples():
                    rule_index = row[1]
                    state_a = row[2]
                    time_a = row[3]
                    state_b = row[4]
                    time_b = row[5]
                    state_c = row[6]
                    time_c = row[7]
                    new_rule = Rules(rule_index, state_a, time_a, state_b, time_b, state_c, time_c)
                    current_rule_text = []
                    for attr, value in new_rule.__dict__.items():
                        current_rule_text.append(str(value))
                    current_rule_display = QTreeWidgetItem(self.treeWidget, current_rule_text)
                    self.treeWidget.addTopLevelItem(current_rule_display)

                    self.rule_list.append(new_rule)
                self.log_box.display_info('Settings loaded.')
            self.add_rule_button.setEnabled(False)
            self.total_cycle.setEnabled(True)
            self.clear_rule_button.setEnabled(True)
            self.apply_setting_button.setEnabled(True)

        except Exception as e:
            error = str(e)
            self.error_msg = QMessageBox()
            self.error_msg.setWindowTitle('Error')
            self.error_msg.setText('An error happened when trying to load file.')
            self.error_msg.setIcon(QMessageBox.Warning)
            self.error_msg.setDetailedText(error)
            self.error_msg.exec()

    def save_para(self):
        # self.save_path = QFileDialog.getExistingDirectory(None, 'Select Folder', 'C:/Users/Public/Documents')
        self.para_file, _ = QFileDialog.getSaveFileName(
            self, "Select folder", 'C:/Users/Public/Documents', "Excel (*.xlsx)")

        if self.para_file == '':
            return
        else:
            # print(self.para_file)
            try:
                df_para = []
                for i in range(len(self.rule_list)):
                    # print(self.rule_list[i].rule_index)
                    df_para.append([self.rule_list[i].rule_index,
                                    self.rule_list[i].condition_a,
                                    self.rule_list[i].time_a,
                                    self.rule_list[i].condition_b,
                                    self.rule_list[i].time_b,
                                    self.rule_list[i].condition_c,
                                    self.rule_list[i].time_c])
                # print(df_para)
                df_write = pd.DataFrame(np.array(df_para), columns=['Step',
                                                                    'Channel A',
                                                                    'Time(s)',
                                                                    'Channel B',
                                                                    'Time(s)',
                                                                    'Channel C',
                                                                    'Time(s)'])
                with pd.ExcelWriter(self.para_file, engine='xlsxwriter') as writer:
                    df_write.to_excel(writer, sheet_name='para', index=False)
                self.log_box.display_info('Settings saved.')

            except Exception as e:
                print(e)

    def start(self):
        try:
            self.light_loop.setStyleSheet('background-color:green')
            self.loop_counter_label.setText('1')
            self.channel_a_thread.run()
            self.channel_b_thread.run()
            self.channel_c_thread.run()

            self.stop_button.setEnabled(True)
            self.start_button.setEnabled(False)
            self.log_box.display_info('Trial started.')
        except Exception as e:
            error = str(e)
            self.error_msg = QMessageBox()
            self.error_msg.setWindowTitle('Error')
            self.error_msg.setText('An error occurred when attempt to execute the program')
            self.error_msg.setInformativeText(error)
            self.error_msg.setIcon(QMessageBox.Warning)
            self.error_msg.exec()

    def clear(self):
        self.active_device.write('10\n'.encode())
        self.active_device.write('20\n'.encode())
        self.active_device.write('30\n'.encode())
        self.rule_list.clear()
        self.rule_index = 0
        self.treeWidget.clear()
        self.start_button.setEnabled(False)

    def stop(self):
        if self.stop_button.text() == 'STOP':
            reply = QMessageBox.question(self,'Stop running',
                                         'Warning: The program is running. '
                                         'Stop it will terminate hardware control and reset all settings.\n'
                                         'Confirm to stop?',
                                         QMessageBox.Yes,QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                try:
                    self.channel_a_thread.stop()
                    self.light_A.setStyleSheet('background-color:grey')
                    self.channel_b_thread.stop()
                    self.light_B.setStyleSheet('background-color:grey')
                    self.channel_c_thread.stop()
                    self.light_C.setStyleSheet('background-color:grey')
                    self.log_box.display_info('Trial stopped.')
                except Exception as e:
                    error = str(e)
                    self.error_msg = QMessageBox()
                    self.error_msg.setWindowTitle('Error')
                    self.error_msg.setText('An error occurred when attempt to terminate the program')
                    self.error_msg.setInformativeText(error)
                    self.error_msg.setIcon(QMessageBox.Warning)
                    self.error_msg.exec()
                finally:
                    self.active_device.write('10\n'.encode())
                    self.active_device.write('20\n'.encode())
                    self.active_device.write('30\n'.encode())
                    self.light_loop.setStyleSheet('background-color:red')
                    self.loop_counter_label.setText('0')
                    self.stop_button.setEnabled(False)
                    self.condition_a.setEnabled(True)
                    self.condition_b.setEnabled(True)
                    self.condition_c.setEnabled(True)
                    self.time_a.setEnabled(True)
                    self.time_b.setEnabled(True)
                    self.time_c.setEnabled(True)
                    self.action_load.setEnabled(True)
                    self.add_rule_button.setEnabled(True)
                    self.action_save.setEnabled(True)
                    self.total_cycle.setEnabled(True)
                    self.clear_rule_button.setEnabled(True)
                    self.apply_setting_button.setEnabled(True)
            else:
                return
        elif self.stop_button.text() == 'RESET':
            self.reset()

    def update_counter(self,count):
        self.loop_counter_label.setText(str(count+1))

    def reset(self):

        self.active_device.write('10\n'.encode())
        self.active_device.write('20\n'.encode())
        self.active_device.write('30\n'.encode())
        self.light_loop.setStyleSheet('background-color:grey')
        self.loop_counter_label.setText('0')
        self.stop_button.setEnabled(False)
        self.condition_a.setEnabled(True)
        self.condition_b.setEnabled(True)
        self.condition_c.setEnabled(True)
        self.time_a.setEnabled(True)
        self.time_b.setEnabled(True)
        self.time_c.setEnabled(True)
        self.action_load.setEnabled(True)
        self.add_rule_button.setEnabled(True)
        self.action_save.setEnabled(True)
        self.total_cycle.setEnabled(True)
        self.clear_rule_button.setEnabled(True)
        self.apply_setting_button.setEnabled(True)
        self.stop_button.setText('STOP')

    def channel_a_on(self):
        self.light_A.setStyleSheet('background-color:yellow')
        self.active_device.write('11\n'.encode())

    def channel_a_off(self):
        self.light_A.setStyleSheet('background-color:black')
        self.active_device.write('10\n'.encode())

    def loop_a_finish(self):
        # change flag and reset counters
        self.channel_a_thread.stop()
        self.active_device.write('10\n'.encode())
        self.light_A.setStyleSheet('background-color:grey')
        if self.channel_a_thread.stopped and self.channel_b_thread.stopped and self.channel_c_thread.stopped:
            self.light_loop.setStyleSheet('background-color:red')
            self.log_box.display_info('All trial cycles are finished.Click RESET to start a new trial.')
            self.stop_button.setText('RESET')

    def channel_b_on(self):
        self.light_B.setStyleSheet('background-color:yellow')
        self.active_device.write('21\n'.encode())

    def channel_b_off(self):
        self.light_B.setStyleSheet('background-color:black')
        self.active_device.write('20\n'.encode())

    def loop_b_finish(self):
        self.channel_b_thread.stop()
        self.active_device.write('20\n'.encode())
        self.light_B.setStyleSheet('background-color:grey')
        if self.channel_a_thread.stopped and self.channel_b_thread.stopped and self.channel_c_thread.stopped:
            self.light_loop.setStyleSheet('background-color:red')
            self.log_box.display_info('All trial cycles are finished.Click RESET to start a new trial.')
            self.stop_button.setText('RESET')

    def channel_c_on(self):
        self.light_C.setStyleSheet('background-color:yellow')
        self.active_device.write('31\n'.encode())

    def channel_c_off(self):
        self.light_C.setStyleSheet('background-color:black')
        self.active_device.write('30\n'.encode())

    def loop_c_finish(self):
        self.channel_c_thread.stop()
        self.active_device.write('30\n'.encode())
        self.light_C.setStyleSheet('background-color:grey')
        if self.channel_a_thread.stopped and self.channel_b_thread.stopped and self.channel_c_thread.stopped:
            self.light_loop.setStyleSheet('background-color:red')
            self.log_box.display_info('All trial cycles are finished.Click RESET to start a new trial.')
            self.stop_button.setText('RESET')


class Rules(object):
    _registry = []

    def __init__(self, rule_index, condition_a, time_a, condition_b, time_b, condition_c, time_c):

        self.rule_index = rule_index
        self.condition_a = condition_a
        self.time_a = time_a
        self.condition_b = condition_b
        self.time_b = time_b
        self.condition_c = condition_c
        self.time_c = time_c
        self._registry.append(self)


class Signals(QObject):
    on = pyqtSignal(str)
    off = pyqtSignal(str)
    finish = pyqtSignal(str)
    b_on = pyqtSignal(str)
    b_off = pyqtSignal(str)
    b_finish = pyqtSignal(str)
    c_on = pyqtSignal(str)
    c_off = pyqtSignal(str)
    c_finish = pyqtSignal(str)
    update_loop = pyqtSignal(int)
    log_msg = pyqtSignal(str)


class ChannelAThread(QThread):

    def __init__(self):
        QThread.__init__(self)
        self.signals = Signals()
        self.mutex = QMutex()
        self.stopped = False

        self.step_timer = QTimer() # on/off time for each rule step
        self.current_step = 0 # init
        self.loop_counter = 0  # init
        self.total_steps = 0 # init total
        self.step_time = []
        self.step_state = [] # 0:off, 1: on
        self.cycles = 0

        self.step_timer.setSingleShot(True)
        self.step_timer.timeout.connect(self.update_loop)

    def run(self):
        with QMutexLocker(self.mutex):
            self.stopped = False
        try:
            self.update_loop()
        except Exception as e:
            print(e)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True
        self.current_step = 0  # reset
        self.loop_counter = 0

    def update_steps(self):
        if not self.stopped:
            # within current loop
            # if not last step
            if self.current_step < self.total_steps:
                # get on/off time for current rule from rule list
                self.step_timer.setInterval(self.step_time[self.current_step])
                # if state for this step is on
                if self.step_state[self.current_step] == 1:
                    self.signals.on.emit('1')
                    self.current_step +=1
                # if state for this step is off
                else:
                    self.signals.off.emit('1')
                    self.current_step += 1
                self.step_timer.start()
            # if already last step
            # go back to step 1 and re-execute all steps again
            else:
                self.current_step = 0
                self.loop_counter += 1
                self.update_loop()
        else:
            pass

    def update_loop(self):
        # thread run
        if not self.stopped:
            # if is last cycle
            if self.loop_counter >= self.cycles:
                self.signals.finish.emit('1')
            # if not last cycle
            # execute all steps
            else:
                self.signals.update_loop.emit(self.loop_counter)
                self.update_steps()
        # thread stopped
        else:
            pass


class ChannelBThread(QThread):

    def __init__(self):
        QThread.__init__(self)
        self.signals = Signals()
        self.mutex = QMutex()
        self.stopped = False

        self.step_timer = QTimer() # on/off time for each rule step
        self.current_step = 0 # init
        self.loop_counter = 0  # init
        self.total_steps = 0 # init total
        self.step_time = []
        self.step_state = [] # 0:off, 1: on
        self.cycles = 0

        self.step_timer.setSingleShot(True)
        self.step_timer.timeout.connect(self.update_loop)

    def run(self):
        with QMutexLocker(self.mutex):
            self.stopped = False
        try:
            self.update_loop()
        except Exception as e:
            print(e)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True
        self.current_step = 0  # reset
        self.loop_counter = 0

    def update_steps(self):
        if not self.stopped:
            # within current loop
            # if not last step
            if self.current_step < self.total_steps:
                # get on/off time for current rule from rule list
                self.step_timer.setInterval(self.step_time[self.current_step])
                # if state for this step is on
                if self.step_state[self.current_step] == 1:
                    self.signals.b_on.emit('1')
                    self.current_step +=1
                # if state for this step is off
                else:
                    self.signals.b_off.emit('1')
                    self.current_step += 1
                self.step_timer.start()
            # if already last step
            # go back to step 1 and re-execute all steps again
            else:
                self.current_step = 0
                self.loop_counter += 1
                self.update_loop()
        else:
            pass

    def update_loop(self):
        # thread run
        if not self.stopped:
            # if is last cycle
            if self.loop_counter >= self.cycles:  # 2 loop make 1 full cycle
                self.signals.b_finish.emit('1')
            # if not last cycle
            # execute all steps
            else:
                self.signals.update_loop.emit(self.loop_counter)
                self.update_steps()
        # thread stopped
        else:
            pass


class ChannelCThread(QThread):

    def __init__(self):
        QThread.__init__(self)
        self.signals = Signals()
        self.mutex = QMutex()
        self.stopped = False

        self.step_timer = QTimer() # on/off time for each rule step
        self.current_step = 0 # init
        self.loop_counter = 0  # init
        self.total_steps = 0 # init total
        self.step_time = []
        self.step_state = [] # 0:off, 1: on
        self.cycles = 0

        self.step_timer.setSingleShot(True)
        self.step_timer.timeout.connect(self.update_loop)

    def run(self):
        with QMutexLocker(self.mutex):
            self.stopped = False
        try:
            self.update_loop()
        except Exception as e:
            print(e)

    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True
        self.current_step = 0  # reset
        self.loop_counter = 0

    def update_steps(self):
        if not self.stopped:
            # within current loop
            # if not last step
            if self.current_step < self.total_steps:
                # get on/off time for current rule from rule list
                self.step_timer.setInterval(self.step_time[self.current_step])
                # if state for this step is on
                if self.step_state[self.current_step] == 1:
                    self.signals.c_on.emit('1')
                    self.current_step +=1
                # if state for this step is off
                else:
                    self.signals.c_off.emit('1')
                    self.current_step += 1
                self.step_timer.start()
            # if already last step
            # go back to step 1 and re-execute all steps again
            else:
                self.current_step = 0
                self.loop_counter += 1
                self.update_loop()
        else:
            pass

    def update_loop(self):
        # thread run
        if not self.stopped:
            # if is last cycle
            if self.loop_counter >= self.cycles:  # 2 loop make 1 full cycle
                self.signals.c_finish.emit('1')
            # if not last cycle
            # execute all steps
            else:
                self.signals.update_loop.emit(self.loop_counter)
                self.update_steps()
        # thread stopped
        else:
            pass


class QTextEditLogger(logging.Handler):
    def __init__(self,parent):
        super().__init__()
        self.signals = Signals()
        self.logger_widget = QPlainTextEdit(parent)
        self.logger_widget.setReadOnly(True)
        self.signals.log_msg.connect(self.logger_widget.appendPlainText)

    def emit(self,record):
        msg = self.format(record)
        self.signals.log_msg.emit(msg)


class LogBox(QGroupBox):
    def __init__(self,parent):
        super(LogBox, self).__init__(parent)

        logTextBox = QTextEditLogger(self)
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)
        logging.getLogger().setLevel(logging.DEBUG)

        layout = QVBoxLayout()
        # Add the new logging box widget to the layout
        layout.addWidget(logTextBox.logger_widget)
        self.setLayout(layout)

    def display_info(self, content):
        # print('display log')
        logging.info(content)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    app.setStyleSheet((open('stylesheet.qss').read()))
    window.show()
    sys.exit(app.exec_())