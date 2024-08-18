import json
import uuid

from flask import redirect, request, url_for, current_app as app, session, abort, current_app
from oauth2client.client import OAuth2Credentials
from pydrive2.auth import GoogleAuth, RefreshError
from pydrive2.drive import GoogleDrive

from common import auth_instances
from db import list_users, remove_user, user_updated

# TODO: url_for for redirect_uri

# HTTPS required for oauth, using mkcert here TODO Removeme, prob unused
# See https://github.com/FiloSottile/mkcert/issues/370 for windows

# TODO This should not be leaked, remove and scrub git history in main
oauth_settings = {
    "client_config_backend": "settings",
    "get_refresh_token": True,
    "oauth_scope": ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"],
    "client_config": {
        "client_id": app.config["CLIENT_ID"],
        "client_secret": app.config["CLIENT_SECRET"],
        "redirect_uri": ""
    }
}


def load_drives():
    users = list_users()
    known_users = len(users)
    loaded = 0
    app.logger.info("Loading drives")
    for user in users:
        auth = GoogleAuth(settings=oauth_settings)
        auth.credentials = OAuth2Credentials.from_json(user.creds)
        try:
            auth.Refresh()
            auth.Authorize() # TODO Check for side effects.
            resp, body = auth.http.request("https://www.googleapis.com/oauth2/v2/userinfo")
        except RefreshError as e:
            print("Couldnt refresh\n", e)
            remove_user(user)
            continue
        if resp.status != 200:
            print("Invalid response?", resp.status)
            continue
        # email = json.loads(body)["email"]
        # if user != email:
        #     # Token somehow doesn't match user, skip and delete records
        #     remove_user(user)
        #     continue
        loaded += 1
        auth_instances[user.email] = GoogleDrive(auth)
    app.logger.info(f"Loaded {loaded}/{known_users} drives")

@app.route('/login/')
def login():
    auth = GoogleAuth(settings=oauth_settings)
    auth.GetFlow()
    state = uuid.uuid4().hex
    auth_url = auth.flow.step1_get_authorize_url(state=state)
    session["state"] = state
    return redirect(auth_url)


@app.route('/login/callback')
def login_callback():
    args = request.args
    state = session.get("state", "")
    session.pop("state", None)
    if args.get("state") != state:
        return abort(403)
    if "error" in args:
        return abort(403)  # TODO: Correct status code for user rejected
    auth = GoogleAuth(settings=oauth_settings)
    auth.GetFlow()
    auth.Auth(args.get("code"))
    resp, body = auth.http.request("https://www.googleapis.com/oauth2/v2/userinfo")
    assert resp.status == 200
    email = json.loads(body)["email"]
    auth_instances.setdefault(email, GoogleDrive(auth))
    session["user"] = email
    user_updated(email, auth.credentials.to_json())
    return redirect(url_for("index"))

oauth_settings["client_config"]["redirect_uri"] = url_for('login_callback')