from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os, uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configure upload folder.
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory storage.
# Each post: { id, title, text, filename, filetype, comments (list), upvotes, downvotes }
posts = []
# Each comment or reply: { id, text, replies (list), upvotes, downvotes }
comment_id_counter = 1
chat_messages = []  # Each message: { username, message }


def get_next_post_id():
    return posts[-1]['id'] + 1 if posts else 1


def get_next_comment_id():
    global comment_id_counter
    cid = comment_id_counter
    comment_id_counter += 1
    return cid


def find_comment(comments, comment_id):
    """Recursively search for a comment with the given id."""
    for comment in comments:
        if comment['id'] == comment_id:
            return comment
        found = find_comment(comment.get('replies', []), comment_id)
        if found:
            return found
    return None


# ------------------ Homepage ------------------
@app.route("/")
def homepage():
    template = '''
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
    return render_template_string(template)


# ------------------ Forum Page ------------------
@app.route("/forum", methods=["GET", "POST"])
def forum():
    if 'saved' not in session:
        session['saved'] = []
    # Handle new post submission.
    if request.method == "POST":
        title = request.form.get("title")
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
            body { background-color: #FFFDD0; font-family: Arial, sans-serif; margin: 0; padding: 0; }
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
            @media (max-width: 600px) {
                .header { font-size: 1.5em; padding: 20px; }
                .container { padding: 10px; }
                .button { padding: 8px 12px; }
            }
        </style>
    </head>
    <body>
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
            <!-- New Post Form -->
            <div class="post-form">
                <h2>Create a Post</h2>
                <form method="POST" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="Post Title">
                    <textarea name="text" placeholder="What's on your mind?" rows="3"></textarea>
                    <input type="file" name="file" id="fileUpload">
                    <label for="fileUpload" class="file-label">Browse</label>
                    <br><br>
                    <button type="submit" class="button">Post</button>
                </form>
            </div>
            <!-- Posts Listing -->
            <div class="posts">
                <h2>Recent Posts</h2>
                {% for post in posts %}
                    <div class="post" onclick="window.location.href='{{ url_for('post_detail', post_id=post.id) }}'">
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
        <script>
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
                })
                .catch(err => console.error(err));
            }
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
        </script>
    </body>
    </html>
    '''
    return render_template_string(forum_template, posts=posts, chat_messages=chat_messages)


# ------------------ Post Detail Page ------------------
@app.route("/post/<int:post_id>", methods=["GET"])
def post_detail(post_id):
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        return "Post not found", 404
    detail_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ post.title }} - Details</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background-color: #FFFDD0; font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
            .button { background-color: #4CAF50; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; text-decoration: none; }
            .button:hover { background-color: #45a049; }
            .comment, .reply { border-bottom: 1px solid #ccc; padding: 5px 0; margin-left: 20px; }
            textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{{ post.title }}</h2>
        </div>
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
            <a href="{{ url_for('uploaded_file', filename=post.filename) }}" download class="button" style="margin-top:10px; padding:10px 20px;">Download File</a>
        {% endif %}
        <br><br>
        <button class="button" onclick="window.location.href='{{ url_for('star_post', post_id=post.id) }}'">★ Save Post</button>
        <hr>
        <h3>Add a Comment</h3>
        <form action="{{ url_for('comment', post_id=post.id) }}" method="POST">
            <textarea name="comment" placeholder="Add a comment" rows="2"></textarea><br>
            <button type="submit" class="button" style="margin-top:5px;">Submit Comment</button>
        </form>
        <hr>
        <h3>Comments</h3>
        {% macro render_comment(comment) %}
            <div class="comment">
                {{ comment.text }} - Score: {{ comment.upvotes - comment.downvotes }}
                <form action="{{ url_for('vote_comment_endpoint', post_id=post.id, comment_id=comment.id) }}" method="POST" style="display:inline;">
                    <button type="submit">Upvote</button>
                    <button type="submit" formaction="{{ url_for('vote_comment_endpoint', post_id=post.id, comment_id=comment.id) }}" formmethod="POST" name="action" value="down">Downvote</button>
                </form>
                <br>
                <form action="{{ url_for('reply', post_id=post.id, comment_id=comment.id) }}" method="POST">
                    <textarea name="reply" placeholder="Reply" rows="1"></textarea>
                    <button type="submit" class="button">Submit Reply</button>
                </form>
                {% for reply in comment.replies %}
                    <div class="reply">
                        {{ reply.text }} - Score: {{ reply.upvotes - reply.downvotes }}
                        <form action="{{ url_for('vote_comment_endpoint', post_id=post.id, comment_id=reply.id) }}" method="POST" style="display:inline;">
                            <button type="submit">Upvote</button>
                            <button type="submit" formaction="{{ url_for('vote_comment_endpoint', post_id=post.id, comment_id=reply.id) }}" formmethod="POST" name="action" value="down">Downvote</button>
                        </form>
                    </div>
                {% endfor %}
            </div>
        {% endmacro %}
        <div>
            {% for comment in post.comments %}
                {{ render_comment(comment) }}
            {% endfor %}
        </div>
        <script>
            function votePost(postId, action, event) {
                event.preventDefault();
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
        </script>
    </body>
    </html>
    '''
    return render_template_string(detail_template, post=post)


# ------------------ File Serving ------------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ------------------ Comment Submission (Non-AJAX) ------------------
@app.route('/comment/<int:post_id>', methods=["POST"])
def comment(post_id):
    comment_text = request.form.get("comment")
    post = next((p for p in posts if p['id'] == post_id), None)
    if post and comment_text:
        comment = {
            'id': get_next_comment_id(),
            'text': comment_text,
            'replies': [],
            'upvotes': 0,
            'downvotes': 0
        }
        post.setdefault('comments', []).append(comment)
    return redirect(url_for('post_detail', post_id=post_id))


# ------------------ Reply Submission (Non-AJAX) ------------------
@app.route('/reply/<int:post_id>/<int:comment_id>', methods=["POST"])
def reply(post_id, comment_id):
    reply_text = request.form.get("reply")
    post = next((p for p in posts if p['id'] == post_id), None)
    if post and reply_text:
        parent_comment = find_comment(post.get('comments', []), comment_id)
        if parent_comment is not None:
            reply = {
                'id': get_next_comment_id(),
                'text': reply_text,
                'replies': [],
                'upvotes': 0,
                'downvotes': 0
            }
            parent_comment.setdefault('replies', []).append(reply)
    return redirect(url_for('post_detail', post_id=post_id))


# ------------------ Toggle Star ------------------
@app.route('/star/<int:post_id>', methods=["POST"])
def star_post(post_id):
    if 'saved' not in session:
        session['saved'] = []
    saved = session['saved']
    if post_id in saved:
        saved.remove(post_id)
        session['saved'] = saved
        message = "Post unsaved!"
        saved_status = False
    else:
        saved.append(post_id)
        session['saved'] = saved
        message = "Post saved!"
        saved_status = True
    return jsonify({"message": message, "saved": saved_status})


# ------------------ Vote on Post (AJAX) ------------------
@app.route('/vote/post/<int:post_id>', methods=["POST"])
def vote_post_endpoint(post_id):
    data = request.get_json()
    action = data.get("action")
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
def vote_comment_endpoint(post_id, comment_id):
    data = request.get_json()
    action = data.get("action")
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
            .post { position: relative; background: #fff8e1; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .post h3 { margin: 0 0 5px; }
            .button { background-color: #4CAF50; color: white; border: none; padding: 10px 15px; border-radius: 5px; cursor: pointer; text-decoration: none; }
            @media (max-width: 600px) { .header { font-size: 1.5em; padding: 20px; } .container { padding: 10px; } }
        </style>
    </head>
    <body>
        <div class="header">Saved Posts</div>
        <div class="container">
            {% for post in saved_posts_list %}
                <div class="post" onclick="window.location.href='{{ url_for('post_detail', post_id=post.id) }}'">
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


if __name__ == '__main__':
    # Listen on all interfaces.
    app.run(debug=True, host='0.0.0.0')
