"""
    activity的主入口GUI
"""
import importlib
import inspect
import os
import platform
import shutil
import threading
import time
import psutil

import commons
import executor
import audio
import batteryui
import hmi_driver
import keymap
import resources
import settings
import update
import version
import vsp_tools
import widget

from actbase import BaseActivity


class MainActivity(BaseActivity):
    """
        主页面的入口活动，所有的活动的跳转基础
    """

    text_main_page, text_processing = resources.get_str([
        "main_page", "processing"
    ])

    def __init__(self, canvas):
        super().__init__(canvas)

        self.lv = widget.ListView(
            self.getCanvas(),
            resources.get_xy("lv_main_page"),
            text_size=resources.get_text_size("lv_main_page")
        )
        self.lv.listview_str_margin_left = resources.get_int("lv_main_page_str_margin")
        self.pi = widget.PageIndicator(self.getCanvas(), self.tags_title)
        self.toast = None

        self.info = None
        self.acts = None

        self.sleep_stop = False
        self.hibernation = False
        self.is_windows = platform.system() == "Windows"

        self.initializing = False

        self.serial_port = None
        self.need_resp = False
        self.exit_count = 0

    def onCreate(self):
        # 创建标题
        self.setTitle(self.text_main_page, (100, 20))
        # 开启中控初始化线程
        threading.Thread(target=self.init).start()

    @staticmethod
    def is_act_mod_name_start(n):
        return n.startswith("activity_")

    @staticmethod
    def is_act_clz_name_start(n):
        return n.endswith("Activity")

    @staticmethod
    def is_act_clz_name(n):
        if inspect.isclass(n):
            module_name = getattr(n, "__module__")
            class_name = getattr(n, "__name__")
            # 判断是否是Act模块或者Act类
            is_mod = MainActivity.is_act_mod_name_start(module_name)
            is_clz = MainActivity.is_act_clz_name_start(class_name)
            return is_mod and is_clz
        return False

    def check_disk_space(self):
        """
            检查磁盘空间
        :return:
        """
        path = commons.PATH_UPAN
        # 测试开始 <
        if self.is_windows:
            path = "F:\\"
        # 测试结束 >
        if os.path.exists(path):
            result = psutil.disk_usage(path)
            # print(result)
            # 取出信息中的剩余空间
            free_size = result[2]
            if free_size < 1024 * 1024:
                # 可用的储存空间小于1MB，我们需要警告用户释放空间
                self.start(WarningDiskFullActivity)
                return False
        return True

    def check_fw_update(self):
        """
            检查固件更新
            1、PM3
            2、FLASH
            3、STM32
            4、linux
        :return:
        """
        if self.is_windows:
            # TODO windows下不需要检查固件更新
            return

        hmi_can_update = update.check_hmi_update()
        pm3_can_update = update.check_pm3_update()
        all_can_update = update.check_all()
        print(f"更新可用性: hmi={hmi_can_update}, pm3={pm3_can_update}, all={all_can_update}")
        if hmi_can_update or pm3_can_update or all_can_update:
            #  我们需要前往OTA页面请求更新
            self.start(OTAActivity)
            return True

        return False

    def check_all_activity(self):
        """
            次入口初始化
        :return:
        """
        # 为了避免动态依赖，我们需要自动在运行时配置依赖
        # 我们需要搜索所有的activity相关的py文件，获取里面的class

        # 1、搜索当前目录下所有的activity规范内的文件
        #  我们限定，activity文件必须以activity开头，以各自的别名结尾
        #  比如 activity_

        try:
            files = os.listdir("lib")
        except Exception as e:
            print("寻找库路径出现异常: ", e)
            files = []

        # 测试开始 <
        # 在工程目录的构建下，此模块是跟act模块同级的
        # 因此可以直接进行列表，但是在发布状态，act存在于lib目录中
        # 万万不可直接list
        if platform.system() == "Windows":
            files = os.listdir(".")

        # 测试结束 >

        # 谨记清空历史加载的记录
        temp_activity_list = list()
        # 存放非尾部的活动
        temp_index_infos_map = dict()
        # 存放尾部的活动
        temp_index_infos_end = list()

        for file in files:
            # print("处理文件: ", file)
            if self.is_act_mod_name_start(file):  # 我们需要处理
                name = file.rsplit(".")[0]
                # print("动态加载Activity模块: ", name)
                lib = importlib.import_module(name)
                if inspect.ismodule(lib):  # 判断是否为模块
                    clzs = inspect.getmembers(lib, self.is_act_clz_name)
                    for clz_t in clzs:  # 迭代所有的类，进行act储存
                        clz_name = clz_t[0]
                        clz_obj = clz_t[1]

                        # print("类信息: ", clz_name)

                        # 类取出后,我们需要进行判断该类是否有实现getManifest函数
                        manifest = clz_obj.getManifest()

                        # 如果没有入口信息，则不允许加入入口列表
                        if manifest is None:
                            # print("没有清单的类: ", clz_name)
                            continue

                        # 进行排序以及有效的入口act识别
                        index = manifest["index"]
                        infos = manifest["infos"]
                        # print("入口信息: ", index, infos, "\n")
                        if manifest is None:
                            # print("没有入口的类: ", clz_name)
                            continue

                        if index in temp_index_infos_map:
                            raise Exception("不允许Activity使用重复存在的索引: {} -> {} : {}".format(
                                index,
                                temp_index_infos_map[index][0],
                                clz_obj,
                            ))

                        if index >= 0:
                            temp_index_infos_map[index] = (
                                clz_name,
                                clz_obj,
                                infos,
                            )
                        elif index == -1:
                            t = (
                                clz_name,
                                clz_obj,
                                infos
                            )
                            temp_index_infos_end.append(t)
                        else:
                            raise Exception("使用了不被接受的索引: ", index)

        for obj in temp_index_infos_end:
            # 获取最大的排序key
            tmp_list_sorted = sorted(temp_index_infos_map.keys())
            if len(tmp_list_sorted) >= 1:
                max_key = tmp_list_sorted[-1]
            else:
                max_key = len(temp_index_infos_map)
            temp_index_infos_map[max_key + 1] = obj

        for key in sorted(temp_index_infos_map.keys()):
            value = temp_index_infos_map[key]
            # print("index: ", key, ", infos: ", value)
            # 在排序过后，我们可以加进全局域中
            t = (
                value[0],  # 这是类名
                value[1],  # 这是类对象
                value[2],  # 这是标题和图像， 从 getManifest 函数里来
            )
            print(f"注册Activity: {t[0]}")
            temp_activity_list.append(t)

        print("当前Activity索引组为: ", sorted(temp_index_infos_map.keys()), "，请开发者添加Activity时注意不要使用重复的索引。")

        # 缓存act组到全局域
        self.acts = temp_activity_list
        # 获得标题项目
        self.info = self.get_activity_info(2)

        # 实例化一个列表视图对象
        self.lv.setItems(self.info)
        self.lv.setOnPageChangeCall(self.pi.update)

        return

    def get_activity_info(self, title_index=2):
        """
            获取所有的可以注册的act的信息
        :return:
        """
        ret = []
        for act in self.acts:
            ret.append(act[title_index])
        return ret

    def sync_time_to_system(self):
        """
            系统时间同步，从STM32中获取
        :return:
        """
        try:
            if not version.is_rtc_support():
                print("固件版本过低，可能没有时间RTC的API，跳过自动更新")
                return
            timestamp = hmi_driver.readrtc()
            if timestamp is not None:
                if self.is_windows:
                    print("Windows下不自动更新H3的时间")
                    return
                timetuple = time.localtime(int(timestamp))
                cmd1 = f'sudo date -s "{timetuple.tm_year}-{timetuple.tm_mon}-{timetuple.tm_mday}'
                cmd1 += f' {timetuple.tm_hour}:{timetuple.tm_min}:{timetuple.tm_sec}"'
                # 通知PM3进行指令执行
                resp = executor.startPM3Plat(cmd1)
                print("同步时间到H3成功: ", resp)
            else:
                print("从STM32获取时间失败，同步失败！")
        except Exception as e:
            print("自动同步时间失败:", e)

    def init(self):
        try:
            self.initializing = True

            if platform.system() == 'Windows':
                # 启动hmi事件分发
                hmi_driver.starthmi("COM4")
            else:
                # 启动hmi事件分发
                hmi_driver.starthmi()

            # 转交屏幕开始显示
            hmi_driver.startscreen()
            audio.setKeyAudioEnable(False)

            # 显示加载框
            self.toast = widget.Toast(self.getCanvas())
            self.toast.show(self.text_processing, mode=widget.Toast.MASK_FULL)

            # 先初始化所有的活动信息的列表
            self.check_all_activity()

            # 加载与初始化设置
            # 初始化音量
            audio.setVolume(settings.fromLevelGetVolume(settings.getVolume()))
            audio.playStartExma()

            # 初始化背光
            hmi_driver.setbaklight(settings.fromLevelGetBacklight(settings.getBacklight()))

            # 打开PM3
            executor.reworkPM3All()

            # 启动电池电量条的更新线程
            batteryui.start()

            # 同步一下时间
            self.sync_time_to_system()

            # 尝试启用最高充电电流
            version.current_limit(False)

            # 初始化结束后，需要检查一下磁盘空间
            if self.check_disk_space():
                print("磁盘检查完成，空间余量很足。")
            else:
                print("磁盘检查完成，剩余空间不足。")
                # 空间不足的情况下应当直接返回，避免跳转到更多页面
                return

            # 如果固件有更新，可以直接跳到更新
            if self.check_fw_update():
                print("检查到有固件更新，将跳转到更新页面。")
                return
            else:
                print("没有发现有效的固件更新可用。")

            # 此处我们需要判断一下，是否只有一个页面，只有一个页面的话，自动跳转
            if len(self.acts) == 1:
                print("只有一个页面，将会自动跳转: ", self.acts)
                self.gotoActByPos(self.lv.getSelection())

        finally:
            self.toast.cancel()
            audio.setKeyAudioEnable(True)
            self.initializing = False

        return  # 为了美观而对齐

    def onKeyEvent(self, event):
        if self.initializing:
            return False

        if event == keymap.DOWN:
            if self.toast.isShow():
                return False
            self.lv.next(True)
            return True

        if event == keymap.UP:
            if self.toast.isShow():
                return False
            self.lv.prev(True)
            return True

        if event == keymap.LEFT:
            if self.toast.isShow():
                return False
            self.lv.prev(prevPage=True)
            return True

        if event == keymap.RIGHT:
            if self.toast.isShow():
                return False
            self.lv.next(nextPage=True)
            return True

        if event == keymap.OK:
            if self.toast.isShow():
                return False
            # 回车键(代替确认键)
            self.gotoActByPos(self.lv.getSelection())
            return True

        if event == keymap.ALL:
            if self.toast.isShow():
                return False
            # Auto Copy页面永远都在最顶层，也就是第0项，所以我们直接跳转到第0项就行了
            self.gotoActByPos(0)
            return True

        if event == keymap.POWER:
            # 禁止发声
            if self.initializing:
                return False
            if self.toast.isShow():
                self.toast.cancel()
                return True
            return

        return False

    def gotoActByPos(self, pos):
        act = self.acts[pos][1]
        if act is None:
            print("未实现此页面: ", pos + 1)
            return False
        self.start(act)
        return True

    def gotoActByName(self, name):
        act_ret = None
        for act in self.acts:
            if act[0] == name:
                act_ret = act[1]
                break

        if act_ret is None:
            print("未实现此页面: ", name)
            return False
        self.start(act_ret)
        return True

    def setCanAttackIClassSe(self, enable):
        """
            设置是否可以使能SE外置读头的监听
        :param enable:
        :return:
        """
        try:
            # 尝试发送消息给ICLASSSE外设的启动服务
            self.callServer(
                "IClassSeAttack",  # 服务名
                enable  # 传输的数据
            )
        except Exception as e:
            print("发送消息失败", e)

    def read_nanopi_info(self):
        try:
            with open("/proc/cpuinfo") as fd:
                return fd.read()
        except Exception as e:
            print(e)
        return None

    def run_serial_call(self):
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
                # print("正在尝试读取行....")
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
                    continue
                # 有时候，我们需要获得UID
                if line == "UID_GET":
                    self.serial_port.write(f"{version.UID}\r\n".encode())
                    continue
                # 打印H3的信息
                if line == "CPU_INFO":
                    self.serial_port.write(f"{self.read_nanopi_info()}\r\n".encode())
                    continue

                # 相应活动跳转的指令
                if line.startswith("START:"):
                    act = line[6:].strip()
                    try:
                        self.serial_port.write(f"OK\r\n".encode())
                    except Exception as e:
                        print(e)
                    finally:
                        self.gotoActByName(act)

                    continue

            except Exception as e:
                print("主页面在接收数据时出现了异常: ", e)
                # 仅仅在还需要继续回复上位机的时候，继续尝试打开串口
                if self.need_resp:
                    self.serial_port = vsp_tools.open_serial()
                time.sleep(0.1)
        try:
            print("关闭串口")
            self.serial_port.close()
        except Exception as e:
            print(e)

        self.exit_count += 1
        print(f"线程退出，次数 {self.exit_count}")

        return

    def onResume(self):
        """
            在运行的时候
        :return:
        """
        super().onResume()

        print("**********发送消息启动监听")
        self.setCanAttackIClassSe(True)

        try:
            if not self.need_resp:
                self.need_resp = True
                threading.Thread(target=self.run_serial_call).start()
        except Exception as e:
            print(e)

    def onPause(self):
        """
            在暂停的时候，我们需要释放掉串口
        :return:
        """
        super().onPause()

        self.setCanAttackIClassSe(False)

        try:
            if self.need_resp:
                self.need_resp = False
                self.serial_port.close()
        except Exception as e:
            print(e)


class OTAActivity(BaseActivity):
    """
        更新
        1、STM32
        2、Flash
        3、PM3
    """

    text_shutdown, text_start, text_yes, text_no, text_update_success, text_processing, text_update_start_tips = \
        resources.get_str([
            "shutdown", "start", "yes", "no", "update_successful", "processing", "update_start_tips"
        ])

    text_ota_tips1, text_ota_tips2, text_ota_tips3, text_ota_tips4, text_ota_tips5 = \
        resources.get_str([
            "ota_battery_tips1", "ota_battery_tips2", "ota_battery_tips3", "ota_battery_tips4", "ota_battery_tips5",
        ])

    def __init__(self, canvas):
        self.isUpdating = False
        self.update_available = False
        self.shutdown_available = False
        self.tags_ota_txt = self.unique_id("tags_ota_txt")
        self.tags_ota_bg = self.unique_id("tags_ota_bg")

        super().__init__(canvas)

    def onActivity(self):
        # 我们不需要任何菜单栏的功能
        batteryui.pause()
        # 绘制一个黑色底
        self.getCanvas().create_rectangle((0, 0, 240, 240), fill="#2B2B2B", width=0, outline="", tags=self.tags_ota_bg)

    def showText(self, txt, size=16, center=False):
        """
            显示一些文本在屏幕上
        :return:
        """
        canvas = self.getCanvas()
        items = canvas.find_withtag(self.tags_ota_txt)
        font_i = resources.get_font(size)
        if not center:
            anchor_v = "nw"
            xy = (8, 10)
        else:
            anchor_v = "center"
            xy = (120, 120)
        if len(items) <= 0:
            canvas.create_text(
                xy,
                text=txt,
                font=font_i,
                fill="white",
                width=230,
                tags=self.tags_ota_txt,
                anchor=anchor_v,
                justify="center",
            )
        else:
            canvas.itemconfig(items, text=txt, state="normal", font=font_i, anchor=anchor_v)
            canvas.coords(items, xy)

    def dismissText(self):
        """
            隐藏文本
        :return:
        """
        self.getCanvas().itemconfig(self.tags_ota_txt, state="hidden")

    def startCheckBat(self):
        """
            开始检测电量和执行后续的操作
        :return:
        """
        min_battery = 50
        batpercent = hmi_driver.readbatpercent()
        if batpercent < 0:
            batpercent = hmi_driver.readbatpercent()
        if batpercent > min_battery:
            while True:
                # 第一步首先检查电量，电量不足50以进行更新，则不允许更新
                batpercent = hmi_driver.readbatpercent()
                if batpercent < min_battery:
                    if hmi_driver.requestChargeState() == 1:
                        charge_state = self.text_yes
                    else:
                        charge_state = self.text_no
                    msg = self.text_ota_tips1.format(min_battery)
                    msg0 = self.text_ota_tips2
                    msg1 = self.text_ota_tips3
                    msg2 = self.text_ota_tips4.format(charge_state)
                    msg3 = self.text_ota_tips5.format(batpercent)
                    self.showText(f"{msg}\n{msg0}\n{msg1}\n\n{msg2}\n{msg3}")
                    time.sleep(1)
                else:
                    break
        # 电量符合更新需求，我们可以继续接下来的更新操作了！
        self.dismissText()
        self.update_available = True
        self.shutdown_available = True
        self.setLeftButton(self.text_shutdown)
        self.setRightButton(self.text_start)
        self.showText(self.text_update_start_tips, center=True)
        print("完成电池电量检测，自动退出线程")

    def onCreate(self):
        self.startBGTask(self.startCheckBat)

    def onDestroy(self):
        # 重启一下电量更新的UI
        batteryui.start()
        super().onDestroy()

    def call(self, obj):
        if obj["finish"]:
            # 更新完成
            # 等待10秒后关闭此页面
            delay_time = 6
            for count in range(delay_time, -1, -1):
                # 尝试解决屏幕有遗留的文本的问题
                self.getCanvas().itemconfig(self.tags_ota_bg, state="hidden")
                self.getCanvas().itemconfig(self.tags_ota_bg, state="normal")
                # 显示实际上需要显示的内容
                self.showText(f"{self.text_update_success}\n\n{count}", 20, True)
                time.sleep(1)
            self.finish()
        else:
            v1 = obj["progress"][0]
            v2 = obj["progress"][1]
            v3 = obj["progress"][2]
            print("升级过程:", obj)
            if "app" in v3 or "stm32" in v3:
                name = "HMI App"
            elif "filelib" in v3:
                name = "HMI Lib"
            elif "elf" in v3:
                name = "RFID Core"
            elif "linux" in v3:
                name = "Linux"
            else:
                name = v3

            msg = f"{name}\n\n\n{int(v1 / v2 * 1000) / 10}%"
            self.showText(msg, 23, True)

    def startUpdate(self):
        """
            开始更新的任务
        :return:
        """
        self.isUpdating = True
        self.dismissButton()
        self.showText(self.text_processing, center=True)
        self.startBGTask(lambda: update.start(self.call))

    def onKeyEvent(self, event):
        if event == keymap.APO:
            def run_internal():
                print("接收到软重启的信号量")
                # 清除接收的缓存区
                hmi_driver.stophmi()
                if platform.system() == "Windows":
                    hmi_driver.starthmi("COM4")
                else:
                    hmi_driver.starthmi()
                # 重新设置亮度
                bl = settings.fromLevelGetBacklight(settings.getBacklight())
                hmi_driver.setbaklight(bl)
                # 转交屏幕，这个操作只是为了自动打开功放
                hmi_driver.startscreen()

            threading.Thread(target=run_internal).start()
            return

        if self.isUpdating:
            print("更新工作中，自动屏蔽一些事件。")
            return False

        if event == keymap.M1:
            if not self.shutdown_available:
                return False
            self.startBGTask(lambda: hmi_driver.planToShutdown())
            return True

        if event == keymap.M2:
            if self.isUpdating or not self.update_available:
                return False
            self.isUpdating = True
            self.shutdown_available = False
            self.startUpdate()
            return True

        return False


class SleepModeActivity(BaseActivity):
    """
        休眠模式使用的UI
    """

    def onActivity(self):
        pass  # 我们不需要任何UI

    def onCreate(self):
        """
            我们只需要绘制一个全黑的UI
        :return:
        """
        self.getCanvas().create_rectangle(0, 0, 240, 240, fill="black")
        # 将亮度调低
        self.startBGTask(lambda: hmi_driver.setbaklight(0))

    def onKeyEvent(self, event):
        # 恢复亮度
        self.startBGTask(lambda: hmi_driver.setbaklight(settings.fromLevelGetBacklight(settings.getBacklight())))
        self.finish()
        return True


class WarningDiskFullActivity(BaseActivity):
    """
        警告用户磁盘可用空间不足的页面
        1、用户可以强制结束本页面，执行相关的功能，虽然可能会出问题
        2、用户执行备份之后，可以点击清除按钮，会自动开始清空该目录
    """

    text_clearing, text_disk_full_tips, text_forceuse, text_clear = resources.get_str([
        "clearing", "disk_full_tips", "forceuse", "clear"
    ])

    def __init__(self, canvas):
        super().__init__(canvas)
        self.progressbar = widget.ProgressBar(canvas, (20, 210))
        self.progressbar.setMessage(self.text_clearing)
        self.progressbar.hide()

    def onCreate(self):
        self.setTitle(resources.get_str("disk_full"))
        self._canvas.create_text((120, 120),
                                 text=self.text_disk_full_tips,
                                 font=resources.get_font(16), fill="#1C6AEB", width=220)
        self.setLeftButton(self.text_forceuse)
        self.setRightButton(self.text_clear)

    def startClear(self):
        """
            开始清空磁盘空间
        :return:
        """
        self.progressbar.show()
        self.dismissButton()

        path = commons.PATH_UPAN

        # 测试开始 <
        if platform.system() == "Windows":
            path = "F:\\"
        # 测试结束 >

        # 迭代所有的文件夹，递归删除
        files = os.listdir(path)
        for file in files:
            file = os.path.join(path, file)

            if os.path.isfile(file):
                # 删除文件
                os.remove(file)

            if os.path.isdir(file):
                # 递归删除文件夹
                shutil.rmtree(file, ignore_errors=True)

            # 获取所有的空间大小统计百分比
            percent = psutil.disk_usage(path)[3]

            # 更新进度条
            self.progressbar.setProgress(100 - percent)

        # 所有的文件都删除完成后，直接结束这个页面
        self.progressbar.hide(True)
        self.setidle()
        self.finish()

        return

    def onKeyEvent(self, event):
        if event == keymap.M1 and not self.isbusy():
            # 强制使用，只需要关闭本页面即可
            self.finish()
            return True

        if event == keymap.M2 and not self.isbusy():
            # 在后台中清理磁盘空间
            self.setbusy()
            self.startBGTask(self.startClear)
            return True

        return False
