from  multi_downloader import *
import os
from m3u8_downloader import mergeTs, ffmpegConvertToMp4
from playwright.sync_api import Playwright, sync_playwright
from utils import decrypt


# browser = None

def single_download():
    # single_url = input("请输入视频的播放网址:")
    single_url = 'https://ke.qq.com/webcourse/426365/100558401#taid=4161995108942205&vid=5285890806942962013'
    cookies = get_cookie()
    get_video(single_url, outputFilePath,cookies)

def multi_download():
    cid = input("请输入要下载的课程的cid:")
    cookies = get_cookie()
    course_name = get_course_info(cid)
    term = input("请输入学期数:")
    chapters = get_chapters_from_file(course_name+'.json',int(term)-1)
    print("已获取到下列课程信息:")
    # 遍历每个章节
    for chapter in chapters:
        # 获取每个章节的名字
        chapter_name = chapter.get('name').replace('/', '／').replace('\\', '＼')
        print(chapter_name)
        # 获取每个章节对应的所有课程
        courses = get_courses_from_chapter(chapter)
        # 遍历每个章节的所有课程
        for course in courses:
            print("   ",course.get('name'))

    print("开始下载：")
    parents = Path(course_name).absolute()
    parents.mkdir(exist_ok=True)
    flag = 0
    wrong_num = 0
    for chapter in chapters:
        # 获取每个章节的名字
        chapter_name = chapter.get('name').replace('/', '／').replace('\\', '＼')
        # 获取每个章节对应的所有课程
        courses = get_courses_from_chapter(chapter)
        parent = Path(str(parents) + "\\" +str(chapter_name)).absolute()
        parent.mkdir(exist_ok=True)
        # 遍历每个章节的所有课程
        for course in courses:
            # 获取每个课程的播放url
            course_url = get_course_url(course)
            flag += 1
            if flag>=8:
                while True:
                    try:
                        print(f"出错{wrong_num}次")
                        print(f"课程第{flag}个视频开始下载")
                        multi_get_video(course_url,cookies,Path(str(parent)+"\\"+str(course.get('name'))+".mp4"))
                        break
                    except:
                        wrong_num += 1
                        continue



def main():
    while True:
        # choice = input("请选择下载方式:\n0.单一视频下载 1.整个课程下载\n")
        choice = '0' #input("请选择下载方式:\n0.单一视频下载 1.整个课程下载\n")
        if choice == '0':
            single_download()
            break
        elif choice == '1':
            multi_download()
            break
        else:
            print("输入有误，请重新输入")

# key 和 iv 获取方式：source 文件中找到 如下文件
# https://cdn-cos-ke.myoed.com/ke_proj/webcourse/assets/js/lib_fd2a4cb1.js
# 搜索 decryptkey 
# js 控制台解码 
# hexArray = Array.from(new Uint8Array(e.data), byte => byte.toString(16).padStart(2, '0')).map(hex => parseInt(hex, 16))
# btoa(String.fromCharCode.apply(null, hexArray)) 得到 base64 key

if __name__ == '__main__':
    global outputFilePath
    outputFilePath = './output'
    # keyStr = "b0fRtloommLk9fvHNuIDhA=="
    # m3u8Url = 'https://1258712167.vod2.myqcloud.com/fb8e6c92vodtranscq1258712167/3d63104f5285890806173814393/drm/voddrm.token.dWluPTE0NDExNTE5OTI1OTM5NDIyNyZ0ZXJtX2lkPTkxMzU3MjQ2OA==.v.f56150.m3u8?t=6695E662&exper=0&us=4274490934480850021&sign=0181e9ab07e82e91c63bb81f2d840013'
    os.system('rm -rf ' + outputFilePath + ' output ')
    main()

    # ffmpegConvertToMp4('./output/cache/cache.flv', './output/cache.mp4')

    # download_m3u8('./m3u8', outputFilePath, 'test.mp4',m3u8Url , keyStr)