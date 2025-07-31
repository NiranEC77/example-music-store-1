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

        .album-actions {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
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

        .delete-form {
            display: inline;
        }

        .btn-danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }

        .btn-danger:hover {
            background: linear-gradient(135deg, #c82333 0%, #bd2130 100%);
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