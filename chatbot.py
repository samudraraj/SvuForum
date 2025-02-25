from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os, uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage for posts and chat messages.
posts = []  # Each post is a dict with: id, text, filename, filetype, comments (list)
chat_messages = []  # Each message: {"username": str, "message": str}


def get_next_post_id():
    return posts[-1]['id'] + 1 if posts else 1


# ------------------ Homepage ------------------
@app.route("/")
def homepage():
    homepage_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SVU Unofficial - Home</title>
        <style>
            body {
                background-color: #FFFDD0;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
            }
            .header {
                background-color: #4CAF50;
                color: white;
                padding: 40px;
                text-align: center;
            }
            .container {
                width: 90%;
                margin: 20px auto;
                padding: 20px;
                text-align: center;
                box-sizing: border-box;
            }
            .button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px 20px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                font-size: 1em;
            }
            .button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Welcome to SVU Unofficial</h1>
            <p>Your community forum for sharing posts, media, and chatting!</p>
        </div>
        <div class="container">
            <a href="{{ url_for('forum') }}" class="button">Enter Forum</a>
        </div>
    </body>
    </html>
    '''
    return render_template_string(homepage_template)


# ------------------ Forum Page ------------------
@app.route("/forum", methods=["GET", "POST"])
def forum():
    if 'saved' not in session:
        session['saved'] = []
    # Handle new post creation.
    if request.method == "POST":
        text = request.form.get("text")
        file = request.files.get("file")
        filename = None
        filetype = None
        if file and file.filename != '':
            orig_name = secure_filename(file.filename)
            filename = f"{uuid.uuid4().hex}_{orig_name}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            ext = os.path.splitext(filename)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.gif']:
                filetype = 'image'
            elif ext in ['.mp4', '.webm', '.ogg']:
                filetype = 'video'
            elif ext in ['.mp3', '.wav', '.ogg']:
                filetype = 'audio'
            elif ext == '.pdf':
                filetype = 'pdf'
            elif ext == '.zip':
                filetype = 'zip'
            else:
                filetype = 'other'
        new_post = {
            'id': get_next_post_id(),
            'text': text,
            'filename': filename,
            'filetype': filetype,
            'comments': []
        }
        posts.append(new_post)
        return redirect(url_for('forum'))

    forum_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SVU Unofficial Forum</title>
        <style>
            body {
                background-color: #FFFDD0;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
            }
            .header {
                background-color: #4CAF50;
                color: white;
                padding: 30px;
                text-align: center;
                font-size: 2em;
            }
            .container {
                width: 90%;
                margin: 20px auto;
                padding: 20px;
                box-sizing: border-box;
            }
            .post-form, .chat-box, .posts {
                background: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                box-sizing: border-box;
            }
            input[type="file"] {
                margin-top: 10px;
            }
            .post {
                border-bottom: 1px solid #ddd;
                padding: 10px;
                cursor: pointer;
            }
            .post:last-child {
                border-bottom: none;
            }
            .post img {
                max-width: 100%;
                margin-top: 10px;
            }
            .button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                cursor: pointer;
            }
            .button:hover {
                background-color: #45a049;
            }
            .overlay {
                position: fixed;
                top: 0; left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            .overlay-content {
                background: white;
                width: 90%;
                max-width: 900px;
                display: flex;
                border-radius: 8px;
                overflow: hidden;
            }
            .overlay-main {
                flex: 2;
                padding: 20px;
                overflow-y: auto;
                max-height: 80vh;
            }
            .overlay-comments {
                flex: 1;
                padding: 20px;
                border-left: 1px solid #ddd;
                overflow-y: auto;
                max-height: 80vh;
            }
            .close-btn {
                background-color: red;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 5px;
                cursor: pointer;
                float: right;
            }
            .comment {
                border-bottom: 1px solid #ccc;
                padding: 5px 0;
            }
            .chat-box {
                max-height: 300px;
                overflow-y: auto;
            }
            .chat-message {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
        </style>
    </head>
    <body>
        <div class="header">SVU Unofficial Forum</div>
        <div class="container">
            <!-- New Post Form -->
            <div class="post-form">
                <h2>Create a Post</h2>
                <form method="POST" enctype="multipart/form-data">
                    <textarea name="text" placeholder="What's on your mind?" rows="3"></textarea><br><br>
                    <input type="file" name="file"><br><br>
                    <button type="submit" class="button">Post</button>
                </form>
            </div>
            <!-- Posts Listing -->
            <div class="posts">
                <h2>Recent Posts</h2>
                {% for post in posts %}
                    <div class="post" onclick="openPost({{ post.id }})" id="post-{{ post.id }}">
                        <p>{{ post.text }}</p>
                        {% if post.filename and post.filetype == 'image' %}
                            <img src="{{ url_for('uploaded_file', filename=post.filename) }}" alt="Post Image" width="200">
                        {% elif post.filename and post.filetype in ['video', 'audio'] %}
                            {% if post.filetype == 'video' %}
                                <video width="200" controls>
                                    <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
                                    Your browser does not support the video tag.
                                </video>
                            {% else %}
                                <audio controls>
                                    <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
                                    Your browser does not support the audio element.
                                </audio>
                            {% endif %}
                        {% elif post.filename and post.filetype in ['pdf', 'zip', 'other'] %}
                            <a href="{{ url_for('uploaded_file', filename=post.filename) }}" download class="button">Download File</a>
                        {% endif %}
                        <br>
                        <button class="button" onclick="starPost(event, {{ post.id }})">★ Save Post</button>
                    </div>
                {% endfor %}
            </div>
            <!-- Chat Integration -->
            <div class="chat-box">
                <h2>Community Chat</h2>
                <div id="chat-messages">
                    {% for msg in chat_messages %}
                        <div class="chat-message"><strong>{{ msg.username }}:</strong> {{ msg.message }}</div>
                    {% endfor %}
                </div>
                <form id="chat-form" onsubmit="sendChatMessage(event)">
                    <input type="text" id="chat-username" placeholder="Your name" required style="width:20%; padding:5px; margin-right:5px;">
                    <input type="text" id="chat-input" placeholder="Type a message..." required style="width:60%; padding:5px; margin-right:5px;">
                    <button type="submit" class="button">Send</button>
                </form>
            </div>
            <br>
            <a href="{{ url_for('saved_posts') }}" class="button">View Saved Posts</a>
        </div>

        <!-- Overlay for Post Detail -->
        <div class="overlay" id="post-overlay">
            <div class="overlay-content">
                <div class="overlay-main" id="overlay-main">
                    <!-- Post details load here -->
                </div>
                <div class="overlay-comments" id="overlay-comments">
                    <!-- Comments load here -->
                </div>
            </div>
        </div>

        <script>
            // Opens the post overlay by fetching detailed content.
            function openPost(postId) {
                fetch('/post/' + postId)
                .then(response => response.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    document.getElementById('overlay-main').innerHTML = doc.getElementById('modal-main').innerHTML;
                    document.getElementById('overlay-comments').innerHTML = doc.getElementById('modal-comments').innerHTML;
                    document.getElementById('post-overlay').style.display = 'flex';
                });
            }
            function closeOverlay() {
                document.getElementById('post-overlay').style.display = 'none';
            }
            // Stars (saves) a post without triggering the overlay.
            function starPost(event, postId) {
                event.stopPropagation();
                fetch('/star/' + postId, {method: 'POST'})
                .then(response => response.json())
                .then(data => { alert(data.message); });
            }
            // Sends a chat message via AJAX.
            function sendChatMessage(event) {
                event.preventDefault();
                const username = document.getElementById('chat-username').value;
                const message = document.getElementById('chat-input').value;
                fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: username, message: message})
                })
                .then(response => response.json())
                .then(data => {
                    let chatDiv = document.getElementById('chat-messages');
                    let newMsg = document.createElement('div');
                    newMsg.className = 'chat-message';
                    newMsg.innerHTML = '<strong>' + data.username + ':</strong> ' + data.message;
                    chatDiv.appendChild(newMsg);
                    document.getElementById('chat-input').value = '';
                });
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(forum_template, posts=posts, chat_messages=chat_messages)


# ------------------ File Serving ------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ------------------ Post Detail & Commenting ------------------
@app.route('/post/<int:post_id>', methods=["GET"])
def post_detail(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        return "Post not found", 404
    modal_template = '''
    <div id="modal-main">
        <button class="close-btn" onclick="closeOverlay()">Close</button>
        <h2>Post Detail</h2>
        <p>{{ post.text }}</p>
        {% if post.filename %}
            {% if post.filetype == 'image' %}
                <img src="{{ url_for('uploaded_file', filename=post.filename) }}" alt="Post Image" style="max-width:100%;cursor:pointer;" onclick="this.style.transform = (this.style.transform=='scale(2)'?'scale(1)':'scale(2)');">
            {% elif post.filetype == 'video' %}
                <video width="100%" controls>
                    <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
                    Your browser does not support the video tag.
                </video>
            {% elif post.filetype == 'audio' %}
                <audio controls>
                    <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
                    Your browser does not support the audio element.
                </audio>
            {% elif post.filetype in ['pdf', 'zip', 'other'] %}
                <a href="{{ url_for('uploaded_file', filename=post.filename) }}" download class="button">Download File</a>
            {% endif %}
        {% endif %}
        <br><br>
        <button class="button" onclick="starPost(event, {{ post.id }})">★ Save Post</button>
    </div>
    <div id="modal-comments">
        <h3>Comments</h3>
        <div id="comments-list">
            {% for comment in post.comments %}
                <div class="comment">{{ comment }}</div>
            {% endfor %}
        </div>
        <form method="POST" action="{{ url_for('add_comment', post_id=post.id) }}">
            <textarea name="comment" placeholder="Add a comment" rows="2" style="width:100%; padding:5px; margin-top:10px; border:1px solid #ccc; border-radius:5px;"></textarea><br>
            <button type="submit" class="button" style="margin-top:5px;">Submit Comment</button>
        </form>
    </div>
    '''
    return render_template_string(modal_template, post=post)


@app.route('/comment/<int:post_id>', methods=["POST"])
def add_comment(post_id):
    comment_text = request.form.get("comment")
    post = next((p for p in posts if p['id'] == post_id), None)
    if post and comment_text:
        post['comments'].append(comment_text)
    return redirect(url_for('post_detail', post_id=post_id))


# ------------------ Save (Star) Post ------------------
@app.route('/star/<int:post_id>', methods=["POST"])
def star_post(post_id):
    if 'saved' not in session:
        session['saved'] = []
    saved = session['saved']
    if post_id not in saved:
        saved.append(post_id)
        session['saved'] = saved
        message = "Post saved!"
    else:
        message = "Post already saved."
    return jsonify({"message": message})


# ------------------ Saved Posts Page ------------------
@app.route('/saved', methods=["GET"])
def saved_posts():
    if 'saved' not in session:
        session['saved'] = []
    saved_ids = session['saved']
    saved_posts_list = [p for p in posts if p['id'] in saved_ids]
    saved_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Saved Posts - SVU Unofficial Forum</title>
        <style>
            body {
                background-color: #FFFDD0;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
            }
            .header {
                background-color: #4CAF50;
                color: white;
                padding: 30px;
                text-align: center;
                font-size: 2em;
            }
            .container {
                width: 90%;
                margin: 20px auto;
                padding: 20px;
                box-sizing: border-box;
            }
            .post {
                background: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .button {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="header">Saved Posts</div>
        <div class="container">
            {% for post in saved_posts_list %}
                <div class="post">
                    <p>{{ post.text }}</p>
                    {% if post.filename and post.filetype == 'image' %}
                        <img src="{{ url_for('uploaded_file', filename=post.filename) }}" alt="Post Image" width="200">
                    {% elif post.filename and post.filetype in ['video', 'audio'] %}
                        {% if post.filetype == 'video' %}
                            <video width="200" controls>
                                <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
                                Your browser does not support the video tag.
                            </video>
                        {% else %}
                            <audio controls>
                                <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
                                Your browser does not support the audio element.
                            </audio>
                        {% endif %}
                    {% elif post.filename and post.filetype in ['pdf', 'zip', 'other'] %}
                        <a href="{{ url_for('uploaded_file', filename=post.filename) }}" download class="button">Download File</a>
                    {% endif %}
                </div>
            {% endfor %}
            <a href="{{ url_for('forum') }}" class="button">Back to Forum</a>
        </div>
    </body>
    </html>
    '''
    return render_template_string(saved_template, saved_posts_list=saved_posts_list)


# ------------------ Chat Integration ------------------
@app.route('/chat', methods=["POST"])
def chat():
    data = request.get_json()
    username = data.get("username", "Anonymous")
    message = data.get("message", "")
    if message:
        new_message = {"username": username, "message": message}
        chat_messages.append(new_message)
        return jsonify(new_message)
    return jsonify({"error": "No message provided"}), 400


if __name__ == '__main__':
    app.run(debug=True)
