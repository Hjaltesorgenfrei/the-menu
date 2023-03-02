# Download web page from https://billboard.itu.dk/canteen-menu and extract div with class canteen with beautifulsoup

import requests
from bs4 import BeautifulSoup
import urllib.parse
import cv2
import numpy as np
import pytesseract
import datetime

def get_itu_dishes():
    # Download web page
    base = 'https://billboard.itu.dk/'
    url = base + 'canteen-menu'
    r = requests.get(url)
    r.raise_for_status()

    # Extract div with class canteen
    soup = BeautifulSoup(r.text, 'html.parser')
    canteen = soup.find('div', class_='canteen')

    # Get first image in div
    image = canteen.find('img')

    image_url = urllib.parse.urljoin(base, image['src'])  
    r = requests.get(image_url)
    r.raise_for_status()

    arr = np.asarray(bytearray(r.content), dtype=np.uint8)
    img = cv2.imdecode(arr, -1) # 'Load it as it is'

    # crop image
    week = img[140:200, 170:380]

    start_x = [350, 670, 955, 1240, 1530]
    width = 225
    height = 120
    warm_dish_y = 662
    veggie_dish_y = 788
    warm_dishes = []
    veggie_dishes = []
    for x in start_x:
        cv2.rectangle(img, (x, warm_dish_y), (x+width, warm_dish_y + height), (0, 255, 0), 2)
        # Extract warm dish with ocr from rectangle
        dish = img[warm_dish_y:warm_dish_y + height, x:x+width]
        text = pytesseract.image_to_string(dish, lang='eng')
        warm_dishes.append(text.strip().replace('\n', ' '))
        cv2.rectangle(img, (x, veggie_dish_y), (x+width, veggie_dish_y + height), (0, 255, 0), 2)
        # Extract veggie dish with ocr from rectangle
        dish = img[veggie_dish_y:veggie_dish_y + height, x:x+width]
        veggie_dish = pytesseract.image_to_string(dish, lang='eng')
        veggie_dishes.append(veggie_dish.strip().replace('\n', ' '))
    return [("ITU - Warm Dishes", warm_dishes),("ITU - Warm Veggie", veggie_dishes)]

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
            if content[index] in uge_dage:
                index += 1
                menu.append(" ".join(dish).strip())
                dish = []
                continue
            # add . if not at end of string
            if not content[index].endswith('.'):
                content[index] += '.'
            dish.append(content[index])
            index += 1


        menus.append((title, menu))

    return menus

# This example requires the 'message_content' intent.

import discord
from discord import app_commands
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name = "menu", description = "Get Today's Menus at ITU and KUA", guild=discord.Object(id=576126976251920386)) 
async def menu(interaction):
    await interaction.response.defer()
    dishes = get_itu_dishes() + get_kua_dishes()    
    # Get the dish for the current day of the week
    day = datetime.datetime.today().weekday()
    msg = [u"**Today's Menu** 👨‍🍳"]
    for title, menu in dishes:
        msg.append(f"**{title}**\n{menu[day]}")

    await interaction.followup.send("\n\n".join(msg))

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=576126976251920386))
    print("Ready!")

client.run("token")