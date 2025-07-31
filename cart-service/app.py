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
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        cart_items = c.execute('''
            SELECT * FROM cart_items 
            WHERE session_id = ? 
            ORDER BY created_at DESC
        ''', (session['session_id'],)).fetchall()
    
    total = sum(item[6] * item[5] for item in cart_items)  # quantity * price
    
    return render_template_string(CART_HTML, cart_items=cart_items, total=total)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    
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
        ''', (session['session_id'], album_id)).fetchone()
        
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
            ''', (session['session_id'], album_id, album_name, artist, price, quantity, cover_url))
        
        conn.commit()
    
    return redirect(url_for('cart'))

@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    item_id = int(request.form['item_id'])
    quantity = int(request.form['quantity'])
    
    if quantity <= 0:
        # Remove item
        with sqlite3.connect(CART_DB_PATH) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM cart_items WHERE id = ? AND session_id = ?', 
                     (item_id, session['session_id']))
            conn.commit()
    else:
        # Update quantity
        with sqlite3.connect(CART_DB_PATH) as conn:
            c = conn.cursor()
            c.execute('UPDATE cart_items SET quantity = ? WHERE id = ? AND session_id = ?', 
                     (quantity, item_id, session['session_id']))
            conn.commit()
    
    return redirect(url_for('cart'))

@app.route('/remove_item', methods=['POST'])
def remove_item():
    item_id = int(request.form['item_id'])
    
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM cart_items WHERE id = ? AND session_id = ?', 
                 (item_id, session['session_id']))
        conn.commit()
    
    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    if 'session_id' not in session:
        return redirect(url_for('cart'))
    
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        cart_items = c.execute('''
            SELECT * FROM cart_items 
            WHERE session_id = ? 
            ORDER BY created_at DESC
        ''', (session['session_id'],)).fetchall()
    
    if not cart_items:
        return redirect(url_for('cart'))
    
    total = sum(item[6] * item[5] for item in cart_items)
    
    return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'session_id' not in session:
        return redirect(url_for('cart'))
    
    # Get cart items
    with sqlite3.connect(CART_DB_PATH) as conn:
        c = conn.cursor()
        cart_items = c.execute('''
            SELECT * FROM cart_items 
            WHERE session_id = ?
        ''', (session['session_id'],)).fetchall()
    
    if not cart_items:
        return redirect(url_for('cart'))
    
    # Validate payment details
    card_number = request.form.get('card_number', '').replace(' ', '')
    expiry = request.form.get('expiry', '')
    cvv = request.form.get('cvv', '')
    
    if not card_number or not expiry or not cvv:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, error="Please fill in all fields")
    
    if len(card_number) < 13 or len(card_number) > 19:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, error="Invalid card number")
    
    if len(cvv) < 3 or len(cvv) > 4:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, error="Invalid CVV")
    
    # Simulate processing delay
    import time
    time.sleep(1)
    
    # Simulate random payment failures (5% chance)
    import random
    if random.random() < 0.05:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, error="Payment declined. Please try again.")
    
    # Send order to order service
    order_data = {
        'session_id': session['session_id'],
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
        'total': sum(item[6] * item[5] for item in cart_items)
    }
    
    try:
        response = requests.post(f"{ORDER_SERVICE_URL}/api/orders", json=order_data)
        if response.status_code == 201:
            # Clear cart after successful order
            with sqlite3.connect(CART_DB_PATH) as conn:
                c = conn.cursor()
                c.execute('DELETE FROM cart_items WHERE session_id = ?', (session['session_id'],))
                conn.commit()
            
            return redirect(url_for('order_success'))
        else:
            total = sum(item[6] * item[5] for item in cart_items)
            return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, error="Order processing failed")
    except requests.RequestException:
        total = sum(item[6] * item[5] for item in cart_items)
        return render_template_string(CHECKOUT_HTML, cart_items=cart_items, total=total, error="Order service unavailable")

@app.route('/order_success')
def order_success():
    return render_template_string(SUCCESS_HTML)

# Cart HTML Template
CART_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopping Cart - Music Store</title>
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
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 300;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .cart-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }

        .cart-item {
            display: grid;
            grid-template-columns: 80px 2fr 1fr 1fr auto;
            gap: 20px;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
        }

        .cart-item:last-child {
            border-bottom: none;
        }

        .item-cover {
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 8px;
            background: linear-gradient(45deg, #667eea, #764ba2);
        }

        .item-info h3 {
            color: #333;
            margin-bottom: 5px;
        }

        .item-info p {
            color: #666;
            font-size: 0.9rem;
        }

        .item-price {
            font-weight: bold;
            color: #667eea;
        }

        .quantity-controls {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .quantity-controls input {
            width: 60px;
            padding: 8px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            text-align: center;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: transform 0.2s;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .btn-danger {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }

        .cart-total {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-top: 30px;
            text-align: right;
            border-left: 4px solid #667eea;
        }

        .cart-total h3 {
            color: #667eea;
            margin-bottom: 15px;
        }

        .total-amount {
            font-size: 2rem;
            font-weight: bold;
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
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛒 Shopping Cart</h1>
            <p>Review your items</p>
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

# Checkout and Success templates (same as before but adapted for cart items)
CHECKOUT_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Checkout - Music Store</title>
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
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 300;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .checkout-card {
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }

        .order-summary {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
        }

        .order-summary h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }

        .order-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 10px 0;
            border-bottom: 1px solid #e9ecef;
        }

        .order-item:last-child {
            border-bottom: none;
        }

        .order-total {
            border-top: 2px solid #e9ecef;
            padding-top: 15px;
            margin-top: 15px;
            font-size: 1.2rem;
            font-weight: bold;
            color: #667eea;
            display: flex;
            justify-content: space-between;
        }

        .payment-form {
            margin-top: 30px;
        }

        .payment-form h3 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.3rem;
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

        .card-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 15px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 500;
            transition: transform 0.2s;
            width: 100%;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            border: 1px solid #f5c6cb;
        }

        .back-link {
            text-align: center;
            margin-top: 20px;
        }

        .back-link a {
            color: white;
            text-decoration: none;
            font-weight: 500;
        }

        .back-link a:hover {
            text-decoration: underline;
        }

        @media (max-width: 768px) {
            .card-row {
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
            <h1>💳 Checkout</h1>
            <p>Complete your purchase</p>
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

            <form action="/process_payment" method="post" class="payment-form">
                <h3>💳 Payment Information</h3>
                
                <div class="form-group">
                    <label for="card_number">Card Number</label>
                    <input type="text" id="card_number" name="card_number" placeholder="1234 5678 9012 3456" maxlength="19" required>
                </div>

                <div class="card-row">
                    <div class="form-group">
                        <label for="expiry">Expiry Date</label>
                        <input type="text" id="expiry" name="expiry" placeholder="MM/YY" maxlength="5" required>
                    </div>
                    <div class="form-group">
                        <label for="cvv">CVV</label>
                        <input type="text" id="cvv" name="cvv" placeholder="123" maxlength="4" required>
                    </div>
                    <div class="form-group">
                        <label>&nbsp;</label>
                        <button type="submit" class="btn">Pay ${{"%.2f"|format(total)}}</button>
                    </div>
                </div>
            </form>
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
    <title>Order Successful - Music Store</title>
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
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .success-card {
            background: white;
            border-radius: 15px;
            padding: 50px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            text-align: center;
            max-width: 500px;
            width: 90%;
        }

        .success-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }

        .success-title {
            color: #28a745;
            font-size: 2rem;
            margin-bottom: 15px;
            font-weight: 600;
        }

        .success-message {
            color: #666;
            font-size: 1.1rem;
            margin-bottom: 30px;
            line-height: 1.6;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 500;
            transition: transform 0.2s;
            text-decoration: none;
            display: inline-block;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .order-details {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }

        .order-details h4 {
            color: #28a745;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="success-card">
        <div class="success-icon">✅</div>
        <h1 class="success-title">Payment Successful!</h1>
        <p class="success-message">
            Thank you for your purchase! Your order has been processed successfully.
            You will receive a confirmation email shortly.
        </p>
        
        <div class="order-details">
            <h4>Order Details</h4>
            <p>Your order has been added to our system and will be processed soon.</p>
        </div>

        <a href="/" class="btn">Continue Shopping</a>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True) 