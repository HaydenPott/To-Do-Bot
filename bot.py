import discord, pymongo, datetime
TOKEN = 'NzIyNzc2NTc1MzE3Mzc3MTM0.XuoAJA.yiH31OD5MtbgwHxN8E4AJo0FKZc'
client = discord.Client()

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
database = mongo_client["ToDo_Bot_Storage"]
guilds_col = database["guild_info"]

PREFIX = "/todo"  # The prefix for all ToDo bot commands

help_message_text = """
~~-------------------------------------~~
**Commands:**
`/todo add <item>` - Adds item to todo list
`/todo complete <id>` - Marks an item as complete using the ID number
`/todo remove <id>` - Removes an item from the todo list
`/todo rename <id> <new_name>` - Renames an item on the todo list
`/todo removecompleted` - Removes all items that have been marked as completed from the todo list
`/todo list` - Shows the current To Do list
`/todo ?` - Displays this message
~~-------------------------------------~~"""

error_messages = {
    "id_not_an_int": "Please use an integer for <id>, for more information, check `/todo ?`"
}
delete_delay = 60

@client.event
async def on_ready():
    print(f'Logged in as: {client.user.name}')
    print(f'With ID: {client.user.id}')
    # update_db()
    for x in guilds_col.find():
        print(x)
        
    

    for g in client.guilds:
        
        query = {"guild_id": g.id}
        # print(guilds_col.find_one(query))
        if not guilds_col.find_one(query):
            await on_guild_join(guild=g)
        else:
            # print(g.id, g.name)
            await update_messages(g)


@client.event
async def on_guild_join(guild):
    todo_channel = await guild.create_text_channel(
        "to-do",
        reason="Initial Creation of the ToDo channel by the ToDo bot",
        topic="Channel created byt the ToDo Bot. Add an item to the todo list to get started!",)
    # await todo_channel.edit(
    #     topic="Channel created byt the ToDo Bot. Add an item to the todo list to get started!",
    # )
    todo_message = await todo_channel.send(content="To Do List:\nAdd an item to the ToDo list using `/todo add <item>`")
    help_message = await todo_channel.send(content=help_message_text)

    update_db(
        guild,
        todo_channel_id=todo_channel.id,
        todo_message_id=todo_message.id,
        help_message_id=help_message.id,
        todo_list=[]
    )

    print(f"Bot has been added to a guild! Guild Name: \"{guild.name}\"")


@client.event
async def on_message(message):
    if message.author == client.user:
        pass
    query = {"guild_id": message.guild.id}
    db_info = guilds_col.find_one(query)
    if message.content.startswith(PREFIX):
        command_params = message.content.split(" ")
        lowered_command = []
        for x in command_params:
            lowered_command.append(x.lower())
        print(lowered_command)
        if len(lowered_command) <= 1 or lowered_command[1] in ["help", "?"]: # /todo, /todo help, /todo ?
            await message.channel.send(content=help_message_text, delete_after=delete_delay)
            await update_messages(g=message.guild)

        elif lowered_command[1] in ["add"]: # /todo add
            todo_list_temp = db_info["todo_list"]
            new_item = " ".join(command_params[2:])
            todo_list_temp.append({
                "item": new_item,
                "completed": False,
                "date_added": datetime.datetime.now(),
                "added_by": str(message.author),
                "category": "",
                "importance": 0,
            })
            update_db(message.guild, todo_list=todo_list_temp)
            returnMessage = f"\"{new_item}\" added to ToDo list by **{message.author.name}**"
            await message.channel.send(returnMessage, delete_after=delete_delay)


        elif lowered_command[1] in ["complete", "done", "finish"]:
            if is_int(lowered_command[2]):
                index = int(lowered_command[2])-1
                todo_list = db_info["todo_list"]
                if index >= 0 and index < len(todo_list):
                    todo_list[index]["completed"] = True
                    await message.channel.send(f"`{todo_list[index]['item']}` marked as completed!", delete_after=delete_delay)
                    update_db(g=message.guild, todo_list=todo_list)
                else:
                    await message.channel.send("Please use an ID number on the todo list.", delete_after=delete_delay)
            else:
                await message.channel.send(f"Please enter an integer for `<id>`. The command should be `/todo {lowered_command[1]} <id>`", delete_after=delete_delay)
        elif lowered_command[1] in ["info", "data", "information"]:
            if is_int(lowered_command[2]):
                index = int(lowered_command[2])-1
                todo_list = db_info["todo_list"]
                if index >= 0 and index < len(todo_list):
                    item = todo_list[index]
                    msg = f"""**Showing Info for item **`#{index+1}:`
**Item Name:** `{item['item']}`
**Category:** `{item['category'] if item['category'] != '' else 'None'}`
**Importance Level:** `{item['importance']}`
**Completed:** `{item['completed']}`
**Date Added:** `{item['date_added'].strftime('%A, %d %B %Y')}`
**Added By:** `{item['added_by']}`
                    """
                    await message.channel.send(msg, delete_after=delete_delay)
                else:
                    await message.channel.send("Please use an ID number on the todo list.", delete_after=delete_delay)
            else:
                await message.channel.send(f"Please enter an integer for `<id>`. The command should be `/todo {lowered_command[1]} <id>`", delete_after=delete_delay)
        else:
            await message.channel.send(f"Unknown subcommand, `{lowered_command[1]}`, use `/todo help` for a list of commands.")

        await update_messages(message.guild)

async def update_messages(g=None):
    if g:
        query = {"guild_id": g.id}
        db_info = guilds_col.find_one(query)
        todo_list = db_info["todo_list"]
        todo_channel = await client.fetch_channel(db_info["todo_channel_id"])
        todo_msg = await todo_channel.fetch_message(db_info["todo_message_id"])
        help_msg = await todo_channel.fetch_message(db_info["help_message_id"])
        s = "ToDo List: "
        for x in range(len(todo_list)):
            done = ":white_check_mark:" if todo_list[x]["completed"] else ""
            # todo_item = todo_list[x]["item"]
            s += f"\n{x+1}: {done}`({'!' * is_int(todo_list[x]['importance'], r=True)})` `{todo_list[x]['item']}`"
        if len(todo_list) <= 0:
            s += "\nThere's nothing on your ToDo list!"
        await todo_msg.edit(content=s)
        await help_msg.edit(content=help_message_text)


def update_db(g=None, **options):
    query = {}
    GUILD_DICT = {}
    if not g:
        for guild in client.guilds:
            GUILD_DICT = {"guild_id": guild.id, "guild_name": guild.name, }
            for x in options:
                GUILD_DICT[x] = options[x]
            query = {"guild_id": guild.id}
    else:
        GUILD_DICT = {"guild_id": g.id, "guild_name": g.name, }
        for x in options:
            GUILD_DICT[x] = options[x]
        query = {"guild_id": g.id}
    if not guilds_col.find_one(query):
        guilds_col.insert_one(GUILD_DICT)
    else:
        guilds_col.update_one(query, {"$set": GUILD_DICT})

def is_int(s, r=False):
    try:
        int(s)
        if not r:
            return True
        else:
            return int(s)
    except ValueError:
        return False
client.run(TOKEN)
