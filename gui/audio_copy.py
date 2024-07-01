"""
    复制卡时需要的音频操作
"""
import audio
import container


def playReadyForCopy(chk=False, infos=None):
    """
        播放操作引导-写卡提示
    :return:
    """
    try:
        typ = infos["type"]
        if typ != -1 and typ is not None and typ in container.containermap:
            contcons = container.get_audio_typ(infos)
            print("获取到的音频标注信息:", contcons)
            if contcons is not None:
                if contcons[2] != "":
                    filesubid = contcons[2]
                else:
                    return None
            else:
                return None
        else:
            if typ not in container.containermap:
                print("playReadyForCopy", "发现了未被注册语音提示音频的卡片类型，请处理。")
            return None

        if filesubid is None:
            print("playReadyForCopy", "发现了未被注册的语音文件类型，请处理。")
            return None

        res = "11"
        if chk:
            return int(res + filesubid)
        file = audio.__audio_dir + res + "." + filesubid + audio.__audio_file_ext
        audio.play(file)
    except Exception as e:
        print("playReadyForCopy", e)

    return None
