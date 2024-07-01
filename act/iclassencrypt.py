"""
    iclass 批量加密
"""
import time

import executor
import hficlass
import iclasswrite
import tagtypes


class FactoryTagRelease:
    """
        工厂发卡封装类
    """

    def __init__(self):
        self.run = False
        self.call1 = None
        self.call2 = None
        self.call3 = None

    @staticmethod
    def encrypt(typ, newkey="2020666666668888", l2e=False):
        """
            进行iclass的加密
        :param typ: 当前写的容器卡的类型
        :param newkey:
        :param l2e:
        :return:
        """
        key = hficlass.chkKeys({"type": typ})
        if key is None:
            print("没有发现这张卡的有效秘钥，无法进行加密。")
            return False
        if iclasswrite.writePassword(typ, newkey, key[1], l2e) == 1:
            print("加密成功!")
            return True
        else:
            print("加密失败")
        return False

    @staticmethod
    def isTagExists():
        """
            当前是否有卡片存在
        :return:
        """
        if executor.startPM3Task("hf iclass info", 5888) == -1:
            return False
        return executor.hasKeyword("Tag Information")

    def fromLegacy2NikolaLegacy(self):
        """
            将普通的legacy卡转换为nikola出售的legacy卡片
        :return:
        """
        return self.encrypt(tagtypes.ICLASS_LEGACY)

    def fromLegacy2NikolaSE(self):
        """
            将普通的legacy卡转换为nikola出售的legacy卡片
        :return:
        """
        return self.encrypt(tagtypes.ICLASS_LEGACY, "6666202066668888")

    def fromLegacy2NikolaElite(self):
        """
            将普通的legacy卡转换为nikola出售的Elite卡片
        :return:
        """
        return self.encrypt(tagtypes.ICLASS_LEGACY, l2e=True)

    def fromNikolaLegacy2Office(self):
        """
            将nikola出厂的legacy转换为普通的官方legacy
        :return:
        """
        return self.encrypt(tagtypes.ICLASS_LEGACY, "AFA785A7DAB33378")

    def fromNikolaElite2Office(self):
        """
            将nikola出厂的elite转换为普通的官方elite
        :return:
        """
        return self.encrypt(tagtypes.ICLASS_ELITE, "AFA785A7DAB33378")

    def fromOffice2NikolaElite(self):
        """
            将普通的官方elite转换为nikola出厂的elite
        :return:
        """
        return self.encrypt(tagtypes.ICLASS_ELITE)

    def setOnFactoryCall(self, befoceCall, retCall, afterCall):
        """
            设置工厂操作进行前的回调
        :return:
        """
        self.call1 = befoceCall
        self.call2 = retCall
        self.call3 = afterCall

    @staticmethod
    def call_not_none(call, param=None):
        """
            执行回调如果不为空
        :param param:
        :param call:
        :return:
        """
        if call is not None:
            if param is not None:
                call(param)
            else:
                call()

    def startCreateTag(self, task):
        """
            开启一个发卡任务，这个任务是循环的，直到用户停止
        :param task:
        :return:
        """
        if self.run:  # 阻止重复执行任务
            return

        self.run = True

        while self.run:
            if self.isTagExists():  # 判断卡片是否存在
                self.call_not_none(self.call1)
                self.call_not_none(self.call2, task(self))
                self.call_not_none(self.call3)
            time.sleep(0.1)

    def stopCreateTag(self):
        """
            停止当前的发卡任务
        :return:
        """
        self.run = False
