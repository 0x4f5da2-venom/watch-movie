import time
import requests
import os
import asyncio
import aiohttp
import aiofiles
from lxml import etree
from tqdm.asyncio import tqdm
from colorama import init, Fore
import pyfiglet

init(autoreset=True)

head = {
    'referer': 'https://www.wannengji.net/',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

proxy_url = 'http://127.0.0.1:7890'
oss = []

def search_in_file(search_term):
    with open('sql.txt', 'r') as f:
        print('正在查询中......')
        print('---------------')
        for line in f:
            line = line.strip()
            parts = line.split(':', 2)
            if len(parts) < 3:
                continue
            url = 'https:' + parts[1]
            line_change = parts[2]
            if search_term in line_change:
                oss.append(line)
                print(f'{line_change}')
    print(Fore.GREEN + '++正在为您匹配的全部有关的信息')
    return oss

def chose(cc):
    try:
        movie_name = input('请复制输入片名：')
        for entry in oss:
            parts = entry.split(':', 2)
            url = 'https:' + parts[1]
            line_change = parts[2]
            if cc == '0' and movie_name == line_change:
                print(url)
                return url
            elif cc == '1' and movie_name == line_change:
                print(f'请打开此----> {url} 就可进行播放---{line_change}')
            elif cc == '2':
                return advanced_search(movie_name)
    except Exception as e:
        print(e)

def advanced_search(movie_name=None):
    try:
        if not movie_name:
            movie_name = input(Fore.RED+'+高级搜索模式开启--(请再次输入电影名字):')
        ag1_url = f'https://www.wannengji.net/search/{movie_name}-1'
        ag1_re = requests.get(ag1_url, proxies={'http': proxy_url}).text
        tree = etree.HTML(ag1_re)
        a = 'https://www.wannengji.net'
        page = tree.xpath('//ul[@class="stui-page text-center clearfix"]/li/a/@href')[-1]
        page = page.split('-')[2]
        print(f"爬取总共的页数是: {page}")

        results = []
        for page_num in range(1, int(page) + 1):
            ag1_url = f'https://www.wannengji.net/search/{movie_name}-{page_num}'
            req = requests.get(ag1_url, proxies={'http': proxy_url}).text
            tree = etree.HTML(req)
            urls = tree.xpath('//div[@class="stui-vodlist__detail"]/h4/a/@href')
            names = tree.xpath('//div[@class="stui-vodlist__detail"]/h4/a/@title')

            if not names or not urls:
                print('没有找到资源-请重试')
            else:
                for url, name in zip(urls, names):
                    full_url = a + url
                    result = f"{full_url}: {name}"
                    results.append(result)
        for result in results:
            if movie_name in result:
                v = 'https:'
                url = v + result.split(':')[1]
                name = result.split(':')[2]
                print(Fore.RED+f'[++]高级查询到!-- {url} {name}')
                bf = input('选择[0]:远程下载到本地  [1]:提供在线观看地址：')
                if bf == '0':
                    print(f'正在远程下载{name}中请稍等....')
                    asyncio.run(async_download(url))

                elif bf == '1':
                    print(f'可以此电影的在线播放地址{url}')
                else:
                    print('请输入正确的数字！！eg(0 or 1)')
    except Exception as e:
        print(e)

def download_file(url_down):
    req = requests.get(url_down, headers=head).text
    tree = etree.HTML(req)
    download_url = tree.xpath('//source[@id="source"]/@src')[0]
    name = tree.xpath('/html/body/div[2]/div/div[1]/div/span[2]/text()')[0].replace(' ', '')
    return download_url, name

async def download_m3u8(session, download_url):
    try:
        print('正在进行m3u8的url抓取---')
        async with session.get(download_url) as response:
            content = await response.content.read()
            if response.status == 200:
                async with aiofiles.open("1.m3u8", 'wb') as f:
                    print(Fore.RED + '下载m3u8成功--')
                    await f.write(content)
    except Exception as e:
        print(e)

async def download_ts(session, line, n, path, retries=3):
    for attempt in range(retries):
        try:
            async with session.get(line) as response:
                content = await response.read()
                if response.status == 200:
                    async with aiofiles.open(f'./{path}/{n}.ts', mode='wb') as f:
                        await f.write(content)
                        return
                else:
                    print(Fore.GREEN + f'下载 {n} 失败，状态码：{response.status}')
        except Exception as e:
            print(Fore.GREEN + f'下载 {n} 失败，重试 {attempt + 1}/{retries}，错误：{e}')
        await asyncio.sleep(2)

def merge_ts_files(name, n):
    path = os.getcwd()
    path1 = 'ts'
    if not os.path.exists(path1):
        os.mkdir(path1)
        print(Fore.RED + f'已创建文件夹-->{path1}')
    path = os.path.join(path, path1)

    ts_files = [f'{i}.ts' for i in range(1, n)]
    ts_max = " ".join(ts_files)

    try:
        os.system(f'cd {path} && cat {ts_max} > {name}.mp4')
        print(Fore.RED + f'{name}--下载成功')
        os.system(f'cd {path} && rm -rf *.ts')
        print(Fore.RED + '*.ts--删除成功')
    except Exception as e:
        print(e)

async def async_download(url_down):
    download_url, name = download_file(url_down)
    connector = aiohttp.TCPConnector(limit_per_host=60)
    async with aiohttp.ClientSession(connector=connector) as session:
        session._default_proxy = proxy_url
        await download_m3u8(session, download_url)

        path = 'ts'
        tasks = []
        async with aiofiles.open('1.m3u8', mode='r', encoding='utf-8') as f:
            n = 1
            async for line in f:
                line = line.strip()
                if line.startswith('#'):
                    continue
                tasks.append(download_ts(session, line, n, path))
                n += 1
        print(pyfiglet.figlet_format("0 x 4 f 5 d a 2"))
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="下载进程"):
            await f

        merge_ts_files(name, n)

async def main():
    url_down = chose(cc)
    if not url_down:
        print('未找到此电影--请重试')
        return
    await async_download(url_down)

if __name__ == '__main__':
    search_term = input('请输入你想要看的电影名称：')
    start_time = time.time()
    search_in_file(search_term)
    if oss:
        cc = input('输入序号(0:下载观看: ，1:在线观看: ,2:在线高级搜索:)')
        asyncio.run(main())
    else:
        use_advanced = input('未找到匹配项，是否使用高级搜索模式？(y/n): ')
        if use_advanced.lower() == 'y':
            advanced_search()
    end_time = time.time()
    total_time = end_time - start_time
    print(f'总耗时: {total_time:.2f}秒')
