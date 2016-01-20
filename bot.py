# -*- coding: utf-8 -*-


import discord
import requests
import random
from sys import exit, argv
from os import path, makedirs
from datetime import datetime, timedelta
from io import BytesIO

from urlparse import urlparse
from dateutil.parser import parse
from PIL import Image
import threading
import pycountry
import cleverbot

from pcbot import Config

__git_url__ = "https://github.com/PcBoy111/PC-BOT"


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
                send_message = handle_message(self.message)
            else:
                send_message = handle_pm(self.message)

        # If a message can be sent and it isn't a wordsearch element
        if send_message:
            send_message = send_message.encode('utf-8')

            # Log received command to console (old format to save myself)
            print("%s@%s> %s" % (
                datetime.now().strftime("%d.%m.%y %H:%M:%S"),
                self.message.author.name,
                self.message.content
            ))

            # Send any received message to the channel as @user <message ...>
            client.send_message(self.message.channel, self.message.author.mention() + " " + send_message)


# Initialize the client
client = discord.Client()

# Get all necessary info
if len(argv) < 3:
    print("usage: " + argv[0] + " <email> <password> [osu!api-key]")
    exit(0)

# Store the password on request (needed to change avatar for mood setting) and login either way
password = None
if argv[2].startswith("*"):
    password = argv[2][1:]
    client.login(argv[1], argv[2][1:])
else:
    client.login(argv[1], argv[2])

# API Key for osu!
if len(argv) > 3:
    osu_api = argv[3]
else:
    osu_api = raw_input("Enter a valid osu! API key for osu! functions (enter nothing to disable): ")

usage = {
    "!pcbot [--git | --reddit]": "display commands",
    "!lmgtfy <query ...>": "let me google that for you~",
    "!define <word/phrase ...>": "define this!",
    "!profile [-m | --me] <user> [*tag]": "sends link to osu! profile (assign with -m)",
    "!stats <user>": "displays various stats for user",
    "!roll [range]": "roll dice",
    "!yn [--set | --global-set [<yes> <no>]]": "yes or no (alternatively multiple choice)",
    "!story": "toggle story mode",
    "!wordsearch [-a | --auto] [-s | --stop]": "start a wordsearch or stop with --stop"
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
wordsearch_characters = Config(
    config={"default": "abcdefghijklmnopqrstuvwxyz"},
    filename="wordsearch_chars"
)
wordsearch_words = []


# Get each word in english dictionary and store it in wordsearch_words
def set_wordsearch_words():
    global wordsearch_words

    word_request = requests.get("http://www.mieliestronk.com/corncob_lowercase.txt")
    wordsearch_words = word_request.text.split("\n")


# Store mood and avatar filename
moods = Config(
    config={},
    filename="moods"
)


# Change the bots mood
def set_mood(mood, url=None):
    game = discord.Game()
    game.name = None

    if not mood == "default":
        game.name = mood

    client.change_status(game)

    # Change avatar if a password is stored
    if password:
        field = {}

        mood = mood.lower()

        if url:
            avatar_request = requests.get(url)
            if avatar_request.ok:
                avatar_bytes = BytesIO(avatar_request.content)
                avatar_object = Image.open(avatar_bytes)
                if not path.exists("avatars/"):
                    makedirs("avatars/")
                avatar_object.save("avatars/{}.png".format(mood))

                moods.set(mood, "{}.png".format(mood))
                moods.save()
                field["avatar"] = avatar_bytes

        if moods.get(mood):
            avatar_file = open("avatars/{}".format(moods.get(mood)), "rb")
            avatar_bytes = avatar_file.read()

            field["avatar"] = avatar_bytes

        client.edit_profile(password, **field)


# Store reminder alarm dates for !remindme
# Formats as user_id: date
reminders = Config(
    config={},
    filename="reminders"
)


# Send a pm to user whenever they requested to be reminded
def send_reminder(user_id):
    client.send_message(client.get_channel(user_id), "Wake up! The time is %s." % datetime.now())

    if reminders.get(user_id):
        reminders.remove(user_id, save=True)


# Remind the user in x seconds from the specified date
def remind_at(date, user_id):
    remind_in_seconds = (date - datetime.now()).total_seconds()

    if remind_in_seconds > 1:
        threading.Timer(remind_in_seconds, send_reminder, args=[user_id]).start()
        reminders.set(user_id, date, save=True)
    else:
        if reminders.get(user_id):
            reminders.remove(user_id, save=True)


# Initialize cleverbot
cleverbot_client = cleverbot.Cleverbot()


def has_permissions(user):
    """
    :param user: A class discord.User
    :return: True if user can manage channels, else False
    """
    for role in user.roles:
        if role.permissions.can_manage_channels:
            return True

    return False


def pretty_date(time):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc

    :param time: datetime object in UTC.
    :return: see above

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


def get_osu_stats(user):
    """
    Lookup an osu! user and return information. Does
    not return user best.

    :param user: username or user_id
    :return: formatted string
    """
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


def get_osu_map(beatmap):
    """
    Returns osu! beatmap info. If a mapset is specified (s),
    only return some info about the mapset. If a difficulty/version
    is specified, return difficulty info. If the map is ranked and
    has a scoreboard, return extra info of the top play.

    :param beatmap: Dictionary with one key, either 's' (mapset) or
                    'b' (version), with the map id as value.
                    Example: {'s', 267767} (required)
    :return: string (see above)
    """
    send_message = ""

    if osu_api:
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
                # Format date. Change hours=8 to whatever your offset is (I've quite frankly forgotten)
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
    else:
        send_message = "This command is disabled :thumbsdown:"

    return send_message


def get_osu_id(user):
    """
    :param user: Username or ID to retrieve from
    :return: The users ID or none if they can't be found
    """
    osu_user_request = requests.get("https://osu.ppy.sh/api/get_user", params={"k": osu_api, "u": user})
    osu_user = osu_user_request.json()

    if osu_user:
        return osu_user[0]["user_id"]

    return None


def subreddit_in(args):
    """
    Return the first occurrence of a subreddit reference in
    a list of strings.
    Example: /r/all

    :param args: list of strings (required)
    :return: subreddit name (ex: all) or False
    """
    for arg in args:
        if arg.startswith("/r/"):
            return arg[3:]

    return False


def osu_maps_in(args):
    """
    Return a list of beatmaps found in a list of strings in
    the form of a dictionary, where the key is map_type and value
    is map_id
    Example: {'s': 267767}

    :param args: list of strings (required)
    :return: beatmap as {map_type: map_id}
    """
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
def handle_message(message):
    """
    Handles any input sent to a channel, going through a list of
    pre-programmed commands and specifiers.
    (This code is really messy)

    Features:
    --  !lmgtfy, !profile, !stats, !roll, !yn, !story, !wordsearch,
        !help, !pcbot, ?trigger,
    --  Handle any words for !story
    --  Handle any entries (guesses) for !wordsearch
    --  Handle subreddit references
    --  Handle beatmap links
    --  Return a message from Cleverbot when mentioned

    :param message: a discord class Message received (required)
    :return: type string to send back to the channel
    """
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

    # Define a word using urban dictionary
    elif args[0] == "!define":
        if len(args) > 1:
            request_params = {"term": " ".join(args[1:])}
            definitions_request = requests.get("http://api.urbandictionary.com/v0/define", request_params)
            definitions = definitions_request.json().get("list")
            if definitions:
                definition = definitions[0]
                if definition.get("example"):
                    definition["example"] = "```%s```" % definition["example"]
                send_message = "**%(word)s**:\n" \
                               "%(definition)s\n" \
                               "%(example)s" % definition
            else:
                send_message = "No such word is defined."
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

                    if osu_api:
                        user = get_osu_id(user)
                        if not user:
                            return "This user does not exist."

                    osu_users.set(message.author.id, user)
                    append_message += "\n*osu! user associated with discord*"
                else:
                    user = osu_users.remove(message.author.id)
                    if user:
                        send_message = "*Removed discord association with osu! user.*"
                    else:
                        send_message = "Please use `!profile -m <user>`"
                osu_users.save()

            if not send_message:
                send_message = "https://osu.ppy.sh/u/" + user.replace(" ", "%20") + append_message
        else:
            user = osu_users.get(message.author.id)
            if user:
                send_message = "https://osu.ppy.sh/u/" + user.replace(" ", "%20") + append_message
            else:
                send_message = "You are not associated with any osu! user :thumbsdown: use `!profile -m <user>` to set."

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
                send_message = "You are not associated with any osu! user :thumbsdown: use `!profile -m <user>` to set."

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

                    # Warn user when the channel is default channel
                    # (my understanding is that the default channel will have the same id as the server)
                    if not globally and message.channel.is_default_channel():
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
        # Change character set
        if len(args) > 1:
            if args[1] == "--charset":
                charset = ""

                if len(args) > 2:
                    charset = args[2].lower()

                channel_charset = wordsearch_characters.get(message.channel.id)

                # Check if channel has a set charset
                if channel_charset:
                    if not charset:
                        return "This channels charset is `%s`." % channel_charset

                # Change if the user has valid permission settings for the channel
                if has_permissions(message.author):
                    wordsearch_characters.set(message.channel.id, charset)
                    wordsearch_characters.save()
                    return "Channel `!wordsearch` charset set to `%s`." % charset
                else:
                    return "You do not have permissions to use this command."

        if not wordsearch.get(message.channel.id):
            auto = False

            if len(args) > 1:
                if args[1] == "--auto" or args[1] == "-a":
                    word = ""
                    auto = True
                    amount = 1

                    if len(args) > 2:
                        try:
                            amount = int(args[2])
                        except ValueError:
                            pass

                    if amount > 5:
                        amount = 5
                    elif amount < 1:
                        amount = 1

                    # Download a list of words if not stored in memory
                    if not wordsearch_words:
                        set_wordsearch_words()

                    for _ in range(amount):
                        word += random.choice(wordsearch_words).strip()

                    wordsearch[message.channel.id] = {"word": word,
                                                      "user": message.author}
                    send_message = "Made me set a word."

            if not auto:
                client.send_message(message.channel,
                                    "Waiting for {} to choose a word.".format(message.author.mention()))
                client.send_message(message.author, "Please enter a word!")
                wordsearch[message.channel.id] = {"user": message.author}

            wordsearch[message.channel.id]["hint"] = ""
            wordsearch[message.channel.id]["tries"] = 0
        else:
            if len(args) > 1:
                if args[1] == "--stop" or args[1] == "-s":
                    if wordsearch[message.channel.id].get("user").id == message.author.id:
                        wordsearch.pop(message.channel.id)
                        return "Word search cancelled."
                    else:
                        return "You are not the host of this word search."

            if wordsearch[message.channel.id].get("word"):
                send_message = "A word search is already in progress. Enter a word ending with `!` to guess the word!"
            else:
                send_message = "The host ({}) has yet to set a word!".format(
                        wordsearch[message.channel.id].get("user").mention()
                )

    # Add to wordsearch if enabled
    elif args[0].endswith("!") and wordsearch.get(message.channel.id):
        user_word = args[0][:-1]
        word = wordsearch[message.channel.id].get("word")
        hint = wordsearch[message.channel.id].get("hint")
        user_hint = ""
        old_hint = user_hint

        if word:
            wordsearch[message.channel.id]["tries"] += 1
            tries = wordsearch[message.channel.id]["tries"]

            # Update hint
            if user_word.startswith(hint):
                old_hint = hint
                for i, c in enumerate(user_word):
                    if len(word) - 1 < i:
                        break

                    if not c == word[i]:
                        break

                    user_hint += c

                # Add the found hint
                wordsearch[message.channel.id]["hint"] = user_hint
            else:
                user_hint = hint

            try:
                # Return whether the word is before or after in the dictionary, or if it's correct
                if user_hint == word:
                    if tries == 1:
                        send_message = "***got it*** after *ONE TRY???* :hand::no_entry_sign:VAC:no_entry_sign::hand:" \
                                       "The word was `%s`." % word
                    elif not old_hint:
                        send_message = "***:trumpet::trumpet::ok_hand::trumpet:WOW THIS IS UNBELIEVABLE:trumpet:" \
                                       "HISTORY HAS BEEN MADE, @EVERYONE:trumpet::ok_hand::trumpet::trumpet:***\n" \
                                       "The word was `%s`!!" % word.upper()
                    else:
                        send_message = "***got it*** after **%d** tries! The word was `%s`." % (
                                wordsearch[message.channel.id]["tries"],
                                word
                        )
                    wordsearch.pop(message.channel.id)
                    user_hint = ""
                elif user_word > word:
                    send_message = "`%s` is *after* in the dictionary." % user_word
                elif user_word < word:
                    send_message = "`%s` is *before* in the dictionary." % user_word

                if not user_word == word and user_hint:
                    send_message += " The word starts with `%s`." % user_hint
            except UnicodeEncodeError:
                send_message = "Your word has an unknown character. :thumbsdown:"

    # Remind users at a set time and date
    elif args[0] == "!remindme":
        if len(args) > 1:
            if args[1] == "at":
                if len(args) > 2:
                    try:
                        remind_time = parse(" ".join(args[2:]), fuzzy=True)
                    except (ValueError, OverflowError):
                        return "I can not remind you at %s" % args[2:]

                    if remind_time < datetime.now():
                        return "I can only remind you in the future."

                    remind_at(remind_time, message.author.id)
                    send_message = "I will remind you at %s" % remind_time
                else:
                    send_message = "When do you want to be reminded? `!remindme <at> <time ...>`"
            else:
                send_message = "Please specify when you want to be reminded: `!remindme <at> <time ...>`"
        else:
            send_message = "Please specify when you want to be reminded: `!remindme <at> <time ...>`"

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

            # Change the bots mood
            elif args[1] == "--mood":
                if len(args) > 2:
                    if has_permissions(message.author):
                        mood = args[2]
                        url = None

                        if len(args) > 3:
                            url = args[3]

                        set_mood(mood, url)
                return

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


def handle_pm(message):
    """
    Handles any input sent to a private channel.

    Features:
        retrieve word from a user requesting a !wordsearch

    :param message: a discord class Message received (required)
    :return: type string to send back to the channel
    """
    args = message.content.split()
    send_message = ""

    # Check if user is trying to give wordsearch info
    for channel, value in wordsearch.items():
        user = value.get("user")

        if user:
            if user.id == message.author.id:
                if len(args[0]) > 1:
                    if not wordsearch[channel].get("word"):
                        word = args[0].lower()
                        # Use only whitelisted characters
                        valid_chars = wordsearch_characters.get("default")
                        valid_channel = wordsearch_characters.get(channel)
                        if valid_channel:
                            valid_chars = valid_channel

                        for char in word:
                            valid = False
                            for valid_char in valid_chars:
                                if char == valid_char:
                                    valid = True

                            if not valid:
                                return "Your word has an invalid character `%s`" % char

                        # Cancel too long words
                        if len(args[0]) > 32:
                            return "This word is wicked long! Please choose a shorter one."

                        # Filter out words that don't work
                        try:
                            "%s" % args[0]
                        except UnicodeEncodeError:
                            return "Your word has an unknown character. :thumbsdown:"
                        except:
                            return "This word does not work for some reason. Please contact PC `!pcbot --git`"
                        wordsearch[channel]["word"] = word
                        send_message = "Word set to `%s`." % word
                        client.send_message(
                                client.get_channel(channel),
                                "{} has started a word search. Enter a word ending with `!` to guess the word!".format(
                                    user.mention()
                                )
                        )
                    else:
                        if not send_message:
                            send_message = "Word is already set to `%s`." % wordsearch[channel]["word"]

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
    wordsearch_characters.load()
    moods.load()
    reminders.load()

    # Set mood to default (no mood) if defined
    if moods.get("default"):
        set_mood("default")

    for user_id, date in reminders.get().items():
        remind_at(date, user_id)


if __name__ == "__main__":
    client.run()
