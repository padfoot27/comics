from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask import url_for,session,flash,render_template,redirect,request   
from flask_oauth import OAuthRemoteApp
from flask_login import LoginManager,UserMixin,current_user,current_app,login_user,logout_user,login_required
from rauth import OAuth2Service 
import json 
from flask import jsonify 
from requests_oauthlib import OAuth2Session
from flask_migrate import Migrate,MigrateCommand
from random import randint 
import linecache

GOOGLE_APP_ID = '304034490852-tm91ml588d7qn9ruvjd1freot0c7plha.apps.googleusercontent.com'
GOOGLE_APP_SECRET = '8foFjOWojo85Q3PxhwXHy1Yh'
GOOGLE_AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_REVOKE_URI = 'https://accounts.google.com/o/oauth2/revoke'
GOOGLE_TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_BASE_URL = 'https://www.googleapis.com/plus/v1/'

app = Flask(__name__)
app.debug = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.secret_key = 'MyNameisBond'
login_manager = LoginManager()
db = SQLAlchemy(app)
login_manager.init_app(app)

SECRET_KEY = 'sid'
USERNAME = 'user'
PASSWORD = 'default'
DEBUG = True 

google = OAuth2Service(
    name='google',
    client_id = GOOGLE_APP_ID,
    client_secret = GOOGLE_APP_SECRET,
    access_token_url=GOOGLE_TOKEN_URI,
    authorize_url=GOOGLE_AUTH_URI,
    base_url = GOOGLE_BASE_URL)


class User(db.Model):
    id = db.Column(db.Integer,primary_key = True,autoincrement = True)
    name = db.Column(db.String(80))
    google_id = db.Column(db.String(200),unique=True)
    links = db.Column(db.Integer)
    done = db.Column(db.Integer)
    plink = db.Column(db.String(200))
    seen = db.relationship('Links',backref = 'user',lazy = 'dynamic')
    
    def __init__(self,name,google_id,seen=[],links=5,done=5,plink=None):
        self.name = name
        self.google_id = google_id
        self.seen = seen 
        self.links = links
        self.done = done 
        
    def is_authenticated(self):
        return True 

    def is_active(self):
        return True 

    def is_anonymous(self):
        return False

    def get_id(self):
        
        try:
            return unicode(self.id)

        except NameError:
            return str(self.id)

    @staticmethod
    def get_or_create(name,google_id):
        user = User.query.filter_by(google_id=google_id).first()

        if user is None:
            print '2'
            user = User(name,google_id)
            db.session.add(user)
            db.session.commit()
            
            for i in range(user.links):
                src = Source.query.filter_by(id=i + 1).first().source 
                print src
                li = Links(src=src,user=user)
                db.session.add(li)
                user.seen.append(li)
                db.session.add(user)
                db.session.commit()
        print '3'
        return user
     
class Links(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    person_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    src = db.Column(db.String(300)) 

class Source(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    source = db.Column(db.String(300)) 
    
    
    def __init__(self,source):
        self.source = source
 
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def start(name=None):
    if current_user.is_authenticated():
        return redirect(url_for('strip'))
    else:
        return render_template('index.html',name=name)

redirect_uri = 'http://127.0.0.1:5000/callback'

@app.route('/login/google')
def googleLogin():
    params = {'scope': 'https://www.googleapis.com/auth/userinfo.profile',
              'access_type': 'offline',
              'response_type': 'code',
              'redirect_uri': redirect_uri}
    return redirect(google.get_authorize_url(**params))


@app.route('/callback')
def callback():
    response = google.get_raw_access_token(data = {'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri})
    
    response = response.json()
    session = google.get_session(response['access_token'])
    user = session.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
    me = User.get_or_create(user['name'],user['id'])
    print me.id 
    print me.name
    print me.google_id 
    login_user(me)
    flash('Hello ' + me.name)
    return redirect(url_for('strip'))

@app.route('/strips')
@login_required 
def strip():
    user = User.query.filter_by(id=current_user.id).first()
    if user.done < 11:
        user.done += 1
   
    s = Source.query.filter_by(id=user.done).first()

    if user.links == 0:
       return 'Links are Done'

    strip = randint(0,user.links - 1)
    
    srce = user.seen[strip].src 
    user.seen.remove(user.seen[strip])
    
    if user.done < 11:
        src = s.source
        li = Links(src=src,user=user)
        db.session.add(li)
        user.seen.append(li)
     
    if user.done == 11:
        user.links -= 1
    
    user.plink = srce
    
    db.session.add(user)
    db.session.commit()
    print user.links 
    print user.done
    s = Source.query.filter_by(source=srce).first()
   
    return render_template('base.html',src=srce,num=s.id)
       
@app.route('/next')
@login_required 
def next():

    user = User.query.filter_by(id=current_user.id).first()
    src = user.plink
    s = Source.query.filter_by(source=src).first()
    n = None
    
    if (s.id == 11):
        n = 1

    else: 
        n = s.id + 1

    s = Source.query.filter_by(id=n).first()

    src = s.source 
    li = Links(src=src,user=user)
    db.session.add(li)
    user.seen.append(li)
    user.plink = src 
    
    db.session.add(user)
    db.session.commit()

    return render_template('base.html',src=src,num=s.id)
    
@app.route('/prev')
@login_required 
def prev():
    user = User.query.filter_by(id=current_user.id).first()
    src = user.plink
    s = Source.query.filter_by(source=src).first()
    n = None
    
    if (s.id == 1):
        n = 11

    else: 
        n = s.id - 1

    s = Source.query.filter_by(id=n).first()

    src = s.source 
    li = Links(src=src,user=user)
    db.session.add(li)
    user.seen.append(li)
    user.plink = src 
    
    db.session.add(user)
    db.session.commit()

    return render_template('base.html',src=src,num=s.id)
                 
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('start'))

if __name__ == '__main__':
    db.create_all()
    app.run()
    #manager.run()
