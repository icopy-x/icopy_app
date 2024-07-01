import subprocess
import os

import gadget_linux
import rftask


def main():
    """
        启动main组件
    :return:
    """
    # 此处仅仅做一个简单的小处理，避免非法的运行
    cmd = "uname -a"  # Linux NanoPi-NEO 4.14.111 #3 SMP Thu Aug 20 13:34:39 CST 2020 armv7l armv7l armv7l GNU/Linux
    pi = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    line = ""
    while pi.poll() is None:
        line += str(pi.stdout.readline())
    # 判断是否是nanopi neo并且是linux
    if "NanoPi-NEO" not in line or "Linux" not in line:
        E = True
        os.system("shutdown -t 0 &")
        os._exit(1)

    if hasattr(main, "E"):
        os._exit(1)

        # 1、先检查res文件目录
    if not os.path.exists("res"):
        print("res目录不存在")
        os._exit(1)
    # 2、检查lib文件目录
    if not os.path.exists("lib"):
        print("lib目录不存在")
        os._exit(1)
    # 3、检查pm3文件目录
    if not os.path.exists("pm3"):
        print("pm3目录不存在")
        os._exit(1)
    else:
        # 我们需要启动pm3客户端，因此需要判断客户端是否正常存在
        if not os.path.exists("pm3/proxmark3"):
            print("pm3客户端不存在")
            os._exit(1)
        # 检查与升级执行权限
        os.system("chmod 777 -R pm3")

    # 初始化启动PM3组件的参数
    # sudo killall -w -q -9 proxmark3
    print("\n正在尝试清除所有的PM3残留进程...")
    pm3_kill_cmd = "sudo killall -w -q -9 proxmark3"
    os.system(pm3_kill_cmd)
    print("清除PM3残留进程完成，开始启动管理器...")
    pm3_cmd = "sudo -s {}/pm3/proxmark3 /dev/ttyACM0 -w --flush".format(os.path.abspath("."))
    pm3_cwd = "pm3"
    pm3_hp = ("0.0.0.0", 8888)
    rm = rftask.RemoteTaskManager(pm3_cmd, pm3_kill_cmd, pm3_cwd, pm3_hp)
    # 启动PM3组件
    rm.startManager()
    print("管理器启动完成\n")

    print("\n正在启动虚拟设备")
    gadget_linux.auto_ms_remount()
    gadget_linux.serial()
    print("虚拟设备启动完成..\n")

    try:
        from lib import application
        application.startApp()
    except Exception as e:
        print(e)
        os._exit(1)
