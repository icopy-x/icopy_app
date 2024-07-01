# -*- coding: UTF-8 -*-

import re
import time
import socket
import select
import platform
import threading

import hmi_driver

# 缓存的执行输出内容
CONTENT_OUT_IN__TXT_CACHE = ""
# 是否是啰嗦输出模式
PRINT_V_MODE = True
# 是否结束任务执行
LABEL_PM3_CMD_TASK_STOP = False
# 等待任务结束
LABEL_PM3_CMD_TASK_STOPPING = False
# 是否在执行任务
LABEL_PM3_CMD_TASK_RUNNING = False

# 部署机
PM3_REMOTE_ADDR = "127.0.0.1"

# 测试开始 <
# 远程PM3的地址
if platform.system() == 'Windows':
    PM3_REMOTE_ADDR = "10.30.0.16"  # 手持机调试机
# 测试结束 >

# PM3远程执行命令的服务端口
PM3_REMOTE_CMD_PORT = 8888
# 任务执行超时的返回值
CODE_PM3_TASK_ERROR = -1

# 执行器回调
LIST_CALL_PRINT = set()
LOCK_CALL_PRINT = threading.RLock()

LOCK_THREAD = threading.RLock()


def isPM3Offline(lines):
    """
        判断PM3是否是离线状态
    """
    return "Nikola.D.OFFLINE" in lines


def isUARTTimeout(lines):
    """
        判断是否写PM3的UART超时了
    """
    return "UART:: write time-out" in lines


def isCMDTimeout(lines):
    """
        命令执行超时
    :param lines:
    :return:
    """
    return "timeout while waiting for reply" in lines


def _set_stopping(status):
    global LABEL_PM3_CMD_TASK_STOPPING
    try:
        LOCK_THREAD.acquire()
        LABEL_PM3_CMD_TASK_STOPPING = status
    finally:
        LOCK_THREAD.release()


def _set_stopped(status):
    global LABEL_PM3_CMD_TASK_STOP
    try:
        LOCK_THREAD.acquire()
        LABEL_PM3_CMD_TASK_STOP = status
    finally:
        LOCK_THREAD.release()


def _set_running(status):
    global LABEL_PM3_CMD_TASK_RUNNING
    try:
        LOCK_THREAD.acquire()
        LABEL_PM3_CMD_TASK_RUNNING = status
    finally:
        LOCK_THREAD.release()


def _stop_task_user():
    if LABEL_PM3_CMD_TASK_STOP:
        # 停止任务
        _set_stopped(False)
        _set_running(False)
        _set_stopping(False)
        print("发现取消动作，将会直接取消执行，然后执行PM3组件重启: ")
        if reworkPM3All():
            print(" -> 重启PM3组件成功")
        else:
            print(" -> 重启PM3组件失败")
        return True
    return False


def _wait_if_stopping():
    """
        如果有任务在停止中，则我们需要暂停等待
    :return:
    """
    # 等待上一次的任务执行完成
    global LABEL_PM3_CMD_TASK_STOPPING
    if LABEL_PM3_CMD_TASK_STOPPING:
        print("发现正在停止中的任务，将会等待上一次任务停止完成。")
        while LABEL_PM3_CMD_TASK_STOPPING: time.sleep(0.1)


def add_task_call(call):
    """
        设置PM3指令执行器的全局回调
    :param call:
    :return:
    """
    with LOCK_CALL_PRINT:
        LIST_CALL_PRINT.add(call)


def del_task_call(call):
    """
        删除PM3执行指令的全局回调
    :param call:
    :return:
    """
    with LOCK_CALL_PRINT:
        if call in LIST_CALL_PRINT:
            LIST_CALL_PRINT.remove(call)


def startPM3Task(cmd, timeout, listener=None, rework_max=2):
    """
        执行PM3指令, 如果设置了listener，则实时打印消息
    """
    if rework_max < 0:
        print("执行失败，超过指定的自动重试次数")
        return -1

    # 定义以及初始化标志位
    global LABEL_PM3_CMD_TASK_STOP, LABEL_PM3_CMD_TASK_RUNNING, CONTENT_OUT_IN__TXT_CACHE

    # 判断是否需要停止任务
    if _stop_task_user(): return CODE_PM3_TASK_ERROR

    # 等待上一个任务退出（如果有）
    _wait_if_stopping()

    if PRINT_V_MODE: print("****************************************************************")

    # 重置变量
    _set_stopped(False)
    _set_running(True)
    # 返回值
    ret = 1

    # 转换命令为字节流
    if isinstance(cmd, str):
        cmd = "Nikola.D.CMD = {}\r\n".format(cmd)
        cmd = cmd.encode("ascii")

    if PRINT_V_MODE: print("开始执行命令 " + str(cmd))

    # 创建PM3的套接字
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        t = client.gettimeout()
        client.settimeout(3)
        print("正在执行连接到执行器......")
        client.connect((PM3_REMOTE_ADDR, PM3_REMOTE_CMD_PORT))
        print("连接执行器成功！")
        client.settimeout(t)
    except Exception as e:
        print("连接失败，将尝试启动PM3命令执行器: ", e)
        if reworkPM3All():
            print("自动启动成功，将会重新执行命令")
            return startPM3Task(cmd, timeout, listener, rework_max - 1)
        else:
            print("PM3命令执行器启动失败")
            _set_running(False)
            return CODE_PM3_TASK_ERROR
    # 开始执行指令
    try:
        client.sendall(cmd)
        # 设置为非堵塞型操作
        client.setblocking(False)
        if PRINT_V_MODE: print("命令发送成功，开始进入接收")
        start_time_ms = time.perf_counter_ns() * 0.000001

        # 缓冲读取 \r \n \r\n
        buffer_on_rn = bytearray()
        # 内容缓冲区
        buffer_on_all = bytearray()

        while True:

            # 判断是否需要停止任务
            if _stop_task_user(): return CODE_PM3_TASK_ERROR

            current_time = time.perf_counter_ns() * 0.000001 - start_time_ms
            # print("当前的执行时间: ", current_time)
            if timeout > 0 and (current_time > timeout):
                print("接收超时，停止接收，并且尝试重启" + str(rework_max) + "次。")
                if rework_max == 0:
                    print("接收超时但是不需要尝试重启重试，将直接返回错误。")
                    return CODE_PM3_TASK_ERROR
                if reworkPM3All():
                    return startPM3Task(cmd, timeout, listener, rework_max - 1)
                else:
                    print("Socket接收超时且重启失败")
                    ret = CODE_PM3_TASK_ERROR
                break

            # 轮询数据缓冲区的变动
            in_fds, out_fds, err_fds = select.select([client, ], [], [], 0)
            if len(in_fds) == 0:
                time.sleep(0.01)
                continue

            # 有数据更新呢，可以接收
            byte_array = client.recv(1024 * 512)
            if len(byte_array) == 0:
                time.sleep(0.01)
                continue

            # 添加到缓冲区中
            buffer_on_all.extend(byte_array)
            buffer_on_rn.extend(byte_array)

            # 实时回调函数处理每行数据
            if callable(listener) or len(LIST_CALL_PRINT) > 0:
                has_r = buffer_on_rn.endswith(b"\r")
                has_n = buffer_on_rn.endswith(b"\n")
                has_rn = buffer_on_rn.endswith(b"\r\n")
                # 判断是否有换行输出
                if has_r or has_n or has_rn:
                    text_print = ''.join(buffer_on_rn.decode("utf-8", errors='ignore'))
                    if callable(listener):
                        listener(text_print)
                    for call_obj in LIST_CALL_PRINT:
                        try:
                            if callable(call_obj):
                                call_obj(text_print)
                        except Exception as e:
                            print("在进行输出回调的时候出现异常: ", e)
                    # 清空缓冲区
                    buffer_on_rn.clear()

            # 转换全部的字节缓冲区为字符串，然后进行处理
            tmp_str_buffer = ''.join(buffer_on_all.decode("utf-8", errors='ignore'))

            # 判断PM3的UART执行是否超时
            if isUARTTimeout(tmp_str_buffer) or isCMDTimeout(tmp_str_buffer):
                if isUARTTimeout(tmp_str_buffer):
                    print("PM3写UART超时，将会重启所有的PM3组件")
                if isCMDTimeout(tmp_str_buffer):
                    print("PM3执行命令超时，硬件端没有回复，将会重启所有的PM3组件")
                if reworkPM3All():
                    print("PM3所有的组件都重启成功")
                    return startPM3Task(cmd, timeout, listener, rework_max - 1)
                else:
                    print("PM3所有的组件中有重启失败的项目，请处理此异常。")
                    ret = CODE_PM3_TASK_ERROR
                    break

            # 发现了PM3离线的消息行
            if isPM3Offline(tmp_str_buffer):
                client.close()
                print("PM3离线，正在检查并重连")
                # 如果重连成功，则递归自身进行命令的重新执行
                if reworkPM3All():
                    print("PM3重启成功，命令将会重新执行")
                    return startPM3Task(cmd, timeout, listener, rework_max - 1)
                else:
                    _set_running(False)
                    return CODE_PM3_TASK_ERROR  # 重启失败了，直接返回超时告知PM3出现超时异常

            # 判断是否发现了正常的命令执行结束行
            end_line = "Nikola.D:"
            start_line = "pm3 -->"
            if end_line in tmp_str_buffer:
                # 先删除一次空白字符
                tmp_str_buffer = tmp_str_buffer.strip()
                # 删除头部
                if start_line in tmp_str_buffer:
                    tmp_str_buffer = tmp_str_buffer[tmp_str_buffer.index("\n", tmp_str_buffer.index(start_line)):]
                # 删除尾部
                tmp_str_buffer = tmp_str_buffer[:tmp_str_buffer.index(end_line) - 1]
                # 删除空白字符
                CONTENT_OUT_IN__TXT_CACHE = tmp_str_buffer
                if PRINT_V_MODE:
                    print("检测到通信结束协议字符，通信完成: ")
                    print(CONTENT_OUT_IN__TXT_CACHE, "\n")
                break

        if PRINT_V_MODE: print("命令执行时间(ms): ", time.perf_counter_ns() * 0.000001 - start_time_ms)
    except Exception as e:
        print("数据交互的过程出现了异常: ", e)
        if platform.system() == "Windows":
            raise e
        ret = CODE_PM3_TASK_ERROR
    # 重置运行时的标志位
    _set_running(False)
    try:
        # 关闭客户端链接，释放资源
        client.close()
    except Exception as e:
        print(e)
    if PRINT_V_MODE: print("执行命令完成")
    if PRINT_V_MODE: print("****************************************************************\n")
    return ret


def stopPM3Task(listener=None, wait=True):
    """
        结束PM3的任务执行
    """
    global LABEL_PM3_CMD_TASK_STOP, LABEL_PM3_CMD_TASK_STOPPING

    if not LABEL_PM3_CMD_TASK_RUNNING:
        print("PM3没有任务在执行，不需要结束。")
        return

    if LABEL_PM3_CMD_TASK_STOPPING:
        print("当前正在结束中，不需要重复调用")
        return

    _set_stopped(True)
    _set_stopping(True)

    def waitStop():
        """等待任务结束"""
        if wait:
            while True:
                if not LABEL_PM3_CMD_TASK_STOP:
                    return
                print("等待任务结束中...")
                time.sleep(0.01)

    if wait:
        # 没有回调，堵塞执行
        if listener is None:
            waitStop()
        else:  # 有回调，开启子线程执行
            threading.Thread(target=waitStop).start()
    else:  # 有回调，开启子线程执行
        threading.Thread(target=waitStop).start()
    return


def startPM3Ctrl(ctrl_cmd, timeout=5888):
    """
        执行PM3的控制命令，并且获得响应的返回
    """
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        c.connect((PM3_REMOTE_ADDR, PM3_REMOTE_CMD_PORT))
    except Exception as e:
        print("警告，PM3控制器可能未启动，你是否忘了执行启动远端管理器？")
        print("socket异常信息：", e)
        return "Failed"
    if isinstance(ctrl_cmd, str):
        ctrl_cmd = "Nikola.D.CTL = {}\r\n".format(ctrl_cmd)
        ctrl_cmd = ctrl_cmd.encode("ascii")

    c.send(ctrl_cmd)
    resp = ""
    start_time_ms = time.perf_counter_ns() * 0.000001
    while True:
        current_time = time.perf_counter_ns() * 0.000001 - start_time_ms
        # print("当前的执行时间: ", current_time)
        if timeout > 0 and (current_time > timeout):
            break

        line = c.recv(1024).decode("ascii").strip('\x00')
        resp += line
        if len(resp) > 1:
            print("接收到的控制回传数据: ", line)
            break
        time.sleep(0.01)

    try:
        c.close()
        # print("待转换的值: ", resp)
        if 'True' in resp:
            resp = True
        elif 'False' in resp:
            resp = False
        else:
            raise Exception("Invalid BOOL string: " + resp)
        return resp
    except Exception as e:
        print("无法转换控制指令的返回结果为BOOL类型: ", e)
        return False


def startPM3Plat(plat_cmd, timeout=5888):
    """
        执行PM3所在的平台的控制指令，并且获得相应的返回
    :param timeout:
    :param plat_cmd:
    :return:
    """
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        c.connect((PM3_REMOTE_ADDR, PM3_REMOTE_CMD_PORT))
    except Exception as e:
        print("警告，PM3控制器可能未启动，你是否忘了执行启动远端管理器？")
        print("socket异常信息：", e)
        return "Failed"

    label = "Nikola.D.PLT"
    if isinstance(plat_cmd, str):
        plat_cmd = "{} = {}\r\n".format(label, plat_cmd)
        plat_cmd = plat_cmd.encode("ascii")

    c.send(plat_cmd)
    resp = list()
    start_time_ms = time.perf_counter_ns() * 0.000001
    try:
        while True:
            current_time = time.perf_counter_ns() * 0.000001 - start_time_ms
            # print("当前的执行时间: ", current_time)
            if timeout > 0 and (current_time > timeout):
                break

            line = c.recv(1024).decode("ascii").strip('\x00')
            resp.append(line)
            if label in ''.join(resp):
                break
            time.sleep(0.01)
    except Exception as e:
        print("接收平台指令执行器的返回失败: ", e)
        return None

    try:
        c.close()
        return ''.join(resp).rstrip(label)
    except Exception as e:
        print("无法转换控制指令的返回结果为BOOL类型: ", e)
        return None


def getPrintContent():
    """
        获取执行命令的输出内容
    """
    return CONTENT_OUT_IN__TXT_CACHE


def isEmptyContent():
    """
        判断是否是空的输出
    """
    content = CONTENT_OUT_IN__TXT_CACHE
    if len(content) == 0: return False
    if content.isspace(): return True
    ret = re.findall(r"[\S]+", content)
    b_ret = len(ret) <= 0
    return b_ret


def getContentFromRegexAll(regex):
    """
        利用正则进行内容获取，返回所有的组
    """
    sea_obj = re.search(regex, CONTENT_OUT_IN__TXT_CACHE, re.M)
    if sea_obj is not None:
        return sea_obj.groups()
    else:
        return []


def getContentFromRegexA(regex):
    """
        获取所有重复匹配的目标
    """
    return re.findall(regex, CONTENT_OUT_IN__TXT_CACHE, re.M)


def getContentFromRegexG(regex, group):
    """
        利用正则进行内容获取，允许使用组
    """
    sea_obj = getContentFromRegexAll(regex)
    if len(sea_obj) <= 0:
        return ""
    ret = sea_obj[group - 1]
    del sea_obj
    return ret


def hasKeyword(keywords, line=None):
    """
        是否在输出中发现了相关的关键字
    """
    if line is None: line = CONTENT_OUT_IN__TXT_CACHE
    if len(line) == 0: return False
    ret = re.findall(keywords, line)
    b_ret = len(ret) > 0
    del ret
    return b_ret


def getContentFromRegex(regex):
    """
        利用正则进行内容获取
    """
    return getContentFromRegexG(regex, 0)


def connect2PM3(serial_port=None, baudrate=None):
    """
        连接到PM3,使用指定的串口号
    """
    cmd = "hw connect"
    if serial_port is not None:
        cmd += (" p " + serial_port)
    if baudrate is not None:
        cmd += (" b " + str(baudrate))
    if startPM3Task(cmd, 1000) != CODE_PM3_TASK_ERROR:
        return hasKeyword("Communicating with PM3")
    return False


def reworkPM3All():
    """
        重启PM3所有可能出现问题的组件，
        比如proxmark3的可执行文件，
        和proxmark3的硬件。
    """
    # 重启软件，使用控制指令
    # 先删除已经存在的串口
    startPM3Ctrl("stop")
    startPM3Plat("sudo rm /dev/ttyACM0")
    hmi_driver.restartpm3()
    startPM3Ctrl("restart")
    return True


if __name__ == '__main__':
    hmi_driver.starthmi("COM4")
    reworkPM3All()
    startPM3Task("hf 14a info", 5000)
