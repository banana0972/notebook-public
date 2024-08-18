from __future__ import annotations

import sqlite3

import typing
from typing import Optional, Dict, cast, List

from pydantic import BaseModel

from common import Item, BaseFolder, type_mappings
if typing.TYPE_CHECKING:
    from filetypes import ParentFolder

DB_FILE = "database.db"


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

# TODO All Items can be pooled, just need to refresh them when retrieved

class User(BaseModel):
    email: str
    role: str
    creds: str

def get_user(email: str) -> Optional[User]:
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = dict_factory
        result = conn.execute("SELECT * FROM users WHERE email = ?", [email]).fetchone()
        if result is None:
            return None
        return User(**result)

def list_users() -> List[User]:
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = dict_factory
        results = conn.execute("SELECT * FROM users").fetchall()
        return [User(**result) for result in results]

def user_updated(email: User, creds: str):
    with sqlite3.connect(DB_FILE) as conn:
        script = """
        INSERT INTO users (email, role, creds) 
        VALUES (?, 'User', ?) ON CONFLICT(email)
        DO UPDATE SET creds = ? WHERE email = ?
        """
        conn.execute(script, (email, creds, creds, email))

def remove_user(user: User):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM users WHERE email = ?", [user.user])


def item_created(file: Item):
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        file_id: str = file.gfile['id']
        cur.execute("""
        INSERT INTO Items(id, fileType, owner, metadata) VALUES (?, ?, ?, ?)""",
                     (file_id, file.filetype, file.owner, "")) # TODO METADATA
        cur.execute("INSERT INTO ClosureTable (childId, parentId, depth) values (?, ?, 0)", (file_id, file_id))
        if file.parent is not None:
            script = """
            INSERT INTO ClosureTable(parentId, childId, depth)
            SELECT p.parentId, c.childId, p.depth + c.depth+1
            FROM closuretable p, closuretable c
            WHERE p.childId = ? AND c.parentId = ? -- First arg is child, 2nd is parent
            """
            cur.execute(script, (file.parent, file_id))


def find_file(file_id: str) -> Optional[Item]:
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = dict_factory
        result: Dict = conn.execute("SELECT * FROM Items WHERE id = ? LIMIT 1", [file_id]).fetchone()
        if result is None:
            return None
        return type_mappings[result["fileType"]](**result)
        # TODO return a representation of file from db


def find_parent(file_id: str, root: bool = False) -> Optional[BaseFolder]:
    """
    Notes: The root of an item might be itself, beware
    """
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = dict_factory
        script = f"""
        SELECT Items.id, fileType, owner, metadata FROM Items 
        JOIN ClosureTable ON Items.id = ClosureTable.parentId 
        WHERE ClosureTable.childId = ? AND {"DEPTH != 0" if not root else ""} -- Skip self ref if finding direct parent.
        ORDER BY depth {"DESC" if root else ""} LIMIT 1 -- Find parent with the highest depth to child if finding root
        """
        result: Dict = conn.execute(script, [file_id]).fetchone()
        # TODO Match based on filetype
        if result is None:
            return None
        return cast(BaseFolder, type_mappings[result['fileType']](**result))

def find_children(parent_id: str) -> List[Item]:
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = dict_factory
        script = """
        SELECT Items.id, fileType, owner, metadata FROM Items
        JOIN ClosureTable on Items.id = ClosureTable.childId
        WHERE ClosureTable.parentId = ? AND depth = 1
        """
        results: List[Dict] = conn.execute(script, [parent_id]).fetchall()
        print('children', results)
        return [type_mappings[result["fileType"]](**result) for result in results]

def get_roots() -> List[ParentFolder]:
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = dict_factory
        results = conn.execute("SELECT * FROM Items WHERE fileType = 'ParentFolder'")
        return [type_mappings["ParentFolder"](**result) for result in results] # noqa TODO cant use cast since it needs to resolve ParentFolder at runtime.


def item_removed(file: Item):
    file_id: str = file.gfile['id']
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM Items where id = ?", [file_id])
        script = """
        DELETE FROM ClosureTable WHERE childId in 
        (SELECT childId from ClosureTable WHERE parentId = ?)
        """
        cur.execute(script, [file_id])


