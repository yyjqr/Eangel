#!/usr/bin/python3
## -*- coding: UTF-8 -*-
import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

class DeploymentApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.selected_file = ""
        
    def initUI(self):
        self.setWindowTitle('设备部署工具')
        self.setGeometry(300, 300, 400, 200)
        
        # 创建主部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        
        # 文件选择部件
        self.file_label = QLabel("当前选中的部署包：无")
        self.btn_choose = QPushButton("选择部署包")
        self.btn_choose.clicked.connect(self.choose_package)
        
        # 解压操作部件
        self.btn_deploy = QPushButton("开始部署")
        self.btn_deploy.clicked.connect(self.start_deployment)
        
        # 状态显示
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # 添加部件到布局
        layout.addWidget(self.file_label)
        layout.addWidget(self.btn_choose)
        layout.addSpacing(20)
        layout.addWidget(self.btn_deploy)
        layout.addWidget(self.status_label)
        
        main_widget.setLayout(layout)
        
    def choose_package(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择部署包", "", "压缩文件 (*.zip *.tar *.gz *.tar.gz)"
        )
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(f"当前选中的部署包：{os.path.basename(file_path)}")
            self.status_label.setText("就绪")

    def start_deployment(self):
        if not self.selected_file:
            QMessageBox.warning(self, "警告", "请先选择部署包！")
            return
            
        if not os.path.exists(self.selected_file):
            QMessageBox.critical(self, "错误", "部署包不存在！")
            return

        try:
            self.status_label.setText("正在解压部署包...")
            QApplication.processEvents()  # 立即更新界面
            
            # 执行解压操作（需要sudo权限）
            shutil.unpack_archive(self.selected_file, "/var")
            
            self.status_label.setText("部署成功！")
            QMessageBox.information(self, "成功", "部署包已成功解压到/var目录！")
            
        except Exception as e:
            self.status_label.setText("部署失败")
            QMessageBox.critical(
                self, 
                "错误", 
                f"部署过程中发生错误：\n{str(e)}\n\n"
                "请检查：\n1. 程序是否具有足够的权限\n"
                "2. 部署包是否完整\n3. 目标目录是否可用"
            )
        finally:
            self.selected_file = ""
            self.file_label.setText("当前选中的部署包：无")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 权限检查
    if os.geteuid() != 0:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("此操作需要管理员权限！")
        msg.setInformativeText("请使用sudo命令运行本程序")
        msg.setWindowTitle("权限警告")
        msg.exec_()
        sys.exit(1)
    
    window = DeploymentApp()
    window.show()
    sys.exit(app.exec_())
