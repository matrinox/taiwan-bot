import sys
import traceback
import json
from datetime import datetime
from http import HTTPStatus

from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
    ConversationState,
    MemoryStorage
)
from fastapi import FastAPI, Request, HTTPException
from botbuilder.schema import Activity, ActivityTypes

from bots import FAQBot
from config import DefaultConfig
import taiwan_bot_sheet

CONFIG = DefaultConfig()

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
settings = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
adapter = BotFrameworkAdapter(settings)

# Catch-all for errors.


async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity, which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)


adapter.on_turn_error = on_error

tbs = taiwan_bot_sheet.TaiwanBotSheet()
memory = MemoryStorage()
conversation_state = ConversationState(memory)
bot = FAQBot(tbs, conversation_state)
app = FastAPI()


@app.get("/healthcheck")
def healthcheck():
    # for https://cron-job.org/ to keep heroku alive
    return {"message": "I'm alive and well! Thank you!"}


@app.get("/sheet")
def sheet():
    tbs = taiwan_bot_sheet.TaiwanBotSheet(
        taiwan_bot_sheet.SpreadsheetContext.GOLDCARD)
    tbs.log_answers("shoul", "be", "in Goldcard gc logs", 1.2)
    tbs.set_context(taiwan_bot_sheet.SpreadsheetContext.GENERAL)
    tbs.log_answers("shoul", "be", "in Goldcard general logs", 1)


@app.post("/api/messages")
async def messages(req: Request):
    # Main bot message handler.
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        raise HTTPException(status_code=415)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await adapter.process_activity(activity, auth_header, bot.on_turn)
    if response:
        return {"data": response.body, "status": response.status}
    return {}
