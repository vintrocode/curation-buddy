# curation buddy 🤓📚

this is. curation buddy

# setup
run the following:
```bash
poetry install
poetry shell
```

then copy the `.env.template` into a `.env` file and fill in the values:
```
BOT_TOKEN=
OPENAI_API_KEY=
APIFY_API_TOKEN=
LANGCHAIN_PROJECT=
LANGCHAIN_TRACING_V2=
LANCHAIN_API_KEY=
```
the langchain values are optional if you want to use langsmith.

# start
run the bot:
```bash
python bot.py
```

now your curation agent is running. the honcho fact memory bot is listening to the honcho database waiting to derive facts when new messages are written there. the curation bot is working in discord waiting to entertain your curations :)
