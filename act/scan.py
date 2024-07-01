# -*- coding: UTF-8 -*-
import platform
import traceback

import commons
import hffelica
import lfread
import executor
import hf14ainfo
import hfmfuinfo
import lfsearch
import hfsearch
import hficlass
import lft55xx
import lfem4x05
import tagtypes

import threading

# PM3超时
CODE_TIMEOUT = executor.CODE_PM3_TASK_ERROR
# 卡片丢失
CODE_TAG_LOST = -2
# 卡片重叠
CODE_TAG_MULT = -3
# 卡片未发现
CODE_TAG_NO = -4
# 卡片类型错误
CODE_TAG_TYPE_WRONG = -5

# 缓存一次查询的结果
INFOS = None
# 是否自动缓存
INFOS_CACHE_ENABLE = True


def createTagNoFound(progress):
    """
        创建标签未发现的返回模板
    """
    return {
        "progress": progress,
        "return": CODE_TAG_NO,
        "found": False,
        "type": -1
    }


def createTagLost(progress):
    """
        创建标签丢失的返回模板
    """
    return {
        "progress": progress,
        "return": CODE_TAG_LOST,
        "found": False,
        "type": -1
    }


def createTagMulti(progress):
    """
        创建标签重叠的返回模板
    """
    return {
        "progress": progress,
        "return": CODE_TAG_MULT,
        "found": True,
        "type": -1
    }


def createExecTimeout(progress):
    """
        创建超时退出的返回模板
    """
    return {
        "progress": progress,
        "return": CODE_TIMEOUT,
        "found": False,
        "type": -1
    }


def createTagTypeWrong(progress):
    """
        创建超时退出的返回模板
    """
    return {
        "progress": progress,
        "return": CODE_TAG_TYPE_WRONG,
        "found": False,
        "type": -1
    }


def isTagTypeWrong(maps):
    """
        判断当前标签的类型是否错误
    :param maps:
    :return:
    """
    if maps is None: return False
    return "return" in maps and maps["return"] == CODE_TAG_TYPE_WRONG


def isTagLost(maps):
    """
        判断当前是否丢失了标签
    """
    if maps is None: return False
    return "return" in maps and maps["return"] == CODE_TAG_LOST


def isTagMulti(maps):
    """
        判断当前是否重叠了太多标签
    """
    if maps is None: return False
    return "return" in maps and maps["return"] == CODE_TAG_MULT


def isTagFound(maps):
    """
        判断当前是否未发现标签
    """
    if isinstance(maps, int): return False
    if maps is None: return False
    if "found" not in maps: return False
    is_found = maps["found"]
    if INFOS_CACHE_ENABLE:
        global INFOS
        if is_found:  # 如果发现卡片，则缓存一下当前的卡片信息
            INFOS = maps
        else:  # 否则，我们需要将卡片信息重置缓存
            INFOS = None
    return is_found


def isTimeout(value):
    """
        是否超时
    """
    if value is None: return False
    if isinstance(value, int) and value == CODE_TIMEOUT: return True
    if value is not None and "return" in value: return value["return"] == CODE_TIMEOUT
    return False


def isCanNext(value):
    """
        在未超时以及卡片未丢失的情况下，可以进行下一步
    """
    if isTimeout(value): return False
    if isTagLost(value): return False

    return not isTagFound(value)


def set_infos_cache(enable):
    """
        设置信息是否自动缓存
    :param enable:
    :return:
    """
    global INFOS_CACHE_ENABLE
    INFOS_CACHE_ENABLE = enable


def scan_14a():
    """
        执行和14a系列卡片的搜索
    """
    # 第一步，先进行hf 14a info的解析
    ret = executor.startPM3Task(hf14ainfo.CMD, hf14ainfo.TIMEOUT)
    if ret != -1:
        maps = hf14ainfo.parser()
        # 判断是否发现14a相关的卡片
        if isTagFound(maps):
            if "isUL" in maps and maps["isUL"]:
                # 如果发现UL卡，我们需要进行UI卡的解析
                ret = executor.startPM3Task(hfmfuinfo.CMD, hfmfuinfo.TIMEOUT)
                if ret != -1:
                    maps = hfmfuinfo.parser()
                    # 判断是否还能发现UL卡，如果无法发现，则是卡片丢失
                    if not isTagFound(maps):
                        return createTagLost(0)
                else:
                    return createExecTimeout(0)
            if "hasMulti" in maps and maps["hasMulti"]:
                # 发现用户叠加了多张卡，需要报错处理
                return createTagMulti(0)
            return maps
        return createTagNoFound(0)
    else:
        return createExecTimeout(0)


def lf_wav_filter():
    """
        低频过滤器
    :return: 如果是低频卡，返回True，否则返回False
    """
    # 此处我们需要修复一下容易误判为T55XX的问题
    # 疑似T55XX系列的卡片，
    # 1、直接执行san3
    # 2、判断峰值
    file = "/tmp/lf_trace_tmp"
    suffix = ".pm3"
    cmd = f"data save f {file}"
    # 执行保存
    ret = executor.startPM3Task(cmd, lfsearch.TIMEOUT)
    if ret != -1:
        # 读取所有的行，转换为峰值int
        file = file + suffix
        try:
            # 读取文件的兼容性处理
            if platform.system() == "Windows":
                data = executor.startPM3Plat(f"cat {file}")
            else:
                with open(file) as fd:
                    data = fd.read()

            if data is None or len(data) == 0:
                return False

            # print("读取到的数据是: ", data)
            # 读取完成后，我们必须删除此文件
            commons.delfile_on_icopy(file)
            # 然后去掉可能存在的 \r 符号
            data = data.replace("\r", "")

            value = []
            for line in data.split("\n"):
                try:
                    value.append(int(line))
                except Exception:
                    continue

            # print("取值完成的列表: ", value)
            print("峰值最大值: ", max(value))
            print("峰值最小值: ", min(value))

            if max(value) - min(value) < 90:
                return False

        except Exception as e:
            print("读取T55XX峰值文件失败: ", e)
            return False
    else:
        return False
    return True


def scan_lfsea():
    """
        执行和低频系列卡片的搜索
    """
    # 第二步，进行lf sea
    ret = executor.startPM3Task(lfsearch.CMD, lfsearch.TIMEOUT)
    if ret != -1:
        maps = lfsearch.parser()
        if isTagFound(maps):
            if "is4xXX" in maps and maps["is4xXX"]:
                # 执行scan4，然后解析
                maps = scan_em4x05()
                # 如果卡片丢失，我们需要重新执行san1
                if not isTagFound(maps):
                    # 重试超过三次以上，我们需要执行步骤3，也就是t55xx
                    if lfsearch.COUNT == 3:
                        # 必须重置计数器
                        lfsearch.COUNT = 0
                        return scan_t55xx()
                    else:
                        lfsearch.COUNT += 1
                        return scan_lfsea()
            if "isT55XX" in maps and maps["isT55XX"]:
                if lf_wav_filter():
                    return scan_t55xx()
                return createTagNoFound(1)
            return maps
        return createTagNoFound(1)
    else:
        return createExecTimeout(1)


def scan_hfsea():
    """
        执行和高频系列卡片的搜索
    """
    # 第三步，进行hf sea
    ret_obj = executor.startPM3Task(hfsearch.CMD, hfsearch.TIMEOUT)
    if ret_obj != -1:
        map_obj = hfsearch.parser()
        if isTagFound(map_obj):
            # 如果发现了iclass卡
            if "isIclass" in map_obj and map_obj["isIclass"]:
                map_obj = hficlass.parser()
                if not isTagFound(map_obj):
                    return createTagLost(2)
                else:
                    return map_obj
            # 如果发现了Mifare卡, 我们可以直接复用14a info的逻辑进行mifare卡的寻卡
            if "isMifare" in map_obj and map_obj["isMifare"]: return scan_14a()
            return map_obj
        else:
            # 我们需要手动对接felica的搜索
            return scan_felica()
    else:
        return createExecTimeout(2)


def scan_t55xx():
    """
        特殊的T55XX容器卡侦测
    """
    # 第四步，进行T55xx的detect
    cmd = lft55xx.CMD_DETECT_NO_KEY
    if lft55xx.KEY_TEMP is not None:
        cmd += " p " + lft55xx.KEY_TEMP
    ret = executor.startPM3Task(cmd, lft55xx.TIMEOUT)
    if ret != -1:
        maps = lft55xx.parser()
        # 判断有没有发现卡片
        if not isTagFound(maps):
            return createTagNoFound(3)
        # 判断是不是已知的卡片，如果不是，我们就需要尝试寻找高频卡，
        # 避免T55XX的判断被高频卡所干扰
        if not maps["known"]:
            set_infos_cache(False)  # 关闭信息缓存，避免覆盖更新lf sea的结果
            hf_maps = scan_hfsea()
            hf_found = isTagFound(hf_maps)
            set_infos_cache(True)  # 恢复信息缓存
            if hf_found:
                return hf_maps
        maps["key"] = lft55xx.KEY_TEMP
        return maps
    else:
        return createExecTimeout(3)


def scan_em4x05():
    """
        特殊的EM4X05容器卡侦测
    """
    # 第五步，进行4x05的info
    if lfem4x05.KEY_TEMP is not None:
        cmd = "lf em 4x05_info " + lfem4x05.KEY_TEMP
    else:
        cmd = lfem4x05.CMD
    ret = executor.startPM3Task(cmd, lfem4x05.TIMEOUT)
    if ret != -1:
        maps = lfem4x05.parser()
        if not isTagFound(maps): return createTagNoFound(4)
        maps["key"] = lfem4x05.KEY_TEMP
        return maps
    else:
        return createExecTimeout(4)


def scan_felica():
    """
        专用于felica的搜索过程
    :return:
    """
    ret_obj = executor.startPM3Task(hffelica.CMD, hffelica.TIMEOUT)
    if ret_obj != -1:
        map_obj = hffelica.parser()
        if not isTagFound(map_obj): return createTagNoFound(5)
        return map_obj
    else:
        return createExecTimeout(5)


def scanForType(listener, typ):
    """
        限定类型进行扫描
    :param listener: 结果回调
    :param typ: 类型
    :return:
    """

    def run():
        # 如果是M1经典系列的卡片，可以直接限定搜索
        m1Types = tagtypes.getM1Types()
        if typ in m1Types:
            result = scan_14a()
            if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                tag_typ = result["type"]
                uid_len = result["len"]

                def call_listener_on_success():
                    result["type"] = typ
                    listener({"progress": 100, "return": result})

                if tag_typ in m1Types or tag_typ not in tagtypes.getAllHigh():
                    # 如果指定了7B的类型，则必须要搜索到7B的UID长度的标签才能限定
                    if typ in tagtypes.getM17BTypes():
                        if uid_len != 7:
                            listener({"progress": 100, "return": createTagTypeWrong(0)})
                        else:
                            call_listener_on_success()
                    elif typ in tagtypes.getM14BTypes():
                        if uid_len != 4:
                            listener({"progress": 100, "return": createTagTypeWrong(0)})
                        else:
                            call_listener_on_success()
                    else:
                        # 如果不需要限定UID长度，则直接进行类型纠正并且回调成功
                        call_listener_on_success()

                else:
                    # 发现的类型不在M1经典系列的卡片里，类型错误
                    listener({"progress": 100, "return": createTagTypeWrong(0)})
            else:
                # 直接报找不到卡片的错误
                listener({"progress": 100, "return": createTagNoFound(0)})
            return

        # 如果是UL系列的卡，可以直接限定搜索
        ulTypes = tagtypes.getULTypes()
        if typ in ulTypes:
            result = scan_14a()
            if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                tag_typ = result["type"]
                if tag_typ == typ:
                    # 发现了ul系列的卡片，直接返回
                    listener({"progress": 100, "return": result})
                else:
                    # 发现的类型不是指定类型的卡片，类型错误
                    listener({"progress": 100, "return": createTagTypeWrong(0)})
            else:
                # 直接报找不到卡片的错误
                listener({"progress": 100, "return": createTagNoFound(0)})
            return

        # 如果是其他的高频卡，可以直接通过hf sea进行限定搜索
        highTypes = tagtypes.getAllHigh()
        if typ in highTypes:
            result = scan_hfsea()
            if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                tag_typ = result["type"]
                if tag_typ == typ:
                    # 发现了ul系列的卡片，直接返回
                    listener({"progress": 100, "return": result})
                else:
                    # 发现的类型不是指定类型的卡片，类型错误
                    listener({"progress": 100, "return": createTagTypeWrong(0)})
            else:
                # 直接报找不到卡片的错误
                listener({"progress": 100, "return": createTagNoFound(0)})
            return

        # 如果是其他的低频卡，可以直接通过lf xxx read进行读取
        lowTypes = tagtypes.getAllLow()
        if typ in lowTypes:
            result = None

            if typ in tagtypes.getAllLowCanDump():
                # 如果是55XX，则我们使用55XX的基础Scan
                if typ == tagtypes.T55X7_ID:
                    result = scan_t55xx()

                # 如果是4X05，则使用EX05的基础scan
                if typ == tagtypes.EM4305_ID:
                    result = scan_em4x05()

            else:
                result = lfread.READ[typ](None, None)
                if result["data"] is not None and result["raw"] is not None:
                    result["type"] = typ
                    result["found"] = True
                else:
                    result["type"] = -1
                    result["found"] = False

            if result is None:
                raise Exception("开发者传入了一个不被处理的低频类型: ", typ)

            if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                tag_typ = result["type"]
                if tag_typ == typ:
                    # 发现了ul系列的卡片，直接返回
                    listener({"progress": 100, "return": result})
                else:
                    # 发现的类型不是指定类型的卡片，类型错误
                    listener({"progress": 100, "return": createTagTypeWrong(0)})
            else:
                # 直接报找不到卡片的错误
                listener({"progress": 100, "return": createTagNoFound(0)})
            return

    thread = threading.Thread(target=run)
    thread.start()


def getScanCache():
    """获取历史查询的记录"""
    return INFOS


def clearScanCahe():
    """
        清除搜索缓存
    :return:
    """
    setScanCache(None)


def setScanCache(infos):
    """
        设置scan的信息
    :param infos:
    :return:
    """
    global INFOS
    INFOS = infos


def set_scan_t55xx_key(key):
    """
        设置scan t55xx卡片的时候需要用上的卡片
    :param key:
    :return:
    """
    lft55xx.set_key(key)


def set_scan_em4x05_key(key):
    """
        设置scan em4x05卡片的时候需要用上的卡片
    :param key:
    :return:
    """
    lfem4x05.set_key(key)


class Scanner:
    """
        卡片扫描器，用于扫描卡片并且获得具体信息
    """

    def __init__(self):
        self._call_progress = None
        self._call_resulted = None
        self._call_exception = None
        self._call_value_max = 100
        self._stop_label = False
        self._scan_running = False
        self._scan_lock = threading.RLock()

    @property
    def call_progress(self):
        """
            进度回调
            回调过去的参数是一个元组，参数分别是：
            (progress_current, progress_max)
        :return:
        """
        return self._call_progress

    @call_progress.setter
    def call_progress(self, call):
        self._call_progress = call

    @property
    def call_resulted(self):
        """
            结果回调
        :return:
        """
        return self._call_resulted

    @call_resulted.setter
    def call_resulted(self, result):
        self._call_resulted = result

    @property
    def call_exception(self):
        """
            结果回调
        :return:
        """
        return self._call_exception

    @call_exception.setter
    def call_exception(self, call):
        self._call_exception = call

    def _call_progress_method(self, progress):
        """
            回调函数，更新进度
        :param progress:
        :return:
        """
        if callable(self._call_progress):
            try:
                self._call_progress(
                    (progress, self._call_value_max,)
                )
            except Exception:
                self._call_exception_method()

    def _call_resulted_method(self, resulted):
        """
            回调搜索卡片的结果
        :param resulted:
        :return:
        """
        if callable(self._call_resulted):
            try:
                self._call_resulted(resulted)
            except Exception:
                self._call_exception_method()

    def _call_exception_method(self):
        """
            回调异常出现时的操作！
        :return:
        """
        if callable(self._call_exception):
            self._call_exception(traceback.format_exc())

    def _set_stop_label(self, value):
        """
            在锁中设置停止位标志
        :param value:
        :return:
        """
        with self._scan_lock:
            self._stop_label = value

    def _set_run_label(self, value):
        """
            在锁中设置停止位标志
        :param value:
        :return:
        """
        with self._scan_lock:
            self._scan_running = value

    def _is_can_next(self, value):
        """
            在未超时以及卡片未丢失的情况下，可以进行下一步
        """
        if isTimeout(value): return False
        if isTagLost(value): return False
        if self._stop_label: return False
        return not isTagFound(value)

    def _raise_on_multi_scan(self):
        if self._scan_running:
            raise Exception("不允许对一个设备同时开启多次查询任务。")

    def scan_all_synchronous(self):
        """
            最终搜索所有的卡片的实现（堵塞操作）
        :return:
        """
        try:
            self._raise_on_multi_scan()
            self._set_stop_label(False)
            self._set_run_label(True)
            self._call_progress_method(23)
            result = scan_14a()
            if self._is_can_next(result):
                self._call_progress_method(53)
                result = scan_lfsea()
                if self._is_can_next(result):
                    self._call_progress_method(83)
                    result = scan_hfsea()
            self._call_progress_method(100)
            self._call_resulted_method(result)
            self._set_run_label(False)
        except Exception:
            self._call_exception_method()

    def scan_all_asynchronous(self):
        """
            扫描所有的卡片，并且获得信息回调（非堵塞操作）
        :return:
        """
        threading.Thread(target=self.scan_all_synchronous).start()

    def scan_type_synchronous(self, typ):
        """
            堵塞查询指定类型的卡片的信息
        :param typ:
        :return:
        """
        try:
            self._raise_on_multi_scan()
            self._set_stop_label(False)
            self._set_run_label(True)
            # 如果是M1经典系列的卡片，可以直接限定搜索
            m1Types = tagtypes.getM1Types()
            ret = None
            try:
                self._call_progress_method(20)
                if typ in m1Types:
                    result = scan_14a()
                    if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                        tag_typ = result["type"]
                        uid_len = result["len"]

                        if tag_typ in m1Types or tag_typ not in tagtypes.getAllHigh():
                            # 如果指定了7B的类型，则必须要搜索到7B的UID长度的标签才能限定
                            if typ in tagtypes.getM17BTypes():
                                if uid_len != 7:
                                    ret = createTagTypeWrong(0)
                                else:
                                    result["type"] = typ
                                    ret = result
                            elif typ in tagtypes.getM14BTypes():
                                if uid_len != 4:
                                    ret = createTagTypeWrong(0)
                                else:
                                    result["type"] = typ
                                    ret = result
                            else:
                                # 如果不需要限定UID长度，则直接进行类型纠正并且回调成功
                                result["type"] = typ
                                ret = result

                        else:
                            # 发现的类型不在M1经典系列的卡片里，类型错误
                            ret = createTagTypeWrong(0)
                    else:
                        # 直接报找不到卡片的错误
                        ret = createTagNoFound(0)

                    return

                # 如果是UL系列的卡，可以直接限定搜索
                ulTypes = tagtypes.getULTypes()
                if typ in ulTypes:
                    result = scan_14a()
                    if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                        tag_typ = result["type"]
                        if tag_typ == typ:
                            # 发现了ul系列的卡片，直接返回
                            ret = result
                        else:
                            # 发现的类型不是指定类型的卡片，类型错误
                            ret = createTagTypeWrong(0)
                    else:
                        # 直接报找不到卡片的错误
                        ret = createTagNoFound(0)
                    return

                # 如果是其他的高频卡，可以直接通过hf sea进行限定搜索
                highTypes = tagtypes.getAllHigh()
                if typ in highTypes:
                    result = scan_hfsea()
                    if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                        tag_typ = result["type"]
                        if tag_typ == typ:
                            # 发现了ul系列的卡片，直接返回
                            ret = result
                        else:
                            # 发现的类型不是指定类型的卡片，类型错误
                            ret = createTagTypeWrong(0)
                    else:
                        # 直接报找不到卡片的错误
                        ret = createTagNoFound(0)
                    return

                # 如果是其他的低频卡，可以直接通过lf xxx read进行读取
                lowTypes = tagtypes.getAllLow()
                if typ in lowTypes:
                    result = None

                    if typ in tagtypes.getAllLowCanDump():
                        # 如果是55XX，则我们使用55XX的基础Scan
                        if typ == tagtypes.T55X7_ID:
                            result = scan_t55xx()

                        # 如果是4X05，则使用EX05的基础scan
                        if typ == tagtypes.EM4305_ID:
                            result = scan_em4x05()

                    else:
                        result = lfread.READ[typ](None, None)
                        if result["data"] is not None and result["raw"] is not None:
                            result["type"] = typ
                            result["found"] = True
                        else:
                            result["type"] = -1
                            result["found"] = False

                    if result is None:
                        raise Exception("开发者传入了一个不被处理的低频类型: ", typ)

                    if isTagFound(result):  # 发现了卡片，但是我们需要查看类型是否一致
                        tag_typ = result["type"]
                        if tag_typ == typ:
                            # 发现了ul系列的卡片，直接返回
                            ret = result
                        else:
                            # 发现的类型不是指定类型的卡片，类型错误
                            ret = createTagTypeWrong(0)
                    else:
                        # 直接报找不到卡片的错误
                        ret = createTagNoFound(0)
                    return
            finally:
                # 我们需要在finally实现最终回调
                self._call_progress_method(100)
                self._call_resulted_method(ret)
                self._set_run_label(False)
        except Exception:
            self._call_exception_method()

    def scan_type_asynchronous(self, typ):
        """
            非堵塞查询指定类型的卡片的信息
        :param typ:
        :return:
        """
        threading.Thread(target=self.scan_type_synchronous, args=(typ,)).start()

    def scan_stop(self):
        """
            停止扫描卡片，结束扫描任务
        :return:
        """
        self._set_stop_label(True)
        executor.stopPM3Task()
