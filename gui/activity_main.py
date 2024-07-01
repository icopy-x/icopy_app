"""
    用户发布活动框架
"""

import numbers
import os
import platform
import re
import shutil
import signal
import subprocess
import time

import psutil
from Crypto.Cipher import AES
import base64

import audio_copy
import commons
import gadget_linux
import games
import hficlass
import hfmfkeys
import hfmfread
import hfmfwrite

import images
import keymap
import lft55xx
import version
import vsp_tools
import widget
import template
import audio
import hmi_driver
import settings
import resources

import read
import write
import scan
import executor
import tagtypes
import sniff
import appfiles
import container
import activity_update

from actbase import BaseActivity
from tkinter import *
from tkinter.font import Font


class AutoExceptCatchActivity(BaseActivity):
    """
        这个实现类仅仅是为了
        复用异常自动处理的逻辑
        而定义
    """

    def save_log(self, ex):
        """
            保存日志
        :return:
        """

        def run_save():
            try:
                # 因为我们使用了版本号来加密，所以判断版本号很重要
                # 然后我们还要判断其他的参数，避免让人家轻易破解
                if version.SERIAL_NUMBER is not None and version.TYP is not None:
                    # 进行加密保存
                    aes = AES.new(
                        # 这里我们需要使用SN + SN的翻转结果为秘钥
                        # 比如SN = 00080001
                        # 那么秘钥就是 0008000110008000
                        (version.SERIAL_NUMBER + version.SERIAL_NUMBER[::-1]).encode(),
                        AES.MODE_CFB,
                        # 加盐的话，我们要跟上面的秘钥类似，但是需要反过来
                        # 按照上面的例子，那就是1000800000080001
                        (version.SERIAL_NUMBER[::-1] + version.SERIAL_NUMBER).encode()
                    )

                    if ex is None:
                        exception = "No exception"
                    elif len(ex) == 0:
                        exception = "Exception empty"
                    else:
                        exception = ex

                    exception = base64.b64encode(aes.encrypt(exception.encode())).decode("utf-8")
                    # 再保存！
                    appfiles.log_to_file(exception)
                    # 延迟一段时间后退出
                    time.sleep(3.333)

            except Exception as e:
                # 为了安全性不需要处理这个异常
                pass

        # 在后台进行保存任务
        self.startBGTask(run_save)

    def onActExcept(self, exception):
        """
            在搜索的时候出现异常的话我们需要进行处理！
        :param exception:
        :return:
        """
        # 设置当前任务状态为空闲
        print("自动捕获异常操作: \n", exception)
        # 自动保存崩溃日志
        self.save_log(exception)
        # 然后结束这个act，回到上级页面
        self.finish()


class ScanActivity(AutoExceptCatchActivity):
    """
        寻卡活动
    """

    text_scan_tag, text_tag_multi, text_tag_found, text_no_tag_found, text_rescan, text_simulate, text_scanning = \
        resources.get_str(
            ["scan_tag", "tag_multi", "tag_found", "no_tag_found", "rescan", "simulate", "scanning"]
        )

    @staticmethod
    def getManifest():
        return {
            "index": 2,
            "infos": tuple((ScanActivity.text_scan_tag, images.load("2.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.scan_progressbar = None
        self.scan_toast = None
        self.scan_found = False
        self.sim_impl = None  # 模拟卡的数据解析的实现函数

        self.scanner = scan.Scanner()  # 卡片扫描器
        # 注册扫描器回调
        self.scanner.call_progress = self.onScanning
        self.scanner.call_resulted = self.onScanFinish
        self.scanner.call_exception = self.onActExcept

        # 扫描成功后的结果缓存
        self.scan_infos = None

    def onScanning(self, progress):
        """
            实现一个函数，用于接收scan的进度回调
            关于参数组成，请看Scanner的具体实现
        :param progress:
        :return:
        """
        progress_new = progress[0]
        progress_max = progress[1]

        self.scan_progressbar.setMax(progress_max)
        self.scan_progressbar.setProgress(progress_new)

    def onScanFinish(self, data):
        # 隐藏进度条
        self.scan_progressbar.hide()

        found = scan.isTagFound(data)
        multi = scan.isTagMulti(data)
        simulate = False

        if found and not multi:
            self.scan_found = found
            # 绘制数据UI
            typ = data["type"]
            template.draw(typ, data, self.getCanvas())
            # 判断是否可以模拟
            print("模拟需要的参数", data)
            if typ in SimulationActivity.getSimMap():
                try:
                    sim_parse_count = SimulationActivity.getSimMap()[typ][1]
                    sim_parse_func = SimulationActivity.getSimMap()[typ][0]
                    sim_data_list = sim_parse_func(data)
                    sim_data_count = len(sim_data_list)
                    if sim_data_count != sim_parse_count:
                        print(f"模拟卡参数 {sim_data_list} 异常个数: {sim_data_count}，不允许模拟")
                    else:
                        simulate = True
                except Exception as e:
                    # 解析模拟需要的参数的时候出现了异常！
                    print(e)

            if simulate:
                def getD():
                    return data

                self.sim_impl = getD
            else:
                self.sim_impl = None

        self.showScanToast(found, multi)
        self.showButton(found, simulate)
        # 设置当前任务状态为空闲
        self.setidle()

    def canidle(self, infos):
        """
            由于scan是联合其他的组件工作的，
            所以我们需要在scan结束后，
            1、恢复空闲状态
            2、保持工作状态，
            以达到scan任务和其他组合任务之间的无缝对接
        :return:
        """
        self.setidle()

    def showScanToast(self, found, multi):
        if found:
            if multi:
                rgb = ((102, 102, 102), (255, 255, 255))
                img = images.load("wrong.png", rgb)
                self.scan_toast.show(self.text_tag_multi, img[1])
                audio.playMultiCard()
            else:
                rgb = ((102, 102, 102), (255, 255, 255))
                img = images.load("right.png", rgb)
                self.scan_toast.show(self.text_tag_found, img[1])
                audio.playTagfound()
        else:
            rgb = ((102, 102, 102), (255, 255, 255))
            img = images.load("wrong.png", rgb)
            self.scan_toast.show(self.text_no_tag_found, img[1])
            audio.playTagNotfound()

    def showButton(self, found, cansim=False):
        if found:
            # 显示按钮
            self.setLeftButton(self.text_rescan)
            if cansim:
                self.setRightButton(self.text_simulate)
            else:
                self.setRightButton(self.text_simulate, "grey")
        else:
            self.setLeftButton(self.text_rescan)
            self.setRightButton(self.text_rescan)

    @staticmethod
    def playScanning():
        time.sleep(0.3)
        audio.playScanning()

    def startScan(self):
        """
            初始化视图并且开始搜索的实现
        :return:
        """
        self.startBGTask(self.playScanning)
        self.sim_impl = None
        self.setbusy()
        # 隐藏土司
        self.scan_toast.cancel()
        # 隐藏按键
        self.dismissButton()
        # 隐藏可能存在的数据视图
        template.dedraw(self.getCanvas())
        # 显示UI
        self.scan_progressbar.setProgress(0, autoShow=False)
        self.scan_progressbar.setMessage(self.text_scanning)
        self.scan_progressbar.show()
        # 调用搜索的封装函数
        self.how2Scan()

    def how2Scan(self):
        """
            具体如何开始scan的实现，开发者可以在此处替换搜索的实现
        :return:
        """
        self.scanner.scan_all_asynchronous()

    def onAutoScan(self):
        """
            ScanActivity会在创建完成后自动开始搜索，如果不需要，请
            Scan自动开始的封装，如果不需要，请覆盖此方法
        :return:
        """
        self.startScan()

    def onCreate(self):
        self.setTitle(self.text_scan_tag)
        # 创建一个进度条显示控件
        self.scan_progressbar = widget.ProgressBar(self.getCanvas(), (20, 210))
        self.scan_progressbar.hide()
        # 创建一个吐司
        self.scan_toast = widget.Toast(self.getCanvas())
        # 自动开始scan
        self.onAutoScan()

    def onKeyEvent(self, event):
        if event == keymap.M1:
            # 如果是忙碌的状态，就不处理按键事件
            if self.isbusy():
                return False
            # 重新搜索
            self.startScan()
            return True

        if event == keymap.M2:
            if self.isbusy():
                return False
            if self.scan_found:
                if self.sim_impl is not None:
                    self.start(SimulationActivity, self.sim_impl())
                else:
                    return False
            else:
                self.startScan()
            return True

        if event == keymap.POWER:
            if self.isbusy():
                return False
            if self.scan_toast.isShow():
                self.scan_toast.cancel()
                return True
            self.finish()
            return True

        return False


class ConsolePrinterActivity(BaseActivity):
    """
        打印终端执行的过程
    """

    def onActivity(self):
        #  self.getCanvas().create_polygon([(0, 0), (0, 240), (240 ,240), (240, 0)], fill="black")
        pass

    def __init__(self, canvas: Canvas, show=True):
        super().__init__(canvas)

        self.tags_pb = "hhhhhhh"
        self.tags_win = "aaaaasdasd"
        state = NORMAL if show else HIDDEN

        self.frame = Frame(self.getCanvas(), width=240, height=240, bg='black', bd=0)
        # 绘制到画布中
        self.getCanvas().create_window((0, 0),
                                       window=self.frame,
                                       anchor='nw',
                                       tags=self.tags_win,
                                       state=state,
                                       )

        self.progresscanvas = Canvas(self.frame,
                                     bd=0,
                                     highlightthickness=0,
                                     bg="#222222",
                                     height=240,
                                     width=10,
                                     )

        self.progresscanvas.create_rectangle(0, 0, 10, 240,
                                             fill="#444444",
                                             outline="",
                                             width=0,
                                             tags=self.tags_pb)

        self.textfont = Font(family='mononoki', size=10)
        self.oneword_w = self.textfont.measure("0")  # 一个字符宽度
        self.oneword_h = self.textfont.metrics("linespace")  # 一个字符高度
        self.NOR = int(int(240 / self.oneword_h) + 0.0)  # 每页行数
        self.NOC = int(int(230 / self.oneword_w) + 0.0)  # 每页列数

        print("字体信息：字符宽度：", self.oneword_w,
              ",字符高度：", self.oneword_h,
              ",每页行数：", self.NOR,
              ",每页列数：", self.NOC)

        self.text = Text(master=self.frame,
                         bg='black',
                         fg='white',
                         height=self.NOR,
                         width=self.NOC,
                         bd=0,
                         highlightthickness=0,
                         highlightbackground="black",
                         highlightcolor="black",
                         insertwidth=0,
                         takefocus=False,
                         cursor='none',
                         padx=0,
                         pady=0,
                         font=self.textfont,
                         # 8--40
                         wrap='none',
                         )

        self.linecounter = 0

        self.text.place(x=0, y=240, anchor='sw')
        self.progresscanvas.place(x=230, y=0, anchor='nw')

    # --------------------------字体控制函数start------------------------
    def textfontsizeup(self):
        tempsize = self.updatefontinfo(get=1)
        tempsize += 1
        if tempsize > 15:
            tempsize = 15
        self.updatefontinfo(tempsize)
        self.updatetextfont()

    def textfontsizedown(self):
        tempsize = self.updatefontinfo(get=1)
        tempsize -= 1
        if tempsize < 2:
            tempsize = 2
        self.updatefontinfo(tempsize)
        self.updatetextfont()

    def updatefontinfo(self, fontsize=8, get=0):
        if get == 1:
            return self.textfont["size"]
        else:
            self.textfont = Font(family='Consolas', size=fontsize)
            self.oneword_w = self.textfont.measure("0")  # 一个字符宽度
            self.oneword_h = self.textfont.metrics("linespace")  # 一个字符高度
            self.NOR = int(int(240 / self.oneword_h) + 0.0)  # 每页行数
            self.NOC = int(int(230 / self.oneword_w) + 0.0)  # 每页列数
            print("字体信息：字符宽度：", self.oneword_w,
                  ",字符高度：", self.oneword_h,
                  ",每页行数：", self.NOR,
                  ",每页列数：", self.NOC)

    def updatetextfont(self):
        self.text.configure(font=self.textfont,
                            height=self.NOR,
                            width=self.NOC,
                            )
        self.text.update()

    # --------------------------字体控制函数end--------------------------

    def update_progress(self):
        if self.linecounter == 0:
            w = self.progresscanvas.find_withtag(self.tags_pb)
            self.progresscanvas.coords(w, 0, 0, 10, 240)
            return

        thistextline = int(self.text.index("@0,240").split(".")[0])  # 下边缘行
        allline = self.linecounter  # 所有行
        lasttextline = thistextline - self.NOR  # 上边缘行
        y1 = int(lasttextline / allline * 240)
        y2 = int(thistextline / allline * 240)
        if y2 - y1 <= 1:
            y2 = y1 + 4
        w = self.progresscanvas.find_withtag(self.tags_pb)
        self.progresscanvas.coords(w, 0, y1, 10, y2)

    def add_text(self, textin):
        tempstr = self.text.get(1.0, END)  # 获取所有内容
        self.linecounter = tempstr.count("\n")  # 获取行数，记录

        self.text.configure(state=NORMAL)  # 需要先解锁才可以操作
        self.text.insert(END, textin)  # 在尾部添加收到的文本
        self.text.configure(state=DISABLED)  # 解锁后再次锁定，防止无意修改
        self.text.update()  # 更新文本区域
        # print(int(self.text.index("@0,240").split(".")[0]), " ", self.linecounter - 1)
        if int(self.text.index("@0,240").split(".")[0]) == self.linecounter - 1:  # 显示区域下沿是最后一行
            self.text.see(str(self.linecounter) + ".0")  # 自动追最后一行(注意不能用end，不然最后换行后多个空行）
        self.update_progress()

    def on_exec_print(self, line: str):
        if self.destroyed:
            print("当前的UI已经销毁，不支持后续更新！！！")
            return
        try:
            lines = line.split("\n")
            for line in lines:
                self.add_text(line + "\n")
        except Exception as e:
            print("控制台打印异常: ", e)

    def onDestroy(self):
        super().onDestroy()
        self.frame.destroy()

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            self.finish()
            return True
        if event == keymap.M2:
            self.textfontsizeup()
            return
        if event == keymap.M1:
            self.textfontsizedown()
            return
        if event == keymap.LEFT:
            self.text.xview("scroll", -1, "units")
            self.update_progress()
            return
        if event == keymap.RIGHT:
            self.text.xview("scroll", 1, "units")
            self.update_progress()
            return
        if event == keymap.UP:
            self.text.yview("scroll", -1, "units")
            self.update_progress()
            return
        if event == keymap.DOWN:
            self.text.yview("scroll", 1, "units")
            self.update_progress()
            return
        return False

    def hidden(self):
        self.getCanvas().itemconfig(self.tags_win, state=HIDDEN)

    def show(self):
        self.getCanvas().itemconfig(self.tags_win, state=NORMAL)

    def is_showing(self):
        return self.getCanvas().itemcget(self.tags_win, "state") == NORMAL

    def clear(self):
        """
            用于清空当前的历史输出
        :return:
        """
        self.text.configure(state=NORMAL)  # 需要先解锁才可以操作
        self.text.delete("1.0", END)
        self.text.configure(state=DISABLED)  # 解锁后再次锁定，防止无意修改
        self.text.update()  # 更新文本区域
        self.linecounter = 0
        self.update_progress()


class ReadActivity(ScanActivity):
    """
        读取卡片数据过程的页面
    """

    # 强制重读
    FORCE_Reread = "ReadActivity.FORCE_Reread"
    # 强制读卡的标志
    FORCE_READ_M1 = "ReadActivity.FORCE_READ_M1"
    FORCE_READ_T55XX = "ReadActivity.FORCE_READ_T55XX"
    FORCE_READ_EM4305 = "ReadActivity.FORCE_READ_EM4305"

    text_reading, text_reading_with_keys, text_t55xx_checking, text_t55xx_reading, text_reread, text_write = \
        resources.get_str([
            "reading", "reading_with_keys", "t55xx_checking", "t55xx_reading", "reread", "write",
        ])

    text_read_ok_2, text_read_ok_1, text_read_failed, text_read_tag, time_progress1, time_progress2, time_progress3 = \
        resources.get_str(
            ["read_ok_2", "read_ok_1", "read_failed", "read_tag", "time>=10h", "10h>time>=1h", "time<1h"])

    @staticmethod
    def getManifest():
        """
            ReadActivity应当是一个base类，不提供任何相关的入口信息
        :return:
        """
        return None

    def __init__(self, canvas):
        super().__init__(canvas)
        self.writeable = False
        self.read_success = False
        self.read_result_toast = None
        self.read_progressbar = None
        self.read_result_bundle = None

        # 实例化一个读卡器实例！
        self.reader = read.Reader()
        self.reader.call_reading = self.onReading
        self.reader.call_exception = self.onActExcept

        # 内置一个ACT，默认不显示，也就是后台活动
        self.console_activity = ConsolePrinterActivity(canvas, False)

        self.action_str_maps = {}

    def startRead(self, infos=None, force=False):
        """
            封装一些开始读取的资源初始化的过程
            以及实际开始读取卡片的实现的调用
        :return:
        """
        self.writeable = False  # 解决重新读卡未完成也能写卡的问题
        # 调用实现的读取函数
        self.setbusy()
        # 隐藏按钮
        self.dismissButton()
        self.read_result_toast.cancel()
        self.read_progressbar.show()
        self.read_progressbar.setProgress(0)
        self.read_progressbar.setMessage(self.text_reading)
        audio.playReadingKeys()
        self.console_activity.clear()  # 清空控制台面板

        # 开始读卡！
        if infos is None:
            infos = scan.getScanCache()
            if infos is None:
                print("逻辑异常，没有传入infos参数也没有在read之前调用scan，程序会自动退出。")
                self.finish()
                return

        self.reader.start(
            infos["type"],  # 需要被读取的卡片的类型！
            {
                "infos": infos,  # 卡片的基本信息
                "force": force,  # 是否允许强制读卡
            }
        )

    def onResume(self):
        super().onResume()
        executor.add_task_call(self.console_activity.on_exec_print)

    def onDestroy(self):
        super().onDestroy()
        executor.del_task_call(self.console_activity.on_exec_print)
        self.console_activity.onDestroy()

    def canidle(self, infos):
        """
            重写scan的函数，在发现卡片时不允许恢复空闲
            因为卡片搜索到的话会自动开始读取
        :param infos:
        :return:
        """
        if infos["found"]:
            return
        super().canidle(infos)

    def stopRead(self):
        """
            停止读取
        :return:
        """
        self.reader.stop()

    def seconds_to_time(self, seconds):
        if seconds <= 0:
            return ""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h >= 10:  # 满10小时
            return self.time_progress1 % (h, m, s)
        elif 10 > h >= 1:  # 不满十小时但是满一小时
            return self.time_progress2 % (h, m, s)
        elif h < 1:  # 不满一小时
            return self.time_progress3 % (m, s)
        return "%02d:%02d:%02d" % (h, m, s)

    def onReading(self, progress):
        print("ReadActivity.onReading():", progress)

        if "new_info" in progress:  # 出现 new_info 则需要更新显示的搜索到的卡片的信息
            info = progress["new_info"]
            template.dedraw(self.getCanvas())
            template.draw(info["type"], info, self.getCanvas())

        if "max" in progress:  # 带有进度，可以直接更新读取进度
            self.read_progressbar.setMax(progress["max"])

        if "progress" in progress:  # 带有进度，可以直接更新读取进度
            self.read_progressbar.setProgress(progress["progress"])

        if hfmfkeys.is_keys_check_call(progress):
            key_found = progress["keyIndex"]
            key_max = progress["keyCountMax"]
            seconds = progress["seconds"]
            action = progress["action"]
            if action is hfmfkeys.RECOVERY_ALL:
                text = self.text_reading_with_keys.format(key_found, key_max)
            else:
                # 此处我们采用缓存机制，解决多次调用动态解密卡顿的问题！
                if action not in self.action_str_maps:
                    action_form_res = resources.get_str(action)
                    self.action_str_maps[action] = action_form_res
                else:
                    action_form_res = self.action_str_maps[action]
                action = action if action_form_res is None else action_form_res
                text = f"{self.seconds_to_time(seconds)}\n{action}...{key_found}/{key_max}keys"
            self.read_progressbar.setMessage(text)

        if "state" in progress:
            if progress["state"] == "checkkeys":
                self.read_progressbar.setMessage(self.text_t55xx_checking)
            else:
                self.read_progressbar.setMessage(self.text_t55xx_reading)

        # 带有结果，根据结果显示UI
        if "success" in progress:
            read_success = progress["success"]
            print("读取完成，是否成功: ", read_success)

            # 进度条隐藏
            self.read_progressbar.hide(True)
            # 更新读取的结果
            infos = progress["tag_info"]
            self.read_success = read_success
            # 必须要支持读，并且读取成功了，才能写。
            can_write = tagtypes.isTagCanWrite(infos["type"])
            self.writeable = can_write and read_success

            if read_success:
                force = progress["force"]

                if "bundle" in progress:
                    self.read_result_bundle = progress["bundle"]
                    # 秘钥传递
                    if "key" in infos:
                        self.read_result_bundle["key"] = infos["key"]

                # 如果读取成功，则根据根据可写标志进行UI绘制
                self.showReadToast(read_success, force)
                self.setLeftButton(self.text_reread)
                if self.writeable:
                    self.setRightButton(self.text_write)
                else:
                    self.setRightButton(self.text_write, "grey")
            else:
                self.setLeftButton(self.text_reread)
                self.setRightButton(self.text_write, "grey")
                # 进入警告页面
                return_value = progress["return"]
                if return_value == -3 or return_value == -4:
                    self.start(WarningM1Activity, return_value)
                elif return_value == -7:
                    self.start(WarningT5XActivity, return_value)
                elif return_value == -8:
                    self.start(WarningT5X4X05KeyEnterActivity, return_value)
                else:
                    self.showReadToast(read_success)

            scan.set_scan_t55xx_key(None)
            scan.set_scan_em4x05_key(None)
            self.setidle()

        print("ReadActivity.onReading() -> 处理完成！")

    def showReadToast(self, success, is_force=False):
        if success:
            rgb = ((102, 102, 102), (255, 255, 255))
            img = images.load("right.png", rgb)
            if is_force:
                msg = self.text_read_ok_2
                audio.playReadPart()
            else:
                msg = self.text_read_ok_1
                audio.playReadAll()
            self.read_result_toast.show(msg, img[1])
        else:
            rgb = ((102, 102, 102), (255, 255, 255))
            img = images.load("wrong.png", rgb)
            self.read_result_toast.show(self.text_read_failed, img[1])
            audio.playReadFail()

    def hideReadToast(self):
        if self.read_result_toast is not None:
            self.read_result_toast.cancel()

    def onData(self, bundle):
        """
            读取页面必须通过其他页面进行数据联动，
            也就是说，读取页面本身不能独立工作，必须要有scan的搜索基础
            或者读取页面本身被继承重写
        :param bundle: 被处理的数据，搜索结果，支持伪装
        :return:
        """
        if isinstance(bundle, dict):
            if self.FORCE_READ_T55XX in bundle:
                print("选择了强制读取T55XX")
                scan.set_scan_t55xx_key(bundle["key"])
                self.startScan()
                return
            elif self.FORCE_READ_EM4305 in bundle:
                print("选择了强制读取EM4305")
                scan.set_scan_em4x05_key(bundle["key"])
                self.startScan()
                return
            else:
                self.startRead(bundle)
                return
        if bundle == self.FORCE_READ_M1:
            print("选择了强制读取M1卡")
            self.startRead(force=True)
            return
        if bundle == self.FORCE_Reread:
            print("申请重新寻卡和读卡")
            self.startScan()
            return

    def onCreate(self):
        # 设置标题
        self.setTitle(self.text_read_tag)
        """
            读取页面整体过程需要用到一些资源
            1、进度条（读取时）
            2、按钮（读取完成后）
        :return:
        """
        # 初始化父类的资源
        super().onCreate()
        self.read_result_toast = widget.Toast(self.getCanvas())
        self.read_progressbar = widget.ProgressBar(self.getCanvas(), (20, 218))
        self.read_progressbar.hide()

    def onKeyEvent(self, event):
        if self.console_activity.is_showing():
            if event == keymap.POWER:
                self.console_activity.hidden()
                return True
            return self.console_activity.onKeyEvent(event)
        if event is keymap.POWER:
            if self.isbusy():
                # 无条件结束读取
                self.stopRead()
                return True
            else:
                if self.read_result_toast.isShow():
                    self.read_result_toast.cancel()
                    return True
                # 没有任务，直接结束自己
                self.finish()
                return True
        if event is keymap.M1:
            if self.isbusy():
                return False
            # 无条件重新开始读取
            self.startRead()
            return True
        if event is keymap.M2 or event is keymap.ALL:
            if self.writeable:
                # 可以写，调用写入函数或者前往写入act
                self.read_result_toast.cancel()
                self.start(WarningWriteActivity, self.read_result_bundle)
                return  # True 不要处理此按钮事件，否则会导致声音被覆盖
            else:
                # 不可写，不响应该事件
                print("该卡片不可写")
                return False
        if event is keymap.RIGHT:
            self.console_activity.show()
            return True

        return False


class WarningM1Activity(BaseActivity):
    """
        M1卡的秘钥缺失的警告页面
    """

    text_sniff, text_enter, text_force, text_pcm, text_warn, text_missing_keys, text_missing_keys_msg1 = \
        resources.get_str(
            ["sniff", "enter", "force", "pc-m", "warning", "missing_keys", "missing_keys_msg1", ]
        )

    text_no_valid_key, text_missing_keys_msg3, text_missing_keys_msg2 = resources.get_str(
        ["no_valid_key", "missing_keys_msg3", "missing_keys_msg2"]
    )

    def __init__(self, canvas):
        super().__init__(canvas)
        self._warningList = None
        self._warningPI = None
        self._m1_key_method = None
        self._m2_key_method = None
        self.ret_value = -1

    def onWarningPageUpdate(self, page_max, page_new):
        self._warningPI.update(page_max, page_new)
        self.updateBtnText()

    def updateBtnText(self):
        if self.ret_value == -3:
            if self._warningList.getPagePosition() == 0:
                self.setLeftButton(self.text_sniff)
                self.setRightButton(self.text_enter)
                self._m1_key_method = self.gotoSniff
                self._m2_key_method = self.gotoEnter
            else:
                self.setLeftButton(self.text_force)
                self.setRightButton(self.text_pcm)
                self._m1_key_method = self.gotoForce
                self._m2_key_method = self.gotoPCMode
        elif self.ret_value == -4:
            if self._warningList.getPagePosition() == 0:
                self.setLeftButton(self.text_sniff)
                self.setRightButton(self.text_enter)
                self._m1_key_method = self.gotoSniff
                self._m2_key_method = self.gotoEnter
        else:
            raise Exception("开发者请检查传递给当前的返回值参数，不支持该参数: ", self.ret_value)

    def gotoSniff(self):
        """
            在单击了警告页面的m1时需要作出的动作
            此处我们需要处理sniff的跳转逻辑
        :return:
        """
        self.finish()
        self.start(SniffForMfReadActivity, {"selection": 0, "auto": True})

    def gotoEnter(self):
        """
            在单击了警告页面的m1时需要作出的动作
            此处我们需要进行秘钥输入
        :return:
        """
        self.finish()
        self.start(KeyEnterM1Activity)

    def gotoForce(self):
        """
            在单击了警告页面的m2时需要作出的动作
        :return:
        """
        # 直接结束自己，给read回传强制读取的参数
        self.finish(ReadActivity.FORCE_READ_M1)

    def gotoPCMode(self):
        """
            在单击了警告页面的m2时需要作出的动作
        :return:
        """
        # 先结束自己，和上层的ReadActivity
        self.finish()
        # 再启动PC-MODE页面
        self.start(PCModeActivity)

    def onCreate(self):
        self.setTitle(self.text_warn, (100, 20))

    def init_ui(self, ret_value):
        self.ret_value = ret_value
        # 绘制缺失秘钥的大标题文本
        if ret_value == -3:
            tips_msg = self.text_missing_keys
            items_act = [
                self.text_missing_keys_msg1,
                self.text_missing_keys_msg2,
            ]
            audio.playMissingKey()
        elif ret_value == -4:
            tips_msg = self.text_no_valid_key
            items_act = [self.text_missing_keys_msg3]
            audio.playNoValidKeyHF()
        else:
            raise Exception("开发者请检查传递给当前的返回值参数，不支持该参数: ", self.ret_value)

        self._canvas.create_text((120, 60), text=tips_msg, font=resources.get_font(16), fill="#1C6AEB")

        self._warningList = widget.BigTextListView(self.getCanvas(), (0, 53), items_act)

        # 创建一个标题列表指示器并且绑定到listview上
        self._warningPI = widget.PageIndicator(self.getCanvas(), self.tags_title)
        self._warningPI.setBottomIndicatorEnable(True)
        self._warningPI.setLoop(True)
        self._warningList.setOnPageChangeCall(self.onWarningPageUpdate)

        # 初始化更新按钮
        self.updateBtnText()

    def onData(self, bundle):
        # 我们需要根据返回值处理不同的情况
        self.init_ui(bundle)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            self.finish(False)
            return True
        if event == keymap.UP:
            if self.ret_value == -4:
                return False
            self._warningList.prev(True)
            return True
        if event == keymap.DOWN:
            if self.ret_value == -4:
                return False
            self._warningList.next(True)
            return True
        if event == keymap.M1:
            self._m1_key_method()
            return True
        if event == keymap.M2:
            self._m2_key_method()
            return True

        return False


class KeyEnterM1Activity(BaseActivity):
    """
        秘钥输入的活动
    """

    text_key_enter, text_read, text_enter_known_keys, text_key_item, text_processing = resources.get_str([
        "key_enter", "read", "enter_known_keys", "key_item", "processing"
    ])

    def __init__(self, canvas):
        super().__init__(canvas)
        self.iml = widget.InputMethodList(self.getCanvas(), xy=(0, 40))
        self.pi = widget.PageIndicator(self.getCanvas(), self.tags_title)
        self.toast = widget.Toast(self.getCanvas())

    def onCreate(self):
        self.setTitle(self.text_key_enter, xy=(100, 20))
        self.setLeftButton(self.text_read)
        self.setRightButton(self.text_read)

        self.iml.addItem(self.text_enter_known_keys, state="normal")
        self.iml.add_method(self.create_key_index())
        self.iml.setOnPageChangeCall(self.pi.update)

    def create_key_index(self):
        return self.text_key_item.format(self.iml.get_input_method_count() + 1)

    def run_save_keys_and_finish(self):
        """
            进行秘钥保存和结束活动
        :return:
        """
        self.toast.show(self.text_processing)
        self.disableButton()
        keys = list(set(self.iml.get_all_input_text()))
        if len(keys) > 0:
            # 随便写入一个
            hfmfkeys.genKeyFile(hfmfkeys.KEY_FILE_USER_NAME, keys)
        # 保存输入的秘钥完成后，返回去写卡
        self.finish(ReadActivity.FORCE_Reread)
        self.toast.cancel()
        self.disableButton(False, False)
        self.setidle()

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if self.iml.has_focus():
                self.iml.focus_exit()
                print("焦点取消成功")
                return True
            self.finish()
            return True

        if event == keymap.M1 or event == keymap.M2:
            if self.isbusy():
                return False
            self.setbusy()
            self.startBGTask(self.run_save_keys_and_finish)
            return True

        if event == keymap.OK:
            if self.isbusy():
                return False

            if self.iml.add_method_if_new(self.create_key_index()):
                return True

            if self.iml.has_focus():
                self.iml.focus_exit()
                print("焦点取消成功")
            else:
                self.iml.update_focus()
            return True

        if event == keymap.UP:
            if self.isbusy():
                return False
            self.iml.prev(True)
            return True

        if event == keymap.DOWN:
            if self.isbusy():
                return False
            self.iml.next(True)
            return True

        if event == keymap.LEFT:
            if self.isbusy():
                return False
            self.iml.left()
            return True

        if event == keymap.RIGHT:
            if self.isbusy():
                return False
            self.iml.right()
            return True

        return False


class WarningT5XActivity(BaseActivity):
    """
        实现一个类，这个类用于在遇到没有秘钥的T55XXX的时候，
        可以选择最终的操作:
            1、输入秘钥
            2、嗅探卡片
    """

    text_warn, text_no_valid_key, text_missing_keys_msg3, text_sniff, text_enter = resources.get_str(
        ["warning", "no_valid_key_t55xx", "missing_keys_t57", "sniff", "enter", ]
    )

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)
        self._data = None

    def onCreate(self):
        self.setTitle(self.text_warn)

        # 初始化需要的消息
        tips_msg = self.text_no_valid_key
        items_act = [self.text_missing_keys_msg3]

        self._canvas.create_text((120, 60), text=tips_msg, font=resources.get_font(16), fill="#1C6AEB")
        widget.BigTextListView(self.getCanvas(), (0, 53), items_act)

        # 初始化按钮
        self.setLeftButton(self.text_sniff)
        self.setRightButton(self.text_enter)

    def onData(self, bundle):
        self._data = bundle

    def onKeyEvent(self, event):
        if event == keymap.M1:
            # 前往T5X嗅探
            self.finish()
            self.start(SniffForT5XReadActivity, {"selection": 4, "auto": True})
            return True
        elif event == keymap.M2:
            # 前往输入秘钥
            self.finish()
            self.start(WarningT5X4X05KeyEnterActivity, self._data)
            return True
        elif event == keymap.POWER:
            self.finish()
            return True
        return False


class WarningT5X4X05KeyEnterActivity(BaseActivity):
    text_warning, text_no_valid_key_t55xx, text_enter_known_keys_55xx, text_enter_55xx_key_tips, text_read = \
        resources.get_str([
            "warning", "no_valid_key_t55xx", "enter_known_keys_55xx", "enter_55xx_key_tips", "read"
        ])

    def __init__(self, canvas):
        super().__init__(canvas)
        self.is_em4x05 = False
        self.input = widget.InputMethods(self.getCanvas(), (90, 155), 30, defdata="FFFFFFFF", bakcolor="#EEEEEE")

    def onCreate(self):
        self.setTitle(self.text_warning)
        # 绘制缺失秘钥的大标题文本
        self._canvas.create_text((120, 60), text=self.text_no_valid_key_t55xx, font=resources.get_font(20),
                                 fill="#1C6AEB")
        # 绘制提示
        self._canvas.create_text((120, 120), text=self.text_enter_known_keys_55xx,
                                 font=resources.get_font(12),
                                 fill="#1C6AEB")
        # 绘制输入框提示文本
        self._canvas.create_text((60, 170), text=self.text_enter_55xx_key_tips, font=resources.get_font(14),
                                 fill="#1C6AEB")
        # 绘制输入框
        self.input.setfocus()
        # 绘制按钮
        self.setLeftButton(self.text_read)
        self.setRightButton(self.text_read)
        # 播放提示音
        audio.playNoValidKeyLF()

    def onData(self, bundle):
        if bundle == -8:
            self.is_em4x05 = True
        else:
            self.is_em4x05 = False

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if self.input.isfocuing():
                self.input.unsetfocus()
                return True
            self.finish()
            return True

        if event == keymap.OK:
            self.input.rollfocus()
            return True

        if event == keymap.M1 or event == keymap.M2:
            if self.is_em4x05:
                ctrl_label = ReadActivity.FORCE_READ_EM4305
            else:
                ctrl_label = ReadActivity.FORCE_READ_T55XX
            bundle = {
                ctrl_label: True,
                "key": self.input.getdata()
            }
            self.finish(bundle)
            return True

        if event == keymap.UP:
            if self.input.isfocuing():
                self.input.upword()
            return True

        if event == keymap.DOWN:
            if self.input.isfocuing():
                self.input.downword()
            return True

        if event == keymap.LEFT:
            if self.input.isfocuing():
                self.input.lastitem()
            return True

        if event == keymap.RIGHT:
            if self.input.isfocuing():
                self.input.nextitem()
            return True

        return False


class WarningWriteActivity(BaseActivity):
    text_data_ready, text_place_empty_tag, text_type_tips, text_cancel, text_write, text_write_wearable = \
        resources.get_str(["data_ready", "place_empty_tag", "type_tips", "cancel", "write", "write_wearable"])

    def __init__(self, canvas):
        super().__init__(canvas)

        self._read_result_bundle = None
        self.use_read_data_draw = False
        self.is_m1_tag_type = False

        self.tag_info = scan.getScanCache()

    def draw_and_play(self, infos):
        """
            绘制信息并且播放音频
        :return:
        """
        # 绘制按钮
        # 注意，我们这里需要单独区分M1卡和其他卡的M1键功能
        # 因为M1卡可以直接去使用写手环功能
        # 因此M1键要更改为 写手环
        if self.is_m1_tag_type:
            self.setLeftButton(self.text_write_wearable)
        else:
            self.setLeftButton(self.text_cancel)

        self._canvas.create_text((120, 180), text=container.get_public_id(infos),
                                 font=resources.get_font_force_en(30), fill="#1C6AEB")

        # 播放音频，提示用户写卡需要做的操作
        audio_copy.playReadyForCopy(infos=infos)

    def onCreate(self):
        self.setTitle(self.text_data_ready)
        # 绘制提示
        self._canvas.create_text((120, 88), text=self.text_place_empty_tag, font=resources.get_font(14),
                                 fill="#1C6AEB", width=200)

        self._canvas.create_text((120, 150), text=self.text_type_tips, font=resources.get_font(14),
                                 fill="#1C6AEB")

        # 类型提示文本
        if self.tag_info is not None:
            self.use_read_data_draw = False
            self.is_m1_tag_type = self.tag_info["type"] in tagtypes.getM1Types()
            self.draw_and_play(self.tag_info)
        else:
            print("警告，信息缓存为空，将自动使用传过来的读卡数据尝试绘制！")
            self.use_read_data_draw = True

        self.setRightButton(self.text_write)

    def finish(self, bundle=None):
        super().finish(bundle)
        audio.stop()

    def onData(self, bundle):
        self._read_result_bundle = bundle
        print("写卡准备数据是: " + str(bundle))

        # 判断是否需要使用此数据绘制页面，如果需要则使用
        # 否则使用缓存的寻卡信息来绘制页面
        if self.use_read_data_draw:
            self.tag_info = bundle
            self.is_m1_tag_type = self.tag_info["type"] in tagtypes.getM1Types()
            self.draw_and_play(bundle)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            self.finish()
            return True

        if event == keymap.M1:
            self.finish()
            if self.is_m1_tag_type:  # 跳转到引导写手环的Activity
                self.start(WearableDeviceActivity, self._read_result_bundle)
            return True

        if event == keymap.M2 or event == keymap.ALL:
            self.finish()
            # 跳转到写卡时，需要传递读出来的数据
            if self._read_result_bundle is None:
                print("警告，遇到空的bundle，进入写卡Activity后会无法自动开始写卡。")
                # self._read_result_bundle = "I'm not None."
            self.start(WriteActivity, self._read_result_bundle)
            return True

        return False


class WriteActivity(AutoExceptCatchActivity):
    """
        写卡UI实现
    """

    text_verify, text_rewrite, text_verifying, text_writing, text_t55xx_checking, text_write_success = \
        resources.get_str([
            "verify", "rewrite", "verifying", "writing", "t55xx_checking", "write_success",
        ])

    text_verify_success, text_verify_failed, text_write_tag, text_write_failed = resources.get_str([
        "verify_success", "verify_failed", "write_tag", "write_failed"
    ])

    def __init__(self, canvas):
        super().__init__(canvas)
        self._write_progressbar = widget.ProgressBar(canvas, (20, 218))
        self._write_toast = widget.Toast(self.getCanvas())
        self.can_verify = False
        self._bundle = None

        # 获取信息缓存
        self.infos = scan.getScanCache()

    def setBtnEnable(self, v_enable, w_enable):
        """
            设置按钮的使能
        :return:
        """
        if v_enable:
            self.setLeftButton(self.text_verify)
        else:
            self.setLeftButton(self.text_verify, "grey")
        if w_enable:
            self.setRightButton(self.text_rewrite)
        else:
            self.setLeftButton(self.text_rewrite, "grey")
        if not v_enable and not w_enable:
            self.dismissButton()

    def on_write(self, progress):
        """
            在写卡时的回调
        :return:
        """
        print("WriteActivity->on_write()", progress)

        if "state" in progress:
            if progress["state"] == "verifying":
                self._write_progressbar.setMessage(self.text_verifying)
            if progress["state"] == "writing":
                self._write_progressbar.setMessage(self.text_writing)
            if progress["state"] == "checkkeys":
                self._write_progressbar.setMessage(self.text_t55xx_checking)

        if "success" in progress:
            self._write_progressbar.hide(True)
            success = progress["success"]
            if success:
                rgb = ((102, 102, 102), (255, 255, 255))
                img = images.load("right.png", rgb)
                self._write_toast.show(self.text_write_success, img[1])
                self.setBtnEnable(True, True)
                self.can_verify = True
                audio.playWriteSuccess()
            else:
                rgb = ((102, 102, 102), (255, 255, 255))
                img = images.load("wrong.png", rgb)
                self._write_toast.show(self.text_write_failed, img[1])
                self.setBtnEnable(False, True)
                self.can_verify = False
                audio.playWriteFail()

                # 可能需要提取出返回值，处理异常情况
                # ret_value = progress["return"]

            # 返回空闲状态
            self.setidle()

        if "max" in progress:
            self._write_progressbar.setMax(progress["max"])

        if "progress" in progress:
            self._write_progressbar.setProgress(progress["progress"])

    def on_verify(self, progress):
        """
            在校验的时候的回调
        :param progress:
        :return:
        """
        if "success" in progress:
            self._write_progressbar.hide(True)
            success = progress["success"]
            if success:
                self._write_toast.show(self.text_verify_success)
                audio.playVerifiSuccess()
            else:
                self._write_toast.show(self.text_verify_failed)
                audio.playVerifiFail()

            self.setBtnEnable(True, True)
            # 返回空闲状态
            self.setidle()

    @staticmethod
    def playWriting():
        time.sleep(0.3)
        audio.playWriting()

    @staticmethod
    def playVerifying():
        time.sleep(0.3)
        audio.playVerifying()

    def startWrite(self):
        """
            开始写入
        :return:
        """
        self.startBGTask(self.playWriting)
        # 设置为繁忙状态
        self.setbusy()
        self.dismissButton()
        self._write_toast.cancel()
        self._write_progressbar.setMessage(self.text_writing)
        self._write_progressbar.setProgress(0)
        write.write(self.on_write, self.infos, self._bundle)

    def startVerify(self):
        """
            开始校验写入结果
        :return:
        """
        self.startBGTask(self.playVerifying)
        self.setbusy()
        self.dismissButton()
        self._write_toast.cancel()
        self._write_progressbar.setMessage(self.text_verifying)
        self._write_progressbar.setProgress(0)
        write.verify(self.on_verify, self.infos, self._bundle)

    def onCreate(self):
        self.setTitle(self.text_write_tag)
        # 绘制搜索的记录
        infos = scan.getScanCache()
        template.draw(infos["type"], infos, self.getCanvas())

    def onData(self, bundle):
        self._bundle = bundle
        self.startWrite()

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if self.isbusy():
                return False
            if self._write_toast.isShow():
                self._write_toast.cancel()
                return True
            self.finish()
            return True

        if event == keymap.M1:
            if self.isbusy() or not self.can_verify:
                return False
            self.startVerify()
            return True

        if event == keymap.M2 or event == keymap.ALL:
            if self.isbusy():
                return False
            self.startWrite()
            return True

        return False


class AutoCopyActivity(ReadActivity):
    """
        自动复制卡片的页面，继承至Scan和Read页面
    """

    text_auto_copy, text_read = resources.get_str(
        ["auto_copy", "read"]
    )

    @staticmethod
    def getManifest():
        return {
            "index": 0,
            "infos": tuple((AutoCopyActivity.text_auto_copy, images.load("1.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.readable = False
        self.nextRead = False

    def onCreate(self):
        """
            需要调用父类的创造方法完成初始化
        :return:
        """
        super().onCreate()
        # 重新设置标题栏
        self.setTitle(self.text_auto_copy)

    def showScanToast(self, found, multi):
        # 重写显示提示框的函数，
        # 我们只需要在：
        #   未发现卡片的时候
        #   发现多重卡片的时候
        #       提醒用户。
        # 如果发现了卡片，就直接开始读卡
        if not found or multi:
            ScanActivity.showScanToast(self, found, multi)

    def onScanFinish(self, data):
        """
            搜索结束，可以根据当前的结果进行处理按键之类的事件和UI
        :param data:
        :return:
        """
        # 调用父类的函数初始化一些资源
        super().onScanFinish(data)
        # 然后初始化子类本身的资源
        # 如果发现卡片，则禁用按钮，开始读取
        if self.scan_found:
            self.dismissButton()
            self.readable = tagtypes.isTagCanRead(data["type"], infos=data)
            # 如果不能读取，则灰化按钮通知用户无法读取
            if not self.readable:
                self.setLeftButton(self.text_rescan, "white")
                self.setRightButton(self.text_read, "grey")
            else:
                # 否则直接开始读取
                self.nextRead = True
                self.startRead()
        else:
            self.showButton(False, False)
        return

    def startScan(self):
        self.readable = False
        self.nextRead = False
        self.hideReadToast()
        super().startScan()

    def onKeyEvent(self, event):
        # 如果没有发现，则复用寻卡的逻辑
        if not self.scan_found:
            if self.isbusy():
                return False
            if event == keymap.ALL:
                self.startScan()
                return True
            return ScanActivity.onKeyEvent(self, event)

        # 如果发现了，则根据当前卡片的可读取状态进行读取
        if not self.readable:
            if self.isbusy():
                return False
            if event == keymap.M1:
                # 无法读取，只响应重新搜索
                self.startScan()
                return True
            if event == keymap.POWER:
                self.finish()
                return True
            return False

        # 当前进入了读取的阶段，我们需要进行事件的处理
        if self.nextRead:
            if event == keymap.M1 and not self.console_activity.is_showing():
                if self.isbusy():
                    return False
                # 无条件重新开始读取，截取当前事件，更换为重新开始scan的逻辑
                self.startScan()
                return True
            else:  # 直接复用read的事件处理逻辑
                return ReadActivity.onKeyEvent(self, event)

        return False


class PCModeActivity(BaseActivity):
    """
        PC模式界面的活动
    """

    dev_path = "/dev"
    pm3_port = "ttyACM0"
    sim_port = "ttyGS0"
    pm3_serial = f"{dev_path}/{pm3_port}"
    sim_serial = f"{dev_path}/{sim_port}"

    text_pcm, text_connect_computer, text_processing, text_stop, text_pcmode_running, text_button, text_start = \
        resources.get_str([
            "pc-mode", "connect_computer", "processing", "stop", "pcmode_running", "button", "start"
        ])

    @staticmethod
    def getManifest():
        return {
            "index": 7,
            "infos": tuple((PCModeActivity.text_pcm, images.load("7.png")))
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
        self.setTitle(self.text_pcm)
        # 创建提示文字
        self._canvas.create_text(120, 120,
                                 text=self.text_connect_computer, font=resources.get_font(14), width=220)
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

    def wait_for_pm3_online(self):
        """
            等待串口上线
        :return:
        """
        while True:
            chk_cmd = f"ls /dev |grep {self.pm3_port}"
            chk_str = executor.startPM3Plat(chk_cmd).strip()

            if self.pm3_port == chk_str:
                time.sleep(2.33)
                break

            if chk_str is None:
                break

            time.sleep(0.01)

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
        dev2 = f"{self.pm3_serial},raw,echo=0"
        cmd = f"sudo socat {dev1} {dev2}"

        try:
            while not self.stop_pcmode:  # 在一个大循环里面，进行socat进程维稳，解决断线的问题！
                self.process_socat = subprocess.Popen(cmd, shell=True)
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
        self.toast.show(self.text_processing)

        self.showButton(True)
        self.disableButton()

        print("开始请求降低充电电流")
        version.current_limit(True)
        print("请求降低充电电流完成")

        print("重新初始化PM3")

        # 重新初始化PM3
        executor.startPM3Ctrl("stop")
        hmi_driver.restartpm3()
        self.wait_for_pm3_online()

        print("初始化PM3完成")

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
        self.toast.show(self.text_processing)

        print("开始请求提高充电电流")
        version.current_limit(False)
        print("请求提高充电电流完成")

        # 先关闭相关的转发进程，释放设备的句柄占用
        self.stop_socat()
        # 然后杀掉双设备模拟模块，并且自动进行磁盘同步！
        gadget_linux.kill_all_module()
        # 然后重新挂载单独的串口模拟设备，此步骤是为了恢复主页面的串口的应答实现
        gadget_linux.serial(False)
        # 然后重启PM3
        executor.reworkPM3All()

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
        elif event == keymap.ALL:
            if self.isbusy():
                return False
            if self.RUNNING == 1:  # 当前pc模式在运行
                def run_finish():
                    self.stopPCMode()
                    self.finish()
                    self.start(AutoCopyActivity)

                self.startBGTask(run_finish)
                return True
            self.finish()
            self.start(AutoCopyActivity)
            return True

        return False

    def showRunningToast(self):
        # 弹框
        self.toast.show(self.text_pcmode_running)
        audio.playPCModeRunning()

    def showButton(self, starting):
        if starting:
            # 显示按钮
            self.setLeftButton(self.text_stop)
            self.setRightButton(self.text_button)
        else:
            self.setLeftButton(self.text_start)
            self.setRightButton(self.text_start)


class AboutActivity(BaseActivity):
    """
        关于界面的活动
    """

    text_about, text_install_failed, text_al1, text_al2, text_al3, text_al4, text_al5, text_al6 = resources.get_str([
        "about", "install_failed", "aboutline1", "aboutline2", "aboutline3", "aboutline4", "aboutline5", "aboutline6",
    ])

    text_alu1, text_alu2, text_alu3, text_alu4, text_alu5, text_processing = resources.get_str([
        "aboutline1_update", "aboutline2_update", "aboutline3_update", "aboutline4_update", "aboutline5_update",
        "processing"
    ])

    @staticmethod
    def getManifest():
        return {
            "index": 11,
            "infos": tuple((AboutActivity.text_about, images.load("10.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.lv = None
        self.pi = None
        self.initializing = False
        self.toast = widget.Toast(canvas)

    def showErr(self, code):
        """
            显示错误信息
        :return:
        """
        msg = self.text_install_failed.format(code)
        self.toast.show(msg, mode=widget.Toast.MASK_FULL)

    def checkUpdate(self):
        """
            检测更新包并且提示用户进行更新
        :return:
        """
        files = None

        try:
            files = os.listdir(commons.PATH_UPAN)
        except Exception as e:
            print("检测更新出现问题 - 1: ", e)
            self.showErr("0x01")

        try:
            if files is not None:
                ipk_path = None
                ipk_file = None

                for file in files:
                    # 组成绝对路径
                    file_path = os.path.join(commons.PATH_UPAN, file)

                    # 判断是否有同格式的dir，这个也要避免
                    if os.path.isdir(file_path):
                        print("发现dir，自动跳过: ", file_path)
                        continue

                    # 然后判断是否是正常的文件
                    if not os.path.isfile(file_path):
                        print("发现非正常的文件，自动跳过: ", file_path)
                        continue

                    # 判断关键信息
                    # 仅仅，前缀和后缀可用的情况下才允许升级
                    prefix_ok = re.match(r"^[a-zA-Z0-9]+", file) is not None
                    suffix_ok = file.endswith(".ipk")

                    # 最终判断能否进行正常的升级
                    if prefix_ok and suffix_ok:
                        # 验证可读写
                        print("验证可读: ")
                        try:
                            with open(file_path):
                                pass
                            print("可读")
                        except Exception as e:
                            print("不可读: ", e)
                            self.showErr("0x04")
                            return

                        ipk_file = file
                        ipk_path = file_path
                        break
                    else:
                        print("该文件不符合ipk审查规范: ", file)
                        if not prefix_ok:
                            print("前缀检查不通过，不是字母或者及数字组合内容开头不允许")
                        if not suffix_ok:
                            print("后缀检查不通过，不是以ipk为结尾")
                        print("")

                if ipk_path is None:
                    self.showErr("0x03")
                else:
                    # 第一步，先移动ipk到old文件夹中
                    target_path = os.path.join(commons.PATH_UPAN, "ipk_old")
                    os.makedirs(target_path, exist_ok=True)

                    # 这里需要避免文件重复，所以使用递增的方式来区分文件
                    target_file = os.path.join(target_path, f"{len(os.listdir(target_path)) + 1}" + "_" + ipk_file)
                    # 如果文件还是重复了，说明确实拿了一样的文件来更新，这个时候我们要删除掉旧的文件
                    if os.path.exists(target_file):
                        os.remove(target_file)
                    # 然后再去拷贝新的文件
                    shutil.move(ipk_path, target_file)
                    print("自动选择ipk文件: ", target_file)
                    # 第二步，启动更新
                    self.start(activity_update.UpdateActivity, target_file)

        except Exception as e:
            print("检测更新出现问题 - 2: ", e)
            self.showErr("0x02")

        self.setidle()

    @staticmethod
    def getKernel():
        """
            获取内核信息
        :return:
        """
        return os.path.getsize("/boot/zImage")

    def init_info(self):
        """
            初始化基本信息
        :return:
        """
        try:
            self.toast.show(self.text_processing, mode=widget.Toast.MASK_FULL)

            item1 = "{}\n\n{}\n{}\n{}\n{}\n{}\n".format(
                self.text_al1.format(version.getTYP()),
                self.text_al2.format(version.getHW()),
                self.text_al3.format(version.getHMI()),
                self.text_al4.format(version.getOS()),
                self.text_al5.format(version.getPM()),
                self.text_al6.format(version.getSN()),
                # f"   KN  {self.getKernel()}",
            )

            # """
            #     Firmware update
            #     1.Download new firmware
            #         icopy-x.com/update
            #     2.Plug USB, Copy it to device.
            #     3.Press”OK”start update.
            # """

            item2 = "{}\n\n{}\n{}\n{}\n{}".format(
                self.text_alu1,
                self.text_alu2,
                self.text_alu3,
                self.text_alu4,
                self.text_alu5,
            )

            self.lv = widget.BigTextListView(self.getCanvas(), (0, 60), items=[item1, item2])
            self.pi = widget.PageIndicator(self.getCanvas(), self.tags_title)
            self.lv.setOnPageChangeCall(self.pi.update)
            self.lv.setPageModeEnable(True)
        finally:
            self.toast.cancel()
            self.setidle()
            self.initializing = False

    def start_init_data_to_view(self):
        """
            将版本信息初始化到屏幕上
        :return:
        """
        self.initializing = True
        self.setbusy()
        self.startBGTask(self.init_info)

    def onCreate(self):
        self.setTitle(self.text_about)
        self.start_init_data_to_view()

    def onResume(self):
        super().onResume()

        # 不在更新视图信息并且触发了这个活动的回调
        # 我们才自动取消对话框
        if not self.initializing:
            self.toast.cancel()

    def onKeyEvent(self, event):
        if self.isbusy() or self.initializing:
            return False

        if event == keymap.ALL:
            self.finish()
            self.start(AutoCopyActivity)
            return True
        if event == keymap.POWER:
            if self.toast.isShow():
                self.toast.cancel()
                return True
            self.finish()
            return True
        if event == keymap.DOWN:
            if self.toast.isShow():
                return True
            self.lv.next(True)
            return True
        if event == keymap.UP:
            if self.toast.isShow():
                return True
            self.lv.prev(True)
            return True
        if event == keymap.OK:
            if self.lv.getPagePosition() == 1:
                self.setbusy()
                # 当前处于第二页，我们需要检查更新
                self.startBGTask(self.checkUpdate)
            return True
        if event == keymap.RIGHT:
            try:
                self.start(SnakeGameActivity)
            except Exception as e:
                print(e)
            return True

        return False


class ReadListActivity(AutoCopyActivity):
    text_no_tag_found2 = resources.get_str("no_tag_found2")

    @staticmethod
    def getManifest():
        return {
            "index": 3,
            "infos": tuple((AutoCopyActivity.text_read_tag, images.load("3.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)

        self.lv = widget.ListView(self.getCanvas(), (0, 40))
        self.pi = widget.PageIndicator(self.getCanvas(), self.tags_title)
        self.pi.hide()

        self.readableList = None
        self.selectPos = -1

    def initList(self):
        """
            初始化所有的可读卡片的列表
        :return:
        """
        self.readableList = tagtypes.getReadable()
        if self.destroyed:
            return
        items = tagtypes.getName(self.readableList)
        for i in items:
            index = items.index(i)
            items[index] = "{: >2d}. {}".format(index + 1, i)
        self.lv.setItems(items)
        self.lv.setOnPageChangeCall(self.pi.update)

    def showScanToast(self, found, multi):
        if not found:
            self.scan_toast.show(self.text_no_tag_found2)
            audio.playwrongTagfound()
        if multi:
            self.scan_toast.show(self.text_tag_multi)
            audio.playMultiCard()

    def how2Scan(self):
        # 覆盖搜索实现的调用
        # 使用类型限定的搜索实现
        self.scanner.scan_type_asynchronous(self.readableList[self.selectPos])

    def onAutoScan(self):
        return  # 不需要自动开始scan

    def onCreate(self):
        # 初始化父类的项目
        super().onCreate()
        # 设置标题
        self.setTitle(self.text_read_tag, (108, 20))
        self.initList()

    def set_tag_list_enable(self, enable):
        if enable:
            # 显示视图
            template.dedraw(self.getCanvas())
            # 设置标题
            self.setTitle(self.text_read_tag, (108, 20))
            self.lv.show()
            self.pi.show()
            self.selectPos = -1
            self.dismissButton()
        else:
            # 隐藏视图
            self.lv.hide()
            self.pi.hide()
            self.setTitle(self.text_read_tag)

    def onKeyEvent(self, event):
        # 进入读取scan页面后开始转交一些按钮事件
        if self.selectPos != -1:
            if event == keymap.POWER:
                if self.isbusy():
                    return super().onKeyEvent(event)

                if self.console_activity.is_showing():
                    self.console_activity.hidden()
                    return True

                if self.scan_toast.isShow():
                    self.scan_toast.cancel()
                    return True

                if self.read_result_toast.isShow():
                    self.read_result_toast.cancel()
                    return True

                if not self.lv.isShowing():  # 显示所有支持读的标签列表
                    self.set_tag_list_enable(True)
                    return True
            return super().onKeyEvent(event)

        if event == keymap.POWER:
            if self.isbusy():
                return False
            if not self.lv.isShowing():
                self.set_tag_list_enable(True)
                return True
            self.finish()
            return True

        if event == keymap.OK:
            # 选中该项目后，缓存当前的类型
            self.selectPos = self.lv.getSelection()
            self.set_tag_list_enable(False)
            # 开始搜索
            self.startScan()
            return True

        if event == keymap.DOWN:
            self.lv.next(True)
            return True

        if event == keymap.UP:
            self.lv.prev(True)
            return True

        if event == keymap.LEFT:
            self.lv.prev(prevPage=True)
            return True

        if event == keymap.RIGHT:
            self.lv.next(nextPage=True)
            return True

        if event == keymap.ALL:
            if self.isbusy() or not self.lv.isShowing():
                return False
            self.finish()
            self.start(AutoCopyActivity)
            return True

        return False


class VolumeActivity(BaseActivity):
    """
        音量控制的活动，用于控制全志的输出音量
    """

    text_volume, text_vl1, text_vl2, text_vl3, text_vl4 = resources.get_str([
        "volume", "valueline1", "valueline2", "valueline3", "valueline4",
    ])

    @staticmethod
    def getManifest():
        return {
            "index": 10,
            "infos": tuple((VolumeActivity.text_volume, images.load("9.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.lv = None

    def onCreate(self):
        self.setTitle(self.text_volume)

        items = [
            self.text_vl1,
            self.text_vl2,
            self.text_vl3,
            self.text_vl4,
        ]

        self.lv = widget.CheckedListView(self.getCanvas(), (0, 40), items=items)
        v = settings.getVolume()
        # 更新视图
        self.lv.selection(v)
        self.lv.check(v)

        # 关闭按键音使能
        audio.setKeyAudioEnable(False)

    def saveSetting(self):
        pos = self.lv.getSelection()
        self.lv.check(pos)
        settings.setVolume(pos)
        # 设置全局的音量标志
        v = settings.fromLevelGetVolume(pos)
        audio.setVolume(v)
        audio.playVolumeExam(v)

    def onKeyEvent(self, event):
        if event == keymap.ALL:
            if self.isbusy():
                return False
            self.finish()
            self.start(AutoCopyActivity)
            return True
        if event == keymap.POWER:
            audio.stop()
            audio.setKeyAudioEnable(True)
            audio.playKeyEnable()
            self.finish()
            return
        if event == keymap.OK:
            self.startBGTask(self.saveSetting)
            return
        if event == keymap.DOWN:
            self.lv.next()
            pos = self.lv.getSelection()
            audio.playVolumeExam(settings.fromLevelGetVolume(pos))
            return
        if event == keymap.UP:
            self.lv.prev()
            pos = self.lv.getSelection()
            audio.playVolumeExam(settings.fromLevelGetVolume(pos))
            return

        return False


class BacklightActivity(BaseActivity):
    """
        亮度控制的活动，用于控制lcd背光亮度
    """

    text_backlight, text_bl1, text_bl2, text_bl3 = resources.get_str([
        "backlight", "blline1", "blline2", "blline3"
    ])

    @staticmethod
    def getManifest():
        return {
            "index": 9,
            "infos": tuple((BacklightActivity.text_backlight, images.load("8.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.lv = None

    def onCreate(self):
        self.setTitle(self.text_backlight)

        items = [
            self.text_bl1,
            self.text_bl2,
            self.text_bl3,
        ]

        self.lv = widget.CheckedListView(self.getCanvas(), (0, 40), items=items)
        pos = settings.getBacklight()
        self.lv.selection(pos)
        self.lv.check(pos)

    def updateBacklight(self):
        pos = self.lv.getSelection()
        bl = settings.fromLevelGetBacklight(pos)
        # 在子线程中执行
        self.startBGTask(lambda: hmi_driver.setbaklight(bl))

    def recovery_backlight(self):
        bl = settings.fromLevelGetBacklight(settings.getBacklight())
        # 在子线程中执行
        self.startBGTask(lambda: hmi_driver.setbaklight(bl))

    def onKeyEvent(self, event):
        if event == keymap.ALL:
            if self.isbusy():
                return False
            self.recovery_backlight()
            self.finish()
            self.start(AutoCopyActivity)
            return True
        if event == keymap.POWER:
            self.recovery_backlight()
            self.finish()
            return True
        if event == keymap.OK:
            pos = self.lv.getSelection()
            self.lv.check(pos)
            settings.setBacklight(pos)
            return True
        if event == keymap.DOWN:
            self.lv.next()
            self.updateBacklight()
            return True
        if event == keymap.UP:
            self.lv.prev()
            self.updateBacklight()
            return True

        return False


class SniffActivity(BaseActivity):
    text_sniff_tag, text_sl1, text_sl2, text_sl3, text_sl4, text_si1, text_si2, text_si3, text_si4, text_si5 = \
        resources.get_str([
            "sniff_tag", "sniffline1", "sniffline2", "sniffline3", "sniffline4",
            "sniff_item1", "sniff_item2", "sniff_item3", "sniff_item4", "sniff_item5"
        ])

    text_sniffing, text_finish, text_t5577_sniff_finished, text_save, text_start, text_sniff_decode, text_sniff_trace = \
        resources.get_str([
            "sniffing", "finish", "t5577_sniff_finished", "save", "start", "sniff_decode", "sniff_trace"
        ])

    text_uid_item, text_key_item, text_save_log, text_processing, text_trace_saved, text_sniffline_t5577, = \
        resources.get_str([
            "uid_item", "key_item", "save_log", "processing", "trace_saved", "sniffline_t5577"
        ])

    text_sniff_notag = resources.get_str("sniff_notag")

    @staticmethod
    def getManifest():
        return {
            "index": 4,
            "infos": tuple((SniffActivity.text_sniff_tag, images.load("5.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)

        self.progress = None
        self.lvTips = None
        self.lvTags = None
        self.lvResult = None
        self.pageIndicator = None
        self.toast = None

        self.pos = -1
        self.start_maps = None
        self.list_maps = None
        self.type_maps = None

        self.sniffing = False
        self.savable = False
        self.keys = None

        self.trace_len_known = None
        self.trace_len_update = 0
        self.stopping = False

        # 提示列表
        self.tips_items = [
            self.text_sl1,
            self.text_sl2,
            self.text_sl3,
            self.text_sl4,
        ]

        # 标签列表
        self.tags_items = [
            self.text_si1,
            self.text_si2,
            self.text_si3,
            self.text_si4,
            self.text_si5,
        ]

        self.start_maps = [
            sniff.sniff14AStart,
            sniff.sniff14BStart,
            sniff.sniffIClassAStart,
            sniff.sniffTopazStart,
            sniff.sniffT5577Start,
        ]

        self.list_maps = [
            "hf list mf",
            "hf list 14b",
            "hf list iclass",
            "hf list topaz",
            "x",
        ]

        self.type_maps = [
            "14a",
            "14b",
            "iclass",
            "topaz",
            "t5577"
        ]

    def onMultiPIUpdate(self, page_max, page_new):
        # 启用在列表页的指示器的底部标志
        self.pageIndicator.setBottomIndicatorEnable(True)
        self.pageIndicator.update(page_max, page_new)

    def onTopPIOnlyUpdate(self, page_max, page_new):
        # 禁用在列表页的指示器的底部标志
        self.pageIndicator.setBottomIndicatorEnable(False)
        self.pageIndicator.update(page_max, page_new)

    def onCreate(self):
        self.setTitle(self.text_sniff_tag, (100, 18))

        # 在初始化标题后，初始化一个指示器，跟随在标题的右边
        self.pageIndicator = widget.PageIndicator(self.getCanvas(), self.tags_title)
        self.pageIndicator.setLoop(True)

        self.lvTips = widget.BigTextListView(self.getCanvas(), (0, 40), self.tips_items)
        self.lvTips.hide()
        self.lvTips.setOnPageChangeCall(self.onMultiPIUpdate)

        self.lvTags = widget.ListView(self.getCanvas(), (0, 40), self.tags_items)
        self.lvTags.setOnPageChangeCall(self.onTopPIOnlyUpdate)

        # 结果列表
        self.lvResult = widget.ListView(self.getCanvas(), (0, 40))
        self.lvResult.setPageModeEnable(True)
        self.lvResult.setDisplayItemMax(4)
        self.lvResult.hide()
        self.lvResult.setOnPageChangeCall(self.onMultiPIUpdate)

        self.toast = widget.Toast(self.getCanvas())

        # 绘制一个进度条，用于显示解码进度
        self.progress = widget.ProgressBar(self.getCanvas(), (20, 188))
        self.progress.hide()

    def startSniff(self):
        """
            开始嗅探
        :return:
        """
        self.toast.show(self.text_sniffing)
        audio.playSniffing()
        self.setRightButton(self.text_finish)
        self.disableButton(right=False)
        self.sniffing = True
        self.savable = False
        self.trace_len_known = None
        self.trace_len_update = 0

        print("启动嗅探！")
        # 取出映射表中的实现函数进行启动嗅探
        self.start_maps[self.pos]()

        # 当前是T5577低频卡嗅探，
        # 启动后，会自动工作到结束，过程是堵塞型的
        # 当有秘钥发现，任务会直接结束，然后我们可以进行秘钥解析了
        if self.pos == 4:
            # 隐藏所有的控件
            self.hideAll()

            # 然后设置按钮
            self.setRightButton(self.text_save)
            self.setLeftButton(self.text_start)

            self.sniffing = False
            self.savable = True

            self.showT5577Result()
            self.setidle()
        print("结束嗅探！")

    def decode_Line(self, line: str):
        """
            解析行并且更新UI
        :param line:
        :return:
        """
        if self.trace_len_known is None:
            # 我们需要在tracelen没有初始化的情况下初始化tracelen
            sea_obj = re.search(sniff.PATTERN_HF_TRACE_LEN, line)
            if sea_obj is not None:
                self.trace_len_known = int(sea_obj.group(1))
                if self.trace_len_known <= 0:
                    return
                # 更新UI
                self.showTracelen4Text(self.trace_len_known)
                self.progress.setMax(self.trace_len_known)
        elif self.trace_len_known <= 0:
            return
        elif self.trace_len_known is not None:
            # 截取字节组
            # bytes_sea_obj = re.search(sniff.PATTERN_DATA_BYTES, line)
            # if bytes_sea_obj is not None:
            #     # 然后进行截取，按照空格
            #     bytes_count = len(bytes_sea_obj.group(1).split(" "))
            #     print("本次发现的字节数: ", bytes_count)
            # 直接使用行数 * 10进行字符统计
            self.trace_len_update += (9 * line.count("\n"))
            # 更新到UI
            if self.trace_len_update <= self.trace_len_known:
                self.progress.setMessage(
                    self.text_sniff_decode.format(self.trace_len_update, self.trace_len_known))
                self.progress.setProgress(self.trace_len_update)

    def hideAll(self):
        """
            简简单单的隐藏所有的控件
        :return:
        """
        self.toast.cancel()
        self.lvTips.hide()
        self.lvTags.hide()
        self.lvResult.hide()
        self.dismissButton()
        self.dismissTracelenText()
        self.progress.hide()

    def showTracelen4Text(self, tracelen, xy=(120, 68)):
        """
            显示嗅探数据的长度
        :param xy: 显示的位置
        :param tracelen: 记录的长度！
        :return:
        """
        canvas = self.getCanvas()
        tags = self.unique_id("tracelen_text")
        text = self.text_sniff_trace.format(tracelen)
        w = canvas.find_withtag(tags)
        if len(w) <= 0:
            canvas.create_text(
                xy,
                font=resources.get_font(15),
                width=220,
                text=text, tags=tags, state="normal"
            )
        else:
            canvas.itemconfig(w, text=text, state="normal")
            canvas.coords(w, xy)
        print("截取到的嗅探数据长度为: ", tracelen)

    def dismissTracelenText(self):
        """
            隐藏tracelen显示的控件
        :return:
        """
        tags = self.unique_id("tracelen_text")
        self.getCanvas().itemconfig(tags, state="hidden")

    def stopSniff(self):
        """
            停止嗅探
        :return:
        """
        if self.stopping:
            return

        if self.pos == 4:
            self.stopping = True
            # 模拟点击PM3，结束嗅探
            hmi_driver.presspm3()
            time.sleep(1)
            executor.stopPM3Task()
            time.sleep(1)
            self.stopping = False
            return

        self.stopping = True

        # 模拟点击PM3，结束嗅探
        hmi_driver.presspm3()
        time.sleep(1)  # 延时一段时间，让PM3先停止任务
        self.hideAll()  # 先隐藏所有的控件
        self.progress.show()  # 再显示解码需要的进度条
        # 结束之后尝试打印结果
        executor.startPM3Task(self.list_maps[self.pos], -1, self.decode_Line)
        self.progress.hide()
        self.dismissTracelenText()
        self.showHfResult()
        self.sniffing = False
        self.stopping = False
        self.setidle()

    def showItems(self, items):
        """
            显示秘钥项在列表上
        :param items:
        :return:
        """
        # 将结果显示在UI上
        self.lvResult.setItems(items)
        self.pageIndicator.setBottomIndicatorEnable(True)

    def showT5577Result(self):
        print("开始解析结果长度...")
        trace_len = sniff.parserLfTraceLen()
        print("结果长度解析完成: ", trace_len)
        print("开始解析秘钥...")
        # 先解析有效的秘钥
        self.keys = sniff.parserKeysForT5577(sniff.parserT5577OkKeyForLine)
        # 再解析无效的秘钥（只用来显示）
        visible_key = []
        visible_key.extend(sniff.parserKeysForT5577(sniff.parserT5577LeadingKeyForLine))
        visible_key.extend(sniff.parserKeysForT5577(sniff.parserT5577WriteKeyForLine))

        print("秘钥解析完成: ", self.keys)

        if self.keys is None or len(self.keys) <= 0:
            print("解析到的秘钥组为空，可能没有嗅探到数据。")
            self.showTracelen4Text(trace_len, (120, 120))
        else:
            items = [self.text_sniff_trace.format(trace_len)]
            # 组成可用秘钥列表
            for index in range(len(self.keys)):
                item_format = "  " + self.text_key_item + "{} √"
                items.append(item_format.format(index + 1, self.keys[index]))

            # 组成可用秘钥列表
            for index in range(len(visible_key)):
                item_format = "  " + self.text_key_item + "{} X"
                items.append(item_format.format(index + 1, visible_key[index]))

            # 自动保存秘钥
            # 我们只保存有效秘钥
            if self.keys is not None and len(self.keys) > 0:
                lft55xx.genKeyFile(self.keys)

            # 将结果显示在UI上
            self.showItems(items)

        self.setLeftButton(self.text_start)
        if trace_len > 0:
            self.setRightButton(self.text_save_log)
            self.savable = True
        else:
            self.savable = False
            self.setRightButton(self.text_save_log, "grey")

    def showHfResult(self):
        print("开始解析结果长度...")
        trace_len = sniff.parserHfTraceLen()
        print("结果长度解析完成: ", trace_len)
        print("开始解析秘钥...")
        self.keys = sniff.parserKeyForM1()
        print("秘钥解析完成: ", self.keys)

        if self.keys is None or len(self.keys) <= 0:
            print("解析到的秘钥组为空，可能没有嗅探到数据。")
            self.showTracelen4Text(trace_len, (120, 120))
        else:
            items = [self.text_sniff_trace.format(trace_len)]
            # 组成列表
            for key_item in self.keys.keys():
                uid = key_item
                items.append(self.text_uid_item + uid)
                keys_list_tmp = self.keys[key_item]
                for index in range(len(keys_list_tmp)):
                    item_format = "  " + self.text_key_item + "{}"
                    items.append(item_format.format(index + 1, keys_list_tmp[index]))

            # 自动保存秘钥
            if self.keys is not None and len(self.keys) > 0:
                for uid in self.keys.keys():
                    hfmfkeys.genKeyFile(uid, self.keys[uid])

            # 将结果显示在UI上
            self.showItems(items)

        self.setLeftButton(self.text_start)
        if trace_len > 0:
            self.setRightButton(self.text_save_log)
            self.savable = True
        else:
            self.savable = False
            self.setRightButton(self.text_save_log, "grey")

    def setupOnTypeSelected(self):
        # 针对相应的模式，提供不同的UI扩展
        if self.pos == 4:  # 当前选择了T55XX的卡片类型，我们需要针对T5577的卡片做出特异的处理
            self.setTitle(self.text_sniff_notag, (100, 18))
            self.lvTips.setItems([self.text_sniffline_t5577], False)
        else:
            self.lvTips.setItems(self.tips_items, False)

        # 显示嗅探的提示文本
        self.lvTips.show()

        # 显示按钮
        self.setLeftButton(self.text_start)
        self.setRightButton(self.text_finish)
        self.disableButton(left=False)
        # 开启底部的指示器
        self.pageIndicator.setBottomIndicatorEnable(True)
        self.pageIndicator.show()

    def saveSniffData(self):
        self.toast.show(self.text_processing)
        self.disableButton()

        content = executor.getPrintContent()
        file = appfiles.create_trace(self.type_maps[self.pos])
        appfiles.save2any(content, file)

        self.toast.show(self.text_trace_saved)
        audio.playTraceFileSaved()
        self.disableButton(False, True)
        self.setidle()

    def nextIfShowing(self, lv):
        if lv.isShowing():
            lv.next(True)
            if lv == self.lvTips:
                if not self.play_select_tips():
                    audio.playKeyDisable()
                return None
            return True
        return False

    def prevIfShowing(self, lv):
        if lv.isShowing():
            lv.prev(True)
            if lv == self.lvTips:
                if not self.play_select_tips():
                    audio.playKeyDisable()
                return None
            return True
        return False

    def onData(self, bundle):
        if isinstance(bundle, dict):
            select_pos = bundle["selection"]
            auto_start = bundle["auto"]

            self.lvTags.selection(select_pos)
            self.pos = select_pos
            self.lvTags.hide()
            self.lvTips.show()
            self.setupOnTypeSelected()

            if auto_start:
                self.setbusy()
                self.startBGTask(self.startSniff)

    def play_select_tips(self):
        """
            播放选择的语音
        :return:
        """
        if self.pos == 4:  # 当前是在T55XX模式，我们没有相对的语音，所以不需要播放
            # TODO  以后有需要可以播放
            return False

        audio.setBlockingPlay(True)
        audio.playKeyEnable()
        audio.setBlockingPlay(False)
        # audio.playSniffStep1()
        # 播放页面切换时的音频
        page_new = self.lvTips.getSelection()
        if page_new == 0:
            audio.playSniffStep1()
        elif page_new == 1:
            audio.playSniffStep2()
        elif page_new == 2:
            audio.playSniffStep3()
        elif page_new == 3:
            audio.playSniffStep4()

        return True

    def onKeyEvent(self, event):
        if event == keymap.ALL:
            if self.isbusy() or not self.lvTags.isShowing():
                return False
            self.finish()
            self.start(AutoCopyActivity)
            return True

        if event == keymap.POWER:
            if self.isbusy():
                if not self.stopping:
                    self.startBGTask(self.stopSniff)
                    return True
                else:
                    return False
            else:
                if self.toast.isShow():
                    self.toast.cancel()
                elif not self.lvTags.isShowing():
                    self.hideAll()
                    self.savable = False  # 解决回退到TAG类型选择页面后，依旧能保存的问题
                    self.lvTags.show()
                else:
                    self.finish()
                return True

        if event == keymap.M1:
            if self.isbusy() or self.lvTags.isShowing() or self.pos < 0:
                return False
            self.setbusy()
            self.startBGTask(self.startSniff)
            return True

        if event == keymap.M2:
            if self.pos < 0 or self.lvTags.isShowing():
                return False
            if self.sniffing and not self.stopping:
                self.setbusy()
                self.startBGTask(self.stopSniff)
                return True
            elif self.savable and not self.isbusy():
                self.setbusy()
                self.savable = False  # 只允许保存一次
                self.startBGTask(self.saveSniffData)
                return True
            # self.startBGTask(self.stopSniff)
            return False

        if event == keymap.OK:
            # 查看选中项
            if self.lvTags.isShowing():
                self.lvTags.hide()
                # 缓存选中项
                self.pos = self.lvTags.getSelection()
                self.startBGTask(self.play_select_tips)
                self.setupOnTypeSelected()
                return
            else:
                return False

        if event == keymap.DOWN:
            if self.isbusy():
                return False
            if self.nextIfShowing(self.lvTips) is None:
                return
            self.nextIfShowing(self.lvTags)
            self.nextIfShowing(self.lvResult)
            return True

        if event == keymap.UP:
            if self.isbusy():
                return False
            if self.prevIfShowing(self.lvTips) is None:
                return
            self.prevIfShowing(self.lvTags)
            self.prevIfShowing(self.lvResult)
            return True

        return False


class SniffForSpecificTag(SniffActivity):
    """
        自动模式下，嗅探指定的卡，然后结束后回发特定的数据
    """

    text_reread = resources.get_str("reread")

    @staticmethod
    def getManifest():
        """
            我们不需要显示在主菜单上，因此把清单信息去掉！
        :return:
        """
        pass

    def onSniffOk(self):
        """
            嗅探完成后处理的事情
        :return:
        """
        color = "white" if len(self.keys) > 0 else "grey"
        self.setRightButton(self.text_reread, color)

    def onSniffFinish(self):
        """
            在点击重新读取的时候
        :return:
        """
        pass

    def onKeyEvent(self, event):
        """
            重新书写专用于读卡时自动嗅探的按钮事件！
        :param event:
        :return:
        """
        if self.sniffing:
            if event == keymap.POWER or event == keymap.M2:
                return super().onKeyEvent(event)
        else:
            if event == keymap.POWER:
                self.finish()  # 直接结束嗅探
            elif event == keymap.M1:
                return super().onKeyEvent(event)
            elif event == keymap.M2:
                if len(self.keys) > 0:  # 有密钥，可以重新尝试读取
                    self.onSniffFinish()
            elif event == keymap.UP or event == keymap.DOWN:
                return super().onKeyEvent(event)
        return False


class SniffForMfReadActivity(SniffForSpecificTag):
    """
        专属于读卡跳转的自动嗅探
    """

    def showHfResult(self):
        super().showHfResult()
        self.onSniffOk()

    def onSniffFinish(self):
        self.finish(ReadActivity.FORCE_Reread)


class SniffForT5XReadActivity(SniffForSpecificTag):
    """
        专属于T55XX的读卡跳转的
        嗅探页面
    """

    def showT5577Result(self):
        super().showT5577Result()
        self.onSniffOk()

    def onSniffFinish(self):
        self.finish(ReadActivity.FORCE_Reread)


class SimulationTraceActivity(BaseActivity):
    """
        模拟卡的一些数据的保存函数
    """

    text_sniff_trace, text_cancel, text_save_log, text_processing, text_trace_saved, text_trace, text_trace_loading = \
        resources.get_str([
            "sniff_trace", "cancel", "save_log", "processing", "trace_saved", "trace", "trace_loading",
        ])

    def __init__(self, canvas):
        super().__init__(canvas)
        self.toast = widget.Toast(self.getCanvas())
        self.savable = False
        self.saved = False

    def showResult(self):
        self.setbusy()

        cmd = "hf 14a list"
        executor.startPM3Task(cmd, 18888)

        trace_len = sniff.parserHfTraceLen()
        text = self.text_sniff_trace.format(trace_len)

        tags = self.unique_id("trace_len")
        self.getCanvas().delete(tags)
        self.getCanvas().create_text((120, 120), font=resources.get_font(15), width=220, text=text, tags=tags)
        self.setLeftButton(self.text_cancel)
        if trace_len > 0:
            self.setRightButton(self.text_save_log)
            self.savable = True
        else:
            self.savable = False
            self.setRightButton(self.text_save_log, "grey")

        self.toast.cancel()
        self.setidle()

    def saveSniffData(self):
        self.setbusy()
        self.toast.show(self.text_processing)
        content = executor.getPrintContent()
        file = appfiles.create_trace("14a")
        appfiles.save2any(content, file)
        self.toast.show(self.text_trace_saved)
        self.disableButton(False, True)
        self.setidle()

    def onCreate(self):
        self.setTitle(self.text_trace)
        self.toast.show(self.text_trace_loading, mode=widget.Toast.MASK_FULL)
        self.startBGTask(self.showResult)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if self.isbusy():
                return False
            if self.toast.isShow():
                self.toast.cancel()
                return True
            self.finish()
            return True

        if event == keymap.M1:
            if self.isbusy():
                return False
            self.finish()
            return True

        if event == keymap.M2:
            if self.isbusy():
                return False
            if self.savable and not self.saved:
                self.saved = True
                self.startBGTask(self.saveSniffData)
            else:
                print("本次模擬卡交互結果不可保存。")
                return False
            return True

        return False


class SimulationActivity(BaseActivity):
    """
        模拟卡ACT
        1、先选择需要模拟的卡的类型
        2、选择后显示UID的输入框
        3、结束模拟后，IC卡需要list数据和保存，ID卡可以直接退出模拟
    """

    text_simulation, text_sim_valid_input, text_simulating, text_sim_valid_param, text_processing, text_stop = \
        resources.get_str([
            "simulation", "sim_valid_input", "simulating", "sim_valid_param", "processing", "stop",
        ])

    text_start = resources.get_str("start")

    @staticmethod
    def getManifest():
        return {
            "index": 5,
            "infos": tuple((SimulationActivity.text_simulation, images.load("6.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)

        self.TYP_ITEMS = [
            # 项目名 模拟卡的指令 模拟卡的UI绘制函数 输入的数据的检测函数 模拟卡结束后需要做的操作 卡片的附属ID 输入框的最小长度限定
            # 高频卡模拟
            (
                "M1 S50 1k",
                "hf 14a sim t 1 u {} ",
                self.draw_hf_sim_4b,
                None,
                self.on14ASimStop,
                tagtypes.M1_S50_1K_4B,
                (8,),
            ),
            (
                "M1 S70 4k",
                "hf 14a sim t 8 u {} ",
                self.draw_hf_sim_4b,
                None,
                self.on14ASimStop,
                tagtypes.M1_S70_4K_4B,
                (8,),
            ),
            (
                "Ultralight",
                "hf 14a sim t 2 u {}",
                self.draw_hf_sim_7b,
                None,
                self.on14ASimStop,
                tagtypes.ULTRALIGHT,
                (14,),
            ),
            (
                "Ntag215",
                "hf 14a sim t 7 u {}",
                self.draw_hf_sim_7b,
                None,
                self.on14ASimStop,
                tagtypes.NTAG215_504B,
                (14,),
            ),
            (
                "FM11RF005SH",
                "hf 14a sim t 9 u {}",
                self.draw_hf_sim_7b,
                None,
                self.on14ASimStop,
                tagtypes.UNSUPPORTED,
                (14,),
            ),
            # 低频卡模拟
            (
                "Em410x ID",
                "lf em 410x_sim {}",
                self.draw_lf_sim_5b,
                None,
                None,
                tagtypes.EM410X_ID,
                (10,),
            ),
            (
                "HID Prox ID",
                "lf hid sim {}",
                self.draw_lf_sim_5b,
                None,
                None,
                tagtypes.HID_PROX_ID,
                (10,),
            ),
            (
                "AWID ID",
                "lf awid sim {} {} {}",
                self.draw_lf_awid,
                None,
                None,
                tagtypes.AWID_ID,
                (2, 4, 8),
            ),
            (
                "IO Prox ID",
                "lf io sim {} {} {}",
                self.draw_lf_io,
                self.chk_ioid_input,
                None,
                tagtypes.IO_PROX_ID,
                (2, 2, 5),
            ),
            (
                "G-Prox II ID",
                "lf gproxii sim {} {} {}",
                self.draw_lf_gporx,
                self.chk_gproxid_input,
                None,
                tagtypes.GPROX_II_ID,
                (2, 3, 5),
            ),
            (
                "Viking ID",
                "lf Viking sim {}",
                self.draw_lf_sim_4b,
                None,
                None,
                tagtypes.VIKING_ID,
                (8,),
            ),
            (
                "Pyramid ID",
                "lf Pyramid sim {} {}",
                self.draw_lf_pyramid,
                self.chk_pyramid_input,
                None,
                tagtypes.PYRAMID_ID,
                (3, 5),
            ),
            (
                "FDX-B ID Animal",
                "lf FDX sim c {} n {} s",
                self.draw_lf_fdx_animal,
                None,
                None,
                tagtypes.FDXB_ID,
                (3, 12),
            ),
            (
                "FDX-B ID Data",
                "lf FDX sim c {} n {} e {}",
                self.draw_lf_fdx_data,
                None,
                None,
                tagtypes.UNSUPPORTED,
                (3, 12, 3),
            ),
            (
                "Jablotron ID",
                "lf Jablotron sim {}",
                self.draw_lf_jablotron,
                None,
                None,
                tagtypes.JABLOTRON_ID,
                (10,),
            ),
            (
                "Nedap ID",
                "lf nedap sim s {} c {} i {}",
                self.draw_lf_nedap,
                self.chk_nedap_input,
                None,
                tagtypes.NEDAP_ID,
                (2, 3, 5),
            ),
        ]

        self.main_items = []
        index_typ = 1
        for typ_item in self.TYP_ITEMS:
            self.main_items.append(f" {index_typ}. {typ_item[0]}")
            index_typ += 1

        self.lv = widget.ListView(canvas, (0, 40), self.main_items)
        self.pi = widget.PageIndicator(canvas, self.tags_title)
        self.lv.setOnPageChangeCall(self.pi.update)
        self.toast = widget.Toast(canvas)

        self.input_methods = []
        self.input_method_selection = 0

        self.sim_stopping = False

    @staticmethod
    def getSimMap():
        """
            获得支持的sim映射表
        :return:
        """
        SIM_MAP = {
            #     卡片类型             参数解析的实现函数         参数个数
            # 高频
            tagtypes.M1_S50_1K_4B: (SimulationActivity.parserUID, 1),
            tagtypes.M1_S70_4K_4B: (SimulationActivity.parserUID, 1),
            tagtypes.ULTRALIGHT: (SimulationActivity.parserUID, 1),
            tagtypes.NTAG215_504B: (SimulationActivity.parserUID, 1),
            # 低频
            tagtypes.EM410X_ID: (SimulationActivity.parserData, 1),
            tagtypes.HID_PROX_ID: (SimulationActivity.parserData, 1),
            tagtypes.AWID_ID: (SimulationActivity.parserFCCN, 3),
            tagtypes.IO_PROX_ID: (SimulationActivity.parserIoPorx, 3),
            tagtypes.GPROX_II_ID: (SimulationActivity.parserFCCN, 3),
            tagtypes.VIKING_ID: (SimulationActivity.parserData, 1),
            tagtypes.PYRAMID_ID: (SimulationActivity.parserPyramid, 2),
            tagtypes.FDXB_ID: (SimulationActivity.parserFdx, 2),
            tagtypes.JABLOTRON_ID: (SimulationActivity.parserJabDat, 1),
            tagtypes.NEDAP_ID: (SimulationActivity.parserNedap, 3),
        }
        return SIM_MAP

    @staticmethod
    def filter_space(data_list):
        """
            过滤掉无效的空的参数
        :param data_list:
        :return:
        """
        ret = []
        for e in data_list:
            if isinstance(e, numbers.Number):
                ret.append(e)
            elif e is not None:
                try:
                    if len(e) > 0:
                        ret.append(e)
                except Exception:
                    ret.append(e)
        return ret

    @staticmethod
    def parserUID(data):
        """
            解析UID参数
        :return:
        """
        return SimulationActivity.filter_space([data["uid"]])

    @staticmethod
    def parserData(data):
        """
            解析data参数
        :param data:
        :return:
        """
        return SimulationActivity.filter_space([data["data"]])

    @staticmethod
    def parserJabDat(data):
        """
            解析jab卡片的模拟卡参数
        :return:
        """
        return SimulationActivity.filter_space([int(data["data"], 16)])

    @staticmethod
    def parserIoPorx(data):
        """
            解析jab卡片的模拟卡参数
        :return:
        """
        # XSF(01)01:00036
        try:
            data = data["data"]
            v = re.search(r"\((.*)\)", data).group(1)
            f = re.search(r"\)(.*):", data).group(1)
            c = re.search(r":(.*)", data).group(1)
            return SimulationActivity.filter_space([v, f, c])
        except Exception:
            return []

    @staticmethod
    def parserFCCN(data):
        """
            解析fccn信息
        :return:
        """
        format_code = data["len"]
        fc = data["fc"]
        cn = data["cn"]
        return SimulationActivity.filter_space([format_code, fc, cn])

    @staticmethod
    def parserPyramid(data):
        """
            解析Pyramid卡片的参数信息
        :param data:
        :return:
        """
        try:
            fc = data["fc"]
            cn = data["cn"]
            return SimulationActivity.filter_space([fc, cn])
        except Exception:
            return []

    @staticmethod
    def parserFdx(data):
        """
            解析fdx的参数
        :param data:
        :return:
        """
        try:
            g = str(data["data"]).split("-")
            return SimulationActivity.filter_space([g[0], g[1]])
        except Exception:
            return []

    @staticmethod
    def parserNedap(data):
        """
            解析fdx的参数
        :param data:
        :return:
        """
        try:
            return SimulationActivity.filter_space(
                [data["subtype"], data["code"], data["data"]]
            )
        except Exception:
            return []

    def chk_max_comm(self, data, typ="'CN'", max_value=65536):
        """
            通用的65536上限检测函数
        :param max_value:
        :param typ:
        :param data:
        :return:
        """
        if int(data) > max_value:
            self.toast.show(self.text_sim_valid_input.format(typ, max_value))
            return False
        return True

    def chk_ioid_input(self, inputs):
        """
            检测io id卡的输入
        :param inputs:
        :return:
        """
        return self.chk_max_comm(inputs[2])

    def chk_gproxid_input(self, inputs):
        """
            检测gproxidk卡的输入
        :return:
        """
        if not self.chk_ioid_input(inputs):
            return False

        return self.chk_max_comm(inputs[1], max_value=255, typ="'FC'")

    def chk_pyramid_input(self, inputs):
        """
            检测pyramid卡的输入
        :param inputs:
        :return:
        """
        if self.chk_max_comm(inputs[0], typ="'FC'", max_value=255):
            return self.chk_max_comm(inputs[1])
        return False

    def chk_nedap_input(self, inputs):
        """
            检测fdx卡片的输入
        :param inputs:
        :return:
        """
        return self.chk_max_comm(inputs[0], typ="'Subtype'", max_value=15)

    def draw_top_title(self, title):
        # 绘制顶部标题
        self._canvas.create_text((120, 60), font=resources.get_font(15), fill="#1C6AEB", width=230, text=title)

    def draw_single_sim(self, title, defdata, mode=2):
        """
            绘制通用的高频卡模拟的输入UI
        :return:
        """
        self.draw_top_title(title)
        # 绘制底色框
        self._canvas.create_rectangle(10, 80, 230, 120, fill="#DDDDDD", outline="", width=0)
        # 绘制输入hint
        self._canvas.create_text((40, 100), font=resources.get_font(15), width=230, text="UID:")
        # 绘制输入法
        im = widget.InputMethods(self._canvas, (68, 88), 25, defdata=defdata, mode=mode)
        self.input_methods.append(im)

    def draw_hf_sim_4b(self, title):
        """
            绘制通用的4BUID高频卡模拟的输入UI
        :return:
        """
        return self.draw_single_sim(title, "12345678")

    def draw_hf_sim_7b(self, title):
        """
            绘制通用的4BUID高频卡模拟的输入UI
        :return:
        """
        return self.draw_single_sim(title, "123456789ABCDE")

    def draw_lf_sim_4b(self, title):
        """
            绘制通用的4BUID低频卡模拟的输入UI
        :return:
        """
        return self.draw_single_sim(title, "AAAAAAAA")

    def draw_lf_sim_5b(self, title):
        """
            绘制通用的5BUID低频卡模拟的输入UI
        :return:
        """
        return self.draw_single_sim(title, "1234567890")

    def draw_lf_jablotron(self, title):
        """
            绘制通用的5BUID低频卡模拟的输入UI
        :return:
        """
        return self.draw_single_sim(title, "4294967295", mode=1)

    def draw_pos_arrow(self, tag_attach):
        """
            根据指定存在的控件的tag获取该控件
            然后获得控件的坐标
            然后绘制一个指示箭头在其后面
        :param tag_attach:
        :return:
        """
        tags = self.unique_id("pos_arrow")
        self._canvas.delete(tags)
        xy_g = self._canvas.coords(tag_attach)
        if len(xy_g) == 0:
            return
        y = xy_g[1] + (xy_g[3] - xy_g[1]) / 2
        self._canvas.create_text((xy_g[2] + 13, y), font=resources.get_font(20), width=230, text="<", tags=tags)

    def create_tags_for_inputmethod(self, index):
        return self.unique_id("i" + str(index))

    def create_tags_for_inputmethods(self):
        return self.create_tags_for_inputmethod(len(self.input_methods))

    def draw_pos_arrow_for_selection(self):
        self.draw_pos_arrow(self.create_tags_for_inputmethod(self.input_method_selection))

    def draw_lf_awid(self, title):
        """
            绘制awid需要用上的UI
        :param title:
        :return:
        """
        self.draw_top_title(title)

        # 绘制底色框
        self._canvas.create_rectangle(40, 80, 200, 110, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((88, 95), font=resources.get_font(15), width=230, text="Format:")
        im1 = widget.InputMethods(self._canvas, (166, 82), 25, defdata="50", mode=1)
        self.input_methods.append(im1)

        self._canvas.create_rectangle(40, 120, 200, 150, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 135), font=resources.get_font(15), width=230, text="FC:")
        im2 = widget.InputMethods(self._canvas, (148, 122), 25, defdata="2001", mode=1)
        self.input_methods.append(im2)

        self._canvas.create_rectangle(40, 160, 200, 190, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 175), font=resources.get_font(15), width=230, text="CN:")
        im3 = widget.InputMethods(self._canvas, (112, 162), 25, defdata="13371337", mode=1)
        self.input_methods.append(im3)

        self.draw_pos_arrow_for_selection()

    def draw_lf_io(self, title):
        """
            绘制awid需要用上的UI
        :param title:
        :return:
        """
        self.draw_top_title(title)

        # 绘制底色框
        self._canvas.create_rectangle(40, 80, 200, 110, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((88, 95), font=resources.get_font(15), width=230, text="Format:")
        im1 = widget.InputMethods(self._canvas, (166, 82), 25, defdata="01", mode=1, usefill=True)
        self.input_methods.append(im1)

        self._canvas.create_rectangle(40, 120, 200, 150, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 135), font=resources.get_font(15), width=230, text="FC:")
        im2 = widget.InputMethods(self._canvas, (166, 122), 25, defdata="FF")
        self.input_methods.append(im2)

        self._canvas.create_rectangle(40, 160, 200, 190, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 175), font=resources.get_font(15), width=230, text="CN:")
        im3 = widget.InputMethods(self._canvas, (139, 162), 25, defdata="65535", mode=1, usefill=True)
        self.input_methods.append(im3)

        self.draw_pos_arrow_for_selection()

    def draw_lf_gporx(self, title):
        """
            绘制awid需要用上的UI
        :param title:
        :return:
        """
        self.draw_top_title(title)

        # 绘制底色框
        self._canvas.create_rectangle(40, 80, 200, 110, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((88, 95), font=resources.get_font(15), width=230, text="Format:")
        im1 = widget.InputMethods(self._canvas, (166, 82), 25, defdata="26", mode=1, usefill=True)
        self.input_methods.append(im1)

        self._canvas.create_rectangle(40, 120, 200, 150, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 135), font=resources.get_font(15), width=230, text="FC:")
        im2 = widget.InputMethods(self._canvas, (158, 122), 25, defdata="255", mode=1, usefill=True)
        self.input_methods.append(im2)

        self._canvas.create_rectangle(40, 160, 200, 190, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 175), font=resources.get_font(15), width=230, text="CN:")
        im3 = widget.InputMethods(self._canvas, (139, 162), 25, defdata="65535", mode=1, usefill=True)
        self.input_methods.append(im3)

        self.draw_pos_arrow_for_selection()

    def draw_lf_pyramid(self, title):
        """
            绘制awid需要用上的UI
        :param title:
        :return:
        """
        self.draw_top_title(title)

        # 绘制底色框
        self._canvas.create_rectangle(40, 80, 200, 110, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 95), font=resources.get_font(15), width=230, text="FC:")
        im1 = widget.InputMethods(self._canvas, (158, 82), 25, defdata="255", mode=1, usefill=True)
        self.input_methods.append(im1)

        self._canvas.create_rectangle(40, 120, 200, 150, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((65, 135), font=resources.get_font(15), width=230, text="CN:")
        im2 = widget.InputMethods(self._canvas, (140, 122), 25, defdata="65536", mode=1, usefill=True)
        self.input_methods.append(im2)

        self.draw_pos_arrow_for_selection()

    def draw_lf_fdx_animal(self, title):
        """
            绘制awid需要用上的UI
        :param title:
        :return:
        """
        self.draw_top_title(title)

        # 绘制底色框
        self._canvas.create_rectangle(20, 80, 200, 110, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((70, 95), font=resources.get_font(15), width=230, text="Country:")
        im1 = widget.InputMethods(self._canvas, (156, 82), 25, defdata="999", mode=1, usefill=True)
        self.input_methods.append(im1)

        self._canvas.create_rectangle(20, 120, 200, 150, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((43, 135), font=resources.get_font(15), width=230, text="NC:")
        im2 = widget.InputMethods(self._canvas, (76, 122), 25, defdata="112233445566", mode=1, usefill=True)
        self.input_methods.append(im2)

        self.draw_pos_arrow_for_selection()

    def draw_lf_fdx_data(self, title):
        """
            绘制awid需要用上的UI
        :param title:
        :return:
        """
        self.draw_lf_fdx_animal(title)

        self._canvas.create_rectangle(20, 160, 200, 190, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((84, 175), font=resources.get_font(15), width=230, text="Animal Bit:")
        im3 = widget.InputMethods(self._canvas, (156, 162), 25, defdata="16A", usefill=True)
        self.input_methods.append(im3)

    def draw_lf_nedap(self, title):
        """
            绘制awid需要用上的UI
        :param title:
        :return:
        """
        self.draw_top_title(title)

        # 绘制底色框
        self._canvas.create_rectangle(40, 80, 200, 110, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((88, 95), font=resources.get_font(15), width=230, text="Subtype:")
        im1 = widget.InputMethods(self._canvas, (166, 82), 25, defdata="15", mode=1, usefill=True)
        self.input_methods.append(im1)

        self._canvas.create_rectangle(40, 120, 200, 150, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((72, 135), font=resources.get_font(15), width=230, text="Code:")
        im2 = widget.InputMethods(self._canvas, (156, 122), 25, defdata="999", mode=1, usefill=True)
        self.input_methods.append(im2)

        self._canvas.create_rectangle(40, 160, 200, 190, fill="#DDDDDD", outline="", width=0,
                                      tags=self.create_tags_for_inputmethods())
        self._canvas.create_text((60, 175), font=resources.get_font(15), width=230, text="ID:")
        im3 = widget.InputMethods(self._canvas, (138, 162), 25, defdata="99999", mode=1, usefill=True)
        self.input_methods.append(im3)

        self.draw_pos_arrow_for_selection()

    def get_focus_im(self):
        """
            获得在焦点中的输入法
        :return:
        """
        for im in self.input_methods:
            if im.isfocuing():
                return im
        return None

    def switch_or_input(self, prev=False):
        """
            切换或者输入
        :return:
        """
        if self.isbusy():
            return False

        if self.toast.isShow():
            self.toast.cancel()

        if len(self.input_methods) == 0:
            return False

        # 取出焦点中的输入法
        focus_im = self.get_focus_im()

        # 没有的话我们直接移动输入法的最外层选择框
        if focus_im is None:
            # 判断当前的输入框有几个，只有一个的情况下不允许上下移动选择
            if len(self.input_methods) == 1:
                return False
            # 否则允许上下移动选择
            if prev:
                self.input_method_selection -= 1
                if self.input_method_selection < 0:
                    self.input_method_selection = len(self.input_methods) - 1
            else:
                self.input_method_selection += 1
                if self.input_method_selection >= len(self.input_methods):
                    self.input_method_selection = 0
            self.draw_pos_arrow_for_selection()
        else:
            # 有焦点，我们需要进行选择
            if prev:
                focus_im.upword()
            else:
                focus_im.downword()

        return True

    def focus_or_unfocus(self):
        """
            获得或者取消焦点的获得
        :return:
        """
        im = self.input_methods[self.input_method_selection]
        im.rollfocus()

    def switch_word_iffocus(self, left=False):
        """
            切换输入的字
        :return:
        """
        if self.isbusy():
            return False
        # 如果吐司存在，我们需要进行取消
        if self.toast.isShow():
            self.toast.cancel()
        # 获取当前的输入控件，进行输入切换
        im = self.get_focus_im()
        if im is None:
            return False
        # 进行左右移动光标
        if left:
            im.lastitem()
        else:
            im.nextitem()
        return True

    def get_all_input(self):
        """
            获得所有的输入
        :return:
        """
        ret = list()
        for im in self.input_methods:
            i_str = str(im.getdata())
            i_str = i_str.split("-")[-1]
            if len(i_str) == 0:
                i_str = "0"
            ret.append(i_str)
        return ret

    def onCreate(self):
        self.setTitle(self.text_simulation, (100, 20))
        self.pi.show()

    def showSniffingToast(self):
        """
            显示提示文本与播放音频
        :return:
        """
        audio.playSimulating()
        self.toast.show(self.text_simulating)

    def startSimForData(self, bundle):
        self.setbusy()
        typ = bundle["type"]
        # 来自外部的数据的解析实现函数
        pf = self.getSimMap()[typ][0]
        # 规定的参数个数
        pc = self.getSimMap()[typ][1]

        # 获得内部的指令
        item = None
        index = 0
        for typ_item in self.TYP_ITEMS:
            if typ_item[5] == typ:
                item = typ_item
                break
            index += 1
        if item is None:
            print("没有找到任何的相关模拟映射")
            return

        self.lv.selection(index)  # 自动选择一下视图

        cmd = item[1]
        dat = pf(bundle)
        self.showSimUi(item, dat)

        if len(dat) != pc:
            print("???: " + str(dat))
            self.toast.show(self.text_sim_valid_param)
            self.setidle()
            return

        self.showSniffingToast()
        self.disableButton(left=False, right=True)

        cmd = cmd.format(*dat)
        executor.startPM3Task(cmd, -1, self.onSim)

    def onData(self, bundle):
        """
            我们需要在以参数启动时解析sim传输
        :param bundle:
        :return:
        """
        self.startBGTask(lambda: self.startSimForData(bundle))

    @staticmethod
    def onSim(line):
        """
            在模拟时会有一些数据打印
        :param line:
        :return:
        """
        print("onSim() -> ", line)

    def on14ASimStop(self):
        """
            在14a种类的卡停止模拟时的操作
        :return:
        """
        self.start(SimulationTraceActivity)

    def startSim(self):
        """
            开始模拟
        :return:
        """
        print("*************开始模拟**************")
        item = self.TYP_ITEMS[self.lv.getSelection()]
        all_input = self.get_all_input()
        print("*************开始模拟1**************")
        chk_fun = item[3]
        if chk_fun is not None:
            if not chk_fun(all_input):
                self.setidle()
                print("参数检测不通过")
                return
        print("*************开始模拟2**************")
        cmd = item[1]
        cmd = cmd.format(*all_input)
        self.showSniffingToast()
        print("*************开始模拟3**************")
        self.disableButton(left=False, right=True)
        executor.startPM3Task(cmd, -1, self.onSim)

    def stopSim(self):
        """
            停止模拟
        :return:
        """
        self.sim_stopping = True
        self.toast.show(self.text_processing)
        hmi_driver.presspm3()
        action_on_stop = self.TYP_ITEMS[self.lv.getSelection()][4]
        if action_on_stop is not None:
            action_on_stop()
        self.toast.cancel()
        self.disableButton(left=True, right=False)
        self.sim_stopping = False
        self.setidle()

    def showSimUi(self, item, data=None):
        """
            显示开始模拟需要的UI
        :return:
        """
        item[2](item[0])  # 调用各个类型的卡单独实现的绘制函数
        lens_final = item[6]  # 取出每个参数对应的最大固定长度
        if data is not None:
            count = 0
            for data_item in data:
                ui_item = self.input_methods[count]
                ui_item.setdata(str(data_item).lstrip("0"), lens_final[count])
                count += 1

        self.lv.hide()
        self.pi.hide()
        self.setLeftButton(self.text_stop)
        self.setRightButton(self.text_start)
        self.setTitle(self.text_simulation)
        self.disableButton(right=False)

    def showListUI(self):
        """
            显示最初始的列表视图
        :return:
        """
        self.lv.show()
        self.pi.show()
        self.disableButton()

    def onKeyEvent(self, event):
        if event == keymap.ALL:
            if self.isbusy() or not self.lv.isShowing():
                return False
            self.finish()
            self.start(AutoCopyActivity)
            return True

        if event == keymap.POWER:
            if self.isbusy() and not self.sim_stopping:
                self.startBGTask(self.stopSim)
                return True
            if self.toast.isShow():
                self.toast.cancel()
                return True
            self.finish()
            return True

        if event == keymap.LEFT:
            if self.isbusy():
                return False
            if self.lv.isShowing():
                self.lv.next(nextPage=True)
                return True
            return self.switch_word_iffocus(True)

        if event == keymap.RIGHT:
            if self.isbusy():
                return False
            if self.lv.isShowing():
                self.lv.next(nextPage=True)
                return True
            return self.switch_word_iffocus()

        if event == keymap.UP:
            if self.isbusy():
                return False
            if self.lv.isShowing():
                self.lv.prev(True)
                return True
            return self.switch_or_input(True)

        if event == keymap.DOWN:
            if self.isbusy():
                return False
            if self.lv.isShowing():
                self.lv.next(True)
                return True
            return self.switch_or_input()

        if event == keymap.M1:
            if not self.isbusy() or self.sim_stopping or self.lv.isShowing():
                return False
            self.startBGTask(self.stopSim)
            return True

        if event == keymap.M2:
            if self.isbusy() or self.lv.isShowing():
                return False
            self.setbusy()
            self.startBGTask(self.startSim)
            return True

        if event == keymap.OK:
            if self.lv.isShowing():
                item = self.TYP_ITEMS[self.lv.getSelection()]
                self.showSimUi(item)
            else:
                # 列表没有出现，我们需要进行输入法焦点的获取与取消
                self.focus_or_unfocus()
            return True

        return False


class SnakeGameActivity(BaseActivity):
    """
        贪吃蛇游戏
    """

    @staticmethod
    def getManifest():
        # return {
        #     "index": -1,
        #     "infos": tuple(("Greedy Snake", images.load("snake.png")))
        # }
        return None

    def __init__(self, canvas):
        super().__init__(canvas)
        self.gs = games.GreedySnake(self.getCanvas())

    def onCreate(self):
        """
            绘制贪吃蛇
        :return:
        """
        self.setTitle(resources.get_str("snakegame"))

    def onKeyEvent(self, event):
        if event == keymap.OK:
            # OK键，一般用来控制游戏开始
            self.gs.start()
            return True

        if event == keymap.POWER:
            if self.gs.isrun():
                # 电源键，一般用来控制游戏结束
                self.gs.stop()
            else:
                self.finish()
            return True

        if self.gs.ispause():
            return False

        if event == keymap.UP:
            # 上键
            self.gs.direction(games.GreedySnake.UP)
            return
        if event == keymap.DOWN:
            # 下键
            self.gs.direction(games.GreedySnake.DOWN)
            return
        if event == keymap.LEFT:
            # 左键
            self.gs.direction(games.GreedySnake.LEFT)
            return
        if event == keymap.RIGHT:
            # 右键
            self.gs.direction(games.GreedySnake.RIGHT)
            return

        return False


class WipeTagActivity(AutoExceptCatchActivity):
    """
        清卡页面实现
        1、实现M1清卡
        2、实现T55XX清卡
    """

    text_wipe_tag, text_wipe_m1, text_wipe_t55xx, text_no_tag_found, text_rescan, text_wipe_block, text_chk_m1_dic = \
        resources.get_str(["wipe_tag", "wipe_m1", "wipe_t55xx", "no_tag_found", "rescan", "wipe_block", "ChkDIC"])

    text_processing, text_t55xx_checking, text_scanning, text_tag_fixing, text_tag_wiping, text_bcc_fix_failed = \
        resources.get_str(["processing", "t55xx_checking", "scanning", "tag_fixing", "tag_wiping", "bcc_fix_failed"])

    text_wipe_success, text_keys_check_failed, text_wipe_no_valid_keys, text_err_at_wiping, text_wipe_failed = \
        resources.get_str(["wipe_success", "keys_check_failed", "wipe_no_valid_keys", "err_at_wiping", "wipe_failed"])

    text_wipe = resources.get_str(["wipe", ])

    @staticmethod
    def getManifest():
        return {
            "index": 13,
            "infos": tuple((WipeTagActivity.text_wipe_tag, images.load("erase.png")))
        }

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)

        self.task_map = {
            self.text_wipe_m1: self.wipe_m1,
            self.text_wipe_t55xx: self.wipe_t5577,
        }
        self.item_raws = list(self.task_map.keys())

        self.lv = widget.ListView(canvas, (0, 40))
        self.toast = widget.Toast(canvas)
        self.progressbar = widget.ProgressBar(self.getCanvas(), (20, 210))
        self.progressbar.hide()

        self.default_b0 = "0102030404080400000000000000BEAF"

    def call_on_write_magic_m1(self, line):
        msg_regex = r"\[.\]wipe block ([0-9]+)"
        msg_content = re.search(msg_regex, line)
        if msg_content is not None:
            msg_content = msg_content.group(1)
            if len(msg_content) > 0:
                self.progressbar.setMessage(f"{self.text_wipe_block} {msg_content}")

    def call_on_write_std_m1(self, progress):
        max_progress = progress['max']
        cur_progress = int(((progress['progress']) / max_progress) * 100)
        self.progressbar.setMax(max_progress)
        self.progressbar.setProgress(cur_progress)
        self.progressbar.setMessage(f"{self.text_wipe_block} {cur_progress}%")

    def call_on_wipe_t55xx(self, progress):
        self.progressbar.setMax(progress['max'])
        self.progressbar.setProgress(progress['progress'])

    def wipe_magic_m1(self):
        """
            清除UID后门卡
        :return:
        """
        # 清卡成功的输出
        # Card wiped successfully
        self.progressbar.setProgress(50)
        executor.startPM3Task("hf mf cwipe", 28888, self.call_on_write_magic_m1)
        # print(executor.getPrintContent())
        self.progressbar.setProgress(80)
        return 1 if executor.hasKeyword("Card wiped successfully") else -3

    def wipe_std_m1(self, infos):
        """
            清除标准的M1卡
        :return:
        """
        # 清普通的卡，我们首先需要进行
        # 1、秘钥的chk
        # 2、扇区的迭代写入
        # 如果没有传入卡片的size，那我们要根据信息来自动获取
        size = hfmfread.sizeGuess(infos['type'])
        self.progressbar.setMessage(self.text_chk_m1_dic)
        if hfmfkeys.fchks(infos, size, False):
            # print("秘钥检索完成")
            self.progressbar.setProgress(99)
            if hfmfkeys.hasAllKeys(size):
                # 开始迭代清除扇区
                # 生成新的空的数据
                data_empty = hfmfread.createTempDatas(size, infos)
                if hfmfwrite.write_with_standard(self.call_on_write_std_m1, data_empty, size):
                    return 1
                else:
                    # 返回-3表示写为空卡时出现了一些非常严重的错误
                    return -3
            else:
                # 返回 -2 表示没有获取到完整的秘钥
                return -2
        else:
            # 返回 -1 表示chk秘钥失败
            return -1

    def wipe_m1(self):
        """
            清除和修复M1卡的实现
        :return:
        """
        # 当一个卡被写坏时，寻卡将会出现：
        #   BCC0 incorrect
        # 所以我们需要进行特殊的照顾
        self.progressbar.setProgress(10)
        self.progressbar.setMessage(self.text_scanning)

        next_wipe = True
        wipe_ret = 0
        # 先进行卡片搜索
        scan_14a_ret = scan.scan_14a()
        tag_found = scan.isTagFound(scan_14a_ret)
        # 是否有发现14A协议的卡片
        if tag_found:
            # 判断有没有校验位异常的问题
            if scan_14a_ret.get("bbcErr"):
                next_wipe = False
                self.progressbar.setProgress(20)
                self.progressbar.setMessage(self.text_tag_fixing)
                # 尝试发送指令修复卡片
                executor.startPM3Task(f"hf mf csetblk 0 {self.default_b0}", 3000)

                # 然后我们需要进行重新搜索
                scan_14a_ret = scan.scan_14a()
                tag_found = scan.isTagFound(scan_14a_ret)
                if tag_found:
                    if scan_14a_ret.get("bbcErr"):
                        self.toast.show(self.text_bcc_fix_failed, mode=widget.Toast.MASK_FULL)
                    else:
                        next_wipe = True

            # 判断能不能进行下一步的清卡操作
            if next_wipe:
                self.progressbar.setProgress(30)
                self.progressbar.setMessage(self.text_tag_wiping)
                # 在这个步骤的时候，我么已经可以清卡了，我们可以看看是要清啥卡
                # 比如，我们要清UID后门卡，那就直接清
                if scan_14a_ret.get('gen1a'):  # 可以直接清后门卡
                    wipe_ret = self.wipe_magic_m1()
                else:  # 我们需要进行秘钥迭代，看能不能获取到全部秘钥，再去清卡
                    wipe_ret = self.wipe_std_m1(scan_14a_ret)

        # 在全部的清卡操作完成后，我们需要取消进度条的显示
        self.progressbar.hide()
        self.toast.show(self.text_processing, mode=widget.Toast.MASK_FULL)

        # 当wipe结果为1时，代表wipe成功
        if wipe_ret == 1:

            # 清卡完成后，重新寻卡，然后看看能不能寻到卡
            scan_14a_ret = scan.scan_14a()
            tag_found = scan.isTagFound(scan_14a_ret)

            if tag_found:
                typ = scan_14a_ret['type']
                if typ in tagtypes.getM1Types():
                    # 我们可以显示一些信息在页面上
                    template.draw(typ, scan_14a_ret, self.getCanvas())
                    wipe_ret = 1
                else:
                    wipe_ret = -3
            else:
                wipe_ret = -4

        if wipe_ret == 1:
            self.toast.show(self.text_wipe_success)
        elif wipe_ret == -1:
            # chk秘钥失败了
            self.toast.show(self.text_keys_check_failed)
        elif wipe_ret == -2:
            # 没有获取到完整的秘钥记录，这个卡可能要破解
            self.toast.show(self.text_wipe_no_valid_keys)
        elif wipe_ret == -3:
            # 在wipe的过程发声了一些未知的错误，wipe失败了
            self.toast.show(self.text_err_at_wiping)
        else:
            # 先判断初始化失败是不是因为卡片丢失
            if not tag_found:
                self.toast.show(self.text_no_tag_found)
            else:
                self.toast.show(self.text_wipe_failed)

        self.setLeftButton(self.text_wipe)
        self.setRightButton(self.text_wipe)

        self.setidle()

    def wipe_t5577(self):
        """
            清空T5577的卡片
        :return:
        """
        self.progressbar.setMessage(self.text_t55xx_checking)
        self.progressbar.setProgress(38)
        # 开始清卡
        wipe_ret = lft55xx.wipe1(self.call_on_wipe_t55xx)
        # 结束后隐藏进度条
        self.progressbar.hide()

        self.toast.show(self.text_processing, mode=widget.Toast.MASK_FULL)

        if wipe_ret:
            scan_ret = scan.scan_t55xx()
            typ = scan_ret['type']
            if scan.isTagFound(scan_ret) and typ == tagtypes.T55X7_ID:
                template.draw(typ, scan_ret, self.getCanvas())
                wipe_ret = True
            else:
                wipe_ret = False

        if wipe_ret:
            self.toast.show(self.text_wipe_success)
        else:
            self.toast.show(self.text_wipe_failed)

        self.setLeftButton(self.text_wipe)
        self.setRightButton(self.text_wipe)
        self.setidle()

    def start_wipe(self):
        """
            启动清卡的任务
        :return:
        """
        template.dedraw(self.getCanvas())
        self.toast.cancel()
        self.dismissButton()
        self.progressbar.hide()
        call_fn = self.task_map[self.item_raws[self.lv.getSelection()]]
        if callable(call_fn):
            self.startBGTask(call_fn)
            return True
        else:
            return False

    def onCreate(self):
        self.setTitle(self.text_wipe_tag)

        item_titles = []

        for index in range(len(self.item_raws)):
            item_titles.append(f"{index + 1}. {self.item_raws[index]}")
        self.lv.setItems(item_titles)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if self.isbusy():
                return False
            if self.toast.isShow():
                self.toast.cancel()
                return True
            if not self.lv.isShowing():
                template.dedraw(self.getCanvas())
                self.dismissButton()
                self.lv.show()
                return True
            self.finish()
            return True

        if event == keymap.UP:
            if self.isbusy() or not self.lv.isShowing():
                return False
            self.lv.prev(True)
            return True

        if event == keymap.DOWN:
            if self.isbusy() or not self.lv.isShowing():
                return False
            self.lv.next(True)
            return True

        if event in [keymap.OK, keymap.M1, keymap.M2]:
            if self.isbusy():
                print("当前有清卡任务正在进行中...")
                return False
            if event != keymap.OK and self.lv.isShowing():
                # 不是OK键的话，仅仅在选择了清卡项目之后才能反应
                return False

            self.setbusy()
            self.lv.hide()

            if self.start_wipe():
                return True

            self.setidle()
            return False

        return False


class TimeSyncActivity(AutoExceptCatchActivity):
    """
        时间同步的活动
    """

    text_time_sync, text_processing, text_edit, text_cancel, text_save, text_time_syncing, text_time_syncok = \
        resources.get_str(["time_sync", "processing", "edit", "cancel", "save", "time_syncing", "time_syncok"])

    @staticmethod
    def getManifest():
        return {
            "index": 14,
            "infos": tuple((TimeSyncActivity.text_time_sync, images.load("time.png")))
        }

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)

        self.toast = widget.Toast(canvas)

        self.serial_port = None
        self.need_resp = False
        self.sync = False

        self.year = 2021
        self.month = 7
        self.day = 16
        self.hour = 18
        self.second = 1

        self.tags_arrow = self.unique_id("TimeSyncActivity.arrow_im_selection")

        # 定义五个坐标，分别计算在五个输入法的下面
        self.arrow_pos = {
            0: (60, 111),
            1: (123, 111),
            2: (178, 111),
            3: (72, 172),
            4: (123, 172),
            5: (174, 172),
        }

        self.im_year = None
        self.im_month = None
        self.im_day = None
        self.im_hour = None
        self.im_minute = None
        self.im_second = None

        self.widget_arrow = None

        self.im_selection = 0

        self.im_list = []

        self.editing = False

    def onCreate(self):
        self.setTitle(self.text_time_sync)
        self.init_views()

    def init_views(self):
        """
            初始化视图
        :return:
        """
        # 绘制底色框
        self.getCanvas().create_rectangle(20, 60, 220, 100, fill="#E5E5E5", outline="", width=0,
                                          tags=self.unique_id("TimeSyncActivity._InputMethod_BG1"))

        self.im_year = widget.InputMethods(self._canvas, (38, 68), 25, defdata="2021", mode=1, highlight_feature=False)

        self.getCanvas().create_text((98, 78), text="-", font=("Consolas", 23), fill="white")

        self.im_month = widget.InputMethods(self._canvas, (108, 68), 25, defdata="07", mode=1, highlight_feature=False)

        self.getCanvas().create_text((150, 78), text="-", font=("Consolas", 23), fill="white")

        self.im_day = widget.InputMethods(self._canvas, (164, 68), 25, defdata="16", mode=1, highlight_feature=False)

        # 绘制底色框
        self.getCanvas().create_rectangle(48, 120, 198, 160, fill="#E5E5E5", outline="", width=0,
                                          tags=self.unique_id("TimeSyncActivity._InputMethod_BG2"))

        self.im_hour = widget.InputMethods(self._canvas, (58, 128), 25, defdata="14", mode=1, highlight_feature=False)

        self.getCanvas().create_text((99, 138), text=":", font=("宋体", 18), fill="white")

        self.im_minute = widget.InputMethods(self._canvas, (108, 128), 25, defdata="30", mode=1,
                                             highlight_feature=False)

        self.getCanvas().create_text((149, 138), text=":", font=("宋体", 18), fill="white")

        self.im_second = widget.InputMethods(self._canvas, (159, 128), 25, defdata="30", mode=1,
                                             highlight_feature=False)

        # 绘制指向箭头
        self.widget_arrow = self.getCanvas().create_text(self.arrow_pos[0], text="^", font=("Consolas", 18),
                                                         tags=self.tags_arrow)

        self.im_list.append(self.im_year)
        self.im_list.append(self.im_month)
        self.im_list.append(self.im_day)
        self.im_list.append(self.im_hour)
        self.im_list.append(self.im_minute)
        self.im_list.append(self.im_second)

        self.setRightButton(self.text_edit)
        self.setLeftButton(self.text_edit)

        self.edit_arrow_enable(self.editing)

    def get_im_focus(self):
        """
            获得有焦点的输入法
        :return:
        """
        if self.im_year.isfocuing():
            return self.im_year
        if self.im_month.isfocuing():
            return self.im_month
        if self.im_day.isfocuing():
            return self.im_day

        if self.im_hour.isfocuing():
            return self.im_hour
        if self.im_minute.isfocuing():
            return self.im_minute
        if self.im_second.isfocuing():
            return self.im_second

        return None

    def im_selection_up_down(self):
        """
            输入法选择的光标上下跳
        :return:
        """
        if self.get_im_focus() is not None:
            return False

        if self.im_selection > 2:
            self.im_selection -= 3
        else:
            self.im_selection += 3

        self.getCanvas().coords(self.widget_arrow, self.arrow_pos[self.im_selection])

        return True

    def im_selection_left_right(self, left=True):
        """
            输入法选择的光标上下跳
        :return:
        """
        if self.get_im_focus() is not None:
            return False

        if left:
            self.im_selection -= 1
            if self.im_selection < 0:
                self.im_selection = len(self.arrow_pos) - 1
        else:
            self.im_selection += 1
            if self.im_selection > len(self.arrow_pos) - 1:
                self.im_selection = 0

        self.getCanvas().coords(self.widget_arrow, self.arrow_pos[self.im_selection])

        return True

    def next_prev_item_if_focus(self, next_item=True):
        im: widget.InputMethods = self.im_list[self.im_selection]
        if im.isfocuing():
            if next_item:
                im.nextitem()
            else:
                im.lastitem()

    def get_max_min(self, im_selection):
        """
            暂时不适用
            最好是最后判断输入
        """
        # 计算每个输入法的输入上限和下限
        if im_selection == 0:  # 年
            max_value = 2038
            min_value = 1971
            len_value = 4
        elif im_selection == 1:  # 月
            max_value = 12
            min_value = 1
            len_value = 2
        elif im_selection == 2:  # 日
            try:
                # 取出年和月
                year = int(self.im_list[0].getdata())
                month = int(self.im_list[1].getdata())
                if month == 1 or month == 3 or month == 5 or month == 7 or month == 8 or month == 10 or month == 12:
                    max_value = 31
                elif month == 4 or month == 6 or month == 9 or month == 11:
                    max_value = 30
                elif month == 2 and ((year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)):
                    max_value = 29
                else:
                    max_value = 28
            except Exception as e:
                print(e)
                max_value = 28
            min_value = 1
            len_value = 2
        elif im_selection == 3:  # 时
            max_value = 23
            min_value = 0
            len_value = 2
        elif im_selection == 4:  # 分
            max_value = 59
            min_value = 0
            len_value = 2
        elif im_selection == 5:  # 秒
            max_value = 59
            min_value = 0
            len_value = 2
        else:
            raise Exception("不被允许的选中项")
        return tuple((max_value, min_value, len_value))

    def up_down_word_if_focus(self, down_word=True):
        im: widget.InputMethods = self.im_list[self.im_selection]

        value_int = int(im.getdata())
        if down_word:
            value_int -= 1
        else:
            value_int += 1

        # 我们需要自动格式化为对应的位数，补零
        max_value, min_value, len_value = self.get_max_min(self.im_selection)
        if value_int > max_value and not down_word:
            return False
        if value_int < min_value and down_word:
            return False

        value_str = ('{:0' + f'{len_value}' + 'd}').format(value_int)
        im.setdata(value_str)

        # 我们还需要处理，当前月份变动时，天数也不同的问题
        if self.im_selection == 1 or self.im_selection == 0:
            max_value = self.get_max_min(2)[0]
            self.im_list[2].setdata('{:02d}'.format(max_value))

        return True

    def run_time_flow(self):
        """
            时间流逝
        :return:
        """
        while self.need_resp:

            if not self.editing:  # 仅仅不需要编辑的时候才手动更新
                localtime = time.localtime(time.time())
                # 进行时间跳动
                self.im_year.setdata("{:04d}".format(localtime.tm_year))
                self.im_month.setdata("{:02d}".format(localtime.tm_mon))
                self.im_day.setdata("{:02d}".format(localtime.tm_mday))
                self.im_hour.setdata("{:02d}".format(localtime.tm_hour))
                self.im_minute.setdata("{:02d}".format(localtime.tm_min))
                self.im_second.setdata("{:02d}".format(localtime.tm_sec))

            time.sleep(1)

    def edit_arrow_enable(self, enable):
        """
            使能与否，编辑模式指示箭头
        :param enable:
        :return:
        """
        if enable:
            state = NORMAL
        else:
            state = HIDDEN
        self.getCanvas().itemconfig(self.widget_arrow, state=state)

    def same_chk(self):
        """
            可以复用的检测，检测结果不为空则有有效检测过程
        :return:
        """
        if self.sync:
            return False

        if self.toast.isShow():
            self.toast.cancel()
            return True

        return None

    def onKeyEvent(self, event):
        # 通用检测逻辑，在做某些重要操作时，不允许按键操作
        ret = self.same_chk()
        if ret is not None:
            return ret

        if event == keymap.POWER:
            self.finish()
            return True

        if event == keymap.UP:
            if not self.editing:
                return False

            return self.up_down_word_if_focus(False)

        if event == keymap.DOWN:
            if not self.editing:
                return False

            return self.up_down_word_if_focus(True)

        if event == keymap.LEFT:
            if not self.editing:
                return False

            self.im_selection_left_right(True)
            return True

        if event == keymap.RIGHT:
            if not self.editing:
                return False

            self.im_selection_left_right(False)
            return True

        if event == keymap.M1 or event == event == keymap.M2:
            if self.editing:
                self.editing = False
                self.setRightButton(self.text_edit)
                self.setLeftButton(self.text_edit)

                # 只有在M2按键的时候，才去保存
                if event == keymap.M2:
                    self.startBGTask(self.run_sync_time_self)
            else:
                self.editing = True
                self.setLeftButton(self.text_cancel)
                self.setRightButton(self.text_save)

            self.edit_arrow_enable(self.editing)
            return True

        return False

    def run_sync_time_self(self):
        """
            手动同步时间
        :return:
        """
        try:

            self.toast.show(self.text_time_syncing, mode=widget.Toast.MASK_FULL)
            self.sync = True

            time_str = "{}-{}-{}-{}-{}-{}".format(
                self.im_year.getdata(),
                self.im_month.getdata(),
                self.im_day.getdata(),
                self.im_hour.getdata(),
                self.im_minute.getdata(),
                self.im_second.getdata(),
            )
            time_tup = time.strptime(time_str, "%Y-%m-%d-%H-%M-%S")
            self.sync_time_to_system(time_tup)

        finally:
            # 显示对话框提醒用户
            self.toast.show(self.text_time_syncok, mode=widget.Toast.MASK_FULL)
            # 结束同步，使能一些事件相应
            self.sync = False

    @staticmethod
    def sync_time_to_system(timetuple):
        """
            系统时间同步，从STM32中获取
        :return:
        """
        if timetuple is not None:
            try:
                cmd1 = f'sudo date -s "{timetuple.tm_year}-{timetuple.tm_mon}-{timetuple.tm_mday}'
                cmd1 += f' {timetuple.tm_hour}:{timetuple.tm_min}:{timetuple.tm_sec + 1}"'
                # 通知PM3进行指令执行
                resp = executor.startPM3Plat(cmd1)
                print("同步时间到H3成功: ", resp.strip())

                time_stamp = int(time.mktime(timetuple))
                if time_stamp >= 4294967295:
                    print("淦，我这个开发者都死了你还能运行，肯定科技树点满了，快复活我。")
                    return

                print("正在尝试同步时间到HMI端")

                # 啊，我们加载时间同步吗？
                # 时间同步功能仅仅在下位机固件版本 1.0 以上，而且不包括 1.0 的固件中才被支持
                if not version.is_rtc_support():
                    print("固件版本过低，可能没有时间RTC的API，同步时间到HMI失败！")
                else:
                    hmi_driver.setrtc(time_stamp + 1)
                    print("同步时间到HMI成功！")

            except Exception as e:
                print(e)
        else:
            print("传入时间组为空，同步失败！")

        print("")

        return

    def run_serial_listener(self):
        """
            执行串口的监听任务
        :return:
        """
        self.serial_port = vsp_tools.open_serial()
        while self.need_resp:
            try:
                if self.serial_port is None or not self.need_resp:
                    break

                # 开始读取数据
                #  print("正在尝试读取行....")
                line = self.serial_port.readline()
                if line is None:
                    print("读取到了指针为空的数据，可能是串口被关闭。")
                    continue
                line = line.decode().strip()
                if line is None or len(line) == 0:
                    time.sleep(0.1)
                    continue
                print("取行到一行指令: ", line)

                # 响应出厂请求SN状态的指令
                if line == "SN_GET":
                    self.serial_port.write(f"{version.getSN()}\r\n".encode())
                elif line == "ARE_YOU_ICOPY?":
                    try:
                        self.serial_port.write(b"YES!ICOPY!\r\n")
                        self.toast.show(self.text_time_syncing, mode=widget.Toast.MASK_FULL)
                        self.sync = True
                    except Exception as e:
                        print(e)
                elif line.startswith("time="):
                    try:
                        time_str = line[5:]
                        time_tup = time.strptime(time_str, "%Y-%m-%d-%H-%M-%S")
                        # 这里直接同步到H3的系统时间中
                        self.sync_time_to_system(time_tup)
                        # 无论如何都要回复上位机
                        self.serial_port.write(b"SET!TIME!OK!\r\n")
                    except Exception as e:
                        print(e)
                    finally:
                        # 显示对话框提醒用户
                        self.toast.show(self.text_time_syncok, mode=widget.Toast.MASK_FULL)
                        # 结束同步，使能一些事件相应
                        self.sync = False
            except Exception as e:
                print("时间同步页面在接收数据时出现了异常: ", e)
                # 仅仅在还需要继续回复上位机的时候，继续尝试打开串口
                if self.need_resp:
                    self.serial_port = vsp_tools.open_serial()
                time.sleep(0.1)

        try:
            self.serial_port.close()
        except Exception as e:
            print(e)

        return

    def onResume(self):
        """
            在运行的时候
        :return:
        """
        super().onResume()

        if platform.system() == "Windows":
            print("Windows下不能启动监听")
            return

        try:
            if not self.need_resp:
                self.need_resp = True
                self.startBGTask(self.run_serial_listener)
                self.startBGTask(self.run_time_flow)
                print("启动自动同步事件监听成功")
        except Exception as e:
            print(e)

    def onDestroy(self):
        """
            在关闭页面的时候，我们需要关闭串口
        :return:
        """
        super().onDestroy()

        if platform.system() == "Windows":
            print("Windows下不能启动监听")
            return

        try:
            if self.need_resp:
                self.need_resp = False
                self.serial_port.close()
                print("关闭自动同步事件监听成功")
        except Exception as e:
            print(e)


class IClassSEActivity(AutoExceptCatchActivity):
    """
        IClassSe的读页面单独实现
    """

    text_processing, text_write, text_se_decoder, text_device_disconnected, text_plz_remove_device, text_tips = \
        resources.get_str(["processing", "write", "se_decoder", "device_disconnected", "plz_remove_device",
                           "iclass_se_read_tips"])

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)

        self.toast = widget.Toast(canvas)
        self.connected = True
        self.run_tag_listener = True
        self.exit_listener = False
        self.first_rd = True

        self.dev_port = None
        self.tag = None

        self.widget_tips = None

        # 默认清除旧的搜索缓存
        scan.clearScanCahe()

    def onCreate(self):
        self.setTitle(self.text_se_decoder)

        self.widget_tips = self.getCanvas().create_text((120, 120), text=self.text_tips, font=resources.get_font(15),
                                                        width=235, justify=CENTER)

        # 启动读卡逻辑
        self.startBGTask(self.onSEReader)

    def onSEReader(self):
        """
            读卡器读卡逻辑
        :return:
        """
        while self.run_tag_listener:

            time.sleep(0.1)

            if self.dev_port is not None:
                # 此处需要处理查询ttyGS0是否存在的问题
                if os.path.exists(self.dev_port):
                    # 设备依旧存在，我们可以继续进行下一步
                    print("设备存在，不需要重新初始化")
                else:
                    self.dev_port = None
                    # 串口发生变动，我们需要重新初始化读卡器
                    self.first_rd = True
                    continue
            else:
                # 先搜索SE的读头
                self.dev_port = hficlass.search_se_dev_reader()
                if self.dev_port is None:
                    # 如果没有读头，我们需要处理这个情况
                    # 比如通知用户
                    if self.connected:
                        self.toast.show(self.text_device_disconnected, mode=widget.Toast.MASK_FULL)
                        self.connected = False
                        self.first_rd = True
                    continue
                else:
                    if not self.connected:
                        self.connected = True
                        self.toast.cancel()

            # 然后开始搜索卡片
            tag = hficlass.search_se_tag_reader(self.dev_port, self.first_rd)
            # 成功初始化一次读头后，我们需要关闭下次初始化
            self.first_rd = False
            if tag is not None:
                # 隐藏提示语
                self.getCanvas().itemconfig(self.widget_tips, state=HIDDEN)
                # 搜索到卡片之后，我们就可以
                # 1、显示卡片信息
                # 2、跳转到写卡页面
                template.dedraw(self.getCanvas())
                template.draw(tagtypes.ICLASS_SE, tag, self.getCanvas())

                self.setLeftButton(self.text_write)
                self.setRightButton(self.text_write)
                self.toast.cancel()

                print("SE卡片信息: ", tag)
                self.tag = tag
                # 缓存寻卡信息到全局域
                scan.setScanCache(tag)

            time.sleep(0.1)

        self.exit_listener = True

    def is_device_exists(self):
        """
            当前当前设备是否还存在
        :return:
        """
        return self.dev_port is not None and os.path.exists(self.dev_port)

    def wait_exit(self):
        """
            等待退出
        :return:
        """
        # 判断设备是否拔除
        if self.is_device_exists():
            self.toast.show(self.text_plz_remove_device, mode=widget.Toast.MASK_FULL)
        else:
            self.toast.show(self.text_processing, mode=widget.Toast.MASK_FULL)

        self.run_tag_listener = False

        # 等待线程退出
        while not self.exit_listener or self.is_device_exists():
            time.sleep(0.2)

        self.finish()
        self.setidle()
        return True

    def wait_exit_and_go_write(self):
        """
            等待退出和前往写卡
        :return:
        """
        self.wait_exit()
        self.start(WarningWriteActivity, self.tag)

    def onKeyEvent(self, event):

        if event == keymap.POWER:
            if self.isbusy():
                return False
            if self.toast.isShow():
                self.toast.cancel()
                return True

            self.setbusy()
            self.startBGTask(self.wait_exit)
            return True

        if event == keymap.M1 or event == keymap.M2:
            if self.isbusy() or self.tag is None:
                return False
            self.setbusy()
            self.startBGTask(self.wait_exit_and_go_write)
            return True

        return False


class WearableDeviceActivity(BaseActivity):
    """
        写入卡片到穿戴式设备的实现
        由于需要媒介卡，因此写卡逻辑需要大改
        1、手持机先写UID到媒介卡（不写卡秘钥，卡数据）
        2、穿戴式设备去读取模拟媒介卡
        3、手持机去写穿戴式设备的密码区
        4、完成。
    """

    text_writing, text_cancel, text_finish, text_start, text_write_success, text_write_failed, text_write_wearable = \
        resources.get_str(["writing", "cancel", "finish", "start", "write_success", "write_failed", "write_wearable"])

    text_write_wearable_tips1, text_write_wearable_tips2, text_write_wearable_tips3, text_start_clone_uid = \
        resources.get_str(["write_wearable_tips1", "write_wearable_tips2", "write_wearable_tips3", "start_clone_uid"])

    text_unknown_error, text_write_wearable_err1, text_write_wearable_err2, text_write_wearable_err3 = \
        resources.get_str(["unknown_error", "write_wearable_err1", "write_wearable_err2", "write_wearable_err3", ])

    text_write_wearable_err4 = \
        resources.get_str(["write_wearable_err4", ])

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)

        self.setTitle(self.text_write_wearable)

        self.items_tips = [
            self.text_write_wearable_tips1,
            self.text_write_wearable_tips2,
            self.text_write_wearable_tips3
        ]
        self.lv = widget.BigTextListView(canvas, (0, 40), self.items_tips)

        self.pi = widget.PageIndicator(canvas, self.tags_title)
        self.pi.setBottomIndicatorEnable(True)
        self.pi.setLoop(True)

        self.lv.setOnPageChangeCall(self.onMultiPIUpdate)

        self.toast = widget.Toast(canvas)
        self.progress = widget.ProgressBar(canvas, (20, 210))
        self.progress.setMessage(self.text_writing)
        self.progress.hide()

        self.setLeftButton(self.text_cancel)
        self.setupBtnAtItemChange()

        # 将会传过来的写卡成功后的一些生成的数据封装
        self._bundle = None

        # 获取信息缓存
        self.infos = scan.getScanCache()

    def onMultiPIUpdate(self, page_max, page_new):
        self.setupBtnAtItemChange()

        # 启用在列表页的指示器的底部标志
        self.pi.setBottomIndicatorEnable(True)
        self.pi.update(page_max, page_new)

    def setupBtnAtItemChange(self):
        """
            自动切换按钮的文本
        :return:
        """
        item_selection = self.lv.getSelection()
        if item_selection == 0 or item_selection == 2:
            self.setRightButton(self.text_start)
        else:
            self.setRightButton(self.text_finish)

    def on_wearable_write_call(self, data):
        """
            在写手环时的回调
        :param data:
        :return:
        """
        # print("写手环: ", data)
        self.progress.setMax(data['max'])
        self.progress.setProgress(data['progress'])

    def write_uid_to_container(self):
        """
            只写UID到空白卡
        :return:
        """
        try:
            self.disableButton()
            self.toast.show(self.text_start_clone_uid)

            ret = hfmfwrite.write_only_uid_unlimited(self.infos)
            if ret != 1:  # 如果UID到媒介卡失败的话，我们需要提示用户
                cause = self.text_unknown_error

                if ret == -9:
                    cause = self.text_write_wearable_err1
                elif ret == -11:
                    cause = self.text_write_wearable_err2
                elif ret == -10:
                    cause = self.text_write_wearable_err3

                self.toast.show(cause)
            else:  # 如果直接写成功了，我们需要校验一下
                ret = hfmfwrite.verify_only_uid(self.infos)
                if ret != 1:  # 没有通过的话需要通知用户
                    self.toast.show(self.text_write_wearable_err4)
                else:  # 通过以后直接自动进入下一步
                    self.toast.cancel()
                    self.lv.next()
        except Exception as e:
            print(e)
        finally:
            self.disableButton(False, False)
            self.setidle()

    def write_dat_to_wearable(self):
        """
            写数据和密码到可穿戴式设备
        :return:
        """
        try:
            self.dismissButton()
            self.progress.show()

            # 开始进行写卡
            ret = hfmfwrite.write_only_blank(
                self.on_wearable_write_call,
                self.infos['type'],
                self._bundle
            )

            if ret:
                self.toast.show(self.text_write_success)
            else:
                self.toast.show(self.text_write_failed)

        finally:
            self.dismissButton(False, False)
            self.progress.hide()
            self.setidle()

    def onData(self, bundle):
        self._bundle = bundle

    def onKeyEvent(self, event):
        if self.isbusy():
            # 不允许繁忙的时候做任何操作
            return False

        if event == keymap.POWER or event == keymap.M1:
            if self.toast.isShow():
                self.toast.cancel()
                return True
            self.finish()
            return True

        if event == keymap.UP or event == keymap.LEFT:
            # 回到上一个步骤
            self.lv.prev(True)
            return True

        if event == keymap.DOWN or event == keymap.RIGHT:
            # 去下一个步骤
            self.lv.next(True)
            return True

        if event == keymap.M2:
            item_selection = self.lv.getSelection()
            if item_selection == 0:
                self.setbusy()
                self.startBGTask(self.write_uid_to_container)
            elif item_selection == 1:  # 在手环自模拟步骤（第二步）时，完成按钮可以直接调到下个步骤
                self.lv.next()
            elif item_selection == 2:  # 如果是第一步和第三步，都需要做出对应的实际写卡操作
                self.setbusy()
                self.startBGTask(self.write_dat_to_wearable)
            else:
                print("开发者是否实现了一些步骤但是没有对接实际逻辑，请务必检查！")
            return True

        return False


class ReadFromHistoryActivity(AutoExceptCatchActivity):
    """
        从读卡历史中加载数据的activity
    """

    text_tag_info, text_simulate, text_write,  = \
        resources.get_str(
            ["tag_info", "simulate", "write", ])

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)

        self.setTitle(self.text_tag_info)

        self.type = tagtypes.UNSUPPORTED
        self.info = {}
        self.file = ""

        self.write_map = {
            # M1卡系列的通用写卡实现
            tagtypes.M1_MINI        : self.write_file_base,
            tagtypes.M1_PLUS_2K     : self.write_file_base,
            tagtypes.M1_S50_1K_4B   : self.write_file_base,
            tagtypes.M1_S50_1K_7B   : self.write_file_base,
            tagtypes.M1_S70_4K_4B   : self.write_file_base,
            tagtypes.M1_S70_4K_7B   : self.write_file_base,

            # MFU的标签的通用写卡实现
            tagtypes.ULTRALIGHT     : self.write_file_base,
            tagtypes.ULTRALIGHT_C   : self.write_file_base,
            tagtypes.ULTRALIGHT_EV1 : self.write_file_base,
            tagtypes.NTAG213_144B   : self.write_file_base,
            tagtypes.NTAG215_504B   : self.write_file_base,
            tagtypes.NTAG216_888B   : self.write_file_base,

            # ID卡卡号系列的通用写卡实现
            tagtypes.EM410X_ID      : self.write_id,
            tagtypes.HID_PROX_ID    : self.write_id,
            tagtypes.INDALA_ID      : self.write_id,
            tagtypes.IO_PROX_ID     : self.write_id,
            tagtypes.AWID_ID        : self.write_id,
            tagtypes.GPROX_II_ID    : self.write_id,
            tagtypes.SECURAKEY_ID   : self.write_id,
            tagtypes.VIKING_ID      : self.write_id,
            tagtypes.PYRAMID_ID     : self.write_id,
            tagtypes.FDXB_ID        : self.write_id,
            tagtypes.GALLAGHER_ID   : self.write_id,
            tagtypes.JABLOTRON_ID   : self.write_id,
            tagtypes.KERI_ID        : self.write_id,
            tagtypes.NEDAP_ID       : self.write_id,
            tagtypes.NORALSY_ID     : self.write_id,
            tagtypes.PAC_ID         : self.write_id,
            tagtypes.PARADOX_ID     : self.write_id,
            tagtypes.PRESCO_ID      : self.write_id,
            tagtypes.VISA2000_ID    : self.write_id,
            tagtypes.NEXWATCH_ID    : self.write_id,

            # 以dump写低频卡卡实现
            tagtypes.T55X7_ID       : self.write_lf_dump,
            tagtypes.EM4305_ID      : self.write_lf_dump,

            # 以dump写15693实现
            tagtypes.ISO15693_ICODE : self.write_file_base,
            tagtypes.ISO15693_ST_SA : self.write_file_base,
        }
        self.simulate_map = {
            # M1卡的模拟过程
            tagtypes.M1_S50_1K_4B   : self.sim_for_info,
            tagtypes.M1_S70_4K_4B   : self.sim_for_info,

            # MFU的模拟过程
            tagtypes.ULTRALIGHT     : self.sim_for_info,
            tagtypes.NTAG215_504B   : self.sim_for_info,

            # ID卡模拟过程
            tagtypes.EM410X_ID      : self.sim_for_info,
            tagtypes.HID_PROX_ID    : self.sim_for_info,
            tagtypes.VIKING_ID      : self.sim_for_info,
            tagtypes.FDXB_ID        : self.sim_for_info,
            tagtypes.JABLOTRON_ID   : self.sim_for_info,
        }

    def sim_for_info(self):
        """
            模拟m1卡的1k4b的实现
        :return:
        """
        self.start(SimulationActivity, self.info)

    def write_file_base(self):
        """
            写M1卡的跳转实现
        :return:
        """
        scan.setScanCache(self.info)
        file = os.path.splitext(self.file)[0]
        self.start(WarningWriteActivity, file)

    def write_id(self):
        """
            写普通ID卡的跳转实现
        :return:
        """
        scan.setScanCache(self.info)
        self.start(WarningWriteActivity, self.info)

    def write_lf_dump(self):
        """
            写T55XX的全DUMP的跳转实现
        :return:
        """
        scan.setScanCache(self.info)
        # 务必保证文件是.bin的存在
        file = os.path.splitext(self.file)[0]
        file = file + ".bin"
        self.start(WarningWriteActivity, {'file': file})

    def get_type(self, file: str):
        """
            根据当前的文件类型，返回对应卡片的类型码
        :param file: 文件名
        :return:
        """
        print("操作的文件是: " + file)
        file_infos = file.split("_")
        prefix = file_infos[0]
        if prefix.startswith("M1"):
            infos = CardWalletActivity.parseInfoByM1FileName(file)
            size = infos['size']
            uid_len = infos['uid_len']
            if size == 'Mini':
                return tagtypes.M1_MINI
            if size == '1K':
                if uid_len == "4B":
                    return tagtypes.M1_S50_1K_4B
                if uid_len == "7B":
                    return tagtypes.M1_S50_1K_7B
            if size == '2K':
                return tagtypes.M1_PLUS_2K
            if size == '4K':
                if uid_len == "4B":
                    return tagtypes.M1_S70_4K_4B
                if uid_len == "7B":
                    return tagtypes.M1_S70_4K_7B

        # 非特殊类型，直接从映射表中获得类型
        return {
            # mfu标签
            appfiles.PREFIX_NAME_UL         : tagtypes.ULTRALIGHT,
            appfiles.PREFIX_NAME_ULC        : tagtypes.ULTRALIGHT_C,
            appfiles.PREFIX_NAME_UL_EV1     : tagtypes.ULTRALIGHT_EV1,
            appfiles.PREFIX_NAME_NTAG213    : tagtypes.NTAG213_144B,
            appfiles.PREFIX_NAME_NTAG215    : tagtypes.NTAG215_504B,
            appfiles.PREFIX_NAME_NTAG216    : tagtypes.NTAG216_888B,

            # 15693标签
            appfiles.FILE_PREFIX_ICODE      : tagtypes.ISO15693_ICODE,

            # 低频卡可DUMP
            appfiles.FILE_PREFIX_T55XX      : tagtypes.T55X7_ID,
            appfiles.FILE_PREFIX_EM4X05     : tagtypes.EM4305_ID,

            # 低频卡不可dump
            appfiles.FILE_PREFIX_EM410X     : tagtypes.EM410X_ID,
            appfiles.FILE_PREFIX_HIDPROX    : tagtypes.HID_PROX_ID,
            appfiles.FILE_PREFIX_INDALA     : tagtypes.INDALA_ID,
            appfiles.FILE_PREFIX_AWID       : tagtypes.AWID_ID,
            appfiles.FILE_PREFIX_IOPROX     : tagtypes.IO_PROX_ID,
            appfiles.FILE_PREFIX_GPROXII    : tagtypes.GPROX_II_ID,
            appfiles.FILE_PREFIX_SECURAKEY  : tagtypes.SECURAKEY_ID,
            appfiles.FILE_PREFIX_VIKING     : tagtypes.VIKING_ID,
            appfiles.FILE_PREFIX_PYRAMID    : tagtypes.PYRAMID_ID,
            appfiles.FILE_PREFIX_FDX        : tagtypes.FDXB_ID,
            appfiles.FILE_PREFIX_GALLAGHER  : tagtypes.GALLAGHER_ID,
            appfiles.FILE_PREFIX_JABLOTRON  : tagtypes.JABLOTRON_ID,
            appfiles.FILE_PREFIX_KERI       : tagtypes.KERI_ID,
            appfiles.FILE_PREFIX_NEDAP      : tagtypes.NEDAP_ID,
            appfiles.FILE_PREFIX_NORALSY    : tagtypes.NORALSY_ID,
            appfiles.FILE_PREFIX_PAC        : tagtypes.PAC_ID,
            appfiles.FILE_PREFIX_PARADOX    : tagtypes.PARADOX_ID,
            appfiles.FILE_PREFIX_PRESCO     : tagtypes.PRESCO_ID,
            appfiles.FILE_PREFIX_VISA2000   : tagtypes.VISA2000_ID,
            appfiles.FILE_PREFIX_NEXWATCH   : tagtypes.NEXWATCH_ID,
        }[prefix]

    def get_info(self, typ, file_base, file_full):
        """
            从文件中读取标签的一些必要的信息
        :param typ: 标签的类型
        :param file_base: 文件的基础名称
        :param file_full: 文件的全路径
        :return: 读取到的标签信息
        """
        ret = {}
        # 专门处理M1卡
        if typ in tagtypes.getM1Types():
            infos = CardWalletActivity.parseInfoByM1FileName(file_base)
            uid_len = infos['uid_len']
            ret['uid'] = infos['uid_hex']
            if uid_len == "4B":
                ret['len'] = 4
                ret['sak'] = '08'
                ret['atqa'] = '0004'
            if uid_len == "7B":
                ret['len'] = 7
                ret['sak'] = '18'
                ret['atqa'] = '0044'

        if typ in tagtypes.getULTypes():
            infos = CardWalletActivity.parseInfoByUIDInfoFileName(file_base)
            ret['uid'] = infos['uid']

        if typ in tagtypes.getAllLowNoDump():  # 低频卡
            infos = CardWalletActivity.parseInfoByIDFileName(file_base)
            ret['data'] = infos['data']
            ret['raw'] = appfiles.read_text(file_full)

        if typ == tagtypes.T55X7_ID:
            infos = CardWalletActivity.parseInfoByT55xxInfoFileName(file_base)
            ret['b0'] = infos['b0']
            ret['modulate'] = "--------"
            ret['chip'] = "T55xx/Unknown"

        if typ == tagtypes.EM4305_ID:
            infos = CardWalletActivity.parseInfoByUIDInfoFileName(file_base)
            ret['sn'] = infos['uid']
            try:
                with open(file_full, mode="rb") as fd:
                    bs = fd.read()
                    cw_bs = bs[16:20]
                    ret['cw'] = cw_bs.hex()
            except Exception as e:
                print(e)
                ret['cw'] = "read cw fail"
            ret['chip'] = "EM4305"

        if typ == tagtypes.ISO15693_ICODE or typ == tagtypes.ISO15693_ST_SA:
            infos = CardWalletActivity.parseInfoByUIDInfoFileName(file_base)
            ret['uid'] = infos['uid']

        ret['found'] = True
        ret['type'] = typ
        return ret

    def onData(self, bundle):
        # 获得基础信息
        self.file = bundle
        base_file = os.path.basename(bundle)
        self.type = self.get_type(base_file)
        self.info = self.get_info(self.type, base_file, bundle)
        # 绘制标签的信息
        template.draw(self.type, self.info, self.getCanvas())
        # 设置下方按键
        self.setLeftButton(self.text_simulate)
        self.setRightButton(self.text_write)
        left_btn_enable = self.type in self.simulate_map
        right_btn_enable = self.type in self.write_map
        self.disableButton(not left_btn_enable, not right_btn_enable)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            self.finish()
            return True
        if event == keymap.M1:
            if self.type in self.simulate_map:
                self.simulate_map[self.type]()
                return True
            else:
                return False
        if event == keymap.M2:
            if self.type in self.write_map:
                self.write_map[self.type]()
                return True
            else:
                return False
        return False


class CardWalletActivity(AutoExceptCatchActivity):
    """
        卡包列表
    """

    text_card_wallet, text_cancel, text_confirm, text_del_confirm, text_opera_unsupported, text_delete, = \
        resources.get_str(["card_wallet", "no", "yes", "delete_confirm", "opera_unsupported", "delete", ])

    text_no_tag_history, text_details = \
        resources.get_str(
            ["no_tag_history", "details", ])

    @staticmethod
    def getManifest():
        return {
            "index": 1,
            "infos": tuple((CardWalletActivity.text_card_wallet, images.load("list.png")))
        }

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)
        self.setTitle(self.text_card_wallet, (100, 20))

        # 首页第一级菜单，显示卡片目录
        self.lvCards = widget.ListView(canvas, (0, 40))

        # 首页第二级菜单，显示dump目录
        self.lvDumps = widget.ListView(canvas, (0, 40))
        self.lvDumps.setDisplayItemMax(4)
        self.lvDumps.hide()

        self.pageIndicator = widget.PageIndicator(canvas, self.tags_title)
        self.pageIndicator.setBottomIndicatorEnable(False)

        # 显示提示
        self.toast = widget.Toast(canvas)

        # 数据为空提示
        self.tags_tips_txt = self.unique_id("txt_tips")
        self._canvas.create_text(
            (40, 100),
            font=resources.get_font(16),
            fill="#1C6AEB",
            justify=LEFT,
            anchor="nw",
            tags=self.tags_tips_txt
        )

        # 存放dump的列表
        self.list_dump = []

        # 标志当前是否空数据
        self.is_dump_list_empty = False
        # 标签当前是否显示日期信息
        self.is_dump_show_date = False
        # 标志当前是否在删除数据
        self.is_dump_del_mode = False

        # 取出读卡历史列表
        dir_list_ret, typ_list_ret = appfiles.get_card_list()
        self.list_dir: list = dir_list_ret
        self.list_typ: list = typ_list_ret
        for i in range(len(typ_list_ret)):
            typ_list_ret[i] = f'{i + 1}'.rjust(2) + f". {typ_list_ret[i]}"

        if len(typ_list_ret) > 0:
            self.is_card_list_empty = False
            self.lvCards.setItems(typ_list_ret)
        else:
            self.is_card_list_empty = True
            self.setTipsTxt(self.text_no_tag_history)

        self.lvDumps.setOnPageChangeCall(self.onMultiPIUpdate)
        self.lvCards.setOnPageChangeCall(self.onMultiPIUpdate)

        if self.is_card_list_empty:
            self.pageIndicator.hide()

        # 加载文件信息的映射表
        self.load_available = [
            # M1卡系列
            appfiles.DIR_NAME_M1,
            # MFU系列
            appfiles.DIR_NAME_MFU,
            # 15693系列
            appfiles.DIR_NAME_ICODE,

            # T55XX
            appfiles.DIR_NAME_T55XX,
            # RM4X05
            appfiles.DIR_NAME_EM4X05,

            # ID卡操作系列
            appfiles.DIR_NAME_EM410x,
            appfiles.DIR_NAME_HID,
            appfiles.DIR_NAME_INDALA,
            appfiles.DIR_NAME_AWID,
            appfiles.DIR_NAME_IOPROX,
            appfiles.DIR_NAME_GPROXII,
            appfiles.DIR_NAME_SECURAKEY,
            appfiles.DIR_NAME_VIKING,
            appfiles.DIR_NAME_PYRAMID,
            appfiles.DIR_NAME_FDX,
            appfiles.DIR_NAME_GALLAGHER,
            appfiles.DIR_NAME_JABLOTRON,
            appfiles.DIR_NAME_KERI,
            appfiles.DIR_NAME_NEDAP,
            appfiles.DIR_NAME_NORALSY,
            appfiles.DIR_NAME_PAC,
            appfiles.DIR_NAME_PARADOX,
            appfiles.DIR_NAME_PRESCO,
            appfiles.DIR_NAME_VISA2000,
            appfiles.DIR_NAME_NEXWATCH,
        ]

    def onMultiPIUpdate(self, page_max, page_new):
        # 启用在列表页的指示器的底部标志
        self.pageIndicator.setBottomIndicatorEnable(self.lvDumps.isShowing())
        self.pageIndicator.update(page_max, page_new)

    def setTipsTxt(self, tips=None):
        """
            设置某些提醒文本
        :param tips:
        :return:
        """
        if tips is not None:
            self.getCanvas().itemconfig(
                self.tags_tips_txt,
                text=tips,
                state=NORMAL,
            )
        else:
            self.getCanvas().itemconfig(
                self.tags_tips_txt,
                text=tips,
                state=HIDDEN,
            )

    @staticmethod
    def parseInfoByM1FileName(file_name):
        sea_obj = re.search(r"M1-(\S+)-(\S+)_([A-Fa-f\d]+)_(\d+).*\.(.*)", file_name)
        return {
            'size': sea_obj.group(1),
            'uid_len': sea_obj.group(2),
            'uid_hex': sea_obj.group(3),
            'index': sea_obj.group(4),
            'suffix': sea_obj.group(5),
        }

    @staticmethod
    def parseInfoByIDFileName(file_name):
        sea_obj = re.search(r"(\S+)_(\S+)_(\d+)\.(.*)", file_name)
        return {
            'name': sea_obj.group(1),
            'data': sea_obj.group(2),
            'index': sea_obj.group(3),
            'suffix': sea_obj.group(4),
        }

    @staticmethod
    def parseInfoByUIDInfoFileName(file_name):
        sea_obj = re.search(r"(\S+)_(\S+)_(\d+).*\.(.*)", file_name)
        return {
            'name': sea_obj.group(1),
            'uid': sea_obj.group(2),
            'index': sea_obj.group(3),
            'suffix': sea_obj.group(4),
        }

    @staticmethod
    def parseInfoByT55xxInfoFileName(file_name):
        sea_obj = re.search(r"(\S+)_(\S+)_(\S+)_(\S+)_(\d+).*\.(.*)", file_name)
        return {
            'name': sea_obj.group(1),
            'b0': sea_obj.group(2),
            'b1': sea_obj.group(3),
            'b2': sea_obj.group(4),
            'index': sea_obj.group(5),
            'suffix': sea_obj.group(6),
        }

    @staticmethod
    def parseInfoByLegicInfoFileName(file_name):
        sea_obj = re.search(r"(\S+)_(\S+)-(\S+)_(\d+).*\.(.*)", file_name)
        return {
            'name': sea_obj.group(1),
            'mcd': sea_obj.group(2),
            'msn': sea_obj.group(3),
            'index': sea_obj.group(4),
            'suffix': sea_obj.group(5),
        }

    def getKeyInfo(self, dir_name, file_name):
        if dir_name == appfiles.DIR_NAME_M1:
            info_dict = self.parseInfoByM1FileName(file_name)
            info_ret = f"{info_dict['size']}-{info_dict['uid_len']}-{info_dict['uid_hex']}({info_dict['index']})"
            return info_ret

        uid_format_list = [
            appfiles.DIR_NAME_HF14A,
            appfiles.DIR_NAME_EM4X05,
            appfiles.DIR_NAME_ICLASS,
            appfiles.DIR_NAME_ICODE,
            appfiles.DIR_NAME_MFU,
            appfiles.DIR_NAME_FELICA,
        ]
        if dir_name in uid_format_list:
            info_dict = self.parseInfoByUIDInfoFileName(file_name)
            info_ret = f"{info_dict['uid']}({info_dict['index']})"
            return info_ret

        if dir_name == appfiles.DIR_NAME_T55XX:
            info_dict = self.parseInfoByT55xxInfoFileName(file_name)
            info_ret = f"{info_dict['b0']}({info_dict['index']})"
            return info_ret

        if dir_name == appfiles.DIR_NAME_LEGIC:
            info_dict = self.parseInfoByLegicInfoFileName(file_name)
            info_ret = f"{info_dict['mcd']}-{info_dict['msn']}({info_dict['index']})"
            return info_ret

        # ID卡操作的规范表
        lf_normal_ids = [
            appfiles.DIR_NAME_EM410x,
            appfiles.DIR_NAME_HID,
            appfiles.DIR_NAME_INDALA,
            appfiles.DIR_NAME_AWID,
            appfiles.DIR_NAME_IOPROX,
            appfiles.DIR_NAME_GPROXII,
            appfiles.DIR_NAME_SECURAKEY,
            appfiles.DIR_NAME_VIKING,
            appfiles.DIR_NAME_PYRAMID,
            appfiles.DIR_NAME_FDX,
            appfiles.DIR_NAME_GALLAGHER,
            appfiles.DIR_NAME_JABLOTRON,
            appfiles.DIR_NAME_KERI,
            appfiles.DIR_NAME_NEDAP,
            appfiles.DIR_NAME_NORALSY,
            appfiles.DIR_NAME_PAC,
            appfiles.DIR_NAME_PARADOX,
            appfiles.DIR_NAME_PRESCO,
            appfiles.DIR_NAME_VISA2000,
            appfiles.DIR_NAME_NEXWATCH,
        ]
        # 如果目标目录名称在ID规范存放列表内，则可以规范取出文件信息
        if dir_name in lf_normal_ids:
            info_dict = self.parseInfoByIDFileName(file_name)
            info_ret = f"{info_dict['data']}({info_dict['index']})"
            return info_ret

    def showDumps(self, selection=0, showdate=False):
        """
            根据当前选中的目录类型，显示对应目录中的的dump的列表
        :return:
        """
        # 先得到目录基础名称
        dir_name = self.list_dir[self.lvCards.getSelection()]
        path_dump = os.path.join(appfiles.PATH_DUMP, dir_name)
        dump_files = os.listdir(path_dump)

        def get_file(file_name):
            return os.path.join(path_dump, file_name)

        def get_ctime(file_sort):
            return os.path.getctime(get_file(file_sort))

        # 根据日期排序
        dump_files.sort(key=get_ctime)

        def date_format(file_path):
            timestamp = get_ctime(file_path)
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

        # 迭代处理文件列表
        dump_list = []
        show_list = []
        self.list_dump.clear()
        for file in dump_files:
            try:
                # 我们只允许.bin或者是.eml通过。
                file: str = file
                if file.endswith(".bin") or file.endswith(".eml") or file.endswith(".txt"):
                    key_info = self.getKeyInfo(dir_name, file)
                    if key_info not in dump_list:
                        dump_list.append(key_info)
                        # 根据需要，进行文件创建的日期显示或者是名称显示
                        if showdate:
                            show_list.append(date_format(file))
                        else:
                            show_list.append(key_info)
                        self.list_dump.append(file)
            except Exception:
                pass
                # 此处解析信息时出现了一些异常，我们应当直接进行跳过加载此文件。。。

        # 有数据才更新
        if len(show_list):
            # 更新到UI上
            self.lvDumps.setItems(show_list)
            self.lvDumps.selection(selection)
            self.setBtn2ListMode()
            self.is_dump_list_empty = False
        else:
            self.lvDumps.hide()
            self.setTipsTxt(self.text_no_tag_history)
            self.dismissButton()
            self.is_dump_list_empty = True

    def delDump(self):
        """
            删除选择的dump
        :return:
        """
        # 基础路径
        dir_name = self.list_dir[self.lvCards.getSelection()]
        path_dump: str = os.path.join(appfiles.PATH_DUMP, dir_name)

        # 取出文件
        dump_selection = self.lvDumps.getSelection()
        dump_file: str = self.list_dump[dump_selection]
        file_name: str = os.path.splitext(dump_file)[0]
        # 迭代所有的文件
        for file in os.listdir(path_dump):
            if file_name == os.path.splitext(file)[0]:
                file_path = os.path.join(path_dump, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(e)

        # 刷新UI
        if dump_selection - 1 >= 0:
            dump_selection = dump_selection - 1
        self.showDumps(dump_selection)

    def setBtn2ListMode(self):
        """
            设置按钮模式为列表模式
        :return:
        """
        self.setLeftButton(self.text_details)
        self.setRightButton(self.text_delete)

    def setBtn2DelMode(self):
        """
            设置按钮模式为删除文件模式
        :return:
        """
        self.setLeftButton(self.text_cancel)
        self.setRightButton(self.text_confirm)

    def showDetail(self):
        """
            显示标签详细信息
        :return:
        """
        # 先得到目录基础名称
        dir_name = self.list_dir[self.lvCards.getSelection()]
        path_dump = os.path.join(appfiles.PATH_DUMP, dir_name)
        file_path = os.path.join(path_dump, self.list_dump[self.lvDumps.getSelection()])
        if dir_name in self.load_available:
            # 跳转到读卡历史信息页面加载并且显示信息
            self.start(ReadFromHistoryActivity, file_path)
        else:
            self.toast.show(self.text_opera_unsupported)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            self.setTipsTxt()
            if self.toast.isShow():
                self.is_dump_del_mode = False
                self.toast.cancel()
                self.setBtn2ListMode()
                return True
            if self.lvDumps.isShowing():
                self.lvDumps.hide()
                self.lvCards.show()
                self.dismissButton()
            elif not self.lvCards.isShowing():
                self.lvCards.show()
                self.dismissButton()
            else:
                self.finish()
            return True

        if event == keymap.OK:
            if self.toast.isShow():
                return False
            # 点击确认显示dump列表
            if self.lvCards.isShowing():
                # 隐藏当前卡包目录列表
                self.lvCards.hide()
                # 显示文件列表
                self.showDumps()
                return True
            # 如果已经在列表里面，我们需要判断，是否有数据
            if not self.is_dump_list_empty:
                self.showDetail()
                return True
            return False

        if self.is_dump_list_empty and self.lvDumps.isShowing():
            print("数据为空，不允许多余的按键操作")
            return False

        if self.is_card_list_empty and self.lvCards.isShowing():
            print("卡片为空，不允许多余的按键操作")
            return False

        if event == keymap.M1:
            # 如果是toast显示状态，可能是删除文件进行中
            if self.toast.isShow():
                if self.is_dump_del_mode:
                    self.is_dump_del_mode = False
                    self.setBtn2ListMode()
                    self.toast.cancel()
                    return True
                else:
                    return False
            # 在dump列表显示时，左按钮是普通的详情功能，
            if self.lvDumps.isShowing():
                dump_selection = self.lvDumps.getSelection()
                self.is_dump_show_date = not self.is_dump_show_date
                self.showDumps(selection=dump_selection, showdate=self.is_dump_show_date)
                return True
            return False

        if event == keymap.M2:
            if self.toast.isShow():
                if self.is_dump_del_mode:
                    self.delDump()
                    self.is_dump_del_mode = False
                    self.setBtn2ListMode()
                    self.toast.cancel()
                    return True
                else:
                    return False
            else:
                if self.lvDumps.isShowing():
                    self.is_dump_del_mode = True
                    self.toast.show(self.text_del_confirm, mode=widget.Toast.MASK_TOP_CENTER)
                    self.setBtn2DelMode()
                    return True
                return False

        if event == keymap.DOWN:
            if self.toast.isShow():
                return False
            if self.lvCards.isShowing():
                self.lvCards.next(loop=True)
                return True
            if self.lvDumps.isShowing():
                self.lvDumps.next(loop=True)
                return True
            return False

        if event == keymap.UP:
            if self.toast.isShow():
                return False
            if self.lvCards.isShowing():
                self.lvCards.prev(loop=True)
                return True
            if self.lvDumps.isShowing():
                self.lvDumps.prev(loop=True)
                return True
            return False

        if event == keymap.LEFT:
            if self.toast.isShow():
                return False
            if self.lvCards.isShowing():
                self.lvCards.prev(prevPage=True)
                return True
            if self.lvDumps.isShowing():
                self.lvDumps.prev(prevPage=True)
                return True
            return False

        if event == keymap.RIGHT:
            if self.toast.isShow():
                return False
            if self.lvCards.isShowing():
                self.lvCards.next(nextPage=True)
                return True
            if self.lvDumps.isShowing():
                self.lvDumps.next(nextPage=True)
                return True
            return False

        return False


class LUAScriptCMDActivity(AutoExceptCatchActivity):
    """
        LUA脚本执行控制台
    """

    text_title = resources.get_str("lua_script")

    @staticmethod
    def getManifest():
        return {
            "index": -1,
            "infos": tuple((LUAScriptCMDActivity.text_title, images.load("script.png")))
        }

    def __init__(self, canvas: Canvas):
        super().__init__(canvas)

        # 指向Lua脚本源文件的目录
        self.path_lua_scripts = os.path.join(appfiles.PATH_MS, "luascripts")

        # 内置一个ACT，默认不显示，也就是后台活动
        self.console_activity = ConsolePrinterActivity(canvas, False)

        # 设置标题
        self.setTitle(self.text_title, (90, 20))

        # 顶部页标
        self.pageIndicator = widget.PageIndicator(canvas, self.tags_title)
        self.pageIndicator.setBottomIndicatorEnable(False)

        # 显示LUA列表
        self.lvLUAs = widget.ListView(canvas, (0, 40))
        self.lua_file_list = self.listLUAFiles()
        self.lvLUAs.setItems(self.lua_file_list)
        self.lvLUAs.setOnPageChangeCall(self.onMultiPIUpdate)

    def onMultiPIUpdate(self, page_max, page_new):
        self.pageIndicator.update(page_max, page_new)

    def listLUAFiles(self):
        """
            列出所有的可执行的LUA脚本的名称
        :return:
        """
        # 列出所有的文件
        files = os.listdir(self.path_lua_scripts)

        def is_lua(file: str):
            return file.endswith(".lua")

        # 进行过滤，非LUA文件不保存
        files = list(filter(is_lua, files))
        ret = []
        for file in files:
            ret.append(os.path.splitext(file)[0])
        return ret

    def onResume(self):
        super().onResume()
        executor.add_task_call(self.console_activity.on_exec_print)

    def onDestroy(self):
        super().onDestroy()
        executor.del_task_call(self.console_activity.on_exec_print)
        self.console_activity.onDestroy()

    def runScriptTask(self):
        """
            运行脚本任务
        :return:
        """
        if len(self.lua_file_list) > 0:
            # 先获得当前要执行的LUA的项目
            index = self.lvLUAs.getSelection()
            lua = self.lua_file_list[index]
            # 然后进行LUA任务执行
            executor.startPM3Task(f"script run {lua}", -1)
            print("执行结束！")

    def onKeyEvent(self, event):
        """
            按键事件触发的回调
        :param event:
        :return:
        """
        if self.console_activity.is_showing():
            if event == keymap.POWER:
                executor.stopPM3Task()
                self.console_activity.hidden()
                return True
            return self.console_activity.onKeyEvent(event)

        # ----------------------------------------------------------------
        #                     处理主页面显示的逻辑
        # M1和M2按键事件触发
        if event == keymap.M1 or event == keymap.M2 or event == keymap.OK:
            self.console_activity.clear()
            self.console_activity.show()
            self.startBGTask(self.runScriptTask)
            return True

        # 取消事件触发
        if event == keymap.POWER:
            self.finish()
            return True

        if event == keymap.DOWN:
            self.lvLUAs.next(loop=True)
            return True

        if event == keymap.UP:
            self.lvLUAs.prev(loop=True)
            return True

        if event == keymap.LEFT:
            self.lvLUAs.prev(prevPage=True)
            return True

        if event == keymap.RIGHT:
            self.lvLUAs.next(nextPage=True)
            return True

        return False
