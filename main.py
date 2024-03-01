from flask import Flask, make_response, redirect, request, jsonify, render_template, send_from_directory, render_template_string
import os
import dotenv
import requests
import datetime
import json
import secrets
import threading

app = Flask(__name__)
dotenv.load_dotenv()
URL = os.getenv('PROXY')
RESTRICTED = os.getenv('RESTRICTED')
RESTRICTED = json.loads(RESTRICTED)
RESTRICTED = [f'{i.lower()}/' for i in RESTRICTED]
TLD = os.getenv('TLD')

# Load cookies
cookies = []

if os.path.isfile('cookies.json'):
    with open('cookies.json') as file:
        cookies = json.load(file)
else:
    with open('cookies.json', 'w') as file:
        json.dump(cookies, file)


# region Auth
@app.route('/auth', methods=['POST'])
def auth():
    global cookies
    auth = login(request)
    if auth == False:
        return render_template_string("Failed to authenticate")
    
    # Make sure user has a correct domain
    if not auth.endswith(f'.{TLD}'):
        return render_template_string(f"You need to have a domain on .{TLD} to access this content.")

    resp = make_response(render_template_string("Success"))
    # Gen cookie
    auth_cookie = secrets.token_hex(12 // 2)
    cookies.append({'name': auth, 'cookie': auth_cookie})

    with open('cookies.json', 'w') as file:
        json.dump(cookies, file)

    resp.set_cookie('auth', auth_cookie, max_age=60*60*24*30)
    return resp

@app.route('/logout')
def logout():
    global cookies
    resp = make_response(redirect('/'))
    resp.set_cookie('auth', '', expires=0)

    if 'auth' not in request.cookies:
        return resp
    cookies = [i for i in cookies if i['cookie'] != request.cookies['auth']]
    with open('cookies.json', 'w') as file:
        json.dump(cookies, file)

    return resp

def login(request):
    dict = request.form.to_dict()
    keys = dict.keys()
    keys = list(keys)[0]
    keys = json.loads(keys)
    auth_request = keys['request']
    # return login(auth_request)
    r = requests.get(f'https://auth.varo.domains/verify/{auth_request}')
    r = r.json()
    if r['success'] == False:
        return False
    
    if 'data' in r:
        data = r['data']
        if 'name' in data:
            return data['name']
    return False

# endregion

# Catch all
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    for i in RESTRICTED:
        if path.lower().startswith(i) or path.lower() == i:
            # Check if user is logged in
            if 'auth' not in request.cookies:
                return render_template('auth.html', year=datetime.datetime.now().year,redirect=request.url,tld=TLD)
            auth = request.cookies['auth']
            if not any(i['cookie'] == auth for i in cookies):
                return render_template('auth.html', year=datetime.datetime.now().year,redirect=request.url,tld=TLD)
            break

    

    res = requests.request(
        method          = request.method,
        url             = request.url.replace(request.host_url, f'{URL}/'),
        headers         = {k:v for k,v in request.headers if k.lower() != 'host'},
        data            = request.get_data(),
        cookies         = request.cookies,
        allow_redirects = False,
    )
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection'] 
    headers          = [
        (k,v) for k,v in res.raw.headers.items()
        if k.lower() not in excluded_headers
    ]
    
    # Replace all instances of the proxy URL with the local URL
    # If content type is html
    if 'text/html' in res.headers['Content-Type']:
        content = res.content.decode('utf-8')
        content = content.replace(URL, request.host_url)
        # TMP: Replace other domains
        content = content.replace('https://alee.freeconcept/', request.host_url)
        response = make_response(content, res.status_code, headers)
        return response
    
    response = make_response(res.content, res.status_code, headers)
    return response

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')