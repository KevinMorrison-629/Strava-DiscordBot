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
import pickle
import json
import urllib3

import polyline

import aiohttp


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



# ============================================================================ #
# |||||||||||||||||||||||       Helper Functions       ||||||||||||||||||||||| #
# ============================================================================ #



def save_asPickle(filename, dict_var):
    ''''''
    with open('obj/'+filename+'.pkl','wb') as f:
        pickle.dump(dict_var, f, pickle.HIGHEST_PROTOCOL)
    print('file saved as: {}'.format(filename))


def load_asPickle(filename):
    ''''''
    with open('obj/'+filename+'.pkl','rb') as f:
        dict_var = pickle.load(f)
        print('loaded: {}'.format(filename))
        return dict_var


#async def asynPost(url, payload):
    #''''''
    #with aiohttp.ClientSession() as session:
        #async with session.post(url, data=payload, verify=False) as response:
            #return await response.json()

#async def asynGet(url, headers=None, params=None):
    #''''''
    #with aiohttp.ClientSession() as session:
        #async with session.get(url, headers=headers, params=params) as response:
            #return await response.json()


def poly_toMap(activity_id, poly, maptype='roadmap'):
    ''''''
    lat_lon = polyline.decode(poly)
    
    lat_avg = sum(pair[0] for pair in lat_lon) / len(lat_lon)
    lon_avg = sum(pair[1] for pair in lat_lon) / len(lat_lon)

    url = "https://maps.googleapis.com/maps/api/staticmap?"
    m_size = '640x640'
    param = {'size': m_size, 'maptype': maptype, 'path':'enc:{}'.format(poly), 'key':g_api_key}
    # maptype: one of ['roadmap', 'satellite', 'hybrid', 'terrain']
    # optional innclude style=feature:element, with options including [landscape.natural, road.local]
    
    #map_r = await asynGet(url, headers=None, params=param)
    map_r = requests.get(url, headers=None, params=param)
    
    with open('obj/activitymaps/{}_{}.png'.format(activity_id, maptype), 'wb') as f:
        f.write(map_r.content)
    #print('\nCreated Map\n')
    return map_r



# ============================================================================ #
# |||||||||||||||||||||||          Constants           ||||||||||||||||||||||| #
# ============================================================================ #



month_year = datetime.datetime.now().strftime('%B')+' '+str(datetime.datetime.now().year)

month_dict = {'January':1, 'February':2, }

user_base_stats = {'monthly_dist':0,
                   'monthly_time':0,
                   'monthly_elev':0,
                   'monthly_days':0,
                   'day_list':[],
                   'dist_level':0,
                   'time_level':0,
                   'elev_level':0,
                   'days_level':0}

level_limits = {'dist':[200*1609, 150*1609, 100*1609, 50*1609, 10*1609, 0],
                'time':[96000, 65000, 40000, 20000, 7200, 0],
                'elev':[10647, 7500, 5000, 2000, 500, 0],
                'days':[20, 16, 12, 8, 4, 0]}

status_list = cycle([discord.Game("Tag with my Imaginary Friends"),
                     discord.Game('in the Sand'),
                     discord.Activity(type=discord.ActivityType.watching, name='a FlightMech Lecture'),
                     discord.Activity(type=discord.ActivityType.watching, name='a video on the theory of walking'),
                     discord.Activity(type=discord.ActivityType.listening, name='to silence'),
                     discord.Activity(type=discord.ActivityType.listening, name='to some music')])

role_names = {'dist':{0:'Distance Leader', 26:'Marathoner', 50:'UltraMarathoner'},
              'time':{0:'Time Leader',10:'10-Hour Lim',24:'24-hour Lim'},
              'elev':{0:'Elevation Leader',5280:'Mountain Climber',13700:'Everest Summiter'},
              'days':{0:'Days Leader',5:'Hobby Runner',15:'Athlete',28:'Might as well join the XC team'}}

# ============================================================================ #
# |||||||||||||||||||||||          Load Data           ||||||||||||||||||||||| #
# ============================================================================ #


# the following 6 values are constants constants
#bot_token = None
#client_secret = None
#g_api_key = None
#client_id = '67096'
#club_id = 551859
#strava_bot_id = 852249770114154546

user_tokens = {}
club_user_stats = {}

user_activities = {}
daily_activities = []
routes = {}
roles = {}
club_totals = {}


# load user_tokens
try:
    user_tokens = load_asPickle('user_tokens')
except EOFError:
    print('Could Not Load File (user_tokens): Ran out of input')
except:
    print('Could not load file (user_tokens)')


# load club_user_stats
try:
    club_user_stats = load_asPickle('club_user_stats')
except EOFError:
    print('Could Not Load File (club_user_stats): Ran out of input')
except:
    print('Could not load file (club_user_stats)')


# load personal_info
# this is a pickle file that contains a dictionary with these values.
# If you want to use this implementation, you will need to create a pickle file
# containing a dictionary with values for these variables
try:
    personal_info = load_asPickle('personal_info')
    bot_token = personal_info['bot_token']
    client_secret = personal_info['client_secret']
    g_api_key = personal_info['g_api_key']
    client_id = personal_info['client_id']
    club_id = personal_info['club_id']
    bot_id = personal_info['bot_id']
    guild_id = personal_info['guild_id']
except EOFError:
    print('Could Not Load File (personal_info): Ran out of input')
except:
    print('Could not load file (personal_info)')


# load user_activities
try:
    user_activities = load_asPickle('user_activities')
except EOFError:
    print('Could Not Load File (user_activities): Ran out of input')
except:
    print('Could not load file (user_activities)')


# load daily_activities
try:
    daily_activities = load_asPickle('daily_activities')
except EOFError:
    print('Could Not Load File (daily_activities): Ran out of input')
except:
    print('Could not load file (daily_activities)')


# load routes
try:
    routes = load_asPickle('routes')
except EOFError:
    print('Could Not Load File (routes): Ran out of input')
except:
    print('Could not load file (routes)')


# load roles
try:
    roles = load_asPickle('roles')
except EOFError:
    print('Could Not Load File (roles): Ran out of input')
except:
    print('Could not load file (roles)')


# load club_totals
try:
    club_totals = load_asPickle('club_totals')
except EOFError:
    print('Could Not Load File (club_totals): Ran out of input')
except:
    print('Could not load file (club_totals)')



# ============================================================================ #
# |||||||||||||||||||||||    Discord Bot Functions     ||||||||||||||||||||||| #
# ============================================================================ #



# define client and command prefix
client = commands.Bot(command_prefix = '$strava ')


# ==================================================== #
# ||||||        Discord Helper Functions        |||||| #
# ==================================================== #



# Remove Expired Tokens
def _removeExpiredTokens():
    ''''''
    if len(user_tokens) > 0:
        rem_list = []
        for user in user_tokens:             
            if user_tokens[user]['expires_at'] < time.time():
                removed = user_tokens[user].pop()
                rem_list.append(removed)
        print(str(len(rem_list))+ ' users were removed from authorization list')
        return


# Refresh Access Tokens
def _updateAccessTokens():
    ''''''
    token_url = 'https://www.strava.com/oauth/token'
    
    if len(user_tokens) > 0:
        for user in user_tokens:
            refresh_token = user_tokens[user]['refresh_token']
            refreshToken_payload = {'client_id' : client_id,
                                    'client_secret' : client_secret,
                                    'refresh_token' : refresh_token,
                                    'grant_type' : 'refresh_token',
                                    'f' : 'json'}
            #res = await asynPost(token_url, payload=refreshToken_payload)
            res = requests.post(token_url, data=refreshToken_payload, verify=False).json()
            
            access_token = res['access_token']
            refresh_token = res['refresh_token']
            expires_at = res['expires_at']
            
            user_tokens[user]['refresh_token'] = refresh_token
            user_tokens[user]['access_token'] = access_token
            user_tokens[user]['expires_at'] = expires_at
            
        save_asPickle('user_tokens', user_tokens)    
        return
    else:
        print('No Authorized Users')


# Update User Activities
def _updateUserActivities(num_activities=15):
    ''''''
    if len(user_tokens) > 0:
        for user in user_tokens:
            access_token = user_tokens[user]['access_token']
            ua_url = 'https://www.strava.com/api/v3/athlete/activities'
            header = {'Authorization': 'Bearer ' + access_token}
            param = {'per_page': num_activities, 'page':1}
            
            #activities = await asynGet(ua_url, headers=header, params=param)
            activities = requests.get(ua_url, headers=header, params=param).json()
            #print(activities)
            
            if user not in user_activities:
                user_activities[user] = {}
            if len(activities) > 0:
                for each in activities:
                    activity_id = each['id']
                    if activity_id not in user_activities[user]:
                        #print(each['type'])
                        if each['type'] == 'Run':
                            user_activities[user][activity_id] = {'name':each['name'],
                                                                  'distance':each['distance'],
                                                                  'moving_time':each['moving_time'],
                                                                  'total_elevation_gain':each['total_elevation_gain'],
                                                                  'type':each['type'],
                                                                  'start_date_local':each['start_date_local'],
                                                                  'summary_polyline':each['map']['summary_polyline'],
                                                                  'id':activity_id,
                                                                  'discord_id':user
                                                                  }
                            if user not in club_user_stats:
                                club_user_stats[user] = user_base_stats.copy()
                            
                            
                            def check_month(date):
                                cur_date = datetime.datetime.now()
                                #print(date,' not same month as ',cur_date)
                                return str(cur_date.month) == date.split('-')[1].lstrip('0') and str(cur_date.year) == date.split('-')[0].lstrip('0')
                            
                            def check_day(date):
                                cur_date = datetime.datetime.now()
                                return str(cur_date.month) == date.split('-')[1].lstrip('0') and str(cur_date.year) == date.split('-')[0].lstrip('0') and str(cur_date.day) == date.split('T')[0].split('-')[-1].lstrip('0')
                            
                            
                            if check_month(each['start_date_local']):
                                club_user_stats[user]['monthly_dist'] += each['distance']
                                club_user_stats[user]['monthly_time'] += each['moving_time']
                                club_user_stats[user]['monthly_elev'] += each['total_elevation_gain']
                                
                                day_num = int(each['start_date_local'].split('T')[0].split('-')[-1])
                                if day_num not in club_user_stats[user]['day_list']:
                                    club_user_stats[user]['monthly_days'] += 1
                                    club_user_stats[user]['day_list'].append(day_num)
                            
                            if check_day(each['start_date_local']):
                                daily_activities.insert(0, user_activities[user][activity_id])
                                if len(daily_activities) > 15:
                                    removed_activity = daily_activities.pop()
                                    print('Removed:', removed_activity['name'])
                                
        save_asPickle('daily_activities', daily_activities)
        save_asPickle('user_activities', user_activities)
        save_asPickle('club_user_stats', club_user_stats)
    else:
        print('No Authorized Users')


# Create Activity Embed
async def _createActivity(activity, pfp, username):
    ''''''
    activity_id = activity['id']
    activity_map = activity['summary_polyline']
    discord_id = activity['discord_id']
    maptype = 'roadmap'
    
    #map_im = await poly_toMap(g_api_key, activity_id, activity_map, maptype=maptype)
    map_im = poly_toMap(activity_id, activity_map, maptype=maptype)
    
    start_date = activity['start_date_local'].split('T')[0].split('-')
    start_time = activity['start_date_local'].split('T')[1].split(':')
    
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
    
    embed = discord.Embed(title=activity['name'],
                          description=desc_time,
                          color=0x00ff00)
    distance = round(activity['distance'] / 1609, 2)
    time = str(datetime.timedelta(seconds=activity['moving_time']))
    elev_gain = round(activity['total_elevation_gain'] * 3.28, 2)
    
    embed.set_author(name= str(username) +' mapped a run!', icon_url=pfp)
    
    embed.add_field(name="Distance", value=str(distance)+' mi', inline=True)
    embed.add_field(name="Time", value=str(time), inline=True)
    embed.add_field(name="Elev Gain", value=str(elev_gain)+' ft', inline=True)
    
    im_file = discord.File('obj/activitymaps/{}_{}.png'.format(activity_id, maptype))
    embed.set_image(url='attachment://obj/activitymaps/{}_{}.png'.format(activity_id, maptype))

    return embed, im_file


# Create Leaderboard
def _createLeaderboard(sort='monthly_dist'):
    ''''''
    if len(club_user_stats) > 0:
        embed_update = discord.Embed(title='Activities Leaderboard',
                                  description=datetime.datetime.now().strftime('%B')+' '+str(datetime.datetime.now().year),
                                  color=0x00ff00)
        
        sorted_leaderboard = list(sorted(club_user_stats.items(), key = lambda x: x[1][sort], reverse=True))
        
        rank, name, dist, time, elev, days = '', '', '', '', '', ''
        iter_val = 0
        
        for each in sorted_leaderboard:
            iter_val += 1
            rank += '#{}'.format(iter_val) + '\n'
            
            username = user_tokens[sorted_leaderboard[iter_val-1][0]]['username']
            
            name += username + '\n'
            dist += str(round(each[1]['monthly_dist']/1609, 2)) + '\n'
            time += str(round(each[1]['monthly_time']/3600,2)) + '\n'
            elev += str(round(each[1]['monthly_elev'],2)) + '\n'
            days += str(round(each[1]['monthly_days'],2)) + '\n'
        
        embed_update.add_field(name='Rank', value=rank, inline=True)
        embed_update.add_field(name='Name', value=name, inline=True)
        
        if sort == 'monthly_dist':
            embed_update.add_field(name='Distance (mi)', value=dist, inline=True)
        elif sort == 'monthly_time':
            embed_update.add_field(name='Time (hr)', value=time, inline=True)
        elif sort == 'monthly_elev':
            embed_update.add_field(name='Elev Gain (ft)', value=elev, inline=True)
        elif sort == 'monthly_days':
            embed_update.add_field(name='Active Days', value=days, inline=True)            
        else:
            raise ValueError('Bad sort input')
        
        return embed_update
    else:
        print('No User Data')


async def _checkIsLeaderboard(payload):
    ''''''
    if payload.event_type == 'REACTION_ADD':
        if payload.user_id != bot_id:
            channel = client.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            #user = client.get_user(payload.user_id)
            
            if message.author.id == bot_id:
                if len(message.embeds) > 0:
                    if 'Activities Leaderboard' in message.embeds[0].to_dict()['title']:
                        #print(message.embeds[0].to_dict())
                        if str(payload.emoji) == '📏':
                            print('Reacted with Dist')
                            new_embed = _createLeaderboard(sort='monthly_dist')
                        elif str(payload.emoji) == '⌚':
                            print('Reacted with Time')
                            new_embed = _createLeaderboard(sort='monthly_time')
                        elif str(payload.emoji) == '🪜':
                            print('Reacted with Elev')
                            new_embed = _createLeaderboard(sort='monthly_elev')
                        elif str(payload.emoji) == '🗓':
                            print('Reacted with Days')
                            new_embed = _createLeaderboard(sort='monthly_days')
                        else:
                            print('Reacted with some random emoji, idk.')
                            return
                        
                        react_emoji = payload.emoji
                        
                        await message.clear_reactions()
                        await message.add_reaction('📏') #dist
                        await message.add_reaction('⌚') #time
                        await message.add_reaction('🪜')  #elev
                        await message.add_reaction('🗓')  #elev
                        
                        await message.edit(embed = new_embed)
                    else:
                        print('Not Leaderboard Message')

async def _authorize(ctx):
    ''''''
    discord_id = str(ctx.message.author.id)
    scope = 'activity:read_all'
    redirect_uri = 'https://localhost/exchange_token'
    auth_url = 'https://www.strava.com/oauth/authorize'
    token_url = 'https://www.strava.com/oauth/token'
    
    authorization_url = '{0}?client_id={1}&response_type=code&redirect_uri={2}&approval_prompt=force&scope={3}'
    authorization_url = authorization_url.format(auth_url, client_id, redirect_uri, scope)
    
    await ctx.send('Please go to \n{} \nand authorize access.'.format(authorization_url))
    
    def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel and 'https://localhost/exchange_token' in msg.content
    
    try:
        await ctx.send('[Please Send the full callback URL]: ')
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
    
    #res = await asynPost(token_url, payload=payload)
    res = requests.post(token_url, data=payload, verify=False).json()
    
    #print('\n')
    #print(res)
    #print('\n')
    
    user_accessToken = res['access_token']
    user_refreshToken = res['refresh_token']
    user_id = res['athlete']['id']
    username = ctx.message.author.display_name
    expires_at = res['expires_at']
    
    if type(user_accessToken) == str and type(user_refreshToken) == str:
        user_tokens[discord_id] = {'access_token':user_accessToken,
                                   'refresh_token':user_refreshToken, 
                                   'authorization_code':auth_code,
                                   'id':user_id,
                                   'username':username,
                                   'expires_at':expires_at}
        await ctx.send('User Authorized! ({})'.format(ctx.author.display_name))
    else:
        await ctx.send('ERROR: User not Authorized. Please try again.')
        print('Error Authorizing User. Tokens returned not type(str)')
    
    save_asPickle('user_tokens', user_tokens)
    print('AuthorizeUser Command Completed')    


def _myActivitiesList(username, disc_id):
    ''''''
    activities = user_activities[disc_id]
    sorted_activities = list(sorted(activities.items(), key = lambda x: x[1]['start_date_local'], reverse=True))
    
    embed = discord.Embed(title="{}'s Activities".format(username),
                                  color=0x00ff00)
    name, dist, act_id = '', '', ''
    iter_val = 0
    
    for each in sorted_activities:
        #print(each)
        if iter_val < 8 or iter_val >= len(sorted_activities)-1:
            iter_val += 1            
            name += each[1]['name'] + '\n'
            dist += str(round(each[1]['distance']/1609, 2)) + '\n'
            act_id += str(each[0]) + '\n'  
    
    embed.add_field(name='Name', value=name, inline=True)
    embed.add_field(name='Dist (mi)', value=dist, inline=True)
    embed.add_field(name='Activity ID', value=act_id, inline=True)
    
    return embed


async def _showActivity(ctx, discord_id, username, pfp, activity_id):
    ''''''
    if discord_id in user_activities:
        if activity_id in user_activities[discord_id]:
            activity = user_activities[str(discord_id)][activity_id]
            
            embed, im_file = await _createActivity(activity, pfp, username)
            message = await ctx.send(embed=embed, file=im_file)
            return message
        else:
            ctx.send('Not Valid Activity ID, please try again')
    else:
        ctx.send('User has no Activities')


async def _dailyRunningShowcase(guild):
    try:
        showcase_channel = discord.utils.get(guild.channels, name='daily-activities')
    except:
        showcase_channel = await guild.create_text_channel(name='daily-activities')
        print('Created Channel')
        
    if len(daily_activities) > 0:
        for i in range(3):
            if len(daily_activities) > 0:
                random.shuffle(daily_activities)
                activity = daily_activities.pop()
                
                discord_id = activity['discord_id']
                user = await client.fetch_user(discord_id)
                pfp = user.avatar_url
                username = user.display_name
                
                embed, im_file = await _createActivity(activity, pfp, username)                
                message = await showcase_channel.send(embed=embed, file=im_file)
            else:
                showcase_channel.send('No Daily Activities')
        save_asPickle('daily_activities', daily_activities)
    else:
        await showcase_channel.send('No Daily Activities')


async def _createRoles(guild):
    ''''''
    roles_list = ['Marathoner','Mountain-Climber']
    guild_roles = guild.roles
    
    guild_role_names = []
    for each in guild_roles:
        guild_role_names.append(each.name)

    for each in roles_list:
        if not each in guild_role_names:
            await guild.create_role(name=each, hoist=True)
    if not 'Authorized' in guild_role_names:
        await guild.create_role(name='Authorized')

async def _createChannels(guild):
    text_channels = ['daily-activities','leaderboard','recommended-routes']
    channels = guild.channels
    channels_list = []
    for each in channels:
        channels_list.append(each.name)
    for each in text_channels:
        if each not in channels_list:
            await guild.create_text_channel(name=each)





def _addRoute():
    ''''''
    pass








# ==================================================== #
# ||||||            Client Commands             |||||| #
# ==================================================== #



@client.command()
async def changeStatus():
    '''Change Bot Status Message'''
    await client.change_presence(activity=next(status_list))
    print('Changing Status')

@client.command()
async def ping(ctx):
    '''Ping Server (Check Latency)
    
    some extra text to test help command'''
    await ctx.send('{}ms'.format(round(client.latency*1000)))

@client.command()
async def clear(ctx, amount=5):
    '''Clear Messages (removes last 4 messages)'''
    await ctx.channel.purge(limit=amount)

@client.command()
async def helper(ctx):
    '''Sends a helpful message containing common commands'''
    embed = discord.Embed(title='Helper',
                          description='use *$strava* to prefix comamnds',
                          color=0x00ff00)
    embed.add_field(name='changeStatus', value='Cycles through available bot statuses', inline=False)
    embed.add_field(name='ping', value='Check bot latency', inline=False)
    embed.add_field(name='clear', value='Clears previous 4 messages', inline=False)
    embed.add_field(name='helper', value="***You're using this right now***", inline=False)
    embed.add_field(name='authorize', value='Authorize bot to use your strava data\n(activity information)', inline=False)
    embed.add_field(name='unauthorize', value='Remove bot authorization to use your strava information', inline=False)
    embed.add_field(name='leaderboard', value='Shows leaderboard for club activities', inline=False)
    embed.add_field(name='addRoute', value='*NOT IMPLEMENTED*', inline=False)
    embed.add_field(name='showActivities', value='NOT IMPLEMENTED', inline=False)
    await ctx.send(embed=embed)

@client.command()
async def authorize(ctx):
    '''Authorize User'''
    await _authorize(ctx)

@client.command()
async def unauthorize(ctx):
    '''Unauthorize Individual User'''
    discord_id = str(ctx.message.author.id)
    if discord_id in user_tokens:
        user_tokens[discord_id].pop()
        await ctx.send('Unauthorized User: ' + ctx.message.author.name)
        save_asPickle('user_tokens', user_tokens)
    else:
        await ctx.send('User is not Authorized')
    
@client.command()
async def leaderboard(ctx):
    '''Create and Sends Club Leaderboard'''
    if len(club_user_stats) > 0:
        leaderboard_embed = _createLeaderboard()
        leaderboard_msg = await ctx.send(embed=leaderboard_embed)
        await leaderboard_msg.add_reaction('📏') #dist
        await leaderboard_msg.add_reaction('⌚') #time
        await leaderboard_msg.add_reaction('🪜')  #elev
        await leaderboard_msg.add_reaction('🗓') #days


@client.command()
async def addRoute(ctx):
    '''*Not Yet Implemented*'''
    ctx.send('Not Implemented Yet')
    pass

@client.command()
async def myActivities(ctx):
    '''Show List of a Few User Activities'''
    discord_id = str(ctx.message.author.id)
    if discord_id in user_activities:
        if len(user_activities[discord_id]) > 0:
            embed = _myActivitiesList(ctx.message.author.display_name, str(discord_id))
            act_list = await ctx.send(embed=embed)
        else:
            ctx.send('No User Activities')
    else:
        ctx.send('No User Activities')

@client.command()
async def showActivity(ctx, *, activity_id):
    '''Show User Activity Details
    
    
    ($strava showActivity <activity id>)'''
    if len(user_activities) > 0:
        for each in user_activities:
            if len(user_activities[each]) > 0:
                for activity in user_activities[each]:
                    if str(activity) == activity_id:
                        user = await client.fetch_user(each)
                        user_name = user.display_name
                        user_pfp = user.avatar_url
                        discord_id = each
                        message = await _showActivity(ctx, discord_id, user_name, user_pfp, int(activity_id))
                        return
    await ctx.send('Could Not Find Activity With This ID')



@client.command()
async def dailyRunningShowcase(ctx):
    '''Shows Some Routes Done Today'''
    guild = ctx.message.guild
    await _dailyRunningShowcase(guild)

@client.command()
async def dailyRecommendedRoutes():
    '''*Not Yet Implemented*'''
    pass

@client.command()
async def close(ctx):
    '''Close Client (logoff bot from server)'''
    #save_asPickle('user_tokens', user_tokens)
    #save_asPickle('club_user_stats', club_user_stats)
    #save_asPickle('user_activities', user_activities)
    #save_asPickle('daily_activities', daily_activities)
    #save_asPickle('routes', routes)
    #save_asPickle('roles', roles)
    #save_asPickle('club_totals', club_totals)
    
    await ctx.send("I'm Logging Off in 5 seconds")
    print('Strava Bot Closing')
    time.sleep(10)
    await client.close()



@client.command()
async def startLoopingTasks(ctx):
    '''*Not Yet Implemented*'''
    pass



@client.command()
async def updateActivities(ctx):
    '''Updates User activities'''
    _updateUserActivities()
    

@client.command()
async def setup(ctx):
    '''Sets up RRC Strava Bot
    
    Creates Roles, Channels, etc to set up bot'''
    guild_id = ctx.guild.id
    guild = ctx.guild
    await _createRoles(guild)
    await _createChannels(guild)
    personal_info['guild_id'] = guild_id
    save_asPickle('personal_info', personal_info)



# ==================================================== #
# ||||||             Client Events              |||||| #
# ==================================================== #


# On Ready
@client.event
async def on_ready():
    _removeExpiredTokens()
    print('\nBot is Online')
    guild = client.get_guild(guild_id)
    
    update_monthly.start()
    update_daily.start(guild)
    update_8Hour.start()
    update_3Hour.start()
    print('\nReady For Other Operations:')

# On Reaction Add
@client.event
async def on_raw_reaction_add(payload):
    await _checkIsLeaderboard(payload)



# ==================================================== #
# ||||||              Client Tasks              |||||| #
# ==================================================== #






# Monthly Update
@tasks.loop(hours=24)
async def update_monthly():
    
    try:
        cur_month
    except NameError:
        cur_month = datetime.datetime.now().month    
    
    if datetime.datetime.now().month != cur_month:
        cur_month = datetime.datetime.now().month
        if len(club_user_stats) > 0:
            for each in club_user_stats:
                club_user_stats[each] = user_base_stats.copy()
        save_asPickle('club_user_stats', club_user_stats)

# Daily Update
@tasks.loop(hours=24)
async def update_daily(guild):
    print('Update Daily')
    try:
        if len(daily_activities) > 0:
            _dailyRunningShowcase(guild)
        daily_activities = []
    except NameError:
        print('daily_activities variable doesnt exist yet')
        daily_activities = []


# 8-Hour Updates
@tasks.loop(hours=8)
async def update_8Hour():
    _updateUserActivities()

# 3-Hour Updates
@tasks.loop(hours=3)
async def update_3Hour():
    _updateAccessTokens()




# Change Bot Status
@tasks.loop(seconds=3600)
async def update_status():
    '''Cahnge'''
    await client.change_presence(activity=next(status_list))
    print('Changing Status')


## Refresh Access Tokens
#@tasks.loop(seconds=3600)
#async def update_tokens():
    #''''''
    #pass

## Update User Activities
#@tasks.loop(seconds=3600)
#async def update_activities():
    #''''''
    #pass

## Update User Stats
#@tasks.loop(seconds=3600)
#async def update_stats():
    #''''''
    #pass

## Update User Roles
#@tasks.loop(seconds=3600)
#async def update_roles():
    #''''''
    #pass



# ==================================================== #
# ||||||               Client Run               |||||| #
# ==================================================== #


client.run(bot_token)