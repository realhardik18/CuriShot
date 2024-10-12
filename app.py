from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from creds import MONGO_URI

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MONGO_URI'] = MONGO_URI

mongo = PyMongo(app)

# Render register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if users.find_one({'username': username}):
            return 'Username already exists!'

        hashed_password = generate_password_hash(password)
        users.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password
        })
        return redirect(url_for('login'))
    return render_template('register.html')

# Render login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        username = request.form['username']
        password = request.form['password']

        user = users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['user'] = str(user['_id'])
            return 'Login successful!'
        else:
            return 'Invalid username or password!'
    return render_template('login.html')

# Logout route
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
