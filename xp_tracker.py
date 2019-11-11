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
#                       "xp":[
# filled with               {"type":"level", "date":date, "level":level, "xp":xp },
# 2 types                   {"type":"leader", "date":date, "level":level, "xp":total_xp_earned },
#                           ..., {"type":"level", "date":date, "level":level,"xp":xp } ],
#                       "time": time
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


leaderboard_cache = ['abc']
guilds = dict()
MINUTES_PER_UPDATE = 60 * 1  # update every 3 hours
SECONDS_PER_DAY = 60 * 60 * 24
PREFIX = "c!"
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
    try:
        await client.get_channel(BEGIN_CHANNEL).send("c!begin")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


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


async def on_command_info(message):
    try:
        await message.channel.send(embed=discord.Embed(color=COLOR, description="Bot invite: https://bit.ly/36ExueR"))
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def on_command_help(message):
    try:
        await message.channel.send(embed=discord.Embed(color=COLOR, description=
        "**" + PREFIX + "track <guild_name>**  - starts tracking guild xp for guild_name\n" +
        "**" + PREFIX + "xp x <guild_name>** - lists the xp earned for guild_name each day, total xp earned, and mean xp earned for the last x days\n" +
        "**" + PREFIX + "xp x y <guild_name>** - lists the xp earned for guild_name each day, total xp earned, and mean xp earned from x days ago to y days ago\n" +
        "**" + PREFIX + "xph zh x y <guild_name>** - lists the xp earned for guild_name each day, total xp earned, and mean xp earned from x days ago to y days ago in an interval of z hours\n"))
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def on_command_xp(message):
    msgs = message.content.split(" ")
    if len(msgs) < 3:
        await correct_command_xp(message.channel)
        return
    if msgs[1].isdigit():
        if msgs[2].isdigit():
            # from date to date
            if len(msgs) < 4:
                await correct_command_xp(message.channel)
                return
            guild_name = " ".join(msgs[3:])
            if guild_name not in guilds:
                await not_tracking(message.channel, guild_name)
                return
            day1 = int(msgs[1])  # day1 came first in time
            day2 = int(msgs[2])
        else:
            # from date to now
            if len(msgs) < 3:
                await correct_command_xp(message.channel)
                return
            guild_name = " ".join(msgs[2:])
            if guild_name not in guilds:
                await not_tracking(message.channel, guild_name)
                return
            day1 = int(msgs[1])  # day1 came first in time
            day2 = 0

        if day1 < day2:
            # make day1 > day2
            temp = day1
            day1 = day2
            day2 = temp
        elif day1 == day2:
            await correct_command_xp(message.channel)
            return
        await xp(message, guild_name, day1, day2, SECONDS_PER_DAY)

    else:
        await correct_command_xp(message.channel)
        return


async def on_command_xp_hourly(message):
    msgs = message.content.split(" ")
    if len(msgs) < 4:
        await correct_command_xp_hourly(message.channel)
        return
    hours = msgs[1]
    if hours[-1] != 'h':
        await correct_command_xp_hourly(message.channel)
        return
    hours = hours[:-1]
    if hours.isdigit():
        hours = int(hours)
        if hours == 0:
            await correct_command_xp_hourly(message.channel)
            return
    else:
        await correct_command_xp_hourly(message.channel)
        return
    if msgs[2].isdigit():
        if msgs[3].isdigit():
            # from date to date
            if len(msgs) < 5:
                await correct_command_xp_hourly(message.channel)
                return
            guild_name = " ".join(msgs[4:])
            if guild_name not in guilds:
                await not_tracking(message.channel, guild_name)
                return
            day1 = int(msgs[3])  # day1 came first in time
            day2 = int(msgs[2])
        else:
            # from date to now
            if len(msgs) < 4:
                await correct_command_xp_hourly(message.channel)
                return
            guild_name = " ".join(msgs[3:])
            if guild_name not in guilds:
                await not_tracking(message.channel, guild_name)
                return
            day1 = int(msgs[2])  # day1 came first in time
            day2 = 0

        if day1 < day2:
            # make day1 > day2
            temp = day1
            day1 = day2
            day2 = temp
        elif day1 == day2:
            await correct_command_xp_hourly(message.channel)
            return
        await xp(message, guild_name, day1, day2, hours * 3600)
    else:
        await correct_command_xp(message.channel)
        return


async def xp(message, guild_name, day1, day2, step):
    date2 = time.time() - (day2 * SECONDS_PER_DAY)
    # find the closest update to date2
    date2 = find_closest(guild_name, date2)
    if date2 == -1:
        await failed_message(message.channel)
        return
    date1 = find_closest(guild_name, int(guilds[guild_name]['xp'][date2]['date']) - ((day1 - day2) * SECONDS_PER_DAY))
    # total xp earned from date1 to date2
    total_xp_earned = get_xp_earned(guilds[guild_name]['xp'][date1], guilds[guild_name]['xp'][date2])
    total_raw_xp_earned = get_raw_xp_earned(guilds[guild_name]['xp'][date1], guilds[guild_name]['xp'][date2])
    middle_xp = list()
    date_last = date2
    days_difference = (datetime.fromtimestamp(
        guilds[guild_name]['xp'][date2]['date']) - datetime.fromtimestamp(
        guilds[guild_name]['xp'][date1]['date'])).total_seconds() / SECONDS_PER_DAY
    now_now = time.time()
    if (day1 - day2) * SECONDS_PER_DAY / step > 90:
        string = "Total " + str(total_xp_earned) + "\nAverage Earned XP From " + str(
            "{:.1f}".format(date1)) + " D Ago to " + str(
            "{:.1f}".format(date2)) + " D Ago = " + "{:,d}".format(int(total_raw_xp_earned / days_difference))
        try:
            await message.channel.send("```ml\n" + string + "```")
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        return

    for i in reversed(range(int(guilds[guild_name]['xp'][date2]['date']) - ((day1 - day2) * SECONDS_PER_DAY),
                            int(guilds[guild_name]['xp'][date2]['date']),
                            step)):
        # big i to small i
        date_now = find_closest(guild_name, i)
        if date_now == -1 or date_last == -1:
            middle_xp.append("???")
        else:
            middle_xp.append(get_xp_earned(guilds[guild_name]['xp'][date_now], guilds[guild_name]['xp'][
                date_last]) + " || " + "{:.1f}".format(
                (datetime.fromtimestamp(int(now_now)) - datetime.fromtimestamp(
                    int(guilds[guild_name]['xp'][date_now][
                            'date']))).total_seconds() / SECONDS_PER_DAY) + " D Ago - " + "{:.1f}".format(
                ((datetime.fromtimestamp(int(now_now)) - datetime.fromtimestamp(
                    int(guilds[guild_name]['xp'][date_last][
                            'date']))).total_seconds()) / SECONDS_PER_DAY) + " D Ago\n")

        date_last = date_now

    while len(middle_xp) != 0:
        string = ''.join(middle_xp[:30])
        middle_xp = middle_xp[30:]
        try:
            await message.channel.send("```ml\n" + string + "```")
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
    date1 = (datetime.fromtimestamp(now_now) - datetime.fromtimestamp(
        guilds[guild_name]['xp'][date1]['date'])).total_seconds() / SECONDS_PER_DAY
    date2 = (datetime.fromtimestamp(now_now) - datetime.fromtimestamp(
        guilds[guild_name]['xp'][date2]['date'])).total_seconds() / SECONDS_PER_DAY
    if days_difference == 0:
        average = "???"
    else:
        average = "{:,d}".format(int(total_raw_xp_earned / days_difference))
    string = "Total " + str(total_xp_earned) + "\nAverage Earned XP From " + str(
        "{:.1f}".format(date1)) + " D Ago to " + str(
        "{:.1f}".format(date2)) + " D Ago = " + average + " per " + str(int(step / 3600)) + " hour(s)"
    try:
        await message.channel.send("```ml\n" + string + "```")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def on_command_track(message):
    guild_name = " ".join(message.content.split(" ")[1:])
    if guild_name in guilds:
        try:
            await message.channel.send("\"" + guild_name + "\" already exists in my records")
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        return

    if guild_name in leaderboard_cache[0]:
        # put an exact amount of xp earned in
        data = leaderboard_cache[0][guild_name]
        date = time.time()
        xp = data['xp']
        level = data['level']
        current = {"type": "leader", "date": date, "level": level, "xp": xp}
        guilds[guild_name] = {"xp": [current], "time": 0, "channel": message.channel.id}

    else:
        try:
            guild_data = await fetch_data(guild_name)
        except:
            try:
                await message.channel.send("Failed to get data for: \"" + guild_name + "\"")
            except (discord.errors.Forbidden, discord.errors.NotFound):
                pass
            return

        current_date = time.time()

        try:
            current_level = guild_data['level']
        except KeyError:
            await not_a_guild(message.channel, guild_name)
            return
        current_xp = guild_data['xp']
        current = {"type": "level", "date": current_date, "level": current_level, "xp": current_xp}
        guilds[guild_name] = {"xp": [current], "time": 0, "channel": message.channel.id}

    write()
    try:
        await message.channel.send(guild_name + " created")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def begin():
    try:
        await client.get_channel(BEGIN_CHANNEL).send("begun")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass
    read()
    begun[0] = True
    count = 0
    while True:
        try:
            await fetch_leaderboard()
            break
        except:
            await asyncio.sleep(20)
    while True:
        if count == 30:
            count = 0
            try:
                await fetch_leaderboard()
            except:
                print("oof")
                await asyncio.sleep(45)
        start = time.time()
        for guild_name in guilds:
            guilds[guild_name]["time"] += 1
            if guilds[guild_name]["time"] >= MINUTES_PER_UPDATE:
                guilds[guild_name]["time"] = 0

                if guild_name in leaderboard_cache[0]:
                    # put an exact amount of xp earned in
                    data = leaderboard_cache[0][guild_name]
                    date = time.time()
                    xp = data['xp']
                    level = data['level']
                    current = {"type": "leader", "date": date, "level": level, "xp": xp}

                else:
                    guild_data = await fetch_data(guild_name)

                    current_date = time.time()
                    current_level = guild_data['level']
                    current_xp = guild_data['xp']
                    current = {"type": "level", "date": current_date, "level": current_level, "xp": current_xp}

                past = guilds[guild_name]['xp'][-1]
                if get_raw_xp_earned(past,current) != 0:
                    guilds[guild_name]["xp"].append(current)

                while len(guilds[guild_name]['xp']) > 8760:  # 365 * 24:
                    guilds[guild_name]['xp'].pop(0)
                # get xp earned in the last cycle
        write()
        await asyncio.sleep(60 - (time.time() - start))


def get_xp_earned(past, current):
    if past['type'] == 'leader':
        if current['type'] == 'leader':
            # leader leader
            xp_earned = current['xp'] - past['xp']
            current_date = current['date']
            past_date = past['date']

            days = int(((current_date - past_date) / SECONDS_PER_DAY) * 100) / 100
            #TODO
            return "XP Earned In " + "{:.2f}".format(days) + " Days = " + "{:10,d}".format(int(xp_earned))
        else:
            # leader level
            xp_earned = 0

            past_xp = past['xp']
            past_level = past['level']

            current_xp = current['xp']
            current_level = current['level']

            while past_level != current_level:
                if past_level - 1 >= len(xp_chart):
                    return "msg appleptr16#5054 \"add level " + str(past_level) + " to the xp chart\""
                xp_earned += xp_chart[past_level - 1] - past_xp
                past_level += 1
                past_xp = 0
            xp_earned += (xp_chart[current_level - 1] * current_xp / 100) - past_xp

            current_date = current['date']
            past_date = past['date']

            days = int(((current_date - past_date) / SECONDS_PER_DAY) * 100) / 100
            return "XP Earned In " + "{:.2f}".format(days) + " Days = " + "{:,d}".format(int(xp_earned))
    else:
        if current['type'] == 'leader':
            # level leader

            xp_earned = 0
            past_level = past['level']
            past_xp = past['xp']

            current_level = current['level']
            current_xp = current['xp']

            while past_level != current_level:
                if past_level - 1 >= len(xp_chart):
                    return "msg appleptr16#5054 \"add level " + str(past_level) + " to the xp chart\""
                xp_earned += xp_chart[past_level - 1] * (1 - past_xp / 100)
                past_level += 1
                past_xp = 0

            xp_earned += current_xp - xp_chart[current_level - 1] * past_xp / 100

            current_date = current['date']
            past_date = past['date']

            days = int(((current_date - past_date) / SECONDS_PER_DAY) * 100) / 100
            return "XP Earned In " + "{:.2f}".format(days) + " Days = " + "{:,d}".format(int(xp_earned))
        else:
            # level level
            if past['level'] > current['level']:
                return "Past level is greater than current level? O.o"
            xp_earned = 0

            past_level = past['level']
            past_xp = past['xp']
            past_date = past['date']

            current_level = current['level']
            current_xp = current['xp']
            current_date = current['date']

            while past_level != current_level:
                if past_level - 1 >= len(xp_chart):
                    return "msg appleptr16#5054 \"add level " + str(past_level) + " to the xp chart\""
                xp_earned += xp_chart[past_level - 1] * (1 - past_xp / 100)
                past_level += 1
                past_xp = 0
            xp_earned += ((current_xp - past_xp) / 100) * xp_chart[current_level]
            days = int(((current_date - past_date) / SECONDS_PER_DAY) * 100) / 100
            return "XP Earned In " + "{:.2f}".format(days) + " Days = " + "{:,d}".format(int(xp_earned))


def get_raw_xp_earned(past, current):
    # TODO
    if past['type'] == 'leader':
        if current['type'] == 'leader':
            # leader leader
            xp_earned = current['xp'] - past['xp']
            current_date = current['date']
            past_date = past['date']

            days = int(((datetime.fromtimestamp(int(current_date)) - datetime.fromtimestamp(
                int(past_date))).total_seconds() / (SECONDS_PER_DAY)) * 100) / 100
            return xp_earned
        else:
            # leader level
            xp_earned = 0

            past_xp = past['xp']
            past_level = past['level']

            current_xp = current['xp']
            current_level = current['level']

            while past_level != current_level:
                if past_level - 1 >= len(xp_chart):
                    return "msg appleptr16#5054 \"add level " + str(past_level) + " to the xp chart\""
                xp_earned += xp_chart[past_level - 1] - past_xp
                past_level += 1
                past_xp = 0
            xp_earned += (xp_chart[current_level - 1] * current_xp / 100) - past_xp

            current_date = current['date']
            past_date = past['date']

            days = int(((datetime.fromtimestamp(int(current_date)) - datetime.fromtimestamp(
                int(past_date))).total_seconds() / (SECONDS_PER_DAY)) * 100) / 100
            return xp_earned
    else:
        if current['type'] == 'leader':
            # level leader

            xp_earned = 0
            past_level = past['level']
            past_xp = past['xp']

            current_level = current['level']
            current_xp = current['xp']

            while past_level != current_level:
                if past_level - 1 >= len(xp_chart):
                    return "msg appleptr16#5054 \"add level " + str(past_level) + " to the xp chart\""
                xp_earned += xp_chart[past_level - 1] * (1 - past_xp / 100)
                past_level += 1
                past_xp = 0

            xp_earned += current_xp - xp_chart[current_level - 1] * past_xp / 100

            current_date = current['date']
            past_date = past['date']

            days = int(((datetime.fromtimestamp(int(current_date)) - datetime.fromtimestamp(
                int(past_date))).total_seconds() / (SECONDS_PER_DAY)) * 100) / 100
            return xp_earned
        else:
            # level level
            if past['level'] > current['level']:
                return "Past level is greater than current level? O.o"
            xp_earned = 0

            past_level = past['level']
            past_xp = past['xp']
            past_date = past['date']

            current_level = current['level']
            current_xp = current['xp']
            current_date = current['date']

            while past_level != current_level:
                if past_level - 1 >= len(xp_chart):
                    return "msg appleptr16#5054 \"add level " + str(past_level) + " to the xp chart\""
                xp_earned += xp_chart[past_level - 1] * (1 - past_xp / 100)
                past_level += 1
                past_xp = 0
            xp_earned += ((current_xp - past_xp) / 100) * xp_chart[current_level]
            days = int(((datetime.fromtimestamp(int(current_date)) - datetime.fromtimestamp(
                int(past_date))).total_seconds() / (SECONDS_PER_DAY)) * 100) / 100
            return xp_earned


async def end(message):
    pass


def write():
    string = dumps(guilds)
    with open("data.txt", 'w') as file:
        file.write(string)


def read():
    with open("data.txt") as file:
        string = file.readline()
    if string == '\n' or string == '':
        return
    loaded = loads(string)
    for element in loaded:
        guilds[element] = loaded[element]


def find_closest(guild_name, desired_date):
    previous_date = -1
    for i in range(len(guilds[guild_name]['xp'])):
        date = guilds[guild_name]['xp'][i]['date']
        if date >= desired_date:
            # if we past the desired date
            if abs(previous_date - desired_date) < abs(date - desired_date):
                # previous_date is what we want
                return i - 1
            else:
                # date is what we want
                return i
        previous_date = date
    return len(guilds[guild_name]['xp']) - 1


async def fetch_leaderboard():
    try_number = 0
    while try_number < 3:
        try:
            leader_board_raw_data = loads(urllib.request.urlopen(
                "https://api.wynncraft.com/public_api.php?action=statsLeaderboard&type=guild&timeframe=alltime").readline().decode(
                "utf-8"))['data']
            leader_board_data = dict()
            for guild_data in leader_board_raw_data:
                leader_board_data[guild_data['name']] = guild_data
            leaderboard_cache[0] = leader_board_data
            return
        except:
            await asyncio.sleep(10)
        try_number += 1


async def fetch_data(guild_name):
    try_number = 0
    guild_name = "%20".join(guild_name.split(" "))
    while try_number < 5:
        try:
            guild_data = loads(urllib.request.urlopen(
                "https://api.wynncraft.com/public_api.php?action=guildStats&command=" + guild_name).readline().decode(
                "utf-8"))
            return guild_data
        except:
            traceback.print_exc()
            await asyncio.sleep(10)
        try_number += 1
    raise Exception("FetchDataFailure")


async def correct_command_xp(channel):
    try:
        await channel.send("c!xp x <guild_name>\nc!xp x y <guild_name>")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def correct_command_xp_hourly(channel):
    try:
        await channel.send("c!xp zh x <guild_name>\nc!xp zh x y <guild_name>")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def not_tracking(channel, guild_name):
    try:
        await channel.send(
            "I'm not tracking xp for " + guild_name + "\nc!track <guild_name> to have me start tracking their xp")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def failed_message(channel):
    try:
        await channel.send("Failed to get xp for the requested date")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def too_many_days(channel):
    try:
        await channel.send("The maximum range for number of days to display is 100 days")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def not_a_guild(channel, guild_name):
    try:
        await channel.send("\"" + guild_name + "\" is not a real guild")
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


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


commands_set = {"track": on_command_track, "xp": on_command_xp, "xph": on_command_xp_hourly, "help": on_command_help,
                "info": on_command_info}
if __name__ == "__main__":
    while True:
        try:
            client_runner()
        except:
            pass
