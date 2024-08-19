from __future__ import annotations

import logging
from functools import wraps
from io import BytesIO
from typing import Optional, cast

from flask import Flask, request, Response, session, redirect, url_for, current_app
from jinjax import Catalog
from pydantic import BaseModel, ValidationError
import tomli

from common import BaseFolder
from db import get_user, find_file, find_parent, find_children, get_roots
from filetypes import ParentFolder, Folder, DriveFile

app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)


# This thing requires keys to be in uppercase for some weird reason
assert app.config.from_file("secrets.toml", load=tomli.load, text=False)
app.config.from_prefixed_env()
app.secret_key = app.config["SECRET_KEY"]


catalog = Catalog(jinja_env=app.jinja_env)
catalog.add_folder("./components")
app.jinja_env.globals["cat"] = catalog


def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session['user'] is None:
            return Response("You are not logged in", 401)
        return f(*args, **kwargs)
    return decorated_function


# https://www.tldraw.com/r/LcwcHPwUKAt9JRsZB_Imy?v=-1054,-284,3543,1878&p=page

@app.route('/')
def index():
    if "user" not in session:
        return catalog.render("Index", user=None, items=[])
    root_folders = get_roots()
    root_folders = [folder for folder in root_folders if folder.can_read(session["user"])]
    return catalog.render("Index", user=session["user"], items=root_folders)

@app.route('/<item_id>')
def item_view(item_id: str):  # put application's code here
    if "user" not in session:
        return catalog.render("Index", user=None, items=[])
    item = find_file(item_id)
    if item is None:
        return redirect(url_for('index'))
    parent = find_parent(item_id)
    if isinstance(item, DriveFile):
        # TODO Query for siblings
        return catalog.render("Index", user=session["user"], items=find_children(parent.id), prev=parent, current=item)
    children = find_children(item_id)
    return catalog.render("Index", user=session["user"], items=children, prev=parent, current=item)

def bad_args_response(err: ValidationError):
    return Response(str(err), 400)

class CreateArgs(BaseModel):
    name: str # TODO proper validation
    folder_type: str # TODO ensure folder type exists
    parent: Optional[str] = None
    # meta: Dict # TODO Make this some generic thing based on folder_type

@app.route("/a/create", methods=["POST"])
@require_login
def create_folder():
    try:
        args = CreateArgs(**request.form)
    except ValidationError as e:
        return bad_args_response(e)
    if args.folder_type == "ParentFolder": # TODO maybe enum this
        user = get_user(session["user"])
        if user is None or user.role != "Admin":
            return Response("You are not allowed to create folders", 403)
        ParentFolder.make(session["user"], args.name)
        return Response("Folder created", 201)
    else:
        parent: Optional[Folder] = find_file(args.parent) if args.parent else None
        if parent is None:
            return Response("No such folder found", 400)
        if not isinstance(parent, BaseFolder):
            return Response("File must be created in a folder", 400)
        parent.create_folder(session["user"], args.name)
        return Response("Folder created", 201)


class FileUploadArgs(BaseModel):
    item_id: str

@app.route("/a/upload", methods=["POST"])
@require_login
def upload_file():
    try:
        args = FileUploadArgs(**request.form)
    except ValidationError as e:
        return Response('Bad args', 400)
    item = find_file(args.item_id) if args.item_id else None
    if item is None:
        return Response("Valid file/folder required", 400)
    file = request.files["file"]
    if file is None:
        return Response("No file uploaded", 400)
    data = file.stream.read() # TODO maybe stream this for big files
    io_object = BytesIO(data)
    if isinstance(item, DriveFile):
        # TODO rename file
        item.upload(io_object, file.mimetype) # TODO
    else:
        cast(BaseFolder, item).create_file(session['user'], file.name, io_object, mimetype=file.mimetype)
    return Response("File uploaded", 201)


class DeleteArgs(BaseModel):
    id: str
@app.route("/a/delete", methods=["POST"])
@require_login
def delete_item():
    try:
        args = DeleteArgs(**request.form)
    except ValidationError as e:
        return Response('Bad args', 400)
    item = find_file(args.id)
    if item is None:
        return Response("Invalid item id", 400)

    if isinstance(item, ParentFolder):
        if not item.owner != session["user"]: # TODO access control for parent folders idk
            return Response("You are not allowed to delete this folder", 403)
        item.delete_self()
    parent = find_parent(args.id)
    if not parent.can_write(session["user"]):
        return Response("You are not allowed to delete items", 403)
    # Since a parent was found for this child, we assume the child exists
    parent.delete_child(args.id)
    return Response("Item deleted", 200)

with app.app_context():
    import auth  # noqa
    auth.load_drives()

if __name__ == '__main__':
    # IMPORTANT DO NOT RUN FROM ITELLIJ/, IT RUNS THE FLASK MODULE WHICH DOES NOT RESPECT APP.RUN()
    app.run(port=5000, debug=False, ssl_context=("localhost.pem", "localhost-key.pem"))