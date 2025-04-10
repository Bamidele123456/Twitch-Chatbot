from twitchio.ext import commands
from pymongo import MongoClient
import time
import requests
from datetime import datetime
import asyncio
# import logging
#
# logging.basicConfig(level=logging.DEBUG)

CLIENT_ID = ''
CLIENT_SECRET = 'y'

TARGET_CHANNEL = 'ozhunt'
SPECIAL_KEYWORD = '!giveall'
KEYWORD = '!release'



client = MongoClient('mongodb+srv://Bamidele1:1631324de@mycluster.vffurcu.mongodb.net/?retryWrites=true&w=majority')
db = client['test']
viewers_collection = db['watch_time']
giveaway = db['giveaway']
bet = db["Twitch-bets"]
winners = db["Twitch-winners"]

user_sessions = {}

# Twitch Bot Class
class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token="oauth:9d15w281ysrfczzgjkx4odsy1ind2b",
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

        print(f"Processing message from: {username}")

        is_streamer_live = await self.is_user_live(TARGET_CHANNEL)
        if is_streamer_live:
            viewer = viewers_collection.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
            if not viewer:
                # Add new user
                viewers_collection.insert_one({
                    "username": username,
                    "first_seen": now,
                    "last_seen": now,
                    "total_time": 0,
                    "Points": 0,
                    "cryptoType": "",
                    "address": "",
                    "Casino-Name": "",
                    "is_logged_in": False,
                    "clear": False
                })
                print(f"New user {username} added to the database.")
            else:
                print(username)
                # Parse last_seen safely
                last_seen = viewer.get("last_seen", now)
                if isinstance(last_seen, str):
                    try:
                        last_seen = datetime.strptime(last_seen, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        print(f"Invalid datetime format for {username}: {last_seen}. Defaulting to now.")
                        last_seen = now

                # Calculate time spent
                time_spent = (now - last_seen).total_seconds()
                if time_spent >= 21600:
                    print(f"{username} has been inactive for too long: {time_spent} seconds. Marking as inactive.")
                    viewers_collection.update_one(
                        {"username": username},
                        {
                            "$set": {
                                "last_seen": now,
                            }
                        }
                    )
                else:
                    new_total_time = viewer["total_time"] + time_spent
                    points = time_spent / 3600
                    old_points = viewer["Points"]
                    new_points = old_points + points
                    viewers_collection.update_one(
                        {"username": username},
                        {
                            "$set": {
                                "last_seen": now,
                                "total_time": new_total_time,
                                "Points": new_points,
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

    @commands.command(name="startbetting")
    async def starbet(self, ctx: commands.Context, type: str, *options: str):
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower() or ctx.author.name.lower() == "tyrshadow":
            options_list = list(options)
            print("Type:", type)
            print("Options:", options_list)
            await self.start_bet(type, options_list)

            formatted_options = "/".join(options_list)
            await ctx.send(f"✅ Betting’s open! Use !bet [amount] [{formatted_options}]")
        else:
            await ctx.send("⚠️ Only the channel owner or moderators can use this command.")

    @commands.command(name="bet")
    async def bet(self, ctx: commands.Context, amount: int, option: str):
        """Allows a user to place a bet."""
        # Step 1: Check if betting is open
        session = bet.find_one({"platform": "twitch"})
        if not session or not session.get("started", False):
            await ctx.send("⚠️ Betting is currently closed.")
            return

        # Step 2: Continue if session is active
        username = ctx.author.name
        points = await self.getpoints(username)

        if points >= amount:
            await self.add_bet(username, amount, option)
            await self.reward_viewerr(username, amount)
            await ctx.send(f"🎲 Bet placed: {username} - {amount} OZcoins on {option}!")
        else:
            await ctx.send(f"❌ {username}, you don't have up to {amount} OZcoins.")

    @commands.command(name="betlist")
    async def betlist(self, ctx: commands.Context):
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower() or ctx.author.name.lower() == "tyrshadow":
            bets = bet.find({"type": "user_bet"})
            bet_lines = []

            for b in bets:
                user = b.get("username", "Unknown")
                option = b.get("option", "N/A")
                amount = b.get("amount", 0)
                bet_lines.append(f"{user}: {amount} OZcoins on {option}")

            if bet_lines:
                response = "📜 Current Bets:\n" + "\n".join(bet_lines)
                await ctx.send(response[:500])
            else:
                await ctx.send("📭 No bets placed yet.")
        else:
            await ctx.send("⚠️ Only the channel owner or moderators can use this command.")

    @commands.command(name="endbetting")
    async def end_betting(self, ctx: commands.Context, winner: str):
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower() or ctx.author.name.lower() == "tyrshadow":
            # Step 1: Get all user bets
            all_bets = list(bet.find({"type": "user_bet"}))
            winners_list = []
            reward_messages = []

            for b in all_bets:
                if b["option"].lower() == winner.lower():
                    username = b["username"]
                    amount = b["amount"]
                    reward = float(amount) * 2

                    # Step 2: Add double coins to user
                    await self.reward_viewera(username, reward)

                    winners_list.append({
                        "username": username,
                        "amount": amount,
                        "option": winner,
                        "reward": reward
                    })

                    reward_messages.append(f"{username} ({amount} on {winner}) gets {reward} Ozcoins!")

            # Step 3: Update the current session
            bet.update_one(
                {"platform": "twitch"},
                {
                    "$set": {
                        "winner": winner,
                        "started": False,
                        "winners": winners_list
                    }
                }
            )

            # Step 4: Save session to `winners` collection
            session_data = bet.find_one({"platform": "twitch"})
            winners.insert_one(session_data)

            # Step 5: Clear current user bets
            bet.delete_many({"type": "user_bet"})

            # Step 6: Send response
            if winners_list:
                await ctx.send(f"✅ Betting closed! Winners: " + " | ".join(reward_messages))
            else:
                await ctx.send(f"✅ Betting closed! No winners this round.")
        else:
            await ctx.send("⚠️ Only the channel owner or moderators can use this command.")

    @commands.command(name="release")
    async def release(self, ctx: commands.Context, *, username: str):
        """Reward a specific viewer."""
        # Split the message content to get the username
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower() or ctx.author.name.lower() == "tyrshadow":
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
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower() or ctx.author.name.lower() == "tyrshadow":
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
        if ctx.author.is_mod or ctx.author.name.lower() == TARGET_CHANNEL.lower() or ctx.author.name.lower() == "tyrshadow":
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

        await ctx.send(f"🎉 {username}, you have {points} Oz Coin!")

    @commands.command(name="enter")
    async def enter(self, ctx: commands.Context, *, username: str = None):
        username = ctx.author.name

        await self.enterg(username)

        await ctx.send(f"🎉 {username}, have registered for the giveaway")

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

    async def enterg(self,username):
        now = datetime.utcnow()

        details = giveaway.find_one({"username": username})
        if not details:
            giveaway.insert_one({"username": username, "date": now, "source": "twitch", "winner": False})
        print(f"{username} has registered for giveaway")

    async def start_bet(self, type, options):
        bet.update_one(
            {"platform": "twitch"},
            {
                "$set": {
                    "type": type,
                    "options": options,
                    "winner": "",
                    "started": True,
                    "winners":""
                }
            },
            upsert=True
        )

    async def add_bet(self, user, amount,option):
        bet.insert_one(
            {
                    "type": "user_bet",
                    "username": user,
                    "option": option,
                    "amount": amount
                }
        )

    async def end_bet(self, winner,winners):
        bet.update_one(
            {"platform": "twitch"},
            {
                "$set": {
                    "winner": winner,
                    "started": False,
                    "winners": ""
                }
            },
        )






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
                "clear":False


            })
            print(f"Added new user {username} and rewarded 1 Oz Coin!")

    async def reward_viewera(self, username,points):
        user = viewers_collection.find_one({"username": username})
        pointi = int(points)

        if user:
            balance = user.get('Points', 0)
            new_balance = balance + pointi
            viewers_collection.update_one(
                {'username': username},
                {'$set': {'Points': new_balance}}
            )
            print(f"Rewarded 1 Oz Coin to {username}!")
        else:
            now = datetime.utcnow()
            viewers_collection.insert_one({
                "username": username,
                "first_seen": now,
                "last_seen": now,
                "total_time": 0,
                "Points": points,
                "cryptoType": "",
                "address": "",
                "Casino-Name": "",
                "is_logged_in": False,
                "clear": False


            })
            print(f"Added new user {username} and rewarded 1 Oz Coin!")

    async def reward_viewerr(self, username,points):
        user = viewers_collection.find_one({"username": username})
        pointsi = int(points)

        if user:
            balance = user.get('Points', 0)
            new_balance = balance - pointsi
            viewers_collection.update_one(
                {'username': username},
                {'$set': {'Points': new_balance}}
            )
            print(f"Removed {points} Coin to {username}!")
        else:
            now = datetime.utcnow()
            viewers_collection.insert_one({
                "username": username,
                "first_seen": now,
                "last_seen": now,
                "total_time": 0,
                "Points": -points,
                "cryptoType": "",
                "address": "",
                "Casino-Name": "",
                "is_logged_in": False,
                "clear": False


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
                "is_logged_in": False,
                "clear": False
            })
            return 0

# Run the Bot
if __name__ == "__main__":
    bot = TwitchBot()
    bot.run()
