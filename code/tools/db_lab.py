import asyncio

from etc.database import Database, User


db = Database(local=True)




async def main():
    await db.connect()
    user = await db.get_user(1347995638414970930)
    if not user:
        user = User.new_user(1347995638414970930)
        user.is_admin = True
        user.is_owner = True
        await db.add_user(user)

    result = await db.set_nuke(user, 3331293782, [76894356873242, 234532545342534])
    print(result)



asyncio.run(main())

# import sqlite3
# import orjson

# con = sqlite3.connect('data/database.db')
# c = con.cursor()
# c.execute('INSERT INTO data(id, users, servers) VALUES(?, ?, ?)', (23498237498, orjson.dumps([]), orjson.dumps([23234347892, 32987234987])))
# c.execute('INSERT INTO data(id, users, servers) VALUES(?, ?, ?)', (234982243224337498, orjson.dumps([]), orjson.dumps([2354335434234347892, 432342332987234987])))
# con.commit()