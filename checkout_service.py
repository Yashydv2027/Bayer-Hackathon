"""
Checkout Service - FastAPI with MULTIPLE REAL ERROR SCENARIOS

This version has multiple types of errors that can be randomly injected:
1. Connection Pool Exhaustion (DB)
2. Memory Leak / OOM
3. Deadlock
4. Network Timeout
5. Cascading Failure
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import time
import logging
import json
import random
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('checkout-api')

app = FastAPI(title="Checkout Service", version="2.3.0")

# Config file
CONFIG_FILE = Path(__file__).parent / "service_config.json"
DB_FILE = Path(__file__).parent / "checkout.db"

# Default healthy config
DEFAULT_CONFIG = {
    "db_pool_max_connections": 100,
    "db_timeout_seconds": 10,
    "memory_limit_mb": 512,
    "max_retry_attempts": 3,
    "downstream_timeout_ms": 5000,
    "is_healthy": True,
    "error_type": None,
    "version": "2.3.0"
}

# Error scenarios
ERROR_SCENARIOS = [
    {
        "type": "connection_pool",
        "name": "Database Connection Pool Exhaustion",
        "config": {"db_pool_max_connections": 50, "db_timeout_seconds": 2},
        "symptoms": ["ConnectionTimeoutException", "pool exhausted", "high latency"]
    },
    {
        "type": "memory_leak",
        "name": "Memory Leak in Cache Service",
        "config": {"memory_limit_mb": 32, "cache_eviction_disabled": True},
        "symptoms": ["OutOfMemoryError", "GC overhead", "heap exhausted"]
    },
    {
        "type": "deadlock",
        "name": "Database Deadlock",
        "config": {"lock_timeout_ms": 100, "max_lock_retries": 1},
        "symptoms": ["DeadlockException", "lock timeout", "transaction rollback"]
    },
    {
        "type": "network_timeout",
        "name": "Downstream Service Timeout",
        "config": {"downstream_timeout_ms": 100, "payment_gateway_unreachable": True},
        "symptoms": ["SocketTimeoutException", "connection refused", "gateway unreachable"]
    },
    {
        "type": "cascading",
        "name": "Cascading Failure from Auth Service",
        "config": {"auth_service_down": True, "circuit_breaker_open": True},
        "symptoms": ["AuthServiceUnavailable", "circuit breaker open", "retry exhausted"]
    }
]

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    config["last_deployment"] = datetime.now().strftime("%H:%M:%S")
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def init_db():
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            quantity INTEGER,
            total REAL,
            created_at TEXT
        )
    ''')
    # Seed products
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        products = [
            (1, 'Widget', 29.99, 100),
            (2, 'Gadget', 49.99, 50),
            (3, 'Gizmo', 19.99, 200)
        ]
        cursor.executemany('INSERT INTO products VALUES (?, ?, ?, ?)', products)
    conn.commit()
    conn.close()
    logger.info("Database initialized")

init_db()

# State
class ServiceState:
    def __init__(self):
        self.active_connections = 50
        self.error_count = 0
        self.request_count = 0
        self.current_error = None
        self.memory_used_mb = 128
        self.locks_held = 0

state = ServiceState()

class CheckoutRequest(BaseModel):
    product_id: int
    quantity: int = 1

# ============= HEALTH & METRICS =============

@app.get("/health")
async def health():
    config = load_config()
    return {
        "status": "healthy" if config.get("is_healthy", True) else "unhealthy",
        "version": config.get("version", "2.3.0"),
        "db_pool_active": state.active_connections,
        "db_pool_max": config.get("db_pool_max_connections", 100),
        "memory_used_mb": state.memory_used_mb,
        "error_type": state.current_error
    }

@app.get("/metrics")
async def metrics():
    config = load_config()
    max_conn = config.get("db_pool_max_connections", 100)
    
    # Calculate metrics based on error state
    if state.current_error:
        latency = random.randint(1500, 2500)
        error_rate = random.uniform(10, 25)
        pool_util = 1.0
    else:
        latency = random.randint(100, 200)
        error_rate = random.uniform(0, 0.5)
        pool_util = state.active_connections / max_conn
    
    return {
        "latency_p99_ms": latency,
        "error_rate": round(error_rate, 1),
        "db_pool_utilization": round(pool_util, 2),
        "memory_used_mb": state.memory_used_mb,
        "locks_held": state.locks_held,
        "request_count": state.request_count,
        "error_count": state.error_count
    }

# ============= ERROR INJECTION =============

@app.post("/admin/inject-error")
async def inject_error(error_type: str = None):
    """Inject a random error or specific type."""
    
    # Pick random error if not specified
    if error_type:
        scenario = next((e for e in ERROR_SCENARIOS if e["type"] == error_type), ERROR_SCENARIOS[0])
    else:
        scenario = random.choice(ERROR_SCENARIOS)
    
    # Load and modify config
    config = load_config()
    config.update(scenario["config"])
    config["is_healthy"] = False
    config["error_type"] = scenario["type"]
    save_config(config)
    
    # Update state
    state.current_error = scenario["type"]
    state.error_count += 1
    
    # Log the injection
    logger.warning(f"CONFIGURATION CHANGED - {scenario['name']}")
    logger.warning(f"Error type: {scenario['type']}")
    for key, value in scenario["config"].items():
        logger.warning(f"Config: {key}={value}")
    
    return {
        "injected": True,
        "error_type": scenario["type"],
        "name": scenario["name"],
        "symptoms": scenario["symptoms"]
    }

@app.post("/admin/inject-error/{error_type}")
async def inject_specific_error(error_type: str):
    """Inject a specific error type."""
    return await inject_error(error_type)

@app.get("/admin/error-types")
async def list_error_types():
    """List available error scenarios."""
    return [{"type": e["type"], "name": e["name"]} for e in ERROR_SCENARIOS]

@app.post("/admin/reset")
async def reset_service():
    """Reset to healthy state."""
    save_config(DEFAULT_CONFIG.copy())
    state.current_error = None
    state.active_connections = 50
    state.memory_used_mb = 128
    state.locks_held = 0
    logger.info("Service reset to healthy configuration")
    return {"status": "reset", "healthy": True}

# ============= CHECKOUT (FAILS BASED ON ERROR TYPE) =============

@app.post("/checkout")
async def checkout(request: CheckoutRequest):
    config = load_config()
    start_time = time.time()
    state.request_count += 1
    
    logger.info(f"Processing checkout: product={request.product_id}, qty={request.quantity}")
    
    error_type = config.get("error_type") or state.current_error
    
    if error_type:
        # Simulate different failure modes
        if error_type == "connection_pool":
            await simulate_connection_pool_error(config)
        elif error_type == "memory_leak":
            await simulate_memory_error(config)
        elif error_type == "deadlock":
            await simulate_deadlock_error(config)
        elif error_type == "network_timeout":
            await simulate_network_timeout_error(config)
        elif error_type == "cascading":
            await simulate_cascading_error(config)
    
    # Successful checkout
    duration = int((time.time() - start_time) * 1000)
    
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    cursor.execute('SELECT price FROM products WHERE id=?', (request.product_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    
    total = row[0] * request.quantity
    cursor.execute(
        'INSERT INTO orders (product_id, quantity, total, created_at) VALUES (?, ?, ?, ?)',
        (request.product_id, request.quantity, total, datetime.now().isoformat())
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    logger.info(f"Checkout completed: order={order_id}, duration={duration}ms")
    
    return {"order_id": order_id, "total": total, "status": "completed"}

# ============= ERROR SIMULATIONS =============

async def simulate_connection_pool_error(config):
    timeout = config.get("db_timeout_seconds", 2)
    max_conn = config.get("db_pool_max_connections", 50)
    
    state.active_connections = max_conn
    logger.warning(f"Connection pool at capacity: {max_conn}/{max_conn}")
    
    time.sleep(timeout)
    
    state.error_count += 1
    logger.error(f"DB connection timeout - pool exhausted after {timeout}s")
    logger.critical(f"ConnectionTimeoutException: Unable to acquire connection from pool")
    
    raise HTTPException(
        status_code=503,
        detail=f"ConnectionTimeoutException: Connection pool exhausted after {timeout}s. Active: {max_conn}/{max_conn}"
    )

async def simulate_memory_error(config):
    state.memory_used_mb = 490
    logger.warning(f"Memory usage critical: {state.memory_used_mb}MB / 512MB")
    
    time.sleep(1)
    
    state.memory_used_mb = 512
    state.error_count += 1
    logger.error("Memory allocation failed - heap exhausted")
    logger.critical("OutOfMemoryError: Java heap space - GC overhead limit exceeded")
    logger.error("Cache eviction disabled - memory cannot be freed")
    
    raise HTTPException(
        status_code=503,
        detail="OutOfMemoryError: Heap exhausted. Memory: 512/512MB. GC overhead limit exceeded."
    )

async def simulate_deadlock_error(config):
    lock_timeout = config.get("lock_timeout_ms", 100)
    
    state.locks_held = 5
    logger.warning(f"Transaction waiting for lock: 5 locks held")
    logger.warning(f"Lock contention detected on table: orders")
    
    time.sleep(lock_timeout / 1000)
    
    state.error_count += 1
    logger.error(f"Lock timeout after {lock_timeout}ms - deadlock detected")
    logger.critical("DeadlockException: Transaction rolled back due to lock timeout")
    logger.error("Circular dependency: TX-001 -> orders -> TX-002 -> products -> TX-001")
    
    raise HTTPException(
        status_code=503,
        detail=f"DeadlockException: Transaction rolled back. Lock timeout: {lock_timeout}ms. Circular dependency detected."
    )

async def simulate_network_timeout_error(config):
    timeout = config.get("downstream_timeout_ms", 100)
    
    logger.info("Calling payment gateway: api.payments.example.com")
    logger.warning(f"Payment gateway not responding after {timeout}ms")
    
    time.sleep(timeout / 1000)
    
    state.error_count += 1
    logger.error(f"Socket timeout after {timeout}ms - gateway unreachable")
    logger.critical("SocketTimeoutException: Connection to payment gateway timed out")
    logger.error("Downstream service: api.payments.example.com:443 - connection refused")
    
    raise HTTPException(
        status_code=504,
        detail=f"SocketTimeoutException: Payment gateway timeout after {timeout}ms. Host unreachable."
    )

async def simulate_cascading_error(config):
    logger.info("Validating user session with auth service")
    logger.warning("Auth service: auth.internal.svc - connection refused")
    logger.warning("Retry 1/3 failed: AuthServiceUnavailable")
    
    time.sleep(0.5)
    
    logger.warning("Retry 2/3 failed: AuthServiceUnavailable")
    
    time.sleep(0.5)
    
    logger.warning("Retry 3/3 failed: AuthServiceUnavailable")
    logger.error("All retries exhausted - circuit breaker opened")
    
    state.error_count += 1
    logger.critical("CircuitBreakerOpenException: Auth service circuit breaker tripped")
    logger.error("Cascading failure: checkout -> auth -> user-db -> primary-db")
    
    raise HTTPException(
        status_code=503,
        detail="CircuitBreakerOpenException: Auth service unavailable. Cascading failure detected."
    )

# ============= PRODUCTS =============

@app.get("/products")
async def get_products():
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = [{"id": r[0], "name": r[1], "price": r[2], "stock": r[3]} for r in cursor.fetchall()]
    conn.close()
    return products

@app.get("/admin/logs")
async def get_logs():
    log_file = Path(__file__).parent / "service.log"
    if log_file.exists():
        with open(log_file) as f:
            lines = f.readlines()
            return {"logs": lines[-50:]}
    return {"logs": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
