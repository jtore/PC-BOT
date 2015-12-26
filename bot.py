import discord
import requests
import sys

client = discord.Client()

if len(sys.argv) < 3:
    print("usage: " + sys.argv[0] + " <email> <password>")
    sys.exit(0)

client.login(sys.argv[1], sys.argv[2])

usage = {
    "!pcbot": "display commands",
    "!google <query ...>": "search the web",
    "!display <query ...>": "search the web for images",
    "!lucky <query ...>": "retrieve a link",
    "!profile <user>": "sends link to osu! profile"
}


# Return length of longest keyword for printing
def longest_cmd():
    cmd_len = 0
    for k, _ in usage.items():
        if len(k) > cmd_len:
            cmd_len = len(k)
    return cmd_len


@client.event
def on_message(message):
    args = message.content.split()
    send_message = ""

    # Avoid these comments
    if len(args) < 1:
        return

    if args[0] == "!google":  # Search google
        if len(args) > 1:
            send_message = "http://www.google.com/search?q=" + "+".join(args[1:])
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!display":  # Link to images
        if len(args) > 1:
            send_message = "http://www.google.com/search?q=" + "+".join(args[1:]) + "&tbm=isch"
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!lucky":  # Return a link from lucky
        if len(args) > 1:
            to_get = r"http://www.google.com/search?q=" + r"+".join(args[1:]) + r"&btnI"
            result = requests.get(to_get, allow_redirects="false")
            send_message = result.url
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!profile":
        if len(args) > 1:
            send_message = r"http://osu.ppy.sh/u/" + str(args[1])
        else:
            send_message = ":thumbsdown:"
    elif args[0] == "!pcbot":  # Show help
        help_message = "Commands: ```"
        space_len = longest_cmd() + 4
        for k, v in usage.items():
            help_message += "\n" + k + " "*(space_len - len(k)) + v
        help_message += "```"
        send_message = help_message

    # Send message if received command
    if send_message:
        client.send_message(message.channel, message.author.mention() + " " + send_message)


@client.event
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


client.run()
