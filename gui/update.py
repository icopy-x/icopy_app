"""
    更新程序的封装
"""
import os
import shutil
import subprocess
import time

import executor
import hmi_driver
import resources
import version
import ymodem


def check_flash():
    """
        检测STM32的flash资源是否需要更新
    :return:
    """
    res = resources.get_fws("flash")
    res = list(filter(lambda item: "filelib" in item, res))
    return res


def check_stm32():
    """
        检测STM32的APP是否需要更新
    :return:
    """
    res = resources.get_fws("app")
    res = list(filter(lambda item: "nib" in item, res))
    return res


def check_pm3():
    """
        检测PM3是否有固件需要更新
    :return:
    """
    res = resources.get_fws("pm3")
    res = list(filter(lambda item: "elf" in item, res))
    return res


def check_linux():
    """
        检测linux有没有啥需要更新的
    :return:
    """
    res = resources.get_fws("linux")
    res = list(filter(lambda item: "zip" in item or "linux" in item, res))
    return res


def check_all():
    """
        检测是否有更新包可以更新
    :return:
    """

    # 但凡有一个非必要固件可以更新，
    # 我们就需要前往更新
    update_available_count = [
        len(check_flash()),
        len(check_linux()),
    ]
    return max(update_available_count) > 0


def delete_fw_if_no_update(file):
    """
        删除固件文件，如果不需要更新
            这样子可以直接跳过动态版本号检测
            提升加载速度，因为如果存在固件文件
            更新器要去动态获取当前设备相关的固件信息
            会导致开机后在主页面的加载速度变慢
    :param file: 对应的要删除的固件包文件
    :return:
    """
    # 我们直接删除文件，避免下次进入检测，
    try:
        os.remove(file)
    except Exception as e:
        print(e)
    return


def parser_nib_info(nib_file):
    """
        解析经过我们处理的nib文件中的信息
        nib就是在文件头加了固定100个字节的长度的bin文件！
    :param nib_file:
    :return:
    """
    try:
        with open(nib_file, mode="rb") as fd:
            # 第一步，读出所有的数据
            data = fd.read()
            if len(data) < 100:
                raise Exception("文件的字节长度小于100，这个不是一个正常的长度！")

            data = data[:100]

            # 第二步，查看头部是否符合规范
            if data[0] != 0x0D:
                raise Exception("包头0不是0x0D: " + str(data[0]))
            if data[1] != 0x0A:
                raise Exception("包头1不是0x0A: " + str(data[1]))

            if data[-2] != 0x0D:
                raise Exception("包尾0不是0x0D是: " + str(data[-2]))
            if data[-1] != 0x0A:
                raise Exception("包尾1不是0x0A是: " + str(data[-1]))

            # 第三，封装成对用的字典进行返回
            return {
                "base_program_addr": int.from_bytes(data[2:6], byteorder='big', signed=False),
                "base_version_addr": int.from_bytes(data[6:10], byteorder='big', signed=False),
                "final_addr": int.from_bytes(data[10:14], byteorder='big', signed=False),
                "ver_major": int(data[14]),
                "ver_minor": int(data[15]),
            }

    except Exception as e:
        print("解析时出现错误: ", e)
        return None

    return None


def check_hmi_update():
    """
        检测HMI的主程序更新
    :return:
    """
    fws = check_stm32()
    # 首先，我们需要看nib文件是否存在
    if len(fws) > 0:
        fw = fws[0]  # 只会有一个，所以我们取出第一个

        # 固件存在，我们需要判断当前的设备是否支持更新HMI的固件
        if not version.is_fw_update_support():
            print("check_hmi_update() 检测到当前的设备不支持更新HMI固件")
            delete_fw_if_no_update(fw)
            return False

        # 支持更新固件的话，我们取出检索到的固件文件信息
        nib_info = parser_nib_info(fw)  # 然后，我们需要解析出来，当前的nib文件中的信息，确认版本
        if nib_info is None:
            print("无法解析nib文件，禁止更新hmi！")
            delete_fw_if_no_update(fw)
            return False

        # ok, 我们解析信息完成了，接下来需要进行信息对比
        ver_from_nib = float(f"{nib_info['ver_major']}.{nib_info['ver_minor']}")
        ver_from_hmi = version.getHMI_Dynamic()

        print("文件中的版本信息是: ", ver_from_nib, "类型是: ", type(ver_from_nib))
        print("硬件中的版本信息是: ", ver_from_hmi, "类型是: ", type(ver_from_hmi))

        if ver_from_hmi == ver_from_nib:
            print("当前已经是这个版本的固件了，跳过更新！")
            delete_fw_if_no_update(fw)
            return False

        # 否则，我们可以更新HMI的固件
        return True

    # 如果nib文件直接不存在，我们禁止更新hmi
    return False


def check_pm3_update():
    """
        检测PM3是否可以更新固件的一个实现
        如果 hw ver 返回来的信息在我们的预期内的话
        我们就不需要更新了，因为说明已经更新过了
    :return:
    """
    fws = check_pm3()
    # 首先，我们需要看pm3的固件文件是否存在
    if len(fws) > 0:
        fw = fws[0]

        # 固件存在，我们需要判断当前的固件是否已经是最新的了
        # 如果是的话，我们就不需要更新了
        if version.is_pm3_fw_same():
            print("check_pm3_update() 检测到当前的PM3固件已经是最新的了")
            delete_fw_if_no_update(fw)
            return False

        # 否则的话，我们就可以去更新了
        return True

    return False


def enter_bl():
    """
        进入
    :return:
    """
    print("正在尝试进入BL")
    # 打开32的BL下载模式
    hmi_driver.gotobl()
    print("命令执行完成...")
    # 判断结果
    while True:
        try:
            line = hmi_driver.readline(True)
            print("获取到的行: ", line)

            if "BL Starting" in line:
                print("正在进入BL中...")
                continue

            if "BL Error" in line:
                print("BL进入失败")
                return False

            if "Wait for SEL" in line:
                print("进入BL成功")
                return True
        except Exception as e:
            print("进入BL时出现异常: ", e)
            break
    return False


def _send_start_cmd(mode):
    """
        发送启动指令
    :param mode:
    :return:
    """
    modeByte = int(mode + 0x30).to_bytes(length=1, byteorder='big', signed=True)
    hmi_driver.ser_putc(modeByte)


def _update_send_file(mode, file, call, addr=b"0x000000", retry_max=3):
    """
        发送文件到YModem
    :return:
    """
    print("开始进入更新模式")
    if retry_max == 0:
        _send_start_cmd(3)
        return False
    print("更新模式: ", mode)

    # 发送相关的ascii，进入对应的更新模式
    _send_start_cmd(mode)

    print("更新模式进入成功...")

    if mode == 4:  # 选择4是flash数据，需要传输地址
        # 等待对方接收地址
        # 判断结果
        while True:
            try:
                line = hmi_driver.readline(True)
                print("获取到的行: ", line)

                if "Waiting for the Address" in line:
                    print("可以进行地址的传输，此次传输的地址是: ", addr)
                    time.sleep(0.1)
                    # 传输地址
                    # 发送写入的地址，开始写入
                    hmi_driver.ser_putc(addr + b"\r\n")
                    time.sleep(1)
                    continue

                if "ok,address =" in line:
                    print("地址传输完成，返回的地址是: ", line)
                    break

            except Exception as e:
                print("刷写FLASH出现异常: ", e)
                break

    hmi_driver.ser_flush()
    time.sleep(1)

    print("开始创建YModem对象进行文件传输")

    # 创建YMODEM的实现
    modem = ymodem.YModemSTM32(hmi_driver.ser_getc, hmi_driver.ser_putc)
    try:
        # 发送文件过去
        with open(file, mode="rb") as fd:
            print("开始发送文件")
            modem.send(
                fd,
                os.path.basename(file),
                file_size=os.path.getsize(file),
                callback=call
            )
            print("发送文件成功")
    except Exception as e:
        print("_update_send_file() -> ", e)

    need_retry = False

    # 读取结果判定
    while True:
        try:
            line = hmi_driver.readline(True)
            print("获取到的行: ", line)

            if "LARGE" in line:
                print("文件超出STM32的预期，不允许传输保存。")
                break

            retry_1 = "Verification failed" in line
            retry_2 = "Aborted by user" in line
            retry_3 = "Failed to receive the file" in line
            if retry_1 or retry_2 or retry_3:
                print("校验失败，将会重新启动发送")
                need_retry = True
                break

            if "Wait for SEL" in line:
                print("刷写完成！！！")
                return True

        except Exception as e:
            print("刷写固件出现异常: ", e)
            break

    if need_retry:
        return _update_send_file(mode, file, call, addr, retry_max - 1)

    return False


def _update_flash(file, call):
    """
        更新STM32的Flash
    :param file: 更新的文件
    :return:
    """
    try:
        if not enter_bl():
            raise Exception("进入BootLoader失败")
        _update_send_file(4, file, call)
        # 需要重启STM32
        hmi_driver.ser_flush()
        time.sleep(1)
        hmi_driver.ser_putc(b"3")
        # 发送完成后回到readline mode
        hmi_driver.ser_cmd_mode()
        return True
    except Exception as e:
        print(e)
    finally:
        # 务必删除文件
        os.remove(file)
    return False


def _make_nib_2_bin(file):
    """
        将nib文件转为bin文件，在原先的基础上
    :param file:
    :return:
    """
    try:
        # 尝试解析nib，无法解析的话，说明nib文件有问题
        if parser_nib_info(file) is None:
            return False

        with open(file, mode="rb") as fd:
            datas = fd.read()
            # 跳过100个字节，然后写回去
            datas = datas[100:]

        with open(file, mode="wb") as fd:
            fd.write(datas)
    except Exception as e:
        print("转换文件失败，异常是: ", e)
        return False

    return True


def _make_nib_only(file):
    """
        确保是nib文件，并且转换为bin文件
    :param file:
    :return:
    """
    if not str(file).endswith(".nib"):
        raise Exception("不要使用不是nib文件的更新包！")

    if not _make_nib_2_bin(file):
        raise Exception("转换nib为bin失败！")


def _update_stm32(file, call):
    """
        单独更新STM32的APP
    :param file:
    :param call:
    :return:
    """
    try:
        if not enter_bl():
            raise Exception("进入BootLoader失败")

        _update_send_file(1, file, call)
        print("发送文件成功")
        # 需要重启STM32
        hmi_driver.ser_flush()
        time.sleep(1)
        hmi_driver.ser_putc(b"3")
        print("重启32成功")
        # 发送完成后回到readline mode
        hmi_driver.ser_cmd_mode()
        print("hmi_driver回到readline模式成功")
        return True
    except Exception as e:
        print(e)
    finally:
        # 务必删除文件
        os.remove(file)
    return False


def _update_stm32_flash_both(app_file, flash_file, call):
    """
        一起更新32的APP和闪存资源
    :param app_file:
    :param flash_file:
    :param call:
    :return:
    """
    try:
        if not enter_bl():
            raise Exception("进入BootLoader失败")

        _update_send_file(1, app_file, call)
        _update_send_file(4, flash_file, call)
        # 需要重启STM32
        hmi_driver.ser_flush()
        time.sleep(1)
        hmi_driver.ser_putc(b"3")
        # 发送完成后回到readline mode
        hmi_driver.ser_cmd_mode()
        return True
    except Exception as e:
        print(e)
    finally:
        # 务必删除文件
        os.remove(app_file)
        os.remove(flash_file)
    return False


def _unpack_zipfile(filename, extract_dir, call, name_force=None):
    """Unpack zip `filename` to `extract_dir`
    """
    import zipfile  # late import for breaking circular dependency

    if not zipfile.is_zipfile(filename):
        raise shutil.ReadError("%s is not a zip file" % filename)

    zip_tmp = zipfile.ZipFile(filename)
    try:
        uncompress_size = sum((file.file_size for file in zip_tmp.infolist()))
        extracted_size = 0
        for info in zip_tmp.infolist():
            name = info.filename
            extracted_size += info.file_size

            if name_force is not None:
                name = name_force
            call(extracted_size, uncompress_size, name)

            # don't extract absolute paths or ones with .. in them
            if name.startswith('/') or '..' in name:
                continue

            target = os.path.join(extract_dir, *name.split('/'))
            if not target:
                continue

            dirname = os.path.dirname(target)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)

            if not name.endswith('/'):
                # file
                data = zip_tmp.read(info.filename)
                f = open(target, 'wb')
                try:
                    f.write(data)
                finally:
                    f.close()
                    del data
    finally:
        zip_tmp.close()


def _update_linux_dtb_resources(res, call):
    """
        更新linux
    :param res:
    :return:
    """
    try:
        # 直接执行指令，解压到目标目录
        _unpack_zipfile(res, "/boot", call, name_force="linux")
    except Exception as e:
        print("_update_linux_dtb_resources() -> ", e)
    finally:
        try:
            # 解压完了之后，删除源文件
            os.remove(res)
        except:
            pass


def _update_pm3_firmware(res, call):
    """
        更新PM3的固件资源
    :param res:
    :param call:
    :return:
    """
    proxamrk3_exe = "/home/pi/ipk_app_main/pm3/proxmark3"
    # image_file = "/mnt/upan/fullimage.elf"
    serial_port = "/dev/ttyACM0"

    try:
        call(10, 100, res)

        # 先取消对PM3的使用
        executor.startPM3Ctrl("stop")

        call(15, 100, res)

        # 然后重启PM3
        hmi_driver.restartpm3()
        for count in range(5):
            time.sleep(1)
            call(15 + (count + 1), 100, res)

        call(22, 100, res)

        cmd = f"sudo {proxamrk3_exe} {serial_port} --flash --image {res}"
        if os.path.exists(res):
            pi = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            while pi.poll() is None:
                outline = str(pi.stdout.readline())
                print(outline)

                if "Waiting for Proxmark3" in outline:
                    call(30, 100, res)

                if "Entering bootloader" in outline:
                    call(40, 100, res)

                if "Flashing..." in outline:
                    call(60, 100, res)

                if "All done" in outline:
                    call(80, 100, res)

                if "Have a nice day" in outline:
                    call(99, 100, res)
        else:
            raise Exception("没有看到固件包")
    except Exception as e:
        print(e)
    finally:
        delete_fw_if_no_update(res)
        # 重启PM3
        hmi_driver.restartpm3()
        executor.startPM3Ctrl("restart")
        # 无论如何都通知结束
        call(100, 100, res)


def start(listener):
    """
        开始进行更新
    :return:
    """

    def call(v1, v2, v3):
        """
            基础回调
        :param v1:
        :param v2:
        :param v3: 文件名
        :return:
        """
        listener({
            "finish": False,
            #       当前进度 总大小 文件名
            "progress": (v1, v2, v3)
        })

    need_wait_apo = False

    try:
        # 判断是否需要更新PM3
        pm3_fws = check_pm3()
        # 首先，我们需要看pm3的固件文件是否存在
        if len(pm3_fws) > 0:
            pm3_fw = pm3_fws[0]
            _update_pm3_firmware(pm3_fw, call)
        else:
            print("未发现有效的PM3系列固件更新")

        # 判断是否有linux的固件更新
        linux_fws = check_linux()
        if len(linux_fws) > 0:
            for file in linux_fws:
                if file.endswith(".zip"):  # 只支持zip压缩包
                    _update_linux_dtb_resources(file, call)
        else:
            print("未发现有效的DTB相关的资源更新")

        # 谨记，谨记！！！
        # STM32 控制了PM3的电源状态
        # 所有的更新，都要在更新STM32之前执行，避免被
        # 异常的STM32状态干扰

        # 判断是否同时有32和flash的固件需要更新
        flash_fws = check_flash()
        stm32_fws = check_stm32()
        # 判断是否需要更新 hmi 的逻辑固件
        if check_hmi_update():
            need_wait_apo = True
            # 得到第一个固件
            stm32_fw = stm32_fws[0]
            # 再确保是刷bin文件
            _make_nib_only(stm32_fw)

            # 如果两个固件同时都有，则一起刷，然后再重启
            if len(flash_fws) > 0:
                _update_stm32_flash_both(stm32_fw, flash_fws[0], call)
            else:
                _update_stm32(stm32_fw, call)

        elif len(flash_fws) > 0:
            _update_flash(flash_fws[0], call)
        else:
            print("未发现有效的HMI系列固件更新")

    except Exception as e:
        print(e)
    finally:
        listener({"finish": True, "wait_apo": need_wait_apo})

    return
