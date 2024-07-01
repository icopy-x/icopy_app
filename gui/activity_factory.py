"""
    主线运行入口
"""
import os
import re
import subprocess
import threading
import time
import serial
import actbase
import commons
import images
import keymap
import hmi_driver
import gadget_linux
import activity_update
import resources
import version


def bytesToHexString(bs):
    # hex_str = ''
    # for item in bs:
    #     hex_str += str(hex(item))[2:].zfill(2).upper() + " "
    # return hex_str
    if isinstance(bs, int): return '%02x' % bs
    return ''.join(['%02X' % b for b in bs])


class WaitInitActivity(actbase.BaseActivity):
    """
        等待初始化
    """

    TIPS_WAIT_CON_0 = "Waiting for creator to connect"
    TIPS_WAIT_CON_1 = TIPS_WAIT_CON_0 + "."
    TIPS_WAIT_CON_2 = TIPS_WAIT_CON_1 + "."
    TIPS_WAIT_CON_3 = TIPS_WAIT_CON_2 + "."

    TIPS_WAIT_CON_G = [
        TIPS_WAIT_CON_0,
        TIPS_WAIT_CON_1,
        TIPS_WAIT_CON_2,
        TIPS_WAIT_CON_3,
    ]

    TIPS_SERIAL_ERR = "Err, cant create connection with creator"

    @staticmethod
    def getManifest():
        return {
            "index": -1,
            "infos": tuple(("Factory", images.load("factory.png")))
        }

    def __init__(self, canvas):
        super().__init__(canvas)
        self.tags_init_tips = self.unique_id("init_tips")
        self.getCanvas().create_text(120, 120, font=resources.get_font(18), width=230, fill="#1C6AEB",
                                     tag=self.tags_init_tips)
        self.run_wait = True
        self.run_wait_index = 0
        self.run_tag_make = False
        self.run_fw_make = False
        self.run_cmd_recv = True
        # 串口
        self.serial_port = None
        # sn
        self.serial_num = None
        # 是否是复合设备模式
        self.is_gadget_both = False
        # 是否可以退出
        self.is_can_exit = True
        # 是否在退出中
        self.is_exiting = False
        # 是否在操作模块中
        self.is_gadget_processing = False

        # 缓存各大信息，方便回复
        self.id_h3 = None
        self.id_pm3 = None
        self.id_stm32 = None

    def init(self):
        """
            初始化发布入口
        :return:
        """
        self.is_can_exit = False
        self.show_tips_text("Restart serial port....")
        # 首先无论如何，我们都要把当前的从机模式切换为单串口模式
        self.is_gadget_processing = True
        gadget_linux.serial()
        # 我们不应当立刻打开串口，应当等待一秒钟，让USB设备完成初始化
        time.sleep(1)
        # 开启串口，等待连接
        try:
            if self.tryOpenSerial() and self.serial_port.is_open:
                # 开始等待出厂设置操作
                self.startBGTask(self.run_wait_action)
                self.startBGTask(self.run_serial_com)
            else:
                self.show_serial_err()
        except Exception as e:
            print(e)
            self.show_serial_err()
        self.is_gadget_processing = False

    def show_serial_err(self, msg=None):
        """
            串口打开失败，无法和上位机通信
        :return:
        """
        if msg is not None:
            msg = "{}: {}".format(self.TIPS_SERIAL_ERR, msg)
        else:
            msg = self.TIPS_SERIAL_ERR
        self.show_tips_text(msg)

    def show_tips_text(self, text):
        """
            显示文本在屏幕上
        :param text:
        :return:
        """
        self.getCanvas().itemconfig(self.tags_init_tips, text=text)

    def run_wait_action(self):
        """
            等待连接的操作
        :return:
        """
        while self.run_wait:
            self.getCanvas().itemconfig(self.tags_init_tips, text=self.TIPS_WAIT_CON_G[self.run_wait_index])
            # 屏幕上显示的消息索引 + 1
            if self.run_wait_index + 1 >= len(self.TIPS_WAIT_CON_G):
                self.run_wait_index = 0
            else:
                self.run_wait_index += 1
            time.sleep(0.3)

    def resp_msg(self, msg, retryMax=3, reopen=False):
        """
            对串口进行消息回应
        :param reopen:
        :param retryMax:
        :param msg:
        :return:
        """
        if retryMax == 0:
            self.show_tips_text("Information resp failed.")
            return False

        if reopen:
            # 需要重新打开串口
            self.tryOpenSerial()

        if self.serial_port is not None:
            # 开始收集信息
            try:
                if isinstance(msg, str):
                    msg = msg.encode()
                self.serial_port.write(msg)
                self.serial_port.flush()
                return True
            except Exception as e:
                print("resp_msg() ->", e)
                return self.resp_msg(msg, retryMax - 1, True)
        return False

    def resp_information(self):
        """
            信息应答
        :return:
        """
        if self.serial_port is not None:
            # 开始收集信息
            try:
                # 收集H3的CPUID
                # 我的小绿      : 02c000814f54266f
                # 孔大神的小红   :
                if self.id_h3 is None:
                    output_str = str(subprocess.check_output("cat /proc/cpuinfo", shell=True), errors='ignore')
                    self.id_h3 = re.search(r"Serial\s*:\s*([a-fA-F0-9]+)", output_str).group(1)

                # 收集PM3的ID
                if self.id_pm3 is None: self.id_pm3 = commons.getFlashID()  # 返回的是字符串信息

                # 收集STM32的ID 0669FF495655836687181528C86704789F3B6434
                if self.id_stm32 is None: self.id_stm32 = hmi_driver.readstid().decode()

                # 组成信息组发送过去
                infos = '{},{},{}\r\n'.format(self.id_h3, self.id_pm3, self.id_stm32)

                return self.resp_msg(infos)
            except Exception as e:
                print(e)
        return False

    def tryCloseSerial(self):
        """
            尝试关闭串口
        :return:
        """
        try:
            if self.serial_port is not None:
                if not self.serial_port.closed:
                    print("\n串口不为空，将会尝试刷新数据后关闭")
                    try:
                        self.serial_port.flush()
                        print("刷新数据完成")
                    except Exception as e:
                        print(e)
                    self.serial_port.close()
                    self.serial_port = None
                    print("关闭旧的记录完成！")
        except Exception as e:
            print("关闭串口的时候出现了一些问题: ", e)
            return

    @staticmethod
    def searchSerial():
        """
            为了防止抽风出现非tyGS0的串口，
            我们需要进行串口搜索
        :return:
        """
        tty_path = "/dev/"
        ttys = os.listdir(tty_path)
        tty_gs_list = list()
        for tty in ttys:
            if tty.startswith("ttyGS"):  # ttyGS0
                tty_gs_list.append(tty)
        # 查看是否有ttyGS系列的串口出现
        if len(tty_gs_list) > 0:
            tty_ret = os.path.join(tty_path, sorted(tty_gs_list)[0])
            print(f"发现了有效的串口: {tty_gs_list}")
            print(f"将自动返回最靠前的: {tty_ret}")
            return tty_ret
        else:
            print("没有发现有效的ttyGS*串口。")
            return None

    def tryOpenSerial(self):
        """
            尝试打开串口
        :return:
        """
        try:
            # 先关闭
            self.tryCloseSerial()
            # 再重新打开
            serial_name = self.searchSerial()
            if serial_name is None:
                print("没有搜索到有效的ttyGS*， 无法继续接下来的操作，请开发者检查此异常。")
                return
            self.serial_port = serial.Serial(serial_name, baudrate=115200, timeout=0)
        except Exception as e:
            print("tryOpenSerial 尝试打开串口时出现异常: ", e)
            return False
        return True

    def try2ReadLine(self, tryMax=3, reopen=False, ):
        """
            尝试读取一行数据
        :return:
        """
        if self.is_exiting or tryMax == 0: return
        if reopen: self.tryOpenSerial()
        if self.serial_port is not None:
            if not self.serial_port.is_open:
                self.tryOpenSerial()
            if not self.serial_port.is_open: return
        else:  # 串口模块是空的，我们应当尝试重新打开设备
            self.tryOpenSerial()
        try:
            if self.serial_port is not None:
                if not self.serial_port.is_open:
                    return
            line = self.serial_port.readline()
            if line is not None and len(line) >= 1:
                line = line.decode("ascii", errors='ignore').strip('\x00').strip("\r\n")
                print("接收到的行: ", line)
                return line
            else:
                return
        except Exception as e:
            if self.serial_port is None or self.serial_port.closed:
                return
            print("try2ReadLine() 读取出现异常: ", e)
            return self.try2ReadLine(tryMax - 1, True)

    def run_serial_com(self):
        """
            串口通信线程
        :return:
        """
        while self.run_cmd_recv:

            if self.is_exiting:  # 如果当前正在退出发布，则不进行接下来的操作
                print("run_serial_com() 检测到退出了发布。")
                break

            try:
                line = self.try2ReadLine()
                if line is None:
                    # print("接收到了空的数据，跳过本次操作。")
                    time.sleep(0.5)
                    continue

                if "SN_GET" in line:
                    self.resp_msg(f"{version.getSN()}\r\n")
                    continue

                if "SN_SAVE:" in line:
                    # 我们需要先截取
                    sn = line.replace("SN_SAVE:", "")
                    sn = sn.lower()
                    self.serial_num = sn
                    # 判断是否已经保存过了
                    file = f"{commons.PATH_UPAN}sn=={sn}.txt"
                    if not os.path.exists(file) or not self.is_gadget_both:
                        print("\n发现SN传输指令，将会将SN保存到U盘中: ", sn)
                        try:
                            with open(file, "w+"):
                                pass
                        except Exception as e:
                            print(e)
                            self.resp_msg("ERR\r\n")
                            return
                        self.resp_msg("OK\r\n")
                        print("保存完成，开始尝试切换到复合设备模拟模式。")
                        # 然后我们需要直接切换到复合设备模式
                        # 注意，切换后，串口下线重启，此时应当注意IO异常
                        # 先关闭串口
                        self.tryCloseSerial()
                        # 然后再切换到复合设备
                        self.is_gadget_processing = True
                        gadget_linux.upan_and_serial()
                        print("切换到复合设备完成。\n")
                        # 切换到复合设备一般都要两秒钟等待重新上线，我们应当休眠一下
                        self.is_gadget_both = True
                        time.sleep(2)
                        self.is_gadget_processing = False
                    else:
                        self.resp_msg("EXISTS\r\n")
                    continue

                if line == "TAG_START":
                    print("标签粘贴开始，我们需要开始闪烁屏幕以提醒生产者贴标签")
                    if self.run_tag_make: continue
                    self.run_tag_make = True

                    def run_flash():
                        while self.run_tag_make:
                            hmi_driver.setbaklight(0)
                            # 一秒闪烁一次
                            time.sleep(1)
                            hmi_driver.setbaklight(100)
                        # 默认结束后恢复亮度为100
                        hmi_driver.setbaklight(100)

                    threading.Thread(target=run_flash).start()

                if line == "TAG_FINISH":
                    print("标签粘贴结束，我们需要开始关闭屏幕闪烁")
                    self.run_tag_make = False

                if line == "FAC_START":  # 请求开启生产，我们需要回复设备信息
                    print("接收到开启指令，将进入信息上发模式")
                    self.run_wait = False
                    self.show_tips_text("Information Uploading")
                    if self.resp_information():
                        self.show_tips_text("Information Upload Successfully(√).")
                    else:
                        self.show_tips_text("Information resp failed(X).")

                if line == "IPK_START":  # 请求开启接收IPK，我们需要开启YModem接收
                    self.run_fw_make = True
                    self.show_tips_text("IPK file install...")
                    # 直接关闭串口和U盘的模拟
                    self.tryCloseSerial()
                    self.is_gadget_processing = True
                    gadget_linux.kill_all_module()
                    self.is_gadget_processing = False
                    ipk_file = f"{commons.PATH_UPAN}{self.serial_num}.ipk"
                    if os.path.exists(ipk_file):
                        print("发现文件: ", ipk_file)
                        self.finish(ipk_file)
                        # 结束循环
                        break
                    else:
                        self.show_tips_text("IPK file receive failed(X).")

            except Exception as e:
                print("接收生产指令时出现异常: ", e)
                time.sleep(0.1)

        print("关闭了数据的接收。")
        self.is_can_exit = True

    def onCreate(self):
        """
            初始化的UI
        :return:
        """
        self.setTitle("Factory Mode")
        self.startBGTask(self.init)

    def run_finish_wait(self, ipk_file=None):
        """
            等待结束完成的过程
        :return:
        """
        self.tryCloseSerial()
        while not self.is_can_exit:
            print("正在等待退出...")
            time.sleep(0.5)
        self.is_gadget_processing = True
        gadget_linux.upan_and_serial()
        self.is_gadget_processing = False
        super().finish()
        if ipk_file is not None:
            # 启动安装页面
            print("\n更新页面启动中...")
            bundle = {
                "file": ipk_file,
                "auto": True,
            }
            self.start(activity_update.UpdateActivity, bundle)
            print("更新页面启动完成。\n")
        return

    def finish(self, bundle=None):
        # 清空标志位，结束一些服务
        self.run_tag_make = False
        self.run_wait = False
        self.run_wait_index = 0
        self.run_cmd_recv = False

        self.show_tips_text("exit...")

        # 在子线程中退出
        threading.Thread(target=self.run_finish_wait, args=(bundle,)).start()

    def onKeyEvent(self, event):
        if event == keymap.POWER:
            if self.run_fw_make:
                print("生产中，无法停止！！！")
                return False
            elif not self.is_exiting and not self.is_gadget_processing:
                self.is_exiting = True
                self.finish()
                print("退出完成。")
                return True
            return False

        return False
