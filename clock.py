#!/usr/bin/python
# -*- coding: utf-8 -*-
# This is designed for running on a RPi Zero W
# does not work locally on a Mac

import os
import sys
import datetime, time
import platform
from bs4 import BeautifulSoup
import RPi.GPIO as GPIO
import pygame
import urllib2
import re
import unicodedata

counter = 10  # starting point for the running directional counter
Enc_A = 23    # Encoder input A: input GPIO 23 (active high)
Enc_B = 24    # Encoder input B: input GPIO 24 (active high)
Backlight_pin = 18 # NOTE will be 13 for final version
size = width, height = 320, 240
speed = [2, 2]
black = 0, 0, 0
maincolor = (255,255,255)
supportcolor = (0,192,255)
alarmset = False
alarmtime = [ 7, 30 ]
redraw = False
weatherurl = "http://www.weeronline.nl/Go/WeatherForecastTab/GetFiveDaysForecast?geoAreaId=4058223&activityType=None&temperatureScale=Celsius"
weathervalid = False

tempmin = tempmax = u"0"
wind = u"4nw"
icon1 = icon2 = icon3 = ""

def init():
    global screen
    # IO: encoder and backlight

    # encoder
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(Enc_A, GPIO.IN) # pull-ups are too weak, they introduce noise
    GPIO.setup(Enc_B, GPIO.IN)
    #GPIO.add_event_detect(Enc_A, GPIO.RISING, callback=rotation_decode, bouncetime=2) # bouncetime in mSec

    # backlight
    #GPIO.setup(backlight_pin, GPIO.OUT)
    #backlight = GPIO.PWM(backlight_pin, 100)
    #backlight.start(5)

    # screen and graphics
    os.environ["SDL_FBDEV"] = "/dev/fb1"
    pygame.init()
    screen = pygame.display.set_mode(size)
    pygame.mouse.set_visible(0)

    # sound
    #pygame.mixer.music.load('sounds/sunny.mp3')

    return

# change alarm time set by <delta> minutes
def alarmchange(delta):
    global alarmtime
    global alarmset

    mins = alarmtime[1]
    hours = alarmtime[0]

    mins = mins + delta

    while mins > 60:
        mins = mins - 60
        hours = hours + 1

    while mins < 0:
        mins = mins + 60
        hours = hours - 1

    while hours > 23:
        hours = hours - 1

    if hours < 0:
        alarmset = True
        hours = 0
        mins = 0

    alarmtime = [hours, mins]

def rotation_decode(Enc_A):
    time.sleep(0.002) # debounce

    Switch_A = GPIO.input(Enc_A)
    Switch_B = GPIO.input(Enc_B)

    if (Switch_A == 1) and (Switch_B == 0):
        alarmchange(10)
        while Switch_B == 0:
            Switch_B = GPIO.input(Enc_B)
        while Switch_B == 1:
            Switch_B = GPIO.input(Enc_B)
        return

    elif (Switch_A == 1) and (Switch_B == 1):
        alarmchange(-10)
        while Switch_A == 1:
            Switch_A = GPIO.input(Enc_A)
        return

    else:
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

def getforecast(offset):
    '''read current weather data and fill relevant vars and icons

    @param offset: True if you want tomorrow's data instead of today's
    '''
    global tempmin, tempmax, wind, icon1, icon2, icon3, weathervalid

    print "Fetching weather"
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
    global alarmset, alarmtime, maincolor, supportcolor, screen
    global tempmin, tempmax, wind, icon1, icon2, icon3, weathervalid

    screen.fill(black)

    if alarmset:
        drawtext("07:30", 160, 10, 'CircularPro-Bold.otf', 20, supportcolor)
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

def main():
    global alarmset
    try:
        init()

        lastdraw = 0
        lastdata = 0

        while True :
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    alarmset = not alarmset
                    redraw = True

            # draw @ 5Hz
            if (time.time() - lastdraw > 0.2) or redraw :
                lastdraw = time.time()
                redraw = False
                draw()

            # data update every 5 mins
            if time.time() - lastdata > 30 * 60:
                lastdata = time.time()
                # after 8pm, show tomorrow's time
                getforecast(datetime.datetime.now().hour >= 20)

    except KeyboardInterrupt:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
