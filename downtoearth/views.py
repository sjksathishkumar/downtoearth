#Flask Imports
from flask import Flask, jsonify, flash, render_template, request, redirect, url_for, session, abort
from flask.ext.security import login_required, current_user, login_user, LoginForm, RegisterForm
from flask.ext.social.views import connect_handler
from flask.ext.social.utils import get_provider_or_404

#App Imports
from downtoearth import app, forms, db
from downtoearth.models import User, social, security
from downtoearth.models import user_datastore as ds
from downtoearth.models import Store, Item, Comment, Vote
from downtoearth.forms import AddItemForm

import config
import facebook

#Python Imports
from datetime import datetime, date
import calendar
import json
import time
import urllib2

categories = ["Items", "Service", "Rates"]

@app.route('/')
@login_required
def index():
    return render_template('index.html')

#You can write 'function decorators' like @login_required as shown below
#def subscription_required(fn):
#    @wraps(fn)
#    def decorated_view(*args, **kwargs):
#        print "subscribe"
#        if not is_subscribed(current_user):
#            return redirect('/subscribe')
#        return fn(*args, **kwargs)
#    return decorated_view

#def is_subscribed(user):
#    return User.query.filter_by(id=user.id).first().is_subscribed

@app.route('/adduser', methods=['GET', 'POST'])
@app.route('/adduser/<provider_id>', methods=['GET', 'POST'])
def adduser(provider_id=None):

    provider = get_provider_or_404(provider_id)

    form = RegisterForm()
    print form
    connection_values = session.get('failed_login_connection', None)
    print connection_values
    access_token = connection_values['access_token']
    graph = facebook.GraphAPI(access_token)
    profile = graph.get_object("me")
    email = profile["email"]
    print email

    #ds = security.user_datastore
    user = ds.create_user(email=email, password="makkarlabsmass")
    ds.commit()
            # See if there was an attempted social login prior to registering
        # and if so use the provider connect_handler to save a connection
    connection_values = session.pop('failed_login_connection', None)

    if connection_values:
        connection_values['user_id'] = user.id
        connect_handler(connection_values, provider)

    if login_user(user):
        ds.commit()
        flash('Account created successfully', 'info')
        return redirect(url_for('profile'))

    return abort(404)

@app.route('/restaurants')
def restaurants():
    return render_template('work.html')

@app.route('/restaurants/<restaurant_name>')
def restaurants_page(restaurant_name = None):
    if restaurant_name is not None:
        store_id = Store.query.filter_by(store_name = restaurant_name).first().id
        return render_template('todo.html', data={'store_name': restaurant_name, 'id': store_id})


@app.route('/api/add_comment', methods=['POST'])
def add_comment():
    try:
        comment = Comment(request.form['item_id'], request.form['comment'], current_user.id)
        db.session.add(comment)
        db.session.commit()
    except:
        raise KeyError
        abort(403)

@app.route('/api/up_vote', methods=['POST'])
def up_vote():
    try:
        vote = Vote(current_user.id, request.form['item_id'], request.form['comment_id'], True)
        db.session.add(vote)
        db.session.commit()
    except:
        print "Database error"
        return jsonify(data={"success":0, "error":"Database Error"})
    return jsonify(data={"success":1, "message":"Comment Up Voted"})

@app.route('/api/down_vote', methods=['POST'])
def down_vote():
    try:
        vote = Vote(current_user.id, request.form['item_id'], request.form['comment_id'], False)
        db.session.add(vote)
        db.session.commit()
    except:
        print "Database error"
        return jsonify(data={"success":0, "error":"Database Error"})
    return jsonify(data={"success":1, "message":"Comment Down Voted"})

@app.route('/api/can_vote', methods=['POST'])
def can_vote():
    comment = Comment.query.filter_by(user_id = current_user.id).filter_by(comment_id = request.form['comment_id']).all()
    if len(comment) > 0:
        return jsonify(data={"can_vote":False})
    else:
        return jsonify(data={"can_vote":True})    

@app.route('/api/list/restaurants', methods=['POST'])
def list_restaurants():
    data=[]
    for store in Store.query.all():
        dat = {}
        dat['id'] = store.id
        dat['name'] = store.store_name
        dat['photo_url'] = store.store_photo_url
        dat['location'] = store.store_location
        data.append(dat)
    return jsonify(data=data)

@app.route('/api/list/items', methods=['POST'])
def list_items():
    try:
        data=[]
        store_id = request.form['store_id']
        print store_id
        for store in Item.query.filter_by(store_id = int(store_id)):
            print "found store"
            dat = {}
            dat['name'] = store.item_name
            data.append(dat)
        return jsonify(data=data)
    except KeyError:
        return abort(404)

@app.route('/api/list/comments', methods=['POST'])
def list_comments():
    """try:
        cat_id = request.form['cat_id']
    except:
        raise KeyError
        abort(404)"""
    data=[]
    store_name = request.form['store_name']
    store_id = Store.query.filter_by(store_name = store_name).first().id
    print store_id
    for store in Item.query.filter_by(store_id = int(store_id)):
        print "found store"
        dat = {}
        dat['id'] = store.id
        dat['name'] = store.item_name
        tdata=[]
        for comment in Comment.query.filter_by(cat_id = store.id).all():
            tdat = {}
            tdat['comment'] = comment.comment
            tdat['cat_id'] = comment.cat_id
            tdat['cat_name'] = comment.cat_name
            tdat['up_votes'] = comment.up_votes
            tdat['down_vote'] = comment.down_votes
            tdat['timestamp'] = comment.timestamp
            tdat['commenter_name'] = comment.commenter_name
            tdat['item_name'] = Item.query.filter_by(id=cat_id).first().item_name
            if len(Vote.query.filter_by(user_id = current_user.id).filter_by(comment_id = comment.id).all()) > 0:
                tdat['can_vote'] = False
            else:
                tdat['can_vote'] = True
            tdata.append(tdat)
        dat['comments'] = tdata
        data.append(dat)
    return jsonify(data=data)

@app.route('/additem', methods=['GET','POST'])
def add_item():
    form = AddItemForm(request.form)    
    if request.method=='POST':
        d = form.data
        item = Item(store_id = d['store_name'],
            item_name = d['item_name'],
            item_photo_url = d['item_url'],
            item_price = d['item_price'])
        db.session.add(item)
        db.session.commit()

    return render_template("additem.html", additem_form = AddItemForm())

@app.route('/rating', methods=['GET'])
def ratings_api():
    name = request.args.get('name', '')
    place = request.args.get('place', '')
    response = urllib2.urlopen("http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20local.search%20where%20query%3D'"+name+"'%20and%20location%3D%22"+place+"%22%20and%20minimum_rating%3D3&format=json")
    jsonres = response.read()
    #print jsonres
    data = json.loads(jsonres)
    try:
        return data["query"]["results"]["Result"][0]["Rating"]["AverageRating"]
    except:
        return "0"

@app.route('/tweets', methods=['GET', 'POST'])
def tweets_shit():
    qstr = request.args.get('query', '')
    print "tweets "
    print qstr
    #try:
    from twython import Twython, TwythonError
    import urllib
    print qstr
    twitter = Twython("YyrtLcLXY3rK0NB4hxPxg", "ITufCiliKOKXJMg2NwH8DjearGD5ZzSbWGBmrADPJk", "154058629-sXgrILo1Wn1iQqY1eE422McGWkIdQP7BMLwFmmew", "7LKdy7WretsZK8mKoSGsQt6waPodtIpLF3pFLypQ")
    print qstr
    search_results = twitter.search(q=qstr, count=50)

    for tweet in search_results['statuses']:
        try:
            if float(analysis(urllib.quote(tweet['text'])).encode('ascii', 'ignore')) < -0.2:
                print tweet['text']
            else:
                print "has a low score"
        except:
            pass
        #print type()
    #except:
        #abort(404)

def analysis(text):
    try:
        import unirest
        response = unirest.get(
            "https://loudelement-free-natural-language-processing-service.p.mashape.com/nlp-text/?text="+text,
            {
            "X-Mashape-Authorization": "ZfkjlcFrPHhgFlc2DjlwjjgyrNUgiXDZ"
            });
        return response.body['sentiment-score']
    except:
        return 0
