#!/usr/bin/python
# -*- coding: utf-8 -*-
# This is designed for running on a RPi Zero W
# does not work locally on a Mac

import os, sys, datetime, time, platform, threading
import pygame, urllib2, re, random, tls2591
from bs4 import BeautifulSoup
from signal import alarm, signal, SIGALRM, SIGKILL
import RPi.GPIO as GPIO

# GPIO layout
Enc_A = 0
Enc_B = 1
Enc_PUSH = 16
backlight_pin = 13
Snz_LED = 5
Snz_PUSH = 6

# screen setup
size = width, height = 320, 240

# colors
black = (0, 0, 0)
maincolor = (255,255,255)
supportcolor = (0,192,255)
alarmbackground = (255,255,255)

# app state
alarmset = True
alarmtime = [ 7, 30 ]
alarmstate = False
redraw = False

# weather
weatherurl = "http://www.weeronline.nl/Go/WeatherForecastTab/GetFiveDaysForecast?geoAreaId=4058223&activityType=None&temperatureScale=Celsius"
weathervalid = False
tsl = 0
tempmin = tempmax = u"0"
wind = u"4nw"
icon1 = icon2 = icon3 = ""

def init():
    global screen, tsl, size, backlight_pin, Enc_A, Enc_B, Enc_PUSH, Snz_LED, Snz_PUSH

    # backlight: set PWM pin mode
    os.system('gpio -g mode ' + str(backlight_pin) + ' pwm')

    # initialize light meter and thread
    tsl = tls2591.Tsl2591()

    # alarm time encoder
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(Enc_A, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(Enc_B, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(Enc_PUSH, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(Enc_A, GPIO.RISING, callback=rotation_decode, bouncetime=2) # bouncetime in mSec
    GPIO.add_event_detect(Enc_PUSH, GPIO.RISING, callback=rotation_push, bouncetime=10) # bouncetime in mSec

    # snooze pushbutton
    GPIO.setup(Snz_LED, GPIO.OUT)
    GPIO.output(Snz_LED, False)
    GPIO.setup(Snz_PUSH, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.add_event_detect(Snz_PUSH, GPIO.RISING, callback=snooze_push, bouncetime=10) # bouncetime in mSec

    # screen and graphics, including a hack to prevent
    # pygame from hanging on 2nd+ run
    os.environ["SDL_FBDEV"] = "/dev/fb1"
    class Alarm(Exception):
        pass
    def alarm_handler(signum, frame):
        raise Alarm
    signal(SIGALRM, alarm_handler)
    alarm(3)
    try:
        pygame.init()
        screen = pygame.display.set_mode(size)
        alarm(0)
    except Alarm:
        raise KeyboardInterrupt

    pygame.mouse.set_visible(0)

    # sound
    pygame.mixer.music.load('sounds/sunny.mp3')
    pygame.mixer.music.set_volume(0.2)  # be kind to our little 0.5W speaker

    return

def alarmchange(delta):
    '''change alarm time up or down

    @delta is number of minutes up (positive) or down (negative)
    assumes < increments of less than 60 minutes.
    '''

    global alarmtime, redraw

    mins = alarmtime[1]
    hours = alarmtime[0]

    mins = mins + delta

    while mins >= 60:
        mins = mins - 60
        hours = hours + 1

    while mins < 0:
        mins = mins + 60
        hours = hours - 1

    if hours > 23:
        hours = 23
        minutes = 60 - delta

    if hours < 0:
        hours = 0
        minutes = 0

    alarmtime = [hours, mins]
    redraw = True

def rotation_decode(v):
    '''this function is called on button rotation interrupt
    and changes the alarm clock time by 10 minute increments.'''

    time.sleep(0.002) # debounce

    Switch_A = GPIO.input(Enc_A)
    Switch_B = GPIO.input(Enc_B)

    if (Switch_A == 1) and (Switch_B == 0):
        alarmchange(5)
        while Switch_B == 0:
            Switch_B = GPIO.input(Enc_B)
        while Switch_B == 1:
            Switch_B = GPIO.input(Enc_B)
        return

    elif (Switch_A == 1) and (Switch_B == 1):
        alarmchange(-5)
        while Switch_A == 1:
            Switch_A = GPIO.input(Enc_A)
        return

    else:
        return

def rotation_push(v):
    '''this function is called on rotate button push interrupt'''
    global alarmset, redraw
    time.sleep(0.01) # debounce
    Switch = GPIO.input(Enc_PUSH)
    if Switch == 1:
        alarmset = not alarmset
        redraw = True
    return

def snooze_push(v):
    '''this function is called on snooze button push interrupt'''
    global alarmset, redraw
    time.sleep(0.01) # debounce
    Switch = GPIO.input(Snz_PUSH)
    if Switch == 1:
        disablealarm()
    return

def drawtext(caption, x, y, fontfile = 'CircularPro-Book.otf', size = 30, color = (200,200,200)):
    global screen
    font = pygame.font.Font("fonts/" + fontfile, size)
    rendered_text = font.render(caption, True, color)
    rendered_size = font.size(caption)
    screen.blit(rendered_text, (x-rendered_size[0]/2, y))

def drawicon(icon, x, y, size = 30, color = (200,200,200)):
    global screen
    font = pygame.font.Font('fontawesome-webfont.ttf', size)
    rendered_text = font.render(icon, True, color)
    screen.blit(rendered_text, (x, y))

def bs_preprocess(html):
    '''remove distracting whitespaces and newline characters'''
    pat = re.compile('(^[\s]+)|([\s]+$)', re.MULTILINE)
    html = re.sub(pat, '', html)       # remove leading and trailing whitespaces
    html = re.sub('\n', ' ', html)     # convert newlines to spaces
                                       # this preserves newline delimiters
    html = re.sub('[\s]+<', '<', html) # remove whitespaces before opening tags
    html = re.sub('>[\s]+', '>', html) # remove whitespaces after closing tags
    return html

def setbrightness():
    '''sets display brightness from 8 (near-absolute darkness)
    to 1023 (sunny)'''
    global tsl, alarmstate

    if alarmstate == True:
        dc = 1023
    else:
        full, ir = tsl.get_full_luminosity()
        lux = tsl.calculate_lux(full, ir)
        dc = lux * 5

    if dc > 1023: dc = 1023
    if dc < 8: dc = 8
    os.system('gpio -g pwm ' + str(backlight_pin) + ' ' + str(dc))

def getforecast(offset):
    '''read current weather data and fill relevant vars and icons

    @param offset: True if you want tomorrow's data instead of today's
    '''
    global tempmin, tempmax, wind, icon1, icon2, icon3, weathervalid

    #print "Fetching weather"
    response = urllib2.urlopen(weatherurl)
    data = bs_preprocess(response.read())
    soup = BeautifulSoup(data, 'html.parser')
    r = soup.find("tr", class_="row_forecast")
    try:
        sr = r.td.next_sibling
        if offset: sr = sr.next_sibling
        tempmin = sr.string.strip()[:-1]

        sr = r.next_sibling.td.next_sibling
        if offset: sr = sr.next_sibling
        tempmax = sr.string.strip()[:-1]
    except:
        print "error getting temp data"
        tempmin = tempmax = "err"

    r = soup.find("tr", class_="row_weathericons")
    try:
        sr = r.td.next_sibling
        if offset: sr = sr.next_sibling

        icon1_name = sr.find("span", class_="morning").div.attrs['class'][0].strip()[10:][:-2]
        icon2_name = sr.find("span", class_="midday").div.attrs['class'][0].strip()[10:][:-2]
        icon3_name = sr.find("span", class_="evening").div.attrs['class'][0].strip()[10:][:-2]

        icon1 = pygame.image.load("icons/" + icon1_name + ".png").convert_alpha()
        icon2 = pygame.image.load("icons/" + icon2_name + ".png").convert_alpha()
        icon3 = pygame.image.load("icons/" + icon3_name + ".png").convert_alpha()
    except:
        print "error getting or loading weather icons: ", sys.exc_info()[0]
        icon1 = icon2 = icon3 = "err"

    r = soup.find("tr", class_="row_forecast")
    try:
        sr = r.next_sibling.next_sibling.td.next_sibling
        if offset: sr = sr.next_sibling

        wind = sr.attrs['title'].strip()[11:].replace(' Bft,','').lower()
    except:
        print "error getting wind info: ", sys.exc_info()[0]
        wind = "err"

    weathervalid = True
    return

def draw():
    global alarmset, alarmtime, maincolor, supportcolor, screen, black
    global alarmstate, alarmbackground
    global tempmin, tempmax, wind, icon1, icon2, icon3, weathervalid

    if alarmstate == True:
        screen.fill(alarmbackground)
        drawtext(time.strftime("%H:%M", time.localtime()), 160, 40, 'CircularPro-Book.otf',120, black)
    else:
        screen.fill(black)

        if alarmset:
            drawtext('{0:02d}'.format(alarmtime[0]) + ':' + '{0:02d}'.format(alarmtime[1]), 160, 10, 'CircularPro-Bold.otf', 20, supportcolor)
        else:
            drawtext(u"", 160, 10, 'FontAwesome.otf', 18, supportcolor)

        drawtext(time.strftime("%H:%M", time.localtime()), 160, 40, 'CircularPro-Book.otf',80, maincolor)

        if(weathervalid):
            drawtext(tempmin + u"º", 105, 205, 'CircularPro-Bold.otf', 20, maincolor)
            drawtext(tempmax + u"º", 160, 205, 'CircularPro-Bold.otf', 20, maincolor)
            drawtext(wind, 215, 209, 'CircularPro-Bold.otf', 16, maincolor)

            screen.blit(icon1, (85, 170))
            screen.blit(icon2, (140, 170))
            screen.blit(icon3, (195, 170))

    pygame.display.flip()

def setalarmstate(state):
    global alarmstate
    alarmstate = state
    '''Enables or disables the actual alarm (light, sound)'''
    if(state == True):
        pygame.mixer.music.play(10)
        GPIO.output(Snz_LED, True)
        t = threading.Timer(5 * 60.0, disablealarm)
        t.start()
    else:
        pygame.mixer.music.stop()
        GPIO.output(Snz_LED, False)
    setbrightness()

def disablealarm():
    '''disable alarm. note: should be callable repeatedly without disrupting state'''
    setalarmstate(False)

def main():
    global alarmset, alarmtime, redraw
    try:
        init()

        last_min = -1
        lastdraw = 0
        lastdata = 0
        lastbri = 0

        while True :
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    redraw = True
                    setalarmstate(True)

            # check for alarm, once per minute, on minute edges only
            cur_min = datetime.datetime.now().minute
            if cur_min != last_min:
                last_min = cur_min
                if alarmset and datetime.datetime.now().hour == alarmtime[0] and cur_min == alarmtime[1]:
                    setalarmstate(True)

            # draw @ 5Hz
            if (time.time() - lastdraw > 0.2) or redraw :
                lastdraw = time.time()
                redraw = False
                draw()

            # update brightness every 20 seconds
            if time.time() - lastbri > 20:
                lastbri = time.time()
                setbrightness()

            # data update every 5 mins
            if time.time() - lastdata > 30 * 60:
                lastdata = time.time()
                # after 8pm, show tomorrow's time
                getforecast(datetime.datetime.now().hour >= 20)

    except KeyboardInterrupt:
        GPIO.remove_event_detect(Enc_A)
        GPIO.cleanup()
        pygame.quit()

if __name__ == '__main__':
    main()
