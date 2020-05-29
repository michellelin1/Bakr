import pyrebase
from functools import wraps
from flask import Flask, redirect, render_template, session, request
from flask_uploads import UploadSet, configure_uploads, IMAGES


config = {
	"apiKey": "AIzaSyD7T33O-Tb4cP9BgNerKcGV_Hy8qroW0MI",
    "authDomain": "bakr-3e04c.firebaseapp.com",
    "databaseURL": "https://bakr-3e04c.firebaseio.com",
    "projectId": "bakr-3e04c",
    "storageBucket": "bakr-3e04c.appspot.com",
    "messagingSenderId": "829186969060",
    "appId": "1:829186969060:web:0081363993fb3e8c4b8bf1",
    "measurementId": "G-XQ2H1H0P37"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()
auth = firebase.auth()

app = Flask(__name__)
photos = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'static/images'
configure_uploads(app, photos)
app.config['SECRET_KEY']="AIzaSyAkuv0IZZ7UcgU6tNhfwT0DP48MV4EYDPU"


# im actually not 100% sure what does but the url to access data is wrong
# found it on github
# line 110 doesn't work with out it
def noquote(s):
    return s
pyrebase.pyrebase.quote = noquote

# this wasn't how i orginally planned on checking but found it after looking through the docs
# thought it was pretty cool
def isAuthenticated(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #check for the variable that pyrebase creates
        if auth.current_user == None:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pw']
        # will throw an error if account info is wrong
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['email'] = email.replace(".", "-")                  # firebase doesn't allow for . in keys --> replace with -
            session['userToken'] = user['idToken']
            return redirect('/')
        except:
            return render_template('login.html',action="login", s=True, error="The email or phone number you've entered doesn't match any account.")
    return render_template('login.html', action="login", s=True)


@app.route('/signUp', methods=['GET', 'POST'])
def signUp():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['pw']
        try:
            #creat a new account then signs them in right away
            auth.create_user_with_email_and_password(email, password)
            user = auth.sign_in_with_email_and_password(email, password)
            #store info that I need globally
            session['email'] = email.replace(".", "-")
            session['userToken'] = user['idToken']
            #creating a new collection for the user
            doc = {'currentIndex':0}
            db.child('users').child(session['email']).set(doc, session['userToken'])
            return redirect('/')
        except:
            return render_template('login.html', action="signUp", error="**make sure your password is 6+ characters or email is taken")
    return render_template('login.html', action="signUp")


@app.route('/', methods=['GET', 'POST'])
@isAuthenticated
def index():
    email = session['email']
    token = session['userToken']
    index = db.child('users').child(session['email']).get(token).val()['currentIndex']
    recipeId = getRecipeId(index)
    # deals with the user input accordingly then updates the current index
    if request.method == 'POST':
        if request.form['submit'] == 'yes':
            saved = db.child('users').child(email).child('saved').get(token).val()
            # checks if list exsists 1st then appends the id to the end
            if saved == None:
                db.child('users').child(email).update({'saved': [recipeId]}, token)
            else:
                saved.append(recipeId)
                db.child('users').child(email).update({'saved': saved}, token)
        db.child('users').child(email).update({'currentIndex': index+1}, token)
        return redirect('/')
    if recipeId == "":
        return render_template('index.html', end="There are currently no more recipes. Feel free to add your own so others can see! :)")
    else:
        recipe = db.child('recipes').child(recipeId).get(token).val()
        return render_template('index.html', r=recipe)
    

        
def getRecipeId(index):
    token = session['userToken']
    recipe = db.child("recipes").order_by_child("recipeIndex").equal_to(index).get(token).each()
    key = ""
    if len(recipe) > 0:
        key=recipe[0].key()
    return key

# i was going to upload the images to the cloud but     
@app.route('/add', methods=['GET', 'POST'])
@isAuthenticated
def add():
    if request.method == 'POST':
        #gets all the info from the form and stores it in a dictionary 
        token = session['userToken']
        index = db.child('numRecipes').get(token).val()
        fileName = request.form['name'].replace(' ', '-') +"."
        imageFile = photos.save(request.files['photo'], name=fileName)
        doc = {'name': request.form['name'], 'imageFile': imageFile, 
               'recipeLink': request.form['recipe'], 'recipeIndex': index}
        db.child('recipes').push(doc, token)
        #updates the total number of recipes
        db.update({'numRecipes':index+1}, token)
        return redirect('/')
    return render_template('add.html')

@app.route('/saved')
@isAuthenticated
def saved():
    token = session['userToken']
    recipeIds = db.child('users').child(session['email']).child('saved').get(token).val()
    if(recipeIds == None):
        return render_template('saved.html', empty="You currently don't have any saved recipes")
    else:
        savedRecipes = []
        for r in recipeIds:
            savedRecipes.append(db.child('recipes').child(r).get(token))
        return render_template('saved.html', saved=savedRecipes)
    

@app.route('/remove/<recipeId>')
@isAuthenticated
def remove(recipeId):
    token = session['userToken']
    email = session['email']
    recipes = db.child('users').child(email).child('saved').get(token).val()
    recipes.remove(recipeId)
    db.child('users').child(email).update({'saved': recipes}, token)
    return redirect('/saved')

# logs user out and clears session data
@app.route('/logout')
def logout():
    auth.current_user = None
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
	app.run(debug=True)
