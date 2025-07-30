from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, session, jsonify
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for sessions

# Configuration
CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://localhost:5002')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:5001')
DB_PATH = os.environ.get('DB_PATH', 'music_store.db')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'covers')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

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
            album_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(album_id) REFERENCES albums(id)
        )''')
        conn.commit()

init_db()

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Main HTML Template
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Music Store - Modern Collection</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 300;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }

        .tabs {
            display: flex;
            background: white;
            border-radius: 15px 15px 0 0;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .tab {
            flex: 1;
            padding: 20px;
            text-align: center;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: 500;
            color: #666;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
        }

        .tab.active {
            background: white;
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .tab:hover {
            background: #e9ecef;
        }

        .cart-tab {
            text-decoration: none;
            color: #666;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: 500;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            padding: 20px;
            text-align: center;
            flex: 1;
        }

        .cart-tab:hover {
            background: #e9ecef;
            color: #667eea;
        }

        .tab-content {
            background: white;
            border-radius: 0 0 15px 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            min-height: 600px;
        }

        .content-section {
            display: none;
        }

        .content-section.active {
            display: block;
        }

        .section-title {
            color: #667eea;
            margin-bottom: 25px;
            font-size: 2rem;
            font-weight: 600;
        }

        .album-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
        }

        .album-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #e9ecef;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .album-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }

        .album-cover {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 15px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.9rem;
        }

        .album-info h3 {
            color: #333;
            margin-bottom: 5px;
            font-size: 1.2rem;
        }

        .album-info p {
            color: #666;
            margin-bottom: 15px;
            font-size: 0.95rem;
        }

        .album-price {
            font-size: 1.3rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 15px;
        }

        .order-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .order-form input[type="number"] {
            width: 80px;
            padding: 8px 12px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 0.9rem;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: transform 0.2s;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .stat-label {
            font-size: 1rem;
            opacity: 0.9;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #555;
        }

        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .orders-list {
            list-style: none;
            max-height: 300px;
            overflow-y: auto;
        }

        .order-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #666;
        }

        .empty-state p {
            font-size: 1.1rem;
            margin-bottom: 10px;
        }

        @media (max-width: 768px) {
            .form-grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .album-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 Music Store</h1>
            <p>Discover and collect your favorite albums</p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('shop')">🛍️ Shop</button>
            <button class="tab" onclick="showTab('admin')">⚙️ Admin</button>
            <a href="/cart" class="tab cart-tab">🛒 Cart</a>
        </div>

        <div class="tab-content">
            <!-- Shop Tab -->
            <div id="shop" class="content-section active">
                <h2 class="section-title">📀 Available Albums</h2>
                {% if albums %}
                <div class="album-grid">
                    {% for a in albums %}
                    <div class="album-card">
                        {% if a[4] %}
                        <img src="{{a[4]}}" alt="Album cover" class="album-cover">
                        {% else %}
                        <div class="album-cover">No Cover</div>
                        {% endif %}
                        <div class="album-info">
                            <h3>{{a[1]}}</h3>
                            <p>by {{a[2]}}</p>
                            <div class="album-price">${{a[3]}}</div>
                            <form action="/add_to_cart" method="post" class="order-form">
                                <input type="hidden" name="album_id" value="{{a[0]}}">
                                <input type="number" name="quantity" value="1" min="1" placeholder="Qty">
                                <button type="submit" class="btn">Add to Cart</button>
                            </form>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="empty-state">
                    <p>No albums available yet.</p>
                    <p>Switch to Admin tab to add some albums!</p>
                </div>
                {% endif %}
            </div>

            <!-- Admin Tab -->
            <div id="admin" class="content-section">
                <h2 class="section-title">⚙️ Store Management</h2>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{{albums|length}}</div>
                        <div class="stat-label">Total Albums</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{{orders|length}}</div>
                        <div class="stat-label">Total Orders</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${{"%.2f"|format(orders|sum(attribute=4) * orders|sum(attribute=3)) if orders else 0}}</div>
                        <div class="stat-label">Total Revenue</div>
                    </div>
                </div>

                <div class="form-grid">
                    <div>
                        <h3 style="color: #667eea; margin-bottom: 20px;">➕ Add New Album</h3>
                        <form action="/add" method="post" enctype="multipart/form-data">
                            <div class="form-group">
                                <label for="name">Album Name</label>
                                <input type="text" id="name" name="name" required>
                            </div>
                            <div class="form-group">
                                <label for="artist">Artist</label>
                                <input type="text" id="artist" name="artist" required>
                            </div>
                            <div class="form-group">
                                <label for="price">Price ($)</label>
                                <input type="number" id="price" name="price" step="0.01" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="cover_file">Cover Image (File)</label>
                                <input type="file" id="cover_file" name="cover_file" accept="image/*">
                            </div>
                            <div class="form-group">
                                <label for="cover_url">Cover Image (URL)</label>
                                <input type="url" id="cover_url" name="cover_url" placeholder="https://example.com/image.jpg">
                            </div>
                            <button type="submit" class="btn" style="width: 100%; padding: 15px;">Add Album</button>
                        </form>
                    </div>

                    <div>
                        <h3 style="color: #667eea; margin-bottom: 20px;">🛒 Recent Orders</h3>
                        {% if orders %}
                        <ul class="orders-list">
                            {% for o in orders %}
                            <li class="order-item">
                                {{o[3]}}x <strong>{{o[1]}}</strong> by {{o[2]}} <span style="color: #667eea;">(${{o[4]}} each)</span>
                            </li>
                            {% endfor %}
                        </ul>
                        {% else %}
                        <div class="empty-state">
                            <p>No orders yet.</p>
                            <p>Start shopping to see orders here!</p>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // Hide all content sections
            const contentSections = document.querySelectorAll('.content-section');
            contentSections.forEach(section => {
                section.classList.remove('active');
            });
            
            // Remove active class from all tabs
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected content section
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
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

@app.route('/api/album/<int:album_id>')
def get_album(album_id):
    """API endpoint to get album details"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        album = c.execute('SELECT * FROM albums WHERE id = ?', (album_id,)).fetchone()
    
    if not album:
        return jsonify({'error': 'Album not found'}), 404
    
    return jsonify({
        'id': album[0],
        'name': album[1],
        'artist': album[2],
        'price': album[3],
        'cover_url': album[4]
    }), 200

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Redirect to cart service"""
    album_id = request.form['album_id']
    quantity = request.form['quantity']
    
    # Redirect to cart service with parameters
    return redirect(f"{CART_SERVICE_URL}/add_to_cart?album_id={album_id}&quantity={quantity}")

@app.route('/cart')
def view_cart():
    """Redirect to cart service"""
    return redirect(CART_SERVICE_URL)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 