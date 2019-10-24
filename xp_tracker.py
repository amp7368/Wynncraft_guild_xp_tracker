from datetime import datetime, timedelta
import discord
from json import loads
from json import dumps
from json.decoder import JSONDecodeError
from aiohttp import client_exceptions
import traceback
import urllib.request
import urllib.error
import asyncio
import time


# think of xp like negative indexes of days
#
# guilds = { guild_name:{
#                       "xp":[ {"date":date, "level":level,"xp":xp },
#                               {"date":date, "level":level,"xp":xp },
#                               ..., {"date":date, "level":level,"xp":xp } ],
#                       "channel": channel
#                       }
#           }
def read_xp_chart():
    chart = list()
    with open("xp_chart.txt") as file:
        for line in file:
            line = line.split(" ")[1]
            chart.append(float(line))
    return chart


guilds = dict()
CYCLES_PER_UPDATE = 1
PREFIX = "t!"
client = discord.Client(max_messages=100)
begun = [False]
xp_chart = read_xp_chart()
with open('config.txt') as config:
    p = 0
    for file_line in config:
        file_line = file_line.split("#")[0].strip()
        if p == 0:
            BOT_ID = file_line
        elif p == 1:
            LOGIN = file_line
        elif p == 2:
            file_line = file_line.split(",")
            COLOR = discord.colour.Color.from_rgb(int(file_line[0]), int(file_line[1]), int(file_line[2]))
        elif p == 3:
            DEBUG_PERSON = int(file_line)
        elif p == 4:
            BEGIN_CHANNEL = int(file_line)
        else:
            break
        p += 1


@client.event
async def on_ready():
    await client.get_channel(BEGIN_CHANNEL).send("t!begin")


@client.event
async def on_message(message):
    '''
    on any message in my discord servers,
    see if a command was said and execute the corresponding command
    :param message:
    :return:
    '''
    if not message.content.startswith(PREFIX):
        return

    content = message.content[len(PREFIX):].split(" ")[0]

    if content == "begin" and str(message.author.id) == BOT_ID and not begun[0]:
        await begin()
    if content == "end" and str(message.author.id) == DEBUG_PERSON:
        await end(message)

    if message.author.bot:
        return

    if content in commands_set:
        await commands_set[content](message)


def write():
    string = dumps(guilds)
    with open("data.txt", 'w') as file:
        file.write(string)


def read():
    with open("data.txt") as file:
        string = file.readline()
    if string == '\n':
        return
    loaded = loads(string)
    for element in loaded:
        guilds[element] = loaded[element]


async def begin():
    await client.get_channel(BEGIN_CHANNEL).send("begun")
    read()
    begun[0] = True
    while True:
        start = time.time()
        for guild_name in guilds:
            guilds[guild_name]["time"] += 1
            if guilds[guild_name]["time"] == CYCLES_PER_UPDATE:
                guilds[guild_name]["time"] = 0
                guild_data = await fetch_data(guild_name)

                current_date = time.time()
                current_level = guild_data['level']
                current_xp = guild_data['xp']

                past = guilds[guild_name]['xp'][-1]
                past_date = past['date']
                past_level = past['level']
                past_xp = past['xp']

                guilds[guild_name]["xp"].append({"date": current_date, "level": current_level, "xp": current_xp})

                await client.get_channel(guilds[guild_name]["channel"]).send(
                    get_xp_earned(past_date, past_level, past_xp, current_date, current_level, current_xp))
        await asyncio.sleep(60 - (time.time() - start))


def get_xp_earned(past_date, past_level, past_xp, current_date, current_level, current_xp):
    if past_level > current_level:
        return "Past level is greater than current level? O.o"
    xp_earned = 0
    while past_level != current_level:
        if past_level - 1 >= len(xp_chart):
            return "msg appleptr16#5054 \"add level " + str(past_level) + " to the xp chart\""
        xp_earned += xp_chart[past_level - 1] * (1 - past_xp / 100)
        past_level += 1
        past_xp = 0
    xp_earned += ((current_xp - past_xp) / 100) * xp_chart[current_level]
    return "xp earned in " + str(
        (datetime.fromtimestamp(int(current_date)) - datetime.fromtimestamp(int(past_date))).total_seconds() / (
                60 * 60)) + " days = " + str(xp_earned)


async def end(message):
    pass


async def fetch_data(guild_name):
    try_number = 0
    while try_number < 5:
        try:
            guild_data = loads(urllib.request.urlopen(
                "https://api.wynncraft.com/public_api.php?action=guildStats&command=" + guild_name).readline().decode(
                "utf-8"))
            return guild_data
        except:
            await asyncio.sleep(10)
        try_number += 1
    raise Exception("FetchDataFailure")


async def create(message):
    guild_name = " ".join(message.content.split(" ")[1:])
    if guild_name in guilds:
        await message.channel.send("\"" + guild_name + "\" already exists in my records")
        return
    try:
        guild_data = await fetch_data(guild_name)
    except:
        await message.channel.send("Failed to get data for: \"" + guild_name + "\"")
        return
    guilds[guild_name] = {"xp": [{"date": time.time(), "level": guild_data["level"], "xp": guild_data["xp"]}],
                          "channel": message.channel.id,
                          "time": 0}
    write()
    await message.channel.send(guild_name + " created")


def client_runner():
    '''
    start the bot
    :return: never
    '''
    while True:
        try:
            client.run(LOGIN)
            print("Wow")
        except:
            traceback.print_exc()
        asyncio.sleep(5)


commands_set = {"create": create}
if __name__ == "__main__":
    while True:
        try:
            client_runner()
        except:
            pass
