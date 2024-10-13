import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
#from creds import PINATA_API_KEY,MONGO_URI,PINATA_SECRET_API_KEY
import bson

app = Flask(__name__)
app.secret_key = 'your_secret_key'
#app.config['MONGO_URI'] = MONGO_URI
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
PINATA_UNPIN_URL = 'https://api.pinata.cloud/pinning/unpin/'


mongo = PyMongo(app)    

def unpin_file_from_pinata(ipfs_hash):
    # Set the headers with the Pinata API key and secret
    headers = {
        #'pinata_api_key': PINATA_API_KEY,
        #'pinata_secret_api_key': PINATA_SECRET_API_KEY
        'pinata_secret_api_key': os.getenv('PINATA_SECRET_API_KEY'),
        'pinata_secret_api_key': os.getenv('PINATA_SECRET_API_KEY')
    }
    
    # Make the unpin request
    response = requests.delete(PINATA_UNPIN_URL + ipfs_hash, headers=headers)
    
    if response.status_code == 200:
        print(f"File {ipfs_hash} successfully unpinned from Pinata.")
    else:
        print(f"Failed to unpin file {ipfs_hash}: {response.text}")

def upload_to_pinata(file):
    # Pinata API details
    pinata_api_url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        #'pinata_api_key': PINATA_API_KEY,
        #'pinata_secret_api_key': PINATA_SECRET_API_KEY
        'pinata_secret_api_key': os.getenv('PINATA_SECRET_API_KEY'),
        'pinata_secret_api_key': os.getenv('PINATA_SECRET_API_KEY')
    }

    # Use a multipart form-data request to upload the file directly
    files = {
        'file': (file.filename, file.stream, file.content_type)
    }
    
    try:
        response = requests.post(pinata_api_url, headers=headers, files=files)
        response.raise_for_status()  # Will raise an HTTPError if the response code is 4xx/5xx
        # If successful, get the IPFS hash of the uploaded file
        ipfs_hash = response.json().get('IpfsHash')
        return ipfs_hash
    except requests.exceptions.RequestException as e:
        print(f"Error uploading to Pinata: {e}")
        return None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        username = request.form['username']
        password = request.form['password']

        user = users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['user'] = str(user['_id'])
            session['username'] = username  # Store username in session
            return redirect(url_for('dashboard'))  # Redirect to dashboard
        else:
            flash('Invalid username or password!',"danger")
            return redirect(url_for('login'))
    return render_template('login.html')

# Render register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if users.find_one({'username': username}):
            flash('Username already exists!','danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        users.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password
        })
        flash('Account created! Kindly Login!','success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Dashboard route with file upload and list of files
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' in session:
        username = session['username']
        files = mongo.db.files.find({'username': username})

        # Handling form submissions (file upload and adding new tag)
        if request.method == 'POST':
            # Add new tag logic with color
            if 'new_tag' in request.form and 'tag_color' in request.form:
                new_tag = request.form['new_tag']
                tag_color = request.form['tag_color']
                if new_tag and tag_color:
                    # Insert new tag into the 'tags' collection for the current user
                    mongo.db.tags.update_one(
                        {'username': username},
                        {'$addToSet': {'tags': {'name': new_tag, 'color': tag_color}}},
                        upsert=True
                    )
                    flash('Tag added successfully!', 'success')

            # Handle file upload and tag selection
            if 'file' in request.files and request.files['file']:
                file = request.files['file']
                
                # Upload file to Pinata directly
                ipfs_hash = upload_to_pinata(file)

                if ipfs_hash:
                    # Store file and selected tags in the database
                    selected_tags = request.form.getlist('tags')
                    file_data = {
                        'username': username,
                        'filename': file.filename,
                        'ipfs_hash': ipfs_hash,
                        'created_at': datetime.utcnow(),
                        'tags': [{'name': tag, 'color': get_tag_color(username, tag)} for tag in selected_tags]
                    }
                    mongo.db.files.insert_one(file_data)
                    flash('File uploaded successfully!', 'success')
                else:
                    flash('Error uploading file!', 'error')
                
                return redirect(url_for('dashboard'))

        # Fetch user's tags from MongoDB
        user_tags = mongo.db.tags.find_one({'username': username})
        user_tags = user_tags['tags'] if user_tags else []

        return render_template('dashboard.html', username=username, files=files, tags=user_tags)
    else:
        return redirect(url_for('login'))


# Route to delete tags
@app.route('/delete-tag/<tag_id>', methods=['POST'])
def delete_tag(tag_id):
    if 'username' in session:
        username = session['username']
        # Delete the tag from the tags collection
        mongo.db.tags.update_one(
            {'username': username},
            {'$pull': {'tags': {'name': tag_id}}}
        )
        flash('Tag deleted successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


def get_tag_color(username, tag_name):
    user_tags = mongo.db.tags.find_one({'username': username})
    if user_tags and 'tags' in user_tags:
        for tag in user_tags['tags']:
            if tag['name'] == tag_name:
                return tag['color']
    return "#ffffff"  # Default color


# Logout route
@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('user', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/delete/<file_id>', methods=['POST'])
def delete_file(file_id):
    # Fetch file from the database using file_id
    file_data = mongo.db.files.find_one({"_id": bson.ObjectId(file_id)})
    
    if file_data:        
        # Get the Pinata IPFS hash of the file
        ipfs_hash = file_data.get('ipfs_hash')
        ipfs_hash=ipfs_hash['IpfsHash']
        #print(ipfs_hash,type(ipfs_hash))
        
        # Debug: Check if ipfs_hash is valid
        if not ipfs_hash:
            return f"Error: No IPFS hash found for file with id {file_id}"
        
        # Unpin file from Pinata
        unpin_file_from_pinata(ipfs_hash)
        
        # Delete the file from MongoDB
        mongo.db.files.delete_one({"_id": bson.ObjectId(file_id)})
        
        # Redirect back to the dashboard
        flash('File deleted','succsess')
        return redirect(url_for('dashboard'))
        #return 'hello'
    
    return 'File not found', 404


if __name__ == '__main__':
    app.run(debug=True)
