import os
import time
import base64
import re
import sys
import threading
import queue
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from luma.core.virtual import viewport
from PIL import ImageFont


""" This script runs two threads and one main loop. 
The first thread prints two predefined global variables to the OLED display and will scroll the text along the display
The second thread constantly queries the shairport-sync-metadata FIFO file for song and artist information, adding it to
 a queue
The main loop periodically gets the music status (playing, mpd output or airplay output) and redfines the global 
variables that are to be printed on the OLED. As soon as a change is detected, (like going from sleep to airplay) the 
OLED will finish scrolling the previous text across the screen and then change to the updated information"""

# TODO speed up transition between audio types
# TODO future; get song info from radio station m3u8 file/ connection

shairport_metadata = os.path.abspath('/tmp/shairport-sync-metadata')
currentsong = os.path.abspath('/var/local/www/currentsong.txt')
song_info = {}

# OLED stuff:
serial = i2c(port=1, address=0x3C)
device = sh1106(serial, rotate=2)
fontsize = 24
font_century = ImageFont.truetype('/opt/moOde_OLED/fonts/century_gothic.ttf', fontsize)
global first_line
first_line = 'moOde'
global second_line
second_line = "Loading..."
global starttime
starttime = time.time()
dw = device.width
dh = device.height
time_to_sleep = 0.3


def print_to_OLED(font=font_century, speed=4):
    while True:
        # First measure the text size
        with canvas(device) as draw:
            w_first_line, h_first_line = draw.textsize(first_line, font)
            w_second_line, h_second_line = draw.textsize(second_line, font)

        virtual = viewport(device, width=dw+dw+max(w_first_line,w_second_line), height=dh)
        with canvas(virtual) as draw:
            draw.text((0, 0), first_line, font=font, fill="white")
            draw.text((0, dh/2), second_line, font=font, fill="white")

        i = 0
        while i < dw + max(h_first_line, h_second_line):  # scroll for an entire width, plus a bit (h)
            # hold position for 2 seconds
            if i == 0:
                time.sleep(2)
            virtual.set_position((i, 0))
            i += speed
            time.sleep(0.025)  # or use sleep(0.5) and speed 8

def replace_item_in_queue(dictionary_key, data):
    try:
        base64_bytes = data.encode('ascii')
        message_bytes = base64.b64decode(base64_bytes)
        message = message_bytes.decode('utf-8')
        dictionary = airplay_queue.get()
        dictionary[dictionary_key] = message
        airplay_queue.put(dictionary)
    except Exception as e:
        print(e)

def get_shairport_data():
    while True:
        try:
            time.sleep(time_to_sleep - ((time.time() - starttime) % time_to_sleep))
            xml_string = ''  # start with an empty string
            with open(shairport_metadata, 'r') as fifo:
                for line in fifo:
                    # reset xml_string back to an empty string whenever a new line (<item>) comes along
                    if '<item>' in line:
                        xml_string = ''
                    # add the 'line' into the string, remove any newline characters
                    xml_string += line.rstrip()
                    # once the full <data>...</data> XML has been recorded for one item, decode the lot
                    if '</data>' in xml_string:
                        # put 'code' XML into the song_info dictionary
                        code_matches = re.findall('<code>([0-9a-zA-Z]*)', xml_string)
                        for match in code_matches:
                            bytes_object = bytes.fromhex(match)
                            ascii_string = bytes_object.decode('ascii')
                            song_info['code'] = ascii_string
                            if any(code in ascii_string for code in ['minm', 'asar', 'ascp', 'asaa', 'assl']):
                                # put 'data' XML into the song_info dictionary
                                data_matches = re.findall('<data encoding="base64">([0-9a-zA-Z=]*)', xml_string)
                                for match in data_matches:
                                    try:
                                        if song_info['code'] == 'minm':  # dmap.itemname
                                            replace_item_in_queue('song', match)
                                        if song_info['code'] == 'asar':  # daap.songartist
                                            replace_item_in_queue('artist', match)
                                        # 'asal' is album (daap.songalbum)
                                        # 'asar' is artist (daap.songartist)
                                        # 'ascp' is composer (daap.songcomposer)
                                    except Exception:
                                        break
        except Exception as e:
            print(e)
        except KeyboardInterrupt:
            sys.exit(0)

def get_mpd_data():
    with open(currentsong, 'r') as f:
        currentsong_status = [line for line in f.readlines()]
    if any('title=' in x for x in currentsong_status):
        title = currentsong_status[3].strip('title=').rstrip()
    if any('artist=' in x for x in currentsong_status):
        artist = currentsong_status[1].strip('artist=').rstrip()
    return artist, title

def get_audio_status():
    with open(currentsong, 'r') as f:
        currentsong_status = [line for line in f.readlines()]
        if any('outrate=0 bps' in x for x in currentsong_status):
            music_status = 'sleeping'
        elif any('file=Airplay Active' in x for x in currentsong_status):
            music_status = 'airplay'
        else:
            music_status = 'mpd'
        return music_status

def get_first_item_in_queue(queue):
    item_to_print = queue.queue[0]
    return item_to_print['artist'], item_to_print['song']


airplay_queue = queue.Queue()
# add first entry, so it is obvious the OLED is working, but still loading the song info
airplay_queue.put({'artist':'moOde', 'song':second_line})

print_thread = threading.Thread(target=print_to_OLED, args=())
print_thread.start()
get_shairport_data_thread = threading.Thread(target=get_shairport_data, args=())
get_shairport_data_thread.start()

while True:
    try:
        time.sleep(time_to_sleep - ((time.time() - starttime) % time_to_sleep))
        music_status = get_audio_status()
        if music_status == 'sleeping':
            first_line = 'moOde'
            second_line = 'sleeping...'
        if music_status == 'airplay':
            first_line, second_line = get_first_item_in_queue(airplay_queue)
        if music_status == 'mpd':
            first_line, second_line = get_mpd_data()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(e)
