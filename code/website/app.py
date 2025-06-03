import requests
import flask
import orjson
import datetime
import werkzeug.exceptions

from traceback import format_exception
from os import name
from hashlib import sha512
from urllib.parse import quote
from traceback import format_exc
from flask import request, session, Flask, flash, url_for, abort
from werkzeug.routing import MapAdapter
from logging import getLogger
from colorama import Fore

from bots.shared.hints import CookieData, TAuthData, SettingsData
from etc.logger import create_logger
from etc.database import Database, User, AuthData
from etc.secret import Encrypt, Decrypt

from typing import (
    Optional,
    Union,
    Literal,
    List,
    Callable,
    Dict,
    Any
)

create_logger('web')
log = getLogger('web')
# Use __name__ instead of string = pain pain pain
app = Flask(
    'application',
    static_folder='website/assets',
    template_folder='website/templates'
)
database = Database()
_ed_params = {
    'key': 'pineappleoneinsteinshead3',
    'seed': 237864,
    'encoding': 'utf-8'
}
encrypt = Encrypt(**_ed_params)
decrypt = Decrypt(**_ed_params)
if name.lower() == 'nt':
# if True:
    BASE = 'https://1550-83-99-204-165.ngrok-free.app'
else:
    BASE = 'https://uid.wtf'

BASE_DISCORD = 'https://discord.com/api'
CLIENT_ID = 1371480853313490966
CLIENT_TOKEN = 'MTM3MTQ4MDg1MzMxMzQ5MDk2Ng.G31Kre.iA-hR5Jtg3Tfe2P-6LjfIOurQfdfy6erzR8R-c'
GUILD_ID = 1371551537649946664
CLIENT_SECRET = 'eLw2EQtXONv-yInjBG1GPgp12GaLhXB7'
REDIRECT_URI = f'{BASE}/callback'
REDIRECT_URI_ENOCDED = quote(REDIRECT_URI)

secret_key = str(CLIENT_TOKEN)
secret_key += str(CLIENT_SECRET)
secret_key += str(CLIENT_ID)
secret_key += str(BASE)
secret_key += str(_ed_params['key'])
secret_key += str(_ed_params['seed'])
secret_key = secret_key.encode()
secret_key = sha512(secret_key)
secret_key = secret_key.hexdigest()
app.secret_key = secret_key
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(weeks=1)



def get_style(response: flask.Response) -> Callable:
    status = response.status

    match int(status[0]):
        case 2:
            return log.info
        
        case 3:
            return log.info

        case 4:
            return log.warning

        case 5:
            return log.error

        case _:
            return log.info



def update_settings(original: SettingsData, new: SettingsData, user_id: int) -> Optional[SettingsData]:
    flagged = False
    
    def check(*content: str):
        nonlocal flagged

        for text in content:
            if '<script>' in text or '</script>' in text:
                flagged = True
                expires = datetime.datetime.now(datetime.UTC).timestamp()
                expires += datetime.timedelta(hours=1).total_seconds()
                database.add_block(user_id, 'XSS attempted.', expires, system=True)
                return


    for key, value in new.items(): # type: ignore
        value: Dict
        if key in ['reasons', 'prefixes']:
            if len(value[key]) == 0:
                continue
            
            values = value[key]
            check(*values)
            if flagged:
                return
                
            original[key] = values
            continue

        for _key, _value in value.items():
            if len(_value) == 0:
                continue
            original[key][_key] = _value

    if flagged:
        return
    return original



def update_token(user: User, *, update: bool = False, code: Optional[str] = None) -> Optional[Union[User, werkzeug.wrappers.response.Response]]:
    timestamp = now().timestamp()
    if user.auth:
        expires = user.auth.expires
    
    else:
        expires = None

    if not expires or (expires and timestamp > expires):
        if code:
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT_URI
            }
        else:
            if user.auth:
                data = {
                    'grant_type': 'refresh_token',
                    'refresh_token': user.auth.refresh_token
                }
            
            else:
                raise Exception(f'No auth for {user.id}')

        headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
        with requests.post(f'{BASE_DISCORD}/oauth2/token', data=data, headers=headers, auth=(CLIENT_ID, CLIENT_SECRET)) as response: # type: ignore
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                flash(f'Server too busy. Please try again later (~{retry_after}s)', 'error')
                return redirect('index')
            response.raise_for_status()
            data = response.json()

        scope = data['scope'].split()
        if not sorted(scope) == sorted(['email', 'identify', 'guilds.join']):
            flash('Invalid scope!', 'error')
            return redirect('index')
        
        auth_data: TAuthData = {
            'id': 0,
            'username': '',
            'avatar': '',
            'access_token': data['access_token'],
            'token_type': data['token_type'],
            'expires': int(timestamp + data['expires_in']),
            'refresh_token': data['refresh_token'],
            'scope': data['scope'],
            'email': ''
        }
        user.auth = AuthData(auth_data)

        if update is True:
            if database.update_user(user):
                return user
            return None
    return user


def refresh_user(user: User, *, update: bool = False) -> Optional[Union[User, werkzeug.wrappers.response.Response]]:
    if not user.auth or not user.auth.access_token:
        return None
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {user.auth.access_token}'
    }
    with requests.get(f'{BASE_DISCORD}/users/@me', headers=headers) as response:
        if response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                flash(f'Server too busy. Please try again later (~{retry_after}s)', 'error')
                return redirect('index')
        response.raise_for_status()
        data: dict = response.json()

    user.id = int(data['id']) if data.get('id') else None # type: ignore
    user.auth.id = int(data['id']) if data.get('id') else None # type: ignore
    user.auth.username = data.get('username') # type: ignore
    user.auth.email = data.get('email') # type: ignore

    if data['avatar']:
        avatar = f'https://cdn.discordapp.com/avatars/{user.id}/{data['avatar']}.gif'
        with requests.get(avatar) as response:
            if not response.status_code == 200:
                avatar = avatar[:-3] + 'png'
        user.auth.avatar = avatar

    else:
        index = int((user.id >> 22) % 6)
        user.auth.avatar = f'https://cdn.discordapp.com/embed/avatars/{index}.png'
                
    if update:
        database.update_user(user)
    return user


def get_session_data() -> Union[Dict[Any, Any], CookieData]:
    if name == 'nt':
        return {
            'id': 1347995638414970930,
            'avatar': 'https://cdn.discordapp.com/avatars/1347995638414970930/2f0ca9b9a64c447ab1e495a1f4efa3bf.png?size=16',
            'name': 'bxod'
        }

    data: Optional[bytes] = session.get('data')
    if not data:
        return {}
    
    result = decrypt.from_bytes(data)
    result = orjson.loads(result.read())
    return result


def save_session_data(data: Union[Dict[Any, Any], CookieData], *, overwrite: bool = False) -> bool:
    existing_data = get_session_data()

    if None in [existing_data, data]:
        return False
    
    if not overwrite:
        existing_data.update(data)

    else:
        existing_data = data

    payload: bytes = orjson.dumps(existing_data)
    result = encrypt.from_str(payload.decode())
    session['data'] = result.getvalue()
    return True


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def redirect(endpoint: str) -> werkzeug.wrappers.response.Response:
    return flask.redirect(url_for(f'route_{endpoint}'))



@app.before_request
def before_request():
    data = get_session_data()
    if data is None:
        abort(400)
    
    session.permanent = True

    if 'id' in data:
        user = database.get_user(data['id'])
        block = database.get_block(data['id'])

        if block:
            if user and not user.elevated:
                return flask.render_template(
                    'blocked.html',
                    timestamp=block['expires'],
                    message=block['reason'],
                    system=block['system']
                ), 403
        
        elif user and user.blacklisted:
            return flask.render_template(
                'blocked.html',
                timestamp='never',
                message='This user is blacklisted.'
            ), 403


    if request.path == '/admin' or request.path.startswith('/admin/'):
        adapter: MapAdapter = app.url_map.bind('')
        try:
            # Make sure the endpoint actually exists
            _, _ = adapter.match(request.path, method=request.method)
        
        except (werkzeug.exceptions.NotFound, werkzeug.exceptions.MethodNotAllowed):
            abort(404)
        
        user = database.get_user(data.get('id', 0))        
        if user is None:
            # Not logged in
            abort(401)

        elif not user.elevated:
            # No permissions to visit dashboard
            abort(403)



@app.after_request
def after_request(response: flask.Response):
    remote = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    get_style(response)(f'{remote} -- {request.url} {response.status}')
    if response.status_code == 403:
        return response
        
    response.headers['Content-Security-Policy'] = 'script-src \'self\' https://cdn.jsdelivr.net/npm/tsparticles@1.37.0/tsparticles.min.js https://cdn.jsdelivr.net/npm/tsparticles@1.37.0/tsparticles.pathseg.js; object-src \'none\';'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'geolocation=(self), microphone=()'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Expect-CT'] = 'max-age=86400, enforce, report-uri="https://uid.wtf/report'
    response.headers['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response



@app.route('/', methods=['get'])
def route_index():
    if 'message' in request.headers:
        flash(request.headers['message'], request.headers.get('message-type', 'success'))
    data = get_session_data()
    return flask.render_template('index.html', data=data)


@app.route('/login', methods=['get'])
def route_login():
    data = get_session_data()
    if 'name' in data:
        flash('You are already logged in!', 'success')
        return redirect('index')
    return redirect('auth_redirect')


@app.route('/logout', methods=['get'])
def route_logout():
    data = get_session_data()
    # I know this would be the dumbest shit ever
    # save_session_data({'endpoint': 'logout'})
    if not data:
        return abort(401)
    
    if save_session_data({}, overwrite=True):
        flash('Successfully logged out!', 'success')

    else:
        flash('Failed to log out!', 'error')
    return redirect('index')


@app.route('/join', methods=['get'])
def route_join():
    try:
        data = get_session_data()
        user_id = data.get('id')
        user = database.get_user(user_id) if user_id else None
        
        if not user:
            save_session_data({'endpoint': 'join'})
            return redirect('auth_redirect')
        
        if not user and user_id:
            user = User.new_user(user_id)
        
        user = update_token(user)
        if not user:
            flash('Failed to check user. Please back up your account again!', 'error')
            return redirect('index')
        
        if isinstance(user, werkzeug.wrappers.response.Response):
            return user
        
        if not user.auth:
            raise Exception(f'No auth data for {user.id}')

        data = { 'access_token': user.auth.access_token }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bot {CLIENT_TOKEN}'
        }

        with requests.put(f'{BASE_DISCORD}/guilds/{GUILD_ID}/members/{user.id}', json=data, headers=headers) as response:
            response.raise_for_status()
            if response.status_code == 204:
                flash('User already in server!', 'success')
                return redirect('index')
            
            if response.status_code == 201:
                flash('User added to server!', 'success')
                return redirect('index')
        flash(f'Nothing happened ;/ ({response.status_code})', 'error')
        return redirect('index')

    except Exception as exc:
        print(format_exc())
        flash(f'{type(str).__name__}: {str(exc)}', 'error')
        return redirect('index')
    

@app.route('/discord', methods=['get'])
def route_discord():
    return flask.redirect('https://discord.gg/ham')
    

@app.route('/data', methods=['get'])
def route_data():
    return flask.render_template('data.html')
    

@app.route('/team', methods=['get'])
def route_team():
    data = get_session_data()
    if not data:
        abort(401)
    return flask.render_template('team.html')
    

@app.route('/leaderboard', methods=['get'])
def route_leaderboard():
    data = get_session_data()
    if not data:
        abort(401)
    return flask.render_template('leaderboard.html')


@app.route('/auth-redirect', methods=['get'])
def route_auth_redirect():
    return flask.redirect(f'https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI_ENOCDED}&scope=identify+email+guilds.join')


@app.route('/callback', methods=['get'])
def route_auth_callback():
    def to_start():
        data = get_session_data()
        endpoint = data.get('endpoint')
        if endpoint:
            data.pop('endpoint')
            save_session_data(data, overwrite=True)
            return redirect(endpoint)
        return redirect('index')


    code = request.args.get('code')
    if not code:
        flash('Invalid request!', 'error')
        return redirect('index')
    
    try:
        data = get_session_data()
        user = User.new_user(0)
        
        try:
            user = update_token(user, code=code)
        
        except requests.HTTPError as exc:
            if data.get('endpoint'):
                return to_start()
            raise exc

        if isinstance(user, flask.Response):
            return user
        
        if not user:
            raise Exception('?')

        user = refresh_user(user) # type: ignore
        if isinstance(user, werkzeug.wrappers.response.Response):
            return user
        
        if not user or not user.auth or None in (user.id, user.auth.id, user.auth.username, user.auth.email):
            return flask.render_template('index.html', message='Invalid response from Discord.')
        
        _user = database.get_user(user.id)
        if not _user and not database.add_user(user):
            flash('Failed to log in!', 'error')
            return to_start()
        
        elif _user:
            user.is_blacklisted = user.blacklisted
            user.is_premium = _user.premium
            user.is_admin = _user.admin
            user.is_owner = _user.is_owner
            # _user.auth = user.auth
            # user = user
            if not database.update_user(user):
                flash('Failed to log in!', 'error')
                return to_start()

        save_session_data({
            'name': user.auth.username,
            'id': user.auth.id,
            'avatar': user.auth.avatar
        })
        flash('Logged in!', 'success')
        return to_start()
        
    except Exception as exc:
        print(format_exc())
        flash(f'{type(str).__name__}: {str(exc)}', 'error')
        return to_start()
    

@app.route('/admin', methods=['get'])
def route_admin():
    data = get_session_data()
    user = database.get_user(data['id'])
    return flask.render_template('admin/admin.html', user=user)
    

@app.route('/admin/users', methods=['get'])
def route_admin_users():
    data = get_session_data()
    user = database.get_user(data['id'])
    return flask.render_template('admin/users.html', user=user)
    

@app.route('/admin/bot', methods=['get'])
def route_admin_config():
    data = get_session_data()
    user = database.get_user(data['id'])
    return flask.render_template('admin/bot.html', user=user)
    

@app.route('/settings', methods=['get', 'patch'])
def route_settings():
    data = get_session_data()
    
    if data is None or not 'id' in data:
        return abort(401)
    
    user = database.get_user(data['id'])
    if not user or not user.premium:
        abort(403)

    if request.method.lower() == 'patch':
        if not request.json:
            return flask.Response(status=400)

        json: Dict[str, Any] = request.json
        settings: SettingsData = json['settings']
        reset: Optional[Literal[True]] = json.get('reset')

        if reset is True:
            user.settings.raw_data = database.default_settings
        
        else:
            if not settings:
                flash('No settings were saved!', 'error')
            
            else:
                user = database.get_user(data['id'])
                if not user:
                    flash('User not found!', 'error')
                    return flask.Response(status=401)
                
                new = update_settings(user.settings.raw_data, settings, user.id)
                if new is None:
                    flash('Illegal settings detected', 'error')
                    return flask.Response(status=400)
                user.settings.raw_data = new

        if database.update_user(user):
            flash('Settings saved!', 'success')
        
        else:
            flash('Settings NOT saved!', 'error')
        return flask.Response(status=200)
    return flask.render_template('settings.html', settings=user.settings.raw_data, len=len), 200
    



@app.errorhandler(400)
def err_400(error: Exception):
    save_session_data({'endpoint': request.path.removeprefix('/')})
    return flask.render_template('badrequest.html'), 401
    

@app.errorhandler(401)
def err_401(error: Exception):
    save_session_data({'endpoint': request.path.removeprefix('/')})
    return flask.render_template('unauthorized.html'), 401


@app.errorhandler(403)
def err_403(error: Exception):
    return flask.render_template('forbidden.html'), 403


@app.errorhandler(404)
def err_404(error: Exception):
    return flask.render_template('notfound.html'), 404


@app.errorhandler(500)
def err_500(error: Exception):
    return flask.render_template('internalerror.html', message=str(error)), 500



def developer_run():
    with database:
        database.connect()
        app.run(host='0.0.0.0', port=80, debug=True)


def application_run():
    from waitress import serve
    with database:
        database.connect()
        serve(app, host='0.0.0.0', port=80)