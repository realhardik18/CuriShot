from flask import Flask, render_template, request, redirect, url_for, session, flash
from appwrite.client import Client
from appwrite.services.account import Account
from creds import API_ENDPOINT,APPWRITE_API_KEY,PROJECT_ID
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Appwrite Client Setup
client = Client()
client.set_endpoint(API_ENDPOINT)  # Your Appwrite endpoint
client.set_project(PROJECT_ID)  # Your project ID
client.set_key(APPWRITE_API_KEY)  # Your API key

# Account Service
account = Account(client)

@app.route('/')
def index():
    user = None
    if 'user' in session:
        user = session['user']
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            session_data = account.create_session(email, password)
            session['user'] = session_data['email']  # Store the user session
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        try:
            account.create(name, email, password)
            flash('Sign up successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Signup failed: {str(e)}', 'danger')
            return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    try:
        session.pop('user', None)  # Remove the user from session
        flash('Logged out successfully!', 'success')
    except Exception as e:
        flash(f'Logout failed: {str(e)}', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
