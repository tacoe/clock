# clock

## Parts

* Raspberry Pi Zero W
* SD card 8Gb
* Adafruit PiTFT 2.8" TFT 320x240 + Capacitive Touchscreen for Raspberry Pi
* Adafruit Mono 2.5W Class D Audio Amplifier - PAM8302
* Adafruit TSL2591 High Dynamic Range Digital Light Sensor
* Pimoroni pHAT DAC
* Adafruit 16mm Illuminated Pushbutton - White Momentary
* Small metal speaker (8 ohm / 0.5W or similar)
* Rotary Encoder 24-pulse w/ push button
* To setup Pi: micro-USB to female USB-A (for keyboard), mini-HDMI to HDMI (screen)
* To run: 5V micro USB adapter and a a Micro USB cable long enough to go from bedside to wall outlet

## Hardware

* Use extra long stacking headers to mount the pHAT DAC, Raspberry Pi and PiTFT all on top of eachother.
* Ensure a female header stack is on the backside of whichever is at the back, so you can plug in wiring for the pushbutton, rotary encoder, and light sensor
* Wire/solder one of the phat dac's output's channel (either R or L) to the amplifier's Audio In + and -
* Wire/solder a +5V and GND pin from RPi to the amplifier
* Make an nice enclosure (TODO include autocad files)

## Software

* Burn Raspbian Jessie Lite to the SD
* Boot w/keyboard and screen, setup Wifi credentials
* `sudo apt-get update`
* `sudo raspi-config`:
  * (2) set hostname to your liking (eg 'clock')
  * (4) set correct timezone
  * (5) enable SSH (5.2), SPI (5.4), I2C (5.5)
  * (7) expand the filesystem
* reboot and SSH into the pi
* install git and `git clone` this repo
