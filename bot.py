import discord
import requests
from sys import exit, argv
from os import path
from datetime import datetime, timedelta
from time import strptime
import random
import threading
import yaml
import pycountry
import cleverbot
import urlparse

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
            send_message = handle_command(self.message)

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
    "!google <query ...>": "search the web",
    "!display [-u url] [query ...]": "search the web for images",
    "!lucky <query ...>": "retrieve a link (please refrain from using this too much)",
    "!lmgtfy <query ...>": "let me google that for you~",
    "!profile [-m | --me] <user>": "sends link to osu! profile (assign with -m)",
    "!stats <user>": "displays various stats for user",
    "!roll [range]": "roll dice",
    "!yn [--set | --global-set [<yes> <no>]]": "yes or no (alternatively multiple choice)",
    "!story": "toggle story mode"
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

# Initialize cleverbot
cleverbot_client = cleverbot.Cleverbot()


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
def get_osu_map(url):
    send_message = ""

    osu_map_path = path.split(urlparse.urlparse(url.strip()).path)
    osu_map_type = osu_map_path[0][1]

    if osu_api and (osu_map_type == "b" or osu_map_type == "s"):
        osu_map_params = urlparse.parse_qs(url)
        osu_map_params["k"] = osu_api

        # Get beatmap id and type
        osu_map_id = osu_map_path[1]
        osu_map_id_end = osu_map_id.find("&")
        if osu_map_id_end > 0:
            osu_map_id = osu_map_id[:osu_map_id_end]
        osu_map_params[osu_map_type] = osu_map_id

        osu_map_request = requests.get("https://osu.ppy.sh/api/get_beatmaps", osu_map_params)

        # If not found, return nothing
        if len(osu_map_request.json()) < 1:
            return send_message

        osu_map = osu_map_request.json()[0]
        osu_map["format_length"] = timedelta(seconds=int(osu_map["total_length"]))

        # Send more info when a version is sent
        if osu_map_type == "b":
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
                           "    CS:{diff_size} AR:{diff_approach} OD:{diff_overall} HP:{diff_drain} " \
                           "Stars:{format_stars:.2f}```".format(**osu_map)

            # If the map has scoreboard, give first player
            if osu_scores:
                osu_scores["format_score"] = "{:,}".format(int(osu_scores["score"]))
                osu_scores["format_pp"] = "{}pp".format(osu_scores["pp"]) if osu_scores["pp"] else "0pp"
                osu_scores_datetime = datetime(*strptime(osu_scores["date"], "%Y-%m-%d %H:%M:%S")[:6])
                osu_scores["format_date"] = datetime.today() - osu_scores_datetime
                send_message += "\n{username} is in the lead! ({format_date.days} days ago)```\n" \
                                "  Score: {format_score} / {format_pp}\n" \
                                "  Combo: {maxcombo}x / Misses: {countmiss}\n" \
                                "         {count300}x300 / {count100}x100 / {count50}x50```".format(**osu_scores)

        # Return map info if no version is selected
        elif osu_map_type == "s":
            send_message = "{artist} - {title} // {creator}```\n" \
                           "Length: {format_length} BPM: {bpm}```".format(**osu_map)

    return send_message


# Return subreddit from command or False
def subreddit_in(args):
    for arg in args:
        if arg.startswith("/r/"):
            return arg[3:]

    return False


# Return osu! map link or false
def osu_map_in(args):
    for s in args:
            if "osu.ppy.sh" in args:
                return s

    return False


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

    # Search google
    if args[0] == "!google":
        if len(args) > 1:
            search_query = " ".join(args[1:])
            search_request = requests.head("https://google.com/search",
                                           params={"q": search_query})
            send_message = search_request.history[0].url
        else:
            send_message = ":thumbsdown:"

    # Link to images
    elif args[0] == "!display":
        if len(args) > 1:
            if len(args) > 2 and args[1].lower() == "-u":
                search_params = {}
                if len(args) > 3:
                    search_query = " ".join(args[3:])
                    search_params["q"], search_params["oq"] = [search_query] * 2
                search_request = requests.head("https://www.google.com/searchbyimage?image_url=%s" % args[2],
                                               params=search_params)
                send_message = search_request.history[0].url
            else:
                search_query = " ".join(args[1:])
                search_request = requests.head("https://google.com/search",
                                               params={"q": search_query, "tbm": "isch"})
                send_message = search_request.history[0].url
        else:
            send_message = ":thumbsdown:"

    # Return first link from google search (deprecated API, allows few searches)
    elif args[0] == "!lucky":
        if len(args) > 1:
            search_string = " ".join(args[1:])
            result_string = requests.get("http://ajax.googleapis.com/ajax/services/search/web",
                                         params={"v": "1.0", "q": search_string})
            result = result_string.json()
            results = []
            if not result["responseData"]:
                if result["responseStatus"] == 403:
                    send_message = "Please refrain from using lucky search too much :thumbsdown:"
                else:
                    send_message = "Unknown error :thumbsdown:"
                return send_message
            else:
                results = result["responseData"]["results"]

            # Send URL of the first result
            if len(results) > 0:
                send_message = results[0]["unescapedUrl"]
            else:
                send_message = "No results :thumbsdown:"
        else:
            send_message = ":thumbsdown:"

    # Return let me google that for you formatted google search
    elif args[0] == "!lmgtfy":
        if len(args) > 1:
            search_query = " ".join(args[1:])
            search_request = requests.head("http://lmgtfy.com/",
                                           params={"q": search_query})
            send_message = search_request.url
        else:
            send_message = ":thumbsdown:"

    # Link to osu! profile or set author as user
    elif args[0] == "!profile":
        if len(args) > 1:
            append_message = ""
            user = " ".join(args[1:])

            # If command is --me
            if args[1] == "-m" or args[1] == "--me":
                if len(args) > 2:
                    user = " ".join(args[2:])
                    osu_users.set(message.author.id, user)
                    append_message = "\n*User " + user + " associated with discord*"
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
                send_message = "https://osu.ppy.sh/u/" + user
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
                send_message = "Your %s story: ```%s```" % (
                    random.choice(["amazing", "fantastic", "wonderful", "excellent", "magnificent", "brilliant",
                                  "genius", "wonderful", "mesmerizing"]),
                    story[message.channel.id]
                )
            else:
                send_message = "Your story had no words! :thumbsdown:"
        else:  # Set to True in channel, also defining if undefined
            story_enabled[message.channel.id] = True
            story[message.channel.id] = ""
            send_message = "Recording *all words* starting with +, write only + to add new paragraph"

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
    elif osu_map_in(args) in args:
        url = osu_map_in(args)
        send_message = get_osu_map(url)

    # Lookup subreddit
    elif subreddit_in(args):
        reddit_enabled = reddit_settings.get("default")
        server_enabled = reddit_settings.get(message.server.id)

        # If server settings are saved, use these
        if server_enabled:
            reddit_enabled = server_enabled

        # Return subreddit link if function is enabled on the server
        if reddit_enabled:
            subreddit = subreddit_in(args)
            search_string = "https://www.reddit.com/r/" + subreddit
            search_request = requests.head(search_string, allow_redirects=True)
            send_message = search_request.url

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
