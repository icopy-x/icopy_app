"""
    用于控制USB从机身份的脚本
"""
import os
import subprocess
import commons


def get_upan_partition():
    """
        获取U盘所在的设备分区
    :return:
    """
    # 我们需要实现检测是否存在不同的硬件版本的分区，达到动态切换的目的。
    return "/dev/mmcblk0p4"


def mount_upan_partition():
    """
        挂载U盘分区
    :return:
    """
    try:
        cmd = f"sudo mount -o rw {get_upan_partition()} {commons.PATH_UPAN}"
        os.system(cmd)
    except Exception as e:
        print("umount_upan_partition():", e)


def umount_upan_partition():
    """
        卸载U盘分区
    :return:
    """
    try:
        cmd = f"sudo umount {get_upan_partition()}"
        os.system(cmd)
    except Exception as e:
        print("umount_upan_partition():", e)


def remount_upan_partition():
    """
        重新挂在U盘分区
    :return:
    """
    try:
        cmd = f"sudo mount -o rw,remount {get_upan_partition()}"
        os.system(cmd)
    except Exception as e:
        print("umount_upan_partition():", e)


def auto_ms_remount():
    """
        重新挂载U盘分区
    :return:
    """
    try:
        upan_p = get_upan_partition()

        output_str = str(subprocess.check_output("mount", shell=True).decode())
        lines = output_str.split("\n")
        has_mounted = False
        for line in lines:
            line = line.strip()
            if upan_p in line:
                has_mounted = True
                break
        print(f"\n正在挂载 {upan_p} 分区...")
        if has_mounted:
            remount_upan_partition()
        else:
            mount_upan_partition()
        print(f"分区 {upan_p} 重新挂载完成。\n")
    except Exception as e:
        print("gadget_linux.remount_upan_partition() 异常: ", e)


def kill_all_module(auto_remount=True):
    """
        卸载所有g_开头的模块
    :return:
    """
    try:
        # 先卸载g_开头的模块
        output_str = str(subprocess.check_output("lsmod", shell=True).decode())
        lines = output_str.split("\n")
        g_list = []
        for line in lines:
            line = line.strip()
            if len(line) == 0:
                continue
            module_name = line.split()[0]
            if module_name.startswith("g_"):
                g_list.append(module_name)
        # 然后进行递归删除
        if len(g_list) > 0:
            print("\n开始卸载模块...")
            for module_name in g_list:
                # 检查到g_开头的模块我们就需要卸载
                print("\n将会卸载该模块: ", module_name)
                os.system(f"sudo modprobe -r {module_name}")
                print(f"卸载该模块: {module_name} 完成。\n")
            print("卸载模块完成。\n")
    except Exception as e:
        print("kill_all_module():", e)
        return

    if auto_remount:
        auto_ms_remount()


def upan_or_both(mod):
    """
        启动一个U盘或者复合设备
    :return:
    """

    try:
        # 卸载可能存在的虚拟设备
        kill_all_module(auto_remount=False)
        # ********
        # sudo mount -o sync,rw /dev/mmcblk0p4 /mnt/upan/
        # sudo umount /dev/mmcblk0p4
        # sudo rmmod g_acm_ms -v
        # sudo modprobe g_acm_ms file=/dev/mmcblk0p4 removable=1
        # sudo modprobe g_acm_ms file=/dev/zero removable=1
        # sudo socat -d -d /dev/ttyGS0,raw,echo=0 /dev/ttyACM0,raw,echo=0
        # ********
        # 然后挂载U盘设备
        cmd = f"sudo modprobe {mod} file={get_upan_partition()} removable=1 stall=0"  # >&- 2>&-
        os.system(cmd)

    except Exception as e:
        print(e)


def usb_mass_storage():
    """
        单独启动U盘
    :return:
    """
    upan_or_both("g_mass_storage")


def upan_and_serial():
    """
        开启U盘和串口
    :return:
    """
    upan_or_both("g_acm_ms")


def serial(kill=True):
    """
        单独启动串口
    :return:
    """
    if kill:
        # 先卸载
        kill_all_module(auto_remount=False)
    # 然后挂载
    os.system("sudo modprobe g_serial")
