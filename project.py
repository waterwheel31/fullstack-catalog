from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask import session as login_session 
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, CatalogItem
from datetime import datetime
import random,string


# database settings
app = Flask(__name__)
app.secret_key = 'secret'

engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# auth settings 


# login route 
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    print(state)
    login_session['state'] = state
    return render_template('login.html', STATE = state)



# root directory - show all the categories and latest added items 
@app.route('/')
def homepage():

    session = DBSession()
    categories = session.query(Category)
    items = session.query(CatalogItem).order_by(desc(CatalogItem.timestamp)).limit(5)
    return render_template('homepage.html', categories = categories, recent_items=items )


    # for logging in  - a user can add, update, delete items only for created by the user

# selecting a specific category shows all the items available for thaat category
@app.route('/catalog/category/<int:category_id>/')
def showCategoryItems(category_id):
    session = DBSession()
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(CatalogItem).filter_by(category_id=category_id)
    return render_template('items.html', category = category, items=items )
    

# selecting a specific item shows specififc information about that item
@app.route('/catalog/item/<int:item_id>/')
def showItemInfo(item_id):
    print('item_id:',item_id)
    session = DBSession()
    item = session.query(CatalogItem).filter_by(id=item_id).one()
    return render_template('iteminfo.html', item = item )

# create an item ß
@app.route('/catalog/item/create',methods=['GET','POST'])
def itemCreate():

    if request.method == 'GET':
        return render_template('create.html')
    elif request.method == 'POST':

        session = DBSession()
        try :
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id
        except: 
            newCategory = Category(name=request.form['category'])
            session.add(newCategory)
            session.commit()
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id

        newItem = CatalogItem(
            name=request.form['name'], 
            description=request.form['description'], 
            category_id=category_id, 
            timestamp=datetime.now())
        session.add(newItem)
        session.commit()
        return redirect(url_for('homepage'))
    else: pass


# editing an item 
@app.route('/catalog/item/<int:item_id>/edit',methods=['GET', 'POST'])
def itemEdit(item_id):
   
    session = DBSession()
    editedItem = session.query(CatalogItem).filter_by(id=item_id).one()

    if request.method == 'POST':      
        try :
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id
        except: 
            newCategory = Category(name=request.form['category'])
            session.add(newCategory)
            session.commit()
            category_id = session.query(Category).filter_by(name=request.form['category']).one().id
        if request.form['name']:
            editedItem.name = request.form['name']
            editedItem.timestamp=datetime.now()
        if request.form['description']:
            editedItem.description = request.form['description']
            editedItem.timestamp=datetime.now()
        editedItem.category_id = category_id
        
        session.add(editedItem)
        session.commit()
        return redirect(url_for('homepage'))
    else:
        session = DBSession()
        category = session.query(Category).filter_by(id=editedItem.category_id).one().name
        return render_template('edit.html', category = category, item=editedItem)

# deleting an item
@app.route('/catalog/item/<int:item_id>/delete',  methods=['GET', 'POST'])
def itemDelete(item_id):

    session = DBSession()
    itemToDelete = session.query(CatalogItem).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('homepage'))
    else:
        return render_template('delete.html', item=itemToDelete)


# API endpoint 
@app.route('/catalog.json')
def api():
    session = DBSession()
    data = session.query(CatalogItem)
    return jsonify(MenuItem=[i.serialize for i in data])



if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)