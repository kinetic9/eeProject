#!/usr/bin/python3
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
alarm = 0
timer = 0
msg = ""


# For ADC SPI

lightByte = int('10000000', 2)
tempByte  = int('10010000', 2)
humidityByte = int('10100000', 2)


adc = spidev.SpiDev()

# For time
sysStart = datetime.datetime.now()
Data = ["00:00:00", 0, 0, 0]

# For threads
threads = []

# For temperature

V_0 = 0.55  # Volts

Vout = 0

# ----------------------------functions----------------------------------


def init():

    # init Gpio
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(36, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(29, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    GPIO.setup(31,GPIO.OUT)

    adc.open(0, 0)
    IsSPI = True

    # Set up threads
    dataThread = threading.Thread(target=dataThreadFunction)
    mainThread = threading.Thread(target=mainThreadFunction)
    DACThread = threading.Thread(target=DACThreadFunction)
    blynkThread = threading.Thread(target=blynkThreadFunction)
    threads.append(mainThread)
    threads.append(DACThread)
    threads.append(dataThread)
    threads.append(blynkThread)

    # Setup interupts for HW buttons
    GPIO.add_event_detect(7, GPIO.FALLING, callback=changeSampleTime, bouncetime=400)
    GPIO.add_event_detect(11, GPIO.FALLING, callback=toggleMonitoring, bouncetime=400)
    GPIO.add_event_detect(36, GPIO.FALLING, callback=resetSysTime, bouncetime=400)
    GPIO.add_event_detect(29, GPIO.FALLING, callback=alarmReset, bouncetime=400)

    # Start threads
    for thread in threads:
        thread.start()


def mainThreadFunction():
    global Vout
    global delay
    global logging
    global alarm
    global timer
    
    #blynk.run()
    while(1):
        if(logging):
            now = datetime.datetime.now()
            print('|{:^10}|{:^11}|   {:1.1f}V   |  {:2.0f}°C  |  {:^4.0f} |  {:1.2f}V  |   {}   |'.format(
                now.strftime("%H:%M:%S"), str(now-sysStart)[:-7], Data[1], Data[2], Data[3], Vout, str(alarm)))
            print("+----------+-----------+----------+--------+-------+---------+-------+")
            wait = time.time()
            while((time.time()-wait) < delay):
                pass
            
            GPIO.output(31, alarm)
            blynk.run()
            
            if (Vout>2.65 or Vout<0.65) :
                alarm = 1
                
                
            
           


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


def blynkThreadFunction():
    # Register Virtual Pins
    
    @blynk.handle_event('read V0')
    def read_virtual_pin_handler(pin):
    
        
        
        global sysStart
        global logging
        global alarm
        global Data
        global blynk

        if (logging):
            blynk.virtual_write(0,str(Data[3]))
            blynk.virtual_write(1, str(round(Data[1],2)))
            blynk.virtual_write(2, str(round(Data[2],1)))
            blynk.virtual_write(3, sysStart)
            blynk.virtual_write(4, alarm)
            
            
            #WidgetLED led1(V4);
            #led1.setValue(alarm * 255)
           # blynk.virtual_read(5, alarm)
        #    blynk.run()
        
        
   # def my_write_handler(value):
    #    global delay
     #   delay = int(value[0])

        while(1):
            blynk.run()
                
        #        time.sleep(10)


def convertToVolt(ADC_Output, Vref=3.3):
    v = ((ADC_Output[1] & int('00000011', 2)) << 8) + ADC_Output[2]
    return (v*Vref)/1024.0


def getHumidty():
    data = [1, humidityByte, 0]
    adc.xfer(data, 10000, 24)
    return convertToVolt(data)


def getLight():
    data = [1, lightByte, 0]
    adc.xfer(data, 10000, 24)
    v = ((data[1] & int('00000011', 2)) << 8) + data[2]
    return (2**10 - 1 - v)


def getTemperature():
    data = [1, tempByte, 0]
    adc.xfer(data, 10000, 24)
    temp = (convertToVolt(data)-V_0)/0.01
    return temp


def getADCData():
    Data[1] = getHumidty()
    Data[3] = getLight()
    Data[2] = getTemperature()
    return



def resetSysTime(channel):
    global sysStart
  
    global alarm

  
    alarm = 0
    GPIO.output(31, alarm)
    sysStart = datetime.datetime.now()

def toggleMonitoring(channel):

  global logging

  if logging:
    logging=False
    print("\nLogging stopped.. ")
  else:
    logging=True
    print("\nLogging started.. ")
   
    
def changeSampleTime(channel):
  
    global delay

    if delay==1:
        delay=2
    elif delay==2:
        delay=5
    elif delay==5:
        delay=1
    print("Sample time is " +str(delay))

def alarmReset(channel):

    global alarm
    global msg
    
    if alarm:
    
        print("\nAlarm Disabled.. ")
        msg = "Alarm Disabled.."
        
        
       
    alarm = 0
    GPIO.output(31, alarm)
        
        #blynk.notify(msg)
    

def main():
    global Vout
   
    print("+----------+-----------+----------+--------+-------+---------+-------+")
    print("| RTC Time | Sys Timer | Humidity |  Temp  | Light | DAC Out | Alarm |")
    print("+==========+===========+==========+========+=======+=========+=======+")
    init()
    getADCData()
    Vout = Data[1]/1023 * Data[3]


def clean():
    if IsGPIO:
        GPIO.cleanup()
    if IsSPI:
        adc.close()
    for thread in threads():
     #   thread.join()
        thread.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as k:
        print("\nExiting gracefully\n")
        clean()
    except Exception as e:
        clean()
        #print("Error: ")
        #print(str(e))
