# -*- coding: UTF-8 -*-
import os
import platform
import executor

# NANOPI模拟的U盘的目录
PATH_UPAN = "/mnt/upan/"


def getFlashID():
    """获取flash的ID号"""
    # [=] ID            | 25 8C 20 A7 82 A8 67 D5
    cmd = "mem info"
    if executor.startPM3Task(cmd, 5000) == -1:
        return None
    return executor.getContentFromRegexG(r"ID.*\|\s+([a-fA-F0-9 ]+)", 1).replace(" ", "")


def startPlatformCMD(cmd):
    """
        执行一个命令
    """
    # 无论如何替换为linux的路径分隔符
    cmd = str(cmd).replace(r"\\", "/")
    if platform.system() == 'Windows':
        executor.startPM3Plat(cmd)
    else:
        # 在linux下，或许是全志linux板，可以直接执行，不经过PM3的中转
        os.system(cmd)


def mkdirs_on_icopy(path):
    """
        创建多级目录，在手持机中的文件系统中
    :param path:
    :return:
    """
    startPlatformCMD("sudo mkdir -p {} ; sudo chmod 775 {}".format(path, path))


def mkfile_on_icopy(file):
    """
        创建文件，在手持机中的文件系统中
    :param file:
    :return:
    """
    startPlatformCMD("sudo touch {} ; sudo chmod 775 {}".format(file, file))


def delfile_on_icopy(file):
    """
        删除文件，在手持机的文件系统
    :param file:
    :return:
    """
    startPlatformCMD("sudo rm -f " + file)


def recreate_on_icopy(file):
    """
        重新在icopy上创建一个文件
    :param file:
    :return:
    """
    delfile_on_icopy(file)
    mkfile_on_icopy(file)


def append_str_on_icopy(txt, file):
    """
        追加字符串到icopy的文件中
    :param txt:
    :param file:
    :return:
    """
    startPlatformCMD('echo "{}" |sudo tee -a {}'.format(txt, file))
