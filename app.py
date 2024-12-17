from twitchio.ext import commands
from pymongo import MongoClient
import time
import requests
from datetime import datetime
import asyncio
# import logging
#
# logging.basicConfig(level=logging.DEBUG)

CLIENT_ID = 'y405cufg37e8l2tmh6u9ruwl9011ce'
CLIENT_SECRET = 'y3cilrhl2oe7tjhxillq4izorunnn7'

TARGET_CHANNEL = 'ozhunt'
SPECIAL_KEYWORD = '!giveall'
KEYWORD = '!release'



client = MongoClient('mongodb+srv://Bamidele1:1631324de@mycluster.vffurcu.mongodb.net/?retryWrites=true&w=majority')
db = client['test']
viewers_collection = db['watch_time']

user_sessions = {}

# Twitch Bot Class
class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token="oauth:l168k48nde6xlhvs3yjhp24a3beqm8",
            prefix="!",
            initial_channels=[TARGET_CHANNEL]
        )

    async def event_ready(self):
        print(f"Bot is online! Connected to {TARGET_CHANNEL}")

    async def event_usernotice_subscription(self, metadata):
        """Handle subscription or re-subscription events."""
        # Extract user and channel information
        subscriber = metadata.user.name
        channel_name = metadata.channel.name
        tier = metadata.tier

        # Print subscription details
        print(f"New subscription! User: {subscriber}, Channel: {channel_name}, Tier: {tier}")

        # Reward the subscriber
        await self.reward_viewer(subscriber)

        # Announce in the chat
        channel_obj = self.get_channel(channel_name)
        if channel_obj:
            await channel_obj.send(f"🎉 Thank you {subscriber} for subscribing at Tier {tier}! You've been rewarded with 1 Oz Coin! 🎉")

    async def event_message(self, message):
        if message.echo:
            return  # Ignore messages sent by the bot itself

        username = message.author.name
        now = datetime.utcnow()

        is_streamer_live = await self.is_user_live(TARGET_CHANNEL)
        if is_streamer_live:
            viewer = viewers_collection.find_one({"username": username})
            if not viewer:
                viewers_collection.insert_one({
                    "username": username,
                    "first_seen": now,
                    "last_seen": now,
                    "total_time": 0,
                    "Points": 0,
                    "cryptoType": "",
                    "address": "",
                    "Casino-Name": "",
                    "is_logged_in": False
                })
                print(f"New user {username} added to the database.")
            else:
                time_spent = (now - viewer["last_seen"]).total_seconds()
                if time_spent >= 21600:
                    pass
                else:
                    new_total_time = viewer["total_time"] + time_spent
                    new_points = new_total_time // 3600


                    viewers_collection.update_one(
                        {"username": username},
                        {
                            "$set": {
                                "last_seen": now,
                                "total_time": new_total_time,
                                "Points": new_points
                            }
                        }
                    )
                    print(f"Updated {username}: Last seen {now}, Total time {new_total_time}, Points {new_points}")
        else:
            print("Not Live")

        await self.handle_commands(message)

    @commands.command(name="hi")
    async def hi(self, ctx: commands.Context):
        """test"""
        await ctx.send("🎉 hELLO IT IS WORKINH")

    @commands.command(name="giveall")
    async def give_all(self, ctx: commands.Context):
        """Reward all viewers with a point."""
        # Check if the user is the owner or a moderator
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower():
            await self.reward_viewers()
            await ctx.send("🎉 All viewers have been rewarded with 1 Oz Coin!")
        else:
            # Deny access if the user is not authorized
            await ctx.send("⚠️ Only the channel owner or moderators can use this command.")

    @commands.command(name="release")
    async def release(self, ctx: commands.Context, *, username: str):
        """Reward a specific viewer."""
        # Split the message content to get the username
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower():
            await self.reward_viewer(username)
            await ctx.send(f"🎉 {username} has been rewarded with 1 Oz Coin!")
        else:
            # Deny access if the user is not authorized
            await ctx.send("⚠️ Only the channel owner or moderators can use this command.")

    @commands.command(name="addpoints")
    async def addpoints(self, ctx: commands.Context, username: str, points: int):
        """Reward a specific viewer."""
        # Split the message content to get the username
        if points < 0:
            await ctx.send("⚠️ Points must be a positive number!")
            return
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower():
            await self.reward_viewera(username,points)
            await ctx.send(f"🎉 {username} has been rewarded with {points} Oz Coin!")
        else:
            # Deny access if the user is not authorized
            await ctx.send("⚠️ Only the channel owner or moderators can use this command.")

    @commands.command(name="removepoints")
    async def removepoints(self, ctx: commands.Context, username: str, points: int):
        """Reward a specific viewer."""
        # Split the message content to get the username
        if points < 0:
            await ctx.send("⚠️ Points must be a positive number!")
            return
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower():
            await self.reward_viewerr(username, points)
            await ctx.send(f"🎉 {username} has been deducted with {points} Oz Coin!")
        else:
            # Deny access if the user is not authorized
            await ctx.send("⚠️ Only the channel owner or moderators can use this command.")

    @commands.command(name="mypoints")
    async def mypoints(self, ctx: commands.Context, *, username: str = None):
        """Reward a specific viewer."""
        # Split the message content to get the username
        if username is None:  # If no username is provided, use the command user's name
            username = ctx.author.name

        points = await self.getpoints(username)

        await ctx.send(f"🎉 {ctx.author.display_name}, you have {points} Oz Coin!")

    async def is_user_live(self, username):
        """Check if a Twitch user is currently streaming."""
        users = await self.fetch_users(names=[username])
        if not users:
            print(f"User {username} not found.")
            return False

        user_id = users[0].id
        streams = await self.fetch_streams(user_ids=[user_id])
        return bool(streams)

    async def reward_viewers(self):
        for viewer in viewers_collection.find():
            new_balance = viewer.get('Points', 0) + 1
            viewers_collection.update_one(
                {'username': viewer['username']},
                {'$set': {'Points': new_balance}}
            )
        print(f"Rewarded 1 Oz Coin to all viewers!")

    async def reward_viewer(self, username):
        user = viewers_collection.find_one({"username": username})
        now = datetime.utcnow()
        if user:
            new_balance = user.get('Points', 0) + 1
            viewers_collection.update_one(
                {'username': username},
                {'$set': {'Points': new_balance}}
            )
            print(f"Rewarded 1 Oz Coin to {username}!")
        else:
            viewers_collection.insert_one({
                "username": username,
                "first_seen": now,
                "last_seen": now,
                "total_time": 0,
                "Points": 1,
                "cryptoType": "",
                "address": "",
                "Casino-Name": "",
                "is_logged_in": False


            })
            print(f"Added new user {username} and rewarded 1 Oz Coin!")

    async def reward_viewera(self, username,points):
        user = viewers_collection.find_one({"username": username})
        now = datetime.utcnow()
        if user:
            new_balance = user.get('Points', 0) + points
            viewers_collection.update_one(
                {'username': username},
                {'$set': {'Points': new_balance}}
            )
            print(f"Rewarded 1 Oz Coin to {username}!")
        else:
            viewers_collection.insert_one({
                "username": username,
                "first_seen": now,
                "last_seen": now,
                "total_time": 0,
                "Points": points,
                "cryptoType": "",
                "address": "",
                "Casino-Name": "",
                "is_logged_in": False


            })
            print(f"Added new user {username} and rewarded 1 Oz Coin!")

    async def reward_viewerr(self, username,points):
        user = viewers_collection.find_one({"username": username})
        now = datetime.utcnow()
        if user:
            new_balance = user.get('Points', 0) - points
            viewers_collection.update_one(
                {'username': username},
                {'$set': {'Points': new_balance}}
            )
            print(f"Rewarded 1 Oz Coin to {username}!")
        else:
            viewers_collection.insert_one({
                "username": username,
                "first_seen": now,
                "last_seen": now,
                "total_time": 0,
                "Points": -points,
                "cryptoType": "",
                "address": "",
                "Casino-Name": "",
                "is_logged_in": False


            })
            print(f"Added new user {username} and rewarded 1 Oz Coin!")

    async def getpoints(self, username):
        user = viewers_collection.find_one({"username": username})
        now = datetime.utcnow()
        if user:
            balance = user.get('Points', 0)
            return balance
        else:
            viewers_collection.insert_one({
                "username": username,
                "first_seen": now,
                "last_seen": now,
                "total_time": 0,
                "Points": 0,
                "cryptoType": "",
                "address": "",
                "Casino-Name": "",
                "is_logged_in": False
            })
            return 0

# Run the Bot
if __name__ == "__main__":
    bot = TwitchBot()
    bot.run()
