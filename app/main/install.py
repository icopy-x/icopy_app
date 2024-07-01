"""
    最终的安装脚本
"""
import os
import shutil
import time


def install_font(unpkg_path, callback):
    """
        安装字体
    :param unpkg_path:
    :param callback:
    :return:
    """
    # 我们需要进行字体的检查与安装
    print("\n检查字体的安装...")
    # 需要用到的路径
    target_font_path = os.path.join(os.sep, "usr", "share", "fonts")
    source_font_path = os.path.join(unpkg_path, "res", "font")
    # 列出字体文件，新的与已安装的
    new_fonts = os.listdir(source_font_path)
    print("新的字体列表: ", new_fonts)
    old_fonts = os.listdir(target_font_path)
    print("旧的字体列表: ", old_fonts)
    # 存放未安装的字体的列表，后续会安装列表中的字体文件
    font_no_install_list = []
    # 字体文件的后缀
    font_suffix = ".ttf"

    for new_font in new_fonts:
        if new_font.endswith(font_suffix):
            if new_font not in old_fonts:
                font_no_install_list.append(new_font)

    if len(font_no_install_list) > 0:  # 判断是否有字体没有安装！
        callback(f"{len(font_no_install_list)} Font will install...", 20)
        for font_install in font_no_install_list:
            source_font_file = os.path.join(source_font_path, font_install)
            if os.path.isfile(source_font_file):  # 直接复制文件到目标字体目录中安装！
                print(f"正在拷贝文件{source_font_file} 到 {target_font_path}")
                shutil.copy(source_font_file, target_font_path)
        # 最终，我们需要更新缓存！
        os.system("sudo fc-cache -fsv")
        callback(f"{len(font_no_install_list)} Font installed.", 100)
    else:
        callback(f"No Font can install.", 100)


def install_lua_dep(unpkg_path, callback):
    """
        安装lua的必要依赖库
    :param unpkg_path:
    :param callback:
    :return:
    """
    callback("LUA dep installing...", 30)
    # 定义U盘目录
    path_upan = os.path.sep + os.path.join("mnt", "upan")
    # 定义 lua zip文件路径
    path_lua_zip = os.path.join(unpkg_path, "pm3", "lua.zip")
    # 定义lua相关库的文件夹
    dir_lualibs = "lualibs"
    dir_luascripts = "luascripts"
    # 指向最终的目录
    path_lua_libs = os.path.join(path_upan, dir_lualibs)
    path_lua_scripts = os.path.join(path_upan, dir_luascripts)
    # 在安装之前，我们先检查文件夹是否存在
    if os.path.exists(path_lua_libs) and os.path.exists(path_lua_scripts):
        print("目录已经存在，不自动解压")
        callback("LUA dep exists...", 100)
    else:
        # 我们得保证，lua.zip必须存在！
        if os.path.exists(path_lua_zip):
            # 将LUA文件解压到U盘根目录
            shutil.unpack_archive(path_lua_zip, path_upan, format="zip")
            callback("LUA dep install done.", 100)
        else:
            callback("lua.zip no found...", 100)


def update_permission(unpkg_path, callback):
    """
        更新文件权限
    :param unpkg_path:
    :param callback:
    :return:
    """
    # 我们需要把文件全部赋予可执行权限
    print("\n正在更新所有的权限...")
    callback("Permission Updating...", 30)
    os.system("chmod 777 -R {}".format(unpkg_path))
    callback("Permission Updating...", 100)
    print("更新权限成功！！！\n")


def install_app(unpkg_path, callback):
    """
        真正安装包的过程！
    :param unpkg_path:
    :param callback:
    :return:
    """
    # 规范：
    # 包名称以ipk起头，以new或者bak或者main结尾
    # 其中，连接用的是下划线
    # 1、bak是备份文件夹，请不要随便生成bak结尾的目录
    # 2、main是主程序的入口文件夹，请不要随便生成main结尾的目录
    # 3、new是更新的程序包的目录，对于安装更新，请尽量将文件包命名为new结尾的目录
    target_path = "/home/pi/"

    # 移动到用户目录然后创建规范内的new包，然后等待启动器服务重启
    unpkg_path_name = os.path.split(unpkg_path)[-1]

    target_path_unpkg = os.path.join(target_path, unpkg_path_name)
    target_path_new_pkg = os.path.join(target_path, "ipk_app_new")

    if target_path == target_path_unpkg:
        print("不允许重命名用户目录！！！")
        return False

    callback("App installing...", 38)

    shutil.rmtree(target_path_unpkg, True)
    shutil.rmtree(target_path_new_pkg, True)
    shutil.move(unpkg_path, target_path)

    os.rename(
        target_path_unpkg,
        target_path_new_pkg
    )
    callback("App installed!", 100)
    print('copy files finished!')


def restart_app(callback):
    """
        重启自身应用
    :return:
    """
    print("\n正在重启")
    callback("App restarting...", 60)
    time.sleep(1.5)
    callback("App restarting...", 100)
    # 最终，我们需要重启服务
    os.system("sudo service icopy restart &")


def install(unpkg_path, callback):
    """
        安装程序的实现
    :param unpkg_path: 安装包管理器的解包目录
    :param callback: 安装回调，我们协同的回调格式为
                     callback(任务名 -> 字符串形式，任务进度 -> 整数值，最小为0，最大为100)
                     可以有多个进度同时出现，将会以轮播的形式更新UI
    :return:
    """

    install_font(unpkg_path, callback)

    time.sleep(1)

    update_permission(unpkg_path, callback)

    time.sleep(1)

    install_lua_dep(unpkg_path, callback)

    time.sleep(1)

    install_app(unpkg_path, callback)

    time.sleep(1)

    restart_app(callback)
    return True
