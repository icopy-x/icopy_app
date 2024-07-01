"""
    用于测试的activity
"""
import platform
import socket
import struct
import time

import audio
import images
import keymap
import resources
import settings
import widget

from actbase import BaseActivity
from iclassencrypt import FactoryTagRelease


class NetworkInfoActivity(BaseActivity):
    """
       网络信息输出
    """

    @staticmethod
    def getManifest():
        return {
            "index": -1,
            "infos": tuple(("Network info", images.load("network.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.lv = None
        self.pi = None

    def onCreate(self):
        self.setTitle(resources.get_str("network"))

        self.getCanvas().create_text(120, 60, text="All possible ip addr", font=resources.get_font(12), fill="#1C6AEB")

        self.lv = widget.ListView(self.getCanvas(), (0, 80))
        self.lv.setDisplayItemMax(4)
        self.pi = widget.PageIndicator(self.getCanvas(), self.tags_title)
        # 获取并且更新数据
        self.getInfo()
        self.lv.setOnPageChangeCall(self.pi.update)
        self.lv.setPageModeEnable(True)

    @staticmethod
    def get_ip_address(ifname):
        try:
            if platform.system() != "Windows":
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                import fcntl
                ip = socket.inet_ntoa(fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR
                    struct.pack('256s', bytes(ifname[:15], 'utf-8'))
                )[20:24])
                return ip
        except Exception as e:
            return e

    def getInfo(self):
        ip_list = []
        if platform.system() == "Windows":
            info = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            for item in info:
                ip = item[4][0]
                print(ip)
                if ip_list.count(ip) == 0:
                    ip_list.append(ip)
        else:
            ip_list.append(self.get_ip_address("eth0"))
        self.lv.setItems(ip_list)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            self.finish()
            return True
        if event == keymap.UP:
            self.lv.prev(True)
            return True
        if event == keymap.DOWN:
            self.lv.next(True)
            return True
        if event == keymap.LEFT:
            self.lv.prev(prevPage=True)
            return True
        if event == keymap.RIGHT:
            self.lv.next(nextPage=True)
            return True

        return False


class IClassFactoryActivity(BaseActivity):
    """
        负责iclass的发卡操作的
    """

    @staticmethod
    def getManifest():
        return {
            "index": -1,
            "infos": tuple(("Factory Tag", images.load("tag_release.png")))
        }

    ITEMS = [
        "Legacy2NikolaLegacy",
        "Legacy2NikolaElite",
        "Legacy2NikolaSE",

        "NikolaLegacy2Office",
        "NikolaElite2Office",
        "Office2NikolaElite"
    ]

    ACTS = [
        FactoryTagRelease.fromLegacy2NikolaLegacy,
        FactoryTagRelease.fromLegacy2NikolaElite,
        FactoryTagRelease.fromLegacy2NikolaSE,

        FactoryTagRelease.fromNikolaLegacy2Office,
        FactoryTagRelease.fromNikolaElite2Office,
        FactoryTagRelease.fromOffice2NikolaElite,
    ]

    TIPS = [
        "Make iClass legacy pwd to nikola private.(iClass Legacy)",
        "Make iClass legacy pwd to nikola private.(iClass Elite)",
        "Make iClass legacy pwd to nikola private.(iClass SE)",

        "Make iClass legacy pwd to default.",
        "Make iClass Elite pwd to default(from 700+ key file)",
        "Make iClass Elite pwd to nikola private(from 700+ key file)",
    ]

    def __init__(self, canvas):
        super().__init__(canvas)
        self.lv = widget.ListView(canvas, (0, 40), self.ITEMS)
        self.lv.setDisplayItemMax(4)
        self.tags_tips = self.unique_id("tips")
        self.tips = canvas.create_text(120, 120, tags=self.tags_tips, width=230, font=resources.get_font(14), fill="#1C6AEB")
        self.pos = -1
        self.toast = widget.Toast(canvas)
        self.success_count = 0

        self.ftr = FactoryTagRelease()
        self.ftr.setOnFactoryCall(self.onTaskStartCall, self.onTaskRetCall, self.onTaskEndCall)

    def onTaskStartCall(self):
        """
            在加密开始时的回调
        :return:
        """
        self.toast.show("Tag found, {}: start".format(self.ITEMS[self.pos]))
        time.sleep(1)

    def onTaskRetCall(self, ret):
        """
            在加密出结果时的回调
            TODO 请在此处针对结果进行语音播报
        :return:
        """
        if ret:
            ret = "Success"
            self.success_count += 1
        else:
            ret = "Failed"
        self.toast.show("Opera done, result: {}, please fast to remove tag.".format(ret))
        time.sleep(2)

    def show_start_and_success_count(self):
        """
            显示一个toast，提示当前已经开始任务，和显示成功的计数
        :return:
        """
        msg = "Task started, please place iclass tag.\nCurrent success count: {}".format(self.success_count)
        self.toast.show(msg)

    def onTaskEndCall(self):
        """
            在加密结束后的回调
        :return:
        """
        self.show_start_and_success_count()

    def onCreate(self):
        """
            创建基本的提示
        :return:
        """
        self.setTitle("Factory Tag")
        self.setLeftButton(resources.get_str("cancel"))
        self.setRightButton(resources.get_str("start"))

    def setTipsEnable(self, enable):
        if enable:
            self.getCanvas().itemconfig(self.tags_tips, state="normal")
        else:
            self.getCanvas().itemconfig(self.tags_tips, state="hidden")

    def task_run(self):
        """
            运行发卡任务
        :return:
        """
        self.show_start_and_success_count()
        self.ftr.startCreateTag(self.ACTS[self.pos])
        self.setidle()
        self.toast.show("Task stopped, please remove iclass tag.")

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if self.isbusy():
                self.ftr.stopCreateTag()
                return True
            else:
                if self.toast.isShow():  # 先取消吐司的显示
                    self.toast.cancel()
                    return True
                if not self.lv.isShowing():  # 然后显示列表出来
                    self.setTipsEnable(False)
                    self.lv.show()
                    return True
                self.finish()
            return True

        if event == keymap.OK:
            if self.lv.isShowing():  # 当前在前台可视，我们可以选择项目
                self.success_count = 0
                self.pos = self.lv.getSelection()
                self.getCanvas().itemconfig(self.tags_tips, text=self.TIPS[self.pos])
                self.setTipsEnable(True)
                self.lv.hide()  # 选择后我们需要隐藏掉
            return True

        if event == keymap.UP:
            self.lv.prev(True)
            return True

        if event == keymap.DOWN:
            self.lv.next(True)
            return True

        if event == keymap.M2:
            if self.isbusy() or self.pos == -1: return False
            self.setbusy()
            self.startBGTask(self.task_run)
            return True

        if event == keymap.M1:
            self.ftr.stopCreateTag()
            return True

        return False


class SleepActivity(BaseActivity):
    """
        休眠控制的活动，用于控制手持机长时间无操作时休眠
    """

    @staticmethod
    def getManifest():
        return {
            "index": -1,
            "infos": tuple(("Sleep", images.load("sleep.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.lv = None

    def onCreate(self):
        self.setTitle("Sleep")

        items = [
            "No Sleep",
            "15 second",
            "30 second",
            "1 minutes",
            "2 minutes",
            "5 minutes",
            "10 minutes",
        ]

        self.lv = widget.CheckedListView(self.getCanvas(), (0, 40), items=items)
        pos = settings.getSleepTime()
        self.lv.selection(pos)
        self.lv.check(pos)

    def saveSetting(self):
        pos = self.lv.getSelection()
        self.lv.check(pos)
        settings.setSleepTime(pos)
        v = settings.fromLevelGetSleepTime(pos)
        keymap.setNoKeyJudgeTime(v)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            audio.stop()
            self.finish()
            return True
        if event == keymap.OK:
            self.startBGTask(self.saveSetting)
            return True
        if event == keymap.DOWN:
            self.lv.next()
            return True
        if event == keymap.UP:
            self.lv.prev()
            return True

        return False
