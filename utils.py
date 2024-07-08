import requests
import re
import json
from pathlib import Path
from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad  , pad
from Crypto.Random import get_random_bytes
from base64 import b64decode  
import os


#格式化cookie为字典，以便requests使用
def format_cookie():
    cookies = {}
    for i in json.loads(Path('cookies.json').read_bytes()):
        cookies.update({i['name']: i['value']})
    return cookies

# 从key文件中读取key
def get_key(filename):
    with open(filename, 'rb') as f:
        key = f.read()
    return key

# 内容解密
def decrypt(ciphertext, key):
    print('key is :' + key)

    # key = md5(b64decode(key).encode('utf8')).digest()
    key = b64decode(key) #get_key("get_dk")
    # iv = bytes(iv, encoding='utf8')
    iv = ciphertext[:AES.block_size]
    # iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, key)
    plaintext = cipher.decrypt(ciphertext)
    plaintext = unpad(plaintext, AES.block_size)
    return plaintext.rstrip(b"\0")

# 文件解密
def decrypt_file(filename, key):
    with open("./downloads/" + filename, 'rb') as f:
        ciphertext = f.read()
    dec = decrypt(ciphertext, key)
    with open("./decrypt/" + filename, 'wb') as f:
        f.write(dec)

# ts文件合并转换为mp4文件
def ts2mp4(n,video):
    file_name = "0.ts"
    _n = 0
    if n <= 200:
        for i in range(1, n):
            file_name = file_name + f"+{i}.ts"
        os.system("cd decrypt&&copy /b " + file_name + " " + str(video).replace(" ",""))
    else:
        for i in range(1,n):
            file_name = file_name + f"+{i}.ts"
            if i == n-1:
                os.system("cd decrypt&&copy /b " + file_name + " " + str(video).replace(" ", ""))
            if i % 500 == 0:
                os.system("cd decrypt&&copy /b " + file_name + f" x{_n}.ts" )
                file_name = f" x{_n}.ts"
                _n += 1
    os.system("cd downloads&&del *.ts")
    os.system("cd decrypt&&del *.ts")
    os.system("del get_dk")
    print(str(video.stem)+" 合并转换完成")

# 进度条
def progress_bar(words,now,total):
    print("\r"+words+":   "+"▋"*(now*50//total),str((now*100/total))+"%",end="")


  




