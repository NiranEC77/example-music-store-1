from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_PATH = os.environ.get('DB_PATH', 'music_store.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'covers')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS albums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            artist TEXT NOT NULL,
            price REAL NOT NULL,
            cover_url TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            album_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY(album_id) REFERENCES albums(id)
        )''')
        conn.commit()

init_db()

# --- Templates ---
INDEX_HTML = '''
<!doctype html>
<title>Music Store 1</title>
<h1>Music Albums</h1>
<ul>
{% for a in albums %}
  <li>
    {% if a[4] %}
      <img src="{{a[4]}}" alt="cover" style="height:60px;width:60px;object-fit:cover;vertical-align:middle;margin-right:10px;">
    {% endif %}
    <b>{{a[1]}}</b> by {{a[2]}} - ${{a[3]}}
    <form action="/order" method="post" style="display:inline">
      <input type="hidden" name="album_id" value="{{a[0]}}">
      <input type="number" name="quantity" value="1" min="1" style="width:40px">
      <button type="submit">Order</button>
    </form>
  </li>
{% endfor %}
</ul>
<h2>Add Album</h2>
<form action="/add" method="post" enctype="multipart/form-data">
  Name: <input name="name"> 
  Artist: <input name="artist"> 
  Price: <input name="price" type="number" step="0.01"> <br>
  Cover Image File: <input type="file" name="cover_file"> <br>
  Or Cover Image URL: <input name="cover_url"> <br>
  <button type="submit">Add</button>
</form>
<h2>Orders</h2>
<ul>
{% for o in orders %}
  <li>{{o[3]}} x <b>{{o[1]}}</b> by {{o[2]}} (${{o[4]}} each)</li>
{% endfor %}
</ul>
'''

# --- Routes ---
@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        albums = c.execute('SELECT * FROM albums').fetchall()
        orders = c.execute('''SELECT orders.id, albums.name, albums.artist, orders.quantity, albums.price FROM orders JOIN albums ON orders.album_id = albums.id''').fetchall()
    return render_template_string(INDEX_HTML, albums=albums, orders=orders)

@app.route('/add', methods=['POST'])
def add_album():
    name = request.form['name']
    artist = request.form['artist']
    price = float(request.form['price'])
    cover_url = request.form.get('cover_url', '').strip()
    cover_file = request.files.get('cover_file')
    cover_path = ''
    if cover_file and cover_file.filename != '' and allowed_file(cover_file.filename):
        filename = secure_filename(cover_file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Ensure unique filename
        base, ext = os.path.splitext(filename)
        i = 1
        while os.path.exists(save_path):
            filename = f"{base}_{i}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            i += 1
        cover_file.save(save_path)
        cover_path = url_for('static', filename=f'covers/{filename}')
    elif cover_url:
        cover_path = cover_url
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO albums (name, artist, price, cover_url) VALUES (?, ?, ?, ?)', (name, artist, price, cover_path))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/order', methods=['POST'])
def order():
    album_id = int(request.form['album_id'])
    quantity = int(request.form['quantity'])
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO orders (album_id, quantity) VALUES (?, ?)', (album_id, quantity))
        conn.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 