# Music Store - Microservices Architecture

A modern music store application built with a microservices architecture, featuring separate services for store management, shopping cart, and order processing.

## 🏗️ Architecture Overview

The application is split into three independent microservices:

### 1. **Store Service** (Port 5000)
- **Purpose**: Main store interface and album management
- **Features**:
  - Browse albums
  - Add new albums (admin)
  - View store statistics
  - Album catalog management
- **Database**: SQLite (`music_store.db`)

### 2. **Cart Service** (Port 5002)
- **Purpose**: Shopping cart management and checkout
- **Features**:
  - Add items to cart
  - Update quantities
  - Remove items
  - Checkout process
  - Credit card payment simulation
- **Database**: SQLite (`cart.db`)

### 3. **Order Service** (Port 5001)
- **Purpose**: Order processing and management
- **Features**:
  - Create orders
  - Order tracking
  - Order dashboard
  - Order history
- **Database**: SQLite (`orders.db`)

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the project**:
   ```bash
   cd exmaple-music-store-1
   ```

2. **Start all services**:
   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - **Store**: http://localhost:5000
   - **Cart**: http://localhost:5002
   - **Orders Dashboard**: http://localhost:5001

### Manual Setup

1. **Store Service**:
   ```bash
   cd exmaple-music-store-1
   pip install -r requirements.txt
   python app.py
   ```

2. **Cart Service**:
   ```bash
   cd cart-service
   pip install -r requirements.txt
   python app.py
   ```

3. **Order Service**:
   ```bash
   cd order-service
   pip install -r requirements.txt
   python app.py
   ```

## 🔄 Service Communication

### API Endpoints

#### Store Service APIs
- `GET /api/album/{id}` - Get album details

#### Cart Service APIs
- `POST /add_to_cart` - Add item to cart
- `POST /update_quantity` - Update item quantity
- `POST /remove_item` - Remove item from cart
- `GET /checkout` - View checkout page
- `POST /process_payment` - Process payment

#### Order Service APIs
- `POST /api/orders` - Create new order
- `GET /api/orders` - Get all orders
- `GET /api/orders/{id}` - Get specific order
- `PUT /api/orders/{id}/status` - Update order status

### Service Dependencies
```
Store Service ←→ Cart Service ←→ Order Service
```

## 💳 Payment Flow

1. **Add to Cart**: User adds albums to cart from store
2. **Cart Management**: User can modify quantities or remove items
3. **Checkout**: User proceeds to checkout with cart items
4. **Payment**: Fake credit card payment simulation
5. **Order Creation**: Cart service sends order to order service
6. **Success**: User sees confirmation and cart is cleared

## 🎨 Features

### Store Service
- ✅ Modern, responsive UI with tabbed interface
- ✅ Album catalog with cover images
- ✅ Admin panel for adding albums
- ✅ Store statistics dashboard
- ✅ File upload for album covers

### Cart Service
- ✅ Shopping cart with persistent storage
- ✅ Quantity management
- ✅ Real-time total calculation
- ✅ Professional checkout interface
- ✅ Credit card payment simulation
- ✅ Input validation and formatting

### Order Service
- ✅ Order creation and tracking
- ✅ Order dashboard with statistics
- ✅ Detailed order views
- ✅ Order status management
- ✅ Revenue tracking

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite (separate for each service)
- **Frontend**: HTML, CSS, JavaScript
- **Containerization**: Docker & Docker Compose
- **Communication**: HTTP REST APIs

## 📁 Project Structure

```
exmaple-music-store-1/
├── app.py                 # Store service
├── requirements.txt       # Store service dependencies
├── Dockerfile            # Store service container
├── docker-compose.yml    # Service orchestration
├── k8s-deployment.yaml   # Kubernetes deployment
├── VERSION               # Version tracking
├── cart-service/         # Cart microservice
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── order-service/        # Order microservice
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
└── static/              # Static assets
    └── covers/          # Album cover images
```

## 🔧 Configuration

### Environment Variables

#### Store Service
- `CART_SERVICE_URL`: URL of cart service (default: http://localhost:5002)
- `ORDER_SERVICE_URL`: URL of order service (default: http://localhost:5001)
- `DB_PATH`: Database file path (default: music_store.db)

#### Cart Service
- `STORE_SERVICE_URL`: URL of store service (default: http://localhost:5000)
- `ORDER_SERVICE_URL`: URL of order service (default: http://localhost:5001)
- `CART_DB_PATH`: Cart database file path (default: cart.db)

#### Order Service
- `STORE_SERVICE_URL`: URL of store service (default: http://localhost:5000)
- `ORDER_DB_PATH`: Order database file path (default: orders.db)

## 🚀 Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f k8s-deployment.yaml
```

### Individual Services
```bash
# Store Service
docker build -t music-store .
docker run -p 5000:5000 music-store

# Cart Service
docker build -t cart-service ./cart-service
docker run -p 5002:5002 cart-service

# Order Service
docker build -t order-service ./order-service
docker run -p 5001:5001 order-service
```

## 🔍 Monitoring

### Service Health Checks
- Store Service: http://localhost:5000/
- Cart Service: http://localhost:5002/
- Order Service: http://localhost:5001/

### Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs store-service
docker-compose logs cart-service
docker-compose logs order-service
```

## 🧪 Testing

### Manual Testing Flow
1. **Add Albums**: Use admin tab to add albums
2. **Browse Store**: View albums in shop tab
3. **Add to Cart**: Add albums to shopping cart
4. **Manage Cart**: Update quantities or remove items
5. **Checkout**: Proceed to payment
6. **Complete Order**: Use fake credit card details
7. **View Orders**: Check order dashboard

### Test Credit Card Details
- **Card Number**: Any 13-19 digit number
- **Expiry**: Any future date (MM/YY format)
- **CVV**: Any 3-4 digit number

## 🔒 Security Notes

- This is a demo application with simulated payments
- No real payment processing is implemented
- Session management uses simple Flask sessions
- Databases are SQLite files (not suitable for production)
- No authentication/authorization implemented

## 🚧 Future Enhancements

- [ ] User authentication and authorization
- [ ] Real payment gateway integration
- [ ] Email notifications
- [ ] Inventory management
- [ ] Advanced search and filtering
- [ ] User reviews and ratings
- [ ] Recommendation system
- [ ] Analytics dashboard
- [ ] API rate limiting
- [ ] Service mesh implementation

## 📝 License

This project is for educational and demonstration purposes. 