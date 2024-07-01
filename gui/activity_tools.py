"""
    保存一些工具的活动页面
"""
import re
import time

import commons

import images
import keymap
import scan
import widget
import audio
import hmi_driver
import resources
import executor

from actbase import BaseActivity


class DiagnosisActivity(BaseActivity):
    """
        自我诊断
    """

    text_diagnosis, text_di1, text_di2, text_sdi1, text_sdi2, text_sdi3, text_sdi4, text_sdi5, text_sdi6, text_sdi7,\
    text_sdi8, text_sdi9, text_testing_with, text_start_diagnosis_tips, text_cancel, text_start = resources.get_str([
        "diagnosis", "diagnosis_item1", "diagnosis_item2",
        "diagnosis_subitem1", "diagnosis_subitem2", "diagnosis_subitem3", "diagnosis_subitem4","diagnosis_subitem5",
        "diagnosis_subitem6", "diagnosis_subitem7", "diagnosis_subitem8", "diagnosis_subitem9", "testing_with",
        "start_diagnosis_tips", "cancel", "start"
    ])

    @staticmethod
    def getManifest():
        return {
            "index": 8,
            "infos": tuple((DiagnosisActivity.text_diagnosis, images.load("diagnosis.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.main_lv = widget.ListView(canvas, (0, 40))
        self.main_pi = widget.PageIndicator(canvas, self.tags_title)
        self.main_pi.setBottomIndicatorEnable(False)
        self.main_lv.setOnPageChangeCall(self.main_pi.update)
        self.main_pi.hide()

        self.ITEMS_MAIN = [
            self.text_di1,
            self.text_di2,
        ]

        self.ITEMS_TEST = [
            # 参数配置：
            #  测试项标题
            #  测试结果
            #  测试的实现函数
            (
                self.text_sdi1,
                self.text_sdi1 + ": {}",
                self._test_hfvoltage),                           
            (
                self.text_sdi2,
                self.text_sdi2 + ": {}",
                self._test_lfvoltage),
            (
                self.text_sdi3,
                self.text_sdi3 + ": {}",
                self._test_hfreader),
            (
                self.text_sdi4,
                self.text_sdi4 + ": {}",
                self._test_lfreader),
            (
                self.text_sdi5,
                self.text_sdi5 + ": {}",
                self._flash_memtest),
            (
                self.text_sdi6,
                self.text_sdi6 + ": {}",
                self._usb_test),
            (
                self.text_sdi7,
                self.text_sdi7 + ": {}",
                self._button_test),
            (
                self.text_sdi8,
                self.text_sdi8 + ": {}",
                self._screen_test),
            (
                self.text_sdi9,
                self.text_sdi9 + ": {}",
                self._sound_test),
            # 工厂测试专用读卡机测试
            (
                self.text_sdi3,
                self.text_sdi3 + ": {}",
                self._test_hf_reader_factory
            ),
            (
                self.text_sdi4,
                self.text_sdi4 + ": {}",
                self._test_lf_reader_factory
            ),
        ]

        self.tags_diagnosis_tips = self.unique_id("tags_diagnosis_tips")
        self.label_result_showing = False
        self.label_item_testing = False
        self.label_item_result = False

    @staticmethod
    def _test_voltage(max_v, min_v, cmd):
        """
            使用指定的命令来检测电压值
        :param max_v: 上限的电压值，包括此值
        :param min_v: 下限的电压值，包括此值
        :param cmd:
        :return:
        """
        mvs = list()

        def newlines(line):
            print("接收到的电压测量行: ", line)
            sobj = re.search(r"/\s*(\d+)\s*V", line)
            if sobj is not None:
                numstr = sobj.group(1)
                if len(numstr) > 0:
                    mvs.append(int(numstr))
            if len(mvs) == 5:
                # 参考个数差不多够了，可以直接结束任务
                hmi_driver.presspm3()
                print("电压数据收集完成，可以结束任务。")

        # 直接执行
        executor.startPM3Task(cmd, 8888, newlines, rework_max=1)
        # 模拟pm3的按钮，进行任务取消
        hmi_driver.presspm3()

        if len(mvs) == 0:
            return "X (NV)"
        # 判断结果
        if max(mvs) > max_v:
            return "X ({}V)".format(round(max(mvs)))
        if min(mvs) < min_v:
            return "X ({}V)".format(round(min(mvs)))
        return "√ ({}V)".format(round(sum(mvs) / len(mvs)))

    def _test_reader(self, wait_ms, cmd):
        """
            测试读卡器是否工作正常
        :return:
        """
        if executor.startPM3Task(cmd, wait_ms) == -1:
            return "X (TO)"
        if hmi_driver.ledpm3() != 1:
            return "√"
        return "X"

    def _test_hfvoltage(self):
        """
            测试高频天线电压的实现
        :return:
        """
        return self._test_voltage(40, 32, "hf tune")

    def _test_lfvoltage(self):
        """
            测试低频天线电压的实现
        :return:
        """
        return self._test_voltage(53, 40, "lf tune")

    def _test_hfreader(self):
        """
            测试高频读卡器是否工作的实现
        :return:
        """
        return self._test_reader(5888, "hf 14a reader")

    def _test_lfreader(self):
        """
            测试低频读卡器是否工作的实现
        :return:
        """
        return self._test_reader(8888, "lf sea")

    def _flash_memtest(self):
        """
            测试PM3的flash工作是否正常
        :return:
        """

        # 首先，生成一个临时文件
        name = "test_pm3_mem.nikola"
        file = "/tmp/" + name
        commons.startPlatformCMD("sudo touch " + file)
        commons.startPlatformCMD("sudo echo A > " + file)
        # 上传文件到PM3
        if executor.startPM3Task("mem spiffs load f {} o {}".format(file, name), 5888) == -1:
            return "X (TO)"
        # 判断是否上传成功
        if not executor.hasKeyword(r"Wrote \d+ bytes to file"):
            return "X (U)"
        # 用清除文件的形式来判断
        if executor.startPM3Task("mem spiffs wipe", 5888) == -1:
            return "X (TO)"
        if executor.hasKeyword(name):
            return "√"

        # 删除临时文件
        commons.startPlatformCMD("sudo rm " + file)
        return "X (W)"

    def _manual_check(self, act, bundle=None):
        self.start(act, bundle)  # 先启动activity
        self.label_item_testing = True
        # 然后等待结果
        while self.label_item_testing:
            time.sleep(0.1)
        if self.label_item_result:
            return "√"
        return "X"

    def _screen_test(self):
        """
            屏幕测试
        :return:
        """
        return self._manual_check(ScreenTestActivity)

    def _sound_test(self):
        """
            音频测试
        :return:
        """
        return self._manual_check(SoundTestActivity)

    def _button_test(self):
        """
            按钮测试
        :return:
        """
        return self._manual_check(ButtonTestActivity)

    def _usb_test(self):
        """
            USB链路测试
        :return:
        """
        if self._manual_check(UsbPortTestActivity):
            if isinstance(self.label_item_result, bool):
                if self.label_item_result:
                    return "√"
                else:
                    return "X"

            if isinstance(self.label_item_result, list) or isinstance(self.label_item_result, tuple):
                if self.label_item_result[0]:
                    return "√"
                else:
                    return "X ({})".format(self.label_item_result[1])

        return "X (DEV)"

    def _test_hf_reader_factory(self):
        return self._manual_check(HFReaderTestActivity)

    def _test_lf_reader_factory(self):
        return self._manual_check(LfReaderTestActivity)

    def startTest(self):
        """
            开始测试，根据当前的测试实现
        :return:
        """
        if self.main_lv.getSelection() == 0:
            test_items = self.ITEMS_TEST[0:5]
        else:
            test_items = self.ITEMS_TEST[0:2]
            test_items.append(self.ITEMS_TEST[4])
            test_items.extend(self.ITEMS_TEST[9:11])
            test_items.extend(self.ITEMS_TEST[5:9])

        # 开始测试
        test_result = list()
        for item in test_items:
            # 取出实现的测试函数
            # print("测试项: ", item)
            test_impl = item[2]
            if test_impl is None:
                print("当前项未实现测试: ", item)
                continue
            # 大字报告当前的测试项目
            self.setTipsEnable(self.text_testing_with.format(item[0]))
            # 执行测试并且格式化测试结果
            test_result.append(item[1].format(test_impl()))

        print("测试结果: ", test_result)
        self.main_lv.setItems(test_result)
        self.updateTitle(True)
        self.main_pi.show()
        self.dismissButton()
        self.setTipsEnable(enable=False)
        self.setidle()
        self.label_result_showing = True

    def onData(self, bundle):
        """
            页面返回的时候是可以带数据的
        :param bundle:
        :return:
        """
        self.label_item_testing = False
        self.label_item_result = bundle

    def setTipsEnable(self, text=None, enable=True):
        """
            显示提示
        :return:
        """
        if text is None:
            text = self.text_start_diagnosis_tips

        if enable:
            state = "normal"
        else:
            state = "hidden"
        self.getCanvas().itemconfig(self.tags_diagnosis_tips, text=text, state=state)

    def updateTitle(self, force_pu_show=None):
        if force_pu_show is None:
            force_pu_show = self.main_pi.showing()
        if force_pu_show:
            self.setTitle(self.text_diagnosis, (100, 20,))
        else:
            self.setTitle(self.text_diagnosis, (120, 20,))

    def onCreate(self):
        self.updateTitle()
        self.main_lv.setItems(self.ITEMS_MAIN)
        self._canvas.create_text((120, 120), font=resources.get_font(15), fill="#1C6AEB",
                                 tags=self.tags_diagnosis_tips,
                                 state="hidden", width=230)

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if not self.isbusy():
                self.finish()
                return True
            return False

        if event == keymap.UP:
            if self.isbusy():
                return False
            self.main_lv.prev()
            return True

        if event == keymap.DOWN:
            if self.isbusy():
                return False
            self.main_lv.next()
            return True

        if event == keymap.OK:
            if self.label_result_showing or self.isbusy():
                return False
            self.main_lv.hide()
            self.main_pi.hide()
            self.setLeftButton(self.text_cancel)
            self.setRightButton(self.text_start)
            self.setTipsEnable(enable=True)
            return True

        if event == keymap.M1:
            if self.isbusy():
                return False
            self.finish()
            return True

        if event == keymap.M2:
            if self.isbusy() or self.main_lv.isShowing():
                return False
            self.setbusy()
            self.dismissButton()
            self.startBGTask(self.startTest)
            return True

        return False


class SoundTestActivity(BaseActivity):
    """
        音频测试活动UI
    """

    text_no, text_yes, text_test_music_tips = resources.get_str([
        "no", "yes", "test_music_tips"
    ])

    def onCreate(self):
        audio.playStartExma(force=True)

        self.setTitle(DiagnosisActivity.text_sdi9)
        self.setLeftButton(self.text_no)
        self.setRightButton(self.text_yes)

        self._canvas.create_text(
            (120, 120),
            font=resources.get_font(15),
            fill="#1C6AEB",
            width=230,
            text=self.text_test_music_tips
        )

    def finish(self, bundle=None):
        audio.stop()
        return super().finish(bundle)

    def onKeyEvent(self, event):
        if event == keymap.M1:
            self.finish(False)
            return True
        if event == keymap.M2:
            self.finish(True)
            return True

        return False


class ScreenTestActivity(BaseActivity):
    """
        音频测试活动UI
    """

    text_fail, text_pass, text_test_screen_tips, text_test_screen_isok_tips = resources.get_str([
        "fail", "pass", "test_screen_tips", "test_screen_isok_tips"
    ])

    def __init__(self, canvas):
        super().__init__(canvas)
        self.label_testing = False
        self.colors = [
            "red",
            "green",
            "blue",
            "black",
            "white"
        ]
        self.color_pos = 0
        self.label_tested = False

    def showBtns(self, enable):
        if enable:
            self.setLeftButton(self.text_fail)
            self.setRightButton(self.text_pass)
        else:
            self.dismissButton()

    def showTips(self, text=None, enable=True):
        """
            显示提示文本
        :param text:
        :param enable:
        :return:
        """
        tags = self.unique_id("tips")
        if enable:
            if text is None:
                tips_text = self.text_test_screen_tips
            else:
                tips_text = text
            self._canvas.create_text((120, 140), font=resources.get_font(15), fill="#1C6AEB", width=230,
                                     text=tips_text, tags=tags)
        else:
            self._canvas.delete(tags)

    def showBigBg(self, enable=True):
        tags = self.unique_id("big_bg")
        if enable:
            bgw = self._canvas.find_withtag(tags)
            if len(bgw) > 0:
                self._canvas.itemconfig(bgw, fill=self.colors[self.color_pos])
            else:
                self._canvas.create_rectangle(0, 0, 240, 240, fill=self.colors[self.color_pos], tags=tags,
                                              outline="", width=0)
        else:
            self._canvas.delete(tags)

    def onCreate(self):
        self.setTitle(DiagnosisActivity.text_sdi8)
        self.showTips()

    def resetColorPos(self, reset2End):
        """
            重置颜色的索引
        :return:
        """
        if self.color_pos >= len(self.colors) or self.color_pos < 0:
            if not reset2End:
                self.color_pos = 0
            else:
                self.color_pos = len(self.colors) - 1

    def onKeyEvent(self, event):
        if event == keymap.M1 and self.label_tested:
            self.finish(False)
            return True

        if event == keymap.M2 and self.label_tested:
            self.finish(True)
            return True

        if event == keymap.OK:
            self.showTips(enable=False)
            self.showBtns(False)
            if self.label_testing:  # 当前正在测试，我们需要关闭测试
                self.showBigBg(False)
                self.showTips(self.text_test_screen_isok_tips)
                self.showBtns(True)
                self.label_testing = False
                self.label_tested = True
                self._battery_bar.show()
            else:
                self._battery_bar.hide()  # 需要隐藏电量条
                self.showBigBg()
                self.label_testing = True
                self.label_tested = False
            return True

        if event == keymap.UP:
            if not self.label_testing: return False
            self.color_pos -= 1
            self.resetColorPos(True)
            self.showBigBg()
            return True

        if event == keymap.DOWN:
            if not self.label_testing: return False
            self.color_pos += 1
            self.resetColorPos(False)
            self.showBigBg()
            return True

        return False


class ButtonTestActivity(BaseActivity):
    """
        按钮测试活动页面
    """

    def __init__(self, canvas):
        super().__init__(canvas)
        self.btn_cache = {}
        self.btn_max = 9
        self.tags_timer = self.unique_id("auto_stop_timer")

    def auto_stop_run(self):
        """
            自动停止检测的任务
        :return:
        """
        second = 30
        while second > 0:
            if self.destroyed:
                return
            self._canvas.itemconfig(self.tags_timer, text=str(second))
            time.sleep(1)
            second -= 1
        # 自动返回失败
        self.finish(False)

    def onCreate(self):
        self.setTitle(DiagnosisActivity.text_sdi7)

        self._canvas.create_oval(23, 86, 50, 113, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.M1))  # M1
        self._canvas.create_oval(23, 176, 50, 204, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.POWER))  # POWER

        self._canvas.create_oval(68, 134, 95, 161, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.LEFT))  # LEFT

        self._canvas.create_oval(106, 100, 133, 127, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.UP))  # UP
        self._canvas.create_oval(106, 166, 133, 193, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.DOWN))  # DOWN

        self._canvas.create_oval(144, 134, 171, 161, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.RIGHT))  # RIGHT

        self._canvas.create_oval(189, 86, 217, 113, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.M2))  # M2
        self._canvas.create_oval(189, 176, 217, 204, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.ALL))  # ALL

        self._canvas.create_oval(106, 134, 134, 161, fill="#EEEEEE", outline="", width=0,
                                 tags=self.unique_id(keymap.OK))  # OK

        # 开启一个计时器
        self._canvas.create_text((120, 220), font=resources.get_font(20), fill="#1C6AEB", width=230,
                                 tags=self.tags_timer)
        self.startBGTask(self.auto_stop_run)

    def update_btn_state(self, key):
        """
            更新对应的按钮的UI状态
        :param key:
        :return:
        """
        tags = self.unique_id(key)
        self._canvas.itemconfig(tags, fill="#00FF00")
        self.btn_cache[key] = True

        if len(self.btn_cache) == self.btn_max:
            self.finish(True)

    def onKeyEvent(self, event):
        if event == keymap.M1:
            self.update_btn_state(event)
            return True
        if event == keymap.M2:
            self.update_btn_state(event)
            return True
        if event == keymap.POWER:
            self.update_btn_state(event)
            return True
        if event == keymap.LEFT:
            self.update_btn_state(event)
            return True
        if event == keymap.RIGHT:
            self.update_btn_state(event)
            return True
        if event == keymap.UP:
            self.update_btn_state(event)
            return True
        if event == keymap.DOWN:
            self.update_btn_state(event)
            return True
        if event == keymap.ALL:
            self.update_btn_state(event)
            return True
        if event == keymap.OK:
            self.update_btn_state(event)
            return True

        return False


class UsbPortTestActivity(BaseActivity):
    """
        USB测试的活动UI
    """

    text_test_usb_connect_tips, text_test_usb_found_tips, text_yes, text_no, text_test_usb_otg_tips = resources.get_str([
        "test_usb_connect_tips", "test_usb_found_tips", "yes", "no", "test_usb_otg_tips"
    ])

    def __init__(self, canvas):
        super().__init__(canvas)
        self.tags_tips = self.unique_id("tips_view")
        self.label_test_state = 0

    def run_check(self):
        """
            执行检测USB的相关功能
        :return:
        """
        msg = self.text_test_usb_connect_tips
        self.showTips(msg)
        second = 30
        while second > 0:
            if self.destroyed:
                return
            if hmi_driver.requestChargeState() == 1:
                # 充电插入
                self.showTips(self.text_test_usb_found_tips)
                self.setLeftButton(self.text_no)
                self.setRightButton(self.text_yes)
                self.label_test_state = 1
                return
            self.showTips(msg + "({})".format(second))
            time.sleep(1)
            second -= 1
        self.finishOnResult(False, "A")

    def showTips(self, text):
        self._canvas.itemconfig(self.tags_tips, text=text)

    def onCreate(self):
        self.setTitle(DiagnosisActivity.text_sdi6)
        self._canvas.create_text(
            (120, 120),
            font=resources.get_font(15),
            fill="#1C6AEB",
            width=230,
            tags=self.tags_tips,
        )
        self.startBGTask(self.run_check)

    def finishOnResult(self, is_pass, msg=None):
        self.finish([is_pass, msg])

    def onKeyEvent(self, event):
        if event == keymap.M1:
            if self.label_test_state == 1:
                self.finishOnResult(False, "B")
                return True

            if self.label_test_state == 2:
                self.finishOnResult(False, "C")
                return True
            return True

        if event == keymap.M2:
            if self.label_test_state == 1:
                # 显示第二个步骤
                self.showTips(self.text_test_usb_otg_tips)
                self.label_test_state = 2
                return True

            if self.label_test_state == 2:
                self.finishOnResult(True)
                return True
            return True

        return False


class HFReaderTestActivity(BaseActivity):
    """
        高频读卡机手动测试的项目
    """

    text_test_hf_reader_tips = resources.get_str("test_hf_reader_tips")

    def __init__(self, canvas):
        super().__init__(canvas)
        self.tags_tips = self.unique_id("tips_view")

    def showTips(self, text):
        if self.destroyed:
            return
        self._canvas.itemconfig(self.tags_tips, text=text)

    def run_check(self):
        """
            执行检测
        :return:
        """
        msg = self.text_test_hf_reader_tips
        self.showTips(msg)
        second = 8
        while second > 0:
            if self.destroyed:
                return
            scan_ret = scan.scan_14a()
            if scan.isTagFound(scan_ret) and not scan.isTagMulti(scan_ret):
                self.finish(True)
                return
            time.sleep(1)
            second -= 1
            self.showTips(msg + "({})".format(second))
        # 超时返回异常
        self.finish(False)

    def onCreate(self):
        self.setTitle(DiagnosisActivity.text_sdi3)
        self._canvas.create_text((120, 120), font=resources.get_font(15), fill="#1C6AEB", width=230,
                                 tags=self.tags_tips)
        self.startBGTask(self.run_check)

    def onKeyEvent(self, event):
        return False


class LfReaderTestActivity(BaseActivity):
    """
        高频读卡机手动测试的项目
    """

    text_test_lf_reader_tips = resources.get_str("test_lf_reader_tips")

    def __init__(self, canvas):
        super().__init__(canvas)
        self.tags_tips = self.unique_id("tips_view")
        self.label_found = False

    def showTips(self, text):
        if self.destroyed:
            return
        self._canvas.itemconfig(self.tags_tips, text=text)

    def run_check(self):
        """
            执行检测
        :return:
        """
        msg = self.text_test_lf_reader_tips
        self.showTips(msg)
        second = 8
        while second > 0:
            if self.destroyed:
                return
            # 检测是否搜索到，搜索到我们需要提前退出
            if self.label_found:
                self.finish(True)
            time.sleep(1)
            second -= 1
            self.showTips(msg + "({})".format(second))
        # 超时返回异常
        self.finish(False)

    def run_watch(self):
        """
            执行PM3的ID卡轮询检测
        :return:
        """

        def onWatchLine(line):
            """
                在监听到行更新时
            :param line:
            :return:
            """
            if "EM TAG ID" in line:
                # 发现卡片，直接关闭任务
                hmi_driver.presspm3()
                self.label_found = True

        cmd = "lf em 410x_watch"
        if executor.startPM3Task(cmd, 10888, onWatchLine) == -1:
            hmi_driver.presspm3()
            self.finish(False)
            return

    def onCreate(self):
        self.setTitle(DiagnosisActivity.text_sdi4)
        self._canvas.create_text((120, 120), font=resources.get_font(15), fill="#1C6AEB", width=230,
                                 tags=self.tags_tips)
        self.startBGTask(self.run_check)
        self.startBGTask(self.run_watch)

    def onKeyEvent(self, event):
        return False
