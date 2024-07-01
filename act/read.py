import importlib
import inspect
import os
import platform
import threading
import traceback

import appfiles
import felicaread
import hf14aread

import hf15read
import legicread
import lfem4x05
import lfread
import hfmfread
import lft55xx
import tagtypes
import hfmfuread
import hfmfkeys
import executor


class AbsReader:
    """
        抽象读卡器，用于规范自动化读取一个搜索到的卡片的操作
    """

    def __init__(self, tag_type, tag_data):
        self.tag_type = tag_type
        self.tag_data = tag_data

    @staticmethod
    def callReadSuccess(listener, infos, bundle, is_force=False):
        """
            在成功的时候生成字典返回到回调
        """
        ret = {"success": True, "tag_info": infos, "force": is_force, "bundle": bundle}
        listener(ret)
        return ret

    @staticmethod
    def callReadFailed(listener, infos, ret):
        """
            在失败的时候生成字典返回到回调
        """
        ret = {"success": False, "tag_info": infos, "return": ret}
        listener(ret)
        return ret

    @staticmethod
    def call_on_finish(ret, listener, infos, bundle):
        """
            快速回调
        :param bundle:
        :param infos:
        :param ret:
        :param listener:
        :return:
        """
        if ret == 1:
            return AbsReader.callReadSuccess(listener, infos, bundle)
        return AbsReader.callReadFailed(listener, infos, ret)

    def isSupport(self):
        """
            判断本读卡器是否支持读取此类型
        :return:
        """

    def start(self, listener):
        """
            规范化一个开始读取的操作
        :return:
        :param listener 读取回调
        """

    def stop(self):
        """
            规范化一个停止读取的操作
        :return:
        """
        executor.stopPM3Task(wait=False)


class MifareClassicReader(AbsReader):
    """
        M1卡读卡器
    """

    def isSupport(self):
        """
            判断传入的类型是否是我们支持的M1卡读取类型
        :return: 如果支持读取此M1卡，则返回True，否则返回False
        """
        return self.tag_type in tagtypes.getM1Types()

    def start(self, listener):
        """
            启动读取过程
        :param listener:
        :return:
        """
        size = hfmfread.sizeGuess(self.tag_type)
        force = self.tag_data.get("force", False)
        infos = self.tag_data.get("infos", None)
        if force:
            # 强制读取M1卡
            print("read.read开始强制读取M1卡")
            # 开始快速检测已知秘钥
            ret = hfmfkeys.fchks(infos, size, with_call=False)
            if ret == 1:
                ret = hfmfread.readAllSector(size, infos, listener)
                if ret == 1:
                    print("读取成功")
                    return self.callReadSuccess(listener, infos, is_force=force, bundle=hfmfread.FILE_READ)
                else:
                    print("读取失败，可能出现了一些问题")
                    return self.callReadFailed(listener, infos, ret)
            else:
                return self.callReadFailed(listener, infos, ret)
        else:
            if infos["gen1a"]:
                ret = hfmfread.readIfIsGen1a(infos)
                if ret == 1:
                    # 读取特殊卡成功，回调通知
                    return self.callReadSuccess(listener, infos, bundle=hfmfread.FILE_READ)
                else:
                    return self.callReadFailed(listener, infos, ret)
            else:
                print("读取正常卡，需要先进行破解")
                ret = hfmfkeys.keys(size, infos, listener)
                if ret == 1:
                    print("破解成功，开始进行读取")
                    ret = hfmfread.readAllSector(size, infos, listener)
                    if ret == 1:
                        print("读取成功")
                        return self.callReadSuccess(listener, infos, bundle=hfmfread.FILE_READ)
                    else:
                        print("读取失败，可能出现了一些问题")
                        return self.callReadFailed(listener, infos, ret)
                else:
                    print("破解失败，可以由用户手动强制读取")
                    return self.callReadFailed(listener, infos, ret)


class MifareUltralightReader(AbsReader):
    """
        Mifare Ultralight卡片读取
    """

    def isSupport(self):
        return self.tag_type in tagtypes.getULTypes()

    def start(self, listener):
        """
            读取UL卡的实现过程
        :param listener:
        :return:
        """
        infos = self.tag_data.get("infos")
        ret = hfmfuread.read(infos)
        return self.call_on_finish(ret, listener, infos, hfmfuread.FILE_MFU_READ)


class LF125KHZReader(AbsReader):
    """
        ID卡读卡器（125KHZ读卡器）
    """

    def isSupport(self):
        return self.tag_type in lfread.READ.keys()

    def start(self, listener):
        """
            启动读取ID卡的过程
        :param listener:
        :return:
        """
        typ = self.tag_type
        infos = self.tag_data.get("infos", None)
        ret = lfread.READ[typ](listener, infos)

        # 在此处保存普通的ID卡文件
        return_value = ret["return"]
        if return_value == 1 and typ in appfiles.CREATE_NORMAL_ID:  # 当该ID卡拥有快速保存数据文件的实现时，可以直接调用
            # 创建文件
            file = appfiles.CREATE_NORMAL_ID[typ](ret["data"])
            # 写入文件
            if appfiles.save2any(ret["raw"], file):
                self.call_on_finish(1, listener, infos, ret)
            else:
                self.call_on_finish(0, listener, infos, ret)
            return
        else:
            # 不是保存的是普通的ID卡文件，则说明有特殊的DUMP文件，我们需要进行文件最终的地址传递
            # 当我们传递到读取信息结果里面时，开发者可以使用此信息进行读写卡
            if typ == tagtypes.T55X7_ID:
                ret["file"] = lft55xx.DUMP_TEMP
                ret["key"] = infos["key"]
            elif typ == tagtypes.EM4305_ID:
                ret["file"] = lfem4x05.DUMP_TEMP
                ret["key"] = infos["key"]

        return self.call_on_finish(return_value, listener, infos, ret)


class HIDIClassReader(AbsReader):
    """
        IClass标签读取器
    """

    def isSupport(self):
        return self.tag_type in tagtypes.getiClassTypes()

    def start(self, listener):
        """
            启动读取IClass标签的过程
        :param listener:
        :return:
        """
        infos = self.tag_data.get("infos")
        try:
            import iclassread
            ret = iclassread.read(infos)
            bundle = {
                "key": iclassread.KEY_READ,
                "file": iclassread.FILE_READ
            }
        except Exception as e:
            print("读取IClass失败:", e)
            ret = -99
            bundle = None

        return self.call_on_finish(ret, listener, infos, bundle)


class LegicMim256Reader(AbsReader):
    """
        LegicMim256标签读取器
    """

    def isSupport(self):
        return self.tag_type == tagtypes.LEGIC_MIM256

    def start(self, listener):
        """
            启动读取LegicMim256标签的过程
        :param listener:
        :return:
        """
        infos = self.tag_data.get("infos")
        ret = legicread.read(infos)
        bundle = None
        return self.call_on_finish(ret, listener, infos, bundle)


class ISO15693Reader(AbsReader):
    """
        ISO15693标签读取器
    """

    def isSupport(self):
        typ = self.tag_type
        return typ == tagtypes.ISO15693_ICODE or typ == tagtypes.ISO15693_ST_SA

    def start(self, listener):
        """
            启动读取ISO15693标签的过程
        :param listener:
        :return:
        """
        infos = self.tag_data.get("infos")
        ret = hf15read.read(infos)
        bundle = hf15read.FILE_READ
        return self.call_on_finish(ret, listener, infos, bundle)


class ISO1443AReader(AbsReader):
    """
        ISO1443A标签读取器
    """

    def isSupport(self):
        return self.tag_type == tagtypes.HF14A_OTHER

    def start(self, listener):
        """
            启动读取ISO1443A标签的过程
        :param listener:
        :return:
        """
        infos = self.tag_data.get("infos")
        ret = hf14aread.read(infos)
        bundle = hf14aread.FILE_READ
        return self.call_on_finish(ret, listener, infos, bundle)


class FelicaReader(AbsReader):
    """
        Felica标签读取器
    """

    def isSupport(self):
        return self.tag_type == tagtypes.FELICA

    def start(self, listener):
        """
            启动读取Felica标签的过程
        :param listener:
        :return:
        """
        infos = self.tag_data.get("infos")
        ret = felicaread.read(infos)
        bundle = None
        return self.call_on_finish(ret, listener, infos, bundle)


class Reader:
    """
        主读卡器，用于查询指定的子读卡器模块，
        发现符合条件的读卡器则用于读卡操作
    """

    # 定义一个默认的读卡器列表合集！
    default_reader = [
        MifareClassicReader,
        MifareUltralightReader,
        LF125KHZReader,
        HIDIClassReader,
        LegicMim256Reader,
        ISO15693Reader,
        ISO1443AReader,
        FelicaReader,
    ]

    def __init__(self):
        self._reader = None  # 是当前选中的读卡器
        self._listener_reading = None
        self._listener_exception = None
        self._readers = self.find_readers()
        self._reading = False

    @property
    def call_reading(self):
        return self._listener_reading

    @call_reading.setter
    def call_reading(self, listener):
        self._listener_reading = listener

    @property
    def call_exception(self):
        return self._listener_exception

    @call_exception.setter
    def call_exception(self, listener):
        self._listener_exception = listener

    def _call_exception_method(self):
        if callable(self._listener_exception):
            self._listener_exception(traceback.format_exc())

    @staticmethod
    def is_reader_class(name):
        """
            判断是否是读卡器实现类
        :param name:
        :return:
        """
        if inspect.isclass(name):
            class_name_sub = getattr(name.__bases__[0], "__name__")  # 这个是当前搜索到的类的父类名
            class_name_abs = getattr(AbsReader, "__name__")  # 这个是当前模块的父类名

            issubclass_1 = issubclass(name, AbsReader)
            issubclass_2 = class_name_sub is class_name_abs

            return issubclass_1 or issubclass_2
        return False

    def find_readers(self):
        """
            寻找并且初始化读卡器列表
        :return: 一个列表，存放了支持的读卡器 类
        """
        ret_list = []
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

        for file in files:
            name = file.rsplit(".")[0]
            lib = importlib.import_module(name)
            if inspect.ismodule(lib):  # 判断是否为模块
                clzs = inspect.getmembers(lib, self.is_reader_class)
                for clz_t in clzs:  # 迭代所有的类，进行act储存
                    clz_name = clz_t[0]
                    clz_obj = clz_t[1]
                    print("发现读卡器实现类: ", clz_name)
                    ret_list.append(clz_obj)

        for clz in self.default_reader:
            if clz not in ret_list:
                ret_list.append(clz)

        return ret_list

    def find_reader(self, tag_type, tag_data):
        """
            寻找一个适合的读卡器
        :return:
        """
        # 重新搜索读卡器
        for reader_clz in self._readers:
            reader: AbsReader = reader_clz(tag_type, tag_data)
            if reader.isSupport():
                print("发现了一个支持此标签读取的读卡器: ", reader)
                return reader
        return None

    def is_reading(self):
        return self._reading

    def start(self, tag_type, tag_data):
        """
            启动最终的读卡过程
            在此过程，我们会选中一个读卡器，并且开始他的读取过程
        :return:
        """
        if self._reading:
            # 不允许同时执行多次读卡！
            return

        # 停止可能存在的读卡过程，并且重置状态！
        self.stop()

        # 搜索可用的读卡器
        self._reader = self.find_reader(tag_type, tag_data)
        if self._reader is None:
            print("没有发现此卡片支持的读卡器")
            AbsReader.call_on_finish(-99, self._listener_reading, tag_data["infos"], None)
            return

        # 创建一个执行函数的封装，用于重置状态量！
        def run():
            try:  # 一定要进行异常捕获！
                self._reader.start(self.call_reading)
            except Exception:
                self._call_exception_method()
            self._reading = False

        self._reading = True
        threading.Thread(target=run).start()
        return

    def stop(self):
        """
            停止读卡过程
        :return:
        """
        if self._reader is not None and self._reading:
            return self._reader.stop()

        return False
