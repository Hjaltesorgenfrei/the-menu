# Download web page from https://billboard.itu.dk/canteen-menu and extract div with class canteen with beautifulsoup

import requests
from bs4 import BeautifulSoup
import urllib.parse
import cv2
import numpy as np
import pytesseract
import datetime
import sys
import os
import re
import io
from dotenv import load_dotenv

load_dotenv()

testing = False

if len(sys.argv) > 1 and sys.argv[1] == '-test':
    testing = True

def get_itu_dishes():
    urls = ['https://billboard.itu.dk/canteen-menu', 'https://itustudent.itu.dk/Campus-Life/Student-Life/Canteen-Menu']
    for url in urls:
        image_urls = []
        try:
            # Download web page
            r = requests.get(url)
            r.raise_for_status()

            # Extract div with class canteen
            soup = BeautifulSoup(r.text, 'html.parser')
            canteen = soup.find('div', class_='canteen')
            if canteen is None:
                canteen = soup.find('div', id='Canteenmenu')
            if canteen is None:
                continue

            # Get first image in div
            for image in canteen.find_all('img'):
                base = url[:url.rfind('/') + 1]
                image_url = urllib.parse.urljoin(base, image['src'])  
                # If contains Infoscreen, then it is the image we want
                if 'infoscreen' in image_url.lower():
                    image_urls.append(image_url)

            if testing:
                print(image_urls)

            for image_url in image_urls:
                r = requests.get(image_url)
                r.raise_for_status()
                arr = np.asarray(bytearray(r.content), dtype=np.uint8)
                img = cv2.imdecode(arr, -1) # 'Load it as it is'

                # Get the image to a string using pytesseract
                text = pytesseract.image_to_string(img, lang='eng').lower()

                # Get the week number from the text string
                regex = r'week\s*(\d+)' # Week followed by one or more digits
                week_number = re.search(regex, text).group(1)

                # remover everything that is not numbers
                week_number = ''.join([x for x in week_number if x.isdigit()])
                if testing:
                    print(week_number)

                # Check if week number is the same as the current week number
                if int(week_number) != datetime.datetime.today().isocalendar()[1]:
                    continue

                # Get all words in the image and their location
                d = pytesseract.image_to_data(img, lang='eng', output_type=pytesseract.Output.DICT)
                # remove everything that is not characters
                d['text'] = [''.join([x for x in word if x.isalpha() or x == ' ']) for word in d['text']]
                n_boxes = len(d['level'])
                cordinates = {}
                for i in range(n_boxes):
                    (x, y, w, h, word) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i], d['text'][i])
                    if word not in cordinates:
                        cordinates[word.lower()] = (x, y, w, h)

                week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
                dishes = []
                for i in range(len(week_days)):
                    day = week_days[i]
                    if day not in cordinates:
                        continue
                    (x, y, w, h) = cordinates[day]
                    # Expand w and h to the next day
                    if i < len(week_days) - 1:
                        (x2, y2, w2, h2) = cordinates[week_days[i + 1]]
                        w = x2 - x
                    else:
                        # Expand to the bottom right corner
                        w = img.shape[1] - x

                    # Make a box underneath the day to the bottom of the image
                    left, top, right, bottom = x - 10, y + h + 2, x + w - 2, img.shape[0] - 200
                    if testing:
                        cv2.rectangle(img, (left, top), (right, bottom), (0, 255, 0), 2)

                    crop_img = img[top:bottom, left:right]
                    # return the image bytes
                    buffer = cv2.imencode('.jpg', crop_img)[1]
                    dishes.append(buffer)

                return [("ITU", dishes)]
        except Exception as e:
            print(e)
            # print stack trace
            import traceback
            traceback.print_exc()
            continue
    return [("ITU", [] * 5)]

def get_kua_dishes():
    # Download web page
    url = "https://www.foodandco.dk/besog-os-her/restauranter/ku/sondre-campus/"
    r = requests.get(url)
    r.raise_for_status()

    # extract divs with class ContentBlock
    soup = BeautifulSoup(r.text, 'html.parser')
    content_blocks = soup.find_all('div', class_='ContentBlock')

    # print content_blocks
    menus = []

    uge_dage = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag']
    lower_case_uge_dage = [x.lower() for x in uge_dage]

    for block in content_blocks:
        content = block.text.replace(u'\xa0', u' ').strip().split('\n')
        content = [x.strip() for x in content if x.strip() != '' or "forbehold for ændringer" in x.lower()]
        if len(content) < 5:
            continue
        title = content[0]
        if title.lower().startswith('wicked'):
            title += ' ' + content[1]
        if title.lower().startswith('folke'):
            title = "FOLKEKØKKEN"
        
        index = content.index(uge_dage[0]) + 1
        menu = []
        dish = []
        while index < len(content):
            if content[index].lower() in lower_case_uge_dage:
                index += 1
                menu.append(" ".join(dish).strip())
                dish = []
                continue
            # add . if not at end of string
            if not content[index].endswith('.'):
                content[index] += '.'
            dish.append(content[index])
            index += 1
        menu.append(" ".join(dish).strip())

        menus.append((title, menu))

    return menus

# Check if cli arg was -test
if testing:
    for menu, dishes in get_itu_dishes():
        break
        print(menu)
        for dish in dishes:
            print(dish)
    for menu, dishes in get_kua_dishes():
        print(menu, len(dishes))
        for dish in dishes:
            print(dish)
    exit()

# This example requires the 'message_content' intent.

import discord
from discord import app_commands
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name = "map", description = "Show map of KUA") 
async def get_map(interaction):
    await interaction.response.send_message("https://cdn.discordapp.com/attachments/1069320174118907934/1075711990493880390/kort_kua_kantinelokationer_25-08-22.png")

import typing

@tree.command(name = "menu", description = "Get Today's Menus at ITU and KUA") 
@app_commands.describe(day="The day of the week to get the menu for. Rangei is 0-4, where 0 is Monday and 4 is Friday.")
# day is an optional argument int 
async def get_menu(interaction, day: typing.Optional[int]):
    # defer the response
    await interaction.response.defer()
    # check if week and day is in cache
    week = datetime.datetime.today().isocalendar()[1]
    if day is None:
        day = datetime.datetime.today().weekday()
        if datetime.datetime.now().hour >= 14:
            day += 1
    day = max(0, min(day, 4))
    dishes = get_kua_dishes()
    
    #if it is after 14:00, get the menu for the next day

    today = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][day]
    msg = [f"**{today}" + u"'s Menu** 👨‍🍳"]
    for title, menu in dishes:
        if len(menu) > day:
            msg.append(f"**{title}**\n{menu[day]}")

    # Get the dishes from ITU's billboard
    image_dishes = get_itu_dishes()

    for title, menu in image_dishes:
        if len(menu) > day and len(menu[day]) > 10:
            msg.append(f"**{title}**")
            # send the image dish for the current day of the week as an attachment
            response = "\n\n".join(msg)
            arr = io.BytesIO(menu[day])
            file = discord.File(arr, filename=f"menu.jpg")
            await interaction.followup.send(response, file=file)

# Make a command that takes all images in the message and sends them to the mads monster memes channel
@tree.command(name = "submit", description = "Submit images to mads monster memes") 
async def submit_memes(interaction, image: discord.Attachment):
    await interaction.response.defer()
    
    url = image.url
    
    # Download the image
    r = requests.get(url)
    r.raise_for_status()
    # Save the image
    imageName = image.filename

    content = r.content
    data = {'visualFile': (imageName, content, image.content_type) }
    body = {'toptext': "", 'bottomtext':""}
    request = requests.Request('POST',"https://api.mads.monster/Upload/Memes", files= data, data=body ).prepare()
    s = requests.Session()
    response = s.send(request)
    if response.status_code != 200:
        await interaction.followup.send("Something went wrong when uploading the image")
        return
    
    await interaction.followup.send("Images uploaded successfully: " + url)

@client.event
async def on_ready():
    await tree.sync()
    print("Ready!")

client.run(os.getenv("KANTINE_TOKEN"))