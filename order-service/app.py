from flask import Flask, render_template_string, request, jsonify
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)

# Configuration
ORDER_DB_PATH = os.environ.get('ORDER_DB_PATH', 'orders.db')

def init_order_db():
    with sqlite3.connect(ORDER_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            order_number TEXT UNIQUE NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            album_id INTEGER NOT NULL,
            album_name TEXT NOT NULL,
            artist TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )''')
        conn.commit()

init_order_db()

def generate_order_number():
    """Generate a unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    import random
    random_suffix = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    return f"ORD-{timestamp}-{random_suffix}"

@app.route('/api/orders', methods=['POST'])
def create_order():
    """API endpoint to create a new order"""
    try:
        data = request.get_json()
        
        if not data or 'items' not in data or 'total' not in data:
            return jsonify({'error': 'Invalid order data'}), 400
        
        session_id = data.get('session_id')
        items = data['items']
        total = data['total']
        
        if not items:
            return jsonify({'error': 'No items in order'}), 400
        
        # Create order
        order_number = generate_order_number()
        
        with sqlite3.connect(ORDER_DB_PATH) as conn:
            c = conn.cursor()
            
            # Insert order
            c.execute('''
                INSERT INTO orders (session_id, order_number, total_amount, status)
                VALUES (?, ?, ?, ?)
            ''', (session_id, order_number, total, 'confirmed'))
            
            order_id = c.lastrowid
            
            # Insert order items
            for item in items:
                c.execute('''
                    INSERT INTO order_items (order_id, album_id, album_name, artist, price, quantity)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, item['album_id'], item['album_name'], item['artist'], item['price'], item['quantity']))
            
            conn.commit()
        
        return jsonify({
            'order_id': order_id,
            'order_number': order_number,
            'status': 'confirmed',
            'total': total
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """API endpoint to get all orders"""
    try:
        with sqlite3.connect(ORDER_DB_PATH) as conn:
            c = conn.cursor()
            orders = c.execute('''
                SELECT o.id, o.order_number, o.total_amount, o.status, o.created_at,
                       COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                GROUP BY o.id
                ORDER BY o.created_at DESC
            ''').fetchall()
        
        return jsonify([{
            'id': order[0],
            'order_number': order[1],
            'total_amount': order[2],
            'status': order[3],
            'created_at': order[4],
            'item_count': order[5]
        } for order in orders]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """API endpoint to get a specific order with items"""
    try:
        with sqlite3.connect(ORDER_DB_PATH) as conn:
            c = conn.cursor()
            
            # Get order details
            order = c.execute('''
                SELECT id, order_number, total_amount, status, created_at
                FROM orders WHERE id = ?
            ''', (order_id,)).fetchone()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Get order items
            items = c.execute('''
                SELECT album_id, album_name, artist, price, quantity
                FROM order_items WHERE order_id = ?
            ''', (order_id,)).fetchall()
        
        return jsonify({
            'id': order[0],
            'order_number': order[1],
            'total_amount': order[2],
            'status': order[3],
            'created_at': order[4],
            'items': [{
                'album_id': item[0],
                'album_name': item[1],
                'artist': item[2],
                'price': item[3],
                'quantity': item[4]
            } for item in items]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """API endpoint to update order status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        with sqlite3.connect(ORDER_DB_PATH) as conn:
            c = conn.cursor()
            c.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
            
            if c.rowcount == 0:
                return jsonify({'error': 'Order not found'}), 404
            
            conn.commit()
        
        return jsonify({'message': 'Order status updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def orders_dashboard():
    """Dashboard to view all orders"""
    with sqlite3.connect(ORDER_DB_PATH) as conn:
        c = conn.cursor()
        orders = c.execute('''
            SELECT o.id, o.order_number, o.total_amount, o.status, o.created_at,
                   COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id
            ORDER BY o.created_at DESC
        ''').fetchall()
    
    return render_template_string(ORDERS_DASHBOARD_HTML, orders=orders)

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    """Detailed view of a specific order"""
    with sqlite3.connect(ORDER_DB_PATH) as conn:
        c = conn.cursor()
        
        # Get order details
        order = c.execute('''
            SELECT id, order_number, total_amount, status, created_at
            FROM orders WHERE id = ?
        ''', (order_id,)).fetchone()
        
        if not order:
            return "Order not found", 404
        
        # Get order items
        items = c.execute('''
            SELECT album_id, album_name, artist, price, quantity
            FROM order_items WHERE order_id = ?
        ''', (order_id,)).fetchall()
    
    return render_template_string(ORDER_DETAIL_HTML, order=order, items=items)

# HTML Templates
ORDERS_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orders Dashboard - Metal Music Store</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Orbitron', 'Arial Black', sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 25%, #2d2d2d 50%, #1a1a1a 75%, #0a0a0a 100%);
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
                radial-gradient(circle at 20% 20%, rgba(204, 0, 0, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(204, 0, 0, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 40% 60%, rgba(204, 0, 0, 0.03) 0%, transparent 50%);
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
            font-size: 3rem;
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

        .dashboard-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%);
            border-radius: 8px;
            padding: 30px;
            box-shadow: 
                0 10px 30px rgba(0,0,0,0.8),
                inset 0 1px 0 rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border: 2px solid #333;
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
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid #333;
            box-shadow: 
                0 5px 15px rgba(0,0,0,0.8),
                inset 0 1px 0 rgba(255,255,255,0.1);
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: 900;
            margin-bottom: 5px;
            color: #cc0000;
            text-shadow: 0 0 8px rgba(204, 0, 0, 0.5);
        }

        .stat-label {
            font-size: 1rem;
            opacity: 0.9;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .orders-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .orders-table th,
        .orders-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #333;
            color: #ffffff;
        }

        .orders-table th {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            font-weight: 700;
            color: #cc0000;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-shadow: 0 0 5px rgba(204, 0, 0, 0.3);
        }

        .orders-table tr:hover {
            background: linear-gradient(135deg, #2d2d2d 0%, #404040 100%);
        }

        .status-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }

        .status-pending {
            background: #fff3cd;
            color: #856404;
        }

        .status-confirmed {
            background: #d1ecf1;
            color: #0c5460;
        }

        .status-shipped {
            background: #d4edda;
            color: #155724;
        }

        .status-delivered {
            background: #c3e6cb;
            color: #155724;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            text-decoration: none;
            display: inline-block;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }

        @media (max-width: 768px) {
            .orders-table {
                font-size: 0.9rem;
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
            <h1>📦 Orders Dashboard</h1>
            <p>Track your brutal metal orders</p>
            <p>Manage all customer orders</p>
        </div>

        <div class="dashboard-card">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{{orders|length}}</div>
                    <div class="stat-label">Total Orders</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${{"%.2f"|format(orders|sum(attribute=2))}}</div>
                    <div class="stat-label">Total Revenue</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{orders|selectattr(3, 'equalto', 'pending')|list|length}}</div>
                    <div class="stat-label">Pending Orders</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{orders|selectattr(3, 'equalto', 'confirmed')|list|length}}</div>
                    <div class="stat-label">Confirmed Orders</div>
                </div>
            </div>

            {% if orders %}
            <table class="orders-table">
                <thead>
                    <tr>
                        <th>Order #</th>
                        <th>Date</th>
                        <th>Items</th>
                        <th>Total</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for order in orders %}
                    <tr>
                        <td><strong>{{order[1]}}</strong></td>
                        <td>{{order[4][:10]}}</td>
                        <td>{{order[5]}} items</td>
                        <td>${{"%.2f"|format(order[2])}}</td>
                        <td>
                            <span class="status-badge status-{{order[3]}}">{{order[3]|title}}</span>
                        </td>
                        <td>
                            <a href="/order/{{order[0]}}" class="btn">View Details</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty-state">
                <p>No orders yet.</p>
                <p>Orders will appear here once customers make purchases.</p>
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

ORDER_DETAIL_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Details - Music Store</title>
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

        .order-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }

        .order-header {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
        }

        .order-header h3 {
            color: #667eea;
            margin-bottom: 15px;
        }

        .order-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .info-item {
            margin-bottom: 10px;
        }

        .info-label {
            font-weight: 600;
            color: #555;
        }

        .info-value {
            color: #333;
        }

        .items-section {
            margin-top: 30px;
        }

        .items-section h3 {
            color: #667eea;
            margin-bottom: 20px;
        }

        .item-list {
            list-style: none;
        }

        .item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }

        .item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }

        .item-name {
            font-weight: 600;
            color: #333;
        }

        .item-price {
            color: #667eea;
            font-weight: bold;
        }

        .item-details {
            color: #666;
            font-size: 0.9rem;
        }

        .order-total {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-top: 30px;
            text-align: center;
        }

        .total-amount {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
            text-decoration: none;
            display: inline-block;
            margin-top: 20px;
        }

        .btn:hover {
            transform: translateY(-2px);
        }

        @media (max-width: 768px) {
            .order-info {
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
            <h1>📋 Order Details</h1>
            <p>Order #{{order[1]}}</p>
        </div>

        <div class="order-card">
            <div class="order-header">
                <h3>Order Information</h3>
                <div class="order-info">
                    <div class="info-item">
                        <div class="info-label">Order Number:</div>
                        <div class="info-value">{{order[1]}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Date:</div>
                        <div class="info-value">{{order[4]}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Status:</div>
                        <div class="info-value">{{order[3]|title}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Items:</div>
                        <div class="info-value">{{items|length}} items</div>
                    </div>
                </div>
            </div>

            <div class="items-section">
                <h3>Order Items</h3>
                <ul class="item-list">
                    {% for item in items %}
                    <li class="item">
                        <div class="item-header">
                            <div class="item-name">{{item[1]}}</div>
                            <div class="item-price">${{"%.2f"|format(item[3] * item[4])}}</div>
                        </div>
                        <div class="item-details">
                            by {{item[2]}} • {{item[4]}}x ${{"%.2f"|format(item[3])}} each
                        </div>
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <div class="order-total">
                <div class="total-amount">${{"%.2f"|format(order[2])}}</div>
                <div>Total Amount</div>
            </div>

            <div style="text-align: center;">
                <a href="/" class="btn">Back to Orders</a>
            </div>
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 