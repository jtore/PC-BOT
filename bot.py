import discord
import requests
import sys
import pycountry
import random

client = discord.Client()

if len(sys.argv) < 3:
    print("usage: " + sys.argv[0] + " <email> <password> [osu!api-key]")
    sys.exit(0)

client.login(sys.argv[1], sys.argv[2])

if len(sys.argv) > 3:
    osu_api = sys.argv[3]
else:
    osu_api = input("Enter a valid osu! API key for osu! functions (enter nothing to disable): ")  # API Key for osu!

usage = {
    "!pcbot": "display commands",
    "!google <query ...>": "search the web",
    "!display [-u url] [query ...]": "search the web for images",
    "!lucky <query ...>": "retrieve a link",
    "!lmgtfy <query ...>": "let me google that for you~",
    "!profile <user>": "sends link to osu! profile",
    "!stats <user>": "displays various stats for user",
    "!roll [range]": "roll dice",
    "!yn [--set [<yes> <no>]]": "yes or no"
}

yn_set = {
   "default": ["yes", "no"]
}


# Return length of longest keyword for printing
def longest_cmd():
    cmd_len = 0
    for k, _ in usage.items():
        if len(k) > cmd_len:
            cmd_len = len(k)
    return cmd_len


def handle_command(message):
    args = message.content.split()
    args[0] = args[0].lower()
    send_message = ""

    # Avoid these comments
    if len(args) < 1:
        return

    if args[0] == "!google":  # Search google
        if len(args) > 1:
            send_message = "http://google.com/search?q=" + "+".join(args[1:])
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!display":  # Link to images
        if len(args) > 1:
            if len(args) > 2 and args[1].lower() == "-u":
                query = ""
                if len(args) > 3:
                    query = "+".join(args[3:])
                    query = "&q=" + query + "&oq=" + query
                send_message = "https://www.google.com/searchbyimage?image_url=%s%s" % (
                    args[2],
                    query
                )
            else:
                send_message = "http://google.com/search?q=" + "+".join(args[1:]) + "&tbm=isch"
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!lucky":  # Return a link from lucky
        if len(args) > 1:
            to_get = r"http://google.com/search?q=" + r"+".join(args[1:]) + r"&btnI"
            result = requests.get(to_get, allow_redirects="false")
            send_message = result.url
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!lmgtfy":
        if len(args) > 1:
            send_message = r"http://lmgtfy.com/q?=" + r"+".join(args[1:])
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!profile":  # Link to osu! profile
        if len(args) > 1:
            send_message = r"http://osu.ppy.sh/u/" + str(args[1])
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!stats":  # Give a list of osu! profile stats
        if len(args) > 1:
            if osu_api:
                user = " ".join(args[1:])
                to_get = r"http://osu.ppy.sh/api/get_user?k=" + osu_api + r"&u=" + user
                osu_stats_request = requests.get(to_get)
                osu_stats = osu_stats_request.json()[0]
                send_message = "**Stats for %s** (%s) ```" % (
                    osu_stats["username"],
                    osu_stats["user_id"]
                )
                send_message += "Performance: %spp (#%s) /%s #%s" % (
                    osu_stats["pp_raw"],
                    osu_stats["pp_rank"],
                    pycountry.countries.get(alpha2=osu_stats["country"]).name,
                    osu_stats["pp_country_rank"]
                )
                send_message += "\nAccuracy:    %0.6f %%" % float(osu_stats["accuracy"])
                send_message += "\n             %s SS %s S %s A" % (
                    osu_stats["count_rank_ss"],
                    osu_stats["count_rank_s"],
                    osu_stats["count_rank_a"]
                )
                send_message += "\nPlaycount:   " + osu_stats["playcount"]
                send_message += "```"
            else:
                send_message = "This command is disabled. :thumbsdown:"
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!roll":  # Roll a dice
        roll_n = 100
        if len(args) > 1:
            try:
                roll_n = int(args[1])
            except ValueError:
                pass
        send_message = "rolls " + str(random.randrange(1, roll_n+1))
    elif args[0] == "!yn":  # Yes or no
        yn_list = yn_set["default"]

        # Update language set
        if len(args) > 1:
                if args[1] == "--set":
                    if len(args) > 3:
                        yn_set[message.channel.id] = [args[2], args[3]]
                        send_message = "YN set to `" + args[2] + "`, `" + args[3] + "` for this channel"
                    else:
                        yn_set[message.channel.id] = yn_set["default"]
                        send_message = "YN reset for this channel"

        # Update if blank (workaround for --set)
        if not send_message:
            if message.channel.id in yn_set:
                yn_list = yn_set[message.channel.id]
            send_message = random.choice(yn_list)
    elif args[0] == "!pcbot":  # Show help
        send_message = "Commands: ```"
        space_len = longest_cmd() + 4
        for k, v in usage.items():
            send_message += "\n" + k + " "*(space_len - len(k)) + v
        send_message += "```"
    elif args[0] == "?trigger":  # Show trigger
        send_message = "Trigger is !"

    return send_message


@client.event
def on_message(message):
    send_message = handle_command(message)
    if send_message:
        client.send_message(message.channel, message.author.mention() + " " + send_message.encode('utf-8'))


# @client.event
# def on_message_edit(before, after):
#     send_message = handle_command(after)
#     if send_message:
#         client.send_message(after.channel, after.author.mention() + " " + send_message)


@client.event
def on_ready():
    print('\nLogged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


client.run()
