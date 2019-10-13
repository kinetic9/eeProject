# Imports
import datetime  # for timing
import threading  # for threads
import time  # for time --> remove when rtc is working

import blynklib  # for blynk app
import RPi.GPIO as GPIO  # for GPIO
import spidev  # for SPI

# ---------------------------Global Variables----------------------------

IsGPIO = False
IsSPI = False
delay = 1 #inital delay time
logging = True
blynk = blynklib.Blynk('YX0MrCEqDyKmbWiOJO-8sgqcq7YmGzZu')  # Initialize Blynk

# For ADC SPI
firstByte = int('00000001', 2)
lightByte = int('10000000', 2)
tempByte  = int('10010000', 2)
humidityByte = int('10100000', 2)
lastByte = int('00000000', 2)

adc = spidev.SpiDev()

# For time
sysStart = datetime.datetime.now()
Data = ["00:00:00", 0, 0, 0]

# For threads
threads = []

# For temperature
Tc = 0.01  # Volts/(degrees Celcius)
V_0 = 0.55  # Volts

Vout = 0

# ----------------------------functions----------------------------------


def init():

    # init Gpio
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(36, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(29, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    
    # init SPI    adc = spidev.SpiDev()
    adc.open(0, 0)
    IsSPI = True

    # Set up threads
    dataThread = threading.Thread(target=dataThreadFunction)
    mainThread = threading.Thread(target=mainThreadFunction)
    DACThread = threading.Thread(target=DACThreadFunction)
    buttonThread = threading.Thread(target=buttonThreadFunction)
    threads.append(mainThread)
    threads.append(DACThread)
    threads.append(dataThread)
    threads.append(buttonThread)

    # Setup interupts for HW buttons
    GPIO.add_event_detect(7, GPIO.FALLING, callback=increment, bouncetime=130)
    GPIO.add_event_detect(11, GPIO.FALLING, callback=decrement, bouncetime=130)
    GPIO.add_event_detect(36, GPIO.FALLING, callback=resetSysTime, bouncetime=130)
    GPIO.add_event_detect(29, GPIO.FALLING, callback=stopStart, bouncetime=130)

    # Start threads
    for thread in threads:
        thread.start()


def mainThreadFunction():
    global Vout
    global delay
    global logging
    while(1):
        if(logging):
            now = datetime.datetime.now()
            print('|{:^10}|{:^11}|   {:1.1f}V   |  {:2.0f}°C  |  {:^4.0f} |  {:1.2f}V  |   {}   |'.format(
                now.strftime("%H:%M:%S"), str(now-sysStart)[:-7], Data[1], Data[2], Data[3], Vout, " "))
            print(
                "+----------+-----------+----------+--------+-------+---------+-------+")
            wait = time.time()
            while((time.time()-wait) < delay):
                pass


def dataThreadFunction():
    global sysSec
    while(1):
        getADCData()
        time.sleep(1)


def DACThreadFunction():
    global Vout
    while (1):
        Vout = Data[1]/1023 * Data[3]
        time.sleep(1)


def buttonThreadFunction():
    # Register Virtual Pins
    ## @blynk.VIRTUAL_WRITE(1)
    def my_write_handler(value):
        global delay
        delay = int(value[0])

    while(1):
        blynk.run()


def convertToVoltage(ADC_Output, Vref=3.3):
    v = ((ADC_Output[1] & int('00000011', 2)) << 8) + ADC_Output[2]
    return (v*Vref)/1024.0


def getHumidty():
    data = [firstByte, humidityByte, lastByte]
    adc.xfer(data, 10000, 24)
    return convertToVoltage(data)


def getLight():
    data = [firstByte, lightByte, lastByte]
    adc.xfer(data, 10000, 24)
    v = ((data[1] & int('00000011', 2)) << 8) + data[2]
    return (2**10 - 1 - v)


def getTemperature():
    data = [firstByte, tempByte, lastByte]
    adc.xfer(data, 10000, 24)
    temp = (convertToVoltage(data)-V_0)/Tc
    return temp


def getADCData():
    Data[1] = getHumidty()
    Data[3] = getLight()
    Data[2] = getTemperature()
    return


def decrement(channel):
    global delay
    switcher = {
        2: 1,
        5: 2,
    }
    delay = switcher.get(delay, delay)


def increment(channel):
    global delay
    switcher = {
        1: 2,
        2: 5,
    }
    delay = switcher.get(delay, delay)


def resetSysTime(channel):
    global sysStart
    sysStart = datetime.datetime.now()


def stopStart(channel):
    global logging
    if(logging):
        logging = False
        print("\nLogging stopped.. ")
    else:
        logging =True
        print("\nLogging started.. ")
    
    


def main():
    global Vout
    print("+====================================================================+")
    print("|                              Starting                              |")
    print("+----------+-----------+----------+--------+-------+---------+-------+")
    print("| RTC Time | Sys Timer | Humidity |  Temp  | Light | DAC Out | Alarm |")
    print("+==========+===========+==========+========+=======+=========+=======+")
    init()
    getADCData()
    Vout = Data[1]/1023 * Data[3]


def cleanUp():
    if IsGPIO:
        GPIO.cleanup()
    if IsSPI:
        adc.close()
    for thread in threads():
        thread.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting gracefully")
        cleanUp()
    except Exception as e:
        cleanUp()
        print("Error: ")
        print(str(e))
