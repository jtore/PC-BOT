# PC BOT
BOT for discord built with [discord.py][parent].
Follow the link for install instructions. I recommend using the legacy branch, as this is needed for the current dev branch (and fixes a quite important bug causing the bot to crash whenever new users join a channel).

**This bot is only supported for python 2.7 (cleverbot is unsupported for python 3.4)**
[parent]: https://github.com/Rapptz/discord.py

## Running
The bot needs two arguments to run, discord login email and password.
```
python bot.py <email> <password> [osu!api-key]
```
To give the bot osu! API functionality, you need to either provide it a valid API key on startup or give the key via command.

You can choose not to use this functionality.

To get started with the bot, send `!pcbot`
