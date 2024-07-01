"""
    虚拟串口工具
"""
import os
import serial


def searchSerial():
    """
        为了防止抽风出现非tyGS0的串口，
        我们需要进行串口搜索
    :return:
    """
    try:
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
    except Exception as e:
        print("搜索串口出现异常: ", e)
        return None


def open_serial():
    """
        内部封装重新打开串口的实现
    :return:
    """
    serial_name = searchSerial()
    if serial_name is None:
        print("没有搜索到有效的ttyGS*， 无法继续接下来的操作，请开发者检查此异常。")
        return
    ret = serial.Serial(serial_name, baudrate=115200, timeout=0.1)
    if not ret.is_open:
        print("无法打开设备，无法请求此操作")
        return None
    return ret
