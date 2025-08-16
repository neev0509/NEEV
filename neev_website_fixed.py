from flask import Flask, request, redirect, url_for, session, jsonify
from cryptography.fernet import Fernet
import os, json
from datetime import datetime, timedelta

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("FLASK_SECRET", "supersecretkey_change_me")

# ---------------- Config ----------------
DEFAULT_ADMIN_PASSWORD = "2468"
UPI_ID = "neev@upi"
COMPANY_NAME = "NEEV Diamonds"
WEBSITE_NAME = "neev.com"

# ---------------- File Paths ----------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
CARDS_FILE = os.path.join(DATA_DIR, "cards.json")
VIDEOS_FILE = os.path.join(DATA_DIR, "videos.json")
STOCK_FILE = os.path.join(DATA_DIR, "stock.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
KEY_FILE = os.path.join(DATA_DIR, "secret.key")

# ---------------- Encryption Key ----------------
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())
with open(KEY_FILE, "rb") as f:
    key = f.read()
fernet = Fernet(key)

# ---------------- Load/Save Helpers ----------------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

# ---------------- Data Initialization ----------------
products = load_json(PRODUCTS_FILE, [
    {"id": 1, "name": "Lab Grown Diamond - 1 Carat", "price": 50000, "video": "https://www.youtube.com/embed/example1", "show_price": True, "stock": 10},
    {"id": 2, "name": "Lab Grown Diamond - 2 Carat", "price": 90000, "video": "https://www.youtube.com/embed/example2", "show_price": True, "stock": 5}
])
orders = load_json(ORDERS_FILE, [])
saved_cards = load_json(CARDS_FILE, {})
videos = load_json(VIDEOS_FILE, [])
stock = load_json(STOCK_FILE, {str(p['id']): p.get("stock", 0) for p in products})
config = load_json(CONFIG_FILE, {})  # may contain encrypted admin_password

next_product_id = max((p["id"] for p in products), default=0) + 1

# ---------------- Admin password helpers ----------------
def get_admin_password():
    enc = config.get("admin_password")
    if enc:
        try:
            return fernet.decrypt(enc.encode()).decode()
        except:
            return DEFAULT_ADMIN_PASSWORD
    return DEFAULT_ADMIN_PASSWORD

def set_admin_password(new_pw):
    enc = fernet.encrypt(new_pw.encode()).decode()
    config["admin_password"] = enc
    save_json(CONFIG_FILE, config)

# ensure first-time config exists
if "admin_password" not in config:
    set_admin_password(DEFAULT_ADMIN_PASSWORD)

# ---------------- Utility ----------------
def iso_now():
    return datetime.now().isoformat()

# ---------------- Routes / Pages ----------------

def render_base_page(content_html):
    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>__COMPANY_NAME__ - __WEBSITE_NAME__</title>
  <style>
    body{font-family:Segoe UI, Tahoma, Geneva, Verdana, sans-serif; margin:0; background:#fafafa; color:#222}
    header{position:fixed; left:0; right:0; top:0; height:60px; background:#fff; box-shadow:0 2px 8px rgba(0,0,0,0.05); display:flex; align-items:center; padding:0 20px; z-index:30}
    .brand{font-weight:700; color:#004d99; font-size:18px}
    .admin-link{position:absolute; right:20px; top:12px; cursor:pointer; text-decoration:underline; color:#444}
    main{padding:100px 20px 40px; max-width:1100px; margin:0 auto}
    .product{background:#fff; padding:18px; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.06); margin-bottom:18px}
    .center{display:flex; gap:20px; align-items:flex-start; flex-wrap:wrap}
    .payment-box{background:#fff; border-radius:12px; padding:24px; min-width:320px; flex:1; box-shadow:0 8px 24px rgba(0,0,0,0.06)}
    .big-btn{padding:12px 18px; border-radius:8px; border:none; background:#28a745; color:#fff; font-weight:700; cursor:pointer; width:100%}
    .upi-btn{padding:10px 14px; border-radius:8px; border:none; background:#0078d7; color:#fff; margin-right:8px; cursor:pointer}
    input[type=text], input[type=tel], input[type=password], textarea, select{padding:10px; font-size:16px; width:100%; box-sizing:border-box; margin:6px 0 12px; border-radius:8px; border:1px solid #ddd}
    label{font-size:14px; color:#333}
    footer{text-align:center; padding:20px; color:#666; font-size:14px}
    /* Admin modal */
    .admin-modal{position:fixed; inset:0; display:none; align-items:center; justify-content:center; z-index:1000;}
    .admin-modal .overlay{position:absolute; inset:0; background:rgba(0,0,0,0.5)}
    .admin-modal .panel{position:relative; width:100%; max-width:900px; height:90vh; background:#fff; border-radius:8px; overflow:auto; z-index:2; display:flex}
    .admin-sidebar{width:240px; background:#0b3b66; color:#fff; padding:18px; box-sizing:border-box}
    .admin-sidebar h2{font-size:18px; margin:0 0 12px}
    .admin-sidebar a{display:block; color:#fff; margin:8px 0; text-decoration:none; cursor:pointer}
    .admin-content{flex:1; padding:18px; box-sizing:border-box}
    .small-muted{font-size:13px; color:#666}
    .tab{display:none}
    .tab.active{display:block}
    .msg-success{color:green; font-weight:700}
    .msg-fail{color:red; font-weight:700}
    .lock-info{color:#b33}
    .grid{display:grid; grid-template-columns:1fr 1fr; gap:12px}
    @media (max-width:800px){
        .grid{grid-template-columns:1fr}
        .admin-sidebar{display:none}
        .admin-modal .panel{height:100vh}
    }
  </style>
</head>
<body>
<header>
  <div class="brand">__COMPANY_NAME__ — __WEBSITE_NAME__</div>
  <div class="admin-link" id="openAdmin">Admin Panel</div>
</header>
<main>
__CONTENT__
</main>
<footer>© __YEAR__ __COMPANY_NAME__</footer>

<!-- Admin Modal (fullscreen) -->
<div class="admin-modal" id="adminModal">
  <div class="overlay" onclick="closeAdmin()"></div>
  <div class="panel" role="dialog" aria-modal="true">
    <div class="admin-sidebar">
      <h2>Admin</h2>
      <div id="adminLockInfo" class="small-muted"></div>
      <a onclick="showTab('orders')">Orders</a>
      <a onclick="showTab('payments')">Payment</a>
      <a onclick="showTab('sales')">Sales</a>
      <a onclick="showTab('profit')">Profit</a>
      <a onclick="showTab('videos')">Videos</a>
      <a onclick="showTab('products')">Products</a>
      <a onclick="showTab('password')">Password</a>
      <a onclick="showTab('stock')">Stock</a>
      <hr style="border:none;height:1px;background:#ffffff33;margin:12px 0">
      <a onclick="logoutAdmin()" style="color:#ffd700; cursor:pointer">Logout</a>
    </div>

    <div class="admin-content">
      <div id="adminLoginBox">
        <h3>Enter admin password</h3>
        <p class="small-muted">You have <span id="attemptsLeft">3</span> attempts left.</p>
        <input type="password" id="adminPassword" placeholder="Password">
        <button class="big-btn" onclick="submitAdminPassword()">Enter</button>
        <p id="adminResult" style="font-size:24px"></p>
      </div>

      <!-- Dashboard tabs -->
      <div id="dashboardTabs" style="display:none">
        <div id="orders" class="tab">
          <h3>Orders</h3>
          <div id="ordersList">Loading...</div>
        </div>

        <div id="payments" class="tab">
          <h3>Payment (manual verification)</h3>
          <div id="paymentsList">Loading...</div>
        </div>

        <div id="sales" class="tab">
          <h3>Sales</h3>
          <div id="salesStats">Loading...</div>
        </div>

        <div id="profit" class="tab">
          <h3>Profit</h3>
          <div id="profitStats">Loading...</div>
        </div>

        <div id="videos" class="tab">
          <h3>Videos</h3>
          <div id="videosList">Loading...</div>
          <h4>Add Video (YouTube embed URL)</h4>
          <input id="videoURL" placeholder="https://www.youtube.com/embed/xxxx">
          <button onclick="addVideo()">Add Video</button>
        </div>

        <div id="products" class="tab">
          <h3>Products</h3>
          <div id="productsList">Loading...</div>
          <h4>Add Product</h4>
          <input id="newName" placeholder="Name"><input id="newPrice" placeholder="Price">
          <input id="newVideo" placeholder="Video embed URL"><input id="newStock" placeholder="Stock">
          <button onclick="addProduct()">Add Product</button>
        </div>

        <div id="password" class="tab">
          <h3>Change Admin Password</h3>
          <input id="oldPass" type="password" placeholder="Old password">
          <input id="newPass" type="password" placeholder="New password">
          <button onclick="changePassword()">Change Password</button>
          <p id="passMsg"></p>
        </div>

        <div id="stock" class="tab">
          <h3>Stock Management</h3>
          <div id="stockList">Loading...</div>
          <h4>Reset All Stock to 0</h4>
          <button onclick="resetStock()">Reset Stock</button>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
// --- Admin modal behavior & login via AJAX ---
const adminModal = document.getElementById('adminModal');
const openAdminBtn = document.getElementById('openAdmin');
const adminResult = document.getElementById('adminResult');
const attemptsLeftEl = document.getElementById('attemptsLeft');
let attemptsLeft = 3;

openAdminBtn.addEventListener('click', async () => {
  await refreshLockInfo();
  adminModal.style.display = 'flex';
});

function closeAdmin(){
  adminModal.style.display = 'none';
  adminResult.innerText = '';
  document.getElementById('adminPassword').value = '';
}

async function refreshLockInfo(){
  const r = await fetch('/admin_status');
  const data = await r.json();
  attemptsLeft = data.attempts_left;
  attemptsLeftEl.innerText = attemptsLeft;
  const lockInfo = document.getElementById('adminLockInfo');
  if(data.locked_until){
    lockInfo.innerText = "Locked until: " + data.locked_until;
    document.getElementById('adminPassword').disabled = true;
    document.querySelector('#adminLoginBox button').disabled = true;
  } else {
    lockInfo.innerText = '';
    document.getElementById('adminPassword').disabled = false;
    document.querySelector('#adminLoginBox button').disabled = false;
  }
}

// Other remaining code is similar.
</script>
</body>
</html>
"""

    html = html.replace("__COMPANY_NAME__", COMPANY_NAME)\
               .replace("__WEBSITE_NAME__", WEBSITE_NAME)\
               .replace("__UPI_ID__", UPI_ID)\
               .replace("__YEAR__", str(datetime.now().year))\
               .replace("__CONTENT__", content_html)
    return html

# ------------------- Page routes -------------------
@app.route("/")
def home():
    # simple product listing linking to /buy/<id>
    product_html = ""
    for p in products:
        price_html = f"₹ {p['price']}" if p.get("show_price", True) else ""
        product_html += """
        <div class="product center">
          <div style="flex:1;min-width:260px">
            <h3>{p['name']}</h3>
            <p style="font-size:18px">{price_html}</p>
            <iframe width="320" height="180" src="{p.get('video','')}" allowfullscreen></iframe>
          </div>
          <div style="min-width:320px">
            <a href="/buy/{p['id']}"><button class="big-btn">Buy Now</button></a>
            <p class="small-muted">Stock: {stock.get(str(p['id']), p.get('stock',0))}</p>
          </div>
        </div>
        """
@app.route("/buy/<int:pid>", methods=["GET", "POST"])
def buy(pid):
    product = next((p for p in products if p["id"] == pid), None)
    if not product:
        return "Product not found", 404

    if request.method == "POST":
        # Add the code that should execute when a POST request is made
        name = request.form.get("name", "")
        address = request.form.get("address", "")
        contact = request.form.get("contact", "")
        # Add any other form processing or logic here

        # After processing, redirect or return the appropriate response
        return redirect(url_for("payment", pid=pid))

    # If it's a GET request, render the product details page
    buy_html = """
    <div class="product">
      <h2>Buy: {product['name']}</h2>
      <p style="font-size:18px">{'₹ '+str(product['price']) if product.get('show_price',True) else ''}</p>
      <div class="center">
        <div style="flex:1;min-width:320px">
          <form method="post" id="checkoutForm">
            <label>Name</label><input name="name" required>
            <label>Address</label><input name="address" required>
            <label>Contact</label><input name="contact" required>
            <label>Payment method</label>
            <label><input type="radio" name="payment" value="upi" checked onchange="updateForm()"> UPI</label>
            <label><input type="radio" name="payment" value="card" onchange="updateForm()"> Card</label>
          </form>
        </div>
        <div style="min-width:320px">
          <h4>Product Details</h4>
          <iframe width="320" height="180" src="{product.get('video','')}" allowfullscreen></iframe>
        </div>
      </div>
    </div>
    """
    buy_html = buy_html.replace("__UPI_ID__", UPI_ID)
    return render_base_page(buy_html)
