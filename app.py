from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)
DB_PATH = os.environ.get('DB_PATH', 'store.db')

# --- Database Setup ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )''')
        conn.commit()

init_db()

# --- Templates ---
INDEX_HTML = '''
<!doctype html>
<title>Store</title>
<h1>Products</h1>
<ul>
{% for p in products %}
  <li>{{p[1]}} - ${{p[2]}} <form action="/order" method="post" style="display:inline"><input type="hidden" name="product_id" value="{{p[0]}}"><input type="number" name="quantity" value="1" min="1" style="width:40px"><button type="submit">Order</button></form></li>
{% endfor %}
</ul>
<h2>Add Product</h2>
<form action="/add" method="post">
  Name: <input name="name"> Price: <input name="price" type="number" step="0.01"> <button type="submit">Add</button>
</form>
<h2>Orders</h2>
<ul>
{% for o in orders %}
  <li>{{o[3]}} x {{o[1]}} (${{o[2]}} each)</li>
{% endfor %}
</ul>
'''

# --- Routes ---
@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        products = c.execute('SELECT * FROM products').fetchall()
        orders = c.execute('''SELECT orders.id, products.name, products.price, orders.quantity FROM orders JOIN products ON orders.product_id = products.id''').fetchall()
    return render_template_string(INDEX_HTML, products=products, orders=orders)

@app.route('/add', methods=['POST'])
def add_product():
    name = request.form['name']
    price = float(request.form['price'])
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO products (name, price) VALUES (?, ?)', (name, price))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/order', methods=['POST'])
def order():
    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO orders (product_id, quantity) VALUES (?, ?)', (product_id, quantity))
        conn.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 