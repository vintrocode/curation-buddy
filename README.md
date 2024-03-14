# curation buddy 🤓📚

this is. curation buddy

# setup
in each agent folder, you'll find poetry files. they're two separate venvs. in each one, run the following:
```bash
poetry install
poetry shell
```

then, in one terminal, cd to `agents/honcho_fact_memory` and run the following:
```bash
python fact_deriver.py
```

then, in another terminal, cd to the root of this repo and run the following:
```bash
python bot.py
```

now your curation agent is running as well as your honcho fact memory bot. so the honcho fact memory bot is listening to the honcho database waiting to derive facts when new messages are written there. the curation bot is working in discord waiting to entertain your curations :)
