from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory, session, jsonify
import psycopg2
import psycopg2.extras
import os
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'your-secret-key-here'  # Required for sessions

# Configuration
CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://localhost:5002')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:5001')

# Database configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'music_store')
DB_USER = os.environ.get('DB_USER', 'music_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'music_password')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'covers')

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/test-static')
def test_static():
    """Test static file serving"""
    return '''
    <h1>Static File Test</h1>
    <p>Testing album covers:</p>
    <img src="/static/covers/Pantera-VulgarDisplayofPower.jpg" alt="Pantera" style="width: 200px;">
    <img src="/static/covers/Metallica_-_...And_Justice_for_All_cover.jpg" alt="Metallica" style="width: 200px;">
    <img src="/static/covers/Sound_garden-Superunknown.jpg" alt="Soundgarden" style="width: 200px;">
    '''

@app.route('/debug-db')
def debug_db():
    """Debug database content"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute('SELECT * FROM albums')
                albums = cur.fetchall()
        
        html = '<h1>Database Debug</h1><h2>Albums in Database:</h2>'
        for album in albums:
            html += f'''
            <div style="border: 1px solid #ccc; margin: 10px; padding: 10px;">
                <h3>{album['name']} - {album['artist']}</h3>
                <p>Price: ${album['price']}</p>
                <p>Cover URL: {album['cover_url']}</p>
                <img src="{album['cover_url']}" alt="{album['name']}" style="width: 200px; border: 1px solid red;">
            </div>
            '''
        return html
    except Exception as e:
        return f'<h1>Database Error</h1><p>Error: {str(e)}</p>'

# Main HTML Template
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metal Music Store - Brutal Collection</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', 'Arial Black', sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 25%, #404040 50%, #2d2d2d 75%, #1a1a1a 100%);
            min-height: 100vh;
            color: #ffffff;
            margin: 0;
            padding: 0;
            position: relative;
            overflow-x: hidden;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 20%, rgba(255, 0, 0, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(255, 0, 0, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 60%, rgba(255, 0, 0, 0.05) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            color: #ffffff;
            position: relative;
            padding: 20px 0;
        }

        .header::before {
            content: '🤘';
            font-size: 2rem;
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
        }

        .header::after {
            content: '🤘';
            font-size: 2rem;
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
        }

        .header h1 {
            font-size: 4rem;
            font-weight: 900;
            margin-bottom: 10px;
            text-shadow: 
                0 0 5px #cc0000,
                0 0 10px #cc0000,
                2px 2px 4px rgba(0,0,0,0.8);
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 3px;
        }

        .header p {
            font-size: 1.4rem;
            opacity: 0.9;
            text-shadow: 0 0 5px rgba(204, 0, 0, 0.3);
            font-weight: 600;
        }

        .tabs {
            display: flex;
            background: linear-gradient(45deg, #1a1a1a, #2d2d2d, #1a1a1a);
            border-radius: 0;
            overflow: hidden;
            box-shadow: 
                0 5px 15px rgba(0,0,0,0.8),
                inset 0 1px 0 rgba(255,255,255,0.1);
            border: 2px solid #333;
            border-bottom: none;
        }

        .tab {
            flex: 1;
            padding: 20px;
            text-align: center;
            background: linear-gradient(45deg, #1a1a1a, #2d2d2d);
            border: none;
            cursor: pointer;
            color: #cccccc;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            position: relative;
            border-right: 1px solid #333;
            font-size: 1.1rem;
            font-weight: 500;
            color: #666;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
        }

        .tab.active {
            background: linear-gradient(45deg, #8b0000, #660000);
            color: #ffffff;
            text-shadow: 0 0 8px rgba(255, 255, 255, 0.6);
            box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
        }

        .tab.active::before {
            content: '🔥';
            position: absolute;
            top: 5px;
            right: 10px;
            font-size: 0.8rem;
        }

        .tab:hover {
            background: linear-gradient(45deg, #2d2d2d, #404040);
            color: #ffffff;
            text-shadow: 0 0 5px rgba(204, 0, 0, 0.3);
        }

        .cart-tab {
            text-decoration: none;
            color: #cccccc;
            background: linear-gradient(45deg, #1a1a1a, #2d2d2d);
            border: none;
            cursor: pointer;
            font-size: 1.1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            padding: 20px;
            text-align: center;
            flex: 1;
        }

        .cart-tab:hover {
            background: linear-gradient(45deg, #2d2d2d, #404040);
            color: #ffffff;
            text-shadow: 0 0 5px rgba(204, 0, 0, 0.3);
        }

        .tab-content {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%);
            border-radius: 0;
            padding: 30px;
            box-shadow: 
                0 10px 30px rgba(0,0,0,0.8),
                inset 0 1px 0 rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            min-height: 600px;
            border: 2px solid #333;
            border-top: none;
        }

        .content-section {
            display: none;
        }

        .content-section.active {
            display: block;
        }

        .section-title {
            color: #cc0000;
            margin-bottom: 25px;
            font-size: 2.5rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 
                0 0 5px #cc0000,
                2px 2px 4px rgba(0,0,0,0.8);
            position: relative;
        }

        .section-title::before {
            content: '⚡';
            position: absolute;
            left: -30px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 1.5rem;
        }

        .album-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
        }

        .album-card {
            background: linear-gradient(135deg, #2d2d2d 0%, #404040 50%, #2d2d2d 100%);
            border-radius: 8px;
            padding: 20px;
            border: 2px solid #333;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100%;
        }

        .album-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 0, 0, 0.1), transparent);
            transition: left 0.5s ease;
        }

        .album-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 
                0 15px 35px rgba(0,0,0,0.8),
                0 0 15px rgba(204, 0, 0, 0.3);
            border-color: #cc0000;
        }

        .album-card:hover::before {
            left: 100%;
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
            color: #ffffff;
            margin-bottom: 5px;
            font-size: 1.3rem;
            font-weight: 700;
            text-shadow: 0 0 3px rgba(204, 0, 0, 0.3);
        }

        .album-info p {
            color: #cccccc;
            margin-bottom: 15px;
            font-size: 1rem;
            font-weight: 600;
        }

        .album-price {
            font-size: 1.5rem;
            font-weight: 900;
            color: #cc0000;
            margin-bottom: 15px;
            text-shadow: 0 0 5px rgba(204, 0, 0, 0.3);
        }

        .album-actions {
            display: flex;
            flex-direction: column;
            gap: 8px;
            align-items: stretch;
            margin-top: auto;
        }

        .order-form {
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 8px;
        }

        .order-form input[type="number"] {
            width: 60px;
            padding: 8px 10px;
            border: 2px solid #333;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: 600;
            background: #1a1a1a;
            color: #ffffff;
            transition: all 0.3s ease;
            text-align: center;
        }

        .order-form input[type="number"]:focus {
            outline: none;
            border-color: #ff0000;
            box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
        }

        .delete-form {
            display: inline;
        }

        .btn-danger {
            background: linear-gradient(135deg, #660000 0%, #4d0000 100%);
            border-color: #4d0000;
            margin-top: 8px;
        }

        .btn-danger:hover {
            background: linear-gradient(135deg, #4d0000 0%, #660000 100%);
            border-color: #8b0000;
            box-shadow: 0 0 15px rgba(102, 0, 0, 0.6);
        }

        .btn {
            background: linear-gradient(135deg, #8b0000 0%, #660000 100%);
            color: white;
            border: 2px solid #333;
            padding: 10px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            text-shadow: 0 0 3px rgba(255, 255, 255, 0.2);
            width: 100%;
            margin-top: auto;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 
                0 5px 15px rgba(0,0,0,0.6),
                0 0 10px rgba(139, 0, 0, 0.3);
            background: linear-gradient(135deg, #660000 0%, #8b0000 100%);
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%);
            color: #ffffff;
            padding: 25px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid #333;
            box-shadow: 
                0 5px 15px rgba(0,0,0,0.8),
                inset 0 1px 0 rgba(255,255,255,0.1);
        }

        .stat-number {
            font-size: 3rem;
            font-weight: 900;
            margin-bottom: 10px;
            color: #cc0000;
            text-shadow: 0 0 8px rgba(204, 0, 0, 0.5);
        }

        .stat-label {
            font-size: 1.1rem;
            opacity: 0.9;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
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
            color: #ffffff;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            text-shadow: 0 0 3px rgba(204, 0, 0, 0.2);
        }

        /* Metal-themed animations */
        @keyframes metalGlow {
            0% { box-shadow: 0 0 3px rgba(204, 0, 0, 0.2); }
            50% { box-shadow: 0 0 10px rgba(204, 0, 0, 0.4); }
            100% { box-shadow: 0 0 3px rgba(204, 0, 0, 0.2); }
        }

        @keyframes headbang {
            0%, 100% { transform: rotate(0deg); }
            25% { transform: rotate(-2deg); }
            75% { transform: rotate(2deg); }
        }

        .header h1 {
            animation: metalGlow 3s ease-in-out infinite;
        }

        .album-card:hover {
            animation: headbang 0.5s ease-in-out;
        }
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
                            <h1>🤘 Metal Music Store</h1>
                            <p>Discover and collect the most brutal metal albums</p>
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
                            {% if a.cover_url %}
                            <img src="{{a.cover_url}}" alt="Album cover" class="album-cover" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                            <div class="album-cover" style="display: none;">{{a.name}}</div>
                            {% else %}
                            <div class="album-cover">{{a.name}}</div>
                            {% endif %}
                            <div class="album-info">
                                <h3>{{a.name}}</h3>
                                <p>by {{a.artist}}</p>
                                <div class="album-price">${{"%.2f"|format(a.price)}}</div>
                                <div class="album-actions">
                                    <form action="/add_to_cart" method="post" class="order-form">
                                        <input type="hidden" name="album_id" value="{{a.id}}">
                                        <input type="number" name="quantity" value="1" min="1" placeholder="Qty">
                                        <button type="submit" class="btn">Add to Cart</button>
                                    </form>
                                    <form action="/delete/{{a.id}}" method="post" class="delete-form" onsubmit="return confirm('Are you sure you want to delete this album?')">
                                        <button type="submit" class="btn btn-danger">Delete</button>
                                    </form>
                                </div>
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
                        <div class="stat-number">${{"%.2f"|format(orders|sum(attribute='price') * orders|sum(attribute='quantity')) if orders else 0}}</div>
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
                            {{o.quantity}}x <strong>{{o.name}}</strong> by {{o.artist}} <span style="color: #667eea;">(${{"%.2f"|format(o.price)}} each)</span>
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
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM albums ORDER BY created_at DESC')
            albums = cur.fetchall()
            cur.execute('''SELECT orders.id, albums.name, albums.artist, orders.quantity, albums.price 
                          FROM orders JOIN albums ON orders.album_id = albums.id 
                          ORDER BY orders.created_at DESC''')
            orders = cur.fetchall()
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
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO albums (name, artist, price, cover_url) VALUES (%s, %s, %s, %s)', 
                       (name, artist, price, cover_path))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:album_id>', methods=['POST'])
def delete_album(album_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM albums WHERE id = %s', (album_id,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/api/album/<int:album_id>')
def get_album(album_id):
    """API endpoint to get album details"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM albums WHERE id = %s', (album_id,))
            album = cur.fetchone()
    
    if not album:
        return jsonify({'error': 'Album not found'}), 404
    
    return jsonify({
        'id': album['id'],
        'name': album['name'],
        'artist': album['artist'],
        'price': float(album['price']),
        'cover_url': album['cover_url']
    }), 200

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Forward request to cart service with album details"""
    import requests
    
    try:
        # Get album details first
        album_id = request.form['album_id']
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute('SELECT * FROM albums WHERE id = %s', (album_id,))
                album = cur.fetchone()
        
        if not album:
            return jsonify({'error': 'Album not found'}), 404
        
        # Prepare data with album details
        cart_data = {
            'album_id': album_id,
            'quantity': request.form['quantity'],
            'album_name': album['name'],
            'artist': album['artist'],
            'price': str(album['price']),
            'cover_url': album['cover_url'] or ''
        }
        
        # Forward the request to cart service with album details
        response = requests.post(f"{CART_SERVICE_URL}/add_to_cart", data=cart_data)
        if response.status_code == 302:  # Redirect response
            return redirect(f"{CART_SERVICE_URL}/cart")
        else:
            return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/cart')
def view_cart():
    """Forward request to cart service"""
    import requests
    
    try:
        response = requests.get(f"{CART_SERVICE_URL}/")
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/checkout')
def checkout():
    """Forward request to cart service checkout"""
    import requests
    
    try:
        response = requests.get(f"{CART_SERVICE_URL}/checkout")
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/process_payment', methods=['POST'])
def process_payment():
    """Forward payment processing to cart service"""
    import requests
    
    try:
        response = requests.post(f"{CART_SERVICE_URL}/process_payment", data=request.form)
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/order_success')
def order_success():
    """Forward order success to cart service"""
    import requests
    
    try:
        response = requests.get(f"{CART_SERVICE_URL}/order_success")
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 