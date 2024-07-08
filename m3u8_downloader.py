# UTF-8
# author hestyle
# desc 必须在终端直接执行，不能在pycharm等IDE中直接执行，否则看不到动态进度条效果

import os
import sys
import re
import m3u8
import time
import requests
import traceback
import threadpool
from urllib.parse import urlparse
from utils import decrypt
from others import format_cookie

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
}

###############################配置信息################################
# m3u8链接批量输入文件(必须是utf-8编码)
# 下载出错的m3u8保存文件
errorM3u8InfoDirPath = "error.txt"
# m3u8文件、key文件下载尝试次数，ts流默认无限次尝试下载，直到成功
m3u8TryCountConf = 10
# 线程数（同时下载的分片数）
processCountConf = 50
######################################################################


# 全局变量
# 全局线程池
taskThreadPool = None
# 当前下载的m3u8 url
m3u8Url = None
# url前缀
rootUrlPath = None
# ts count
sumCount = 0
# 已处理的ts
doneCount = 0
# log file
logFile = None
# download bytes(0.5/1 s)
downloadedBytes = 0
# download speed
downloadSpeed = 0
    

# 2、下载key文件
def getKey(keyUrl):
    global logFile
    tryCount = m3u8TryCountConf
    while True:
        if tryCount < 0:
            print("\t{0}下载失败！".format(keyUrl))
            logFile.write("\t{0}下载失败！".format(keyUrl))
            return None
        tryCount = tryCount - 1
        try:
            response = requests.get(keyUrl, headers=headers, timeout=20, allow_redirects=True)
            if response.status_code == 301:
                nowKeyUrl = response.headers["location"]
                print("\t{0}重定向至{1}！".format(keyUrl, nowKeyUrl))
                logFile.write("\t{0}重定向至{1}！\n".format(keyUrl, nowKeyUrl))
                keyUrl = nowKeyUrl
                continue
            expected_length = int(response.headers.get('Content-Length'))
            actual_length = len(response.content)
            if expected_length > actual_length:
                raise Exception("key下载不完整")
            print("\t{0}下载成功！key = {1}".format(keyUrl, response.content.decode("utf-8")))
            logFile.write("\t{0}下载成功！ key = {1}".format(keyUrl, response.content.decode("utf-8")))
            break
        except :
            print("\t{0}下载失败！".format(keyUrl))
            logFile.write("\t{0}下载失败！".format(keyUrl))
    return response.text

# 3、多线程下载ts流
def mutliDownloadTs(playlist):
    global logFile
    global sumCount
    global doneCount
    global taskThreadPool
    global downloadedBytes
    global downloadSpeed
    taskList = []

    # 每个ts单独作为一个task
    for index in range(len(playlist)):
        dict = {"playlist": playlist, "index": index}
        taskList.append((None, dict))
    # 重新设置ts数量，已下载的ts数量
    doneCount = 0
    sumCount = len((taskList))
    printProcessBar(sumCount, doneCount, 50)
    # 构造thread pool
    requests = threadpool.makeRequests(downloadTs, taskList)
    [taskThreadPool.putRequest(req) for req in requests]
    # 等待所有任务处理完成
    while doneCount < sumCount:
        # 统计1秒钟下载的byte
        beforeDownloadedBytes = downloadedBytes
        time.sleep(1)
        downloadSpeed = downloadedBytes - beforeDownloadedBytes
        # 计算网速后打印一次
        printProcessBar(sumCount, doneCount, 50, True)
    print("")
    return True

# 4、下载单个ts playlists[index]
def downloadTs(playlist, index):
    global logFile
    global sumCount
    global doneCount
    global cachePath
    global rootUrlPath
    global downloadedBytes
    succeed = False
    while not succeed:
        # 文件名格式为 "00000001.ts"，index不足8位补充0
        outputPath = cachePath + "/" + "{0:0>8}.ts".format(index)
        outputFp = open(outputPath, "wb+")
        if playlist[index].startswith("http"):
            tsUrl = playlist[index]
        else:
            tsUrl = rootUrlPath + "/" + playlist[index]
        try:
            response = requests.get(tsUrl, timeout=5, headers=headers, stream=True, cookies=format_cookie())
            if response.status_code == 200:
                expected_length = int(response.headers.get('Content-Length'))
                actual_length = len(response.content)
                # 累计下载的bytes
                downloadedBytes += actual_length
                if expected_length > actual_length:
                    raise Exception("分片下载不完整")
                outputFp.write(response.content)
                doneCount += 1
                printProcessBar(sumCount, doneCount, 50, isPrintDownloadSpeed=True)
                logFile.write("\t分片{0:0>8} url = {1} 下载成功！".format(index, tsUrl))
                succeed = True
        except Exception as exception:
            logFile.write("\t分片{0:0>8} url = {1} 下载失败！正在重试...msg = {2}".format(index, tsUrl, exception))
        outputFp.close()

# 5、合并ts
def mergeTs(tsFileDir, outputFilePath,  count, key):
    global logFile

    if key is None:
        key = input("请输入视频密钥：")
        print(f'使用密钥：{key}')

    outputFp = open(outputFilePath, "wb+")
    for index in range(count):
        printProcessBar(count, index + 1, 50)
        # logFile.write("\t{0}\n".format(index))
        print("\t{0}\n".format(index))
        inputFilePath = tsFileDir + "/" + "{0:0>8}.ts".format(index)
        if not os.path.exists(outputFilePath):
            print("\n分片{0:0>8}.ts, 不存在，已跳过！".format(index))
            # logFile.write("分片{0:0>8}.ts, 不存在，已跳过！\n".format(index))
            print("分片{0:0>8}.ts, 不存在，已跳过！\n".format(index))
            continue
        inputFp = open(inputFilePath, "rb")
        fileData = inputFp.read()
        try:
            outputFp.write(decrypt(fileData, key,))
            # outputFp.write(fileData)
        except Exception as exception:
            inputFp.close()
            outputFp.close()
            print(exception)
            return False
        inputFp.close()
    print("")
    outputFp.close()
    return True

# 6、删除ts文件
def removeTsDir(tsFileDir):
    # 先清空文件夹
    for root, dirs, files in os.walk(tsFileDir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(tsFileDir)
    return True

# 7、convert to mp4（调用了FFmpeg，将合并好的视频内容放置到一个mp4容器中）
def ffmpegConvertToMp4(inputFilePath, ouputFilePath):
    global logFile
    if not os.path.exists(inputFilePath):
        print(inputFilePath + " 路径不存在！")
        logFile.write(inputFilePath + " 路径不存在！\n")
        return False
    cmd = r'.\lib\ffmpeg -i "{0}" -vcodec copy -acodec copy "{1}"'.format(inputFilePath, ouputFilePath)
    if sys.platform == "darwin":
        cmd = r'./lib/ffmpeg -i "{0}" -vcodec copy -acodec copy "{1}"'.format(inputFilePath, ouputFilePath)
    if os.system(cmd) == 0:
        print(inputFilePath + "转换成功！")
        # logFile.write(inputFilePath + "转换成功！\n")
        return True
    else:
        print(inputFilePath + "转换失败！")
        logFile.write(inputFilePath + "转换失败！\n")
        return False

# 8、模拟输出进度条(默认不打印网速)
def printProcessBar(sumCount, doneCount, width, isPrintDownloadSpeed=False):
    global downloadSpeed
    precent = doneCount / sumCount
    useCount = int(precent * width)
    spaceCount = int(width - useCount)
    precent = precent*100
    if isPrintDownloadSpeed:
        # downloadSpeed的单位是B/s, 超过1024*1024转换为MiB/s, 超过1024转换为KiB/s
        if downloadSpeed > 1048576:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}MiB/s'.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed / 1048576),
                  file=sys.stdout, flush=True, end='')
        elif downloadSpeed > 1024:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}KiB/s'.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed / 1024),
                  file=sys.stdout, flush=True, end='')
        else:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}B/s  '.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed),
                  file=sys.stdout, flush=True, end='')
    else:
        print('\r\t{0}/{1} {2}{3} {4:.2f}%'.format(sumCount, doneCount, useCount*'■', spaceCount*'□', precent), file=sys.stdout, flush=True, end='')

# m3u8下载器
def m3u8VideoDownloader(m3u8_url, key, title):
    global logFile
    global m3u8Url
    global cachePath
    global downloadedBytes
    global downloadSpeed
    # 1、下载m3u8
    print("\t1、开始下载m3u8...")
    logFile.write("\t1、开始下载m3u8...\n")
   
    playlist = []
    # 从m3u8链接中取出需要的前缀和后缀
    pattern2 = re.compile(r'(?P<prefix>.*?)voddrm.token.*?exper=0(?P<suffix>.*)', re.S)
    res = pattern2.finditer(m3u8_url)
    for i in res:
        prefix = i.group("prefix")
        suffix = i.group("suffix")
    
    print("开始整理下载地址 ")
    with open("m3u8", "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                continue
            single_ts_url = prefix + line + suffix
            playlist.append(single_ts_url)
            
        print(" 下载地址整理完成")


    # 3、下载ts
    print("\t3、开始下载ts...")
    logFile.write("\t3、开始下载ts...\n")
    # 清空bytes计数器
    downloadSpeed = 0
    downloadedBytes = 0
    if mutliDownloadTs(playlist):
        logFile.write("\tts下载完成---------------------\n")
    # 4、合并ts
    print("\t4、开始合并ts...")
    logFile.write("\t4、开始合并ts...\n")
    if mergeTs(cachePath, cachePath + "/cache.flv",  len(playlist), key):
        logFile.write("\tts合并完成---------------------\n")
    else:
        print("\tts合并失败！")
        logFile.write("\tts合并失败！\n")
        return False
    # 5、开始转换成mp4
    print('use cachePath: ' + cachePath + '/cache.flv')
    mp4Path = f'./{outputFilePath}/{title}.mp4'
    print('5、开始mp4转换...' + mp4Path)
    logFile.write("\t5、开始mp4转换...\n")
    if not ffmpegConvertToMp4(cachePath + '/cache.flv', mp4Path):
        return False
    return True




def download_m3u8(m3u8InputFilePath: str, outDir: str,outfileName: str, m3u8_url: str, key: str=None ):
    global outputFilePath
    global logFile
    global taskThreadPool
    global cachePath

    outputFilePath = outDir

    cachePath = f'{outputFilePath}/cache'
    logPath = f'{cachePath}/log.txt'
    # 判断m3u8文件是否存在
    if not (os.path.exists(m3u8InputFilePath)):
        print("{0}文件不存在！".format(m3u8InputFilePath))
        exit(0)
    # 如果输出目录不存在就创建
    if not (os.path.exists(outputFilePath)):
        os.mkdir(outputFilePath)

    # 如果记录错误文件不存在就创建
    if not (os.path.exists(errorM3u8InfoDirPath)):
        open(errorM3u8InfoDirPath, 'w+')

    m3u8InputFp = open(m3u8InputFilePath, "r", encoding="utf-8")
    # 设置error的m3u8 url输出
    # errorM3u8InfoFp = open(errorM3u8InfoDirPath, "a+", encoding="utf-8")
    # 设置log file
    if not os.path.exists(cachePath):
        os.makedirs(cachePath)
    logFile = open(logPath, "w+", encoding="utf-8")
    # 初始化线程池
    taskThreadPool = threadpool.ThreadPool(processCountConf)
    title = outfileName

    try:
        print("{0} 开始下载:".format(title))
        logFile.write("{0} 开始下载:\n".format(title))
        if m3u8VideoDownloader(m3u8_url, key , title):
            # 成功下载完一个m3u8则清空logFile
            logFile.seek(0)
            logFile.truncate()
            print("{0} 下载成功！".format(title))
        else:
            print(str(title) + "," + str(m3u8_url) + '\n')
            # errorM3u8InfoFp.write(title + "," + m3u8Url + '\n')
            # errorM3u8InfoFp.flush()
            print("{0} 下载失败！".format(title))
            logFile.write("{0} 下载失败！\n".format(title))
    except Exception as exception:
        print(exception)
        traceback.print_exc()
    # 关闭文件
    logFile.close()
    m3u8InputFp.close()
    # errorM3u8InfoFp.close()
    print("----------------下载结束------------------")