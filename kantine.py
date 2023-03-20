# Download web page from https://billboard.itu.dk/canteen-menu and extract div with class canteen with beautifulsoup

import requests
from bs4 import BeautifulSoup
import urllib.parse
import cv2
import numpy as np
import pytesseract
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

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


            for image_url in image_urls:
                r = requests.get(image_url)
                r.raise_for_status()
                arr = np.asarray(bytearray(r.content), dtype=np.uint8)
                img = cv2.imdecode(arr, -1) # 'Load it as it is'

                # crop image
                week = img[140:200, 170:380]
                week_number = pytesseract.image_to_string(week, lang='eng')
                # remover everything that is not numbers
                week_number = ''.join([x for x in week_number if x.isdigit()])

                # Check if week number is the same as the current week number
                if int(week_number) != datetime.datetime.today().isocalendar()[1]:
                    continue
                
                start_x = [330, 650, 935, 1220, 1510]
                width = 245
                height = 140
                warm_dish_y = 662
                veggie_dish_y = 810
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
        except Exception as e:
            print(e)
    return [("ITU", ["No menu available, failed in retrieving image from ITU's billboard"] * 5)]

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
        menu.append(" ".join(dish).strip())

        menus.append((title, menu))

    return menus



# This example requires the 'message_content' intent.

import discord
from discord import app_commands
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name = "map", description = "Show map of KUA", guild=discord.Object(id=576126976251920386)) 
async def get_map(interaction):
    await interaction.response.send_message("https://cdn.discordapp.com/attachments/1069320174118907934/1075711990493880390/kort_kua_kantinelokationer_25-08-22.png")

@tree.command(name = "menu", description = "Get Today's Menus at ITU and KUA", guild=discord.Object(id=576126976251920386)) 
async def get_menu(interaction):
    # defer the response
    await interaction.response.defer()
    dishes = get_itu_dishes() + get_kua_dishes()    
    # Get the dish for the current day of the week
    day = datetime.datetime.today().weekday()
    
    #if it is after 14:00, get the menu for the next day
    if datetime.datetime.now().hour >= 14:
        day += 1
        if day > 4:
            day = 0

    msg = [u"**Today's Menu** 👨‍🍳"]
    for title, menu in dishes:
        msg.append(f"**{title}**\n{menu[day]}")

    print(msg)
    
    await interaction.followup.send("\n\n".join(msg))

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=576126976251920386))
    print("Ready!")

client.run(os.getenv("KANTINE_TOKEN"))