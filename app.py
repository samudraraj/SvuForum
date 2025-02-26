import os
import uuid
from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Use environment variable in production.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# Configure upload folder.
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions.
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.webm', '.ogg', '.mp3', '.wav', '.pdf', '.zip'}

# In-memory storage.
# Each post: { id, title, text, filename, filetype, comments (list), upvotes, downvotes }
posts = []
# Global counter for comment IDs.
comment_id_counter = 1
# Chat messages.
chat_messages = []  # Each: { username, message }

# Dummy user data for login.
# In production, use a persistent database with proper password hashing.
users = {
    "admin": "adminpass",
    "user": "userpass"
}


def allowed_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_next_post_id() -> int:
    return posts[-1]['id'] + 1 if posts else 1


def get_next_comment_id() -> int:
    global comment_id_counter
    cid = comment_id_counter
    comment_id_counter += 1
    return cid


def find_comment(comments: list, comment_id: int) -> dict:
    """Recursively search for a comment with the given ID."""
    for comment in comments:
        if comment['id'] == comment_id:
            return comment
        found = find_comment(comment.get('replies', []), comment_id)
        if found:
            return found
    return None


# ------------------ Login & Sign Up Routes ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    login_template = '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Login</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { background-color: #FFFDD0; font-family: Arial, sans-serif; }
        .login-container { max-width: 400px; margin: 50px auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }
        .button { background-color: #4CAF50; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer; width: 100%; }
        .button:hover { background-color: #45a049; }
        .link { text-align: center; margin-top: 10px; }
      </style>
    </head>
    <body>
      <div class="login-container">
        <h2>Login</h2>
        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        <form method="POST">
          <input type="text" name="username" placeholder="Username" required>
          <input type="password" name="password" placeholder="Password" required>
          <button type="submit" class="button">Login</button>
        </form>
        <div class="link">
          <a href="{{ url_for('signup') }}">Don't have an account? Sign Up</a>
        </div>
      </div>
    </body>
    </html>
    '''
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            session['user'] = username
            return redirect(url_for('forum'))
        else:
            error = "Invalid credentials"
    return render_template_string(login_template, error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    signup_template = '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Sign Up</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { background-color: #FFFDD0; font-family: Arial, sans-serif; }
        .signup-container { max-width: 400px; margin: 50px auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; }
        .button { background-color: #4CAF50; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer; width: 100%; }
        .button:hover { background-color: #45a049; }
        .link { text-align: center; margin-top: 10px; }
      </style>
    </head>
    <body>
      <div class="signup-container">
        <h2>Sign Up</h2>
        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        <form method="POST">
          <input type="text" name="username" placeholder="Choose a username" required>
          <input type="password" name="password" placeholder="Choose a password" required>
          <input type="password" name="confirm_password" placeholder="Confirm password" required>
          <button type="submit" class="button">Sign Up</button>
        </form>
        <div class="link">
          <a href="{{ url_for('login') }}">Already have an account? Login</a>
        </div>
      </div>
    </body>
    </html>
    '''
    error = None
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if username in users:
            error = "Username already exists. Please choose another."
        elif password != confirm_password:
            error = "Passwords do not match."
        else:
            users[username] = password
            session['user'] = username  # Auto-login after sign up.
            return redirect(url_for('forum'))
    return render_template_string(signup_template, error=error)


@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('forum'))


# ------------------ Homepage ------------------
@app.route("/")
def homepage():
    homepage_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SVU Unofficial - Home</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background-color: #FFFDD0; font-family: Arial, sans-serif; margin: 0; padding: 0; }
            .header { background-color: #4CAF50; color: white; padding: 40px; text-align: center; }
            .container { width: 90%; margin: 20px auto; padding: 20px; text-align: center; box-sizing: border-box; }
            .button { background-color: #4CAF50; color: white; border: none; padding: 15px 20px; border-radius: 5px; cursor: pointer; text-decoration: none; font-size: 1em; }
            .button:hover { background-color: #45a049; }
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
    """
    Render the forum page.
    - Handles new post submissions.
    - Displays posts along with integrated chat.
    - Includes a navbar with login, logout, and sign-up links.
    - Clicking on a post opens an overlay with post details.
    """
    if 'saved' not in session:
        session['saved'] = []

    # Handle new post creation.
    if request.method == "POST":
        if 'user' not in session:
            return redirect(url_for('login'))
        title = request.form.get("title", "").strip()
        text = request.form.get("text", "").strip()
        file = request.files.get("file")
        filename = None
        filetype = None

        if file and file.filename:
            orig_name = secure_filename(file.filename)
            filename = f"{uuid.uuid4().hex}_{orig_name}"
            try:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            except Exception as e:
                app.logger.error("Error saving file: %s", e)
                return "File upload failed", 500
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
            'title': title,
            'text': text,
            'filename': filename,
            'filetype': filetype,
            'comments': [],
            'upvotes': 0,
            'downvotes': 0
        }
        posts.append(new_post)
        return redirect(url_for('forum'))

    forum_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SVU Unofficial Forum</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            /* Basic styling */
            body { background-color: #FFFDD0; font-family: Arial, sans-serif; margin: 0; padding: 0; }
            .nav { background-color: #333; color: white; padding: 10px; text-align: right; }
            .nav a { color: #FFD700; text-decoration: none; margin-left: 15px; }
            .header { background-color: #4CAF50; color: white; padding: 30px; text-align: center; font-size: 2em; }
            .container { width: 95%; max-width: 1200px; margin: 20px auto; padding: 20px; box-sizing: border-box; }
            .chat-box, .post-form, .posts { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .chat-box { margin-bottom: 30px; }
            input[type="text"], textarea { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
            input[type="file"] { display: none; }
            .file-label { background-color: #4CAF50; color: white; padding: 10px 15px; border-radius: 5px; cursor: pointer; display: inline-block; margin-bottom: 10px; }
            .post { position: relative; background: #fff8e1; border-bottom: 1px solid #ddd; padding: 10px; margin-bottom: 10px; cursor: pointer; }
            .post:last-child { border-bottom: none; }
            .post h3 { margin: 0 0 5px; }
            .post p { margin: 5px 0; }
            .post img { max-width: 100%; margin-top: 10px; }
            .star-button { position: absolute; top: 10px; right: 10px; background: none; border: none; font-size: 1.5em; cursor: pointer; }
            .star-unsaved { color: grey; }
            .star-saved { color: #FFD700; }
            .button { background-color: #4CAF50; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
            .button:hover { background-color: #45a049; }
            .chat-message { padding: 5px; border-bottom: 1px solid #eee; }
            /* Modal overlay */
            #post-overlay {
                display: none;
                position: fixed;
                top: 0; left: 0;
                width: 100%; height: 100%;
                background: rgba(0, 0, 0, 0.6);
                z-index: 1000;
                overflow-y: auto;
            }
            #post-overlay .overlay-content {
                background: #FFFDD0;
                margin: 5% auto;
                padding: 20px;
                max-width: 800px;
                border-radius: 8px;
                position: relative;
            }
            #post-overlay .close-btn {
                position: absolute;
                top: 10px;
                right: 15px;
                font-size: 1.5em;
                cursor: pointer;
            }
            @media (max-width: 600px) {
                .header { font-size: 1.5em; padding: 20px; }
                .container { padding: 10px; }
                .button { padding: 8px 12px; }
            }
            /* Additional styling for comment/reply forms */
            .comment-form, .reply-form { margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="nav">
            {% if session.get('user') %}
                Logged in as {{ session.get('user') }} | <a href="{{ url_for('logout') }}">Logout</a>
            {% else %}
                <a href="{{ url_for('login') }}">Login</a> | <a href="{{ url_for('signup') }}">Sign Up</a>
            {% endif %}
        </div>
        <div class="header">SVU Unofficial Forum</div>
        <div class="container">
            <!-- Chat Integration -->
            <div class="chat-box">
                <h2>Community Chat</h2>
                <div id="chat-messages">
                    {% for msg in chat_messages %}
                        <div class="chat-message"><strong>{{ msg.username }}:</strong> {{ msg.message }}</div>
                    {% endfor %}
                </div>
                <form id="chat-form" onsubmit="sendChatMessage(event)">
                    <input type="text" id="chat-username" placeholder="Your name" required style="width:20%; margin-right:5px;">
                    <input type="text" id="chat-input" placeholder="Type a message..." required style="width:60%; margin-right:5px;">
                    <button type="submit" class="button">Send</button>
                </form>
            </div>
            <!-- New Post Form (requires login) -->
            <div class="post-form">
                <h2>Create a Post</h2>
                {% if session.get('user') %}
                <form method="POST" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="Post Title">
                    <textarea name="text" placeholder="What's on your mind?" rows="3"></textarea>
                    <input type="file" name="file" id="fileUpload">
                    <label for="fileUpload" class="file-label">Browse</label>
                    <br><br>
                    <button type="submit" class="button">Post</button>
                </form>
                {% else %}
                  <p>Please <a href="{{ url_for('login') }}">login</a> to create a post.</p>
                {% endif %}
            </div>
            <!-- Posts Listing -->
            <div class="posts">
                <h2>Recent Posts</h2>
                {% for post in posts %}
                    <div class="post" onclick="showPostOverlay({{ post.id }})">
                        <h3>{{ post.title }}</h3>
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
                            <span class="button">Download File</span>
                        {% endif %}
                        <button class="star-button {% if post.id in session.get('saved', []) %}star-saved{% else %}star-unsaved{% endif %}" onclick="event.stopPropagation(); toggleStar({{ post.id }}, this);">★</button>
                        <div>
                            Score: <span id="post-score-{{ post.id }}">{{ post.upvotes - post.downvotes }}</span>
                            <button onclick="votePost({{ post.id }}, 'up', event)">Upvote</button>
                            <button onclick="votePost({{ post.id }}, 'down', event)">Downvote</button>
                        </div>
                    </div>
                {% endfor %}
            </div>
            <br>
            <a href="{{ url_for('saved_posts') }}" class="button">View Saved Posts</a>
        </div>
        <!-- Modal Overlay for Post Detail -->
        <div id="post-overlay">
            <div class="overlay-content" id="overlay-content">
                <!-- Post details will be loaded here via AJAX -->
            </div>
        </div>
        <script>
            // Chat polling.
            function refreshChat() {
                fetch('/chat')
                .then(response => response.json())
                .then(data => {
                    let chatDiv = document.getElementById('chat-messages');
                    chatDiv.innerHTML = '';
                    data.forEach(function(msg) {
                        let newMsg = document.createElement('div');
                        newMsg.className = 'chat-message';
                        newMsg.innerHTML = '<strong>' + msg.username + ':</strong> ' + msg.message;
                        chatDiv.appendChild(newMsg);
                    });
                })
                .catch(err => console.error(err));
            }
            setInterval(refreshChat, 5000);
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
                    refreshChat();
                    document.getElementById('chat-input').value = '';
                })
                .catch(err => console.error(err));
            }
            // Toggle star (save post)
            function toggleStar(postId, elem) {
                fetch('/star/' + postId, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.saved) {
                        elem.classList.remove('star-unsaved');
                        elem.classList.add('star-saved');
                    } else {
                        elem.classList.remove('star-saved');
                        elem.classList.add('star-unsaved');
                    }
                    alert(data.message);
                })
                .catch(err => console.error(err));
            }
            // Vote on a post.
            function votePost(postId, action, event) {
                event.stopPropagation();
                fetch('/vote/post/' + postId, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: action})
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('post-score-' + postId).textContent = data.score;
                })
                .catch(err => console.error(err));
            }
            // Vote on a comment (or reply).
            function voteComment(postId, commentId, action, btn) {
                fetch('/vote/comment/' + postId + '/' + commentId, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: action})
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById('comment-score-' + commentId).textContent = data.score;
                })
                .catch(err => console.error(err));
            }
            // Toggle reply form visibility.
            function toggleReplyForm(commentId) {
                var form = document.getElementById('reply-form-' + commentId);
                form.style.display = (form.style.display === 'none' || form.style.display === '') ? 'block' : 'none';
            }
            // Show post overlay by fetching its details.
            function showPostOverlay(postId) {
                fetch('/post_overlay/' + postId)
                .then(response => response.text())
                .then(html => {
                    document.getElementById('overlay-content').innerHTML = html;
                    document.getElementById('post-overlay').style.display = 'block';
                })
                .catch(err => console.error(err));
            }
            // Close the overlay.
            function closeOverlay() {
                document.getElementById('post-overlay').style.display = 'none';
            }
            // Submit comment via AJAX.
            function submitComment(event, postId) {
                event.preventDefault();
                const form = event.target;
                const formData = new FormData(form);
                fetch('/comment/' + postId, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: formData
                })
                .then(response => response.json())
                .then(data => { showPostOverlay(postId); })
                .catch(err => console.error(err));
            }
            // Submit reply via AJAX.
            function submitReply(event, postId, commentId) {
                event.preventDefault();
                const form = event.target;
                const formData = new FormData(form);
                fetch('/reply/' + postId + '/' + commentId, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: formData
                })
                .then(response => response.json())
                .then(data => { showPostOverlay(postId); })
                .catch(err => console.error(err));
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(forum_template, posts=posts, chat_messages=chat_messages)


# ------------------ Post Overlay (Modal) ------------------
@app.route("/post_overlay/<int:post_id>", methods=["GET"])
def post_overlay(post_id: int):
    """
    Returns the post detail view as an HTML fragment to be displayed in an overlay.
    Includes the post content, media, AJAX voting, and nested comments with AJAX-enabled reply forms.
    """
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        return "Post not found", 404

    overlay_template = '''
    <div>
      <span class="close-btn" onclick="closeOverlay()">×</span>
      <h2>{{ post.title }}</h2>
      <p>{{ post.text }}</p>
      <div>
        Score: <span id="post-score-{{ post.id }}">{{ post.upvotes - post.downvotes }}</span>
        <button onclick="votePost({{ post.id }}, 'up', event)">Upvote</button>
        <button onclick="votePost({{ post.id }}, 'down', event)">Downvote</button>
      </div>
      {% if post.filename %}
        {% if post.filetype == 'image' %}
          <img src="{{ url_for('uploaded_file', filename=post.filename) }}" alt="Post Image" style="max-width:100%; margin-top:10px;">
        {% elif post.filetype == 'video' %}
          <video controls style="width:100%; margin-top:10px;">
            <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
            Your browser does not support the video tag.
          </video>
        {% elif post.filetype == 'audio' %}
          <audio controls style="width:100%; margin-top:10px;">
            <source src="{{ url_for('uploaded_file', filename=post.filename) }}">
            Your browser does not support the audio element.
          </audio>
        {% endif %}
        <br><br>
        <a href="{{ url_for('uploaded_file', filename=post.filename) }}" download class="button" style="margin-top:10px;">Download File</a>
      {% endif %}
      <hr>
      <h3>Add a Comment</h3>
      {% if session.get('user') %}
      <form class="comment-form" onsubmit="submitComment(event, {{ post.id }})">
        <textarea name="comment" placeholder="Add a comment" rows="2"></textarea><br>
        <button type="submit" class="button" style="margin-top:5px;">Submit Comment</button>
      </form>
      {% else %}
        <p>Please <a href="{{ url_for('login') }}">login</a> to comment.</p>
      {% endif %}
      <hr>
      <h3>Comments</h3>
      {% macro render_comment(comment) -%}
        <div class="comment" style="border-bottom:1px solid #ccc; padding:5px 0; margin-bottom:5px;">
          <div>
            {{ comment.text }} - Score: <span id="comment-score-{{ comment.id }}">{{ comment.upvotes - comment.downvotes }}</span>
            <button onclick="voteComment({{ post.id }}, {{ comment.id }}, 'up', this)">Upvote</button>
            <button onclick="voteComment({{ post.id }}, {{ comment.id }}, 'down', this)">Downvote</button>
            <button onclick="toggleReplyForm({{ comment.id }})">Reply</button>
          </div>
          <div id="reply-form-{{ comment.id }}" class="reply-form" style="display:none; margin-top:5px;">
            <form onsubmit="submitReply(event, {{ post.id }}, {{ comment.id }})">
              <textarea name="reply" placeholder="Your reply" rows="2"></textarea>
              <button type="submit" class="button">Submit Reply</button>
            </form>
          </div>
          {%- for reply in comment.replies %}
            <div class="reply" style="margin-left:20px;">
              {{ render_comment(reply) }}
            </div>
          {%- endfor %}
        </div>
      {%- endmacro %}
      <div>
        {% for comment in post.comments %}
          {{ render_comment(comment) }}
        {% endfor %}
      </div>
    </div>
    '''
    return render_template_string(overlay_template, post=post)


# ------------------ File Serving ------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename: str):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ------------------ Comment Submission ------------------
@app.route('/comment/<int:post_id>', methods=["POST"])
def comment(post_id: int):
    comment_text = request.form.get("comment", "").strip()
    post = next((p for p in posts if p['id'] == post_id), None)
    if post and comment_text:
        new_comment = {
            'id': get_next_comment_id(),
            'text': comment_text,
            'replies': [],
            'upvotes': 0,
            'downvotes': 0
        }
        post.setdefault('comments', []).append(new_comment)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    return redirect(url_for('post_overlay', post_id=post_id))


# ------------------ Reply Submission ------------------
@app.route('/reply/<int:post_id>/<int:comment_id>', methods=["POST"])
def reply(post_id: int, comment_id: int):
    reply_text = request.form.get("reply", "").strip()
    post = next((p for p in posts if p['id'] == post_id), None)
    if post and reply_text:
        parent_comment = find_comment(post.get('comments', []), comment_id)
        if parent_comment is not None:
            new_reply = {
                'id': get_next_comment_id(),
                'text': reply_text,
                'replies': [],
                'upvotes': 0,
                'downvotes': 0
            }
            parent_comment.setdefault('replies', []).append(new_reply)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    return redirect(url_for('post_overlay', post_id=post_id))


# ------------------ Toggle Star ------------------
@app.route('/star/<int:post_id>', methods=["POST"])
def star_post(post_id: int):
    if 'saved' not in session:
        session['saved'] = []
    saved_posts = session['saved']
    if post_id in saved_posts:
        saved_posts.remove(post_id)
        message = "Post unsaved!"
        saved_status = False
    else:
        saved_posts.append(post_id)
        message = "Post saved!"
        saved_status = True
    session['saved'] = saved_posts
    session.modified = True
    return jsonify({"message": message, "saved": saved_status})


# ------------------ Vote on Post (AJAX) ------------------
@app.route('/vote/post/<int:post_id>', methods=["POST"])
def vote_post_endpoint(post_id: int):
    data = request.get_json(silent=True)
    action = data.get("action") if data else None
    post = next((p for p in posts if p['id'] == post_id), None)
    if post:
        if action == "up":
            post['upvotes'] += 1
        elif action == "down":
            post['downvotes'] += 1
        score = post['upvotes'] - post['downvotes']
        return jsonify({"score": score})
    return jsonify({"error": "Post not found"}), 404


# ------------------ Vote on Comment (AJAX) ------------------
@app.route('/vote/comment/<int:post_id>/<int:comment_id>', methods=["POST"])
def vote_comment_endpoint(post_id: int, comment_id: int):
    data = request.get_json(silent=True)
    action = data.get("action") if data else None
    post = next((p for p in posts if p['id'] == post_id), None)
    if post:
        comment = find_comment(post.get('comments', []), comment_id)
        if comment:
            if action == "up":
                comment['upvotes'] += 1
            elif action == "down":
                comment['downvotes'] += 1
            score = comment['upvotes'] - comment['downvotes']
            return jsonify({"score": score})
        return jsonify({"error": "Comment not found"}), 404
    return jsonify({"error": "Post not found"}), 404


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
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background-color: #FFFDD0; font-family: Arial, sans-serif; margin: 0; padding: 0; }
            .header { background-color: #4CAF50; color: white; padding: 30px; text-align: center; font-size: 2em; }
            .container { width: 95%; max-width: 1200px; margin: 20px auto; padding: 20px; box-sizing: border-box; }
            .post { position: relative; background: #fff8e1; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); cursor: pointer; }
            .post h3 { margin: 0 0 5px; }
            .button { background-color: #4CAF50; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; text-decoration: none; }
            @media (max-width: 600px) { .header { font-size: 1.5em; padding: 20px; } .container { padding: 10px; } }
        </style>
    </head>
    <body>
        <div class="header">Saved Posts</div>
        <div class="container">
            {% for post in saved_posts_list %}
                <div class="post" onclick="showPostOverlay({{ post.id }})">
                    <h3>{{ post.title }}</h3>
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
                    <button class="star-button {% if post.id in session.get('saved', []) %}star-saved{% else %}star-unsaved{% endif %}" onclick="event.stopPropagation(); toggleStar({{ post.id }}, this);">★</button>
                </div>
            {% endfor %}
            <a href="{{ url_for('forum') }}" class="button">Back to Forum</a>
        </div>
    </body>
    </html>
    '''
    return render_template_string(saved_template, saved_posts_list=saved_posts_list)


# ------------------ Chat Integration ------------------
@app.route('/chat', methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        data = request.get_json(force=True)
        username = data.get("username", "Anonymous")
        message = data.get("message", "").strip()
        if message:
            new_message = {"username": username, "message": message}
            chat_messages.append(new_message)
            return jsonify(new_message)
        return jsonify({"error": "No message provided"}), 400
    else:
        return jsonify(chat_messages)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
