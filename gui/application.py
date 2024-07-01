import platform

from tkinter import *

import actmain
import actstack
import keymap
import sermain
import serpool


def setWindows(window):
    """
        初始化窗口，仅需要在Windows平台下设置
    :return:
    """
    try:
        if platform.system() == "Windows":
            # 初始化缩放比例开始 <
            import ctypes

            # Query DPI Awareness (Windows 10 and 8)
            awareness = ctypes.c_int()
            errorCode = ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
            # print(awareness.value)

            # Set DPI Awareness  (Windows 10 and 8)
            errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
            # the argument is the awareness level, which can be 0, 1 or 2:
            # for 1-to-1 pixel control I seem to need it to be non-zero (I'm using level 2)

            # Set DPI Awareness  (Windows 7 and Vista)
            success = ctypes.windll.user32.SetProcessDPIAware()
            # behaviour on later OSes is undefined, although when I run it on my Windows 10 machine,
            # it seems to work with effects identical to SetProcessDpiAwareness(1)

            window.tk.call('tk', 'scaling', 1.4)
            # 初始化缩放比例结束 >

    except Exception as e:
        print("初始化窗口失败: ", e)


def startApp():
    """
        启动APP
    :return:
    """
    # 创建一个窗口
    window = Tk()
    window.resizable(False, False)
    window.geometry("240x240")
    # 初始化Windows，如果是Windows平台
    setWindows(window)
    # 关闭鼠标指针
    window.config(cursor="none")

    # 更改字体
    window.option_add("*Font", "mononoki")

    # 如果是windows，我们可以去掉默认窗口
    # if platform.system() == 'Windows':
    #     window.overrideredirect(True)

    # print(font.families())
    # 创建基础框架

    # 绑定按键事件，可以是从HMI过来的事件，也可以是从windows过来的事件
    window.bind("<Key>", keymap.key.onKey)

    # 传入基础视图启动基础act
    actstack.window = window
    # 先启动主服务
    serpool.start_server(sermain.MainServer)
    # 启动主活动
    actstack.start_activity(actmain.MainActivity)

    # UI开始循环绘制
    window.mainloop()


if __name__ == '__main__':
    startApp()
