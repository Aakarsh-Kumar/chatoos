from datetime import datetime
from flask_login.utils import login_required, login_user, logout_user, current_user
from db import add_room_members, get_messages, get_room, get_room_members, get_rooms_for_user, get_user, is_room_admin, is_room_member, remove_room_members, save_message, save_room,save_user, is_room_admin, update_room
from bson.json_util import dumps
from flask import Flask, render_template, redirect, request, url_for,session, abort
from flask_socketio import SocketIO,socketio, join_room, leave_room
from flask_login import LoginManager
from pymongo.errors import DuplicateKeyError
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests   
import os
import pathlib
import requests


app = Flask(__name__,template_folder='templates')
app.secret_key = "0128d79584614d4e92b42cb07032bb0e"
socketio = SocketIO(app, logger = True)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = "722263076239-mrqd0m23c58kr9j3ntttgi8ns5k0lnh7.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="https://chatoos.herokuapp.com/callback"
)


@app.route('/')
def home():
    rooms=[]
    room_members = []
    if current_user.is_authenticated:
        rooms = get_rooms_for_user(current_user.username)
        for room in rooms:
            room_members.append(get_room_members(room['_id']['room_id'])) 
    return render_template("index.html",rooms=rooms, room_members=room_members)

@app.route('/login',methods=['GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        authorization_url, state = flow.authorization_url()
        session["state"] = state
        return redirect(authorization_url)
    
@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    try:
        save_user(id_info.get("email"),id_info.get("name"))
        login_user(get_user(id_info.get("email")))
        
    except DuplicateKeyError:
        login_user(get_user(id_info.get("email")))
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/create-room',methods=['GET','POST'])
@login_required
def create_room():
    message = ''
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        usernames = [username.strip() for username in request.form.get('members').split(',')]

        if len(room_name) and len(usernames):
            room_id = save_room(room_name,current_user.username)

            if current_user.username in usernames:
                usernames.remove(current_user.username)
            add_room_members(room_id,room_name,usernames,current_user.username)
            return redirect(url_for('view_room', room_id=room_id))
        else:
            message = 'Failed to Create Room !'

    return render_template('create_room.html', message=message)
        

@app.route('/rooms/<room_id>')
@login_required
def view_room(room_id):
    room = get_room(room_id)

    if room and is_room_member(room_id,current_user.username):
        room_members = get_room_members(room_id)
        messages = get_messages(room_id)
        return render_template('view_room.html',name =current_user.name ,username=current_user.username, room=room, room_members=room_members, messages=messages)
    else:
        return "Room not found", 404

@app.route('/rooms/<room_id>/messages')
@login_required
def get_older_messages(room_id):
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        page = int(request.args.get('page', 0))
        messages = get_messages(room_id, page)
        return dumps(messages)
    else:
        return "Room not found", 404


@app.route('/rooms/<room_id>/edit', methods=['GET','POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id, current_user.username):
        existing_room_members = [member['_id']['username'] for member in get_room_members(room_id)]
        room_members_str = ",".join(existing_room_members)
        message = ''
        if request.method == 'POST':
            room_name = request.form.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = [username.strip() for username in request.form.get('members').split(',')]
            members_to_add = list(set(new_members) - set(existing_room_members))
            members_to_remove = list(set(existing_room_members) - set(new_members))


            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username)
            
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            
            message = 'Room edited successfully'
            room_members_str = ",".join(new_members)
        return render_template('edit_room.html', room=room, room_members_str=room_members_str, message=message)
    else:
        return "You are not the admin!", 404

@socketio.on('join_room')
def handle_join_room_event(data):
    join_room(data['room'])
    socketio.emit('join_room_announcement',data, room=data['room'])

@socketio.on('send_message')
def handle_send_message_event(data):
    data['created_at'] = datetime.now().strftime("%d %b, %H:%M")
    save_message(data['room'],data['message'],data['username'])
    socketio.emit('receive_message',data,room=data['room'])

@socketio.on('leave_room')
def handle_leave_room_event(data):
    leave_room(data['room'])
    socketio.emit('leave_room_announcement', data, room=data['room'])


@login_manager.user_loader
def load_user(username):
    return get_user(username)

@app.errorhandler(404)
def error_404(e):
    return "404 Not Found"

if __name__ == '__main__':
    # socketio.run(app,debug=True, host="127.0.0.1", port=2222)
    app.run()
