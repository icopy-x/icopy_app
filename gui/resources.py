import base64
import os
import re
import hashlib
import platform
import subprocess

from Crypto.Cipher import AES

import version


class StringEN:

    title = {
        "main_page":                            "Main Page",
        "auto_copy":                            "Auto Copy",
        "about":                                "About",
        "backlight":                            "Backlight",
        "key_enter":                            "Key Enter",
        "network":                              "Network",
        "update":                               "Update",
        "pc-mode":                              "PC-Mode",
        "read_tag":                             "Read Tag",
        "scan_tag":                             "Scan Tag",
        "sniff_tag":                            "Sniff TRF",
        "sniff_notag":                          "Sniff TRF",
        "volume":                               "Volume",
        "warning":                              "Warning",
        "missing_keys":                         "Missing keys",
        "no_valid_key":                         "No valid key",
        "no_valid_key_t55xx":                   "No valid key",
        "data_ready":                           "Data ready!",
        "write_tag":                            "Write Tag",
        "disk_full":                            "Disk Full",
        "snakegame":                            "Greedy Snake",
        "trace":                                "Trace",
        "simulation":                           "Simulation",
        "diagnosis":                            "Diagnosis",

        "wipe_tag":                             "Erase Tag",
        "time_sync":                            "Time Settings",

        "se_decoder":                           "SE Decoder",
        "write_wearable":                       "Watch",
        "card_wallet":                          "Dump Files",
        "tag_info":                             "Tag Info",
        "lua_script":                           "LUA Script",
    }

    button = {
        "button":                               "Button",
        "read":                                 "Read",
        "stop":                                 "Stop",
        "start":                                "Start",
        "reread":                               "Reread",
        "rescan":                               "Rescan",
        "retry":                                "Retry",
        "sniff":                                "Sniff",
        "write":                                "Write",
        "simulate":                             "Simulate",
        "finish":                               "Finish",
        "save":                                 "Save",
        "enter":                                "Enter",
        "pc-m":                                 "PC-M",
        "cancel":                               "Cancel",
        "rewrite":                              "Rewrite",
        "force":                                "Force",
        "verify":                               "Verify",
        "forceuse":                             "Force-Use",
        "clear":                                "Clear",
        "shutdown":                             "Shutdown",
        "yes":                                  "Yes",
        "no":                                   "No",
        "fail":                                 "Fail",
        "pass":                                 "Pass",
        "save_log":                             "Save",

        "wipe":                                 "Erase",
        "edit":                                 "Edit",
        "delete":                               "Delete",
        "details":                              "Details",
    }

    procbarmsg = {
        "reading":                              "Reading...",
        "writing":                              "Writing...",
        "verifying":                            "Verifying...",
        "scanning":                             "Scanning...",
        "updating_with":                        "Updating with: ",
        "updating":                             "Updating...",
        "t55xx_checking":                       "T55xx keys checking...",
        "t55xx_reading":                        "T55xx Reading...",
        "reading_with_keys":                    "Reading...{}/{}Keys",
        "remaining_with_value":                 "Remaining: {}s",
        "clearing":                             "Clearing...",
        "ChkDIC":                               "ChkDIC",
        "Darkside":                             "Darkside",
        "Nested":                               "Nested",
        "STnested":                             "STnested",
        "time>=10h":                            "    %02dh %02d'%02d''",
        "10h>time>=1h":                         "    %dh %02d'%02d''",
        "time<1h":                              "      %02d'%02d''",

        "wipe_block":                           "Erasing",
        "tag_fixing":                           "Repairing...",
        "tag_wiping":                           "Erasing...",
    }

    toastmsg = {
        "update_finish":                        "Update finish.",
        "update_unavailable":                   "No update available",
        "pcmode_running":                       "PC-mode Running...",
        "read_ok_2":                            "Read\nSuccessful!\nPartial data\nsaved",
        "read_ok_1":                            "Read\nSuccessful!\nFile saved",
        "read_failed":                          "Read Failed!",
        "no_tag_found2":                        "No tag found \nOr\n Wrong type found!",
        "no_tag_found":                         "No tag found",
        "tag_found":                            "Tag Found",
        "tag_multi":                            "Multiple tags detected!",
        "processing":                           "Processing...",
        "trace_saved":                          "Trace file\nsaved",
        "sniffing":                             "Sniffing in progress...",
        "t5577_sniff_finished":                 "T5577 Sniff Finished",
        "write_success":                        "Write successful!",
        "write_verify_success":                 "Write and Verify successful!",
        "write_failed":                         "Write failed!",
        "verify_success":                       "Verification successful!",
        "verify_failed":                        "Verification failed!",

        "you_win":                              "You win",
        "game_over":                            "Game Over",
        "game_tips":                            "Press 'OK' to start game.",
        "pausing":                              "Pausing",

        "trace_loading":                        "Trace\nLoading...",
        "simulating":                           "Simulation in progress...",
        "sim_valid_input":                      "Input invalid:\n{} greater than {}",
        "sim_valid_param":                      "Invalid parameter",

        "bcc_fix_failed":                       "BCC repair failed",
        "wipe_success":                         "Erase successful",
        "wipe_failed":                          "Erase failed",
        "keys_check_failed":                    "Time out",
        "wipe_no_valid_keys":                   "No valid keys，Please use 'Auto Copy' first, Then erase",
        "err_at_wiping":                        "Unknown error",
        "time_syncing":                         "Synchronizing system time",
        "time_syncok":                          "Synchronization successful!",

        "device_disconnected":                  "USB device is removed!",
        "plz_remove_device":                    "Please remove USB device!",

        "start_clone_uid":                      "Start writing UID",
        "unknown_error":                        "Unknown error.",
        "write_wearable_err1":                  "The original tag and tag(new)\n type is not the same.",
        "write_wearable_err2":                  "Encrypted cards are not supported.",
        "write_wearable_err3":                  "Change tag position on the antenna.",
        "write_wearable_err4":                  "UID write failed. Make sure the tag is placed on the antenna.",

        "delete_confirm":                       "Delete?",
        "opera_unsupported":                    "Invalid command",
    }

    itemmsg = {
        "missing_keys_msg1":                    "Option 1) Go to reader to sniff keys\n\n"
                                                "Option 2) Enter known keys manually",

        "missing_keys_msg2":                    "Option 3) Force read  to get partial data\n\n"
                                                "Option 4) Go into PC Mode to perform hardnest",

        "missing_keys_msg3":                    "Option 1) Go to reader to sniff keys.\n\n"
                                                "Option 2) Enter known keys manually.",

        "missing_keys_t57":                     "Option 1) Go to reader to sniff keys.\n\n"
                                                "Option 2) Enter known keys manually.",

        "enter_known_keys":                     "  Enter known keys",

        "aboutline1":                           "    {}",
        "aboutline2":                           "   HW  {}",
        "aboutline3":                           "   HMI {}",
        "aboutline4":                           "   OS  {}",
        "aboutline5":                           "   PM  {}",
        "aboutline6":                           "   SN  {}",

        "aboutline1_update":                    "Firmware update",
        "aboutline2_update":                    "1.Download firmware",
        "aboutline3_update":                    " icopy-x.com/update",
        "aboutline4_update":                    "2.Plug USB, Copy firmware to device.",
        "aboutline5_update":                    "3.Press 'OK' start update.",

        "valueline1":                           "Off",
        "valueline2":                           "Low",
        "valueline3":                           "Middle",
        "valueline4":                           "High",

        "blline1":                              "Low",
        "blline2":                              "Middle",
        "blline3":                              "High",

        "sniffline1":                           "Step 1: \nPrepare client's \nreader and tag, \nclick start.",
        "sniffline2":                           "Step 2: \nRemove antenna cover \n"
                                                "on iCopy and place \niCopy on reader.",
        "sniffline3":                           "Step 3: \nSwipe tag on iCopy \n"
                                                "to ensure reader \nable to identify tag.",
        "sniffline4":                           "Step 4: \nRepeat 3-5 times \nand click finish.",
        "sniffline_t5577":                      "Click start, then\nswipe iCopy on reader.\nUntil you get keys.",

        "sniff_item1":                          "1. 14A Sniff",
        "sniff_item2":                          "2. 14B Sniff",
        "sniff_item3":                          "3. iclass Sniff",
        "sniff_item4":                          "4. Topaz Sniff",
        "sniff_item5":                          "5. T5577 Sniff",

        "sniff_decode":                         "Decoding...\n{}/{}",
        "sniff_trace":                          "TraceLen: {}",

        "diagnosis_item1":                      "User diagnosis",
        "diagnosis_item2":                      "Factory diagnosis",

        "diagnosis_subitem1":                   "HF Voltage  ",
        "diagnosis_subitem2":                   "LF Voltage  ",
        "diagnosis_subitem3":                   "HF reader   ",
        "diagnosis_subitem4":                   "LF reader   ",
        "diagnosis_subitem5":                   "Flash Memory",
        "diagnosis_subitem6":                   "USB port    ",
        "diagnosis_subitem7":                   "Buttons     ",
        "diagnosis_subitem8":                   "Screen      ",
        "diagnosis_subitem9":                   "Sound       ",

        "key_item":                             "Key{}: ",
        "uid_item":                             "UID: ",

        "wipe_m1":                              "Erase MF1/L1/L2/L3",
        "wipe_t55xx":                           "Erase T5577",

        "write_wearable_tips1":                 "1. Copy UID\n\nWrite UID to tag(new), "
                                                "please place new card on iCopy antenna, then click 'start'",
        "write_wearable_tips2":                 "2. Record UID\n\nPlease use your watch "
                                                "to record the UID from the tag(new) and then click 'Finish'.",
        "write_wearable_tips3":                 "3. Write data\n\nplace your watch on iCopy antenna, "
                                                "then click 'start' to write data to your watch.",
    }

    tipsmsg = {
        "enter_known_keys_55xx":                "Enter a known key for \nT5577 or EM4305",
        "enter_55xx_key_tips":                  "Key:",
        "connect_computer":                     "Please connect to\nthe computer.Then\npress start button",
        "place_empty_tag":                      "Data ready for copy!\nPlease place new tag for copy.",
        "type_tips":                            "TYPE:",
        "disk_full_tips":                       "The disk space is full.\nPlease clear it after backup.",
        "start_diagnosis_tips":                 "Press start button to start diagnosis.",

        "installation":                         "During installation\ndo not turn off\n "
                                                "or power off, do not long press the button.",
        "start_install_tips":                   "Press 'Start' to install",
        "testing_with":                         "Testing with: \n{}",
        "test_music_tips":                      "Do you hear the music?",
        "test_screen_tips":                     "Press 'OK' to start test.\nPress 'OK' again to stop test.\n\n"
                                                "'UP' and 'DOWN' change screen color.",
        "test_screen_isok_tips":                "Is the screen OK?",
        "test_usb_connect_tips":                "Please connect to charger.",
        "test_usb_found_tips":                  "Does the computer have a USBSerial(Gadget Serial) found?",
        "test_usb_otg_tips":                    "1. Connect to OTG tester.\n"
                                                "2. Judge whether the power supply of OTG is normal?",
        "test_hf_reader_tips":                  "Please place Tag with 'IC Test'",
        "test_lf_reader_tips":                  "Please place Tag with 'ID Test'",
        "install_failed":                       "Install failed, code = {}",

        "iclass_se_read_tips":                  "\nPlease place\niClass SE tag on\n"
                                                "USB decoder\n\nDo not place\nother types!",

        "update_successful":                    "The update is successful.",
        "update_start_tips":                    "Do you want to start the update?",

        "ota_battery_tips1":                    "The battery is less than {}%.",
        "ota_battery_tips2":                    "Update is unavailable.",
        "ota_battery_tips3":                    "please connect the charger.",
        "ota_battery_tips4":                    "Charging  : {}",
        "ota_battery_tips5":                    "Percentage: {}",
        "no_tag_history":                       "No dump info. \nOnly support:\n.bin .eml .txt",
    }


class StringZH:

    title = {
        "main_page":                            "主页面",
        "auto_copy":                            "自动复制",
        "about":                                "关于本机",
        "backlight":                            "背光调整",
        "key_enter":                            "输入页面",
        "network":                              "网络",
        "update":                               "固件升级",
        "pc-mode":                              "电脑模式",
        "read_tag":                             "读取卡片",
        "scan_tag":                             "扫描类型",
        "sniff_tag":                            "有卡嗅探",
        "sniff_notag":                          "无卡嗅探",
        "volume":                               "音量调整",
        "warning":                              "警告",
        "missing_keys":                         "不支持的半加密卡",
        "no_valid_key":                         "不支持的全加密卡",
        "no_valid_key_t55xx":                   "不支持的加密卡",
        "data_ready":                           "读卡完成",
        "write_tag":                            "写卡",
        "disk_full":                            "存储器满",
        "snakegame":                            "贪吃蛇",
        "trace":                                "记录",
        "simulation":                           "模拟卡片",
        "diagnosis":                            "设备诊断",

        "wipe_tag":                             "初始化卡",
        "time_sync":                            "时间设置",

        "se_decoder":                           "SE解码器",
        "write_wearable":                       "写手环",
        "card_wallet":                          "卡包列表",
        "tag_info":                             "卡片信息",
        "lua_script":                           "LUA脚本",
    }

    button = {
        "button":                               "PM3按钮",
        "read":                                 "读卡",
        "stop":                                 "停止",
        "start":                                "开始",
        "reread":                               "重读卡",
        "rescan":                               "重扫描",
        "retry":                                "重试",
        "sniff":                                "嗅探",
        "write":                                "写卡",
        "simulate":                             "模拟卡",
        "finish":                               "完成",
        "save":                                 "保存",
        "enter":                                "输入",
        "pc-m":                                 "电脑模式",
        "cancel":                               "取消",
        "rewrite":                              "再写一张",
        "force":                                "强制读",
        "verify":                               "校验",
        "forceuse":                             "强制忽视",
        "clear":                                "清除数据",
        "shutdown":                             "关机",
        "yes":                                  "是的",
        "no":                                   "不是",
        "fail":                                 "失败",
        "pass":                                 "通过",
        "save_log":                             "保存日志",

        "wipe":                                 "初始化",
        "edit":                                 "编辑",
        "delete":                               "删除",
        "details":                              "详情",
    }

    procbarmsg = {
        "reading":                              "读取中...",
        "writing":                              "写入中...",
        "verifying":                            "核验中...",
        "scanning":                             "扫描中...",
        "updating_with":                        "Updating with: ",
        "updating":                             "更新中...",
        "t55xx_checking":                       "T57密码检索中...",
        "t55xx_reading":                        "T57读取中...",
        "reading_with_keys":                    "读取中...{}/{}Keys",
        "remaining_with_value":                 "预计时长: {}s",
        "clearing":                             "格式化中",
        "ChkDIC":                               "密码检索中",
        "Darkside":                             "全加密解密",
        "Nested":                               "知一求全中",
        "STnested":                             "无漏洞解密",
        "time>=10h":                            "剩余时间：%02d时 %02d分 %02d秒",
        "10h>time>=1h":                         "剩余时间：%d时 %02d分 %02d秒",
        "time<1h":                              "剩余时间：%02d分 %02d秒",

        "wipe_block":                           "初始化块",
        "tag_fixing":                           "卡片修复中",
        "tag_wiping":                           "卡片初始化中",
    }

    toastmsg = {
        "update_finish":                        "更新已完成",
        "update_unavailable":                   "无可用更新",
        "pcmode_running":                       "电脑模式\n正在运行",
        "read_ok_2":                            "读取成功\n部分\n已保存",
        "read_ok_1":                            "读取成功\n文件\n已保存",
        "read_failed":                          "读取失败！",
        "no_tag_found2":                        "未识别\n或错误类型！",
        "no_tag_found":                         "未识别到卡！",
        "tag_found":                            "识别到卡片！",
        "tag_multi":                            "识别到多张卡！",
        "processing":                           "处理中...",
        "trace_saved":                          "嗅探日志已保存！",
        "sniffing":                             "正在嗅探中...",
        "t5577_sniff_finished":                 "T5577嗅探完成",
        "write_success":                        "写卡成功！",
        "write_verify_success":                 "写卡成功！核验成功！",
        "write_failed":                         "写卡失败！",
        "verify_success":                       "核验成功！",
        "verify_failed":                        "核验失败！",

        "you_win":                              "你赢了",
        "game_over":                            "游戏结束",
        "game_tips":                            "按下“ok”开始游戏",
        "pausing":                              "暂停",

        "trace_loading":                        "记录解析中...",
        "simulating":                           "正在模拟中...",
        "sim_valid_input":                      "非法输入：\n{}应大于{}",
        "sim_valid_param":                      "非法参数",

        "bcc_fix_failed":                       "BCC修复失败",
        "wipe_success":                         "初始化成功",
        "wipe_failed":                          "初始化失败",
        "keys_check_failed":                    "字典秘钥检测超时",
        "wipe_no_valid_keys":                   "无有效秘钥，请先使用“自动复制”读卡，再使用初始化卡。",
        "err_at_wiping":                        "在初始化卡片时出现无法处理的异常",
        "time_syncing":                         "系统时间同步中",
        "time_syncok":                          "系统时间同步成功",

        "device_disconnected":                  "外置设备已被移除",
        "plz_remove_device":                    "请移除外置设备",

        "start_clone_uid":                      "开始写入UID",
        "unknown_error":                        "未知的错误",
        "write_wearable_err1":                  "原卡和空白卡的UID长度或者容量不一致",
        "write_wearable_err2":                  "不支持被加密的非空白卡",
        "write_wearable_err3":                  "可能是被天线位置或者卡片控制位影响",
        "write_wearable_err4":                  "UID写入失败，请确保卡片稳定放置在天线上。",

        "delete_confirm":                       "确认删除？",
        "opera_unsupported":                    "操作不支持",
    }

    itemmsg = {
        "missing_keys_msg1":                    "选项1：去读头有卡嗅探\n\n选项2：手工输入已知秘钥",
        "missing_keys_msg2":                    "选项3：强制读非加密区\n       制卡\n\n选项4：连接电脑增强解密",
        "missing_keys_msg3":                    "选项1：去读头有卡嗅探\n\n选项2：手工输入已知秘钥",
        "missing_keys_t57":                     "选项1：去读头进行嗅探\n\n选项2：手工输入已知秘钥",
        
        "enter_known_keys":                     "  输入秘钥",

        "aboutline1":                           "      {}",
        "aboutline2":                           "      HW  {}",
        "aboutline3":                           "      HMI {}",
        "aboutline4":                           "      OS  {}",
        "aboutline5":                           "      PM  {}",
        "aboutline6":                           "      SN  {}",

        "aboutline1_update":                    "固件更新",
        "aboutline2_update":                    "1.下载固件",
        "aboutline3_update":                    " icopy-x.com/update",
        "aboutline4_update":                    "2.插入USB，拷贝固件到\n 设备里.",
        "aboutline5_update":                    "3.按下'OK'键开始更新.",

        "valueline1":                           "关闭声音",
        "valueline2":                           "低音量",
        "valueline3":                           "中音量",
        "valueline4":                           "高音量",

        "blline1":                              "低亮度",
        "blline2":                              "中亮度",
        "blline3":                              "高亮度",

        "sniffline1":                           "步骤1：\n准备好读头和原卡，然后\n按开始按钮。",
        "sniffline2":                           "步骤2：\n拆下天线罩，把天线放在\n读头上。",
        "sniffline3":                           "步骤3：\n在天线上刷卡，确保读头\n可以正常读到卡。",
        "sniffline4":                           "步骤4：\n调整三者间距，重复数次\n后按完成按钮。",
        "sniffline_t5577":                      "点击开始按钮， 把天线靠近读头刷卡， 直至成功获得密码。",

        "sniff_item1":                          "1. 14A有卡嗅探",
        "sniff_item2":                          "2. 14B有卡嗅探",
        "sniff_item3":                          "3. iclass有卡嗅探",
        "sniff_item4":                          "4. Topaz有卡嗅探",
        "sniff_item5":                          "5. T5577无卡嗅探",

        "sniff_decode":                         "解析中...\n{}/{}",
        "sniff_trace":                          "交互日志: {}",

        "diagnosis_item1":                      "用户诊断程序",
        "diagnosis_item2":                      "工厂诊断程序",

        "diagnosis_subitem1":                   "HF天线电压",
        "diagnosis_subitem2":                   "LF天线电压",
        "diagnosis_subitem3":                   "HF天线读卡",
        "diagnosis_subitem4":                   "LF天线读卡",
        "diagnosis_subitem5":                   "存储器    ",
        "diagnosis_subitem6":                   "USB口     ",
        "diagnosis_subitem7":                   "按钮      ",
        "diagnosis_subitem8":                   "屏幕      ",
        "diagnosis_subitem9":                   "声音      ",

        "key_item":                             "秘钥{}: ",
        "uid_item":                             "卡号: ",

        "wipe_m1":                              "IC(MF)卡初始化",
        "wipe_t55xx":                           "ID(T57)卡初始化",

        "write_wearable_tips1":                 "一、写UID到空白卡\n\n请放置空白卡到iCopy\n天线位置，然后点击‘开始’\n完成后自动进入下一步。",
        "write_wearable_tips2":                 "二、手环读取空白卡\n\n请使用手环收录此空白卡\n，然后点击‘完成‘\n完成后继续进行下一步。",
        "write_wearable_tips3":                 "三、写数据到手环\n\n请放置手环到iCopy\n天线位置，然后点击‘开始’\n完成后即可开门。",
    }

    tipsmsg = {
        "enter_known_keys_55xx":                "请输入T5577或\nEM4305的已知密码。",
        "enter_55xx_key_tips":                  "秘钥：",
        "connect_computer":                     "请连接到电脑，再按下开始键。",
        "place_empty_tag":                      "数据已准备好，请放复制用的空卡。",
        "type_tips":                            "类型：",
        "disk_full_tips":                       "硬盘空间满，请清理空间后使用。",
        "start_diagnosis_tips":                 "按下开始键开始诊断。",

        "installation":                         "在安装期间不要关闭电源。或复位系统。",
        "start_install_tips":                   "请按下开始键安装。",
        "testing_with":                         "测试：\n{}",
        "test_music_tips":                      "是否听到音乐？",
        "test_screen_tips":                     "请按下OK键开始测试。再次按下停止。上下箭头改变屏幕颜色。",
        "test_screen_isok_tips":                "屏幕是否正常？",
        "test_usb_connect_tips":                "请连接USB到电脑。",
        "test_usb_found_tips":                  "电脑是否发现新串口？",
        "test_usb_otg_tips":                    "1.连接OTG测试器2.判断OTG反向供电是否正常？",
        "test_hf_reader_tips":                  "请放一张IC卡",
        "test_lf_reader_tips":                  "请放一张ID卡",
        "install_failed":                       "安装失败，代码={}",

        "iclass_se_read_tips":                  "请将iClass SE卡放置于外置读头上读取，请勿放置其他类型卡片",

        "update_successful":                    "更新成功",
        "update_start_tips":                    "现在开始更新？",

        "ota_battery_tips1":                    "电量低于 {}%.",
        "ota_battery_tips2":                    "无法启动更新",
        "ota_battery_tips3":                    "请连接到充电器",
        "ota_battery_tips4":                    "是在充电吗  : {}",
        "ota_battery_tips5":                    "电池电量    : {}",
        "no_tag_history":                       "没有读卡历史\n只支持：\n.bin .eml .txt",
    }


class StringXSC:
    """
        这是 iCopy-XSC(CN) 的定制固件的文本资源
    """

    title = {
        "main_page":                            "主页面",
        "auto_copy":                            "自动复制",
        "about":                                "关于本机",
        "backlight":                            "背光调整",
        "key_enter":                            "输入页面",
        "network":                              "网络",
        "update":                               "固件升级",
        "pc-mode":                              "电脑模式",
        "read_tag":                             "读取卡片",
        "scan_tag":                             "扫描类型",
        "sniff_tag":                            "有卡嗅探",
        "sniff_notag":                          "无卡嗅探",
        "volume":                               "音量调整",
        "warning":                              "警告",
        "missing_keys":                         "不支持的半加密卡",
        "no_valid_key":                         "不支持的全加密卡",
        "no_valid_key_t55xx":                   "不支持的加密卡",
        "data_ready":                           "读卡完成",
        "write_tag":                            "写卡",
        "disk_full":                            "存储器满",
        "snakegame":                            "贪吃蛇",
        "trace":                                "记录",
        "simulation":                           "模拟卡片",
        "diagnosis":                            "设备诊断",

        "wipe_tag":                             "初始化卡",
        "time_sync":                            "时间设置",

        "se_decoder":                           "SE解码器",
        "write_wearable":                       "写手环",
        "card_wallet":                          "卡包列表",
        "tag_info":                             "卡片信息",
        "lua_script":                           "LUA脚本",
    }

    button = {
        "button":                               "PM3按钮",
        "read":                                 "读卡",
        "stop":                                 "停止",
        "start":                                "开始",
        "reread":                               "重读卡",
        "rescan":                               "重扫描",
        "retry":                                "重试",
        "sniff":                                "嗅探",
        "write":                                "写卡",
        "simulate":                             "模拟卡",
        "finish":                               "完成",
        "save":                                 "保存",
        "enter":                                "输入",
        "pc-m":                                 "电脑模式",
        "cancel":                               "取消",
        "rewrite":                              "再写一张",
        "force":                                "强制读",
        "verify":                               "校验",
        "forceuse":                             "强制忽视",
        "clear":                                "清除数据",
        "shutdown":                             "关机",
        "yes":                                  "是的",
        "no":                                   "不是",
        "fail":                                 "失败",
        "pass":                                 "通过",
        "save_log":                             "保存日志",

        "wipe":                                 "初始化",
        "edit":                                 "编辑",
        "delete":                               "删除",
        "details":                              "详情",
    }

    procbarmsg = {
        "reading":                              "读取中...",
        "writing":                              "写入中...",
        "verifying":                            "核验中...",
        "scanning":                             "扫描中...",
        "updating_with":                        "Updating with: ",
        "updating":                             "更新中...",
        "t55xx_checking":                       "T57密码检索中...",
        "t55xx_reading":                        "T57读取中...",
        "reading_with_keys":                    "读取中...{}/{}Keys",
        "remaining_with_value":                 "预计时长: {}s",
        "clearing":                             "格式化中",
        "ChkDIC":                               "密码检索中",
        "Darkside":                             "全加密解密",
        "Nested":                               "知一求全中",
        "STnested":                             "无漏洞解密",
        "time>=10h":                            "剩余时间：%02d时 %02d分 %02d秒",
        "10h>time>=1h":                         "剩余时间：%d时 %02d分 %02d秒",
        "time<1h":                              "剩余时间：%02d分 %02d秒",

        "wipe_block":                           "初始化块",
        "tag_fixing":                           "卡片修复中",
        "tag_wiping":                           "卡片初始化中",
    }

    toastmsg = {
        "update_finish":                        "更新已完成",
        "update_unavailable":                   "无可用更新",
        "pcmode_running":                       "电脑模式\n正在运行",
        "read_ok_2":                            "读取成功\n部分\n已保存",
        "read_ok_1":                            "读取成功\n文件\n已保存",
        "read_failed":                          "读取失败！",
        "no_tag_found2":                        "未识别\n或错误类型！",
        "no_tag_found":                         "未识别到卡！",
        "tag_found":                            "识别到卡片！",
        "tag_multi":                            "识别到多张卡！",
        "processing":                           "处理中...",
        "trace_saved":                          "嗅探日志已保存！",
        "sniffing":                             "正在嗅探中...",
        "t5577_sniff_finished":                 "T5577嗅探完成",
        "write_success":                        "写卡成功！",
        "write_verify_success":                 "写卡成功！核验成功！",
        "write_failed":                         "写卡失败！",
        "verify_success":                       "核验成功！",
        "verify_failed":                        "核验失败！",

        "you_win":                              "你赢了",
        "game_over":                            "游戏结束",
        "game_tips":                            "按下“ok”开始游戏",
        "pausing":                              "暂停",

        "trace_loading":                        "记录解析中...",
        "simulating":                           "正在模拟中...",
        "sim_valid_input":                      "非法输入：\n{}应大于{}",
        "sim_valid_param":                      "非法参数",

        "bcc_fix_failed":                       "BCC修复失败",
        "wipe_success":                         "初始化成功",
        "wipe_failed":                          "初始化失败",
        "keys_check_failed":                    "字典秘钥检测超时",
        "wipe_no_valid_keys":                   "无有效秘钥，请先使用“自动复制”读卡，再使用初始化卡。",
        "err_at_wiping":                        "在初始化卡片时出现无法处理的异常",
        "time_syncing":                         "系统时间同步中",
        "time_syncok":                          "系统时间同步成功",

        "device_disconnected":                  "外置设备已被移除",
        "plz_remove_device":                    "请移除外置设备",

        "start_clone_uid":                      "开始写入UID",
        "unknown_error":                        "未知的错误",
        "write_wearable_err1":                  "原卡和空白卡的UID长度或者容量不一致",
        "write_wearable_err2":                  "不支持被加密的非空白卡",
        "write_wearable_err3":                  "可能是被天线位置或者卡片控制位影响",
        "write_wearable_err4":                  "UID写入失败，请确保卡片稳定放置在天线上。",
        "delete_confirm":                       "确认删除？",
        "opera_unsupported":                    "操作不支持",
    }

    itemmsg = {
        "missing_keys_msg1":                    "选项1：去读头有卡嗅探\n\n选项2：手工输入已知秘钥",
        "missing_keys_msg2":                    "选项3：强制读非加密区\n       制卡\n\n选项4：连接电脑增强解密",
        "missing_keys_msg3":                    "选项1：去读头有卡嗅探\n\n选项2：手工输入已知秘钥",
        "missing_keys_t57":                     "选项1：去读头进行嗅探\n\n选项2：手工输入已知秘钥",
        
        "enter_known_keys":                     "  输入秘钥",

        "aboutline1":                           "     {}",
        "aboutline2":                           "     HW  {}",
        "aboutline3":                           "     HMI {}",
        "aboutline4":                           "     OS  {}",
        "aboutline5":                           "     PM  {}",
        "aboutline6":                           "     SN  {}",

        "aboutline1_update":                    "固件更新",
        "aboutline2_update":                    "1.下载固件",
        "aboutline3_update":                    "  进入电脑模式.",
        "aboutline4_update":                    "2.插入USB，拷贝固件到\n 设备里.",
        "aboutline5_update":                    "3.按下'OK'键开始更新.",

        "valueline1":                           "关闭声音",
        "valueline2":                           "低音量",
        "valueline3":                           "中音量",
        "valueline4":                           "高音量",

        "blline1":                              "低亮度",
        "blline2":                              "中亮度",
        "blline3":                              "高亮度",

        "sniffline1":                           "步骤1：\n准备好读头和原卡，然后\n按开始按钮。",
        "sniffline2":                           "步骤2：\n拆下天线罩，把天线放在\n读头上。",
        "sniffline3":                           "步骤3：\n在天线上刷卡，确保读头\n可以正常读到卡。",
        "sniffline4":                           "步骤4：\n调整三者间距，重复数次\n后按完成按钮。",
        "sniffline_t5577":                      "点击开始按钮， 把天线靠近读头刷卡， 直至成功获得密码。",

        "sniff_item1":                          "1. 14A有卡嗅探",
        "sniff_item2":                          "2. 14B有卡嗅探",
        "sniff_item3":                          "3. iclass有卡嗅探",
        "sniff_item4":                          "4. Topaz有卡嗅探",
        "sniff_item5":                          "5. T5577无卡嗅探",

        "sniff_decode":                         "解析中...\n{}/{}",
        "sniff_trace":                          "交互日志: {}",

        "diagnosis_item1":                      "用户诊断程序",
        "diagnosis_item2":                      "工厂诊断程序",

        "diagnosis_subitem1":                   "HF天线电压",
        "diagnosis_subitem2":                   "LF天线电压",
        "diagnosis_subitem3":                   "HF天线读卡",
        "diagnosis_subitem4":                   "LF天线读卡",
        "diagnosis_subitem5":                   "存储器    ",
        "diagnosis_subitem6":                   "USB口     ",
        "diagnosis_subitem7":                   "按钮      ",
        "diagnosis_subitem8":                   "屏幕      ",
        "diagnosis_subitem9":                   "声音      ",

        "key_item":                             "秘钥{}: ",
        "uid_item":                             "卡号: ",

        "wipe_m1":                              "IC(MF)卡初始化",
        "wipe_t55xx":                           "ID(T57)卡初始化",

        "write_wearable_tips1":                 "一、写UID到空白卡\n\n请放置空白卡到设备\n天线位置，然后点击‘开始’\n完成后自动进入下一步。",
        "write_wearable_tips2":                 "二、手环读取空白卡\n\n请使用手环收录此空白卡\n，然后点击‘完成‘\n完成后继续进行下一步。",
        "write_wearable_tips3":                 "三、写数据到手环\n\n请放置手环到设备\n天线位置，然后点击‘开始’\n完成后即可开门。",
    }

    tipsmsg = {
        "enter_known_keys_55xx":                "请输入T5577或\nEM4305的已知密码。",
        "enter_55xx_key_tips":                  "秘钥：",
        "connect_computer":                     "请连接到电脑，再按下开始键。",
        "place_empty_tag":                      "数据已准备好，请放复制用的空卡。",
        "type_tips":                            "类型：",
        "disk_full_tips":                       "硬盘空间满，请清理空间后使用。",
        "start_diagnosis_tips":                 "按下开始键开始诊断。",

        "installation":                         "在安装期间不要关闭电源。或复位系统。",
        "start_install_tips":                   "请按下开始键安装。",
        "testing_with":                         "测试：\n{}",
        "test_music_tips":                      "是否听到音乐？",
        "test_screen_tips":                     "请按下OK键开始测试。再次按下停止。上下箭头改变屏幕颜色。",
        "test_screen_isok_tips":                "屏幕是否正常？",
        "test_usb_connect_tips":                "请连接USB到电脑。",
        "test_usb_found_tips":                  "电脑是否发现新串口？",
        "test_usb_otg_tips":                    "1.连接OTG测试器2.判断OTG反向供电是否正常？",
        "test_hf_reader_tips":                  "请放一张IC卡",
        "test_lf_reader_tips":                  "请放一张ID卡",
        "install_failed":                       "安装失败，代码={}",

        "iclass_se_read_tips":                  "请将iClass SE卡放置于外置读头上读取，请勿放置其他类型卡片",

        "update_successful":                    "更新成功",
        "update_start_tips":                    "现在开始更新？",

        "ota_battery_tips1":                    "电量低于 {}%.",
        "ota_battery_tips2":                    "无法启动更新",
        "ota_battery_tips3":                    "请连接到充电器",
        "ota_battery_tips4":                    "是在充电吗  : {}",
        "ota_battery_tips5":                    "电池电量    : {}",
        "no_tag_history":                       "没有读卡历史\n只支持：\n.bin .eml .txt",
    }


class DrawParEN:
    """"
        绘制参数，英文版本
    """

    widget_xy = {
        "lv_main_page":                     (0, 40),
    }

    text_size = {
        "lv_main_page":                     13,
    }

    int_param = {
        "lv_main_page_str_margin":          50,
    }


class DrawParZH:
    """"
        绘制参数，中文版本
    """

    widget_xy = {
        "lv_main_page":                     (0, 40),
    }

    text_size = {
        "lv_main_page":                     15,
    }

    int_param = {
        "lv_main_page_str_margin":          61,
    }


def get_font_type(typ, size, bold=False):
    """
        获得指定的字体
    :param typ: 字体类型
    :param size: 字体大小
    :param bold: 是否加粗
    :return:
    """
    if typ.upper() == "ZH":
        f = "文泉驿等宽正黑"
    elif typ.upper() == "EN":
        f = "mononoki"
    else:
        raise Exception("不支持的字体类型: " + typ)

    font = f"{f} {size} {'bold' if bold else ''}"
    return font


def get_font_force_zh(size, bold=False):
    """
        获得指定的中文字体
    :param size: 字体大小
    :param bold: 是否加粗
    :return:
    """
    return get_font_type("ZH", size, bold)


def get_font_force_en(size, bold=False):
    """
        获得指定的英文字体
    :param size: 字体大小
    :param bold: 是否加粗
    :return:
    """
    return get_font_type("EN", size, bold)


def __get_str_impl(clz, key, typ):

    def inner_str_get_fn(str_key):
        try:

            if typ is not None:
                clz_ds = clz.__dict__
                for ds_key in clz_ds.keys():
                    value = clz_ds[ds_key]
                    if isinstance(value, dict) and ds_key == typ:
                        if str_key in value:
                            return str(value[str_key])
                        else:
                            raise Exception("在" + typ + "中没有" + str_key + "这个键")
                raise Exception("传入了非法的字符串类型")
            else:
                clz_ds = clz.__dict__
                for ds_key in clz_ds.keys():
                    value = clz_ds[ds_key]
                    if isinstance(value, dict):
                        if str_key in value:
                            return str(value[str_key])
                raise Exception("传入了非法的字符串类型")

        except Exception as e:
            print("在取出字符串时出现异常: ", e)
            return "?"

    if isinstance(key, list) or isinstance(key, tuple):
        ret = []
        for k in key:
            ret.append(inner_str_get_fn(k))
        if len(ret) == 1:
            return ret[0]
        return tuple(ret)

    return inner_str_get_fn(key)


def __get_par_impl(clz, key, typ):
    """
        获取参数的具体实现！
    :param clz: 参数存放的类
    :param key: 参数的键
    :param typ: 参数的类型，对应的是参数的字典名称或者引用！
    :return:
    """
    if isinstance(typ, dict):
        return typ[key]

    clz_ds = clz.__dict__
    for ds_key in clz_ds.keys():
        value = clz_ds[ds_key]
        if isinstance(value, dict) and ds_key == typ:
            if key in value:
                return value[key]
            else:
                raise Exception("在" + typ + "中没有" + key + "这个键")

    raise Exception("传入了非法的参数类型")


# -------------------------------------------------------------------------------
# 上面是封装定义
# 下面是调用实现
# 正常情况下，请在上面实现可复用函数的封装
# 然后下方简化对封装函数的调用
# -------------------------------------------------------------------------------


# 测试开始 <
if platform.system() == "Windows":
    # 由此处定义一个调试的切换入口
    test_map = {
        "x": (StringEN, DrawParEN, "EN"),
        "xr": (StringEN, DrawParEN, "EN"),
        "zh": (StringZH, DrawParZH, "ZH"),
        "xs": (StringEN, DrawParEN, "EN"),
        "uk": (StringEN, DrawParEN, "EN"),
        "xsc": (StringXSC, DrawParZH, "ZH"),
    }

    # 定义我们需要使用的测试类型
    test_typ = "xs"

    DEFAULT_STRING, DEFAULT_PARAMS, DEFAULT_TYPE = test_map[test_typ]
# 测试结束 >


def get_str(key, typ=None):
    """
        根据键来获取字符串
    :param typ: 获取指定类型的文本资源，如果不指定，自动搜索并且使用第一个遇到的匹配的资源
    :param key: 文本资源的映射键
    :return:
    """
    # 测试开始 <
    if platform.system() == "Windows":
        # 此处我们直接返回
        return __get_str_impl(DEFAULT_STRING, key, typ)
    # 测试结束 >

    # 此处我们需要进行实时获取权限对应的文本资源
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

        # 这里我们不做判断，只去映射
        maps = {
            "x":    StringEN,   # 英文
            "xr":   StringEN,   # 英文
            "zh":   StringZH,   # 中文
            "xs":   StringEN,   # 英文
            "uk":   StringEN,   # 英文
            "xsc":  StringXSC,  # 中文（没有iCopy字样的定制版本）
        }

        # 解密UID
        aes_obj = AES.new(
            key_device.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        # 最终的文本资源获取实现
        return __get_str_impl(
            maps[i[3]],  # 解密UID，并且进行文本资源获取
            key,  # 需要获取的文本的键
            typ,  # 强行指定从某个类型中获取文本资源
        )

    except Exception as e:
        print("无法通过验证，无法继续获取文本资源", e)
        # 我们直接返回问好就好了，这样还能显示一些奇奇怪怪的东西
        return "?"
    # 验证结束 >


def get_font(size, bold=False):
    """
        自动获得指定的字体
    :param size: 字体大小
    :param bold: 是否加粗
    :return:
    """
    if hasattr(get_font, "typ"):
        typ = getattr(get_font, "typ", None)
    else:
        typ = None

    if typ is None:
        # 测试开始 <
        if platform.system() == "Windows":
            # 此处我们直接返回
            return get_font_type(DEFAULT_TYPE, size, bold)
        # 测试结束 >

        # 此处我们需要进行实时获取权限对应的字体资源
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

            # 解密UID
            aes_obj = AES.new(
                key_device.encode("utf-8"),
                AES.MODE_CFB,
                "VB1v2qvOinVNIlv2".encode("utf-8"),
            )
            # 全部解密
            i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

            # 根据当前的设备类型来决定用什么字体！
            typ = i[3]
            setattr(get_font, "typ", typ)

        except Exception as e:
            print("无法通过验证，无法继续获取字体资源", e)
            # 我们直接返回奇奇怪怪的资源就好了，这样还能显示一些奇奇怪怪的东西
            return "瞎体 8"
        # 验证结束 >

    maps = {
        "x":    get_font_type("EN", size, bold),       # 英文
        "xr":   get_font_type("EN", size, bold),      # 英文
        "zh":   get_font_type("ZH", size, bold),      # 中文
        "xs":   get_font_type("EN", size, bold),      # 英文
        "uk":   get_font_type("EN", size, bold),      # 英文
        "xsc":  get_font_type("ZH", size, bold),     # 中文（没有iCopy字样的定制版本）
    }

    return maps[typ]


def get_par(key, typ, default):
    """
        获取参数的安全实现
    :param default: 在无法获取时的默认值
    :param typ: 类型，也就是对应的字典名称
    :param key: 键，也就是存放在字典中的数据的索引
    :return:
    """

    dict_key = typ

    # 测试开始 <
    if platform.system() == "Windows":
        # 此处我们直接返回
        return __get_par_impl(DEFAULT_PARAMS, key, dict_key)
    # 测试结束 >

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

        # 解密UID
        aes_obj = AES.new(
            key_device.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        # 根据当前的设备类型来决定用什么字体！
        maps = {
            "x":    DrawParEN,  # 英文
            "xr":   DrawParEN,  # 英文
            "zh":   DrawParZH,  # 中文
            "xs":   DrawParEN,  # 英文
            "uk":   DrawParEN,  # 英文
            "xsc":  DrawParZH,  # 中文（没有iCopy字样的定制版本）
        }

        return __get_par_impl(maps[i[3]], key, dict_key)

    except Exception as e:
        print("无法通过验证，无法继续获取资源值", e)
        # 我们直接返回奇奇怪怪的资源就好了，这样还能显示一些奇奇怪怪的东西
        return default
    # 验证结束 >


def get_fws(typ):
    """
        获取固件包，根据相应的类型
    :param typ: 类型，可以是
                1、flash
                2、pm3
                3、stm32
    :return:
    """
    path = os.path.join("res", "firmware", typ)
    fw_list = []
    try:
        files = os.listdir(path)
        if len(files) == 0:
            return []
        for name in files:
            fw_list.append(os.path.join(path, name))
    except Exception as e:
        print(e)
        pass
    return fw_list


def get_xy(key):
    """
        获取控件绘制时初始的xy位置
    :param key:
    :return:
    """
    return get_par(key, "widget_xy", tuple((0, 0,)))


def get_text_size(key):
    """
        获取控件绘制时初始的xy位置
    :param key:
    :return:
    """
    return get_par(key, "text_size", 5)


def get_int(key):
    """
        从参数中获取一个键对应的整形变量！
    :param key:
    :return:
    """
    return get_par(key, "int_param", 0)


# -------------------------------------------------------------------------------
# 上面是调用实现
# 下面是工具函数
# 正常情况下，下面的函数是不对外使用的，一般是只在本地使用的，除非有特殊情况，
# 因为工具函数一般是对资源的各种检查，校错，内容修改，必须要在运行时或者
# 在此模块被加载时自动调用，去完成上述的工作内容，才能保证程序的正常。
# -------------------------------------------------------------------------------


def is_keys_same(keys_list):
    """
        判断给定集合的里面的键是否一致
    :param keys_list:
    :return:
    """
    header: dict = keys_list[0]
    for index in range(1, len(keys_list)):
        current: dict = keys_list[index]
        if header.keys() != current.keys():
            return False
    return True


def force_check_str_res():
    """
        检测str资源是否完整映射
    :return:
    """

    if not is_keys_same([StringZH.title, StringEN.title, StringXSC.title]):
        raise Exception("标题 字符串资源未完整定义！")

    if not is_keys_same([StringZH.button, StringEN.button, StringXSC.button]):
        raise Exception("按钮 字符串资源未完整定义！")

    if not is_keys_same([StringZH.procbarmsg, StringEN.procbarmsg, StringXSC.procbarmsg]):
        raise Exception("进度条 字符串资源未完整定义！")

    if not is_keys_same([StringZH.toastmsg, StringEN.toastmsg, StringXSC.toastmsg]):
        raise Exception("吐司 字符串资源未完整定义: ")

    if not is_keys_same([StringZH.itemmsg, StringEN.itemmsg, StringXSC.itemmsg]):
        raise Exception("项目 字符串资源未完整定义！")

    if not is_keys_same([StringZH.tipsmsg, StringEN.tipsmsg, StringXSC.tipsmsg]):
        raise Exception("提示 字符串资源未完整定义！")

    print("资源完整性检查通过")


# 此处我们自动检测字符串定义类中的字符串组是否元素一致
# 也就是说，我们需要保证，字符串资源类必须要统一添加某个字符串定义，或者删除某个字符串定义
# 如果字符串的元素个数不统一，此处会抛出异常！
force_check_str_res()
