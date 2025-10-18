from flask import Flask, render_template, request, redirect, url_for, flash, abort, make_response
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb
import pandas as pd
from flask import send_file
from functools import wraps
from mysql.connector import Error
from MySQLdb import OperationalError, Error
from datetime import datetime
from flask import jsonify
import qrcode
from io import BytesIO
from flask import send_file
import base64
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from math import ceil

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

# MySQL configuration
# # If on server: 
# app.config['MYSQL_HOST'] = #your host
# app.config['MYSQL_PORT'] = #your port
# app.config['MYSQL_USER'] = 'doadmin'  # Your MySQL username
# app.config['MYSQL_PASSWORD'] = # Your MySQL password
# If locally:
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Your MySQL username
app.config['MYSQL_PASSWORD'] = '123456'  # Your MySQL password
#######################################################################################
app.config['MYSQL_DB'] = 'inventory_system'
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Ensure this directory exists
app.config['ALLOWED_EXTENSIONS'] = {'xls', 'xlsx'}  # Allowed Excel file extensions

mysql = MySQL(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class to work with Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role
        
# Load user from database
@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", [user_id])
    user = cur.fetchone()
    cur.close()
    if user:
        return User(user[0], user[1], user[3])  # user_id, username, role
    return None

# Role-based access control decorator
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("Unauthorized access!", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.route('/change_role', methods=['POST'])
@login_required
def change_role():
    new_role = request.form['role']

    # Update role in the database
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, current_user.id))
    mysql.connection.commit()
    cur.close()

    # Update current_user role dynamically after changing
    current_user.role = new_role
    flash(f"Role changed to {new_role} successfully!", "success")
    return redirect(url_for('index'))

# Home route
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username, role=current_user.role)

# 采购单
@app.route('/purchase_order', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase')
def purchase_order():
    cursor = mysql.connection.cursor()

    # Fetch products from database
    cursor.execute("SELECT item, sku FROM products")
    products = cursor.fetchall()  # List of tuples [(product_name1, sku1), (product_name2, sku2), ...]

    cursor.close()  # Close after fetching
    if request.method == 'POST':
        try:
            # Get form data for purchase
            purchase_date = request.form.get('purchase_date')
            supplier = request.form.get('supplier')
            invoice = request.form.get('invoice')
            pay_way = request.form.get('pay_way')
            user_name = current_user.username
            order_price = request.form.get('grand_total')
            # Ensure all required fields are provided
            if not all([purchase_date, pay_way, order_price]):
                flash("All fields are required!", "danger")
                return redirect(url_for('purchase_order'))

            # Insert into 'purchase' table
            cursor = mysql.connection.cursor()
            cursor.execute('''
                INSERT INTO purchase (purchase_date, supplier, invoice, pay_way, price, user_name)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (purchase_date, supplier, invoice, pay_way, order_price, user_name))
            
            # Get the purchase_id (last inserted ID)
            purchase_id = cursor.lastrowid

            # Get form data for each product in purchase_order
            product_skus = request.form.getlist('product_sku[]')
            product_names = request.form.getlist('product_name[]')
            unit_prices =  request.form.getlist('unit_price[]') 
            quantities = request.form.getlist('quantity[]') 
            prices =  request.form.getlist('total_price[]') 
            delivery_fees =  request.form.getlist('delivery_fee[]') 
            

            # Check if product details exist
            if not product_skus:
                flash("At least one product is required!", "danger")
                return redirect(url_for('purchase_order'))
    
            # Insert into 'purchase_order' table
            for i in range(len(product_skus)):
                cursor.execute('''
                    INSERT INTO purchase_order 
                    (purchase_id, product_sku, product_name, unit_price, quantity, price, delivery_fee)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (purchase_id, product_skus[i], product_names[i], 
                      unit_prices[i], quantities[i], prices[i], 
                      delivery_fees[i]))

            mysql.connection.commit()
            cursor.close()

            flash('Purchase Order added!', 'success')
            return redirect(url_for('inventory_in',purchase_id=purchase_id))  # Removed passing purchase_id

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('purchase_order'))

    return render_template('purchase_order.html',products=products)

@app.route('/view_purchase', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def view_purchase():
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
                    SELECT 
                        p.purchase_id,
                        p.purchase_date,
                        p.supplier,
                        p.invoice,
                        p.price,
                        p.pay_way,
                        p.user_name
                    FROM 
                        purchase p
                   """)
    purchase_data = cursor.fetchall()
    cursor.close() 
    return render_template('view_purchase.html', purchase=purchase_data)

@app.route('/view_purchase_order/<int:purchase_id>', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def view_purchase_order(purchase_id):
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
                    SELECT 
                        p.product_name,
                        p.product_sku,
                        p.unit_price,
                        p.quantity,
                        p.price,
                        p.delivery_fee
                    FROM 
                        purchase_order p
                    WHERE 
                        p.purchase_id = %s
                """, (purchase_id,))
    purchase_data = cursor.fetchall()
    cursor.close() 
    return render_template('view_purchase_order.html', purchase = purchase_data)

# Download purchase orders
@app.route('/download_purchase')
@login_required
def download_purchase():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cur = mysql.connection.cursor()
    query = '''
        SELECT p.purchase_id, p.purchase_date, p.supplier, p.invoice, p.price, p.pay_way, p.user_name,
               o.product_sku, o.product_name, o.unit_price, o.quantity, o.price AS order_price, o.delivery_fee
        FROM purchase p
        JOIN purchase_order o ON p.purchase_id = o.purchase_id
        WHERE p.purchase_date BETWEEN %s AND %s
        ORDER BY p.purchase_date DESC
    '''
    
    cur.execute(query, (start_date, end_date))
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data, columns=[
        '采购单号', '采购日期', '供货商', '发票号', '价格', '结算方式', '操作人',
        '产品sku', '产品名称', '单价', '数量', '金额', '运费'
    ])
    path = '/tmp/purchase_data.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True, download_name='purchase_data.xlsx')

# 生产单
@app.route('/produce_order', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase')
def produce_order():
    cursor = mysql.connection.cursor()

    # Fetch all products from the products table
    cursor.execute('''SELECT item, sku FROM products''')
    products = cursor.fetchall()  # List of tuples [(product_name1, sku1), (product_name2, sku2), ...]

    if request.method == 'POST':
        # Get form data for produce
        produce_date = request.form.get('produce_date')
        product_name = request.form.get('product_name')
        product_sku = request.form.get('product_sku')
        sale_id = request.form.get('sale_id')  # Nullable field
        plan_quantity = request.form.get('plan_quantity')
        user_name = current_user.username

        # Validate required fields
        if not all([produce_date, product_name, product_sku, plan_quantity, user_name]):
            flash('Missing required fields. Please fill out all fields.', 'danger')
            return redirect(url_for('produce_order'))

        # Generate the produce_source
        today = datetime.strptime(produce_date, '%Y-%m-%d')
        date_str = today.strftime('%Y%m%d')  # Format as YYYYMMDD

        # Find the most recent produce_source for today to get the serial number
        cursor.execute('''
            SELECT produce_source FROM produce WHERE produce_source LIKE %s ORDER BY produce_source DESC LIMIT 1
        ''', (f'BCH{date_str}%',))
        result = cursor.fetchone()

        if result:
            # Extract the last serial number (e.g., BCH20250401-002), increment it
            last_produce_source = result[0]
            serial_number = int(last_produce_source[-3:]) + 1  # Increment the last serial number
        else:
            # If no previous produce_source exists, start from 001
            serial_number = 1

        # Generate the new produce_source
        produce_source = f"BCH{date_str}-{serial_number:03d}"  # Format as BCHYYYYMMDD-XXX

        # Insert into the 'produce' table with the generated produce_source
        cursor.execute('''
            INSERT INTO produce (produce_source, production_date, product_name, product_sku, sale_id, plan_quantity, user_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (produce_source, produce_date, product_name, product_sku, sale_id, plan_quantity, user_name))

        # Insert into 'produce_order' table
        product_skus_order = request.form.getlist('product_sku_order[]')
        product_names_order = request.form.getlist('product_name_order[]')
        quantities_order = request.form.getlist('quantity[]')
        
        if len(product_skus_order) != len(product_names_order) or len(product_skus_order) != len(quantities_order):
            flash('Mismatch in order details. Please check the input.', 'danger')
            return redirect(url_for('produce_order'))

        for i in range(len(product_skus_order)):
            if product_names_order[i] and quantities_order[i]:
                cursor.execute('''
                    INSERT INTO produce_order (produce_source, material_sku, material_name, quantity)
                    VALUES (%s, %s, %s, %s)
                ''', (produce_source, product_skus_order[i], product_names_order[i], quantities_order[i]))

        mysql.connection.commit()
        cursor.close()

        flash('Produce Order added successfully!', 'success')
        #return redirect(url_for('produce_order'))
        return redirect(url_for('produce_order_print', produce_source=produce_source))

    return render_template('produce_order.html', products=products)   # Render the form on GET requests

@app.route('/download_produce')
@login_required
def download_produce():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT p.produce_id, p.production_date, p.produce_source, p.product_name, p.product_sku, 
               p.sale_id, p.plan_quantity, p.user_name,
               o.material_sku, o.material_name, o.quantity
        FROM produce p
        JOIN produce_order o ON p.produce_source = o.produce_source
        WHERE p.production_date BETWEEN %s AND %s 
        ORDER BY p.production_date DESC
    ''', (start_date, end_date))
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data, columns=[
        '生产id', '生产日期', '生产批号', '产品名称', '产品sku',
        '对应销售单号', '计划生产数量', '操作人',
        '原料sku', '原料名称', '原料数量'
    ])
    path = '/tmp/produce_data.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True, download_name='produce_data.xlsx')

@app.route('/produce_order_print/<produce_source>', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def produce_order_print(produce_source):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Fetch results as a dictionary!

    # Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(produce_source)
    qr.make(fit=True)
    # Convert QR Code to base64
    img = qr.make_image(fill="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Fetch production order details based on produce_source
    cursor.execute('''
        SELECT * FROM produce WHERE produce_source = %s
    ''', (produce_source,))
    produce_order  = cursor.fetchone()

    if not produce_order:
        flash("Production order not found!", "danger")
        return redirect(url_for('produce_order'))

    cursor.execute('''
        SELECT * FROM produce_order WHERE produce_source = %s
    ''', (produce_source,))
    produce_order_items = cursor.fetchall()

    cursor.close()
    # print("DEBUG: produce_order =", produce_order)  # Debugging output
    # print("DEBUG: produce_order_items =", produce_order_items)  # Debugging output
    return render_template('produce_order_print.html', produce_order=produce_order, produce_order_items=produce_order_items,qr_code=qr_base64)

#dynamically generate product_source
@app.route('/generate_produce_source', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def generate_produce_source():
    produce_date = request.args.get('produce_date')
    if not produce_date:
        return jsonify({'error': 'Date is required'}), 400

    # Generate the produce_source based on the selected date
    today = datetime.strptime(produce_date, '%Y-%m-%d')
    date_str = today.strftime('%Y%m%d')  # Format as YYYYMMDD

    cursor = mysql.connection.cursor()

    # Find the most recent produce_source for today to get the serial number
    cursor.execute('''
        SELECT produce_source FROM produce WHERE produce_source LIKE %s ORDER BY produce_source DESC LIMIT 1
    ''', (f'BCH{date_str}%',))
    result = cursor.fetchone()

    if result:
        # Extract the last serial number (e.g., BCH20250401-002), increment it
        last_produce_source = result[0]
        serial_number = int(last_produce_source[-3:]) + 1  # Increment the last serial number
    else:
        # If no previous produce_source exists, start from 001
        serial_number = 1

    # Generate the new produce_source
    produce_source = f"BCH{date_str}-{serial_number:03d}"  # Format as BCHYYYYMMDD-XXX

    return jsonify({'produce_source': produce_source})

#搜索查看生产单
@app.route('/produce_search', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def produce_search():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM produce")
    produce_list = cursor.fetchall()
    cursor.close()
    return render_template('produce_search.html', produce_list=produce_list)

@app.route('/view_produce_order', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def view_produce_order():
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
                    SELECT 
                        p.produce_source,
                        p.production_date,
                        p.product_name,
                        p.product_sku,
                        p.sale_id,
                        p.plan_quantity,
                        p.user_name
                    FROM 
                        produce p;
                   """)
    produce_data = cursor.fetchall()
    cursor.close() 
    return render_template('view_produce_order.html', produce = produce_data)

#销售单表
@app.route('/sale_order', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase')
def sale_order():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    sale_id = ""  # Default empty sale_id

    if request.method == 'POST':
        # Get user-inputted sale_date
        sale_date = request.form.get('sale_date')

        try:
            # Convert user input date to extract year and month
            sale_date_obj = datetime.strptime(sale_date, "%Y-%m-%d")
            year = sale_date_obj.year
            month = f"{sale_date_obj.month:02d}"  # Ensure two-digit month format
            day = f"{sale_date_obj.day:02d}"
        except ValueError:
            flash('Invalid date format! Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('sale_order'))

        # Generate the sale_id based on user-inputted date
        cursor.execute(
            "SELECT sale_id FROM sale WHERE sale_id LIKE %s ORDER BY sale_id DESC LIMIT 1",
            (f"PO{year}{month}%",)
        )
        last_sale = cursor.fetchone()

        if last_sale:
            last_number = int(last_sale['sale_id'][-3:])  # Extract last 3 digits
            new_number = f"{last_number + 1:03d}"  # Increment and keep 3-digit format
        else:
            new_number = "001"  # Start from 001 if no sales exist for that month

        sale_id = f"PO{year}{month}{day}{new_number}"  # Construct sale_id

        # Get other form data
        client = request.form.get('client')
        rep = request.form.get('rep') or "" # Selected sales representative
        delivery_way = request.form.get('delivery_way')
        invoice = request.form.get('invoice') or ""
        user_name = current_user.username
        delivery_fee = request.form.get('delivery_fee')
        tax = request.form.get('tax') or "0.00"
        tax_rate = request.form.get('tax_rate') or "0.00"
        grand_total = request.form.get('grand_total_tax') or "0.00"  # Default to 0.00 if empty
        amount_received="0.00"
        # Validate required fields
        if not all([sale_id, sale_date, client, rep, delivery_way, user_name]):
            flash('Missing required fields. Please fill out all fields.', 'danger')
            return redirect(url_for('sale_order'))

        # Insert into 'sale' table
        try:
            cursor.execute('''
                INSERT INTO sale (sale_id, sale_date, client, rep, delivery_way, invoice, user_name, grand_total,amount_received,delivery_fee,tax,tax_rate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', 
                (sale_id, sale_date, client, rep, delivery_way, invoice, user_name, grand_total,amount_received,delivery_fee,tax,tax_rate))
            #mysql.connection.commit()
            #cursor.close()
        except Exception as e:
            print(f"Error inserting into sale table: {e}")
            flash(f"Error inserting into sale table: {e}", 'danger')
            return redirect(url_for('sale_order'))

        
        # Get product data
        product_names = request.form.getlist('product_name[]')
        product_skus = request.form.getlist('product_sku[]')
        unit_prices = request.form.getlist('unit_price[]')
        quantities = request.form.getlist('quantity[]')
        #delivery_fees = request.form.getlist('delivery_fee[]')
        total_prices = request.form.getlist('price[]')
        notes = request.form.getlist('note[]') or []

        # Insert data into 'sale_order' table
        for i in range(len(product_skus)):
            if product_skus[i] and product_names[i] and quantities[i]:  # Ensure mandatory fields are filled
                unit_price = float(unit_prices[i])
                quantity = int(quantities[i])
                #delivery_fee = float(delivery_fees[i] )
                calculated_price = unit_price * quantity

                cursor.execute('''
                    INSERT INTO sale_order (sale_id, product_sku, product_name, unit_price, quantity, price, note)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (sale_id, product_skus[i], product_names[i], unit_price, quantity, calculated_price, notes[i]))

        mysql.connection.commit()
        cursor.close()

        flash(f'Sale Order {sale_id} added successfully!', 'success')
        return redirect(url_for('view_sale', sale_id=sale_id))

    # Fetch product list for dropdown selection
    cursor.execute("SELECT item, sku FROM products")
    products = cursor.fetchall()

    # Fetch sales representatives from sales_list table
    cursor.execute("SELECT sales_name FROM sales_list")
    sales_reps = [row['sales_name'] for row in cursor.fetchall()]
    cursor.close()

    return render_template('sale_order.html', sale_id=sale_id, products=products, sales_reps=sales_reps)

# generate sale id
@app.route('/generate_sale_id/<int:year>/<string:month>/<int:day>', methods=['GET'])
@login_required
def generate_sale_id(year, month, day):
    cursor = mysql.connection.cursor()
    
    # Format the date string with the year, month, and day
    date_str = f"{year}{month.zfill(2)}{day:02d}"
    
    # Fetch the last sale_id for the given year, month, and day
    cursor.execute("SELECT sale_id FROM sale WHERE sale_id LIKE %s ORDER BY sale_id DESC LIMIT 1", (f'PO{date_str}%',))
    result = cursor.fetchone()
    
    # If no sale record is found, start from '001'
    if result:
        # Extract the last 3 digits from the sale_id and increment it
        last_po_number = result[0]
        serial_number = int(last_po_number[-3:]) + 1  # Increment and format it as 3 digits
    else:
        # If no sales exist for that day, start from '001'
        serial_number = 1

    # Construct the new sale_id including day info
    sale_id = f"PO{date_str}{serial_number:03d}"  # POYYYYMMDDNNN (e.g., PO20250409001)
    cursor.close()

    return jsonify({"sale_id": sale_id})  # Return the new sale_id as JSON

# 销售单查询
@app.route('/sale_search', methods=['GET'])
@login_required
@role_required('admin', 'purchase', 'general')
def sale_search():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Use dictionary cursor for easier templating
        cursor.execute("SELECT * FROM sale WHERE status = 0") #0: 未付款
        # Fetch all records from the sale table
        sales_data0 = cursor.fetchall()  # Retrieve all rows
        
        cursor.execute("SELECT * FROM sale WHERE status = 1") #1:已付款未出库
        # Fetch sale data that is 出库 from the sale table
        sales_data1 = cursor.fetchall()  # Retrieve all rows
        
        cursor.execute("SELECT * FROM sale WHERE status = 2") #2:已出库
        # Fetch sale data that is 出库 from the sale table
        sales_data2 = cursor.fetchall() 
        
        cursor.execute("SELECT * FROM sale WHERE status = 3") #3:已删除
        # Fetch sale data that is 出库 from the sale table
        sales_data3 = cursor.fetchall() 
        cursor.close()

        if not sales_data0:
            flash("No sales data found.", 'warning')  # Flash a warning message if no data is found

        return render_template('sale_search.html', sales0=sales_data0, sales1=sales_data1,sales2=sales_data2, sales3=sales_data3)  # Pass data to template
    except Exception as e:
        flash(f"Error fetching sales data: {e}", 'danger')  # Flash an error message in case of any exceptions
        return render_template('sale_search.html', sales=sales_data0)  # Render the template without data

# 进入销售单详情页
@app.route('/view_sale/<sale_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase', 'general')
def view_sale(sale_id):
    try:
        # Fetch sale data
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM sale WHERE sale_id = %s", (sale_id,))
        sale_data = cursor.fetchone()

        if not sale_data:
            flash("Sale not found.", 'warning')
            return redirect(url_for('sale_search'))  # Redirect if no sale found

        # Fetch sale order data
        
        cursor.execute("SELECT * FROM sale_order WHERE sale_id = %s", (sale_id,))
        sale_order_data = cursor.fetchall()  # Get all sale order items related to this sale
        invoice_number = sale_data['invoice']
        cursor.execute("SELECT * FROM payments WHERE invoice = %s", (invoice_number,))
        payment_data = cursor.fetchall()
        
        cursor.close()

        return render_template('view_sale.html', sale=sale_data, sale_order_items=sale_order_data, payments=payment_data)

    except Exception as e:
        flash(f"Error fetching sales data: {e}", 'danger')
        return redirect(url_for('sale_search'))

#delete sale order
@app.route('/delete_sale/<sale_id>', methods=['POST'])
@login_required
@role_required('admin', 'purchase')  # Only admin/purchase can delete
def delete_sale(sale_id):
    try:
        cursor = mysql.connection.cursor()

        # First check if the sale exists
        cursor.execute("SELECT * FROM sale WHERE sale_id = %s", (sale_id,))
        sale = cursor.fetchone()

        if not sale:
            flash("销售单未找到。", "danger")
            return redirect(url_for('sale_search'))

        # Soft delete the sale
        cursor.execute("UPDATE sale SET status = 3 WHERE sale_id = %s", (sale_id,))

        # Also soft delete related sale_order rows
        cursor.execute("UPDATE sale_order SET status = 3 WHERE sale_id = %s", (sale_id,))

        mysql.connection.commit()
        cursor.close()
        flash("销售单及相关内容已标记为已删除。", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"删除销售单时发生错误: {e}", "danger")

    return redirect(url_for('sale_search'))

#恢复已删除销售单
@app.route('/restore_sale/<sale_id>', methods=['POST'])
@login_required
@role_required('admin', 'purchase')
def restore_sale(sale_id):
    try:
        cursor = mysql.connection.cursor()
        
        # Update status to 0 for the sale
        cursor.execute("UPDATE sale SET status = 0 WHERE sale_id = %s", (sale_id,))
        
        # Also update related sale order items' status to 0
        cursor.execute("UPDATE sale_order SET status = 0 WHERE sale_id = %s", (sale_id,))

        mysql.connection.commit()
        cursor.close()

        flash("销售单已恢复。", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"恢复销售单时发生错误: {e}", "danger")

    return redirect(url_for('sale_search'))

#已收款按钮确认并更改sale里订单状态到paid
@app.route('/mark_sale_paid/<sale_id>', methods=['POST'])
@login_required
def mark_sale_paid(sale_id):
    try:
        cursor = mysql.connection.cursor()

        # Update sale status to 1 (已收款)
        cursor.execute("UPDATE sale SET status = 1 WHERE sale_id = %s", (sale_id,))

        # Update related sale_order status to 1
        cursor.execute("UPDATE sale_order SET status = 1 WHERE sale_id = %s", (sale_id,))

        cursor.execute("SELECT * FROM sale WHERE sale_id = %s", (sale_id,))
        sale_data = cursor.fetchone()

        # Fetch related sale_order data to pass to inventory_out page
        cursor.execute("SELECT * FROM sale_order WHERE sale_id = %s", (sale_id,))
        sale_order_data = cursor.fetchall()
        
        mysql.connection.commit()
        cursor.close()

        flash("销售单状态已更新为 '已收款'。", "success")
        return redirect(url_for('view_sale', sale_id=sale_id))

    except Exception as e:
        mysql.connection.rollback()
        flash(f"更新状态失败: {e}", "danger")
        return redirect(url_for('view_sale', sale_id=sale_id))

#出库按钮确认出库并更改sale里订单状态到出库 0：未收款未出库 1：已收款未出库 2：已收款已出库 3：已删除
@app.route('/mark_inventory_out/<sale_id>', methods=['POST'])
@login_required
def mark_inventory_out(sale_id):
    try:
        cursor = mysql.connection.cursor()

        # Update sale status to 2 (已收款)
        cursor.execute("UPDATE sale SET status = 2 WHERE sale_id = %s", (sale_id,))

        # Update related sale_order status to 1
        cursor.execute("UPDATE sale_order SET status = 2 WHERE sale_id = %s", (sale_id,))

        cursor.execute("SELECT * FROM sale WHERE sale_id = %s", (sale_id,))
        sale_data = cursor.fetchone()

        # Fetch related sale_order data to pass to inventory_out page
        cursor.execute("SELECT * FROM sale_order WHERE sale_id = %s", (sale_id,))
        sale_order_data = cursor.fetchall()
        
        mysql.connection.commit()
        cursor.close()

        flash(f"销售单:{sale_id} 状态已更新为 '已出库'。", "success")
        return redirect(url_for(f'inventory_out', sale_id=sale_id))

    except Exception as e:
        mysql.connection.rollback()
        flash(f"更新状态失败: {e}", "danger")
        return redirect(url_for('view_sale', sale_id=sale_id))
    
# 修改销售单
@app.route('/edit_sale/<sale_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase', 'general')
def edit_sale(sale_id):
    try:
        # Fetch sale data
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM sale WHERE sale_id = %s", (sale_id,))
        sale_data = cursor.fetchone()

         # Fetch all products from the products table
        cursor.execute('''SELECT item, sku FROM products''')
        products = cursor.fetchall()
        cursor.execute("SELECT sales_name FROM sales_list")
        sales_reps = [row['sales_name'] for row in cursor.fetchall()]

        if not sale_data:
            flash("Sale not found.", 'warning')
            return redirect(url_for('sale_search'))  # Redirect if no sale found

        # Fetch sale order data
        cursor.execute("SELECT * FROM sale_order WHERE sale_id = %s", (sale_id,))
        sale_order_data = cursor.fetchall()  # Get all sale order items related to this sale
        # Fetch invoice number of this sale data
        invoice_number = sale_data['invoice']
        cursor.execute("SELECT * FROM payments WHERE invoice = %s", (invoice_number,))
        payment_data = cursor.fetchall()

        cursor.close()
        # Handle POST request to update sale order
        if request.method == 'POST':
            # Update sale data
            sale_id = request.form.get('sale_id')
            sale_date = request.form.get('sale_date')
            client = request.form.get('client')
            rep = request.form.get('rep')
            delivery_way = request.form.get('delivery_way')
            invoice = request.form.get('invoice') or ""
            user_name = request.form.get('user_name')
            delivery_fee = request.form.get('delivery_fee') or "0.00"
            tax = request.form.get('tax') or "0.00"
            tax_rate = request.form.get('tax_rate') or "0.00"
            grand_total = request.form.get('grand_total_tax') or "0.00"
             # Default to 0.00 if empty
            amount_received=request.form.get('amount_received') or "0.00"
            # Validate required fields
            if not all([sale_id, sale_date, client, rep, delivery_way, user_name]):
                flash('Missing required fields. Please fill out all fields.', 'danger')
                return redirect(url_for('edit_sale', sale_id=sale_id))  # Redirect back if validation fails

            cursor = mysql.connection.cursor()
            cursor.execute('''
                UPDATE sale 
                SET client=%s, rep=%s, delivery_way=%s, invoice=%s, user_name=%s, grand_total=%s, amount_received=%s, delivery_fee = %s, tax = %s, tax_rate = %s
                WHERE sale_id=%s
                ''', (
                    client, rep, delivery_way, invoice, user_name, grand_total, amount_received, delivery_fee,tax,tax_rate, sale_id
                ))
            
            # Update sale order data
            product_skus = request.form.getlist('product_sku[]')
            product_names = request.form.getlist('product_name[]')
            unit_prices = request.form.getlist('unit_price[]')
            quantities = request.form.getlist('quantity[]')
            prices = request.form.getlist('price[]')
            #delivery_fees = request.form.getlist('delivery_fee[]')
            notes = request.form.getlist('note[]')

            # Validate product data consistency
            if not (len(product_skus) == len(product_names) == len(unit_prices) == len(quantities) == len(prices) == len(notes)):
                flash('Mismatch in product details. Please check the input.', 'danger')
                return redirect(url_for('edit_sale', sale_id=sale_id))
            # Update each sale order item
            # First, delete existing sale order items for the current sale_id
            cursor.execute("DELETE FROM sale_order WHERE sale_id = %s", (sale_id,))

            # Then, reinsert all items from the form
            for i in range(len(product_skus)):
                cursor.execute('''
                INSERT INTO sale_order (sale_id, product_sku, product_name, unit_price, quantity, price, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    sale_id,
                    product_skus[i],
                    product_names[i],
                    unit_prices[i],
                    quantities[i],
                    prices[i],
                    notes[i]
                )) 
            # Update payment data
            payment_dates = request.form.getlist('payment_date[]')
            payment_amounts = request.form.getlist('payment_amount[]')
            payment_methods = request.form.getlist('payment_method[]')

            # Validate payment data consistency
            if not (len(payment_dates) == len(payment_amounts) == len(payment_methods)):
                flash('Mismatch in payment details. Please check the input.', 'danger')
                return redirect(url_for('edit_sale', sale_id=sale_id))

            # Delete existing payments with the same invoice
            cursor.execute("DELETE FROM payments WHERE invoice = %s", (invoice,))
            # Insert new payment records from the form
            for i in range(len(payment_dates)):
                cursor.execute(
                    '''INSERT INTO payments (invoice, payment_date, amount, payment_method)
                    VALUES (%s, %s, %s, %s)''',
                    (invoice, payment_dates[i], payment_amounts[i], payment_methods[i])
                )
            mysql.connection.commit()
            cursor.close()
            return redirect(url_for('view_sale', sale_id=sale_id))  # Redirect to sale search after successful update
        
        
        return render_template('edit_sale.html', payments=payment_data, sales_reps=sales_reps, products=products, sale=sale_data, sale_order_items=sale_order_data)

    except Exception as e:
        flash(f"Error fetching sales data: {e}", 'danger')
        return redirect(url_for('sale_search'))  # Redirect on error

# Download sale orders based on given date
@app.route('/download_sale_orders')
@login_required
def download_sale_orders():
    cur = mysql.connection.cursor()
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = """
        SELECT 
            s.sale_id,
            s.sale_date,
            s.client,
            s.rep,
            s.delivery_way,
            s.invoice,
            s.grand_total,
            s.amount_received,
            s.amount_remained,
            s.tax,
            s.tax_rate,
            s.delivery_fee,
            s.user_name,
            s.status AS sale_status,
            so.product_sku,
            so.product_name,
            so.unit_price,
            so.quantity,
            so.price,
            so.note,
            so.status AS order_status
        FROM sale_order so
        JOIN sale s ON so.sale_id = s.sale_id
        WHERE s.sale_date BETWEEN %s AND %s
        ORDER BY s.sale_id, so.product_sku
    """
    param = [start_date, end_date]
    cur.execute(query, param)
    result = cur.fetchall()
    cur.close()

    # Define the column headers
    columns = [
        '销售单号', '销售日期', '客户名', '销售代表', '配送方式', '发票号',
        '订单总额', '已收金额', '剩余应收', '税费', '税率', '运费',
        '操作员', '销售状态', '产品SKU', '产品名称', '单价', '数量', '小计', '备注', '订单状态'
    ]

    # Convert to DataFrame
    df = pd.DataFrame(result, columns=columns)

    # Save to Excel
    excel_file_path = '/tmp/sale_orders_data.xlsx'
    df.to_excel(excel_file_path, index=False)

    return send_file(excel_file_path, as_attachment=True, download_name='sale_orders_data.xlsx')

# 入库单
@app.route('/inventory_in', methods=['GET', 'POST'])
@app.route('/inventory_in/purchase/<purchase_id>', methods=['GET', 'POST'])
@app.route('/inventory_in/production/<produce_id>', methods=['GET', 'POST'])
@app.route('/inventory_in/exchange_return/<exchange_return_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase')
def inventory_in(produce_id=None, purchase_id=None, exchange_return_id=None):
    today = datetime.today().strftime('%Y-%m-%d')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    inventory_in_id = ""  # Default empty inventory_in_id
    exchange_return_id = str(exchange_return_id)
    # Fetch all products from the products table
    cursor.execute('''SELECT item, sku FROM products''')
    products = cursor.fetchall()  # List of tuples [(product_name1, sku1), (product_name2, sku2), ...]
    # Example field to autofill
    if produce_id:
        cursor.execute('''SELECT * FROM produce WHERE produce_id = %s''', (produce_id,))
        produce_data = cursor.fetchone()
    else:
        produce_data = None
    
    if purchase_id:
        cursor.execute('''SELECT * FROM purchase_order WHERE purchase_id = %s''', (purchase_id,))
        purchase_data = cursor.fetchall()
        cursor.execute('''SELECT invoice FROM purchase WHERE purchase_id = %s''', (purchase_id,))
        purchase_data2 = cursor.fetchone()
        print("DEBUG: purchase data type: ", type(purchase_data))
    else:
        purchase_data = None
        purchase_data2 = None

    if exchange_return_id != None:
        cursor.execute('''SELECT * FROM exchange_return WHERE exchange_return_id = %s''', (exchange_return_id,))
        exchange_return_data1 = cursor.fetchone()
        cursor.execute('''SELECT * FROM exchange_return_order WHERE exchange_return_id = %s''', (exchange_return_id,))
        exchange_return_data2 = cursor.fetchall()
    else:
        exchange_return_data = None
    
    if request.method == 'POST':
        try:
            # Get form data
            date = request.form.get('date')
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                year = date_obj.year
                month = f"{date_obj.month:02d}"  # Two-digit month
                day = f"{date_obj.day:02d}"      # Two-digit day
            except ValueError:
                flash("Invalid date format! Please use YYYY-MM-DD.", "danger")
                return redirect(url_for('inventory_in'))

            # Generate inventory_in_id like IN20250404001 (with day included)
            prefix = f"IN{year}{month}{day}"
            cursor.execute(
                "SELECT inventory_in_id FROM inventory_in WHERE inventory_in_id LIKE %s ORDER BY inventory_in_id DESC LIMIT 1",
                (f"{prefix}%",)
            )
            last_entry = cursor.fetchone()

            if last_entry:
                last_number = int(last_entry['inventory_in_id'][-3:])
                new_number = f"{last_number + 1:03d}"
            else:
                new_number = "001"

            inventory_in_id = f"{prefix}{new_number}"

            # Get other form data
            in_type = request.form.get('in_type')  # 入库类型
            corresponding_order = request.form.get('corresponding_order')  # 对应单号/发票号
            user_name = request.form.get('user_name')  # 操作员
            corresponding_order = corresponding_order.replace(" ", "")
            if in_type == 'produce':
                cursor.execute('''
                    UPDATE produce
                    SET status = 1
                    WHERE produce_source = %s
            ''', (corresponding_order,))
            
            # Check if required fields are missing
            if not all([inventory_in_id, in_type, date, corresponding_order, user_name]):
                flash("All fields are required!", "danger")
                return redirect(url_for('inventory_in'))

            # Insert into 'inventory_in' table
            cursor.execute(''' 
                INSERT INTO inventory_in (inventory_in_id, in_type, date, corresponding_order, user_name)
                VALUES (%s, %s, %s, %s, %s)
            ''', (inventory_in_id, in_type, date, corresponding_order, user_name))
            
            # Insert into 'inventory_in_order' table
            product_skus = request.form.getlist('product_sku[]')  # List of SKU values
            # product_names = request.form.getlist('product_name[]')  # List of product names
            ideal_quantities = [int(q) for q in request.form.getlist('ideal_quantity[]')]
            true_quantities = [int(q) for q in request.form.getlist('true_quantity[]')]
            diffs = [int(q) for q in request.form.getlist('diff[]')]
            source_ids = request.form.getlist('source_id[]')

            # Based on sku find corresponding product name
            product_names = []
            for i in range(len(product_skus)):
                sku = product_skus[i]
                # Find the corresponding product_name by matching SKU
                product_name = None
                for product in products:
                    if product['sku'] == sku:
                        product_name = product['item']
                        product_names.append(product_name)
                        break
            
            # Check the data length
            if len(product_skus) != len(product_names) or len(product_skus) != len(ideal_quantities):
                return "Error: Inconsistent form data"

            for i in range(len(product_skus)):
                cursor.execute('''
                    INSERT INTO inventory_in_order 
                    (inventory_in_id, product_sku, product_name, ideal_quantity, true_quantity, diff, source_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (inventory_in_id, product_skus[i], product_names[i], 
                      ideal_quantities[i], true_quantities[i], diffs[i], source_ids[i]))
                cursor.execute('''
                    INSERT INTO source_track 
                    (source_id, product_sku, quantity, date)
                    VALUES (%s, %s, %s, %s)
                ''', (source_ids[i], product_skus[i], true_quantities[i], date))
            
            # Commit after loop finishes
            mysql.connection.commit()

            cursor.close()
            flash(f'Inventory record {inventory_in_id} added successfully!', 'success')
            return redirect(url_for('inventory_in_print', inventory_in_id=inventory_in_id))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {str(e)}", "danger")
            print(f"Exception: {str(e)}") 
            return redirect(url_for('inventory_in'))
             
    return render_template('inventory_in.html', inventory_in_id=inventory_in_id,
                           today=today, products=products,
                           produce_data=produce_data,
                           purchase_data=purchase_data,
                           purchase_data2=purchase_data2,
                           exchange_return_data1=exchange_return_data1,
                           exchange_return_data2 = exchange_return_data2)

@app.route('/download_inventory_in')
@login_required
def download_inventory_in():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cur = mysql.connection.cursor()
    query = '''
        SELECT i.date, i.in_type, o.product_sku, o.product_name, o.true_quantity, o.source_id,
                 i.inventory_in_id, i.corresponding_order, o.ideal_quantity, o.diff, o.notes, i.user_name
        FROM inventory_in i
        JOIN inventory_in_order o ON i.inventory_in_id = o.inventory_in_id
        WHERE i.date BETWEEN %s AND %s
        ORDER BY i.date DESC
    '''
    cur.execute(query, (start_date, end_date))
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data, columns=[
         '入库日期', '入库类型', '产品sku', '产品名称', '实际入库数量', '溯源码', 
         '入库单号','对应生产单号/发票号', '计划入库数量', '差额', '备注', '操作人'
    ])
    path = '/tmp/inventory_in_data.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True, download_name='inventory_in_data.xlsx')

# generate inventory in id: in + date + batchnumber
@app.route('/generate_inventory_in_id/<int:year>/<string:month>/<int:day>', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def generate_inventory_in_id(year, month, day):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    date_str = f"{year}{str(month).zfill(2)}{str(day).zfill(2)}"
    
    # Fetch the last inventory_in_id for the given year, month, and day
    cursor.execute(
        "SELECT inventory_in_id FROM inventory_in WHERE inventory_in_id LIKE %s ORDER BY inventory_in_id DESC LIMIT 1",
        (f'IN{date_str}%',)
    )
    result = cursor.fetchone()
    print(f'IN{date_str}%')
    print(f"Fetched result: {result}")
    
    # Determine the next serial number
    if result:
        last_in_number = result['inventory_in_id']
        serial_number = int(last_in_number[-3:]) + 1
    else:
        serial_number = 1
    

    inventory_in_id = f"IN{date_str}{serial_number:03d}"
    cursor.close()

    return jsonify(inventory_in_id=inventory_in_id)

@app.route('/inventory_in/print/<inventory_in_id>')
@login_required
@role_required('admin', 'purchase')
def inventory_in_print(inventory_in_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch inventory_in main record
    cursor.execute('''
        SELECT * FROM inventory_in WHERE inventory_in_id = %s
    ''', (inventory_in_id,))
    inventory_in = cursor.fetchone()

    # Fetch related inventory_in_order records
    cursor.execute('''
        SELECT * FROM inventory_in_order WHERE inventory_in_id = %s
    ''', (inventory_in_id,))
    items = cursor.fetchall()

    cursor.close()

    if not inventory_in:
        flash("Inventory record not found.", "danger")
        return redirect(url_for('inventory_in'))

    # Generate QR codes for each source_id
    for item in items:
        source_id = item['source_id']
        img = qrcode.make(source_id)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        item['qr_code'] = f"data:image/png;base64,{qr_base64}"
    
    # Render template as HTML
    rendered = render_template('inventory_in_print.html', inventory_in=inventory_in, items=items)

    return rendered  # For now, just render the HTML to the browser

@app.route('/view_inventory_in', methods=['GET'])
@login_required
@role_required('admin','purchase')
def view_inventory_in():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM inventory_in")
    inventory_in_list = cursor.fetchall()
    cursor.close()
    return render_template('view_inventory_in.html', inventory_in_list=inventory_in_list)

@app.route('/view_inventory_in_order/<inventory_in_id>', methods=['GET'])
@login_required
@role_required('admin','purchase')
def view_inventory_in_order(inventory_in_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM inventory_in_order WHERE inventory_in_id = %s", (inventory_in_id,))
    order_items = cursor.fetchall()
    cursor.close()
    return render_template('view_inventory_in_order.html', inventory_in_id=inventory_in_id, order_items=order_items)

# generate inventory out id: out + date + batchnumber
@app.route('/generate_inventory_out_id/<int:year>/<string:month>/<int:day>', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def generate_inventory_out_id(year, month, day):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    date_str = f"{year}{str(month).zfill(2)}{str(day).zfill(2)}"  # Format YYYYMMDD
    
    # Fetch the last inventory_out_id for the given year, month, and day
    cursor.execute(
        "SELECT inventory_out_id FROM inventory_out WHERE inventory_out_id LIKE %s ORDER BY inventory_out_id DESC LIMIT 1",
        (f'OUT{date_str}%',)
    )
    result = cursor.fetchone()
    
    # Determine the next serial number
    if result:
        last_out_number = result['inventory_out_id']
        serial_number = int(last_out_number[-3:]) + 1  # Increment last 3 digits
    else:
        serial_number = 1

    # Construct the new inventory_out_id
    inventory_out_id = f"OUT{date_str}{serial_number:03d}"
    cursor.close()

    return jsonify(inventory_out_id=inventory_out_id)

@app.route('/inventory_out_print/<inventory_out_id>')
@login_required
@role_required('admin', 'purchase')
def inventory_out_print(inventory_out_id):
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch inventory_out main record
    cursor.execute('''
        SELECT * FROM inventory_out WHERE inventory_out_id = %s
    ''', (inventory_out_id,))
    inventory_out = cursor.fetchone()

    # Fetch related inventory_out_order records
    cursor.execute('''
        SELECT * FROM inventory_out_order WHERE inventory_out_id = %s
    ''', (inventory_out_id,))
    items = cursor.fetchall()

    # Fetch related inventory_out_order records
    cursor.execute('''
        SELECT item, sku FROM products
    ''')
    products = cursor.fetchall()
    products_dict = {product['sku']: product['item'] for product in products}
    cursor.close()

    if not inventory_out:
        flash("Inventory record not found.", "danger")
        return redirect(url_for('inventory_out'))

    # Generate QR codes for each source_id
    for item in items:
        source_id = item['source_id']
        img = qrcode.make(source_id)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        item['qr_code'] = f"data:image/png;base64,{qr_base64}"
    
    # Render template as HTML
    rendered = render_template('inventory_out_print.html', inventory_out=inventory_out, items=items, products=products_dict)

    return rendered  # For now, just render the HTML to the browser

# 溯源二维码
@app.route('/generate_qrcode/<source_id>')
@login_required
@role_required('admin', 'purchase')
def generate_qrcode(source_id):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(source_id)
        qr.make(fit=True)
        print(type(source_id))
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return send_file(buffer, mimetype='image/png')

    except Exception as e:
        print(f"QR code generation failed for {source_id}: {e}")
        return abort(500)

# 出库单
@app.route('/inventory_out', methods=['GET', 'POST'])
@app.route('/inventory_out/<sale_id>', methods=['GET', 'POST'])
@app.route('/inventory_out/produce/<id>', methods=['GET', 'POST'],endpoint='inventory_out_produce')
@login_required
@role_required('admin', 'purchase')
def inventory_out(sale_id=None, id=None):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    inventory_out_id = ""  # Default empty inventory_out_id
    # Fetch all products from the products table
    cursor.execute('''SELECT item, sku FROM products''')
    products = cursor.fetchall() 
    if sale_id:
    # Query sale data based on sale_id
        cursor.execute("SELECT * FROM sale WHERE sale_id = %s", (sale_id,))
        sale_data = cursor.fetchone()
    # Query sale order data based on sale_id
        cursor.execute("SELECT * FROM sale_order WHERE sale_id = %s", (sale_id,))
        sale_order_data = cursor.fetchall()
    else:
        sale_data=None
        sale_order_data=None

    if id:
        #print('id!')
        #print(id)
        cursor.execute("SELECT * FROM produce WHERE produce_source = %s", (id,))
        produce_source_data = cursor.fetchone()
        cursor.execute("SELECT * FROM produce_order WHERE produce_source = %s", (id,))
        produce_data = cursor.fetchall()
    else:
        produce_data=None
        produce_source_data=None
    #print(produce_data)
    today_date = datetime.today().strftime('%Y-%m-%d')
    #produce_order_source=id

    if request.method == 'POST':
        # Get form data for inventory_out
        date = request.form['date']

        try:
            date_obj = datetime.strptime(today_date, "%Y-%m-%d")
            year = date_obj.year
            month = f"{date_obj.month:02d}"
            day = f"{date_obj.day:02d}"
        except ValueError:
            flash("Invalid date format! Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('inventory_out', sale_id=sale_id))
        
        # Generate inventory_out_id like OUT202504001
        cursor.execute(
            "SELECT inventory_out_id FROM inventory_out WHERE inventory_out_id LIKE %s ORDER BY inventory_out_id DESC LIMIT 1",
            (f"OUT{year}{month}{day}%",)
        )
        last_entry = cursor.fetchone()

        if last_entry:
            last_number = int(last_entry['inventory_out_id'][-3:])
            new_number = f"{last_number + 1:03d}"
        else:
            new_number = "001"

        inventory_out_id = f"OUT{year}{month}{day}{new_number}"
        corresponding_order = request.form['corresponding_order']
        invoice = request.form['invoice']
        client = request.form['client']
        delivery_way = request.form['delivery_way']
        user_name = request.form['user_name']

        # Insert data into 'inventory_out' table
        cursor.execute(''' 
            INSERT INTO inventory_out (inventory_out_id, date, corresponding_order, invoice, client, delivery_way, user_name) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (inventory_out_id, date, corresponding_order, invoice, client, delivery_way, user_name))
        
        # Process the order items and track inventory changes
        product_skus = request.form.getlist('product_sku[]')
        ideal_quantities = request.form.getlist('ideal_quantity[]')
        true_quantities = request.form.getlist('true_quantity[]')
        notes = request.form.getlist('note[]')

        for i in range(len(product_skus)):
            product_sku = product_skus[i]
            ideal_total_quantity = ideal_quantities[i]
            true_quantity = true_quantities[i]
            note = notes[i]
            product_ids = request.form.getlist(f'source_id[{product_sku}][]')
            product_qtys = request.form.getlist(f'source_qty[{product_sku}][]')

            for j in range(len(product_ids)):
                source_id = product_ids[j]
                source_qty = int(product_qtys[j])

                # Insert into inventory_out_order
                cursor.execute(''' 
                    INSERT INTO inventory_out_order 
                    (inventory_out_id, product_sku, ideal_total_quantity, true_quantity, note, source_id) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (inventory_out_id, product_sku, ideal_total_quantity, source_qty, note, source_id))

                # Update source_track table
                cursor.execute(''' 
                    UPDATE source_track 
                    SET quantity = quantity - %s 
                    WHERE source_id = %s AND quantity >= %s 
                ''', (source_qty, source_id, source_qty))

        if corresponding_order and corresponding_order!='none':
            #print('corresponding_order')
            #print(corresponding_order)
            cursor.execute('''UPDATE sale SET status = 2 WHERE sale_id = %s''', (corresponding_order,))
        
        # Update related sale_order status to 1
            cursor.execute('''UPDATE sale_order SET status = 2 WHERE sale_id = %s''', (corresponding_order,))
            flash(f'出库单 {inventory_out_id} 已经成功添加!', 'success')
            flash(f"销售单:{corresponding_order} 状态已更新为 '已出库'。", "success")
        #print("produce_data: ")
        produce_data = request.form['corresponding_order']
        #print(produce_data)
        if produce_data:
            #print("produce_data: ")
            #print(produce_data['produce_source'])
            cursor.execute('''UPDATE produce SET status2 = 1 WHERE produce_source = %s''', (produce_data,))
        
        mysql.connection.commit()
        cursor.close()
       
        
        # Redirect to the inventory_out_print
        return redirect(url_for('inventory_out_print', inventory_out_id=inventory_out_id, sale_id=sale_id))

    return render_template('inventory_out.html', produce_source_data=produce_source_data, today_date=today_date, inventory_out_id=inventory_out_id, 
                           products=products, sale_id=sale_id, sale_data=sale_data, sale_order_data=sale_order_data,produce_data=produce_data)

@app.route('/download_inventory_out')
@login_required
def download_inventory_out():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cur = mysql.connection.cursor()
    query = '''
    SELECT o.date, o.client, oo.product_sku, p.item AS product_name, oo.true_quantity, oo.source_id, 
        o.inventory_out_id,  o.corresponding_order, o.invoice, o.delivery_way,
        oo.ideal_total_quantity, oo.note, o.user_name
    FROM inventory_out o
    LEFT JOIN inventory_out_order oo ON o.inventory_out_id = oo.inventory_out_id
    LEFT JOIN products p ON oo.product_sku = p.sku
    WHERE o.date BETWEEN %s AND %s
    ORDER BY o.date DESC
    '''
    cur.execute(query, (start_date, end_date))
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data, columns=[
        '出库日期', '客户名', '产品sku', '产品名称', '实际出库数量', '溯源码', 
        '出库单号', '对应单号', '发票号', '配送方式', '计划出库数量', '备注', '操作人'
    ])
    path = '/tmp/inventory_out_data.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True, download_name='inventory_out_data.xlsx')

@app.route('/view_inventory_out', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def view_inventory_out():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM inventory_out")
    inventory_out_list = cursor.fetchall()
    cursor.close()
    return render_template('view_inventory_out.html', inventory_out_list=inventory_out_list)

@app.route('/view_inventory_out_order/<inventory_out_id>', methods=['GET'])
@login_required
@role_required('admin', 'purchase')
def view_inventory_out_order(inventory_out_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
            SELECT io.*, p.item as product_name 
            FROM inventory_out_order io
            JOIN products p ON io.product_sku = p.sku
            WHERE io.inventory_out_id = %s
        """, (inventory_out_id,))
    order_items = cursor.fetchall()
    cursor.close()
    return render_template('view_inventory_out_order.html', inventory_out_id=inventory_out_id, order_items=order_items)

# Function to update inventory dynamically using source_track table
def update_inventory_table():
    cur = mysql.connection.cursor()

    # Fetch total quantity per SKU and corresponding product name
    cur.execute("""
        SELECT 
            st.product_sku, 
            p.item, 
            SUM(st.quantity) AS total_quantity
        FROM source_track st
        JOIN products p ON st.product_sku = p.sku
        GROUP BY st.product_sku, p.item;
    """)
    inventory_data = cur.fetchall()

    try:
        for product in inventory_data:
            product_sku = product[0]
            product_name = product[1]
            total_quantity = product[2]

            # Check if the product already exists in inventory
            cur.execute("""
                SELECT quantity FROM inventory WHERE product_sku = %s
            """, (product_sku,))
            current_quantity = cur.fetchone()

            if current_quantity:
                # Update quantity and product_name in case it changed
                cur.execute("""
                    UPDATE inventory
                    SET quantity = %s, product_name = %s
                    WHERE product_sku = %s
                """, (total_quantity, product_name, product_sku))
            else:
                # Insert new entry with product_name and quantity
                cur.execute("""
                    INSERT INTO inventory (product_sku, product_name, quantity)
                    VALUES (%s, %s, %s)
                """, (product_sku, product_name, total_quantity))

        mysql.connection.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()

#FIFO Source Lookup API
@app.route('/get_fifo_sources/<string:product_sku>/<int:quantity>', methods=['GET'])
@login_required
def get_fifo_sources(product_sku,quantity):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check available inventory quantity for the SKU
    cursor.execute('''
        SELECT product_sku, quantity
        FROM inventory
        WHERE product_sku = %s
    ''', (product_sku,))
    product = cursor.fetchone()

    selected_sources = []
    selected_quantities = []

    if product and product['quantity'] < quantity:
        # Not enough inventory, but return all sources anyway
        cursor.execute('''
            SELECT source_id, quantity
            FROM source_track
            WHERE product_sku = %s AND status = 0
            ORDER BY date ASC
        ''', (product_sku,))
        
        for row in cursor.fetchall():
            selected_sources.append(row['source_id'])
            selected_quantities.append(row['quantity'])

        return jsonify({
            'status': 'error',
            'source_ids': selected_sources,
            'quantities': selected_quantities,
            'message': '库存不足'
        })
    else:
        # FIFO: get source_ids and their quantities until the requested quantity is fulfilled
        cursor.execute('''
            SELECT source_id, quantity
            FROM source_track
            WHERE product_sku = %s AND status = 0
            ORDER BY date ASC
        ''', (product_sku,))

        total = 0
        for row in cursor.fetchall():
            if total >= quantity:
                break

            remaining = quantity - total
            used_quantity = min(row['quantity'], remaining)
            total += used_quantity

            selected_sources.append(row['source_id'])
            selected_quantities.append(used_quantity)

        return jsonify({
            'status': 'success',
            'source_ids': selected_sources,
            'quantities': selected_quantities
        })

# 库存查询
@app.route('/inventory', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase', 'general')
def inventory():
    cursor = mysql.connection.cursor()
    update_inventory_table()
    cursor.execute("SELECT * FROM inventory")
    inventory_data = cursor.fetchall()
    #check source_track table 
    cursor.close() 
    return render_template('inventory.html', inventory=inventory_data)

# Download Inventory as Excel
@app.route('/download_inventory')
@login_required
def download_inventory():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM inventory ORDER BY product_sku")
    inventory_data = cur.fetchall()
    cur.close()

    # Convert data to DataFrame
    df = pd.DataFrame(inventory_data, columns=['product_sku', 'product_name', 'quantity'])

    # Save the DataFrame to an Excel file
    excel_file_path = '/tmp/inventory_data.xlsx'  # Temporary location
    df.to_excel(excel_file_path, index=False)

    # Send the file to the user for download
    return send_file(excel_file_path, as_attachment=True, download_name='inventory_data.xlsx')

# 盘点表
@app.route('/inventory_order', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase')
def inventory_order():
    cursor = mysql.connection.cursor()

    # Pull current inventory from source_track
    cursor.execute("""
        SELECT 
            st.product_sku, 
            p.item, 
            st.quantity,
            st.source_id
        FROM source_track st
        JOIN products p ON st.product_sku = p.sku
        WHERE st.quantity > 0
        ORDER BY st.product_sku, st.source_id
    """)
    source_track_data = cursor.fetchall()

    if request.method == 'POST':
        date = request.form['date']
        user_name = request.form['user_name']

        # Retrieve form data
        product_skus = request.form.getlist('product_sku[]')
        product_names = request.form.getlist('product_name[]')
        inventory_quantities = request.form.getlist('inventory_quantity[]')
        true_quantities = request.form.getlist('true_quantity[]')
        source_ids = request.form.getlist('source_id[]')
        notes = request.form.getlist('note[]')

        used_source_ids = set()
        
        for i in range(len(product_skus)):
            source_id = source_ids[i]
            old_qty = int(inventory_quantities[i])
            new_qty = int(true_quantities[i])
            diff = new_qty - old_qty
            note = notes[i]

            # Only insert header once per unique source_id
            if source_id not in used_source_ids:
                cursor.execute('''
                    INSERT INTO inventory_update (source_id, date, user_name)
                    VALUES (%s, %s, %s)
                ''', (source_id, date, user_name))
                used_source_ids.add(source_id)

            # Insert details into the inventory update order table
            cursor.execute('''
                INSERT INTO inventory_update_order (
                    source_id, product_sku, product_name,
                    inventory_quantity, true_quantity, diff, note
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                source_id, product_skus[i], product_names[i],
                old_qty, new_qty, diff, note
            ))

            # Update source_track table instead of inventory
            cursor.execute('''
                UPDATE source_track
                SET quantity = %s
                WHERE source_id = %s AND product_sku = %s
            ''', (new_qty, source_id, product_skus[i]))

        mysql.connection.commit()
        cursor.close()

        flash('盘点提交成功！', 'success')
        return redirect(url_for('inventory_order'))

    return render_template('inventory_order.html', source_track_data=source_track_data)

# 查看盘点记录
@app.route('/view_inventory_update', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def view_inventory_update():
    cursor = mysql.connection.cursor()
    
    cursor.execute("""
                   SELECT 
                        iuo.update_id,
                        u.date,
                        iuo.source_id,
                        iuo.product_sku,
                        iuo.product_name,
                        iuo.inventory_quantity,
                        iuo.true_quantity,
                        iuo.diff,
                        iuo.note,
                        u.user_name
                    FROM 
                        inventory_update_order iuo
                    JOIN 
                        inventory_update u
                    ON 
                        iuo.update_id = u.id;
                   """)
    inventory_update = cursor.fetchall()
    cursor.close() 
    return render_template('view_inventory_update.html', inventory=inventory_update)

@app.route('/download_inventory_update')
@login_required
def download_inventory_update():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cur = mysql.connection.cursor()
    query = '''
        SELECT u.id, u.source_id, u.date, u.user_name,
               o.product_sku, o.product_name, o.inventory_quantity, o.true_quantity, o.diff, o.note
        FROM inventory_update u
        JOIN inventory_update_order o ON u.id = o.update_id
        WHERE u.date BETWEEN %s AND %s
        ORDER BY u.date DESC
    '''
    cur.execute(query, (start_date, end_date))
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data, columns=[
        '盘点id', '溯源码', '盘点日期', '操作人',
        '产品sku', '产品名称', '系统库存数量', '实际盘点数量', '差额', '备注'
    ])
    path = '/tmp/inventory_update_data.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True, download_name='inventory_update_data.xlsx')

# 查看sold out盘点记录
@app.route('/view_inventory_sold_out', methods=['GET','POST'])
@login_required
@role_required('admin')
def view_inventory_sold_out():
    cursor = mysql.connection.cursor()

    # Pull current inventory from source_track
    cursor.execute("""
        SELECT 
            st.product_sku, 
            p.item, 
            st.quantity,
            st.source_id
        FROM source_track st
        JOIN products p ON st.product_sku = p.sku
        WHERE st.quantity <= 0
        ORDER BY st.product_sku, st.source_id
    """)
    source_track_data = cursor.fetchall()

    if request.method == 'POST':
        date = request.form['date']
        user_name = request.form['user_name']

        # Retrieve form data
        product_skus = request.form.getlist('product_sku[]')
        product_names = request.form.getlist('product_name[]')
        inventory_quantities = request.form.getlist('inventory_quantity[]')
        true_quantities = request.form.getlist('true_quantity[]')
        source_ids = request.form.getlist('source_id[]')
        notes = request.form.getlist('note[]')

        used_source_ids = set()
        
        for i in range(len(product_skus)):
            source_id = source_ids[i]
            old_qty = int(inventory_quantities[i])
            new_qty = int(true_quantities[i])
            diff = new_qty - old_qty
            note = notes[i]

            # Only insert header once per unique source_id
            if source_id not in used_source_ids:
                cursor.execute('''
                    INSERT INTO inventory_update (source_id, date, user_name)
                    VALUES (%s, %s, %s)
                ''', (source_id, date, user_name))
                used_source_ids.add(source_id)

            # Insert details into the inventory update order table
            cursor.execute('''
                INSERT INTO inventory_update_order (
                    source_id, product_sku, product_name,
                    inventory_quantity, true_quantity, diff, note
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                source_id, product_skus[i], product_names[i],
                old_qty, new_qty, diff, note
            ))

            # Update source_track table instead of inventory
            cursor.execute('''
                UPDATE source_track
                SET quantity = %s
                WHERE source_id = %s AND product_sku = %s
            ''', (new_qty, source_id, product_skus[i]))

        mysql.connection.commit()
        cursor.close()

        flash('盘点提交成功！', 'success')
        return redirect(url_for('view_inventory_sold_out'))
    return render_template('view_inventory_sold_out.html', source_track_data=source_track_data)

# 退换货单
@app.route('/exchange_return_order', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'purchase')
def exchange_return_order():
    cursor = mysql.connection.cursor()

    # Fetch products from database
    cursor.execute("SELECT item, sku FROM products")
    products = cursor.fetchall()  # List of tuples [(product_name1, sku1), (product_name2, sku2), ...]
    
    # Fetch sales representatives from sales_list table
    cursor.execute("SELECT sales_name FROM sales_list")
    sales_reps = cursor.fetchall()
    
    cursor.close()  # Close after fetching
    
    if request.method == 'POST':
        try:
            # Get form data for exchange_return
            date = request.form['date']
            client = request.form['client']
            rep = request.form['rep']
            user_name = request.form['user_name']

            # Insert data into 'exchange_return' table
            cursor = mysql.connection.cursor()

            cursor.execute('''
                INSERT INTO exchange_return (date, client, rep, user_name)
                VALUES (%s, %s, %s, %s)
            ''', (date, client, rep, user_name))
            
            exchange_return_id = cursor.lastrowid  # Get the last inserted ID

            # Insert data into 'exchange_return_order' table
            product_skus = request.form.getlist('product_sku[]')
            product_names = request.form.getlist('product_name[]')
            unit_prices = request.form.getlist('unit_price[]')
            quantities = request.form.getlist('quantity[]')
            prices = request.form.getlist('price[]')
            original_dates = request.form.getlist('original_date[]')
            reviewer = request.form.getlist('reviewer')
            
            for i in range(len(product_skus)):
                cursor.execute('''
                    INSERT INTO exchange_return_order (exchange_return_id, product_sku, product_name, unit_price, quantity, price, original_date, reviewer)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (exchange_return_id, product_skus[i], product_names[i], unit_prices[i], quantities[i], prices[i], original_dates[i], reviewer[0]))
            
            mysql.connection.commit()
            
            cursor.close()

            flash('Exchange/Return Order added successfully!', 'success')

            return redirect(url_for('inventory_in', exchange_return_id = exchange_return_id))  # Redirect back to the same page

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('exchange_return_order'))

    return render_template('exchange_return_order.html', products=products, sales_reps=sales_reps)

@app.route('/download_exchange_return')
@login_required
def download_exchange_return():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    cur = mysql.connection.cursor()
    query = '''
        SELECT e.exchange_return_id, e.date, e.client, e.rep, e.user_name,
               o.product_sku, o.product_name, o.unit_price, o.quantity, o.price, 
               o.original_date, o.reviewer
        FROM exchange_return e
        LEFT JOIN exchange_return_order o ON e.exchange_return_id = o.exchange_return_id
        WHERE e.date BETWEEN %s AND %s
        ORDER BY e.date DESC
    '''
    cur.execute(query, (start_date, end_date))
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data, columns=[
        '退换货id', '日期', '客户名', '销售代表', '操作人',
        '产品sku', '产品名称', '单价', '数量', '价格',
        '原始发货日期', '审核人'
    ])
    path = '/tmp/return_exchange_data.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True, download_name='return_exchange_data.xlsx')

# Add User Route (Admin Only)
@app.route('/add_user', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        # hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    (username, password, role))
        mysql.connection.commit()
        cur.close()

        flash('User added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_user.html')

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    # Delete user from the database
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", [user_id])
    mysql.connection.commit()
    cur.close()

    flash("User has been deleted successfully.", "success")
    return redirect(url_for('register'))

# Add Sales Representative Route (Admin Only)
@app.route('/register_new_sale_rep', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register_new_sale_rep():
    if request.method == 'POST':
        sales_name = request.form['sales_name']
        sales_username = request.form['sales_username']
        
        # Check if the sales representative already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM sales_list WHERE sales_name = %s", [sales_name])
        existing_sales_rep = cur.fetchone()

        if existing_sales_rep:
            flash('Sales representative already exists!', 'danger')
        else:
            cur.execute("INSERT INTO sales_list (sales_name, username) VALUES (%s, %s)", (sales_name, sales_username))
            mysql.connection.commit()
            flash('Sales representative added successfully!', 'success')

        cur.close()

    # After POST or GET, display the list of sales reps
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM sales_list")
    sales_reps = cur.fetchall()
    cur.close()

    return render_template('register_new_sale_rep.html', sales_reps=sales_reps)

# Delete Sales Representative Route (Admin Only)
@app.route('/delete_sale_rep/', defaults={'sales_name': None}, methods=['POST'])
@app.route('/delete_sale_rep/<string:sales_name>', methods=['POST'])
@login_required
@role_required('admin')
def delete_sale_rep(sales_name):
    if not sales_name:
        flash("No sales representative specified.", "danger")
        return redirect(url_for('register_new_sale_rep'))  # Redirect to a safe page

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM sales_list WHERE sales_name = %s", [sales_name])
    mysql.connection.commit()
    cur.close()

    flash("Sales representative has been deleted successfully.", "success")
    return redirect(url_for('register_new_sale_rep'))

# Add SKU
@app.route('/add_sku', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_sku():
    page = request.args.get('page', 1, type=int)  # Get current page, default to 1
    per_page = 10  # Number of items per page
    sort_by = request.args.get('sort_by', 'sku')  # Default sorting by SKU

    # If POST method (to add a new SKU)
    if request.method == 'POST':
        sku = request.form['sku']
        item = request.form['item']
        
        # Check if SKU already exists in the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM products WHERE sku = %s", (sku,))
        if cur.fetchone()[0] > 0:
            flash("SKU already exists. Please choose a different SKU.", "danger")
            return redirect(url_for('add_sku'))  # Redirect back to the page if SKU exists

        # Insert new SKU if not exists
        cur.execute("INSERT INTO products (sku, item) VALUES (%s, %s)", (sku, item))
        mysql.connection.commit()
        cur.close()
        flash("Product added successfully!", "success")
    
    # Get SKUs and items, sorted by the selected attribute
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT * FROM products ORDER BY {sort_by} LIMIT %s OFFSET %s", (per_page, (page - 1) * per_page))
    products = cur.fetchall()

    # Get the total number of products for pagination
    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]
    total_pages = ceil(total_products / per_page)  # Calculate the total number of pages

    cur.close()

    # Pass the necessary variables to the template
    return render_template('add_sku.html', 
                           products=products, 
                           page=page, 
                           total_pages=total_pages, 
                           sort_by=sort_by)

@app.route('/delete_sku/<string:sku>', methods=['POST'])
@login_required
@role_required('admin')
def delete_sku(sku):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM products WHERE sku = %s", (sku,))
    mysql.connection.commit()
    cur.close()

    flash("Product has been deleted successfully.", "success")
    return redirect(url_for('add_sku'))  # Redirect back to add_sku page

@app.route('/view_skus', methods=['GET'])
@login_required
@role_required('admin')
def view_skus():
    page = request.args.get('page', 1, type=int)  # Get current page, default to 1
    per_page = 10  # Number of items per page
    sort_by = request.args.get('sort_by', 'sku')  # Default sorting by SKU
    
    # Get SKUs and items, sorted by the selected attribute
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT * FROM products ORDER BY {sort_by} LIMIT %s OFFSET %s", (per_page, (page - 1) * per_page))
    products = cur.fetchall()

    # Get the total number of products for pagination
    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]
    total_pages = ceil(total_products / per_page)  # Calculate the total number of pages

    cur.close()

    return render_template('view_skus.html', 
                           products=products, 
                           page=page, 
                           total_pages=total_pages, 
                           sort_by=sort_by)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Route for uploading the Excel file and storing data in the products table
@app.route('/upload_excel', methods=['POST'])
@login_required
@role_required('admin')
def upload_excel():
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('add_sku'))

    file = request.files['file']

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('add_sku'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Save the file
        file.save(file_path)

        try:
            # Read Excel file
            df = pd.read_excel(file_path)

            # Check if required columns exist
            if 'SKU' not in df.columns or 'ITEM' not in df.columns:
                flash('Excel file must contain SKU and ITEM columns.', 'error')
                return redirect(url_for('add_sku'))

            # Connect to MySQL
            cursor = mysql.connection.cursor()

            for _, row in df.iterrows():
                sku = str(row['SKU']).strip()
                item = str(row['ITEM']).strip()

                # Check if SKU already exists
                cursor.execute("SELECT COUNT(*) FROM products WHERE SKU = %s", (sku,))
                exists = cursor.fetchone()[0]
                
                if exists:
                    flash(f'Product with SKU {sku} already exists.', 'info')
                else:
                    # Insert new product
                    cursor.execute(
                        "INSERT INTO products (SKU, ITEM) VALUES (%s, %s)",
                        (sku, item)
                    )

                    # Commit changes
                    mysql.connection.commit()
            cursor.close()

        except Exception as e:
            flash(f'Error processing file: {e}', 'error')

        return redirect(url_for('add_sku'))

    flash('Invalid file type. Only Excel files are allowed.', 'error')
    return redirect(url_for('add_sku'))

# 下载产品清单
@app.route('/download_product')
@login_required
def download_product():
    cur = mysql.connection.cursor()
    query = '''
        SELECT * FROM products
    '''
    cur.execute(query)
    data = cur.fetchall()
    cur.close()

    df = pd.DataFrame(data, columns=[
        'sku', '产品名称'
    ])
    path = '/tmp/product_data.xlsx'
    df.to_excel(path, index=False)
    return send_file(path, as_attachment=True, download_name='product_sku.xlsx')    

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_role = request.form['role']  # Get role from dropdown

        # Fetch user from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", [username])
        user = cur.fetchone()
        cur.close()

        # Check if user exists and password is correct
        if user and user[2] == password:
            # Check if the selected role matches the user's role
            if user[3] == selected_role:
                # Create a User object and log the user in
                user_obj = User(user[0], user[1], user[3])
                login_user(user_obj)
                flash(f"Welcome, {username}! Logged in as {selected_role}.", "success")
                return redirect(url_for('index'))
            else:
                flash("Incorrect role selected. Please choose the correct role.", "danger")
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register():
    if request.method == 'POST':
        submit_type = request.form.get('submit_type')

        # If registering a new user
        if submit_type == "register_user":
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                        (username, password, role))
            mysql.connection.commit()
            cur.close()

            flash('用户添加成功!', 'success')
            return redirect(url_for('register'))

        # If adding a new sales representative
        elif submit_type == "register_sales":
            sales_name = request.form['sales_name']
            sales_username = request.form['sales_username']

            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM sales_list WHERE sales_name = %s OR username = %s", (sales_name, sales_username))
            existing_sales = cur.fetchone()

            if existing_sales:
                flash('该销售代表已存在!', 'danger')
            else:
                cur.execute("INSERT INTO sales_list (sales_name, username) VALUES (%s, %s)", (sales_name, sales_username))
                mysql.connection.commit()
                flash('销售代表添加成功!', 'success')

            cur.close()
            return redirect(url_for('register'))

    # Fetch all users
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()

    # Fetch all sales representatives
    cur.execute("SELECT id, sales_name, username FROM sales_list")
    sales_reps = cur.fetchall()

    cur.close()
    return render_template('register.html', users=users, sales_reps=sales_reps)

if __name__ == '__main__':
    app.run()
