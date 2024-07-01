import serial
import signal

from serial import SerialException

"""
    此模块待启用！
"""


class SerialBridge:
    sp1 = "COM3"
    br1 = 115200

    sp2 = "COM4"
    br2 = 115200

    def __init__(self):
        self.ser1 = None
        self.ser2 = None
        self.inst = False
        self.buffer = b""

    def start(self):
        self.on_creat()

    def on_creat(self):
        try:
            signal.signal(signal.SIGINT, self.on_exit)
            signal.signal(signal.SIGTERM, self.on_exit)
            signal.signal(signal.SIGKILL, self.on_exit)
        except Exception as e:
            pass
            # print(e)
        # 打开串口们
        try:
            self.ser1 = serial.Serial(self.sp1, self.br1, timeout=1)
            self.ser1.flushInput()
            # print ("找到了串口：[", sp1, "]\n")
        except (IOError, SerialException) as e:
            # print ("未找到串口：[", sp1, "]正在退出\n")
            exit(1)
        try:
            self.ser2 = serial.Serial(self.sp2, self.br2, timeout=1)
            self.ser2.flushInput()
            # print("找到了串口：[", sp2, "]\n")
        except (IOError, SerialException) as e:
            # print("未找到串口：[", sp2, "]正在退出\n")
            exit(1)
        try:
            while True:
                if self.ser1.inWaiting() > 0:
                    rx1 = self.ser1.read()
                    # print(rx1)
                    if self.inst is True:
                        self.buffer += rx1
                        if len(self.buffer) > 8:
                            if self.buffer.find(b"reopenpm3") > -1:
                                self.inst = False
                                self.buffer = b""
                                print("重启发现了\n")
                            else:
                                self.inst = False
                                self.buffer = b""
                                # print("哦是假的\n")
                        else:
                            pass
                    if rx1 == b'r':
                        if self.inst:
                            # print("已经在处理了又发现了一个r.......")
                            self.inst = True
                            self.buffer = b"r"
                        else:
                            self.inst = True
                            self.buffer += b"r"
                            # print("发现了一个r.......")
                    self.ser2.write(rx1)
                if self.ser2.inWaiting() > 0:
                    rx2 = self.ser2.read()
                    self.ser1.write(rx2)
        except IOError:
            pass

    def on_exit(self, signum, frame):
        if self.ser1 is not None:
            try:
                self.ser1.close()
            except (IOError, SerialException) as e:
                exit(1)
        if self.ser2 is not None:
            try:
                self.ser2.close()
            except (IOError, SerialException) as e:
                exit(1)
