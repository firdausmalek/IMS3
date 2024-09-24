from sqlite3 import Cursor
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import csv
from io import StringIO
from flask import Response
from flask import Flask, request, render_template, jsonify


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management

# Configure MySQL Database Connection
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'inventory'

    
}

# Connect to the MySQL database
def connect_db():
    connection = mysql.connector.connect(**db_config)
    return connection

# Home route (Login Page)
@app.route('/')
def home():
    return render_template('login.html')

# Login Route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    try:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('home'))
    except mysql.connector.Error as err:
        return f"Error: {err}"

# Dashboard Route (Protected Page)
@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('submit.html', username=session['username'])
    else:
        return redirect(url_for('home'))
    
# Dashboard Route (Protected Page)
@app.route('/in')
def in1():
    return render_template('in.html', username=session['username'])

# Dashboard Route (Protected Page)
@app.route('/out')
def out1():
    return render_template('out.html', username=session['username'])

# Dashboard Route (Protected Page)
@app.route('/check')
def check():
    return render_template('check.html', username=session['username'])

#view product function
@app.route('/view_products')
def view_products():
    return render_template('in.html', inventory=session.get('products', []))


@app.route('/get_inventory', methods=['GET'])
def get_inventory():
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT Serial_Number, Name, Location, Status FROM inventory_2024")
    results = cursor.fetchall()

    cursor.close()
    connection.close()
    
    # Format the results to return a list of dictionaries
    return jsonify([{'Serial_Number': r[0], 'Name': r[1], 'Location': r[2], 'Status': r[3]} for r in results])




@app.route('/check_uid', methods=['POST'])
def check_uid():
    try:
        data = request.get_json()
        app.logger.info(f"Received data: {data}")  # Log received data
        uid = data.get('uid')
        if not uid:
            return jsonify({"error": "UID not provided"}), 400  # Change 4000 to 400

        with connect_db() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM inventory_2024 WHERE UID = %s", (uid,))
                results = cursor.fetchall()

        if not results:
            return jsonify({"message": "UID not found"}), 404
        
        return jsonify(results)

    except Exception as e:
        app.logger.error(f"Error in check_uid: {e}")
        return jsonify({"error": str(e)}), 500


## Route to handle adding products and displaying products on the same pag
@app.route('/submit_product', methods=['GET', 'POST'])
def submit_product():
    if 'username' in session:
        connection = connect_db()
        cursor = connection.cursor()

        # Handle form submission to add a product
        if request.method == 'POST':
            UID = request.form['UID']
            location = request.form['location']

            try:
                cursor.execute("INSERT INTO inventory_2024 (UID, location) VALUES (%s, %s)", (UID, location))
                connection.commit()
                flash("Product added successfully!")
            except mysql.connector.Error as err:
                return f"Error: {err}"

        # Fetch all products to display on the page
        cursor.execute("SELECT * FROM inventory_2024")
        products = cursor.fetchall()

        cursor.close()
        connection.close()

        return render_template('in.html', products=products)
    else:
        return redirect(url_for('home'))

# Logout Route
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.")
    return redirect(url_for('home'))


@app.route('/search_products', methods=['GET', 'POST'])
def search_products():
    connection = connect_db()
    cursor = connection.cursor()

    # Fetch all products to display in the table by default
    query = "SELECT * FROM inventory_2024"
    cursor.execute(query)
    inventory = cursor.fetchall()  # Fetch all rows

    products = []  # Initialize for search results
    if request.method == 'POST':
        uid = request.form.get('UID', '').strip()  # Safe way to get UID
        if not uid:
            flash("Please enter a UID.")
            return redirect(url_for('search_products'))

        # Search for products by UID
        search_query = "SELECT * FROM inventory_2024 WHERE UID LIKE %s OR name LIKE %s"
        uid_param = f"%{uid}%"
        name_param = f"%{uid}%"  # Adjust if you want to search by name too

        try:
            cursor.execute(search_query, (uid_param, name_param))
            products = cursor.fetchall()
        except Exception as e:
            print("Database query error:", e)  # Log any database error
            flash("An error occurred while searching for products.")
            return redirect(url_for('search_products'))

        if not products:
            flash("No products found for the given search criteria.")
        else:
            inventory = products  # Replace inventory with search results

    return render_template('in.html', inventory=inventory)


#csv function
import csv
from io import StringIO
from flask import Response, session

@app.route('/download_csv', methods=['POST'])
def download_csv():
    products = session.get('products', [])

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Bil', 'Name', 'Serial Number', '', 'QTT', 'Status','Location'])

    for product in products:
        writer.writerow(product)

    output.seek(0)

    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=products.csv"}
    )

@app.route('/save_products', methods=['POST'])
def save_products():
    products = session.get('products', [])
    
    # Implement your save logic here, e.g., saving to a file or database
    
    session.pop('products', None)  # Clear products from session after saving
    return redirect(url_for('index'))


# add function
@app.route('/add_product', methods=['POST'])
def add_product():
    if 'products' not in session:
        session['products'] = []

    connection = connect_db()
    cursor = connection.cursor()

    serial_number = request.form.get('Serial_Number')

    # Query to fetch the product with the given Serial Number
    query = "SELECT * FROM inventory_2024 WHERE Serial_Number = %s"
    cursor.execute(query, (serial_number,))

    product = cursor.fetchone()

    if product:
        # Append the new product to the session list
        if product not in session['products']:
            session['products'].append(product)
        else:
            flash("Product already added.")
    else:
        flash("No products found for the given Serial Number.")

    cursor.close()
    connection.close()

    return render_template('in.html', inventory=session['products'])

#clear caching
@app.after_request
def add_header(response):
    # Disable caching and ensure connection is closed after the request
    response.cache_control.no_store = True
    response.headers["Connection"] = "close"  # Add 'Connection: close' header
    return response



if __name__ == '__main__':
    app.run(debug=True)


