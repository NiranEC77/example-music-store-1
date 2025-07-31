from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import sqlite3
import os
import requests
import json

app = Flask(__name__)
app.secret_key = 'cart-secret-key-here'

# Configuration
CART_DB_PATH = os.environ.get('CART_DB_PATH', 'cart.db')
ORDER_SERVICE_URL = os.environ.get('ORDER_SERVICE_URL', 'http://localhost:5001')
STORE_SERVICE_URL = os.environ.get('STORE_SERVICE_URL', 'http://localhost:5000')

def init_cart_db():
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            album_id INTEGER NOT NULL,
            album_name TEXT NOT NULL,
            artist TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            cover_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()

init_cart_db()

@app.route('/')
def cart():
    # Get session_id from query parameter or session
    session_id = request.args.get('session_id')
    if not session_id:
        if 'session_id' not in session:
            session['session_id'] = os.urandom(16).hex()
        session_id = session['session_id']
    else:
        # Use the provided session_id and store it in our session
        session['session_id'] = session_id
    
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        cart_items = c.execute('''
            SELECT * FROM cart_items 
            WHERE session_id = ? 
            ORDER BY created_at DESC
        ''', (session_id,)).fetchall()
    
    total = sum(item[6] * item[5] for item in cart_items)  # quantity * price
    
    return render_template_string(CART_HTML, cart_items=cart_items, total=total)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    # Get session_id from request or create new one
    session_id = request.form.get('session_id')
    if not session_id:
        if 'session_id' not in session:
            session['session_id'] = os.urandom(16).hex()
        session_id = session['session_id']
    else:
        # Use the provided session_id and store it in our session
        session['session_id'] = session_id
    
    album_id = int(request.form['album_id'])
    quantity = int(request.form['quantity'])
    
    # Get album details from form data (sent by store service)
    album_name = request.form.get('album_name')
    artist = request.form.get('artist')
    price = float(request.form.get('price', 0))
    cover_url = request.form.get('cover_url', '')
    
    # If album details not provided, try to get from store service
    if not album_name or not artist:
        try:
            api_url = f"{STORE_SERVICE_URL}/api/album/{album_id}"
            print(f"DEBUG: Trying to connect to store service at: {api_url}")
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                album = response.json()
                album_name = album['name']
                artist = album['artist']
                price = album['price']
                cover_url = album.get('cover_url', '')
            else:
                return jsonify({'error': f'Album not found. Status: {response.status_code}'}), 404
        except requests.RequestException as e:
            print(f"DEBUG: Request failed: {e}")
            return jsonify({'error': f'Store service unavailable: {str(e)}'}), 503
    
    # Add to cart
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        
        # Check if item already in cart
        existing = c.execute('''
            SELECT id, quantity FROM cart_items 
            WHERE session_id = ? AND album_id = ?
        ''', (session_id, album_id)).fetchone()
        
        if existing:
            # Update quantity
            new_quantity = existing[1] + quantity
            c.execute('''
                UPDATE cart_items 
                SET quantity = ? 
                WHERE id = ?
            ''', (new_quantity, existing[0]))
        else:
            # Add new item
            c.execute('''
                INSERT INTO cart_items (session_id, album_id, album_name, artist, price, quantity, cover_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, album_id, album_name, artist, price, quantity, cover_url))
        
        conn.commit()
    
    # Return JSON response with session_id for store service to use
    return jsonify({
        'success': True,
        'message': 'Item added to cart',
        'session_id': session_id,
        'redirect_url': url_for('cart')
    })

@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    # Get session_id from request or session
    session_id = request.form.get('session_id')
    if not session_id:
        if 'session_id' not in session:
            return redirect(url_for('cart'))
        session_id = session['session_id']
    else:
        # Use the provided session_id and store it in our session
        session['session_id'] = session_id
    
    item_id = int(request.form['item_id'])
    quantity = int(request.form['quantity'])
    
    if quantity <= 0:
        # Remove item
        with sqlite3.connect(CART_DB_PATH) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM cart_items WHERE id = ? AND session_id = ?', 
                     (item_id, session_id))
            conn.commit()
    else:
        # Update quantity
        with sqlite3.connect(CART_DB_PATH) as conn:
            c = conn.cursor()
            c.execute('UPDATE cart_items SET quantity = ? WHERE id = ? AND session_id = ?', 
                     (quantity, item_id, session_id))
            conn.commit()
    
    return redirect(url_for('cart'))

@app.route('/remove_item', methods=['POST'])
def remove_item():
    # Get session_id from request or session
    session_id = request.form.get('session_id')
    if not session_id:
        if 'session_id' not in session:
            return redirect(url_for('cart'))
        session_id = session['session_id']
    else:
        # Use the provided session_id and store it in our session
        session['session_id'] = session_id
    
    item_id = int(request.form['item_id'])
    
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM cart_items WHERE id = ? AND session_id = ?', 
                 (item_id, session_id))
        conn.commit()
    
    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    # Get session_id from query parameter or session
    session_id = request.args.get('session_id')
    if not session_id:
        if 'session_id' not in session:
            return redirect(url_for('cart'))
        session_id = session['session_id']
    else:
        # Use the provided session_id and store it in our session
        session['session_id'] = session_id
    
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        cart_items = c.execute('''
            SELECT * FROM cart_items 
            WHERE session_id = ? 
            ORDER BY created_at DESC
        ''', (session_id,)).fetchall()
    
    if not cart_items:
        return redirect(url_for('cart'))
    
    total = sum(item[6] * item[5] for item in cart_items)
    
    return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    # Get session_id from request or session
    session_id = request.form.get('session_id')
    if not session_id:
        if 'session_id' not in session:
            return redirect(url_for('cart'))
        session_id = session['session_id']
    else:
        # Use the provided session_id and store it in our session
        session['session_id'] = session_id
    
    # Get cart items
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        cart_items = c.execute('''
            SELECT * FROM cart_items 
            WHERE session_id = ?
        ''', (session_id,)).fetchall()
    
    if not cart_items:
        return redirect(url_for('cart'))
    
    # Validate all form fields
    required_fields = [
        'card_number', 'expiry', 'cvv', 'cardholder_name',
        'shipping_first_name', 'shipping_last_name', 'shipping_address', 
        'shipping_city', 'shipping_state', 'shipping_zip', 'shipping_country',
        'billing_first_name', 'billing_last_name', 'billing_address',
        'billing_city', 'billing_state', 'billing_zip', 'billing_country',
        'email', 'phone'
    ]
    
    for field in required_fields:
        if not request.form.get(field, '').strip():
            total = sum(item[6] * item[5] for item in cart_items)
            return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                        error=f"Please fill in all required fields. Missing: {field.replace('_', ' ').title()}")
    
    # Validate payment details
    card_number = request.form.get('card_number', '').replace(' ', '')
    expiry = request.form.get('expiry', '')
    cvv = request.form.get('cvv', '')
    cardholder_name = request.form.get('cardholder_name', '').strip()
    
    # Enhanced validation
    if len(card_number) < 13 or len(card_number) > 19:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                    error="Invalid card number. Please enter a valid credit card number.")
    
    if len(cvv) < 3 or len(cvv) > 4:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                    error="Invalid CVV. Please enter a valid 3 or 4 digit CVV.")
    
    if len(cardholder_name) < 2:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                    error="Please enter the cardholder name as it appears on the card.")
    
    # Validate email format
    import re
    email = request.form.get('email', '').strip()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                    error="Please enter a valid email address.")
    
    # Simulate processing delay
    import time
    time.sleep(2)
    
    # Simulate random payment failures (3% chance)
    import random
    if random.random() < 0.03:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                    error="Payment declined. Please check your card details and try again.")
    
    # Prepare order data with shipping and billing information
    order_data = {
        'session_id': session_id,
        'items': [
            {
                'album_id': item[2],
                'album_name': item[3],
                'artist': item[4],
                'price': item[5],
                'quantity': item[6]
            }
            for item in cart_items
        ],
        'total': sum(item[6] * item[5] for item in cart_items),
        'shipping_info': {
            'first_name': request.form.get('shipping_first_name', '').strip(),
            'last_name': request.form.get('shipping_last_name', '').strip(),
            'address': request.form.get('shipping_address', '').strip(),
            'city': request.form.get('shipping_city', '').strip(),
            'state': request.form.get('shipping_state', '').strip(),
            'zip_code': request.form.get('shipping_zip', '').strip(),
            'country': request.form.get('shipping_country', '').strip(),
            'phone': request.form.get('phone', '').strip()
        },
        'billing_info': {
            'first_name': request.form.get('billing_first_name', '').strip(),
            'last_name': request.form.get('billing_last_name', '').strip(),
            'address': request.form.get('billing_address', '').strip(),
            'city': request.form.get('billing_city', '').strip(),
            'state': request.form.get('billing_state', '').strip(),
            'zip_code': request.form.get('billing_zip', '').strip(),
            'country': request.form.get('billing_country', '').strip()
        },
        'payment_info': {
            'cardholder_name': cardholder_name,
            'card_last_four': card_number[-4:],
            'email': email
        }
    }
    
    try:
        response = requests.post(f"{ORDER_SERVICE_URL}/api/orders", json=order_data)
        if response.status_code == 201:
            # Clear cart after successful order
            with sqlite3.connect(CART_DB_PATH) as conn:
                c = conn.cursor()
                c.execute('DELETE FROM cart_items WHERE session_id = ?', (session_id,))
                conn.commit()
            
            # Store order details in session for success page
            session['order_details'] = order_data
            
            return redirect(url_for('order_success'))
        else:
            total = sum(item[6] * item[5] for item in cart_items)
            return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                        error="Order processing failed. Please try again.")
    except requests.RequestException:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, 
                                    error="Order service unavailable. Please try again later.")

@app.route('/order_success')
def order_success():
    # Get session_id from query parameter or session
    session_id = request.args.get('session_id')
    if session_id:
        # Use the provided session_id and store it in our session
        session['session_id'] = session_id
    
    # We don't need order_details for the simplified success page
    return render_template_string(SUCCESS_HTML)

# Cart HTML Template
CART_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopping Cart - Metal Music Store</title>
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
            background: #1a1a1a;
            color: white;
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.3);
            margin-bottom: 40px;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            color: #ffffff;
            letter-spacing: -0.5px;
        }

        .cart-card {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e1e5e9;
        }

        .cart-item {
            display: grid;
            grid-template-columns: 80px 2fr 1fr 1fr auto;
            gap: 20px;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid #e1e5e9;
            transition: all 0.3s ease;
        }

        .cart-item:last-child {
            border-bottom: none;
        }

        .item-cover {
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 8px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }

        .item-info h3 {
            color: #1a1a1a;
            margin-bottom: 5px;
            font-weight: 700;
        }

        .item-info p {
            color: #666;
            font-size: 0.9rem;
            font-weight: 500;
        }

        .item-price {
            font-weight: 800;
            color: #667eea;
        }

        .quantity-controls {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .quantity-controls input {
            width: 60px;
            padding: 10px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            text-align: center;
            background: white;
            color: #1a1a1a;
            font-weight: 500;
            transition: all 0.3s ease;
        }

        .quantity-controls input:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .btn-danger {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        }

        .btn-danger:hover {
            box-shadow: 0 8px 25px rgba(231, 76, 60, 0.3);
        }

        .cart-total {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-top: 30px;
            text-align: right;
            border-left: 4px solid #667eea;
            border: 1px solid #e1e5e9;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .cart-total h3 {
            color: #1a1a1a;
            margin-bottom: 15px;
            font-weight: 700;
        }

        .total-amount {
            font-size: 2.5rem;
            font-weight: 800;
            color: #667eea;
        }

        .cart-actions {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
        }

        .empty-cart {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }

        .empty-cart p {
            font-size: 1.1rem;
            margin-bottom: 20px;
            font-weight: 500;
        }

        @media (max-width: 768px) {
            .cart-item {
                grid-template-columns: 1fr;
                gap: 10px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .container {
                padding: 0 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-content">
                <h1>🛒 Shopping Cart</h1>
            </div>
            <p>Review your brutal metal collection</p>
        </div>

        <div class="cart-card">
            {% if cart_items %}
                {% for item in cart_items %}
                <div class="cart-item">
                    <div>
                        {% if item[7] %}
                        <img src="{{item[7]}}" alt="Album cover" class="item-cover">
                        {% else %}
                        <div class="item-cover" style="display: flex; align-items: center; justify-content: center; color: white; font-size: 0.8rem;">No Cover</div>
                        {% endif %}
                    </div>
                    
                    <div class="item-info">
                        <h3>{{item[3]}}</h3>
                        <p>by {{item[4]}}</p>
                    </div>
                    
                    <div class="item-price">${{"%.2f"|format(item[5])}}</div>
                    
                    <div class="quantity-controls">
                        <form action="/update_quantity" method="post" style="display: flex; align-items: center; gap: 10px;">
                            <input type="hidden" name="item_id" value="{{item[0]}}">
                            <input type="number" name="quantity" value="{{item[6]}}" min="1" style="width: 60px;">
                            <button type="submit" class="btn">Update</button>
                        </form>
                    </div>
                    
                    <div>
                        <form action="/remove_item" method="post">
                            <input type="hidden" name="item_id" value="{{item[0]}}">
                            <button type="submit" class="btn btn-danger">Remove</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
                
                <div class="cart-total">
                    <h3>Total</h3>
                    <div class="total-amount">${{"%.2f"|format(total)}}</div>
                </div>
                
                <div class="cart-actions">
                    <a href="/" class="btn btn-secondary" style="text-decoration: none;">Continue Shopping</a>
                    <a href="/checkout" class="btn" style="text-decoration: none;">Proceed to Checkout</a>
                </div>
            {% else %}
                <div class="empty-cart">
                    <p>Your cart is empty</p>
                    <p>Add some albums to get started!</p>
                    <a href="/" class="btn" style="text-decoration: none;">Go Shopping</a>
                </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

# Enhanced Checkout HTML Template with complete checkout experience
CHECKOUT_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Checkout - Metal Music Store</title>
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
            background: #1a1a1a;
            color: white;
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.3);
            margin-bottom: 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            color: #ffffff;
            letter-spacing: -0.5px;
        }

        .checkout-card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e1e5e9;
        }

        .order-summary {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
            border: 1px solid #e1e5e9;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .order-summary h3 {
            color: #1a1a1a;
            margin-bottom: 15px;
            font-size: 1.3rem;
            font-weight: 700;
        }

        .order-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 10px 0;
            border-bottom: 1px solid #e1e5e9;
            color: #1a1a1a;
        }

        .order-item:last-child {
            border-bottom: none;
        }

        .order-total {
            border-top: 2px solid #e1e5e9;
            padding-top: 15px;
            margin-top: 15px;
            font-size: 1.2rem;
            font-weight: bold;
            color: #667eea;
            display: flex;
            justify-content: space-between;
        }

        .form-section {
            margin-bottom: 40px;
        }

        .form-section h3 {
            color: #1a1a1a;
            margin-bottom: 20px;
            font-size: 1.3rem;
            border-bottom: 2px solid #e1e5e9;
            padding-bottom: 10px;
            font-weight: 700;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group.full-width {
            grid-column: 1 / -1;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #1a1a1a;
            font-size: 0.9rem;
        }

        .form-group input, .form-group select {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
            background: white;
            color: #1a1a1a;
        }

        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .card-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 15px;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
        }

        .checkbox-group input[type="checkbox"] {
            width: auto;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            width: 100%;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
        }

        .back-link {
            text-align: center;
            margin-top: 20px;
        }

        .back-link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }

        .back-link a:hover {
            text-decoration: underline;
        }

        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
            .form-row, .card-row {
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
            <h1>💳 Complete Checkout</h1>
            <p>Enter your shipping and payment information</p>
        </div>

        <div class="checkout-card">
            <div class="order-summary">
                <h3>📋 Order Summary</h3>
                {% for item in cart_items %}
                <div class="order-item">
                    <span>{{item[6]}}x {{item[3]}} by {{item[4]}}</span>
                    <span>${{"%.2f"|format(item[5] * item[6])}}</span>
                </div>
                {% endfor %}
                <div class="order-total">
                    <span>Total:</span>
                    <span>${{"%.2f"|format(total)}}</span>
                </div>
            </div>

            {% if error %}
            <div class="error-message">
                {{ error }}
            </div>
            {% endif %}

            <form action="process_payment" method="post" id="checkout-form">
                <!-- Contact Information -->
                <div class="form-section">
                    <h3>📧 Contact Information</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="email">Email Address *</label>
                            <input type="email" id="email" name="email" placeholder="your@email.com" required>
                        </div>
                        <div class="form-group">
                            <label for="phone">Phone Number *</label>
                            <input type="tel" id="phone" name="phone" placeholder="(555) 123-4567" required>
                        </div>
                    </div>
                </div>

                <!-- Shipping Address -->
                <div class="form-section">
                    <h3>🚚 Shipping Address</h3>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="shipping_first_name">First Name *</label>
                            <input type="text" id="shipping_first_name" name="shipping_first_name" required>
                        </div>
                        <div class="form-group">
                            <label for="shipping_last_name">Last Name *</label>
                            <input type="text" id="shipping_last_name" name="shipping_last_name" required>
                        </div>
                    </div>
                    <div class="form-group full-width">
                        <label for="shipping_address">Address *</label>
                        <input type="text" id="shipping_address" name="shipping_address" placeholder="123 Main St" required>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="shipping_city">City *</label>
                            <input type="text" id="shipping_city" name="shipping_city" required>
                        </div>
                        <div class="form-group">
                            <label for="shipping_state">State/Province *</label>
                            <input type="text" id="shipping_state" name="shipping_state" required>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="shipping_zip">ZIP/Postal Code *</label>
                            <input type="text" id="shipping_zip" name="shipping_zip" required>
                        </div>
                        <div class="form-group">
                            <label for="shipping_country">Country *</label>
                            <select id="shipping_country" name="shipping_country" required>
                                <option value="">Select Country</option>
                                <option value="US">United States</option>
                                <option value="CA">Canada</option>
                                <option value="UK">United Kingdom</option>
                                <option value="AU">Australia</option>
                                <option value="DE">Germany</option>
                                <option value="FR">France</option>
                                <option value="JP">Japan</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Billing Address -->
                <div class="form-section">
                    <h3>💳 Billing Address</h3>
                    <div class="checkbox-group">
                        <input type="checkbox" id="same_as_shipping" name="same_as_shipping">
                        <label for="same_as_shipping">Same as shipping address</label>
                    </div>
                    <div id="billing-fields">
                        <div class="form-row">
                            <div class="form-group">
                                <label for="billing_first_name">First Name *</label>
                                <input type="text" id="billing_first_name" name="billing_first_name" required>
                            </div>
                            <div class="form-group">
                                <label for="billing_last_name">Last Name *</label>
                                <input type="text" id="billing_last_name" name="billing_last_name" required>
                            </div>
                        </div>
                        <div class="form-group full-width">
                            <label for="billing_address">Address *</label>
                            <input type="text" id="billing_address" name="billing_address" required>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="billing_city">City *</label>
                                <input type="text" id="billing_city" name="billing_city" required>
                            </div>
                            <div class="form-group">
                                <label for="billing_state">State/Province *</label>
                                <input type="text" id="billing_state" name="billing_state" required>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="billing_zip">ZIP/Postal Code *</label>
                                <input type="text" id="billing_zip" name="billing_zip" required>
                            </div>
                            <div class="form-group">
                                <label for="billing_country">Country *</label>
                                <select id="billing_country" name="billing_country" required>
                                    <option value="">Select Country</option>
                                    <option value="US">United States</option>
                                    <option value="CA">Canada</option>
                                    <option value="UK">United Kingdom</option>
                                    <option value="AU">Australia</option>
                                    <option value="DE">Germany</option>
                                    <option value="FR">France</option>
                                    <option value="JP">Japan</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Payment Information -->
                <div class="form-section">
                    <h3>💳 Payment Information</h3>
                    <div class="form-group">
                        <label for="cardholder_name">Cardholder Name *</label>
                        <input type="text" id="cardholder_name" name="cardholder_name" placeholder="As it appears on card" required>
                    </div>
                    <div class="form-group">
                        <label for="card_number">Card Number *</label>
                        <input type="text" id="card_number" name="card_number" placeholder="1234 5678 9012 3456" maxlength="19" required>
                    </div>
                    <div class="card-row">
                        <div class="form-group">
                            <label for="expiry">Expiry Date *</label>
                            <input type="text" id="expiry" name="expiry" placeholder="MM/YY" maxlength="5" required>
                        </div>
                        <div class="form-group">
                            <label for="cvv">CVV *</label>
                            <input type="text" id="cvv" name="cvv" placeholder="123" maxlength="4" required>
                        </div>
                        <div class="form-group">
                            <label>&nbsp;</label>
                            <button type="submit" class="btn" id="submit-btn">
                                <span id="btn-text">Pay ${{"%.2f"|format(total)}}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </form>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Processing your payment...</p>
            </div>
        </div>

        <div class="back-link">
            <a href="/">← Back to Cart</a>
        </div>
    </div>

    <script>
        // Format card number with spaces
        document.getElementById('card_number').addEventListener('input', function(e) {
            let value = e.target.value.replace(/\\s/g, '').replace(/[^0-9]/gi, '');
            let formattedValue = value.replace(/(.{4})/g, '$1 ').trim();
            e.target.value = formattedValue;
        });

        // Format expiry date
        document.getElementById('expiry').addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^0-9]/g, '');
            if (value.length >= 2) {
                value = value.substring(0, 2) + '/' + value.substring(2, 4);
            }
            e.target.value = value;
        });

        // Only allow numbers for CVV
        document.getElementById('cvv').addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });

        // Same as shipping address functionality
        document.getElementById('same_as_shipping').addEventListener('change', function(e) {
            const billingFields = document.getElementById('billing-fields');
            if (e.target.checked) {
                billingFields.style.display = 'none';
                // Copy shipping values to billing
                document.getElementById('billing_first_name').value = document.getElementById('shipping_first_name').value;
                document.getElementById('billing_last_name').value = document.getElementById('shipping_last_name').value;
                document.getElementById('billing_address').value = document.getElementById('shipping_address').value;
                document.getElementById('billing_city').value = document.getElementById('shipping_city').value;
                document.getElementById('billing_state').value = document.getElementById('shipping_state').value;
                document.getElementById('billing_zip').value = document.getElementById('shipping_zip').value;
                document.getElementById('billing_country').value = document.getElementById('shipping_country').value;
            } else {
                billingFields.style.display = 'block';
            }
        });

        // Form submission with loading state
        document.getElementById('checkout-form').addEventListener('submit', function(e) {
            const submitBtn = document.getElementById('submit-btn');
            const btnText = document.getElementById('btn-text');
            const loading = document.getElementById('loading');
            
            submitBtn.disabled = true;
            btnText.textContent = 'Processing...';
            loading.style.display = 'block';
        });

        // Auto-fill with sample data for testing
        function fillSampleData() {
            const sampleData = {
                'email': 'test@example.com',
                'phone': '(555) 123-4567',
                'shipping_first_name': 'John',
                'shipping_last_name': 'Doe',
                'shipping_address': '123 Main Street',
                'shipping_city': 'New York',
                'shipping_state': 'NY',
                'shipping_zip': '10001',
                'shipping_country': 'US',
                'billing_first_name': 'John',
                'billing_last_name': 'Doe',
                'billing_address': '123 Main Street',
                'billing_city': 'New York',
                'billing_state': 'NY',
                'billing_zip': '10001',
                'billing_country': 'US',
                'cardholder_name': 'John Doe',
                'card_number': '4111 1111 1111 1111',
                'expiry': '12/25',
                'cvv': '123'
            };
            
            for (const [key, value] of Object.entries(sampleData)) {
                const element = document.getElementById(key);
                if (element) {
                    element.value = value;
                }
            }
        }

        // Add sample data button for testing (remove in production)
        const sampleBtn = document.createElement('button');
        sampleBtn.textContent = 'Fill Sample Data (Testing)';
        sampleBtn.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #28a745; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer; z-index: 1000;';
        sampleBtn.onclick = fillSampleData;
        document.body.appendChild(sampleBtn);
    </script>
</body>
</html>
'''

SUCCESS_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Successful - Metal Music Store</title>
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
            background: #1a1a1a;
            color: white;
            padding: 20px 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.3);
            margin-bottom: 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 10px;
            color: #ffffff;
            letter-spacing: -0.5px;
        }

        .success-card {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid #e1e5e9;
            text-align: center;
        }

        .success-icon {
            font-size: 4rem;
            margin-bottom: 20px;
            color: #667eea;
        }

        .success-title {
            color: #1a1a1a;
            font-size: 2rem;
            margin-bottom: 15px;
            font-weight: 700;
        }

        .success-message {
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 30px;
            line-height: 1.6;
        }

        .order-summary {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
            text-align: left;
            border: 1px solid #e1e5e9;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }

        .order-summary h4 {
            color: #28a745;
            margin-bottom: 15px;
            font-size: 1.3rem;
            text-align: center;
            font-weight: 700;
        }

        .order-info {
            color: #1a1a1a;
            font-size: 1rem;
            line-height: 1.6;
            text-align: center;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin: 10px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .btn-secondary {
            background: #f8f9fa;
            color: #666;
            border: 1px solid #e1e5e9;
        }

        .btn-secondary:hover {
            background: #e9ecef;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤘 Purchase Complete!</h1>
            <p>Your brutal metal albums are on the way!</p>
        </div>

        <div class="success-card">
            <div class="success-icon">🎉</div>
            <h1 class="success-title">Transaction Successful!</h1>
            <p class="success-message">
                🤘 Your brutal metal albums have been purchased successfully! 
                <br>Your collection is on its way to your lair!
                <br>You'll receive a confirmation email with tracking information.
                <br><strong>Rock on! 🤘</strong>
            </p>
            
            <div class="order-summary">
                <h4>📋 Order Confirmation</h4>
                <div class="order-info">
                    <p>✅ Your order has been processed successfully</p>
                    <p>✅ Payment has been confirmed</p>
                    <p>✅ Your albums will be shipped within 2-3 business days</p>
                    <p>✅ You'll receive tracking information via email</p>
                    <p style="margin-top: 20px; font-weight: bold; color: #667eea;">
                        Thank you for supporting brutal metal! 🤘
                    </p>
                </div>
            </div>

            <div style="margin-top: 30px;">
                <a href="/" class="btn">Continue Shopping</a>
                <a href="/" class="btn btn-secondary">Back to Store</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True) 