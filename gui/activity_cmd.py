"""
    单纯用来调试的时候，通过USB的虚拟串口进行指令执行
"""
import os
import signal
import subprocess

import psutil

import audio
import gadget_linux
import hmi_driver
import images
import keymap
import resources
import widget
from actbase import BaseActivity


class CMDActivity(BaseActivity):
    """
        PC模式界面的活动
    """

    home_path = "/home/pi/"
    dev_path = "/dev"
    sim_port = "ttyGS0"
    sim_serial = f"{dev_path}/{sim_port}"

    @staticmethod
    def getManifest():
        return {
            "index": -1,
            "infos": tuple(("命令行转发", images.load("7.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.toast = None
        self.RUNNING = 0
        self.process_socat = None
        self.stop_pcmode = False

    def onCreate(self):
        # 创建吐司提示
        self.toast = widget.Toast(self.getCanvas())
        # 创建标题
        self.setTitle("命令行转发")
        # 创建提示文字
        self._canvas.create_text(120, 120,
                                 text="连接到电脑", font=resources.get_font(14), width=220)
        self.showButton(False)

    @staticmethod
    def print_warning_on_windows():
        """
            有一些警告消息一定要打印出来
        :return:
        """
        print("\n**************** 警告 ****************")
        print("主页面做了SN应答的子进程创建，")
        print("其占用了ttyGS0串口，如果你是在windows上进行")
        print("网络联合调试，请你务必将被调试手持机上的页面")
        print("切换到非主页面，以关闭应答进程，释放串口。")
        print("**************************************\n")

    @staticmethod
    def kill_child_processes(parent_pid, sig=signal.SIGTERM):
        try:
            p = psutil.Process(parent_pid)
            child_pid = p.children(recursive=True)
            for pid in child_pid:
                os.kill(pid.pid, sig)
            p.send_signal(sig)
        except psutil.NoSuchProcess:
            return

    def start_socat(self):
        """
            启动转发进程！
        :return:
        """
        # 先停止历史存在的socat
        self.stop_socat()
        self.stop_pcmode = False

        restart_count = 0

        dev1 = f"{self.sim_serial},raw,echo=0"
        dev2 = f"EXEC:/bin/bash,pty,stderr"
        cmd = f"sudo socat {dev1} {dev2}"

        try:
            while not self.stop_pcmode:  # 在一个大循环里面，进行socat进程维稳，解决断线的问题！
                self.process_socat = subprocess.Popen(cmd, shell=True, cwd=self.home_path)
                self.process_socat.wait()
                self.process_socat = None
                if not self.stop_pcmode:
                    restart_count += 1
                    print(f"检测到转发进程掉线，开始自动维稳，将自动重启转发进程，次数: {restart_count}")
        except Exception as e:
            print("启动socat进程的时候出现了问题: ", e)

    def stop_socat(self):
        """
            停止转发进程！
        :return:
        """
        if self.process_socat is not None:
            self.stop_pcmode = True
            try:
                self.kill_child_processes(self.process_socat.pid)
            except Exception as e:
                print("停止socat进程的时候出现异常: ", e)

    def startPCMode(self):
        """
            启动pcmode
        :return:
        """
        self.print_warning_on_windows()
        self.setbusy()
        self.toast.show("启动中")

        self.showButton(True)
        self.disableButton()

        print("重启虚拟串口模块")

        # 重新初始化串口和分区
        gadget_linux.kill_all_module(auto_remount=False)  # 先下线虚拟设备
        gadget_linux.umount_upan_partition()  # 再取消挂载U盘
        gadget_linux.upan_and_serial()  # 再加载U盘和串口双设备虚拟的模块

        print("虚拟串口模块重启完成")

        self.RUNNING = 1
        self.showRunningToast()

        self.setidle()
        self.disableButton(False, False)

        # 最终开启桥接
        self.start_socat()

    def stopPCMode(self):
        """
            关闭pcmode
        :return:
        """
        self.setbusy()
        self.toast.show("结束中")

        # 先关闭相关的转发进程，释放设备的句柄占用
        self.stop_socat()
        # 然后杀掉双设备模拟模块，并且自动进行磁盘同步！
        gadget_linux.kill_all_module()
        # 然后重新挂载单独的串口模拟设备，此步骤是为了恢复主页面的串口的应答实现
        gadget_linux.serial(False)

        self.RUNNING = 0
        self.toast.cancel()
        self.showButton(False)

        self.setidle()

    def onKeyEvent(self, event):
        if event == keymap.M1 or event == keymap.M2:
            if self.isbusy():
                return False
            if self.RUNNING == 0:  # 当前pc模式不在运行
                self.startBGTask(self.startPCMode)
                # print("操作：启动pc模式")
            else:  # 当前pc模式在运行
                if event == keymap.M2:  # 在运行的时候，M2功能键是Button键
                    def run_press():
                        self.disableButton(False, True)
                        hmi_driver.presspm3()
                        self.disableButton(False, False)

                    self.startBGTask(run_press)
                else:
                    self.startBGTask(self.stopPCMode)
                # print("操作：退出启动pc模式")
            return True
        elif event == keymap.POWER:
            if self.isbusy():
                return False
            if self.toast.isShow():  # 当前正显示
                self.toast.cancel()
            if self.RUNNING == 1:  # 当前pc模式在运行
                def run_finish():
                    self.stopPCMode()
                    self.finish()

                self.startBGTask(run_finish)
                return True
            self.finish()
            return True

        return False

    def showRunningToast(self):
        # 弹框
        self.toast.show("命令行转发中")
        audio.playPCModeRunning()

    def showButton(self, starting):
        if starting:
            # 显示按钮
            self.setLeftButton("停止")
            self.setRightButton("PM3按钮")
        else:
            self.setLeftButton("启动")
            self.setRightButton("启动")
