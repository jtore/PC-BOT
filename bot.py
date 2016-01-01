import discord
import requests
from sys import exit, argv
from os import path
from urlparse import urlparse
from datetime import datetime, timedelta
from dateutil.parser import parse
import random
import threading
import yaml
import pycountry
import cleverbot

__git_url__ = "https://github.com/PcBoy111/PC-BOT"


# Sets up config files for saving and loading
class Config:
    """
    Creates a configuration yml file of a dictionary

    Arguments:
        config -- Initializer for dictionaries (required)
        file -- Filename for the config, specified without extension (default "config")
    """
    def __init__(self, config, filename="config"):
        self.config = config
        self.filename = "{}.yml".format(filename)

    def save(self):
        f = open(self.filename, "w")
        f.write(yaml.safe_dump(self.config, encoding="utf-8", allow_unicode=True))
        f.close()

    def load(self):
        if path.isfile(self.filename):
            with open(self.filename, "r") as f:
                self.config = yaml.load(f.read())
        else:
            self.save()

    def set(self, index, value):
        self.config[index] = value

    def get(self, index):
        if index:
            return self.config.get(index)
        return self.config

    def remove(self, index):
        return self.config.pop(index, False)


# Thread class handling messages
class OnMessage(threading.Thread):
    """
    Thread for handling commands.

    Logs are printed to the console only, with the format: time@user> command
    Example: 29.12.15 22:38:18@PC> !stats -PC
    """

    def __init__(self, message):
        threading.Thread.__init__(self)
        self.message = message

    def run(self):
        send_message = ""

        if self.message.content:
            if not self.message.channel.is_private:
                send_message = handle_command(self.message)
            else:
                send_message = handle_pm(self.message)

        if send_message:
            send_message = send_message.encode('utf-8')

            # Log received command to console
            print("%s@%s> %s" % (
                datetime.now().strftime("%d.%m.%y %H:%M:%S"),
                self.message.author.name,
                self.message.content
            ))

            #
            client.send_message(self.message.channel, self.message.author.mention() + " " + send_message)


client = discord.Client()

if len(argv) < 3:
    print("usage: " + argv[0] + " <email> <password> [osu!api-key]")
    exit(0)

client.login(argv[1], argv[2])

if len(argv) > 3:
    osu_api = argv[3]
else:
    osu_api = input("Enter a valid osu! API key for osu! functions (enter nothing to disable): ")  # API Key for osu!

usage = {
    "!pcbot [--git | --reddit]": "display commands",
    "!lmgtfy <query ...>": "let me google that for you~",
    "!profile [-m | --me] <user> [*tag]": "sends link to osu! profile (assign with -m)",
    "!stats <user>": "displays various stats for user",
    "!roll [range]": "roll dice",
    "!yn [--set | --global-set [<yes> <no>]]": "yes or no (alternatively multiple choice)",
    "!story": "toggle story mode",
    "!wordsearch [-s | --stop]": "start a wordsearch or stop with --stop"
}

# Store !yn info in multiple channels
yn_set = Config(
    config={"default": ["yes", "no"]},
    filename="yn"
)

# Store osu! user links
osu_users = Config(
    config={},
    filename="osu-users"
)

# Store server wide settings
reddit_settings = Config(
    config={"default": False},
    filename="reddit_settings"
)

# Store story info in multiple channels
story_enabled = {}
story = {}

# Store wordsearch in multiple channels
wordsearch = {}

# Initialize cleverbot
cleverbot_client = cleverbot.Cleverbot()


# Return the date since in a readable format
def pretty_date(time):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc

    source: http://stackoverflow.com/a/1551394 with some minor adjustments to fit my needs
    """
    now = datetime.utcnow()
    diff = now - time
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return "something's wrong"

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"


# Get and format osu! user stats
def get_osu_stats(user):
    if osu_api:
        osu_stats_request = requests.get("https://osu.ppy.sh/api/get_user", params={"k": osu_api, "u": user})

        # If not found, override send_message and break with return
        if len(osu_stats_request.json()) < 1:
            return "No such user :thumbsdown:"

        osu_stats = osu_stats_request.json()[0]
        osu_stats["country_name"] = pycountry.countries.get(alpha2=osu_stats["country"]).name
        osu_stats["accuracy"] = float(osu_stats["accuracy"])

        # Format message with osu_stats
        send_message = "**Stats for {username}** / https://osu.ppy.sh/u/{user_id} ```\n" \
                       "Performance: {pp_raw}pp (#{pp_rank}) /{country_name} #{pp_country_rank}\n" \
                       "Accuracy:    {accuracy:.6f} %\n" \
                       "             {count_rank_ss} SS {count_rank_s} S {count_rank_a} A\n" \
                       "Playcount:   {playcount}```".format(**osu_stats)
    else:
        send_message = "This command is disabled. :thumbsdown:"

    return send_message


# Get and format osu! map
def get_osu_map(beatmap):
    send_message = ""

    osu_map_params = beatmap
    osu_map_params["k"] = osu_api

    osu_map_request = requests.get("https://osu.ppy.sh/api/get_beatmaps", osu_map_params)

    # If not found, return nothing
    if len(osu_map_request.json()) < 1:
        return send_message

    osu_map = osu_map_request.json()[0]
    osu_map["format_length"] = timedelta(seconds=int(osu_map["total_length"]))

    # Send more info when a version is sent
    if "b" in beatmap:
        osu_scores = None

        # Get scores if the map has a scoreboard
        if int(osu_map["approved"]) > 0:
            osu_scores_params = osu_map_params
            osu_scores_params["limit"] = 1
            osu_scores_request = requests.get("https://osu.ppy.sh/api/get_scores", osu_scores_params)

            osu_scores = osu_scores_request.json()[0]

        # Format message with beatmap and difficulty info
        osu_map["format_drain"] = timedelta(seconds=int(osu_map["hit_length"]))
        osu_map["format_stars"] = float(osu_map["difficultyrating"])
        send_message = "{artist} - {title} // {creator} [{version}]```\n" \
                       "Length: {format_length} ({format_drain} drain) BPM: {bpm} Max combo: {max_combo}\n" \
                       "    CS: {diff_size} AR: {diff_approach} OD: {diff_overall} HP: {diff_drain} " \
                       "Stars: {format_stars:.2f}\n" \
                       "Favourites: {favourite_count} / Success Rate: {passcount}/{playcount}```".format(**osu_map)

        # If the map has scoreboard, give first player
        if osu_scores:
            osu_scores["format_score"] = "{:,}".format(int(osu_scores["score"]))
            osu_scores["format_pp"] = "{}pp".format(osu_scores["pp"]) if osu_scores["pp"] else "0pp"
            osu_scores["format_date"] = pretty_date(parse(osu_scores["date"]) - timedelta(hours=8))
            send_message += "\n{username} is in the lead! ({format_date})```\n" \
                            "Score: {format_score} / {format_pp}\n" \
                            "Combo: {maxcombo}x / Misses: {countmiss}\n" \
                            "       {count300}x300 / {count100}x100 / {count50}x50```".format(**osu_scores)

    # Return map info if no version is selected
    elif "s" in beatmap:
        send_message = "{artist} - {title} // {creator}```\n" \
                       "Length: {format_length} BPM: {bpm}\n" \
                       "Favourites: {favourite_count}```".format(**osu_map)

    return send_message


# Return subreddit from command or False
def subreddit_in(args):
    for arg in args:
        if arg.startswith("/r/"):
            return arg[3:]

    return False


# Return osu! map links in a list
def osu_maps_in(args):
    beatmaps = []
    for s in args:
            if "osu.ppy.sh" in s:
                # Get map type and id
                osu_map_path = path.split(urlparse(s).path)
                osu_map_type = osu_map_path[0][1]
                osu_map_id = osu_map_path[1]
                osu_map_id_end = osu_map_id.find("&")
                if osu_map_id_end > 0:
                    osu_map_id = osu_map_id[:osu_map_id_end]

                # Create dictionary for beatmaps list
                beatmap = {osu_map_type: osu_map_id}

                # Add any unique beatmaps
                if beatmap not in beatmaps:
                    beatmaps.append(beatmap)

    return beatmaps


# Split string into list and handle keywords
def handle_command(message):
    global story_enabled, story

    args = message.content.split()

    # Do not lowercase for stories
    if not args[0].startswith("+"):
        args[0] = args[0].lower()

    # Initialize message string to return
    send_message = ""

    # Avoid these comments
    if len(args) < 1:
        return

    # Return let me google that for you formatted google search
    elif args[0] == "!lmgtfy":
        if len(args) > 1:
            search_query = "+".join(args[1:])
            send_message = "http://lmgtfy.com/?q={}".format(search_query)
        else:
            send_message = ":thumbsdown:"

    # Link to osu! profile or set author as user
    elif args[0] == "!profile":
        append_message = ""

        # If command ends with a tag, apply the tag
        if args[-1].startswith("*"):
            append_message = "#_"
            reference = args[-1].replace("*", "")
            if "ranks" in reference or "performance" in reference:
                reference = "leader"
            elif reference == "kudosu":
                reference = "kudos"
            append_message += reference

        if (len(args) > 1 and not args[-1].startswith("*")) or len(args) > 2:
            user = " ".join(args[1:])
            if args[-1].startswith("*"):
                user = " ".join(args[1:-1])

            # If command is --me
            if args[1] == "-m" or args[1] == "--me":
                if len(args) > 2:
                    user = " ".join(args[2:])
                    if args[-1].startswith("*"):
                        user = " ".join(args[2:-1])
                    osu_users.set(message.author.id, user)
                    append_message += "\n*User " + user + " associated with discord*"
                else:
                    user = osu_users.remove(message.author.id)
                    if user:
                        send_message = "*Removed discord association with " + user + "*"
                    else:
                        send_message = "Please use `!profile -m <user>`"
                osu_users.save()

            if not send_message:
                send_message = "https://osu.ppy.sh/u/" + user + append_message
        else:
            user = osu_users.get(message.author.id)
            if user:
                send_message = "https://osu.ppy.sh/u/" + user + append_message
            else:
                send_message = "You are not associated with any osu! user :thumbsdown: use `!profile -m <user>` to set"

    # Give a list of osu! profile stats
    elif args[0] == "!stats":
        if len(args) > 1:
            user = " ".join(args[1:])
            send_message = get_osu_stats(user)
        else:
            user = osu_users.get(message.author.id)
            if user:
                send_message = get_osu_stats(user)
            else:
                send_message = "You are not associated with any osu! user :thumbsdown: use `!profile -m <user>` to set"

    # Roll a dice
    elif args[0] == "!roll":
        roll_n = 100
        if len(args) > 1:
            try:
                roll_n = int(args[1])
            except ValueError:
                pass
        send_message = "rolls " + str(random.randrange(1, roll_n+1))

    # Very extensive yes or no function
    elif args[0] == "!yn":
        yn_list = yn_set.get("default")

        # Update language set
        if len(args) > 1:
                if (args[1] == "--set") or (args[1] == "--global-set"):
                    globally = False
                    if args[1] == "--global-set":
                        globally = True
                    # Clone settings for mentioned channel
                    if len(message.channel_mentions) > 0:
                        mentioned_channel = message.channel_mentions[0]  # Set to first one, ignore other mentions
                        if yn_set.get(mentioned_channel.id):
                            # Clone settings as default in current server
                            if globally:
                                yn_set.set(message.server.id, yn_set.get(mentioned_channel.id))
                            # Clone settings to current channel
                            else:
                                yn_set.set(message.channel.id, yn_set.get(mentioned_channel.id))
                            send_message = "YN " + ("globally " if globally else "") + "cloned from " + \
                                           mentioned_channel.mention()
                    else:
                        if len(args) > 3:
                            # Add to list
                            for i in range(2, len(args)):
                                args[i] = args[i].replace("_", " ")

                            # Apply list to server
                            if globally:
                                yn_set.set(message.server.id, args[2:])
                            # Apply list to channel
                            else:
                                yn_set.set(message.channel.id, args[2:])

                            # Send formatted message
                            send_message = "YN set to "
                            for i in range(2, len(args)):
                                args[i] = "`" + args[i] + "`"
                            send_message += ",".join(args[2:])
                            send_message += " for this " + ("server" if globally else "channel")
                        else:
                            # Reset server settings
                            if globally:
                                yn_set.remove(message.server.id)
                            # Reset channel settings
                            else:
                                yn_set.remove(message.channel.id)

                            send_message = "YN reset for this " + ("server" if globally else "channel")
                    yn_set.save()

                    # Warn user when the channel id equals the server id
                    # (my understanding is that the default channel will have the same id as the server)
                    if not globally and (message.channel.id == message.server.id):
                        send_message += "\n*setting YN for this channel is* ***the same*** *as setting server wide YN*"

        # Return value from list
        if not send_message:
            yn_server = yn_set.get(message.server.id)
            yn_channel = yn_set.get(message.channel.id)

            # Use global server settings if set and not equal to default settings
            if yn_server:
                yn_list = yn_server

            # Use channel settings if set and not equal to default settings, overriding any global setting
            if yn_channel:
                yn_list = yn_channel

            # Choose from list and send
            send_message = random.choice(yn_list)

    # Enable or disable story mode
    elif args[0] == "!story":
        if story_enabled.get(message.channel.id):  # Check if channel exists and if enabled
            story_enabled[message.channel.id] = False
            if story[message.channel.id]:
                send_message = "Your {} story: ```{}```".format(
                    random.choice(["amazing", "fantastic", "wonderful", "excellent", "magnificent", "brilliant",
                                  "genius", "wonderful", "mesmerizing"]),
                    story[message.channel.id]
                )
            else:
                send_message = "Your story had no words! :thumbsdown:"
        else:  # Set to True in channel, also defining if undefined
            story_enabled[message.channel.id] = True
            story[message.channel.id] = ""
            send_message = "Recording *all words* starting with +, write only + to add new paragraph."

    # Add to story if enabled
    elif (args[0].startswith("+")) and story_enabled.get(message.channel.id):
        for n in args:
            if n == "+":
                story[message.channel.id] += "\n\n"
            elif len(n) > 0:
                if n[0] == "+":
                    story[message.channel.id] += n[1:] + " "
                else:
                    story[message.channel.id] += n + " "
                    
    # Begin wordsearch (Users try finding a word set by a host
    elif args[0] == "!wordsearch":
        if not wordsearch.get(message.channel.id):
            send_message = "Please PM me a word for users to search."
            wordsearch[message.channel.id] = {"user": message.author}
            wordsearch[message.channel.id]["hint"] = ""
        else:
            if len(args) > 1:
                if args[1] == "--stop" or args[1] == "-s":
                    return "Word search cancelled. Shame on you."

            if wordsearch[message.channel.id].get("word"):
                send_message = "A word search is already in progress. Enter a word ending with `!` to guess the word!"
            else:
                send_message = "The host ({}) has yet to set a word!".format(
                        **wordsearch[message.channel.id].get("user").mention()
                )

    # Add to wordsearch if enabled
    elif args[0].endswith("!") and wordsearch.get(message.channel.id):
        user_word = args[0][:-1]
        word = wordsearch[message.channel.id].get("word")
        hint = wordsearch[message.channel.id].get("hint")
        user_hint = ""

        if word:
            # Update hint
            if user_word.startswith(hint):
                for i, c in enumerate(user_word):
                    if not c == word[i]:
                        break

                    user_hint += c

                # Add the found hint
                wordsearch[message.channel.id]["hint"] = user_hint

            # Return whether the word is before or after in the dictionary, or if it's correct
            if user_word > word:
                send_message = "`{}` is after in the dictionary.".format(user_word)
            elif user_word < word:
                send_message = "`{}` is before in the dictionary.".format(user_word)
            else:
                send_message = "got it! The word was `{}`.".format(word)
                wordsearch.pop(message.channel.id)

            if not user_word == word and user_hint:
                send_message += " The word starts with {}".format(user_hint)

    # Display  help command
    elif args[0] == "!help":
        send_message = "`!pcbot`"

    # Show help, return github link or change settings
    elif args[0] == "!pcbot":
        if len(args) > 1:
            # Give link to git
            if args[1] == "--git":
                send_message = __git_url__
                return send_message

            # Toggle subreddit functionality
            elif args[1] == "--reddit":
                if reddit_settings.get(message.server.id):
                    reddit_settings.set(message.server.id, False)
                    send_message = "*Automatic subreddit linking* ***disabled*** *for this server*"
                else:
                    reddit_settings.set(message.server.id, True)
                    send_message = "*Automatic subreddit linking* ***enabled*** *for this server*"

                reddit_settings.save()
                return send_message

        # Print list of commands with description
        send_message = "Commands: ```"
        longest_cmd = len(max(usage))  # Return length of longest key
        space_len = longest_cmd + 4
        for k, v in usage.items():
            send_message += "\n" + k + " "*(space_len - len(k)) + v
        send_message += "```"

    # Show trigger
    elif args[0] == "?trigger":
        send_message = "Trigger is !"

    # Get map links and display info
    elif osu_maps_in(args):
        beatmaps = osu_maps_in(args)
        if len(beatmaps) > 0:
            for i, beatmap in enumerate(beatmaps):
                send_message += get_osu_map(beatmap)
                if len(beatmaps) > i+1:
                    send_message += "\n\n"

    # Send reddit link
    elif subreddit_in(args):
        reddit_enabled = reddit_settings.get("default")
        server_enabled = reddit_settings.get(message.server.id)

        # If server settings are saved, use these
        if server_enabled:
            reddit_enabled = server_enabled

        # Return subreddit link if function is enabled on the server
        if reddit_enabled:
            send_message = "https://www.reddit.com/r/" + subreddit_in(args)

    # Perform cleverbot command on mention
    elif client.user in message.mentions and not message.mention_everyone:
        # Get question asked
        cleverbot_question = ""
        for i in range(0, len(args)):
            if (not args[i].startswith("<@")) and (not args[i].endswith(">")):  # Remove any mentions
                cleverbot_question += args[i] + " "

        # Make sure message was received
        if cleverbot_question:
            client.send_typing(message.channel)
            send_message = cleverbot_client.ask(cleverbot_question.encode('utf-8'))

    return send_message


# Handles private messages
def handle_pm(message):
    args = message.content.split()

    # Check if user is trying to give wordsearch info
    for channel, value in wordsearch.items():
        user = value.get("user")

        if user:
            if user.id == message.author.id:
                if len(args[0]) >= 1:
                    if not wordsearch[channel].get("word"):
                        wordsearch[channel]["word"] = args[0].lower()
                        return "Word set to `{}`.".format(args[0])
                    else:
                        return "Word is already set to `{}`.".format(wordsearch[channel]["word"])


@client.event
def on_message(message):
    # Start new thread to handle commands
    OnMessage(message).start()


@client.event
def on_ready():
    print('\nLogged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    # Load configuration files
    yn_set.load()
    osu_users.load()
    reddit_settings.load()

if __name__ == "__main__":
    client.run()
