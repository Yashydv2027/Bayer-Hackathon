"""
Real Checkout Service - FastAPI Backend

This is a REAL service that:
1. Connects to a SQLite database
2. Can process checkout requests
3. Will ACTUALLY CRASH when config is broken
4. Writes REAL logs
"""
import sqlite3
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup logging - writes to a REAL log file
LOG_FILE = Path(__file__).parent / "service.log"
DB_FILE = Path(__file__).parent / "checkout.db"
CONFIG_FILE = Path(__file__).parent / "service_config.json"

# Configure logging to file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("checkout-api")

app = FastAPI(title="Checkout Service", version="2.3.0")

# CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Configuration =============

def get_default_config():
    return {
        "db_pool_max_connections": 100,
        "db_timeout_seconds": 10,
        "is_healthy": True,
        "version": "2.3.0",
        "last_deployment": None
    }

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return get_default_config()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ============= Database =============

class DatabasePool:
    """Simulates a connection pool that can be broken."""
    
    def __init__(self):
        self.active_connections = 0
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with sample data."""
        conn = sqlite3.connect(str(DB_FILE))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT,
                price REAL,
                stock INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                product_id INTEGER,
                quantity INTEGER,
                total REAL,
                status TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # Insert sample data if empty
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            products = [
                (1, "Widget A", 29.99, 100),
                (2, "Widget B", 49.99, 50),
                (3, "Widget C", 99.99, 25),
            ]
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection - THIS CAN FAIL!"""
        config = load_config()
        max_connections = config.get("db_pool_max_connections", 100)
        timeout = config.get("db_timeout_seconds", 10)
        is_healthy = config.get("is_healthy", True)
        
        # REAL ERROR: If not healthy, simulate pool exhaustion
        if not is_healthy:
            self.active_connections = max_connections  # Pool is full!
            
            # Simulate waiting for connection
            logger.warning(f"Connection pool at capacity: {self.active_connections}/{max_connections}")
            time.sleep(timeout)  # Wait for timeout
            
            # REAL EXCEPTION!
            logger.error(f"DB connection timeout - pool exhausted after {timeout}s")
            logger.critical("ConnectionTimeoutException: Unable to acquire connection from pool")
            raise Exception(f"ConnectionTimeoutException: Connection pool exhausted after {timeout}s. Active: {self.active_connections}/{max_connections}")
        
        # Normal operation
        self.active_connections += 1
        logger.info(f"Connection acquired: {self.active_connections}/{max_connections}")
        
        try:
            conn = sqlite3.connect(str(DB_FILE), timeout=timeout)
            yield conn
        finally:
            conn.close()
            self.active_connections -= 1
            logger.info(f"Connection released: {self.active_connections}/{max_connections}")

# Global pool
db_pool = DatabasePool()

# ============= Models =============

class CheckoutRequest(BaseModel):
    product_id: int
    quantity: int

class CheckoutResponse(BaseModel):
    order_id: int
    product_name: str
    quantity: int
    total: float
    status: str

# ============= API Endpoints =============

@app.get("/health")
def health_check():
    """Health check endpoint."""
    config = load_config()
    return {
        "status": "healthy" if config.get("is_healthy", True) else "unhealthy",
        "version": config.get("version", "2.3.0"),
        "db_pool_active": db_pool.active_connections,
        "db_pool_max": config.get("db_pool_max_connections", 100)
    }

@app.get("/products")
def list_products():
    """List all products."""
    with db_pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        return [
            {"id": p[0], "name": p[1], "price": p[2], "stock": p[3]}
            for p in products
        ]

@app.post("/checkout", response_model=CheckoutResponse)
def process_checkout(request: CheckoutRequest):
    """Process a checkout - THIS CAN FAIL!"""
    start_time = time.time()
    
    logger.info(f"Processing checkout: product={request.product_id}, qty={request.quantity}")
    
    try:
        with db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get product
            cursor.execute("SELECT * FROM products WHERE id = ?", (request.product_id,))
            product = cursor.fetchone()
            
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            if product[3] < request.quantity:
                raise HTTPException(status_code=400, detail="Insufficient stock")
            
            # Calculate total
            total = product[2] * request.quantity
            
            # Create order
            cursor.execute(
                "INSERT INTO orders (product_id, quantity, total, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (request.product_id, request.quantity, total, "completed", datetime.now())
            )
            order_id = cursor.lastrowid
            
            # Update stock
            cursor.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (request.quantity, request.product_id)
            )
            
            conn.commit()
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"Checkout completed: order={order_id}, duration={duration:.0f}ms")
            
            return CheckoutResponse(
                order_id=order_id,
                product_name=product[1],
                quantity=request.quantity,
                total=total,
                status="completed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"Checkout FAILED after {duration:.0f}ms: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/metrics")
def get_metrics():
    """Get current service metrics."""
    config = load_config()
    
    if config.get("is_healthy", True):
        return {
            "latency_p99_ms": 150,
            "error_rate": 0.1,
            "requests_per_second": 450,
            "db_pool_utilization": db_pool.active_connections / config.get("db_pool_max_connections", 100)
        }
    else:
        return {
            "latency_p99_ms": 2000,
            "error_rate": 15.0,
            "requests_per_second": 180,
            "db_pool_utilization": 1.0  # 100% utilized = bad!
        }

# ============= Admin Endpoints (for Streamlit) =============

@app.post("/admin/inject-error")
def inject_error():
    """INJECT A REAL ERROR - breaks the service!"""
    broken_config = {
        "db_pool_max_connections": 50,  # Reduced from 100
        "db_timeout_seconds": 2,        # Reduced from 10
        "is_healthy": False,
        "version": "2.3.1",
        "last_deployment": datetime.now().strftime("%H:%M")
    }
    save_config(broken_config)
    
    logger.warning("CONFIGURATION CHANGED - DB pool reduced!")
    logger.warning(f"New config: max_connections=50, timeout=2s")
    
    return {"status": "error_injected", "config": broken_config}

@app.post("/admin/reset")
def reset_service():
    """Reset service to healthy state."""
    save_config(get_default_config())
    logger.info("Service reset to healthy configuration")
    return {"status": "reset", "config": get_default_config()}

@app.get("/admin/logs")
def get_logs(lines: int = 50):
    """Get recent log entries."""
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            all_lines = f.readlines()
            return {"logs": all_lines[-lines:]}
    return {"logs": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
