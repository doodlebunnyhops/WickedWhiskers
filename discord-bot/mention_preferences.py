"""Player-controlled public mention preferences, scoped to a server."""
import re
import discord
import db_utils as db

PATTERN=re.compile(r'<@!?(\d+)>')


def initialize_schema(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS player_mentions (guild_id INTEGER, player_id INTEGER, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), PRIMARY KEY(guild_id,player_id))')


def enabled(guild_id,player_id):
    row=db.get_db_connection().execute('SELECT enabled FROM player_mentions WHERE guild_id=? AND player_id=?',(guild_id,player_id)).fetchone()
    return bool(row[0]) if row else True


def configure(guild_id,player_id,value):
    if type(value) is not bool:raise ValueError('Expected a boolean')
    with db.transaction() as conn:
        conn.execute('INSERT OR REPLACE INTO player_mentions VALUES(?,?,?)',(guild_id,player_id,int(value)))


class Announcement:
    def __init__(self,guild):
        self.guild=guild
        self.muted={row[0] for row in db.get_db_connection().execute('SELECT player_id FROM player_mentions WHERE guild_id=? AND enabled=0',(guild.id,))}

    def label(self,uid):
        if uid not in self.muted:return f'<@{uid}>'
        member=self.guild.get_member(uid) if hasattr(self.guild,'get_member') else None
        name=member.display_name[:32] if member else str(uid)
        return discord.utils.escape_markdown(discord.utils.escape_mentions(name).replace('<@','<\u200b@'))

    def text(self,value):
        return PATTERN.sub(lambda m:self.label(int(m[1])),value)

    def message(self,value):
        if isinstance(value,str):return self.text(value)
        result=value.copy()
        if result.title:result.title=self.text(result.title)
        if result.description:result.description=self.text(result.description)
        for i,f in enumerate(result.fields):result.set_field_at(i,name=self.text(f.name),value=self.text(f.value),inline=f.inline)
        return result

    def allowed(self,value):
        texts=[value] if isinstance(value,str) else [value.title or '',value.description or '',*[v for f in value.fields for v in (f.name,f.value)]]
        ids={int(uid) for text in texts for uid in PATTERN.findall(text)}-self.muted
        return discord.AllowedMentions(everyone=False,roles=False,replied_user=False,users=[discord.Object(id=uid) for uid in sorted(ids)])
