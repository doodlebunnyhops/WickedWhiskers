import matplotlib.pyplot as plt # type: ignore
import discord

# List of available discord.Color options
colors = {
    "default": discord.Color.default(),
    "teal": discord.Color.teal(),
    "dark_teal": discord.Color.dark_teal(),
    "green": discord.Color.green(),
    "dark_green": discord.Color.dark_green(),
    "blue": discord.Color.blue(),
    "dark_blue": discord.Color.dark_blue(),
    "og_blurple": discord.Color.blurple(),
    "blurple": discord.Color.blurple(),
    "purple": discord.Color.purple(),
    "dark_purple": discord.Color.dark_purple(),
    "fuchsia": discord.Color.fuchsia(),
    "magenta": discord.Color.magenta(),
    "dark_magenta": discord.Color.dark_magenta(),
    "gold": discord.Color.gold(),
    "dark_gold": discord.Color.dark_gold(),
    "yellow": discord.Color.yellow(),
    "orange": discord.Color.orange(),
    "dark_orange": discord.Color.dark_orange(),
    "red": discord.Color.red(),
    "dark_red": discord.Color.dark_red(),
    "lighter_gray": discord.Color.lighter_gray(),
    "light_gray": discord.Color.light_gray(),
    "dark_gray": discord.Color.dark_gray(),
    "darker_gray": discord.Color.darker_gray(),
    "greyple": discord.Color.greyple(),
    "dark_theme": discord.Color.dark_theme(),
}

discord.Color.blurple

# Plot the colors
fig, ax = plt.subplots(figsize=(8, 12))
ax.set_xlim(0, 1)
ax.set_ylim(0, len(colors))
ax.set_xticks([])
ax.set_yticks(range(len(colors)))
ax.set_yticklabels(colors.keys(), fontsize=12)

for i, (name, color) in enumerate(colors.items()):
    # Convert the discord.Color object to a hex color string
    hex_color = f'#{color.value:06x}'
    ax.add_patch(plt.Rectangle((0, i), 1, 1, color=hex_color))

ax.set_title("discord.Color Options", fontsize=16)
plt.show()
