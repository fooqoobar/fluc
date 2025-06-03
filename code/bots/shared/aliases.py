import discord

from typing import Union, Type, TypeAlias



def check_alias(obj: Type, alias: TypeAlias) -> bool:
    return isinstance(obj, alias.__args__) # type: ignore



ManagableMember: TypeAlias = Union[discord.Member, discord.User, int, str]
Duration: TypeAlias = Union[str, int]