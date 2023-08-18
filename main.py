import requests
import os
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from bs4 import BeautifulSoup
import asyncio
import datetime
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    PushMessageRequest,
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    Template,
    TemplateMessage,
    CarouselTemplate,
    ButtonsTemplate,
    MessageAction,
    URIAction,
    PostbackAction,
    FlexMessage, 
    FlexContainer,
    FlexComponent,
    AsyncMessagingApi
)
from linebot.v3.messaging.rest import ApiException
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    AudioMessageContent,
    StickerMessageContent,
    VideoMessageContent
)

try:
    from response import Response
    from service import GoogleSafeBrowsingService, OpenDataAPIService, OpenAIService, \
        LibService, BlackListService, ImgurUploadService, WebCrawlerService, \
        GoogleVisionAIService, LineBotMessageService, GoogleSheetService
    safebrowsing = GoogleSafeBrowsingService()
    opendata = OpenDataAPIService()
    chatgpt = OpenAIService()
    libs = LibService()
    blacks = BlackListService()
    imgs = ImgurUploadService()
    webs = WebCrawlerService()
    res = Response()
    visions = GoogleVisionAIService()
    linebots = LineBotMessageService()
    sheets = GoogleSheetService()
except Exception as e:
    print(str(e))

configuration = Configuration(access_token='C3rkeZ32jHKGWaKx39q3pPxK4Ts2JjfUfbc65BUaLrlV2zbrnmfTUKVpDAsOKsdH2Qsk7KE/0ONy+Yt0YNup+3f8d/jSk4euLyNkIJJh0P4gWUmy9CGLk0K46+YlHFT2auPJGydhfYW3s6S8JaEcGAdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('5f8376d2f0c52b98e92326a358080d7c')

app = Flask(__name__, static_folder = "./static", template_folder = "./templates")
CORS(app)

@app.route('/')
def hello_world():
    return render_template('index.html')

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

# ##########
# Web Routes
# ##########

# WebAPI.1-1 search web dom
@app.route('/api/v1/web/crawler', methods=['GET'])
def getWebCrawler():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        result = webs.progress_elements(soup=soup)
        return res.successWithData(result)
    else:
        return res.errorWithData(400, "NONE_RESULT")

# WebAPI.1-2 compare blocklist and opendata
@app.route('/api/v1/web/blocklist', methods=['GET'])
def getWebBlocklist():
    text = request.args.get('text')
    if not text:
        return res.errorWithData(400, "URL_INVAILD")
    try:
        output = []
        # 撈詐騙LINE ID清單
        ScamResult, ScamStatus = opendata.callScamLineIdAPI()
        # 撈賭博網站清單
        GambleResult, GambleStatus = opendata.callGambleAPI()

        # Blocklist Search
        bres = blacks.searchTypeWeb(text)
        if len(bres) > 0:
            for bre in bres:
                output.append(blacks.typeResponser(bre))
            
        if ScamStatus:
            scamLists = opendata.compareLineId(text, ScamResult)
            if len(scamLists) > 0:
                output.append("lineid")
        if GambleStatus:
            gambleLists = opendata.compareGambleWebUrl(text, GambleResult)
            if len(gambleLists) > 0:
                output.append("fakewe")
        return res.successWithData(output)
    except Exception as e:
        return res.errorWithData(400, "NONE_RESULT")

@app.route('/api/v1/web/deep', methods=['GET'])
def getWebDeepsearch():
    return None

@app.route('/api/v1/web/key', methods=['GET'])
def getSheetSavingContext():
    id = request.args.get('key')
    if not id:
        return res.errorWithData(400, "KEY_INVAILD")
    title, context, img = sheets.queryLineResult(id)
    result = {
        "title": title,
        "context": context,
        "img": img
    }
    return res.successWithData(result)

@app.route('/api/v1/web/comment', methods=['POST'])
def postWebComment():
    return None

# ##########
# Extension Routes
# ##########

# ExtensionAPI.2-1 跑所有的連結並送進Google Safe Browser
@app.route('/api/v1/ext/risk', methods=['GET'])
def getExtensionRisk():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        return res.errorWithData(400, "NONE_RESULT")
    
    webHerfs = []
    links = soup.find_all('a')
    for link in links:
        if 'href' in link.attrs:
            if safebrowsing.isHttpUrl(link['href']):
                webHerfs.append(link['href'])
    riskWebUrl = safebrowsing.risk(webHerfs)

    response = {
        "count": len(riskWebUrl),
        "lists": riskWebUrl
    }
    return res.successWithData(response)    

# ExtensionAPI.2-2 跑所有的連結和文字並比對Blocklist&opendata
@app.route('/api/v1/ext/context', methods=['GET'])
def getUrlContext():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    # 過濾清單
    filters = []
    for key in range(len(blacks.using)):
        if request.args.get(blacks.using[key]) != "1":
            filters.append(blacks.using[key])
    
    response = requests.get(url)
    try:
        # 爬蟲&call API
        soup = BeautifulSoup(response.content, 'html.parser')
        ScamResult, ScamStatus = opendata.callScamLineIdAPI()
        GambleResult, GambleStatus = opendata.callGambleAPI()
    except Exception as e:
        return res.errorWithData(400, "NONE_RESULT")
    
    # 危險清單
    output = []

    # 抓取所有的網頁文本
    divs = soup.find_all('div')
    context = libs.contextOutput(divs)
    
    # 抓取所有的網頁連結屬性
    hrefs = soup.find_all('a')
    links = libs.hrefsOutput(hrefs)
    
    # 比對所有的黑名單
    if len(links) > 0:
        bres = blacks.checkMultiableData(links, filters)
        if len(bres) > 0:
            for bre in bres:
                output.append(blacks.typeResponser(bre))

    # 比對所有的資料
    scamLists = opendata.compareLineId(context, ScamResult)
    if len(scamLists) > 0:
        output.append(scamLists[0])
    
    # 比對所有的資料
    gambleLists = opendata.compareGambleWebUrl(links, GambleResult)
    if len(gambleLists) > 0:
        for gms in gambleLists:
            output.append(gms)

    response = {
        "output": output,
        "lengths": len(output)
    }
    return res.successWithData(response)

# ExtensionAPI.2-3 跑所有的圖片並送入Vision AI
@app.route('/api/v1/ext/image', methods=['GET'])
def getExtensionImage():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        return res.errorWithData(400, "NONE_RESULT")
    
    imgTags = soup.find_all("img")
    count = 0
    checklist = [0, 0, 0, 0, 0]
    for img in imgTags:
        imgUrl = img.get("src")
        if safebrowsing.isHttpUrl(imgUrl) != None:
            checklist = visions.queryImage(imgUrl, checklist)
            count += 1
    ans = visions.stageInference(checklist, count)
    return res.successWithData(ans)

# ExtensionAPI.2-4 跑指定標籤內的文本並送入ChatGPT API進行評分
@app.route('/api/v1/ext/trust', methods=['GET'])
def getExtensionTrust():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

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

        response = {
            "score": articleScore,
            "feedback": articleFeedback
        }
        return res.successWithData(response)
    else:
        return res.errorWithData(400, "NONE_RESULT")

# ExtensionAPI.2-5 跑指定標籤內的文本並送入ChatGPT API進行分類
@app.route('/api/v1/ext/badge', methods=['GET'])
def getExtensionBadge():
    url = request.args.get('url')
    if not url:
        return res.errorWithData(400, "URL_INVAILD")
    
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # 抓取所有的網頁文本
        divs = soup.find_all('div')
        context = libs.contextOutput(divs)
        
        # 篩選出最長的篇章
        maxlength = 0
        keycontext = ""
        for con in context:
            if len(con) > maxlength and len(con) < 3000:
                maxlength = len(con)
                keycontext = con

        ans = chatgpt.createBadgeChat(keycontext)
        return res.successWithData(ans)
    else:
        return res.errorWithData(400, "NONE_RESULT")

# ExtensionAPI.2-6 將所有的資訊回送進DB
@app.route('/api/v1/ext/save', methods=['POST'])
def postExtensionSave():
    return None

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

# ##########
# Linebot Routes
# ##########

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    # app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    if event.message.text == "閱讀操作說明":
        descriptionTemplate = linebots.descriptionTemplate()
        linebots.sendReplyMessage(configuration, event, descriptionTemplate)
    elif event.message.text == "查看安裝說明":
        installTemplate = linebots.installTemplate()
        linebots.sendReplyMessage(configuration, event, installTemplate)
    elif event.message.text == "Chrome插件安裝資訊":
        descriptionTemplate = linebots.descriptionTemplate()
        linebots.sendReplyMessage(configuration, event, descriptionTemplate)
    elif event.message.text == "Firefox插件安裝資訊":
        descriptionTemplate = linebots.descriptionTemplate()
        linebots.sendReplyMessage(configuration, event, descriptionTemplate)
    elif event.message.text == "Safari插件安裝資訊":
        descriptionTemplate = linebots.descriptionTemplate()
        linebots.sendReplyMessage(configuration, event, descriptionTemplate)
    elif event.message.text == "LINE機器人安裝資訊":
        descriptionTemplate = linebots.descriptionTemplate()
        linebots.sendReplyMessage(configuration, event, descriptionTemplate)
    else:
        nowTime = libs.convertTimestamp()
        text, allText = chatgpt.createLinebotChat(event.message.text)
        sheets.appendValue(nowTime, event.message.text, allText, "")
        textTemplate = linebots.trustableTextTemplate(event, text, nowTime)
        try:
            linebots.sendReplyMessage(configuration, event, textTemplate)
        except ApiException as e:
            if 'x_line_retry_key' in e.error.details:
                retry_key = e.error.details['x_line_retry_key']
                with ApiClient(configuration) as api_client:
                    line_bot_api = MessagingApi(api_client)
                    line_bot_api.push_message(
                        PushMessageRequest(
                        x_line_retry_key=retry_key,
                        messages=[textTemplate]
                    )
                )
            else:
                print('Other LineBotApiError:', e)
        
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    url = f"https://api-data.line.me/v2/bot/message/{event.message.id}/content"
    headers = { "Authorization": f"Bearer C3rkeZ32jHKGWaKx39q3pPxK4Ts2JjfUfbc65BUaLrlV2zbrnmfTUKVpDAsOKsdH2Qsk7KE/0ONy+Yt0YNup+3f8d/jSk4euLyNkIJJh0P4gWUmy9CGLk0K46+YlHFT2auPJGydhfYW3s6S8JaEcGAdB04t89/1O/w1cDnyilFU=" }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open('downloaded_image.png', 'wb') as f:
            f.write(response.content)
            link = imgs.glucose_graph()
            repo = visions.queryImageContent(response.content)
            output, allText = chatgpt.createLinebotChat(repo)
            nowTime = libs.convertTimestamp()
            sheets.appendValue(nowTime, "檢測圖片結果", allText, link)
    try:
        title = "檢測圖片結果"
        imgButtonTemplate = linebots.imageResponseTemplate(title, output, link, nowTime)
        linebots.sendReplyMessage(configuration, event, imgButtonTemplate)
    except ApiException as e:
        if 'x_line_retry_key' in e.error.details:
            print(e)
            retry_key = e.error.details['x_line_retry_key']
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.push_message(
                    PushMessageRequest(
                        x_line_retry_key=retry_key,
                        messages=[imgButtonTemplate]
                    )
                )
        else:
            print('Other LineBotApiError:', e)

@handler.add(MessageEvent, message=AudioMessageContent)
def handle_audio_message(event):
    audioUpload = False
    title = "檢測語檔結果"
    text = ""
    url = f"https://api-data.line.me/v2/bot/message/{event.message.id}/content"
    headers = { "Authorization": f"Bearer C3rkeZ32jHKGWaKx39q3pPxK4Ts2JjfUfbc65BUaLrlV2zbrnmfTUKVpDAsOKsdH2Qsk7KE/0ONy+Yt0YNup+3f8d/jSk4euLyNkIJJh0P4gWUmy9CGLk0K46+YlHFT2auPJGydhfYW3s6S8JaEcGAdB04t89/1O/w1cDnyilFU=" }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            with open('./downloaded_audio.mp3', 'wb') as f:
                for chunk in response.iter_content():
                    f.write(chunk)
            audioUpload = True
        except Exception as e:
            audioUpload = False

    if audioUpload :
        chat = chatgpt.audioTransText()
        text, allText = chatgpt.audioLinebotChat(chat)
        nowTime = libs.convertTimestamp()
        sheets.appendValue(nowTime, chat, allText, "")
    else:
        text = "很抱歉，系統出現異常，請稍後再試。"

    try:
        textTemplate = linebots.audioResponseTemplate(title, text, nowTime)
        linebots.sendReplyMessage(configuration, event, textTemplate)
    except ApiException as e:
        if 'x_line_retry_key' in e.error.details:
            retry_key = e.error.details['x_line_retry_key']
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.push_message(
                    PushMessageRequest(x_line_retry_key=retry_key,messages=[textTemplate])
                )
        else:
            print('Other LineBotApiError:', e)

@handler.add(MessageEvent, message=VideoMessageContent)
def handle_video_message(event):
    template = linebots.unServiceTemplate("video")
    linebots.sendReplyMessage(configuration, event, template)

@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event):
    template = linebots.unServiceTemplate("sticker")
    linebots.sendReplyMessage(configuration, event, template)

if __name__ == '__main__':
    app.debug = True
    app.run()