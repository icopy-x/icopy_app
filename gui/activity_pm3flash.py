"""
    用于烧写PM3的activity
"""
import os
import subprocess

import images
import keymap
import resources
import widget
import executor

from actbase import BaseActivity


class PM3FlasherActivity(BaseActivity):
    """
       烧写PM3用的Activity
    """

    @staticmethod
    def getManifest():
        return {
            "index": -1,
            "infos": tuple(("PM3 烧录器", images.load("network.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)

        self.toast = widget.Toast(canvas)

        self.proxamrk3_exe = "/home/pi/ipk_app_main/pm3/proxmark3"
        self.image_file = "/mnt/upan/fullimage.elf"
        self.serial_port = "/dev/ttyACM0"
        self.tags_tips = "show_tips"

    def onCreate(self):
        self.setTitle("PM3 烧录器")
        self.getCanvas().create_text(
            120, 120,
            text="未启动烧录",
            font=resources.get_font(12),
            fill="#1C6AEB",
            tags=self.tags_tips
        )
        self.setLeftButton("取消")
        self.setRightButton("烧录")

    def showTips(self, txt):
        """
            显示文本
        :param txt:
        :return:
        """
        self.getCanvas().itemconfig(self.tags_tips, text=txt)

    def run_pm3_flash(self):
        """
            执行PM3的烧录过程！
        :return:
        """
        try:
            self.showTips("正在停止\n中控对PM3的占用......")

            # 先取消对PM3的使用
            executor.startPM3Ctrl("stop")

            self.showTips("正在启动\nPM3的烧录程序......")

            cmd = f"sudo {self.proxamrk3_exe} {self.serial_port} --flash --unlock-bootloader --image {self.image_file}"
            if os.path.exists(self.image_file):
                pi = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                while pi.poll() is None:
                    outline = str(pi.stdout.readline())
                    print(outline)

                    if "Waiting for Proxmark3" in outline:
                        self.showTips("等待PM3\n通信连接......")

                    if "Entering bootloader" in outline:
                        self.showTips("使PM3进去\nBOOT模式......")

                    if "Flashing..." in outline:
                        self.showTips("烧写中......")

                    if "All done" in outline:
                        self.showTips("烧写完成，\n正在使PM3进去APP模式......")

                    if "Have a nice day" in outline:
                        self.showTips("进入APP成功，\n没我事儿了，\n拜拜。")
            else:
                self.toast.show("没有看到固件包")
        except Exception as e:
            print(e)
        finally:
            # 启用PM3的任务进程
            executor.startPM3Ctrl("restart")
            # 无论如何都要释放任务
            self.setidle()

    def onKeyEvent(self, event):
        if self.isbusy():
            return False

        if event == keymap.POWER or event == keymap.M1:
            self.finish()
            return True

        if event == keymap.M2:
            self.setbusy()
            self.startBGTask(self.run_pm3_flash)
            return True

        return False
