"""
    专门负责安装和更新事项的活动
"""
import os
import shutil
import sys
import time
import zipfile
import tkinter

import importlib.machinery
import importlib.util

import actbase
import gadget_linux
import keymap
import resources
import widget
import version


class UpdateActivity(actbase.BaseActivity):
    """
        安装更新专用的活动
        1、需要检测安装包是否符合规范
        3、需要检测SN是否匹配（如果SN不为空，则需要检测SN，避免覆盖SN安装）
    """

    # 临时的解包目录
    TMP_OUT_DIR = "/tmp/.ipk/unpkg"
    # 主程序入口脚本
    MAIN_APP_SCRIPT = "app.py"
    # 版本信息的脚本文件
    VERSION_SCRIPT = "lib/version.so"
    # 安装器的脚本文件
    INSTALLER_SCRIPT = "main/install.so"

    text_installation, text_cancel, text_start, text_install_failed, text_update, text_start_install_tips = resources.get_str([
        "installation", "cancel", "start", "install_failed", "update", "start_install_tips"
    ])

    def __init__(self, canvas: tkinter.Canvas):
        super().__init__(canvas)
        self.progressbar = widget.ProgressBar(canvas, (20, 210))
        self.progressbar.hide()
        self.toast = widget.Toast(canvas)
        self.can_click = True
        self.data = None

    @staticmethod
    def search(path, name):
        print("本次搜索的文件名: ", name)
        for root, dirs, files in os.walk(path):  # path 为根目录
            print("\n搜索安装包文件迭代信息: ", root, dirs, files)
            if name in files:
                # root = str(root)
                # dirs = str(dirs)
                return os.path.join(root, name)
        return None

    def showTips(self, enable=True, text=None):
        """
            显示提示
        :return:
        """
        if text is None:
            text = self.text_installation
        tags = self.unique_id("install_tips")
        widgets = self.getCanvas().find_withtag(tags)
        if len(widgets) <= 0:
            # 绘制一个提示页面
            widgets = self.getCanvas().create_text(
                (120, 120),
                text=text,
                font=resources.get_font(15), fill="#1C6AEB", width=230, tags=tags
            )
        if enable:
            state = "normal"
        else:
            state = "hidden"
        self.getCanvas().itemconfig(widgets, state=state)

    def showBtns(self, enable):
        """
            显示按钮咯
        :param enable:
        :return:
        """
        if enable:
            self.setLeftButton(self.text_cancel)
            self.setRightButton(self.text_start)
            self.can_click = True
        else:
            self.dismissButton()
            self.can_click = False

    def showErr(self, code):
        """
            显示错误信息
        :return:
        """
        msg = self.text_install_failed.format(code)
        self.toast.show(msg, mode=widget.Toast.MASK_TOP_CENTER)
        self.showTips(False)
        self.progressbar.hide()
        self.showBtns(True)

    def install(self, file):
        """
            开始安装
        :return:
        """
        self.showTips(True)
        self.showBtns(False)
        self.progressbar.show()
        self.toast.cancel()

        time.sleep(1)

        # 首先判断基本的包组成
        if self.checkPkg(file):
            print("包组成检测通过...")
            # 然后解包
            path = self.unpkg(file)
            if path is None:
                print("解包失败，自动结束安装。")
                self.showErr("0x01")
            else:
                print("解包成功，开始进行版本校验...")
                if self.checkVer(path):
                    print("版本信息校验成功，开始进行安装")
                    installer_so = self.search(self.TMP_OUT_DIR, os.path.basename(self.INSTALLER_SCRIPT))
                    if installer_so is None:
                        print("无法搜索到安装脚本，自动结束安装")
                        self.showErr("0x02")
                    else:
                        try:
                            my_module = self.path_import(installer_so)

                            # 使用模块中的安装实现函数进行安装
                            # 请注意，此UI不应当过来的包含安装的过程
                            # 应当只包含需要告知用户的信息，所有的安装实现应当
                            # 放在安装脚本中

                            def callback(name, progress):
                                self.onInstall(name, progress)

                            if my_module.install(path, callback):
                                print("安装成功，将自动退出当前的程序！！！")
                                # exit(0)
                            else:
                                self.showErr("0x06")

                        except Exception as e:
                            print("通过安装脚本模块安装失败: ", e)
                            self.showErr("0x03")

                else:
                    print("版本信息校验失败，自动结束安装")
                    self.showErr("0x04")
        else:
            print("包组成检测不通过，自动结束安装。")
            self.showErr("0x05")

    def unpkg(self, file):
        """
            尝试解包到临时的文件目录
        :return:
        """
        try:
            if os.path.exists(self.TMP_OUT_DIR):
                shutil.rmtree(self.TMP_OUT_DIR)  # 先删除
            shutil.unpack_archive(file, self.TMP_OUT_DIR, format="zip")
        except Exception as e:
            print(e)
            return None
        return self.TMP_OUT_DIR

    # @staticmethod
    # def path_import(file):
    #     """
    #         导入模块
    #     :param file:
    #     :return:
    #     """
    #     path = os.path.dirname(file)
    #     sys.path.insert(0, path)
    #     # 开始导入
    #     importlib.invalidate_caches()
    #     module = importlib.import_module(os.path.splitext(os.path.basename(file))[0])
    #     sys.path.remove(path)
    #     return module

    @staticmethod
    def path_import(file):
        """
            导入模块
        :param file:
        :return:
        """
        print("\n******************* 开始动态加载模块 *************************")
        loader_details = (
            importlib.machinery.ExtensionFileLoader,
            importlib.machinery.EXTENSION_SUFFIXES
        )
        tools_finder = importlib.machinery.FileFinder(os.path.dirname(file), loader_details)
        print("FileFinder: ", tools_finder)
        toolbox_specs = tools_finder.find_spec(os.path.basename(file).split(".")[0])
        print("find_spec: ", toolbox_specs)
        toolbox = importlib.util.module_from_spec(toolbox_specs)
        print("module: ", toolbox)
        toolbox_specs.loader.exec_module(toolbox)
        print("导入成功 path_import(): ", toolbox)
        print("检查sys中是否包含了此模块: ", toolbox in sys.modules)
        print("******************* 动态加载模块完成 *************************\n")
        return toolbox

    def checkVer(self, path):
        """
            检查版本信息，也就是SN是否撇匹配
        :param path:
        :return:
        """
        # 搜索版本信息文件
        ver_info_file = self.search(path, os.path.basename(self.VERSION_SCRIPT))
        if ver_info_file is None:
            print("无法搜索到版本信息文件，校验失败。")
            return False
        print("搜索到的版本信息文件: ", ver_info_file)
        # 然后加载模块并且读取信息
        try:
            my_module = self.path_import(ver_info_file)
            # 开始验证
            if my_module == version:
                print("警告，两个版本信息模块的对象相同...")
            if my_module.SERIAL_NUMBER is not None and version.SERIAL_NUMBER is not None:
                print("新的安装包中的序列号: ", my_module.SERIAL_NUMBER)
                print("当前的程序中的序列号: ", version.SERIAL_NUMBER)
                return my_module.SERIAL_NUMBER == version.SERIAL_NUMBER
            elif version.SERIAL_NUMBER is None:  # 如果本机SN是空的，那我们就不验证SN，直接安装，适合调试和初级发布
                return True
            else:  # 否则的话，就不能安装，避免被空的序列号的固件覆盖掉正常的固件
                return False
        except Exception as e:
            print("校验版本信息失败", e)
            return False

    def checkPkg(self, file):
        """
            检查安装包的组成
            需要包含
                1、app.py  -> 在最主页的位置，是程序非常必要的入口文件
                2、lib/version.so  -> 版本信息，在Lib目录下，是非常重要的差异对比文件
                3、main/install.so  -> 安装过程，是非常重要的安装脚本
        :return:
        """
        # 我们认为的比较关键的文件的存在状态映射
        maps_file = {
            self.MAIN_APP_SCRIPT: False,
            self.VERSION_SCRIPT: False,
            self.INSTALLER_SCRIPT: False,
        }
        try:
            zfd = zipfile.ZipFile(file)
            for zf in zfd.infolist():  # 迭代所有的文件
                if zf.filename in maps_file:
                    maps_file[zf.filename] = True
            # 最终我们需要检测当前的映射表是否全部为True，否则安装包为无效包
            if False in maps_file.values():
                print(f"安装包不符合规范: {maps_file}")
                return False
        except Exception as e:
            print("解析安装包出现异常: ", e)
            return False  # 解析安装包出错的话，我们也不能安装。
        print("安装包解析成功，符合初级规范。")
        return True

    def onInstall(self, name, progress):
        """
            在安装的时候的回调
        :param name:
        :param progress:
        :return:
        """
        # 更新信息
        self.progressbar.setMessage(name)
        self.progressbar.setProgress(progress)

    def onCreate(self):
        self.setTitle(self.text_update)
        self.showBtns(True)
        self.showTips(True, text=self.text_start_install_tips)

    def onData(self, bundle):
        """
            在有数据传递时，处理相关的数据
        :param bundle:
        :return:
        """
        if isinstance(bundle, str):
            self.data = bundle
        elif isinstance(bundle, dict):
            key = "file"
            if key in bundle:
                self.data = bundle["file"]

                # 在进入时如果需要进行相关的操作
                key_auto = "auto"
                key_remount = "remount"

                if key_remount in bundle:
                    if bundle[key_remount]:
                        gadget_linux.auto_ms_remount()

                if key_auto in bundle:
                    if bundle[key_auto]:
                        self.startBGTask(lambda: self.install(self.data))
        return

    def onKeyEvent(self, event):
        if self.can_click:

            if event == keymap.POWER or event == keymap.M1:
                self.finish()
                return True

            if event == keymap.M2:
                # 在每次进行操作时，我们默认尝试进行分区的重新挂载
                gadget_linux.auto_ms_remount()
                self.startBGTask(lambda: self.install(self.data))
                return True

        return False
