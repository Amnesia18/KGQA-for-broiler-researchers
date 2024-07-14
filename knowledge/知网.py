import os
import re
import time
import random
import pandas as pd
from lxml import etree
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

def next_page(driver):
    driver.execute_script("$(arguments[0]).click()", driver.find_element(By.ID, 'PageNext'))
    time.sleep(2)


def parse_page(driver, datas):
    html = etree.HTML(driver.page_source)
    trs = html.xpath('//table[@class="result-table-list"]/tbody/tr')
    for tr in trs:
        title = tr.xpath('.//td//a[@class="fz14"]//text()')
        title = ''.join(title).strip()

        authors = tr.xpath('.//td[@class="author"]//text()')
        authors = ''.join(authors).strip()

        source = tr.xpath('.//td[@class="source"]//text()')
        source = ''.join(source).strip()

        date = tr.xpath('.//td[@class="date"]//text()')
        date = ''.join(date).strip()

        database = tr.xpath('.//td[@class="data"]//text()')
        database = ''.join(database).strip()

        counted = tr.xpath('.//td[@class="quote"]//text()')
        counted = ''.join(counted).strip()
        if counted == '':
            counted = '0'

        download_count = tr.xpath('.//td[@class="download"]//text()')
        download_count = ''.join(download_count).strip()
        if download_count == '':
            download_count = '0'

        data_pack = {
            "title": title,
            "authors": authors,
            "source": source,
            "date": date,
            "database": database,
            "counted": counted,
            "downloadCount": download_count,
        }
        datas.append(data_pack)
    time.sleep(random.uniform(2, 4))


def search(driver, keyword, date_start, date_end):
    url = 'https://kns.cnki.net/kns8/AdvSearch?dbprefix=SCDB&&crossDbcodes=CJFQ%2CCDMD%2CCIPD%2CCCND%2CCISD%2CSNAD' \
          '%2CBDZK%2CCJFN%2CCCJD '
    driver.get(url)
    time.sleep(3)
    search_page = driver.find_element(By.XPATH, "//li[@name='majorSearch']")
    search_page.click()
    time.sleep(3)
    search_win = driver.find_element(By.CSS_SELECTOR, '.textarea-major')
    search_win.send_keys(keyword)
    search_btn = driver.find_element(By.CSS_SELECTOR, '.btn-search')
    search_btn.click()
    time.sleep(3)
    js = 'document.getElementById("datebox0").removeAttribute("readonly");'
    driver.execute_script(js)
    js_value = 'document.getElementById("datebox0").value="{}"'.format(date_start)
    driver.execute_script(js_value)
    js = 'document.getElementById("datebox1").removeAttribute("readonly");'
    driver.execute_script(js)
    js_value = 'document.getElementById("datebox1").value="{}"'.format(date_end)
    driver.execute_script(js_value)
    search_btn.click()


# 其他代码保持不变

def store(data, filename='陈松林-.xlsx'):
    # 检查数据是否为空，避免保存空文件
    if data:
        abs_path = os.path.dirname(os.path.abspath(__file__))
        out_path = os.path.join(abs_path, filename)
        df = pd.DataFrame(data)
        df.to_excel(out_path, index=False)  # 设置 index=False 避免保存行索引


def main(driver, datas):
    pages = driver.find_element(By.CLASS_NAME, 'countPageMark').text
    pages = re.sub(r"\D", "", pages)

    # 保存初始空文件，确保后续追加数据
    store([])

    for i in range(int(pages)):
        parse_page(driver, datas)
        print("成功爬取第" + str(i + 1) + "页")

        # 保存当前已爬取的数据
        store(datas)

        if i < int(pages) - 1:  # 如果不是最后一页，翻页
            next_page(driver)
        else:
            print("成功爬取第" + str(i + 1) + "页（最后一页），程序结束")



if __name__ == "__main__":
    # 使用本地下载的ChromeDriver路径
    driver_path = r"D:\chromedriver-win64\chromedriver-win64\chromedriver.exe"
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)
    keyword = "AU='陈松林' and AF='中国科学院水生生物研究所'"
    search(driver, keyword, date_start="1900-10-25", date_end="2024-6-25")
    time.sleep(3)
    datas = []
    main(driver, datas)
    store(datas)
    driver.close()
    driver.quit()
