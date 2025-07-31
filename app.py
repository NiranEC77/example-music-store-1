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
USERS_SERVICE_URL = os.environ.get('USERS_SERVICE_URL', 'http://localhost:5003')

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
    <title>Vinyl Records Store - Premium Collection</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #ffffff;
            color: #1a1a1a;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 1.8rem;
            font-weight: 800;
            text-decoration: none;
            color: white;
            letter-spacing: -0.5px;
        }

        .nav-actions {
            display: flex;
            gap: 20px;
            align-items: center;
        }

        .cart-link {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }

        .cart-link:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-1px);
        }

        .admin-button {
            background: rgba(255,255,255,0.1);
            color: white;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
        }

        .admin-button:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-1px);
        }

        /* Hero Section */
        .hero {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 80px 0;
            text-align: center;
            margin-bottom: 60px;
        }

        .hero h1 {
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 20px;
            color: #1a1a1a;
            letter-spacing: -1px;
        }

        .hero p {
            font-size: 1.3rem;
            color: #666;
            max-width: 600px;
            margin: 0 auto;
            font-weight: 400;
        }

        /* Main Content */
        .main-content {
            padding: 40px 0;
        }

        .section-header {
            text-align: center;
            margin-bottom: 60px;
        }

        .section-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 16px;
            letter-spacing: -0.5px;
        }

        .section-subtitle {
            font-size: 1.1rem;
            color: #666;
            max-width: 600px;
            margin: 0 auto;
        }

        /* Album Grid */
        .album-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 30px;
            margin-bottom: 80px;
        }

        .album-card {
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            position: relative;
        }

        .album-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.12);
        }

        .album-cover-container {
            position: relative;
            overflow: hidden;
            aspect-ratio: 1;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }

        .album-cover {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }

        .album-card:hover .album-cover {
            transform: scale(1.05);
        }

        .album-cover-placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #999;
            font-size: 0.9rem;
            font-weight: 500;
            text-align: center;
            padding: 20px;
        }

        .album-info {
            padding: 24px;
        }

        .album-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 8px;
            line-height: 1.3;
        }

        .album-artist {
            font-size: 1rem;
            color: #666;
            margin-bottom: 16px;
            font-weight: 500;
        }

        .album-price {
            font-size: 1.4rem;
            font-weight: 800;
            color: #667eea;
            margin-bottom: 20px;
        }

        .album-actions {
            display: flex;
            gap: 12px;
            align-items: center;
        }

        .quantity-input {
            width: 80px;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            text-align: center;
            transition: border-color 0.3s ease;
        }

        .quantity-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .add-to-cart-btn {
            flex: 1;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 20px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .add-to-cart-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 80px 20px;
            color: #666;
        }

        .empty-state h3 {
            font-size: 1.5rem;
            margin-bottom: 16px;
            color: #1a1a1a;
        }

        .empty-state p {
            font-size: 1.1rem;
            max-width: 500px;
            margin: 0 auto;
        }

        /* Login Modal */
        .login-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            backdrop-filter: blur(5px);
        }

        .login-content {
            background: white;
            margin: 10% auto;
            padding: 40px;
            border-radius: 16px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }

        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }

        .login-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 8px;
        }

        .login-subtitle {
            color: #666;
            font-size: 1rem;
        }

        .close {
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 24px;
            font-weight: bold;
            color: #999;
            cursor: pointer;
            transition: color 0.3s ease;
        }

        .close:hover {
            color: #1a1a1a;
        }

        .login-form {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .form-group label {
            font-weight: 600;
            color: #1a1a1a;
            font-size: 0.9rem;
        }

        .form-group input {
            padding: 14px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .login-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 16px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .error-message {
            color: #e74c3c;
            text-align: center;
            margin: 10px 0;
            display: none;
            font-size: 0.9rem;
        }

        /* Cart Notification */
        .cart-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
            z-index: 1000;
            transform: translateX(400px);
            transition: transform 0.3s ease;
            max-width: 320px;
            border: 1px solid #e1e5e9;
        }

        .cart-notification.show {
            transform: translateX(0);
        }

        .cart-notification h3 {
            color: #1a1a1a;
            margin-bottom: 12px;
            font-size: 1.2rem;
            font-weight: 700;
        }

        .cart-notification p {
            color: #666;
            margin-bottom: 20px;
            line-height: 1.5;
        }

        .cart-notification .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin-right: 10px;
        }

        .cart-notification .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
        }

        .cart-notification .btn-secondary {
            background: #f8f9fa;
            color: #666;
            border: 1px solid #e1e5e9;
        }

        .cart-notification .btn-secondary:hover {
            background: #e9ecef;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .container {
                padding: 0 16px;
            }

            .hero {
                padding: 60px 0;
            }

            .hero h1 {
                font-size: 2.5rem;
            }

            .hero p {
                font-size: 1.1rem;
            }

            .section-title {
                font-size: 2rem;
            }

            .album-grid {
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 20px;
            }

            .header-content {
                flex-direction: column;
                gap: 20px;
            }

            .nav-actions {
                width: 100%;
                justify-content: center;
            }
        }

        @media (max-width: 480px) {
            .album-grid {
                grid-template-columns: 1fr;
            }

            .hero h1 {
                font-size: 2rem;
            }

            .album-actions {
                flex-direction: column;
                gap: 16px;
            }

            .quantity-input {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="container">
            <div class="header-content">
                <a href="/" class="logo">Vinyl Records</a>
                <div class="nav-actions">
                    <a href="/cart" class="cart-link">🛒 Cart</a>
                    <button class="admin-button" onclick="showLoginModal()">Admin</button>
                </div>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <h1>Discover Premium Vinyl Records</h1>
            <p>Explore our curated collection of classic and contemporary albums on vinyl</p>
        </div>
    </section>

    <!-- Main Content -->
    <main class="main-content">
        <div class="container">
            <div class="section-header">
                <h2 class="section-title">Available Albums</h2>
                <p class="section-subtitle">Browse our collection of carefully selected vinyl records</p>
            </div>

            {% if albums %}
            <div class="album-grid">
                {% for a in albums %}
                <div class="album-card">
                    <div class="album-cover-container">
                        {% if a.cover_url %}
                        <img src="{{a.cover_url}}" alt="{{a.name}} cover" class="album-cover" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                        <div class="album-cover-placeholder" style="display: none;">{{a.name}}</div>
                        {% else %}
                        <div class="album-cover-placeholder">{{a.name}}</div>
                        {% endif %}
                    </div>
                    <div class="album-info">
                        <h3 class="album-title">{{a.name}}</h3>
                        <p class="album-artist">{{a.artist}}</p>
                        <div class="album-price">${{"%.2f"|format(a.price)}}</div>
                        <div class="album-actions">
                            <form action="/add_to_cart" method="post" onsubmit="return addToCart(event, this)">
                                <input type="hidden" name="album_id" value="{{a.id}}">
                                <div style="display: flex; gap: 12px; align-items: center;">
                                    <input type="number" name="quantity" value="1" min="1" class="quantity-input" placeholder="Qty">
                                    <button type="submit" class="add-to-cart-btn">Add to Cart</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <h3>No albums available</h3>
                <p>We're currently updating our collection. Please check back soon or contact the store administrator to add some albums!</p>
            </div>
            {% endif %}
        </div>
    </main>

    <!-- Login Modal -->
    <div id="loginModal" class="login-modal">
        <div class="login-content">
            <span class="close" onclick="closeLoginModal()">&times;</span>
            <div class="login-header">
                <h2 class="login-title">Store Administration</h2>
                <p class="login-subtitle">Sign in to manage your store</p>
            </div>
            <div class="error-message" id="loginError"></div>
            <form class="login-form" onsubmit="return handleLogin(event)">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="login-btn">Sign In</button>
            </form>
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

        function showLoginModal() {
            document.getElementById('loginModal').style.display = 'block';
            document.getElementById('username').focus();
        }

        function closeLoginModal() {
            document.getElementById('loginModal').style.display = 'none';
            document.getElementById('loginError').style.display = 'none';
            document.getElementById('username').value = '';
            document.getElementById('password').value = '';
        }

        function handleLogin(event) {
            event.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('loginError');
            
            // Call login API
            fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Store token in localStorage
                    localStorage.setItem('adminToken', data.token);
                    localStorage.setItem('adminUser', JSON.stringify(data.user));
                    
                    // Close modal and redirect to admin page
                    closeLoginModal();
                    window.location.href = '/admin';
                } else {
                    errorDiv.textContent = data.error || 'Login failed';
                    errorDiv.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                errorDiv.textContent = 'Login failed. Please try again.';
                errorDiv.style.display = 'block';
            });
            
            return false;
        }

        // Close modal when clicking outside of it
        window.onclick = function(event) {
            const modal = document.getElementById('loginModal');
            if (event.target == modal) {
                closeLoginModal();
            }
        }

        function addToCart(event, form) {
            event.preventDefault();
            
            const formData = new FormData(form);
            
            fetch('/add_to_cart', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showCartNotification(data.redirect_url);
                } else {
                    alert('Error adding to cart: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error adding to cart');
            });
            
            return false;
        }

        function showCartNotification(redirectUrl) {
            // Remove existing notification
            const existing = document.querySelector('.cart-notification');
            if (existing) {
                existing.remove();
            }
            
            // Create notification
            const notification = document.createElement('div');
            notification.className = 'cart-notification';
            notification.innerHTML = `
                <h3>🎉 Item Added!</h3>
                <p>Your vinyl record has been added to the cart successfully!</p>
                <a href="/cart" class="btn">View Cart</a>
                <button class="btn btn-secondary" onclick="this.parentElement.remove()">Continue Shopping</button>
            `;
            
            document.body.appendChild(notification);
            
            // Show notification
            setTimeout(() => {
                notification.classList.add('show');
            }, 100);
            
            // Auto-hide after 8 seconds
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 300);
            }, 8000);
        }
    </script>
</body>
</html>
'''

# Admin HTML Template
ADMIN_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Store Administration - Metal Music Store</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', 'Arial Black', sans-serif;
            background: linear-gradient(135deg, #404040 0%, #555555 25%, #666666 50%, #555555 75%, #404040 100%);
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

        .admin-info {
            position: absolute;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #8b0000 0%, #660000 100%);
            padding: 10px 20px;
            border-radius: 6px;
            border: 2px solid #333;
            font-size: 0.9rem;
        }

        .back-button {
            position: absolute;
            top: 20px;
            left: 20px;
            background: linear-gradient(135deg, #404040 0%, #333333 100%);
            color: white;
            border: 2px solid #333;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            text-decoration: none;
            text-shadow: 0 0 3px rgba(255, 255, 255, 0.2);
        }

        .back-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.6);
            background: linear-gradient(135deg, #333333 0%, #404040 100%);
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

        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #333;
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s;
            background: #1a1a1a;
            color: #ffffff;
        }

        .form-group input:focus {
            outline: none;
            border-color: #cc0000;
            box-shadow: 0 0 10px rgba(204, 0, 0, 0.3);
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
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 
                0 5px 15px rgba(0,0,0,0.6),
                0 0 10px rgba(139, 0, 0, 0.3);
            background: linear-gradient(135deg, #660000 0%, #8b0000 100%);
        }

        .btn-danger {
            background: linear-gradient(135deg, #660000 0%, #4d0000 100%);
            border-color: #4d0000;
        }

        .btn-danger:hover {
            background: linear-gradient(135deg, #4d0000 0%, #660000 100%);
            border-color: #8b0000;
            box-shadow: 0 0 15px rgba(102, 0, 0, 0.6);
        }

        .orders-list {
            list-style: none;
            max-height: 300px;
            overflow-y: auto;
        }

        .order-item {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #cc0000;
            border: 2px solid #333;
        }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #cccccc;
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
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-button">← Back to Store</a>
            <div class="admin-info">
                Logged in as: {{user.username}}
            </div>
            <h1>⚙️ Store Administration</h1>
            <p>Manage your brutal metal collection</p>
        </div>

        <h2 class="section-title">📊 Store Statistics</h2>
        
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
                <h3 style="color: #cc0000; margin-bottom: 20px;">➕ Add New Album</h3>
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
                <h3 style="color: #cc0000; margin-bottom: 20px;">🛒 Recent Orders</h3>
                {% if orders %}
                <ul class="orders-list">
                    {% for o in orders %}
                    <li class="order-item">
                        {{o.quantity}}x <strong>{{o.name}}</strong> by {{o.artist}} <span style="color: #cc0000;">(${{"%.2f"|format(o.price)}} each)</span>
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

        <div style="margin-top: 40px;">
            <h3 style="color: #cc0000; margin-bottom: 20px;">🗑️ Manage Albums</h3>
            {% if albums %}
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px;">
                {% for a in albums %}
                <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%); border: 2px solid #333; border-radius: 8px; padding: 20px;">
                    <h4 style="color: #ffffff; margin-bottom: 10px;">{{a.name}}</h4>
                    <p style="color: #cccccc; margin-bottom: 15px;">by {{a.artist}}</p>
                    <p style="color: #cc0000; font-weight: bold; margin-bottom: 15px;">${{"%.2f"|format(a.price)}}</p>
                    <form action="/delete/{{a.id}}" method="post" style="display: inline;" onsubmit="return confirm('Are you sure you want to delete {{a.name}}?')">
                        <button type="submit" class="btn btn-danger" style="width: 100%;">Delete Album</button>
                    </form>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty-state">
                <p>No albums to manage.</p>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        // Check if user is still authenticated
        function checkAuth() {
            const token = localStorage.getItem('adminToken');
            if (!token) {
                window.location.href = '/';
                return;
            }

            fetch('/api/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: token })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.valid || data.user.role !== 'admin') {
                    localStorage.removeItem('adminToken');
                    localStorage.removeItem('adminUser');
                    window.location.href = '/';
                }
            })
            .catch(error => {
                console.error('Auth check failed:', error);
                localStorage.removeItem('adminToken');
                localStorage.removeItem('adminUser');
                window.location.href = '/';
            });
        }

        // Check auth every 5 minutes
        setInterval(checkAuth, 300000);
        
        // Check auth on page load
        checkAuth();
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
        
        # Get or create session_id
        if 'cart_session_id' not in session:
            session['cart_session_id'] = os.urandom(16).hex()
        
        # Prepare data with album details and session_id
        cart_data = {
            'album_id': album_id,
            'quantity': request.form['quantity'],
            'album_name': album['name'],
            'artist': album['artist'],
            'price': str(album['price']),
            'cover_url': album['cover_url'] or '',
            'session_id': session['cart_session_id']
        }
        
        # Forward the request to cart service with album details
        response = requests.post(f"{CART_SERVICE_URL}/add_to_cart", data=cart_data)
        
        if response.status_code == 200:
            # Parse JSON response
            result = response.json()
            if result.get('success'):
                # Update session_id if provided
                if 'session_id' in result:
                    session['cart_session_id'] = result['session_id']
                # Return success with redirect info for JavaScript handling
                return jsonify({
                    'success': True,
                    'message': 'Item added to cart!',
                    'redirect_url': f"{CART_SERVICE_URL}/?session_id={session['cart_session_id']}"
                })
            else:
                return jsonify(result), 400
        else:
            return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/cart')
def view_cart():
    """Forward request to cart service"""
    import requests
    
    try:
        # Get session_id from our session
        session_id = session.get('cart_session_id')
        if not session_id:
            # Create new session if none exists
            session['cart_session_id'] = os.urandom(16).hex()
            session_id = session['cart_session_id']
        
        # Pass session_id as query parameter
        response = requests.get(f"{CART_SERVICE_URL}/?session_id={session_id}")
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/checkout')
def checkout():
    """Forward request to cart service checkout"""
    import requests
    
    try:
        # Get session_id from our session
        session_id = session.get('cart_session_id')
        if not session_id:
            return redirect(url_for('view_cart'))
        
        # Pass session_id as query parameter
        response = requests.get(f"{CART_SERVICE_URL}/checkout?session_id={session_id}")
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/process_payment', methods=['POST'])
def process_payment():
    """Forward payment processing to cart service"""
    import requests
    
    try:
        # Get session_id from our session
        session_id = session.get('cart_session_id')
        if not session_id:
            return redirect(url_for('view_cart'))
        
        # Add session_id to the form data
        form_data = request.form.copy()
        form_data['session_id'] = session_id
        
        response = requests.post(f"{CART_SERVICE_URL}/process_payment", data=form_data, allow_redirects=False)
        
        # Handle redirects from cart service
        if response.status_code in [301, 302, 303, 307, 308]:
            redirect_url = response.headers.get('Location', '')
            if redirect_url.startswith('/'):
                # If it's a relative URL, redirect to our order_success route
                return redirect(url_for('order_success'))
            else:
                # If it's an absolute URL, redirect to it
                return redirect(redirect_url)
        
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/remove_item', methods=['POST'])
def remove_item():
    """Forward remove item request to cart service"""
    import requests
    
    try:
        # Get session_id from our session
        session_id = session.get('cart_session_id')
        if not session_id:
            return redirect(url_for('view_cart'))
        
        # Forward the request with session_id
        cart_data = {
            'item_id': request.form['item_id'],
            'session_id': session_id
        }
        response = requests.post(f"{CART_SERVICE_URL}/remove_item", data=cart_data)
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    """Forward update quantity request to cart service"""
    import requests
    
    try:
        # Get session_id from our session
        session_id = session.get('cart_session_id')
        if not session_id:
            return redirect(url_for('view_cart'))
        
        # Forward the request with session_id
        cart_data = {
            'item_id': request.form['item_id'],
            'quantity': request.form['quantity'],
            'session_id': session_id
        }
        response = requests.post(f"{CART_SERVICE_URL}/update_quantity", data=cart_data)
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/order_success')
def order_success():
    """Forward order success to cart service"""
    import requests
    
    try:
        # Get session_id from our session
        session_id = session.get('cart_session_id')
        if not session_id:
            return redirect(url_for('index'))
        
        # Pass session_id as query parameter
        response = requests.get(f"{CART_SERVICE_URL}/order_success?session_id={session_id}")
        return response.content, response.status_code
    except requests.RequestException as e:
        return f"Error connecting to cart service: {str(e)}", 503

@app.route('/api/login', methods=['POST'])
def login():
    """Forward login request to users service"""
    import requests
    
    try:
        response = requests.post(f"{USERS_SERVICE_URL}/api/login", json=request.get_json())
        return response.content, response.status_code
    except requests.RequestException as e:
        return jsonify({'error': f'Users service unavailable: {str(e)}'}), 503

@app.route('/api/logout', methods=['POST'])
def logout():
    """Forward logout request to users service"""
    import requests
    
    try:
        response = requests.post(f"{USERS_SERVICE_URL}/api/logout", json=request.get_json())
        return response.content, response.status_code
    except requests.RequestException as e:
        return jsonify({'error': f'Users service unavailable: {str(e)}'}), 503

@app.route('/api/verify', methods=['POST'])
def verify_token():
    """Forward token verification to users service"""
    import requests
    
    try:
        response = requests.post(f"{USERS_SERVICE_URL}/api/verify", json=request.get_json())
        return response.content, response.status_code
    except requests.RequestException as e:
        return jsonify({'error': f'Users service unavailable: {str(e)}'}), 503

@app.route('/admin')
def admin_panel():
    """Admin panel - authentication handled by JavaScript"""
    # Get albums and orders for admin panel
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM albums ORDER BY created_at DESC')
            albums = cur.fetchall()
            cur.execute('''SELECT orders.id, albums.name, albums.artist, orders.quantity, albums.price 
                          FROM orders JOIN albums ON orders.album_id = albums.id 
                          ORDER BY orders.created_at DESC''')
            orders = cur.fetchall()
    
    # Let JavaScript handle authentication
    return render_template_string(ADMIN_HTML, albums=albums, orders=orders, user=None)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 