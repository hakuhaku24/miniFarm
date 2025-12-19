# miniFarm迷你溫室
112403545王柏翔
***
## 專案簡介
這個裝置目的是盡量遠端化種植的基本動作，自動澆水、偵測水位，使用者也可以手動操控風扇降溫、控制抽水馬達開啟關閉，用line messenging api傳送通知給使用者知道植物的狀況：土穰濕度狀況，水箱的水還夠不夠。
專案所需材料
1. raspberry pi 4
2. 二路繼電器一個
3. 土穰濕度傳感器
4. 水位傳感器
5. USB充電器改裝外接電源
6. 沉水式小型抽水馬達
7. DC散熱風扇 5V

## 裝置照片 

<img src="https://github.com/user-attachments/assets/d76b05cf-b9fa-4c74-b698-d09ab2f1c4b0" width="50%" height="60%">

![274b5ef2-f481-4030-8bab-6805572b80e2](https://github.com/user-attachments/assets/dfb06d16-ef96-4ad6-963b-613b6a0e97a1)

## 程式碼功能介紹

## 前置
```
import RPi.GPIO as GPIO
import time
import requests
from flask import Flask, render_template, request, jsonify
from linebot import LineBotApi
from linebot.models import TextSendMessage
```

## 定義函數 

發訊息給使用者、控制繼電器、自動澆水的if邏輯，開機前 10 秒不動作，等待感測器訊號穩定，手動關閉後 20 秒內自動邏輯不介入，偵測到缺水時強制切斷馬達，並傳送 LINE 通知。這幾行確保系統不會因為空抽或頻繁開關而損壞。
```
def send_line(msg):
    try:
        line_bot_api.push_message(USER_ID, TextSendMessage(text=msg))
    except Exception as e:
        print(f"LINE 發送失敗: {e}")

def set_gpio(pin, action):
    if action == "ON":
        GPIO.output(pin, GPIO.LOW)
        return "ON"
    else:
        GPIO.output(pin, GPIO.HIGH)
        if pin in [WATER_PUMP_PIN, FAN_PIN]:
            global LAST_MANUAL_OFF_TIME
            LAST_MANUAL_OFF_TIME = time.time()
        return "OFF"

def auto_logic():
    global current_data, control_status
    curr = time.time()
    soil = GPIO.input(SOIL_SENSOR_PIN)
    water = GPIO.input(WATER_LEVEL_PIN)
    
    current_data["soil_status"] = "極乾燥 " if soil == GPIO.LOW else "濕度足夠 "
    current_data["water_level"] = "缺水 " if water == GPIO.LOW else "正常 "
    
    if (curr - SYSTEM_START_TIME) < STARTUP_DELAY: return
    if (curr - LAST_MANUAL_OFF_TIME) < MANUAL_COOLDOWN: return

    if soil == GPIO.LOW and control_status["pump"] == "OFF":
        if water == GPIO.LOW:
            send_line("\n 警告：溫室缺水！\n水箱已空，馬達已強制停機，請加水。")
            return
        
        send_line("\n 系統提示：自動澆水啟動 (3秒)。")
        control_status["pump"] = set_gpio(WATER_PUMP_PIN, "ON")
        time.sleep(3)
        control_status["pump"] = set_gpio(WATER_PUMP_PIN, "OFF")
```

## Web服務

```=python
app = Flask(__name__)

@app.route("/")
def index():
    auto_logic()
    return render_template("index.html", data=current_data, status=control_status)

@app.route("/control/<device>/<action>", methods=["POST"])
def control(device, action):
    pin = WATER_PUMP_PIN if device == "pump" else FAN_PIN
    control_status[device] = set_gpio(pin, action.upper())
    return jsonify({"status": "ok", "device": device, "action": control_status[device]})

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n系統關閉")
    finally:
        GPIO.cleanup()
```
## messenging api設定
```
CHANNEL_ACCESS_TOKEN = "寫自己的Token"
USER_ID = "User ID"

# 初始化 LINE API
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
```

## Web服務

```
@app.route("/control/<device>/<action>", methods=["POST"])
def control(device, action):
    # 判斷要控制馬達還是風扇
    pin = WATER_PUMP_PIN if device == "pump" else FAN_PIN
    # 執行開啟或關閉動作
    control_status[device] = set_gpio(pin, action.upper())
    return jsonify({"status": "ok"})
```
---
## 環境建置與軟體安裝流程

1. 安裝樹莓派
2. 安裝相關工具
```
sudo apt-get install python3-pip python3-dev -y
pip3 install flask line-bot-sdk requests
```
3. 去line官網申請一個企業帳號，申請完成後在messenging api拿到金鑰，程式碼這兩行打上
```
CHANNEL_ACCESS_TOKEN = '自己的金鑰'
USER_ID = '自己的USERID'
```

---
# 遇到的困難

現在的濕度傳感器是我在五金行40塊買的，超難用，要很乾他才會輸出0，原本想用DHT22溫濕度感測器，但那類比輸出的，我沒有買到ADC，我應該上網買的沒想到電子材料行買不到，所以這個問題沒解決。

我本來以為風扇跟抽水馬達買小功率的，應該電池組就夠力了，但後來發現抽水馬達完全不抽，風扇也轉移下就停，所以主供電我後來把我用不到的USB充電線剪掉，剪開發現裡面有五條線，而且黑色還不是負極，用三用電表找出正負極之後把它拿來當供電就沒問題了，其他三根線用膠布包起來。
![7453ff5e-68e8-486b-9f77-20871a7d38d3](https://github.com/user-attachments/assets/2dc87bc2-839f-4167-8eef-33532aaa989c)

# 可以改進的地方
聲控系統沒有做，前端做得很醜，植物還沒長出來應該直接去買一株成熟有綠葉的植物，可以做更多色彩分析判斷植物的健康度，也可以用紅外線感溫看植物溫度，想到很多但是都沒有做出來。

<img width="464" height="582" alt="螢幕擷取畫面 2025-12-19 071618" src="https://github.com/user-attachments/assets/b83a12dd-4feb-47fc-b0df-dc5a430e6ac0" />

![下載 (1)](https://github.com/user-attachments/assets/cc3a8af3-c0df-4c40-8dcf-13b0a3c334fb)
