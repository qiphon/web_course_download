from playwright.sync_api import Playwright, sync_playwright
from utils import *
from m3u8_downloader import download_m3u8

# 模拟登录获取cooikie
def run_browser2get_cookie(playwright: Playwright, cookie = []) -> None:
    if len(cookie) > 15 :
        write_cookie(cookie)
    else :
        browser = playwright.firefox.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://ke.qq.com/")
        page.click('.kecomp-dialog-hd-close svg')
        page.click("a[data-hook='login']")

        page.wait_for_selector('i.kecomp-checkbox-icon')
        page.click("i.kecomp-checkbox-icon")
        page.click('button.login-btn.wx-btn')

        page.wait_for_selector('.login-mask', state='attached')
        page.wait_for_selector('.login-mask', state='detached')
        cookie = page.context.cookies()
        page.close()
        # context.close()
        # browser.close()
        write_cookie(cookie)
    # with open("cookies.json","w") as f:
        # f.write(json.dumps(cookie))

def write_cookie(cookies):
    with open("cookies.json","w") as f:
        f.write(json.dumps(cookies))

# 通过播放页的url获取对应的m3u8链接
def run_browser2get_m3u8_info(playwright : Playwright, play_url : str, playlist_url : list,course_name : list,flag : bool,cookies) -> None:
    browser = playwright.firefox.launch(headless=True,devtools=True)
    context = browser.new_context()
    page = context.new_page()
    page.context.add_cookies(cookies)
    def filter(response):
        if ".m3u8" in response.url:
            print('m3u8 url: ' + response.url )
            playlist_url.append(response.url)
    page.on("response",filter)
    print('jump to ' + play_url + 'url length ' + str(len(play_url)))
    page.goto(play_url, wait_until="load")
    while len(playlist_url) < 1 :
        playlist_url.clear()
        page.on("response", filter)
        page.goto(play_url, wait_until="load")

    if flag:
        title = page.query_selector('title').text_content()
        print( ' 课程名：' + title  )
        course_name.append(str(title))
    print('下载 m3u8 文件中....')
    resp = requests.get(playlist_url[0],cookies=format_cookie())
    with open("playlist.txt","wb") as f:
        f.write(resp.content)

#获取cookie，返回json格式的cookie
def get_cookie():
    cookies_file = Path("cookies.json")
    if cookies_file.exists():
        print("检测到cookie")
    else:
        with sync_playwright() as playwright:
            run_browser2get_cookie(playwright)
        if cookies_file.exists():
            print("已获取cookie")
        else:
            print("程序出错，请重试或者手动添加cookie")
            exit(0)
    cookies = json.loads(cookies_file.read_bytes())
    return cookies

# 通过播放页面url下载视频
def get_video(play_url : str, outputFilePath: str , cookies ):
    playlist_url = []
    course_name = []

    print('下载 m3u8 文件')
    with sync_playwright() as playwright:
        run_browser2get_m3u8_info(playwright,play_url,playlist_url,course_name,True,cookies)

    print('m3u8 文件下载完成')
    playlist = Path("playlist.txt")
    resolution_list = []
    m3u8_list = []
    flag = 0

    with open(playlist,"r") as f:
        for i in f:
            i.strip()
            if i.startswith("#EXT-X-STREAM-INF"):
                resolution_list.append(i)
                flag =1
                continue
            if flag == 1:
                flag = 0
                m3u8_list.append(i)
    print("检测到有以下码率可供选择，请选择要下载的资源(网络原因可能导致某些码率下载不了，此时会选择尽可能高的码率下载)\n")
    n=0
    for i in resolution_list:
        print(f"{n}.",resolution_list[n],end="")
        # print(n +'  '+ 'url ->' + play_url[i] + ' ---> ' + resolution_list[n])
        n+=1
    # choice = input()
    outfileName = Path(course_name[0] + ".mp4").absolute()
    try:
        download(playlist_url[1], course_name[0], outputFilePath)
    except:
        download(playlist_url[-1], course_name[0], outputFilePath)

def multi_get_video(play_url : str , cookies,video):
    playlist_url = []
    course_name = []
    with sync_playwright() as playwright:
        run_browser2get_m3u8_info(playwright, play_url, playlist_url, course_name,False, cookies)
    download(playlist_url[-1], video)


def download(m3u8_url,outfileName=None, outputFilePath='output'):
    # 从m3u8链接中取出需要的前缀和后缀
    pattern2 = re.compile(r'(?P<prefix>.*?)voddrm.token.*?exper=0(?P<suffix>.*)', re.S)
    res = pattern2.finditer(m3u8_url)
    for i in res:
        prefix = i.group("prefix")
        suffix = i.group("suffix")

    # 获取m3u8文件
    m3u8_resp = requests.get(m3u8_url, cookies=format_cookie())
    print('下载视频 m3u8文件完成')
    with open("m3u8", "wb") as f:
        f.write(m3u8_resp.content)

    #拿视频解密要用的key 这里免费视频可以拿到，付费视频需要自己找
    pattern1 = re.compile(r'URI="(?P<key>.*?)"')
    res = pattern1.finditer(m3u8_resp.text)
    for i in res:
        key_url = i.group("key")
        # print('download key is '+key_url)
    key_resp = requests.get(key_url, cookies=format_cookie())
    with open("get_dk", "wb") as f:
        f.write(key_resp.content)
    key = get_key("get_dk")
    print("成功拿到key : " + str(key))

    
    download_m3u8("m3u8", outputFilePath, outfileName,m3u8_url )