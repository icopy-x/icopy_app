"""
    负责处理写卡的实现
"""
import threading

import hfmfuwrite
import hfmfwrite

try:
    import iclasswrite
except:
    pass

import hf15write
import lfverify
import lfwrite
import tagtypes


def callReadSuccess(listener):
    """
        在成功的时候生成字典返回到回调
    """
    ret = {"success": True}
    listener(ret)
    return ret


def callReadFailed(listener, ret):
    """
        在失败的时候生成字典返回到回调
    """
    ret = {"success": False, "return": ret}
    listener(ret)
    return ret


def call_on_finish(ret, listener):
    """
        快速回调
    :param ret:
    :param listener:
    :return:
    """
    if ret == 1:
        return callReadSuccess(listener)
    return callReadFailed(listener, ret)


def call_on_state(state, listener):
    """
        快速回调更新消息
    :param state:
    :param listener:
    :return:
    """
    listener({"state": state})


def run_action(run, run_on_subthread):
    """
        执行一个动作，自动根据参数选择是否在子线程中运行
    :param run:
    :param run_on_subthread:
    :return:
    """
    # 判断是否需要在子线程执行read
    if run_on_subthread:
        # 在子线程中执行read
        read_thread = threading.Thread(target=run)
        read_thread.start()
    else:  # 不需要在子线程执行，则直接调用函数
        return run()

    # 美观对齐
    return -9999


def write(listener, infos, bundle, run_on_subthread=True):
    """
        写入实现
    :return:
    """

    def run():
        typ = infos["type"]

        if typ in tagtypes.getM1Types():
            write_ret = hfmfwrite.write(listener, infos, bundle)
            if write_ret == 1:
                call_on_state("verifying", listener)
                # 自动进行ID卡的写入校验
                verify_ret = hfmfwrite.verify(infos, bundle)
                return call_on_finish(verify_ret, listener)
            else:
                return call_on_finish(write_ret, listener)

        if typ in tagtypes.getAllLow():

            if typ in tagtypes.getAllLowCanDump():  # 如果自带Dump指令，可以Dump数据，则我们需要读取文件
                file = bundle["file"]
                # 调用写卡实现开始写卡
                write_ret = lfwrite.write(listener, typ, infos, file)
                if write_ret == 1:
                    call_on_state("verifying", listener)
                    # 自动进行ID卡的写入校验
                    verify_ret = lfverify.verify(typ, None, file)
                    return call_on_finish(verify_ret, listener)
                else:
                    return call_on_finish(write_ret, listener)
            else:
                # 取出普通的ID信息进行校验
                uid = bundle["data"]
                raw = bundle["raw"]
                # 调用写卡实现开始写卡
                write_ret = lfwrite.write(listener, typ, infos, raw)
                if write_ret == 1:
                    call_on_state("verifying", listener)
                    # 自动进行ID卡的写入校验
                    verify_ret = lfverify.verify(typ, uid, raw)
                    return call_on_finish(verify_ret, listener)
                else:
                    return call_on_finish(write_ret, listener)

        if typ in tagtypes.getULTypes():
            write_ret = hfmfuwrite.write(infos, bundle)
            if write_ret == 1:
                call_on_state("verifying", listener)
                # 自动进行ID卡的写入校验
                verify_ret = hfmfuwrite.verify(infos, bundle)
                return call_on_finish(verify_ret, listener)
            else:
                return call_on_finish(write_ret, listener)

        if typ == tagtypes.ISO15693_ICODE or typ == tagtypes.ISO15693_ST_SA:
            write_ret = hf15write.write(infos, bundle)
            if write_ret == 1:
                call_on_state("verifying", listener)
                # 自动进行ID卡的写入校验
                verify_ret = hf15write.verify(infos, bundle)
                return call_on_finish(verify_ret, listener)
            else:
                return call_on_finish(write_ret, listener)

        if typ == tagtypes.HF14A_OTHER:
            write_ret = hfmfwrite.write_only_uid(infos)
            if write_ret == 1:
                call_on_state("verifying", listener)
                # 自动进行ID卡的写入校验
                verify_ret = hfmfwrite.verify_only_uid(infos)
                return call_on_finish(verify_ret, listener)
            else:
                return call_on_finish(write_ret, listener)

        if typ in tagtypes.getiClassTypes():
            write_ret = iclasswrite.write(infos, bundle)
            if write_ret == 1:
                call_on_state("verifying", listener)
                # 自动进行ID卡的写入校验
                verify_ret = iclasswrite.verify(infos, bundle)
                return call_on_finish(verify_ret, listener)
            else:
                return call_on_finish(write_ret, listener)

        print("write.py 未实现该类型的写入功能。")
        return call_on_finish(-1, listener)

    return run_action(run, run_on_subthread)


def verify(listener, infos, bundle, run_on_subthread=True):
    """
        校验写入的数据
    :return:
    """

    def run():
        typ = infos["type"]

        if typ in tagtypes.getM1Types():
            return call_on_finish(hfmfwrite.verify(infos, bundle), listener)

        if typ in tagtypes.getAllLow():

            if "uid" in bundle:
                uid = bundle["uid"]
            else:
                uid = None

            if "raw" in bundle:
                raw = bundle["raw"]
            else:
                raw = None

            return call_on_finish(lfverify.verify(typ, uid, raw), listener)

        if typ in tagtypes.getULTypes():
            return call_on_finish(hfmfuwrite.verify(infos, bundle), listener)

        if typ == tagtypes.ISO15693_ICODE or typ == tagtypes.ISO15693_ST_SA:
            return call_on_finish(hf15write.verify(infos, bundle), listener)

        if typ == tagtypes.HF14A_OTHER:
            return call_on_finish(hfmfwrite.verify(infos, bundle), listener)

        if typ in tagtypes.getiClassTypes():
            return call_on_finish(iclasswrite.verify(infos, bundle), listener)

        print("write.py 未实现该类型的校验功能。")
        return call_on_finish(-1, listener)

    return run_action(run, run_on_subthread)
