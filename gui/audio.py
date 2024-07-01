"""
    音频播放
    pygame 安装文章
    看：
        1、https://blog.csdn.net/ablo_zhou/article/details/4901589          自动安装的过程，不推荐用，会自动依赖py2
        2、https://wii.leseratte10.de/devkitPro/other-stuff/libraries/SDL/  手动编译需要的库
"""
import base64
import hashlib
import os
import platform
import re
import subprocess
import time

import pygame
import wave

from Crypto.Cipher import AES

import version
import resources

__default_framerate = 16000
__volume = 100
__stop_prev = True
__blocking_play = False
__key_audio_enable = True
__audio_dir = "res/audio/"
__audio_file_ext = ".wav"


def init():
    """
        初始化函数
    :return:
    """
    if pygame.mixer.get_init() is None:
        pygame.mixer.init(frequency=__default_framerate)


def setVolume(v):
    """
        设置音量
    :param v:
    :return:
    """
    global __volume
    __volume = v


def setBlockingPlay(enable=__blocking_play):
    """
        进行堵塞播放
    :return:
    """
    global __blocking_play
    __blocking_play = enable


def get_framerate(name):
    """
        获取采样率
    :param name:
    :return:
    """
    try:
        with wave.open(name, "rb") as fd:
            return fd.getframerate()
    except Exception as e:
        print("get_framerate() -> ", e)
    return __default_framerate


def playOfVolumeImpl(n, v):
    """
        播放音频文件
        根据指定的音量！
    :param n: 音频文件名，完整的或者相对的路径
    :param v: 音量
    :return:
    """
    if __stop_prev:
        stop()
    init()
    sound_wav = pygame.mixer.Sound(n)
    if v == 0:
        v = 0
    else:
        v = v / 100
    sound_wav.set_volume(v)
    sound_wav.play()
    if __blocking_play:
        print("正在等待播放完毕...")
        print("播放长度: ", sound_wav.get_length())
        time.sleep(sound_wav.get_length())
        print("播放已完毕")
    # print("播放时的音量: ", volume)


def playOfVolume(name, volume):
    """
        播放音频文件
        根据指定的音量！
    :param name: 音频文件名，完整的或者相对的路径
    :param volume: 音量
    :return:
    """

    def try_make_zh_name():
        """
            生成中文文件名，如果文件存在
        :return:
        """
        audio_path_split = os.path.splitext(os.path.abspath(name))
        audio_zh_file = f"{audio_path_split[0]}_cn{audio_path_split[1]}"
        # print("生成的资源路径名称: ", audio_zh_file)
        if os.path.exists(audio_zh_file):
            return audio_zh_file
        return name

    maps = {
        "x": name,                      # 英文
        "xr": name,                     # 英文
        "zh": try_make_zh_name(),       # 中文
        "xs": name,                     # 英文
        "uk": name,                     # 英文
        "xsc": try_make_zh_name(),      # 中文
    }

    # 测试开始 <
    if platform.system() == "Windows":
        # TODO Windows调试阶段直接播放相关的测试需要的音频
        #  我们这里直接去播放设置好的设备对应类型的音频
        name = maps[resources.test_typ]
        playOfVolumeImpl(name, volume)
        return
    # 测试结束 >

    # 此处我们需要进行实时生成所需要播放的音频资源的文件名！
    # 验证开始 <
    try:
        # Serial          : 02c000814f54266f
        output_str = str(subprocess.check_output("cat /proc/cpuinfo", shell=True), errors='ignore')
        sn_str = re.search(r"Serial\s*:\s*([a-fA-F0-9]+)", output_str).group(1)
        sn_bytes = sn_str.encode("utf-8")  # Unicode字符串解码为字节流
        # 经过三次MD5 16后，我们获得了解密UID的秘钥
        m = hashlib.md5()
        m.update(sn_bytes)
        m.update(sn_bytes)
        m.update(sn_bytes)
        r = m.hexdigest()
        # 进行MD5求和
        count = 0
        key_device = ""  # 这个是秘钥，
        while count < len(r):
            tmp = format(int(r[count], 16) + int(r[count + 1], 16), "x")
            key_device += tmp[0]
            count += 2

        # 进行UID信息串的解密
        aes_obj = AES.new(
            key_device.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        destr = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        # 播放映射表中的音频文件
        playOfVolumeImpl(maps[destr[3]], volume)
    except Exception as e:
        print("无法通过验证，放弃播放音频", e)
        return None
    # 验证结束 >


def play(name):
    """
        播放音频
    :param name:
    :return:
    """
    # print("\n开始播放音频: ", name)
    playOfVolume(name, __volume)
    # print("\n")


def stop():
    """
        停止所有通道的播放
    :return:
    """
    if pygame.mixer.get_init() is not None:
        pygame.mixer.stop()


def setKeyAudioEnable(enable):
    """
        设置是否可以播放按键音
    :param enable:
    :return:
    """
    global __key_audio_enable
    __key_audio_enable = enable


# --------------------------------资源函数开始


def playKeyEnable(chk=False):
    """
        播放按键音
    :return:
    """
    # 仅在按键音播放使能时播放，避免一些情况下
    # 出现按键音与播放音冲突的问题
    res = "1"
    if chk:
        return int(res)
    if __key_audio_enable:
        play(__audio_dir + res + __audio_file_ext)


def playKeyDisable(chk=False):
    """
        播放按键不可用音
    :return:
    """
    # 仅在按键音播放使能时播放，避免一些情况下
    # 出现按键音与播放音冲突的问题
    res = "2"
    if chk:
        return int(res)
    if __key_audio_enable:
        play(__audio_dir + res + __audio_file_ext)


def playVolumeExam(v=100, chk=False):
    """
        播放音量例子
    :return:
    """
    res = "3"
    if chk:
        return int(res)
    playOfVolume(__audio_dir + res + __audio_file_ext, v)


def playMissingKey(chk=False):
    """
        播放操作引导-密码不完整
    :return:
    """
    res = "4"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playNoValidKeyHF(chk=False):
    """
        播放操作引导-无可用密码（高频卡）
    :return:
    """
    res = "5"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playNoValidKeyLF(chk=False):
    """
        播放操作引导-无可用密码（低频卡）
    :return:
    """
    res = "6"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playSniffStep1(chk=False):
    """
        播放操作引导-嗅探步骤1
    :return:
    """
    res = "7"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playSniffStep2(chk=False):
    """
        播放操作引导-嗅探步骤2
    :return:
    """
    res = "8"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playSniffStep3(chk=False):
    """
        播放操作引导-嗅探步骤3
    :return:
    """
    res = "9"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playSniffStep4(chk=False):
    """
        播放操作引导-嗅探步骤4
    :return:
    """
    res = "10"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playTagfound(chk=False):
    """
        播放卡片已找到提示
    :return:
    """
    res = "12"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playTagNotfound(chk=False):
    """
        播放卡片未找到提示
    :return:
    """
    res = "13"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playwrongTagfound(chk=False):
    """
        播放卡片未找到（或者错类型）提示
    :return:
    """
    res = "14"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playReadAll(chk=False):
    """
        播放卡片读取完毕(完全提取)提示
    :return:
    """
    res = "15"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playReadPart(chk=False):
    """
        播放卡片读取完毕(部分提取)提示
    :return:
    """
    res = "16"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playReadFail(chk=False):
    """
        播放卡片读取失败
    :return:
    """
    res = "17"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playMultiCard(chk=False):
    """
        播放多重卡片存在提示
    :return:
    """
    res = "18"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playWriteSuccess(chk=False):
    """
        播放卡片写入完毕提示
    :return:
    """
    res = "19"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playWriteFail(chk=False):
    """
        播放卡片写入失败提示
    :return:
    """
    res = "20"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playVerifiFail(chk=False):
    """
        播放卡片验证失败提示
    :return:
    """
    res = "21"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playVerifiSuccess(chk=False):
    """
        播放卡片验证成功提示
    :return:
    """
    res = "22"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playTraceFileSaved(chk=False):
    """
        播放嗅探文件保存成功提示
    :return:
    """
    res = "23"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playPCModeRunning(chk=False):
    """
        播放PCMode运行中提示
    :return:
    """
    res = "24"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playCancel(chk=False):
    """
        播放已取消提示
    :return:
    """
    res = "25"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playSniffing(chk=False):
    """
        播放正在嗅探提示
    :return:
    """
    res = "26"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playSimulating(chk=False):
    """
        播放正在模拟提示
    :return:
    """
    res = "27"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playProcessing(chk=False):
    """
        播放处理中的音频
    :return:
    """
    res = "36"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playScanning(chk=False):
    """
        播放扫描中的音频
    :return:
    """
    res = "28"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playReading1p32(chk=False):
    """
        播放读取中（1/32）的音频
    :return:
    """
    res = "29"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playReadingKeys(chk=False):
    """
        播放读取中的音频
    :return:
    """
    res = "30"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playWriting(chk=False):
    """
        播放写入中的音频
    :return:
    """
    res = "32"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playVerifying(chk=False):
    """
        播放验证中的音频
    :return:
    """
    res = "33"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playResultOnRight(chk=False):
    """
        播放出现正确结果的音频
    :return:
    """
    res = "37"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playResultOnWrong(chk=False):
    """
        播放出现错误结果的音频
    :return:
    """
    res = "38"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playChargingAudio(chk=False):
    """
        播放充电中的提示音
    :return:
    """
    res = "39"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


def playStartExma(chk=False, force=False):
    """
        播放开机音乐
    :return:
    """
    if force:
        play(__audio_dir + "start.wav")
    elif platform.system() != "Windows":
        res = "40"
        if chk:
            return int(res)
        play(__audio_dir + res + __audio_file_ext)


def playWarrning(chk=False):
    """
        播放警告提示音
    :return:
    """
    res = "41"
    if chk:
        return int(res)
    play(__audio_dir + res + __audio_file_ext)


if __name__ == '__main__':

    playOfVolume("res/audio/11.4.wav", 100)
    # playReadyForCopy(infos=infoo)
    while True: pass
