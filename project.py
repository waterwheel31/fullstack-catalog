from flask import Flask, render_template, request
from flask import redirect, url_for, jsonify, flash, make_response
from flask import session as login_session
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CatalogItem, User
from datetime import datetime
import random
import string
import os

from authlib.client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery
from google.oauth2 import id_token

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from google.auth.transport import requests
import requests as req

# database settings
app = Flask(__name__)

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# auth settings
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
CLIENT_SECRET = json.loads(open('client_secrets.json', 'r').read())['web']['client_secret']
app.secret_key = CLIENT_SECRET


@app.route('/gconnect', methods=['POST'])
def gconnect():

    print('gconnect!')
    # print(request.form['idtoken'])
    state = request.form['state']
    token = request.form['idtoken']

    # Validatng state
    if state != login_session['state']:
        response = make_response(json.dumps('Invalid State'))
        response.headers['Content-Type'] = 'application/json'
        return response
    print('state validated!')
    # print('token:',token)

    # checking the validity of the access token

    idinfo = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
    # print('idinfo:',idinfo)

    # verifying that the token is for the user
    g_id = idinfo['sub']
    if request.form['g_id'] != g_id:
        response = make_response(json.dumps("Token's user does not match givven user ID."), 401)
        response.headers['Conetnt-Type'] = 'application/json'
        return response
    print('token validated!')

    # store the access token in the session for the later use
    login_session['token'] = token
    login_session['g_id'] = g_id

    # get user info

    login_session['username'] = idinfo['given_name']
    login_session['email'] = idinfo['email']

    # see if user exists, if it does not, make a new one
    user_id = getUserID(login_session['email'])
    print('user_id:', user_id)
    if not user_id:
        user_id = createUser(login_session)

    login_session['user_id'] = user_id

    output = ''
    output += '<h1> Welcome, '
    output += login_session['username']
    output += '!<img src="'
    # flash("you are now logged in as %s" % login_session['username'])
    print('username:', login_session['username'])
    return output

# functions

def createUser(login_session):

    print('creating user!')
    newUser = User(
        name=login_session['username'],
        email=login_session['email'],
    )
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).limit(1).one()
    print('user id:', user.id, user.name, user.email)
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    print('getUserInfo:', user)
    return user

def getUserID(email):
    try:
        print('email:', email)
        session = DBSession()
        user = session.query(User).filter_by(email=email).limit(1).one()
        print('getUserID:', user.id)
        return user.id
    except:
        print('failed to get ID by email')
        return None


# disconnect
@app.route('/gdisconnect')
def gdisconnect():

    print('disconnecting!')

    access_token = login_session['token']
    if access_token is None:
        print ('Access Token is None')
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print ('In gdisconnect access token is %s', access_token)
    print ('User name is: ')
    print (login_session['username'])
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    print ('result is ')
    print (result)
    if result['status'] == '200' or '400':
        del login_session['token']
        del login_session['g_id']
        del login_session['username']
        del login_session['email']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# root directory - show all the categories and latest added items
@app.route('/')
def homepage():

    session = DBSession()
    categories = session.query(Category)
    items = session.query(CatalogItem).order_by(desc(CatalogItem.timestamp)).limit(5)
    return render_template('homepage.html', categories=categories, recent_items=items)

    # for logging in  - a user can add, update, delete items only for created by the user

# selecting a specific category shows all the items available for thaat category
@app.route('/catalog/category/<int:category_id>/')
def showCategoryItems(category_id):
    session = DBSession()
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(CatalogItem).filter_by(category_id=category_id)
    return render_template('items.html', category=category, items=items)
        
# selecting a specific item shows specififc information about that item
@app.route('/catalog/item/<int:item_id>/')
def showItemInfo(item_id):
    print('item_id:', item_id)
    session = DBSession()
    item = session.query(CatalogItem).filter_by(id=item_id).one()
    return render_template('iteminfo.html', item=item)

# create an item ß
@app.route('/catalog/item/create', methods=['GET', 'POST'])
def itemCreate():

    if 'username' not in login_session:
        return redirect(url_for('homepage'))

    print(login_session)

    if request.method == 'GET':
        return render_template('create.html')
    elif request.method == 'POST':

        session = DBSession()
        try:
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id
        except:
            newCategory = Category(name=request.form['category'])
            session.add(newCategory)
            session.commit()
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id

        user_id = getUserID(login_session['email'])
        print('current user id:', user_id)

        newItem = CatalogItem(
            name=request.form['name'],
            description=request.form['description'],
            category_id=category_id,
            timestamp=datetime.now(),
            user_id=user_id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('homepage'))
    else:
        pass


# editing an item
@app.route('/catalog/item/<int:item_id>/edit', methods=['GET', 'POST'])
def itemEdit(item_id):

    session = DBSession()
    data_user_id = session.query(CatalogItem).filter_by(id=item_id).one().user_id
    try:
        login_user_id = session.query(User).filter_by(email = login_session['email']).limit(1).one().id
    except:
        login_user_id = None

    if data_user_id != login_user_id:
        return redirect(url_for('homepage'))

    session = DBSession()
    editedItem = session.query(CatalogItem).filter_by(id=item_id).one()

    if request.method == 'POST':
        try:
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id
        except:
            newCategory = Category(name=request.form['category'])
            session.add(newCategory)
            session.commit()
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id
        if request.form['name']:
            editedItem.name = request.form['name']
            editedItem.timestamp = datetime.now()
        if request.form['description']:
            editedItem.description = request.form['description']
            editedItem.timestamp = datetime.now()
        editedItem.category_id = category_id

        session.add(editedItem)
        session.commit()
        return redirect(url_for('homepage'))
    else:
        session = DBSession()
        category = session.query(Category).filter_by(id=editedItem.category_id).one().name
        return render_template('edit.html', category=category, item=editedItem)

# deleting an item
@app.route('/catalog/item/<int:item_id>/delete',  methods=['GET', 'POST'])
def itemDelete(item_id):

    session = DBSession()
    data_user_id = session.query(CatalogItem).filter_by(id=item_id).one().user_id
    try:
        login_user_id = session.query(User).filter_by(email=login_session['email']).limit(1).one().id
    except:
        login_user_id = None

    if data_user_id != login_user_id:
        return redirect(url_for('homepage'))

    session = DBSession()
    itemToDelete = session.query(CatalogItem).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('homepage'))
    else:
        return render_template('delete.html', item=itemToDelete)

# login route
@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    print(state)
    login_session['state'] = state
    return render_template('login.html', STATE=state, CLIENT_ID=CLIENT_ID, CLIENT_SECRET=CLIENT_SECRET)

# API endpoints
@app.route('/json')
def api():
    session = DBSession()
    data = session.query(CatalogItem)
    return jsonify(MenuItem=[i.serialize for i in data])

@app.route('/catalog/category/<int:category_id>/json')
def api_category(category_id):
    session = DBSession()
    data = session.query(CatalogItem).filter_by(category_id=category_id)
    return jsonify(MenuItem=[i.serialize for i in data])

@app.route('/catalog/item/<int:item_id>/json')
def api_item(item_id):
    session = DBSession()
    data = session.query(CatalogItem).filter_by(id=item_id)
    return jsonify(MenuItem=[i.serialize for i in data])

# session clear - foår development use
@app.route('/sessionclear')
def sessionclear():
    login_session.clear()
    print(login_session)
    return redirect(url_for('homepage'))

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)