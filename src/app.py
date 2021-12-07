import logging

logging.basicConfig(level=logging.INFO)

import asyncio
import os

import meraki.aio
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp

app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])


async def chunks(lst, n):
    chunked_lst = []
    for i in range(0, len(lst), n):
        chunked_lst.append(lst[i:i + n])
    return chunked_lst

@app.message('hello')
async def say_hello(ack, say, logger):
    logger.info("Hey there")
    await ack()
    await say('hey there')

@app.event('app_mention')
async def handle_mentions(event, client, say, logger):
    logger.info("App mention")
    api_response = await client.reactions_add(
        channel=event['channel'],
        timestamp=event['ts'],
        name='eyes'
    )

    await say("Hey")

@app.view("socket_modal_submission")
async def submission(ack):
    await ack()


# export SLACK_APP_TOKEN=xapp-***
# export SLACK_BOT_TOKEN=xoxb-***

@app.message("ping")
async def ping(ack, say):
    await ack()
    await say("pong")

@app.command("/meraki-orgs")
async def cmd_organizations(ack, say, command, client, logger):
    await ack()
    
    msg = await say("...")
    
    split_command = command['text'].split()

    match len(split_command):
        case 1:
            perPage = int(split_command[0])
            page = 1
        case 2:
            perPage = int(split_command[0])
            page = int(split_command[1])
        case _:
            perPage = 3
            page = 1

    await client.chat_update(
        ts=msg['ts'], 
        channel=msg['channel'],
        text="Connecting to Meraki Dashboard API...")
    
    try:
        async with meraki.aio.AsyncDashboardAPI(os.environ.get('MERAKI_DASHBOARD_API_KEY'), log_path='./log_meraki') as dashboard:
            organizations = await dashboard.organizations.getOrganizations()
    except Exception as e:
        await client.chat_update(
            ts=msg['ts'], 
            channel=msg['channel'],
            text=f"Connection failed.")
        logger.error(e)
        return None

    # with meraki.DashboardAPI(os.environ.get('MERAKI_DASHBOARD_API_KEY'), log_path='./log_meraki') as dashboard:
    #     organizations = dashboard.organizations.getOrganizations()

    organization_chunks = await chunks(organizations, perPage)

    block_header = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Hello,  *{command['user_name']}*.\n\n *These are your managed organizations:*"
            }
        },
        {
            "type": "divider"
        }
    ]

    block_body_organizations = []

    for org in organization_chunks[page]:
        block_body_organizations.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{org['name']}*\nAPI enabled: {':white_check_mark:' if org['api']['enabled'] else ':x:'}\n URL: <{org['url']}>"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Details",
                        "emoji": True
                    },
                    "value": f"get_org_{org['id']}",
                    "action_id": f"get_org"
			    }
            }
        )

    block_footer = [
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Showing *{perPage}* out of *{len(organizations)}* | Page *{page}* of *{len(organization_chunks)}*",
                }
            ]
        }
    ]

    # Only add navigation buttons if more than one page
    if len(organization_chunks) > 1:
        block_nav_buttons = {
            "type": "actions",
            "elements": []
        }
        
        # 'First' btn only if not in first page
        if page != 1:
            block_nav_buttons['elements'].append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "First :black_left_pointing_double_triangle_with_vertical_bar:",
                        "emoji": True
                    },
                    "value": "first"
                }
            )   

        # 'Prev' btn only if beyond second page
        if page > 2:
            block_nav_buttons['elements'].append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Previous :arrow_backward:",
                        "emoji": True
                    },
                    "value": "prev"
                }
            )
        
        # 'Next' only if before penultimate page
        if page < len(organization_chunks) - 1:
            block_nav_buttons['elements'].append(
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Next :arrow_forward:",
                        "emoji": True
                    },
                    "value": "next"
                }
            )

        # 'Last' only if not in last page
        if page != len(organization_chunks):
            block_nav_buttons['elements'].append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Last :black_right_pointing_double_triangle_with_vertical_bar:",
                    "emoji": True
                },
                "value": "last"
            })


        block_pages_buttons = [
        {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": str(n),
                "emoji": True
            },
            "value": f"page_{n}"
        } for n in range(1, len(organization_chunks)+1) if n != page]
        
        block_nav_buttons['elements'].extend(block_pages_buttons)
        block_footer.append(block_nav_buttons)

    await client.chat_update(
        ts=msg['ts'], 
        channel=msg['channel'],
        blocks=block_header + block_body_organizations + block_footer,
        text=f"{len(organizations)} organizations have been found."
    )

# TODO: Set get_org up and running
# @app.action("get_org")
# def get_organization():
#     pass

async def ack_shortcut(ack):
    await ack()

async def open_modal(body, client):
    await client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "socket_modal_submission",
            "submit": {
                "type": "plain_text",
                "text": "Submit",
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel",
            },
            "title": {
                "type": "plain_text",
                "text": "Socket Modal",
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "q1",
                    "label": {
                        "type": "plain_text",
                        "text": "Write anything here!",
                    },
                    "element": {
                        "action_id": "feedback",
                        "type": "plain_text_input",
                    },
                },
                {
                    "type": "input",
                    "block_id": "q2",
                    "label": {
                        "type": "plain_text",
                        "text": "Can you tell us your favorites?",
                    },
                    "element": {
                        "type": "external_select",
                        "action_id": "favorite-animal",
                        "min_query_length": 0,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select your favorites",
                        },
                    },
                },
            ],
        },
    )

app.shortcut("socket-mode")(ack=ack_shortcut, lazy=[open_modal])

@app.event("app_home_opened")
async def update_home_tab(client, event, logger):
    try:
        logger.info("Updating home tab")
        # views.publish is the method that your app uses to push a view to the Home tab
        await client.views_publish(
            # the user that opened your app's app home
            user_id=event["user"],
            # the view object that appears in the app home
            view={
                "type": "home",
                "callback_id": "home_view",

                # body of the view
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Welcome to your _App's Home_* :tada:"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "This button won't do much for now but you can set up a listener for it using the `actions()` method and passing its unique `action_id`. See an example in the `examples` folder within your Bolt app."
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "Hello world, I guess."
                            }
                        ]
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Click me!"
                                }
                            }
                        ]
                    }
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


async def main():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    if not os.path.isdir('./log_meraki'):
        os.mkdir('./log_meraki')
    asyncio.run(main())
