import RPi.GPIO as GPIO
import time
import threading
# リクエスト処理
import requests
import pprint
import json
# ホスト取得
import socket

led1 = 4
led2 = 17
led3 = 27
led4 = 22

sw1 = 5
sw2 = 6
sw3 = 13
sw4 = 19

R = 'R'
G = 'G'
B = 'B'
Y = 'Y'

leds = [led1, led2, led3, led4]
sws = [sw1, sw2, sw3, sw4]
swled = { sw1 : led1, sw2 : led2, sw3 : led3, sw4 : led4 }
clrled = { R : led1, G : led2, B : led3, Y : led4 }
swclr = { sw1 : R, sw2 : G, sw3 : B, sw4 : Y }
host = ''
stopFlash = False

ledsr = [led4, led3, led2, led1]

# GPIO設定
GPIO.setmode(GPIO.BCM)
GPIO.setup(leds, GPIO.OUT)
GPIO.setup(sws, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(leds, GPIO.LOW)

# タップン
evSwOn = threading.Event()

tapphrase = []
phrase = []
count = 0
is_active = False

# スイッチ押下コールバック
def tapping(sw):

    global tapphrase
    global evSwOn

#   スイッチonだったらフレーズ追加
    if not GPIO.input(sw):
        tapphrase.append(swclr[sw])
        print('(tapping)append phrase', sw, tapphrase)

        if not evSwOn.isSet():
            evSwOn.set()

    while not GPIO.input(sw):
        # 同時に押されているボタンを光らせる
        for swa in sws:
            if not GPIO.input(swa):
                GPIO.output(swled[swa], GPIO.HIGH)

            else:
                GPIO.output(swled[swa], GPIO.LOW)
#   離したらoff
    GPIO.output(swled[sw], GPIO.LOW)

# LED出力制御
def showLed():

    while True:
        freq = 50 # Hz (PWM のパルスを一秒間に 50 個生成)
        duty = 0.0 # デューティー比 0.0 で出力開始 (パルス内に占める HIGH 状態の時間が 0.0 %)
        np = 1
        count = 0

        pwms = []
        for led in leds:
            pwm = GPIO.PWM(led, freq)
            pwms.append(pwm)
            pwm.start(duty)

        print('(flash)start PMW1:', not is_active)
#       タイマーが有効じゃなければLED PWMにする
        while not is_active:
            # デューティー比 (duty cycle) を 0..100 の範囲で変化 (Ctrl-C 待ち)
            if duty >= 17:
                np = -1
            elif duty <= 1:
                np = 1
            duty = (duty + np) % 101
            # デューティー設定
            for pwm in pwms:
                pwm.ChangeDutyCycle(duty)
            # 調光のスピード
            time.sleep(0.054)

        # PWM停止
        for pwm in pwms:
            pwm.stop()

        print('(flash)start phrase:', is_active)

#       タイマー有効ならフレーズ再生
        while is_active:
            # if stopFlash :
            try:
                beat = count % 4
                if count < len(phrase):
                    GPIO.output(clrled[phrase[count]], GPIO.HIGH)
                    time.sleep(0.12)
                    GPIO.output(clrled[phrase[count]], GPIO.LOW)
                    time.sleep(0.02)

                elif beat == 0 :
                    for sw in sws:
                        GPIO.output(swled[sw], GPIO.HIGH)
                    time.sleep(0.001)

                    for sw in sws:
                        GPIO.output(swled[sw], GPIO.LOW)
                    time.sleep(0.139)

                else:
                    time.sleep(0.14)
                count += 1
                if count >= 16:
                    count = 0

            except Exception as e:
                print('(flash)Exception')
                print(e)
            finally:
                pass

# LED流す
def waveLed(wled, times):

    global phrase

    savedPhrase = phrase[:]
    phrase.clear()
    time.sleep(0.55)

    for i in range(times):
        for led in wled:
            GPIO.output(led, GPIO.HIGH)
            time.sleep(0.04)

        time.sleep(0.01)

        for led in wled:
            GPIO.output(led, GPIO.LOW)
            time.sleep(0.04)

    time.sleep(0.55)

    phrase = savedPhrase[:]

# LED点滅
def flashLed(led, times):
    global stopFlash
    # savedPhrase = phrase[:]
    # phrase.clear()
    stopFlash = True
    time.sleep(0.55)
    for i in range(times):
            GPIO.output(led, GPIO.HIGH)
            time.sleep(0.12)

            GPIO.output(led, GPIO.LOW)
            time.sleep(0.02)

    time.sleep(0.55)
    # phrase = savedPhrase[:]
    stopFlash = False

# リクエスト送信
def sendRequests(host, senPhrase, mode):

    global phrase
    global is_active

    # API_TOKEN = '6fc8b747c792dc7bd8a5f6743d1ec610'
    headers = {'content-type': 'application/json'}
    # auth = requests.auth.HTTPBasicAuth(API_TOKEN, 'api_token')
    url = 'https://script.google.com/macros/s/AKfycbw9Pctpv-5dUpYs8JrvF4dqN77OpWODIFwPDf-SYAs5EOgb2kM/exec'
    # url = 'https://dummy'

    phrasestr = ''.join(senPhrase)
    tapn_entry = {'tapn_entry':{'id':host,'phrase':phrasestr,'mode':mode}}
    data = json.dumps(tapn_entry)
    resPhrase = []

    if mode != 3:
        waveLed(leds, 2)

    try:
        pprint.pprint(data)
        r = requests.post(url,
                        # auth=auth,
                        data=data,
                        headers=headers)
    except Exception as e:
        print('(send)requests Exception')
        print(e)
        flashLed(led1, 8)
        return

    waveLed(ledsr, 2)

    print('(send)status code:' + str(r.status_code))

    if r.status_code == 200:
        print('(send)success')

        try:
            print('(send)print response')
            pprint.pprint(r)
            print('(send)parth response')
            j = r.json()
            print('(send)print json')
            pprint.pprint(j)
        except Exception as e:
            print('(send)parth json Exception')
            print(e)
            flashLed(led1, 4)
            return

        print('(send)print rc:', j['return']['rc'])
        print('(send)print response phrase:', j['return']['current_phrase'])
        print('(send)print response is_active:', j['return']['is_active'])


        if j['return']['rc'] == 0:
            print('(send)gas saccessed :p')
            flashLed(led2, 4)
        else:
            print('(send)gas failed XD')
            flashLed(led1, 4)

#       レスポンスフレーズセット
        phrasestr = j['return']['current_phrase']

        for s in phrasestr:
            resPhrase.append(s)

        phrase = resPhrase[:]
        if phrase == 'undefined':
            phrase.clear()

#       レスポンス実行ステータスセット
        res_is_active = j['return']['is_active']
        if res_is_active == 0:
            is_active = True
        else:
            is_active = False

    else:
        print('(send)request failed')
        flashLed(led1, 8)

# 照会バッチ処理
def getCurrent():

    global phrase
    while True:
        mode = 3
        # phrase = []

        # 送信
        tSend = threading.Thread(target=sendRequests, args=(host, phrase, mode,))
        tSend.setDaemon(True)
        tSend.start()

        time.sleep(30)

# メイン
def main():

    global phrase
    global count
    global is_active
    global host

    mode = 1

    host = socket.gethostname()

# 入力変化割り込みイベント設定
    for sw in sws:
        GPIO.add_event_detect(sw, GPIO.FALLING, callback=tapping, bouncetime=14)

    print('(main)tapn start!:', phrase)

    try:
        # 出力用スレッドスタート
        thshowLed = threading.Thread(target=showLed)
        thshowLed.setDaemon(True)
        thshowLed.start()

        # 照会系スレッドスタート
        thGetCue = threading.Thread(target=getCurrent)
        thGetCue.setDaemon(True)
        thGetCue.start()

        while True:
#           入力待ち
            print('(main)wait for tapping')
            evSwOn.wait()
            print('(main)start phrasing')
            evSwOn.clear()
#           入力あったらLED止める
            count = 0
            phrase.clear()
            is_active = True

            while True:
                # 待避
                lastphrase = tapphrase[:]
                # 入力待ち時間語に追加入力がなければ確定
                time.sleep(0.55)
                if (lastphrase == tapphrase):
                    phrase = tapphrase[:]
                    print('(main)phrase:', phrase)

                    # 開始処理
                    if len(phrase) == 1:
                        phrase.clear()
                        is_active = True
                        mode = 1

                    # 停止処理
                    elif phrase == [R, R]:
                        phrase.clear()
                        is_active = False
                        mode = 9

                    # フレーズ送信
                    else:
                        mode = 2

                    # 送信
                    tSend = threading.Thread(target=sendRequests, args=(host, phrase, mode,))
                    tSend.setDaemon(True)
                    tSend.start()

                    # 後始末
                    tapphrase.clear()
                    lastphrase.clear()
                    evSwOn.clear()
                    break

    # Ctrl+CでGPIO終了
    except KeyboardInterrupt:
        print('(main)Interrupt')
    except Exception as e:
        print(e)
    finally:
        # time.sleep(0.1)
        GPIO.cleanup()
        print('(main)Bye!')


if __name__ == '__main__':
    main()
