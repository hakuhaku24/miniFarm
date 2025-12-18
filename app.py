import RPi.GPIO as GPIO
import time
from flask import Flask, render_template, request, jsonify
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 硬體與 API 設定 ---
WATER_PUMP_PIN = 17      
FAN_PIN = 27             
SOIL_SENSOR_PIN = 22     
WATER_LEVEL_PIN = 21     

# LINE API資訊
CHANNEL_ACCESS_TOKEN = "wvZgUDMHJPwtbrcb5DVJbm1ZJ2EcJ26zgX8oOoszKvb2ZlSW6Hqb5QxETTjjybGS4vxF7eT/MGiKlqbrbNQWjwij8Ozz8f2d6IemrmL/8GkOkTjAYqz+MW8D5y3VCBmPO7HSeXA/PK3QBkA4/2mWPgdB04t89/1O/w1cDnyilFU="
USER_ID = "U7dd86ac1bce1c9655fc58bab755e7982"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)

GPIO.setmode(GPIO.BCM)
GPIO.setup(WATER_PUMP_PIN, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(FAN_PIN, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(SOIL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(WATER_LEVEL_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- 2. 全域狀態 ---
current_data = {"soil_status": "讀取中...", "water_level": "正常"}
control_status = {"pump": "OFF", "fan": "OFF"}
LAST_MANUAL_OFF_TIME = 0
MANUAL_COOLDOWN = 20         
SYSTEM_START_TIME = time.time()
STARTUP_DELAY = 10           

# --- 3. 功能函數 ---

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
    
    current_data["soil_status"] = "極乾燥 🚨" if soil == GPIO.LOW else "濕度足夠 ✅"
    current_data["water_level"] = "缺水 🚨" if water == GPIO.LOW else "正常 ✅"
    
    if (curr - SYSTEM_START_TIME) < STARTUP_DELAY: return
    if (curr - LAST_MANUAL_OFF_TIME) < MANUAL_COOLDOWN: return

    if soil == GPIO.LOW and control_status["pump"] == "OFF":
        if water == GPIO.LOW:
            send_line("\n❌ 警告：溫室缺水！\n水箱已空，馬達已強制停機，請加水。")
            return
        
        send_line("\n🌱 系統提示：自動澆水啟動 (3秒)。")
        control_status["pump"] = set_gpio(WATER_PUMP_PIN, "ON")
        time.sleep(3)
        control_status["pump"] = set_gpio(WATER_PUMP_PIN, "OFF")

# --- 4. Web 服務 ---
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
