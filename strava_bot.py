
import discord
from discord.ext import commands, tasks
from discord.utils import get
import asyncio
from itertools import cycle
import random
import os
import time
import datetime

import requests
import json
import urllib3

import polyline
import sqlite3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




# ============================================================================ #
# ||||||||||||||||||||||          Custom Errors          ||||||||||||||||||||| #
# ============================================================================ #

class NoActivitiesError(Exception):
    '''Error Handling for when there are no activities in the database'''
    pass


# ============================================================================ #
# ||||||||||||||||||||||       Database Connection       ||||||||||||||||||||| #
# ============================================================================ #

# connect to sqlite3 database (create it if it doesnt exist)
conn = sqlite3.connect('stravaDiscordBot.db')
# create a cursor for this connection
c = conn.cursor()

def create_tables():
    '''Creates tables for storing data in the strava_discord.db database
    
    Included tables in this database are as follows:
            userTokens : user-specific information for identification and authorization
            userStats : monthly dist, elev, time, and active days statistics
            userActivities : activity information for all authorized users (includes polyline)
            dailyActivities : similar to userActivities, but only for today's activities
            routes : various routes and information, including user comments
            roles : user-specific roles (to change monthly)'''
    
    #create userTokens Table
    c.execute('CREATE TABLE IF NOT EXISTS userTokens(discord_id INTEGER PRIMARY KEY, \
                                                     username TEXT, \
                                                     ref_token TEXT, \
                                                     ac_token TEXT, \
                                                     exp_at REAL)')
    #create userStats Table
    c.execute('CREATE TABLE IF NOT EXISTS userStats(discord_id INTEGER, \
                                                    dist REAL, \
                                                    time REAL, \
                                                    elev REAL, \
                                                    days INTEGER, \
                                                    guild_id INTEGER)')
    #create userActivities Table
    c.execute('CREATE TABLE IF NOT EXISTS userActivities(discord_id INTEGER, \
                                                         activity_id INTEGER PRIMARY KEY, \
                                                         activity_name TEXT, \
                                                         distance REAL, \
                                                         moving_time REAL, \
                                                         elev_gain REAL, \
                                                         type TEXT, \
                                                         start_date_local TEXT, \
                                                         polyline TEXT, \
                                                         day INTEGER, \
                                                         month INTEGER, \
                                                         year INTEGER)')
    #create dailyActivities Table
    c.execute('CREATE TABLE IF NOT EXISTS dailyActivities(discord_id INTEGER, \
                                                          activity_id INTEGER PRIMARY KEY, \
                                                          activity_name TEXT, \
                                                          distance REAL, \
                                                          moving_time REAL, \
                                                          elev_gain REAL, \
                                                          type TEXT, \
                                                          guild_id INTEGER)')
    #create routes Table
    c.execute('CREATE TABLE IF NOT EXISTS routes(route_id INTEGER PRIMARY KEY, \
                                                 route_name TEXT, \
                                                 category TEXT, \
                                                 type TEXT, \
                                                 filename TEXT, \
                                                 distance REAL, \
                                                 average_moving_time REAL, \
                                                 elev_gain REAL, \
                                                 polyline TEXT, \
                                                 comments TEXT, \
                                                 guild_id INTEGER, \
                                                 isPublic TEXT)')
    #create roles Table
    c.execute('CREATE TABLE IF NOT EXISTS roles(discord_id INTEGER PRIMARY KEY, \
                                                guild_id INTEGER, \
                                                dist_role TEXT, \
                                                time_role TEXT, \
                                                elev_role TEXT, \
                                                days_role TEXT)')
    #create id table
    c.execute('CREATE TABLE IF NOT EXISTS _idTable(guild_id INTEGER, \
                                                   discord_id INTEGER, \
                                                   strava_id INTEGER, \
                                                   username)')
    #create guildSettings Table
    c.execute('CREATE TABLE IF NOT EXISTS guildSettings(guild_id INTEGER PRIMARY KEY, \
                                                        types TEXT, \
                                                        lead_id INTEGER, \
                                                        show_id INTEGER, \
                                                        rec_id INTEGER, \
                                                        lat_lon_center TEXT, \
                                                        lead_freq INTEGER, \
                                                        show_freq INTEGER, \
                                                        rec_freq INTEGER, \
                                                        update_freq INTEGER)')


create_tables()
# ============================================================================ #
# |||||||||||||||||||||||       Helper Functions       ||||||||||||||||||||||| #
# ============================================================================ #




def dataEntry(tableName, dict):
    '''Insert a given dict into a sqlite3 database
    
    Inputs
        tableName : name of table to insert dict into
        dict : dictionary to insert into database table
    '''

    sql = 'INSERT OR REPLACE INTO {} ({}) VALUES ({});'.format(tableName,
                                                    ','.join(dict.keys()),
                                                    ','.join(['?']*len(dict)))
    c.execute(sql, tuple(dict.values()))
    conn.commit()


def dataRead(tableName, des_vals, cond_key=None, cond_ineq=None, cond_value=None, fetchOne=False, extra_cond=None):
    '''Read a row(s) in a sqlite3 database table
    
    Inputs
        tableName : name of table to insert dict into
        des_vals : desired returned values in a row of the table (type: list)
        cond_key : table column key to query with a conditional
        cond_ineq : inequality to use in conditional (==, <, >, <=, >=, !=)
        cond_value : value of ineqality in conditional
    '''

    exec_str = 'SELECT {} FROM {}'.format(','.join(des_vals), tableName)
    if cond_key != None and cond_ineq in ['<','>','=','!=','<=','>='] and cond_value != None:
        exec_str +=  ' WHERE {} {} {}'.format(cond_key, cond_ineq, cond_value)
        if extra_cond != None:
                    exec_str += ' AND {}'.format(extra_cond)
    c.execute(exec_str)

    if fetchOne:
        return c.fetchone()
    else:
        return c.fetchall()


def dataUpdate(tableName, des_vals, update_vals, cond_key=None, cond_ineq=None, cond_value=None, extra_cond=None):
    '''Updates rows in a database table
        
    Inputs
        tableName : name of table to insert dict into
        des_vals : desired returned values in a row of the table (type: list)
        cond_key : table column key to query with a conditional
        cond_ineq : inequality to use in conditional (==, <, >, <=, >=, !=)
        cond_value : value of ineqality in conditional
    '''

    c.execute('SELECT * FROM {}'.format(tableName))
    if len(des_vals) == len(update_vals):
        for i in range(len(des_vals)):
            exec_str = 'UPDATE {} SET {} = {}'.format(tableName, des_vals[i], update_vals[i])
            if cond_key != None and cond_ineq in ['<','>','=','!=','<=','>='] and cond_value != None:
                exec_str +=  ' WHERE {} {} {}'.format(cond_key, cond_ineq, cond_value)
                if extra_cond != None:
                    exec_str += ' AND {}'.format(extra_cond)
            c.execute(exec_str)
            conn.commit()


def dataDelete(tableName, cond_key=None, cond_ineq=None, cond_value=None):
    '''Deletes rows in a database table
        
    Inputs
        tableName : name of table to insert dict into
        cond_key : table column key to query with a conditional
        cond_ineq : inequality to use in conditional (==, <, >, <=, >=, !=)
        cond_value : value of ineqality in conditional
    '''

    exec_str = 'DELETE FROM {}'.format(tableName)
    if cond_key != None and cond_ineq in ['<','>','=','!=','<=','>='] and cond_value != None:
                exec_str +=  ' WHERE {} {} {}'.format(cond_key, cond_ineq, cond_value)
    c.execute(exec_str)
    conn.commit()


def poly_toMap(activity_id, poly, maptype='roadmap'):
    '''Create a map image from a given polyline using google map api
    
    Inputs
        activity_id : id of the activity (for file save purposes)
        poly : the polyline of the activity
        maptype : type of map type (roadmap, satellite, hybrid, terrain)
    '''

    url = "https://maps.googleapis.com/maps/api/staticmap?"
    m_size = '640x640'
    param = {'size': m_size, 'maptype': maptype, 'path':'enc:{}'.format(poly), 'key':g_api_key}

    map_r = requests.get(url, headers=None, params=param)
    
    # save map image to /obj/activitymaps with name based on activity id and maptype
    with open('obj/activitymaps/{}_{}.png'.format(activity_id, maptype), 'wb') as f:
        f.write(map_r.content)
    return map_r


def multiPoly_toMap(filename, poly_list, maptype='roadmap', m_size='640x640'):
    '''Create a map image from multiple polylines using google map api
    
    Inputs
        filename : name of file to save map image
        poly_list : list of all polylines to be plotted on map
        maptype (optional) : type of map type (roadmap, satellite, hybrid, terrain)
        m_size (optional) : image size of the map created
    '''

    url = "https://maps.googleapis.com/maps/api/staticmap?"
    m_size = '640x640'
    multipoly = []

    color_list = ['0x0000FF80','0xFF000080','0x00FF0080']

    i = 0
    for each in poly_list:
        multipoly.append('color:{}|weight:2|enc:{}'.format(color_list[i], each))
        i += 1
    
    param = {'size': m_size, 'maptype': maptype, 'path':multipoly, 'key':g_api_key}
    map_r = requests.get(url, headers=None, params=param)

    # save map image to /obj/activitymaps with name based on input filename
    with open('obj/recommendedmaps/{}.png'.format(filename), 'wb') as f:
        f.write(map_r.content)
    return map_r



# ============================================================================ #
# |||||||||||||||||||||||          Constants           ||||||||||||||||||||||| #
# ============================================================================ #

status_list = cycle([discord.Game("Tag with my Imaginary Friends"),
                     discord.Game('in the Sand'),
                     discord.Activity(type=discord.ActivityType.watching, name='a FlightMech Lecture'),
                     discord.Activity(type=discord.ActivityType.watching, name='a video on the theory of walking'),
                     discord.Activity(type=discord.ActivityType.listening, name='to silence'),
                     discord.Activity(type=discord.ActivityType.listening, name='to some LoFi Beats')])

role_names = {'dist':{80:'Basically a Professional', 50:'UltraMarathoner', 26:'Marathoner',13:'Half-Marathoner'},
              'time':{24:'24-hour Lim', 10:'10-Hour Lim', 5:'10-Hour Lim'},
              'elev':{13700:'Everest Summiter', 5280:'Mountain Climber'},
              'days':{28:'Might as well join the XC team', 15:'Athlete', 5:'Hobby Runner'}}


# ============================================================================ #
# |||||||||||||||||||||||          Load Data           ||||||||||||||||||||||| #
# ============================================================================ #

# loads variables bot_token, client_secret, g_api_key, client_id, bot_id
with open('obj/botInfo.txt') as f:
    bot_token, client_secret, g_api_key, \
           client_id, bot_id = f.read().splitlines()
print('Bot Token:______'+bot_token)
print('Client Secret:__'+client_secret)
print('Google API Key:_'+g_api_key)
print('Client ID:______'+client_id)
print('Bot ID:_________'+bot_id)

bot_id = int(bot_id)
client_id = int(client_id)

# use this to set permissions (in front of command definition, but after client.command decorator) : @commands.has_role("Admin")

# ============================================================================ #
# |||||||||||||||||||||||    Discord Bot Functions     ||||||||||||||||||||||| #
# ============================================================================ #

# define client and command prefix
client = commands.Bot(command_prefix = '$strava ',help_command=None)



# ==================================================== #
# ||||||        Discord Helper Functions        |||||| #
# ==================================================== #

def _removeExpiredTokens():
    '''Delete rows of database table where access tokens have expired'''

    print('Removed Tokens:',len(dataRead('userTokens', ['*'], cond_key='exp_at', cond_ineq='<', cond_value=time.time())))
    dataDelete('userTokens', cond_key='exp_at', cond_ineq='<', cond_value=time.time())


def _updateAccessTokens():
    '''Updates the access tokens (userTokens table) for authorized users 
    and updates the database'''

    token_url = 'https://www.strava.com/oauth/token'
    
    # get all user tokens to be updated (all tokens)
    tokenList = dataRead('userTokens', ['*'])
    
    if len(tokenList) > 0:
        for i in tokenList:
            discord_id = tokenList[i][0]
            ref_token = tokenList[i][2]
            ac_token = tokenList[i][3]

            refreshToken_payload = {'client_id' : client_id,
                                    'client_secret' : client_secret,
                                    'refresh_token' : ref_token,
                                    'grant_type' : 'refresh_token',
                                    'f' : 'json'}
            # make request to strava api to update access tokens (returns new access and refresh tokens)
            res = requests.post(token_url, data=refreshToken_payload, verify=False).json()

            access_token = res['access_token']
            refresh_token = res['refresh_token']
            exp_at = res['expires_at']

            # update the new token values in the database (for each user (discord_id))
            dataUpdate('userTokens', ['ref_token','ac_token','exp_at'],
                       [refresh_token, access_token, exp_at],
                       cond_key='discord_id', cond_ineq='=', cond_value=discord_id)
    else:
        # if length of tokenList is 0 (no authorized users)
        print('No Authorized Users')


def _updateUserActivities(guild_id, num_activities=99):
    '''Update user activities and save new activities to userActivities table in database
    
    Inputs
        guild_id : (server_id) id number for the server where userActivities will be updated
        num_activities (optional) : the maxiumum number of activities to add at one time
    '''

    print('attempting to update activities. . .')
    tokenList = dataRead('userTokens', ['*'])

    if len(tokenList) > 0:
        for i in range(len(tokenList)):
            discord_id = tokenList[i][0]
            ac_token = tokenList[i][3]

            ua_url = 'https://www.strava.com/api/v3/athlete/activities'
            header = {'Authorization': 'Bearer ' + ac_token}
            param = {'per_page': num_activities, 'page':1}
            
            activities = requests.get(ua_url, headers=header, params=param).json()

            for each in activities:
                activity = {'discord_id' : discord_id,
                            'activity_id': each['id'],
                            'activity_name': each['name'],
                            'distance': each['distance'],
                            'moving_time': each['moving_time'],
                            'elev_gain': each['total_elevation_gain'],
                            'type': each['type'],
                            'start_date_local': each['start_date_local'],
                            'polyline': each['map']['summary_polyline'],
                            'day': int(each['start_date_local'].split('T')[0].split('-')[2]),
                            'month': int(each['start_date_local'].split('T')[0].split('-')[1]),
                            'year': int(each['start_date_local'].split('T')[0].split('-')[0])}
                
                dataEntry('userActivities', activity)


def _updateUserStats(guild_id):
    '''Go through user activities and update userStats based on monthly totals'''

    today = datetime.date.today().strftime("%Y-%m-%d")
    month = today.split('-')[1]
    year = today.split('-')[0]

    discord_id_list = dataRead('_idTable',
                                ['discord_id'],
                                cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
    try:
        dataDelete('userStats', cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
    except:
        print('could not delete userStats')
    type_list = dataRead('guildSettings',['types'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
    if len(type_list) > 0:
        print(type_list[0])
        if len(type_list[0]) > 0:
            type_string = ""
            print(type_list[0][0])
            if len(type_list[0][0]) > 0:
                for each in type_list[0][0].split(','):
                    if len(type_string) == 0:
                        type_string += "\'{}\'".format(each)
                    else:
                        type_string += ",\'{}\'".format(each)
                if len(discord_id_list) > 0:
                    for each in discord_id_list:
                        discord_id = each[0]

                        monthly_activities = dataRead('userActivities',
                                                      ['activity_id','distance','moving_time','elev_gain',
                                                       'type','start_date_local'],
                                                      cond_key='discord_id', cond_ineq='=', cond_value=discord_id,
                                                      extra_cond='month = {} AND year = {} AND type IN ({})'.format(month, year, type_string))
                        print(type_string)
                        if len(monthly_activities) > 0:
                            dist_total = 0
                            time_total = 0
                            elev_total = 0
                            days_set = set()
                            for activity in monthly_activities:
                                dist_total += activity[1]
                                time_total += activity[2]
                                elev_total += activity[3]
                                days_set.add(activity[5].split('T')[0].split('-')[2])
                            days_total = len(days_set)

                            stats_dict = {'discord_id':discord_id, 'guild_id': guild_id,
                                          'dist':dist_total, 'time':time_total,'elev':elev_total,'days':days_total}
                            dataEntry('userStats',stats_dict)
                        else:
                            print('no monthly activities')
                else:
                    print('no authorized users in guild:',guild_id)
            else:
                print('No valid activity types. (Must set guild valid activity types using addType command)')


def _updateDailyActivities(guild_id):
    '''Go through user activities and add all today's activities to dailyActivities Table'''

    today = datetime.date.today().strftime("%Y-%m-%d")
    day = today.split('-')[2]
    month = today.split('-')[1]
    year = today.split('-')[0]

    discord_id_list = dataRead('_idTable',
                                ['discord_id'],
                                cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
    if len(discord_id_list) <= 0:
        return
    discord_id_list = ','.join([str(x[0]) for x in discord_id_list])

    daily_activities = dataRead('userActivities',
                                ['discord_id','activity_id','activity_name','distance',
                                 'moving_time','elev_gain','type','day','month','year'],
                                cond_key='day', cond_ineq='=', cond_value=day,
                                extra_cond='month = {} AND year = {} and discord_id IN ({})'.format(month, year, discord_id_list))
    if len(daily_activities) > 0:
        for each in daily_activities:
            dailyActivity = {'discord_id' : each[0],
                             'activity_id' : each[1],
                             'activity_name' : each[2],
                             'distance' : each[3],
                             'moving_time' :  each[4],
                             'elev_gain' : each[5],
                             'type' : each[6],
                             'guild_id' : guild_id}
            dataEntry('dailyActivities', dailyActivity)


async def _createActivity(activity_id, pfp, username, maptype='roadmap'):
    '''Create an activity embed from activity information

    Is set to be a asynchronous function due to creation of map (using googleMapsAPI)
    
    Inputs
        activity_id : activity-specific id for a given activity
        pfp : url for a discord user's profile picture (url to link to image)
        username : discord username
        maptype (optional) : design of map (options include roadmap, terrain, hybrid)
    Returns
        embed : the activity embed displayed through discord (includes title, description, and map)
        im_file : the file location for the embeded activity map
    '''

    activity = dataRead('userActivities', ['activity_name','distance','moving_time','elev_gain',
                                           'type','start_date_local','polyline'],
                        cond_key='activity_id', cond_ineq='=', cond_value=activity_id)
    if len(activity) <= 0:
        print('No activities with this id')
        return None
    map_im = poly_toMap(activity_id, poly=activity[0][6], maptype=maptype)

    start_date = activity[0][5].split('T')[0].split('-')
    start_time = activity[0][5].split('T')[1].split(':')

    if int(start_time[0]) >= 12:
        am_pm = 'PM'
    else:
        am_pm = 'AM'
    if int(start_time[0]) % 12 == 0:
        hour = 12
    else:
        hour = int(start_time[0]) % 12
    desc_time = '{}/{}/{} at {}:{} {}'.format(start_date[1], start_date[2], start_date[0],
                                              hour, start_time[1], am_pm)
    embed = discord.Embed(title=activity[0][0],
                          description=desc_time,
                          color=0x00ff00)
    distance = round(activity[0][1] / 1609, 2)
    time = str(datetime.timedelta(seconds=activity[0][2]))
    elev_gain = round(activity[0][3] * 3.28, 2)

    if pfp != None and username != None:
        embed.set_author(name= str(username) +' mapped a run!', icon_url=pfp)

    embed.add_field(name="Distance", value=str(distance)+' mi', inline=True)
    embed.add_field(name="Time", value=str(time), inline=True)
    embed.add_field(name="Elev Gain", value=str(elev_gain)+' ft', inline=True)

    im_file = discord.File('obj/activitymaps/{}_{}.png'.format(activity_id, maptype))
    embed.set_image(url='attachment://obj/activitymaps/{}_{}.png'.format(activity_id, maptype))

    return embed, im_file


def _createLeaderboard(guild_id, sort='dist'):
    '''Creates a leaderboard from the userStats of users in specified guild
    
    Inputs
        guild_id : (server_id) id number for the server where leaderboard will be posted
        sort : (optional) the method in which the leaderboard will be sorted (dist, time, elev, days)
    Returns
        embed_update : a embed for the guild/club leaderboard
    '''
    
    embed_update = discord.Embed(title='Activities Leaderboard',
                                description=datetime.datetime.now().strftime('%B')+' '+str(datetime.datetime.now().year),
                                color=0x00ff00)

    # get discord_id(s) of all authorized users in the guild
    discord_ids = dataRead('_idTable', ['discord_id'], cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
    
    if len(discord_ids) <= 0:
        print('No User Data (no authorized users in _idTable)')
        return
    discord_ids = [str(val[0]) for val in discord_ids]
    discord_ids = ', '.join(discord_ids)

    # get the user stats for all the discord_id(s)
    user_data = dataRead('userStats',
                         ['discord_id','dist','time','elev','days'],
                         cond_key='discord_id', cond_ineq='IN', cond_value='({})'.format(discord_ids),
                         extra_cond='guild_id = {}'.format(guild_id))
    if len(user_data) <= 0:
        print('No User Data (userStats not found for authorized users)')
        return

    # get the discord usernames for all the discord_id(s) maybe switch this to call discord server instead (less calls to own database)
    discord_usernames = dataRead('_idTable', ['discord_id', 'username'], cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
    if len(discord_usernames) <= 0:
        print('No User Data (usernames not found in _idTable)')
        return

    # create a discord_id:username (key:value) dictionary
    username_dict = {}
    for i in range(len(discord_usernames)):
        username_dict[str(discord_usernames[i][0])] = discord_usernames[i][1]

    #sort the user data for the leaderboard by one of the sort methods
    if sort == 'dist':
        sorted_data = sorted(user_data, key=lambda x: x[1], reverse=True)
    elif sort == 'time':
        sorted_data = sorted(user_data, key=lambda x: x[2], reverse=True)
    elif sort == 'elev':
        sorted_data = sorted(user_data, key=lambda x: x[3], reverse=True)
    elif sort == 'days':
        sorted_data = sorted(user_data, key=lambda x: x[4], reverse=True)
    else:
        raise ValueError('Bad sort input')

    # initialize the leadreboard text for each of the fields
    rank, name, dist, time, elev, days = '', '', '', '', '', ''
    iter_val = 0

    for each in sorted_data:
        iter_val += 1
        rank += '#{}'.format(iter_val) + '\n'

        username = username_dict[str(sorted_data[iter_val-1][0])]
        name += username + '\n'

        dist += str(round(sorted_data[iter_val-1][1]/1609, 2)) + '\n'
        time += str(round(sorted_data[iter_val-1][2]/3600,2)) + '\n'
        elev += str(round(sorted_data[iter_val-1][3],2)) + '\n'
        days += str(round(sorted_data[iter_val-1][4],2)) + '\n'

    embed_update.add_field(name='Rank', value=rank, inline=True)
    embed_update.add_field(name='Name', value=name, inline=True)

    if sort == 'dist':
        embed_update.add_field(name='Distance (mi)', value=dist, inline=True)
    elif sort == 'time':
        embed_update.add_field(name='Time (hr)', value=time, inline=True)
    elif sort == 'elev':
        embed_update.add_field(name='Elev Gain (ft)', value=elev, inline=True)
    elif sort == 'days':
        embed_update.add_field(name='Active Days', value=days, inline=True)            
    else:
        raise ValueError('Bad sort input')
    
    return embed_update


async def _checkIsLeaderboard(guild_id, payload):
    '''Checks whether a given reaction (through payload) was on a leaderboard
    
    Also removes all user reactions if it is a leaderboard (and if user reacts with wrong emoji)

    Inputs
        payload : (type:discord.payload) holds the data for the reaction of discord users
    '''
    
    if payload.event_type == 'REACTION_ADD':
        if payload.user_id != bot_id:
            channel = client.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if message.author.id == bot_id:
                if len(message.embeds) > 0:
                    if 'Activities Leaderboard' in message.embeds[0].to_dict()['title']:
                        if str(payload.emoji) == '????':
                            print('Reacted with Dist')
                            new_embed = _createLeaderboard(guild_id, sort='dist')
                        elif str(payload.emoji) == '???':
                            print('Reacted with Time')
                            new_embed = _createLeaderboard(guild_id, sort='time')
                        elif str(payload.emoji) == '????':
                            print('Reacted with Elev')
                            new_embed = _createLeaderboard(guild_id, sort='elev')
                        elif str(payload.emoji) == '????':
                            print('Reacted with Days')
                            new_embed = _createLeaderboard(guild_id, sort='days')
                        else:
                            print('Reacted with some random emoji, idk.')
                            await message.remove_reaction(payload.emoji, payload.member)
                            return
                        
                        await message.remove_reaction(payload.emoji, payload.member)
                        await message.edit(embed = new_embed)
                    else:
                        print('Not Leaderboard Message')
                else:
                    print('No embeds')
            else:
                print('Message not by bot')
        else:
            print('reaction not by user')
    else:
        print('Not type: REACTION_ADD')


async def _authorize(ctx):
    '''Method for authorizing user 
    
    (need to update to rediret_uri to own server to obtain authorization code
     without user having to retype the callback_url)
    
    Inputs
        ctx : (context) the message context (discord.py class)
    '''

    discord_id = str(ctx.message.author.id)
    scope = 'activity:read_all'
    redirect_uri = 'https://localhost/exchange_token'
    auth_url = 'https://www.strava.com/oauth/authorize'
    token_url = 'https://www.strava.com/oauth/token'

    authorization_url = '{}?client_id={}&response_type=code&redirect_uri={}&approval_prompt=force&scope={}'.format(auth_url, client_id, redirect_uri, scope)
    authorization_url = authorization_url.format(auth_url, client_id, redirect_uri, scope)

    url_message = await ctx.send('Please go to \n{} \nand authorize access.'.format(authorization_url))
    
    def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and 'https://localhost/exchange_token' in msg.content
    
    try:
        send_message = await ctx.send('[Please Send the full callback URL]: ')
        authorization_response = await client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await ctx.send('Input Timeout (60s), please retry the authorize command')
        return

    auth_code = authorization_response.content.split('&')[1][5:] # get content of message and split to get auth_code

    print('Authorization Code:',auth_code)
    payload = {'client_id' : client_id,
               'client_secret' : client_secret,
               'code' : auth_code,
               'grant_type' : 'authorization_code',
               'f' : 'json'}
    res = requests.post(token_url, data=payload, verify=False).json()

    ac_token = res['access_token']
    ref_token = res['refresh_token']
    username = ctx.message.author.display_name
    exp_at = res['expires_at']

    if type(ac_token) == str and type(ref_token) == str:
        tokens_dict = {'discord_id' : discord_id,
                       'username' : username,
                       'ref_token' : ref_token,
                       'ac_token' : ac_token,
                       'exp_at' : exp_at}

        _id_dict = {'guild_id' : ctx.guild.id,
                    'discord_id' : discord_id,
                    'strava_id' : None,
                    'username' : ctx.message.author.name}
        
        dataEntry('userTokens', tokens_dict)
        dataEntry('_idTable', _id_dict)

        await ctx.send('User Authorized! ({})'.format(ctx.author.display_name))
        await url_message.delete()
        await send_message.delete()
        await authorization_response.delete()


        initStats = {'discord_id' : discord_id,
                     'dist':0,
                     'time':0,
                     'elev':0,
                     'days':0,
                     'guild_id':ctx.guild.id}

        user = ctx.message.author
        role = get(ctx.guild.roles, name="Authorized")
        await user.add_roles(role)

        if len(dataRead('userStats', ['*'],
                       cond_key='discord_id', cond_ineq='=', cond_value=discord_id,
                       extra_cond='guild_id = {}'.format(ctx.guild.id))) <= 0:
            dataEntry('userStats',initStats)
        else:
            pass
    else:
        await ctx.send('ERROR: User not Authorized. Please try again.')
        print('Error Authorizing User. Tokens returned not type(str)')
    print('AuthorizeUser Command Completed')


def _myActivitiesList(username, discord_id, list_len=8):
    '''Create a embed list of user's activities
    
    (Possible Update : add multiple pages to embed 
     (can react <- or -> to switch to earlier/later activities))

    Input
        username : discord username of the user whose activities are displayed
        discord_id : discord identifying number (unique per discord user)
        list_len (optional) : the number of activities to display on the embed
    Return
        embed : the discord.py embed containing the list of user activities
    '''

    # get user activities (using discord_id)
    activities = dataRead('userActivities', ['activity_name','activity_id','distance'],
                         cond_key='discord_id', cond_ineq='=', cond_value=discord_id)
    # sort activities by local_start_date
    sorted_activities = sorted(activities, key=lambda x: x[1], reverse=True)

    embed = discord.Embed(title="{}'s Activities".format(username),
                                  color=0x00ff00)

    name, dist, act_id = '', '', ''
    iter_val = 0

    if len(sorted_activities) > 0:
        for each in sorted_activities:
            if iter_val < list_len or iter_val >= len(sorted_activities)-1:
                iter_val += 1
                name += each[0] + '\n'
                dist += str(round(each[2]/1609, 2)) + '\n'
                act_id += str(each[1]) + '\n'

    embed.add_field(name='Name', value=name, inline=True)
    embed.add_field(name='Dist (mi)', value=dist, inline=True)
    embed.add_field(name='Activity ID', value=act_id, inline=True)

    return embed


async def _showActivity(ctx, activity_id):
    '''Show a given embed containing a user's activities list (send through discord)
    
    Inputs
        ctx : (context) the message context (discord.py class)
        activity_id : activity-specific id for a given activity
    '''

    activity = dataRead('userActivities', ['discord_id'], cond_key='activity_id', cond_ineq='=', cond_value=activity_id)

    #if no activities, return None
    if len(activity) <= 0:
        ctx.send('Not Valid Activity ID, please try again')
        return None

    # get username and pfp from discord_id
    discord_id = activity[0][0]
    user = await client.fetch_user(discord_id)
    username = user.display_name
    pfp = user.avatar_url

    # create activity embed and send
    embed, im_file = await _createActivity(activity_id, pfp, username)
    message = await ctx.send(embed=embed, file=im_file)

    return message


async def _dailyRunningShowcase(guild, channel_id=None, channel_name='daily-activities'):
    '''Displays daily club activities in a "showcase" channel
    
    (Possible Update : make it so that it is based on channel_id so that guild owners
     can change the name of the channel and it will still post to correct channel)
    (Possible Update : add another column to the dailyActivities database with that
     holds a BOOL (or STR or INT) that signifies whether that activity has been showcased in that guild)

    Inputs
        guild : the guild (server) in which the showcase is to be shown (type:discord.py object)
        channel_name (optional) : channel name in which the showcase is to be displayed
    '''
    if channel_id != None:
        try:
            showcase_channel = await client.fetch_channel(channel_id)
        except:
            return
    else:
        try:
            showcase_channel = discord.utils.get(guild.channels, name=channel_name)
        except:
            #showcase_channel = await guild.create_text_channel(name=channel_name)
            #print('Created Channel')
            return
    
    # get the daily activities for specified guild
    dailyActivities = dataRead('dailyActivities',
                               ['discord_id','activity_id'],
                               cond_key='guild_id', cond_ineq='=', cond_value=guild.id)
    if len(dailyActivities) > 0:
        # get a random activity
        random.shuffle(dailyActivities)
        showcase_activity = dailyActivities.pop()

        discord_id = showcase_activity[0]
        user = await client.fetch_user(discord_id)
        pfp = user.avatar_url
        username = user.display_name

        # create activity embed and send to showcase_channel
        embed, im_file = await _createActivity(showcase_activity[1], pfp, username)
        message = await showcase_channel.send(embed=embed, file=im_file)

        # delete the activity from the dailyActivities table in the database
        dataDelete('dailyActivities', cond_key='activity_id', cond_ineq='=', cond_value=showcase_activity[1])
        print('removed {} from daily activities'.format(showcase_activity[1]))
    else:
        print('No Daily Activities')
        await showcase_channel.send('No Daily Activities.')


async def _setRoles(guild_id):
    '''Sets the user roles based on userStats
    
    Inputs
        guild_id : (server_id) id number for the server where leaderboard will be posted
    '''

    # get all the authorized users in the guild (their discord_id(s))
    discord_ids = dataRead('_idTable', ['discord_id'], cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
    
    if len(discord_ids) <= 0:
        print('No User Data (no authorized users in _idTable)')
        return
    discord_ids = ', '.join(discord_ids)

    user_data = dataRead('userStats', ['discord_id','dist','time','elev','days'],
                         cond_key='discord_id', cond_ineq='IN', cond_value='({})'.format(discord_ids),
                         extra_cond='guild_id = {}'.format(guild_id))

    guild = client.get_guild(guild_id)

    for each in user_data:
        for role_type in role_names:

            # assign distance role
            if role_type == 'dist':
                for limit in role_names[role_type]:
                    if each[1] > limit:
                        # assign this role
                        role_name = role_names[role_type][limit]
                        break
            # assign time role
            elif role_type == 'time':
                for limit in role_names[role_type]:
                    if each[2] > limit:
                        # assign this role
                        role_name = role_names[role_type][limit]
                        break
            # assign elev role
            elif role_type == 'elev':
                for limit in role_names[role_type]:
                    if each[3] > limit:
                        # assign this role
                        role_name = role_names[role_type][limit]
                        break
            # assign days role
            elif role_type == 'days':
                for limit in role_names[role_type]:
                    if each[4] > limit:
                        # assign this role
                        role_name = role_names[role_type][limit]
                        break
            else:
                print('Invalid role_type')

            # check that the role exists in the guild, and if not, create it
            if get(guild.roles, name=role_name):
                # role exists, continue
                pass
            else:
                await guild.create_role(name=role_name, colour=discord.Colour(0x0062ff))

            role = discord.utils.get(guild.roles, name=role_name)
            user = await client.fetch_user(each[0])
            await user.add_roles(role)
    print('Roles Updated for {}'.format(guild.name))


async def _addRoute(guild_id, activity_id, route_name, comments, maptype='roadmap', isPublic='False'):
    '''Adds route (activity information) to the routes database
    
    Inputs
        guild_id : (server_id) id number for the server who has access to the route
        activity_id : activity-specific id for a given activity
        route_name : the name of the route as defined by the person adding the route
        comments : any comments on the quality of the route (goes through sketch area, big hill, etc.)
        isPublic (optional) : defines whether other guilds can access this route (type:bool)
        '''

    # possibly create own system for making route_id(s)
    #route_id = random.randrange(0,99999999999,1)

    activity = dataRead('userActivities', ['type','distance','moving_time','elev_gain','polyline'],
                        cond_key='activity_id', cond_ineq='=', cond_value=activity_id)

    if len(activity) > 0:

        if os.path.isfile('obj/activitymaps/{}_{}.png'.format(activity_id, maptype)):
            filename = 'obj/activitymaps/{}_{}.png'.format(activity_id, maptype)
        else:
            # activity map doesnt exist so create map
            embed, filename = await _createActivity(activity_id, pfp=None, username=None, maptype='roadmap')

    
        route = {'route_id':activity_id,
                 'route_name':route_name,
                 'type':activity[0][0],
                 'filename':filename,
                 'distance':activity[0][1],
                 'average_moving_time':activity[0][2],
                 'elev_gain':activity[0][3],
                 'polyline':activity[0][4],
                 'comments':comments,
                 'guild_id':guild_id,
                 'isPublic':isPublic}

        dataEntry('routes', route)
        print('Added route:',route_name)
    else:
        print('Activity not in database')


async def _showRecommended(guild, channel_id=None, channel_name='recommended-routes'):
    '''creates and sends recommended routes to the specified channel
    
    (Needed Updates: add an average Lat/Lon value to the routes table, and have a conditional that
     the polyline average should be within a certain distance of the club center)

    Inputs
        guild_id : 
        channel_name (optional) : 
        '''
    
    guild_id = guild.id

    if channel_id != None:
        try:
            rec_channel = await client.fetch_channel(channel_id)
        except:
            return
    else:
        try:
            rec_channel = discord.utils.get(guild.channels, name=channel_name)
        except:
            #rec_channel = await guild.create_text_channel(name=channel_name)
            #print('Created Channel')
            return
    
    short_routes = dataRead('routes',
                            ['route_name','type','polyline','filename','distance','average_moving_time','elev_gain','comments'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id,
                            extra_cond='distance < 4887')
    medium_routes = dataRead('routes',
                            ['route_name','type','polyline','filename','distance','average_moving_time','elev_gain','comments'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id,
                            extra_cond='distance < 8045 AND distance > 4887')
    long_routes = dataRead('routes',
                            ['route_name','type','polyline','filename','distance','average_moving_time','elev_gain','comments'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id,
                            extra_cond='distance > 8045')

    # shuffle lists
    random.shuffle(short_routes)
    random.shuffle(medium_routes)
    random.shuffle(long_routes)

    # combine polylines into one
    now = datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")

    # create unique file ID
    map_fileId = str(now)

    #create embed
    embed = discord.Embed(title="Recommended Routes",
                            description=datetime.date.today().strftime("%m/%d"),
                            color=0x00ff00)

    poly_list = []
    if len(short_routes) > 0:
        if len(short_routes[0]) == 8:
            #print(short_routes[0])
            poly_list.append(short_routes[0][2])
            embed.add_field(name=short_routes[0][0], value=str(round(short_routes[0][4]/1609,2))+' mi', inline=True)
    if len(medium_routes) > 0:
        if len(medium_routes[0]) == 8:
            #print(medium_routes[0])
            poly_list.append(medium_routes[0][2])
            embed.add_field(name=medium_routes[0][0], value=str(round(medium_routes[0][4]/1609,2))+' mi', inline=True)
    if len(long_routes) > 0:
        if len(long_routes[0]) == 8:
            #print(long_routes[0])
            poly_list.append(long_routes[0][2])
            embed.add_field(name=long_routes[0][0], value=str(round(long_routes[0][4]/1609,2))+' mi', inline=True)
    
    if len(poly_list) == 0:
        await rec_channel.send('No Saved Routes.')
        raise NoActivitiesError('No Added Routes in Guild')

    map_im = multiPoly_toMap(map_fileId, poly_list, maptype='roadmap', m_size='640x640')
    map_filename = 'obj/recommendedmaps/{}.png'.format(map_fileId)
    
    file = discord.File(map_filename, filename="recMap.png")
    embed.set_image(url="attachment://recMap.png")

    #send embed
    await rec_channel.send(file=file, embed=embed)






# ==================================================== #
# ||||||            Client Commands             |||||| #
# ==================================================== #

@client.command()
@commands.guild_only()
async def help(ctx):
    embed = discord.Embed(title='Help',
                          description='A few commands to get you started\nPrefix is "$strava"',
                          color=0x00ff00)
    embed.add_field(name="authorize", value='authorizes the bot to use access your strava activities', inline=False)
    embed.add_field(name="unauthorize", value='removes bot access to your strava activities', inline=False)
    embed.add_field(name="myActivities", value='shows your most recent activities\n(can also use "ma")', inline=False)
    embed.add_field(name="showActivity", value='shows a map and statistics of a give activity\n(can also use "sa")', inline=False)
    embed.add_field(name="leaderboard", value='shows a leaderboard of authorized users', inline=False)
    embed.add_field(name="updateActivities", value='(Admin Only) updates the activities of all authroized users\n(can also use "ua")', inline=False)
    embed.add_field(name="dailyRecommendedRoutes", value='(Admin Only) Shows a few suggested routes\n(can also use "rec")', inline=False)
    embed.add_field(name="dailyRunningShowcase", value='(Admin Only) Shows a showcase activity from the club daily activities\n(can also use "drs")', inline=False)
    embed.add_field(name="addType", value='(Admin Only) Adds a considered activity type to userStats/leaderboards', inline=False)
    embed.add_field(name="setLeaderboard", value='(Admin Only) sets a default channel to post recurring leaderboard\n(can also use "set-l")', inline=False)
    embed.add_field(name="setShowcase", value='(Admin Only) sets a default channel to post recurring showcase\n(can also use "set-s")', inline=False)
    embed.add_field(name="setRecommended", value='(Admin Only) sets a default channel to post recurring recommended activities\n(can also use "set-r")', inline=False)
    embed.add_field(name="frequency", value='(Admin Only) sets a default frequency for leaderboard, showcase, and recommended routes posting\nin addition to the updates to user activities\n(can also use "freq")', inline=False)
    
    message = await ctx.send(embed=embed)

@client.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def changeStatus():
    '''Change Bot Status Message'''
    await client.change_presence(activity=next(status_list))
    print('Changing Status')


@client.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def ping(ctx):
    '''Ping Server (Check Latency)
    
    some extra text to test help command'''
    await ctx.send('{}ms'.format(round(client.latency*1000)))

@client.command()
@commands.guild_only()
async def authorize(ctx):
    '''Authorize User'''
    await _authorize(ctx)


@client.command()
@commands.guild_only()
@commands.has_role("Authorized")
async def unauthorize(ctx):
    '''Unauthorize Individual User'''
    discord_id = str(ctx.message.author.id)

    dataDelete('userTokens', cond_key='discord_id', cond_ineq='=', cond_value=discord_id)
    dataDelete('userStats', cond_key='discord_id', cond_ineq='=', cond_value=discord_id)
    dataDelete('userActivities', cond_key='discord_id', cond_ineq='=', cond_value=discord_id)
    dataDelete('dailyActivities', cond_key='discord_id', cond_ineq='=', cond_value=discord_id)
    dataDelete('_idTable', cond_key='discord_id', cond_ineq='=', cond_value=discord_id)

    await ctx.send('Unauthorized User: ' + ctx.message.author.name)
    
    member = await ctx.guild.fetch_member(int(discord_id))
    role = discord.utils.get(ctx.guild.roles, name='Authorized')
    await member.remove_roles(role)


@client.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def leaderboard(ctx):
    '''Create and Sends Club Leaderboard'''
    try:
        leaderboard_embed = _createLeaderboard(ctx.guild.id)
        leaderboard_msg = await ctx.send(embed=leaderboard_embed)
        await leaderboard_msg.add_reaction('????') #dist
        await leaderboard_msg.add_reaction('???') #time
        await leaderboard_msg.add_reaction('????')  #elev
        await leaderboard_msg.add_reaction('????') #days
    except:
        print('Error in creating leaderboard for guild:',ctx.guild.id)


@client.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def addRoute(ctx, *, commInput):
    '''*Not Yet Implemented*'''
    try:
        guild_id = ctx.guild.id
        if len(commInput.split('//')) == 3:
            activity_id, route_name, comments = commInput.split('//')

            #print(activity_id)
            #print(route_name)
            #print(comments)

            if activity_id.isnumeric():
                await _addRoute(guild_id, int(activity_id), route_name, comments)
                await ctx.message.add_reaction('???')
            else:
                await ctx.send('activity_id incorrect type (Expected type(int))')
                await ctx.message.add_reaction('???')
        else:
            await ctx.send('Not correct number of inputs (Expected 3, with "//" separator)')
            await ctx.message.add_reaction('???')
    except Exception as exc:
        print(exc)
        await ctx.message.add_reaction('???')


@client.command(aliases=['ma'])
@commands.guild_only()
@commands.has_role("Authorized")
async def myActivities(ctx):
    '''Show List of a Few User Activities'''
    discord_id = str(ctx.message.author.id)
    username = ctx.message.author.display_name
    try:
        embed = _myActivitiesList(username, discord_id)
        act_list = await ctx.send(embed=embed)
    except:
        await ctx.send('Error Showing Activities for user:',username)


@client.command(aliases=['sa'])
@commands.guild_only()
async def showActivity(ctx, *, activity_id):
    '''Show User Activity Details
    ($strava showActivity <activity id>)'''
    try:
        await _showActivity(ctx, activity_id)
    except:
        print('Error in showing activity:',activity_id)
    

@client.command(aliases=['drs'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def dailyRunningShowcase(ctx):
    '''Shows Some Routes Done Today'''
    try:
        guild = ctx.message.guild
        await _dailyRunningShowcase(guild, channel_id=ctx.message.channel.id)
    except:
        print('Error showing activityShowcase in guild:',ctx.guild.id)


@client.command(aliases=['rec'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def dailyRecommendedRoutes(ctx):
    '''Show Recommended Routes'''
    try:
        await _showRecommended(ctx.guild, channel_id=ctx.message.channel.id)
    except Exception as exc:
        print('Error showing recommended routes in guild:',ctx.guild.id)
        print(exc)
        if exc == 'No Added Routes in Guild':
            mes = await ctx.send(exc)


@client.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    '''Close Client (logoff bot from server)'''
    
    await ctx.send("I'm Logging Off in 4 seconds")
    print('Strava Bot Closing')
    time.sleep(4)
    await client.close()


@client.command(aliases=['ua'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def updateActivities(ctx):
    '''Updates User activities'''
    guild_id = ctx.message.guild.id
    _updateUserActivities(guild_id, num_activities=99)
    try:
        print('Attempting to update userStats')
        _updateUserStats(guild_id)
    except Exception as exce:
        await ctx.send('Could not update userStats')
        print(exce)
    try:
        print('Attempting to update daily activities')
        _updateDailyActivities(guild_id)
        await ctx.message.add_reaction('???')
    except:
        await ctx.send('Could not update dailyActivities for guild:',guild_id)


# ==================================================== #
# ||||||         Setup Client Commands          |||||| #
# ==================================================== #


@client.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def addType(ctx, *, type):
    '''Adds a given activity type to the guild (only these types will be shown)

    Inputs
        type : a given type of activity that will be considered when doing club totals/ leaderboards
    '''
    
    try:
        valid_types = ['Run','Ride','Walk','Hike','Canoe','E-Bike Ride','Handcycle','Ice Skate',
                       'Kayak','Row','Snowboard','Alpine Ski','Nordic Ski','Snowshoe',
                       'Surf','Wheelchair']

        if type not in valid_types:
            await ctx.send('Invalid Type')
            return

        guild_id = ctx.guild.id
        settings = dataRead('guildSettings',
                            ['guild_id','types',
                             'lead_id','show_id','rec_id','lat_lon_center',
                             'lead_freq','show_freq','rec_freq','update_freq'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
        #print(type)
        if len(settings) > 0:
            if type not in settings[0][1].split(','):
                updateSettings = {'guild_id':guild_id,
                                  'types':settings[0][1]+','+type,
                                  'lead_id':settings[0][2],
                                  'show_id':settings[0][3],
                                  'rec_id':settings[0][4],
                                  'lat_lon_center':settings[0][5],
                                  'lead_freq':settings[0][6],
                                  'show_freq':settings[0][7],
                                  'rec_freq':settings[0][8],
                                  'update_freq':settings[0][9]}
                dataEntry('guildSettings',updateSettings)
                await ctx.message.add_reaction('???')
                print('Add activity type:',type)
            else:
                print('type already in list')
        else:
            updateSettings = {'types':type, 'guild_id':guild_id}
            dataEntry('guildSettings',updateSettings)
            print('Add activity type:',type)
            await ctx.message.add_reaction('???')
    except:
        print('Could not addType({}) for guild: {}'.format(type, ctx.guild.id))


@client.command(aliases=['set-l'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def setLeaderboard(ctx):
    '''Sets the channel as the location for looping leaderboard updates

    Inputs
        ctx : message contrext
    '''

    try:
        guild_id = ctx.guild.id
        settings = dataRead('guildSettings',
                            ['guild_id','types',
                             'lead_id','show_id','rec_id','lat_lon_center',
                             'lead_freq','show_freq','rec_freq','update_freq'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
        if len(settings) > 0:
            print('lead_channel_id:',ctx.message.channel.id)
            updateSettings = {'guild_id':guild_id,
                                'types':settings[0][1],
                                'lead_id':ctx.message.channel.id,
                                'show_id':settings[0][3],
                                'rec_id':settings[0][4],
                                'lat_lon_center':settings[0][5],
                                'lead_freq':settings[0][6],
                                'show_freq':settings[0][7],
                                'rec_freq':settings[0][8],
                                'update_freq':settings[0][9]}
            dataEntry('guildSettings',updateSettings)
            await ctx.message.add_reaction('???')
        else:
            print('lead_channel_id:',ctx.message.channel.id)
            update_settings = {'guild_id':guild_id, 'lead_id':ctx.message.channel.id}
            dataEntry('guildSettings',updateSettings)
            await ctx.message.add_reaction('???')
    except:
        print('Could not set leaderboard channel for guild:',ctx.guild.id)

@client.command(aliases=['set-s'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def setShowcase(ctx):
    '''Sets the channel as the location for looping showcase updates

    Inputs
        ctx : message context
    '''

    try:
        guild_id = ctx.guild.id
        settings = dataRead('guildSettings',
                            ['guild_id','types',
                             'lead_id','show_id','rec_id','lat_lon_center',
                             'lead_freq','show_freq','rec_freq','update_freq'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
        if len(settings) > 0:
            print('show_channel_id:',ctx.message.channel.id)
            updateSettings = {'guild_id':settings[0][0],
                                'types':settings[0][1],
                                'lead_id':settings[0][2],
                                'show_id':ctx.message.channel.id,
                                'rec_id':settings[0][4],
                                'lat_lon_center':settings[0][5],
                                'lead_freq':settings[0][6],
                                'show_freq':settings[0][7],
                                'rec_freq':settings[0][8],
                                'update_freq':settings[0][9]}
            dataEntry('guildSettings',updateSettings)
            await ctx.message.add_reaction('???')
        else:
            print('show_channel_id:',ctx.message.channel.id)
            update_settings = {'guild_id':guild_id, 'show_id':ctx.message.channel.id}
            dataEntry('guildSettings',updateSettings)
            await ctx.message.add_reaction('???')
    except:
        print('Could not set Showcase channel for guild:',ctx.guild.id)

@client.command(aliases=['set-r'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def setRecommended(ctx):
    '''Sets the channel as the location for looping recommended updates

    Inputs
        ctx : message context
    '''

    try:
        guild_id = ctx.guild.id
        settings = dataRead('guildSettings',
                            ['guild_id','types',
                             'lead_id','show_id','rec_id','lat_lon_center',
                             'lead_freq','show_freq','rec_freq','update_freq'],
                            cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
        if len(settings) > 0:
            print('rec_channel_id:',ctx.message.channel.id)
            updateSettings = {'guild_id':settings[0][0],
                                'types':settings[0][1],
                                'lead_id':settings[0][2],
                                'show_id':settings[0][3],
                                'rec_id':ctx.message.channel.id,
                                'lat_lon_center':settings[0][5],
                                'lead_freq':settings[0][6],
                                'show_freq':settings[0][7],
                                'rec_freq':settings[0][8],
                                'update_freq':settings[0][9]}
            dataEntry('guildSettings',updateSettings)
            await ctx.message.add_reaction('???')
        else:
            print('rec_channel_id:',ctx.message.channel.id)
            update_settings = {'guild_id':guild_id, 'rec_id':ctx.message.channel.id}
            dataEntry('guildSettings',updateSettings)
            await ctx.message.add_reaction('???')
    except:
        print('Could not set recommended channel for guild:',ctx.guild.id)

@client.command()
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def center(ctx, *, lat_lon):
    '''Sets the center lattitude and longitude for the club activities

    Inputs
        lat_lon : (type:str) contains the lat and lon center of the club in the form <lat,lon>
    '''
    
    try:
        lat_range = [-90, 90]
        lon_range = [-180, 180]

        if len(lat_lon.split(',')) == 2:
            lat = float(lat_lon.split(',')[0])
            lon = float(lat_lon.split(',')[1])

            if 90 >= lat >= -90 and 180 >= lon >= -180:
                guild_id = ctx.guild.id
                settings = dataRead('guildSettings',
                                    ['guild_id','types',
                                     'lead_id','show_id','rec_id','lat_lon_center',
                                     'lead_freq','show_freq','rec_freq','update_freq'],
                                    cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
                if len(settings) > 0:
                    #print(lat_lon.strip())
                    updateSettings = {'guild_id':settings[0][0],
                                      'types':settings[0][1],
                                      'lead_id':settings[0][2],
                                      'show_id':settings[0][3],
                                      'rec_id':settings[0][4],
                                      'lat_lon_center':lat_lon.strip(),
                                      'lead_freq':settings[0][6],
                                      'show_freq':settings[0][7],
                                      'rec_freq':settings[0][8],
                                      'update_freq':settings[0][9]}
                    dataEntry('guildSettings',updateSettings)
                else:
                    #print(lat_lon.strip())
                    update_settings = {'guild_id':guild_id, 'lat_lon_center':lat_lon.strip()}
                    dataEntry('guildSettings',updateSettings)
        else:
            await ctx.send('not valid <lat,lon>')
            print('not valid lat_lon')
    except:
        print('Could not set lat/lon center for guild:',ctx.guild.id)


@client.command(aliases=['freq'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def frequency(ctx, *, frequency):
    '''Sets the update frequency for leaderboard, showcase, recommended_routes, and updateActivities

    Inputs
        frequency : (type:str) contains the update frequencies of the various posts <a,b,c,d>
    '''

    try:
        guild_id = ctx.guild.id

        if len(frequency.split(',')) == 4:
            if all(x.strip().isnumeric() for x in frequency.split(',')):
                if all(1 <= int(x) <= 24 for x in frequency.split(',')):
                    lead_freq = int(frequency.split(',')[0])
                    show_freq = int(frequency.split(',')[1])
                    rec_freq = int(frequency.split(',')[2])
                    update_freq = int(frequency.split(',')[3])
            
                    settings = dataRead('guildSettings',
                                        ['guild_id','types',
                                         'lead_id','show_id','rec_id','lat_lon_center',
                                         'lead_freq','show_freq','rec_freq','update_freq'],
                                        cond_key='guild_id', cond_ineq='=', cond_value=guild_id)
                    if len(settings) > 0:
                        #print(frequency)
                        updateSettings = {'guild_id':settings[0][0],
                                          'types':settings[0][1],
                                          'lead_id':settings[0][2],
                                          'show_id':settings[0][3],
                                          'rec_id':settings[0][4],
                                          'lat_lon_center':settings[0][5],
                                          'lead_freq':lead_freq,
                                          'show_freq':show_freq,
                                          'rec_freq':rec_freq,
                                          'update_freq':update_freq}
                        dataEntry('guildSettings',updateSettings)
                        await ctx.message.add_reaction('???')
                    else:
                        #print(frequency)
                        updateSettings = {'guild_id':guild_id, 'lead_freq':lead_freq, 'show_freq':show_freq,
                                          'rec_freq':rec_freq, 'update_freq':update_freq}
                        dataEntry('guildSettings',updateSettings)
                        await ctx.message.add_reaction('???')
                else:
                    await ctx.send('frequency not in range [1,24]')
            else:
                await ctx.send('frequency is not type(int)')
        else:
            await ctx.send('incorrect number of frequencies (expected:4)')
    except Exception as exc:
        print(exc)
        print('Could not set looping frequency for guild:',ctx.guild.id)



# ==================================================== #
# ||||||             Client Events              |||||| #
# ==================================================== #

# On Ready
@client.event
async def on_ready():
    _removeExpiredTokens()
    hourLoop.start()
    print('\nBot is Online')
    print('\nReady For Other Operations:')


# On Reaction Add
@client.event
async def on_raw_reaction_add(payload):
    if payload.guild_id != None:
        guild_id = payload.guild_id
        await _checkIsLeaderboard(guild_id, payload)
    else:
        print('Message not in guild')



# ==================================================== #
# ||||||              Client Tasks              |||||| #
# ==================================================== #

@tasks.loop(seconds=3600)
async def update_status():
    '''Change bot status'''
    await client.change_presence(activity=next(status_list))
    print('Changing Status')


@tasks.loop(seconds=3600)
async def hourLoop():
    '''hourly bot updates'''
    print('\nSTARTING HOURLY UPDATES:')
    settings = dataRead('guildSettings',
                        ['guild_id','types', 'lead_id','show_id','rec_id','lat_lon_center',
                        'lead_freq','show_freq','rec_freq','update_freq'])
    try:
        iter_hour += 1
        if iter_hour > 24:
            iter_hour = 1
    except:
        iter_hour = int(datetime.datetime.now().strftime("%H"))

    try:
        if cur_month != datetime.datetime.now().strftime("%m"):
            cur_month = datetime.datetime.now().strftime("%m")
            # clear user stats
            discord_and_guild_ids = dataRead('userStats',['discord_id','guild_id'])
            dataDelete('userStats')
            print('deleted userStats:',len(discord_and_guild_ids))
            for each in discord_and_guild_ids:
                initStats = {'discord_id' : each[0],
                             'dist':0,
                             'time':0,
                             'elev':0,
                             'days':0,
                             'guild_id':each[1]}
                dataEntry('userStats',initStats)
            # clear roles
            for member in client.get_all_members():
                for type in role_names:
                    for limit in role_names[type]:
                        try:
                            role = discord.utils.get(member.guild.roles, name=role_names[type][limit])
                            await member.remove_roles([role],reason='monthly userStats reset')
                            print('Removed Roles. . .')
                        except:
                            print('Error removing role ({}) from {} in guild {} (id:{})'.format(role_names[type][limit],
                                                                                        member.display_name,
                                                                                        member.guild.name, member.guild.id))
    except:
        cur_month = datetime.datetime.now().strftime("%m")



    if iter_hour % 24 == 0:
        dataDelete('dailyActivities')


    #print(settings)
    if len(settings) > 0:
        for each in settings:
            #print(each)
            guild_id = each[0]

            # update userActivities
            if each[9] != None and each[9] != 'None':
                try:
                    if iter_hour % each[9] == 0:
                        print('updating activities')
                        _updateUserActivities(guild_id, num_activities=99)
                        _updateUserStats(guild_id)
                        _updateDailyActivities(guild_id)
                except:
                    print('Error Updating User Activities')

            # send recommendedActivities
            if each[8] != None and each[4] != None and each[8] != 'None' and each[4] != 'None':
                if iter_hour % each[8] == 0:
                    try:
                        print('posting recommended activities')
                        rec_channel = await client.fetch_channel(each[4])
                        guild = await client.fetch_guild(guild_id)
                        await _showRecommended(guild, channel_id=each[4])
                    except Exception as exc:
                        print(exc)
                        print('Error in Sending Recommended Activities')
            else:
                print('recommendedActivities frequency or channel_id not defined')

            # send activity showcase
            if each[7] != None and each[3] != None and each[7] != 'None' and each[3] != 'None':
                if iter_hour % each[7] == 0:
                    guild = await client.fetch_guild(guild_id)
                    try:
                        print('posting daily showcase')
                        show_channel = await client.fetch_channel(each[3])
                        await _dailyRunningShowcase(guild, channel_id=each[3])
                    except:
                        print('Error in Sending Showcase Activities')
            else:
                print('showcase frequency or channel_id not defined')

            # send activity leaderboard
            if each[6] != None and each[2] != None and each[6] != 'None' and each[2] != 'None':
                if iter_hour % each[6] == 0:
                    guild = await client.fetch_guild(guild_id)
                    try:
                        print('posting leaderboard')
                        leaderboard_channel = await client.fetch_channel(each[2])
                        leaderboard_embed = _createLeaderboard(guild.id)
                        leaderboard_msg = await leaderboard_channel.send(embed=leaderboard_embed)
                        await leaderboard_msg.add_reaction('????') #dist
                        await leaderboard_msg.add_reaction('???') #time
                        await leaderboard_msg.add_reaction('????')  #elev
                        await leaderboard_msg.add_reaction('????') #days
                    except:
                        print('Error in Sending Leaderboard')
            else:
                print('leaderboard frequency or channel_id not defined')

            







# ==================================================== #
# ||||||               Client Run               |||||| #
# ==================================================== #


client.run(bot_token)
