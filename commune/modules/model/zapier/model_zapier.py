import imaplib
import email
import discord
import commune as c
import asyncio
import logging
from .config import userEmail, password, imap_host, imap_port, mail_channel_id, token
from email.header import decode_header
from discord.ext import tasks
from discord.ext import commands
from discord import Embed
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@commands.command(name='info')
async def info(ctx):
    """Provides information about the bot."""
    print("info called")
    embed = discord.Embed(title="Bot Information", description="EmailToDiscordBot", color=0x3498db)
    embed.add_field(name="Version", value="1.0.0", inline=False)
    embed.add_field(name="Author", value="Shahjab", inline=False)
    # Add more fields as necessary
    await ctx.send(embed=embed)


@commands.command(name='status')
async def status( ctx):
    """Responds with the bot's current status."""
    await ctx.send("I'm online and operational!")

class EmailToDiscordBot(c.Module):

    def __init__(self):
        self.user = userEmail
        self.password = password
        self.host = imap_host
        self.port = imap_port
        self.mail_channel_id = mail_channel_id
        self.token = token
        # self.client = discord.Client(intents=discord.Intents.default())
        self.mail = imaplib.IMAP4_SSL(self.host, self.port)
        self.mail.login(self.user, self.password)
        intents = discord.Intents.default()
        intents.messages = True  # Enables messages events
        intents.message_content = True  # Enables message content
        self.client = commands.Bot(command_prefix="!", intents=intents)
        
        self.client.add_command(info)
        self.client.add_command(status)

    def parse_email(self, raw_email):

        email_message = email.message_from_bytes(raw_email)

        email_details = {
            'from': decode_header(email_message["From"])[0][0],
            'subject': decode_header(email_message["Subject"])[0][0],
            'body': '',
            'attachments': 0
        }

        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                email_details['attachments'] += 1

            elif content_type == "text/plain" and "attachment" not in content_disposition:
                email_details['body'] += part.get_payload(decode=True).decode()

            elif content_type == "text/html":
                html_content = part.get_payload(decode=True).decode()
                soup = BeautifulSoup(html_content, "html.parser")
                email_details['body'] += soup.get_text()

        return email_details

    async def check_email(self):
        self.mail.select('inbox')
        status, unseen_msg_nums = self.mail.search(None, 'UNSEEN')

        if status == 'OK':
            for num in unseen_msg_nums[0].split():
                status, data = self.mail.fetch(num, '(RFC822)')

                if status == 'OK':
                    email_details = self.parse_email(data[0][1])
                    channel = self.client.get_channel(self.mail_channel_id)

                    if channel:
                        embed = Embed(title="New Email", color=0x3498db)
                        embed.add_field(name="From", value=email_details['from'], inline=False)
                        embed.add_field(name="Subject", value=email_details['subject'], inline=False)
                        embed.add_field(name="Body", value=email_details['body'], inline=False)

                        print(f"From: {email_details['from']}")
                        print(f"Subject: {email_details['subject']}")
                        print(f"Body: {email_details['body']}")

                        if email_details['attachments'] > 0:
                            embed.add_field(name="Attachments", value=f"{email_details['attachments']} attachments", inline=False)

                        await channel.send(embed=embed)

                    else:
                        print(f"Cannot find channel")

    def processing_email(raw_email):
        # Parse raw email bytes to an email message
        email_message = email.message_from_bytes(raw_email)

        # Initialize email details
        details = {
            'from': '',
            'subject': '',
            'body': '',
            'attachments': 0
        }

        # Decode email header details
        details['from'] = decode_header(email_message["From"])[0][0]
        details['subject'] = decode_header(email_message["Subject"])[0][0]

        # Process each part of the email
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                details['attachments'] += 1

            elif content_type == "text/plain" and "attachment" not in content_disposition:
                details['body'] += part.get_payload(decode=True).decode()

            elif content_type == "text/html":
                html_content = part.get_payload(decode=True).decode()
                soup = BeautifulSoup(html_content, "html.parser")
                details['body'] += soup.get_text()

        return details

    @tasks.loop(seconds=3)
    async def email_check_loop(self):
        await self.check_email()

    async def on_ready(self):
        logger.info(f"Logged in as {self.client.user}")
        self.email_check_loop.start()

    async def on_message(self, message):
        if message.author == self.client.user:
            return
        message_content = message.content
        print(f"message_content: {message_content}")
        channel = self.client.get_channel(self.mail_channel_id)
        if message_content == '!info':
            embed = Embed(title="Bot Information", description="EmailToDiscordBot", color=0x3498db)
            embed.add_field(name="Version", value="1.0.0", inline=False)
            embed.add_field(name="Author", value="Shahjab", inline=False)
            # await channel.send(embed = embed)
        await self.client.process_commands(message)

    # @commands.command(name='checkmail')
    # async def check_mail_command(self, ctx):
    #     """Manually triggers email checking."""
    #     await ctx.send("Checking mailbox...")
    #     await self.check_email()


    def run(self):
        self.client.event(self.on_ready)
        self.client.event(self.on_message)
        self.client.run(self.token)

    @classmethod
    def start_bot(cls):
        bot = cls()
        bot.run()


# if __name__ == "__main__":
#     bot = EmailToDiscordBot()
#     bot.run()