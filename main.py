import requests
import os
import openai
from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from google.cloud import vision

"""
API Functions
  - end-point: {host}/api/v1/{functions}
1 | phone/trust | 網頁爬蟲電話號碼可信度
2 | phone/trust | 網頁爬蟲電話號碼可信度
"""

try:
    from response import Response
    from service import GoogleSafeBrowsingService, OpenDataAPIService, OpenAIService, LibService, BlackListService, ImgurUploadService
    safebrowsing = GoogleSafeBrowsingService()
    opendata = OpenDataAPIService()
    chatgpt = OpenAIService()
    libs = LibService()
    blacks = BlackListService()
    imgs = ImgurUploadService()
    res = Response()
except Exception as e:
    print(str(e))

line_bot_api = LineBotApi("C3rkeZ32jHKGWaKx39q3pPxK4Ts2JjfUfbc65BUaLrlV2zbrnmfTUKVpDAsOKsdH2Qsk7KE/0ONy+Yt0YNup+3f8d/jSk4euLyNkIJJh0P4gWUmy9CGLk0K46+YlHFT2auPJGydhfYW3s6S8JaEcGAdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler("5f8376d2f0c52b98e92326a358080d7c")

app = Flask(__name__)

# 網頁爬蟲電話號碼可信度
@app.route('/api/v1/phone/trust', methods=['GET'])
def getPhoneData():
    phone = request.args.get('phone')
    if not phone:
        return res.errorWithData(400, "PHONE_INVAILD")
    
    url = 'https://phone-book.tw/search/{}.html'.format(phone)
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        trustable = soup.find(id='pho_num').text # 使用 ID 尋找元素
        return res.successWithData(int(trustable))
    else:
        return res.errorWithData(400, "NONE_RESULT")

@app.route('/api/v1/opendata/line', methods=['GET'])
def getOpenDataLine():
    url = "https://od.moi.gov.tw/api/v1/rest/datastore/A01010000C-002150-013"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json() 
            print(data["result"])
            return data
        else:
            print(f"API 请求失败，状态码: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"发生异常：{e}")
        return None
    

# 網頁爬蟲並詢問GPT可信度
@app.route('/api/v1/url', methods=['GET'])
def getWebDomData():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    
    if response.status_code == 200:
        # 撈網頁資料
        soup = BeautifulSoup(response.content, 'html.parser')
        # 撈詐騙LINE ID清單
        ScamResult, ScamStatus = opendata.callScamLineIdAPI()
        # 撈賭博網站清單
        GambleResult, GambleStatus = opendata.callGambleAPI()
            
        divs = soup.find_all('div')
        scamLists = []
        gambleLists = []
        prev = ""
        for item in divs:
            temp = libs.convertString(item.getText())
            if prev != temp and temp != None:
                prev = temp
                if ScamStatus:
                    scamLists = opendata.compareLineId(temp, ScamResult)
                if GambleStatus:
                    gambleLists = opendata.compareGambleWebUrl(url, GambleResult)

        articleScore = 0
        articleCount = 0
        articleSum = 0
        articleFeedback = 0
        articles = soup.find('article')
        for item in articles:
            article = libs.convertString(item.getText())
            description = soup.find("meta", property="og:description")["content"]
            title = soup.title.getText()
            temp = "該文章的標題是%s \n 關鍵字是%s \n 內文是%s" % (title, description, article)
            articleSum += chatgpt.createScoreChat(temp)
            articleCount += 1

        articleScore = articleSum / articleCount
        articleFeedback = libs.rankingArticle(articleScore)

        webHerfs = []
        links = soup.find_all('a')
        for link in links:
            if 'href' in link.attrs:
                if safebrowsing.isHttpUrl(link['href']):
                    webHerfs.append(link['href'])

        riskWebUrl = safebrowsing.risk(webHerfs)
                
        response = {
            "lineID": {
                "count": len(scamLists),
                "lists": scamLists
            },
            "scamWeb": {
                "count": len(gambleLists),
                "lists": gambleLists
            },
            "content": {
                "score": articleScore,
                "feedback": articleFeedback
            },
            "browsing": {
                "count": len(riskWebUrl),
                "lists": riskWebUrl
            }
        }
        return res.successWithData(response)
    else:
        return res.errorWithData(400, "NONE_RESULT")

# 判斷網站是否是黑名單資料
@app.route('/api/v1/url/type', methods=['GET'])
def getBlackList():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    output = []
    try:
        bres = blacks.searchTypeWeb(url)
        if len(bres) > 0:
            for bre in bres:
                output.append(blacks.typeResponser(bre))
            return res.successWithData(output)
        else:
            return res.success()
    except Exception as e:
        return res.errorWithData(400, "NONE_RESULT")
  
# 深度搜索並網頁爬蟲 比對資料評比
@app.route('/api/v1/url/deep', methods=['GET'])
def searchWebRelation():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    
    if response.status_code == 200:
        # 撈網頁資料
        soup = BeautifulSoup(response.content, 'html.parser')

        # 關鍵詞資料
        relates = []

        # 抓取關鍵詞 <h1> 資料
        headTitle1 = soup.find_all('h1')
        if not headTitle1 is None:
            for item in headTitle1:
                temp = libs.convertString(item.getText())
                relates.append(temp)
        
        # 抓取關鍵詞 <h2> 資料
        headTitle2 = soup.find_all('h2')
        if not headTitle2 is None:
            for item in headTitle2:
                temp = libs.convertString(item.getText())
                relates.append(temp)
                
        # 抓取關鍵詞 <meta description> <title> 資料
        description = soup.find("meta", property="og:description")["content"]
        title = soup.title.getText()
        relates.append(description)
        relates.append(title)

        # 查找Google相關資料但不包含本網址

        # 走訪5個網站，進行爬蟲+蒐集資料

        # 整合回覆並比對本網址article資料
        
        # 整合多方資料+給整合標籤

        # 計分
            
        response = {
            "search": {
                "host": "",
                "result": {
                    "score": 0,
                    "reason": ""
                },
                "record": [
                    {
                        "uri": "",
                        "score": "",
                    }
                ],
                "badges": {
                    "count": 0,
                    "data": []
                }
            }
        }
            
        return res.successWithData(response)
    else:
        return res.errorWithData(400, "NONE_RESULT")
  
# 查詢Google Vision API分析和處理圖像
# @app.route('/api/v1/vision', methods=['GET'])
# def searchWebRelation():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    
    if response.status_code == 200:
        # 撈網頁資料
        soup = BeautifulSoup(response.content, 'html.parser')

        # 關鍵詞資料
        relates = []

        # 抓取關鍵詞 <h1> 資料
        headTitle1 = soup.find_all('h1')
        if not headTitle1 is None:
            for item in headTitle1:
                temp = libs.convertString(item.getText())
                relates.append(temp)
        
        # 抓取關鍵詞 <h2> 資料
        headTitle2 = soup.find_all('h2')
        if not headTitle2 is None:
            for item in headTitle2:
                temp = libs.convertString(item.getText())
                relates.append(temp)
                
        # 抓取關鍵詞 <meta description> <title> 資料
        description = soup.find("meta", property="og:description")["content"]
        title = soup.title.getText()
        relates.append(description)
        relates.append(title)

        # 查找Google相關資料但不包含本網址

        # 走訪5個網站，進行爬蟲+蒐集資料

        # 整合回覆並比對本網址article資料
        
        # 整合多方資料+給整合標籤

        # 計分
            
        response = {
            "search": {
                "host": "",
                "result": {
                    "score": 0,
                    "reason": ""
                },
                "record": [
                    {
                        "uri": "",
                        "score": "",
                    }
                ],
                "badges": {
                    "count": 0,
                    "data": []
                }
            }
        }
            
        return res.successWithData(response)
    else:
        return res.errorWithData(400, "NONE_RESULT")
  
# 查詢Natural Language API辨識用
# @app.route('/api/v1/chat', methods=['GET'])
# def searchWebRelation():
    url = request.args.get('message')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    
    if response.status_code == 200:
        # 撈網頁資料
        soup = BeautifulSoup(response.content, 'html.parser')

        # 關鍵詞資料
        relates = []

        # 抓取關鍵詞 <h1> 資料
        headTitle1 = soup.find_all('h1')
        if not headTitle1 is None:
            for item in headTitle1:
                temp = libs.convertString(item.getText())
                relates.append(temp)
        
        # 抓取關鍵詞 <h2> 資料
        headTitle2 = soup.find_all('h2')
        if not headTitle2 is None:
            for item in headTitle2:
                temp = libs.convertString(item.getText())
                relates.append(temp)
                
        # 抓取關鍵詞 <meta description> <title> 資料
        description = soup.find("meta", property="og:description")["content"]
        title = soup.title.getText()
        relates.append(description)
        relates.append(title)

        # 查找Google相關資料但不包含本網址

        # 走訪5個網站，進行爬蟲+蒐集資料

        # 整合回覆並比對本網址article資料
        
        # 整合多方資料+給整合標籤

        # 計分
            
        response = {
            "search": {
                "host": "",
                "result": {
                    "score": 0,
                    "reason": ""
                },
                "record": [
                    {
                        "uri": "",
                        "score": "",
                    }
                ],
                "badges": {
                    "count": 0,
                    "data": []
                }
            }
        }
            
        return res.successWithData(response)
    else:
        return res.errorWithData(400, "NONE_RESULT")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print(400)

    return 'OK'

# 學你說話
ngrok_url = "https://46d5-219-69-73-188.ngrok-free.app"

@handler.add(MessageEvent)
def handle_message(event):
    print("-----測試-----\n\n", event, "\n\n-----結束-----")
    if (event.message.type == "image"):
        SendImage = line_bot_api.get_message_content(event.message.id)
        local_save = './images/' + event.message.id + '.png'
        with open(local_save, 'wb') as fd:
            for chenk in SendImage.iter_content():
                fd.write(chenk)
        client = vision.ImageAnnotatorClient()
        
        # 讀取圖像
        with open(local_save, 'rb') as image_file:
            context = image_file.read()
        
        # 將圖像轉換為 Vision API 的 image 物件
        image = vision.Image(content=context)

        # 使用 Vision API 進行圖像內容分析
        response = client.label_detection(image=image)

        # 分析結果
        labels = response.label_annotations
        for label in labels:
            print(label.description)
        
        img_url = imgs.glucose_graph(local_save)
        line_bot_api.reply_message(
            event.reply_token, 
            ImageSendMessage(original_content_url=img_url, preview_image_url=img_url)
        )
    
    if (event.message.type == "text"):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text)
        )

    if (event.message.type == "audio"):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="已收到音檔。")
        )
if __name__ == '__main__':
    app.run()
    app.debug = True
