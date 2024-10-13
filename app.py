from flask import Flask, render_template, request, redirect, session, flash, url_for
import csv
import os
import pandas as  pd
from flask import send_file, redirect, url_for
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secure_key'  # Change to a secure key in production
# Update payment amount
#RESUMEN DE VENTAS 
def update_payment(item_id, additional_amount):
    updated_sales = []
    item_found = False

    # Read the existing sales data
    with open('sales.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['ID'] == str(item_id):
                item_found = True
                try:
                    current_amount = float(row['MONTOPAGADO'])
                    new_amount = current_amount + additional_amount
                    row['MONTOPAGADO'] = new_amount

                    # Update status based on new amount
                    row['STATUS'] = 'VENDIDO' if new_amount >= float(row['VENTACOP']) else 'DEUDA'
                except ValueError as e:
                    print(f"Error converting amounts for item ID: {item_id}. Error: {e}")
            updated_sales.append(row)

    # Write the updated sales data back to the CSV
    with open('sales.csv', mode='w', newline='') as file:
        fieldnames = ["MARCA","NOMBREPRODUCTO", "CAMBIOCOP", "PRECIOUSD", "PRECIOCOP", 
                      "VENTACOP", "TALLA", "COLOR", "PIEZA", "ID", 
                      "CLIENTE", "METODOPAGO", "MONTOPAGADO", "STATUS"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_sales)

    if item_found:
        print(f"Updated item ID: {item_id} with new amount: {additional_amount}")
    else:
        print(f"Item ID: {item_id} not found.")



@app.route('/sold_items', methods=['GET', 'POST'])
def sold_items():
    sales = load_sales()

    # Convert to float
    for sale in sales:
        sale['VENTACOP'] = float(sale['VENTACOP'])
        sale['MONTOPAGADO'] = float(sale['MONTOPAGADO'])

    # Apply filters
    filter_params = {
        
        'filter_nombreproducto': request.args.get('filter_nombreproducto', ''),
         'filter_cliente': request.args.get('filter_cliente', ''),
        'filter_talla': request.args.get('filter_talla', ''),
        'filter_color': request.args.get('filter_color', ''),
        'filter_pieza': request.args.get('filter_pieza', ''),
        'filter_status': request.args.get('filter_status', '')
    }

    # Filter sales based on parameters
    for key, value in filter_params.items():
        if value:
            sales = [sale for sale in sales if value.lower() in sale[key.replace('filter_', '').upper()].lower()]

    if request.method == 'POST':
        item_id = request.form.get('id')
        additional_amount = float(request.form.get('montopagado'))  # Convert to float

        # Check if the item's status is 'DEUDA' before updating
        sale_to_update = next((s for s in sales if s['ID'] == str(item_id)), None)
        if sale_to_update and sale_to_update['STATUS'] == 'DEUDA':
            update_payment(item_id, additional_amount)  # Call the function to update
            flash('Payment updated successfully!', 'success')
        else:
            flash('Cannot update payment for this sale.', 'error')

        return redirect(url_for('sold_items'))  # Redirect after processing

    return render_template('sold_items.html', sales=sales)



#FIN RESUMENT VENTAS 

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or session.get('role') != 'Admin':
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
import csv




    
@app.route('/download_inventory')
@admin_required  # Restricting this route to Admins only
def download_inventory():
    path = "inventory.csv"  # Path to your inventory CSV file
    if os.path.exists(path):
        return send_file(path, as_attachment=True)  # Send file as attachment
    else:
        return "File not found", 404  # Handle the error if file doesn't exist

# Route to download sales CSV
@app.route('/download_sales')
@admin_required  # Restricting this route to Admins only
def download_sales():
    path = "sales.csv"  # Path to your sales CSV file
    if os.path.exists(path):
        return send_file(path, as_attachment=True)  # Send file as attachment
    else:
        return "File not found", 404  # Handle the error if file doesn't exist




# Load users from CSV for user authentication
def load_users():
    users = {}
    try:
        with open('users.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                users[row['USERNAME']] = {
                    'role': row['ROLE'],
                    'password': row['PASSWORD'],
                }
    except FileNotFoundError:
        flash('User data file not found!')
    return users

# Load inventory from CSV
def load_inventory():
    inventory = []
    try:
        with open('inventory.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                inventory.append(row)
    except FileNotFoundError:
        with open('inventory.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=["MARCA","NOMBREPRODUCTO", "CAMBIOCOP", "PRECIOUSD", "PRECIOCOP", "VENTACOP", "TALLA", "COLOR", "PIEZA", "ID"])
            writer.writeheader()

    # Sort inventory by ID in descending order (most recent first)
    inventory.sort(key=lambda item: int(item['ID']), reverse=True)  # Convert 'ID' to int for proper sorting
    return inventory




def load_sales():
    sales = []
    try:
        with open('sales.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sales.append(row)
    except FileNotFoundError:
        with open('sales.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=["MARCA", "NOMBREPRODUCTO", "CAMBIOCOP", "PRECIOUSD", "PRECIOCOP", "VENTACOP", "TALLA", "COLOR", "PIEZA", "ID", 'CLIENTE', 'METODOPAGO', "MONTOPAGADO", "STATUS"])
            writer.writeheader()

    # Sort sales first by STATUS (DEUDA first) and then by ID (higher IDs first)
    sales.sort(key=lambda item: int(item['ID']) if item['ID'].isdigit() else -1, reverse=True)

    return sales


# Add new item to inventory
@admin_required  # Restricting this route to Admins only

def add_item_to_inventory(MARCA,NOMBREPRODUCTO, CAMBIOCOP, PRECIOUSD, VENTACOP, TALLA, COLOR, PIEZA, TALLA2=None):
    PRECIOCOP = CAMBIOCOP * PRECIOUSD
    
    # Load existing inventory and sales
    inventory = load_inventory()
    sales = load_sales()
    
    # Get the max ID from inventory and sales
    max_inventory_id = max(int(item['ID']) for item in inventory) if inventory else 0
    max_sales_id = max(int(item['ID']) for item in sales) if sales else 0
    
    # Choose the highest ID from both inventory and sales and add 1
    new_id = max(max_inventory_id, max_sales_id) + 1
    
    # Combine TALLA for sets, if PIEZA is "SET" and TALLA2 is provided
    if PIEZA == "SET" and TALLA2:
        TALLA = f"{TALLA}-{TALLA2}"

    # Append to the inventory CSV
    with open('inventory.csv', mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["MARCA","NOMBREPRODUCTO", "CAMBIOCOP", "PRECIOUSD", "PRECIOCOP", "VENTACOP", "TALLA", "COLOR", "PIEZA", "ID"])
        writer.writerow({
            "MARCA": MARCA,
            "NOMBREPRODUCTO": NOMBREPRODUCTO,
            "CAMBIOCOP": CAMBIOCOP,
            "PRECIOUSD": PRECIOUSD,
            "PRECIOCOP": PRECIOCOP,
            "VENTACOP": VENTACOP,
            "TALLA": TALLA,
            "COLOR": COLOR,
            "PIEZA": PIEZA,
            "ID": new_id
        })


# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    users = load_users()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)

        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('admin_dashboard' if user['role'] == 'Admin' else 'seller_dashboard'))
        else:
            flash('Invalid username or password!')

    return render_template('login.html')

# Seller dashboard
@app.route('/seller_dashboard', methods=['GET', 'POST'])
@admin_required  # Restricting this route to Admins only
def seller_dashboard():
    if request.method == 'POST':
        MARCA=request.form['marca']
        NOMBREPRODUCTO = request.form['nombreproducto']
        CAMBIOCOP = float(request.form['cambiocop'])
        PRECIOUSD = float(request.form['preciousd'])
        VENTACOP = float(request.form['precioVentaCop'])
        TALLA = request.form['talla']
        COLOR = request.form['color']
        PIEZA = request.form['pieza']
        
        # Initialize TALLA2 as None
        TALLA2 = None
        
        # Only get TALLA2 if PIEZA is "SET"
        if PIEZA == "SET":
            TALLA2 = request.form.get('talla2')  # Get TALLA2 if provided
        
        # Call the function to add the item to inventory
        add_item_to_inventory(MARCA,NOMBREPRODUCTO, CAMBIOCOP, PRECIOUSD, VENTACOP, TALLA, COLOR, PIEZA, TALLA2)
        
        return redirect(url_for('seller_dashboard'))

    inventory = load_inventory()
    return render_template('seller_dashboard.html', inventory=inventory)

@app.route('/delete_item/<item_id>', methods=['POST'])
@admin_required  # Restricting this route to Admins only
def delete_item(item_id):
    inventory = load_inventory()
    updated_inventory = [item for item in inventory if item['ID'] != str(item_id)]

    with open('inventory.csv', mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["MARCA","NOMBREPRODUCTO", "CAMBIOCOP", "PRECIOUSD", "PRECIOCOP", "VENTACOP", "TALLA", "COLOR", "PIEZA", "ID"])
        writer.writeheader()
        writer.writerows(updated_inventory)

    flash('Item deleted successfully.')
    return redirect(url_for('seller_dashboard'))

# Save updated inventory to CSV
def save_inventory(inventory):
    with open('inventory.csv', mode='w', newline='') as file:
        fieldnames = ["MARCA","NOMBREPRODUCTO", "CAMBIOCOP", "PRECIOUSD", "PRECIOCOP", "VENTACOP", "TALLA", "COLOR", "PIEZA", "ID"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory)

# Save sold items to sales CSV
def save_sales(sold_items):
    with open('sales.csv', mode='a', newline='') as file:
        fieldnames = ["MARCA","NOMBREPRODUCTO", "CAMBIOCOP", "PRECIOUSD", "PRECIOCOP", "VENTACOP", "TALLA", "COLOR", "PIEZA", "ID", 'CLIENTE', 'METODOPAGO', "MONTOPAGADO","STATUS"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        for item in sold_items:
            writer.writerow(item)

# Admin dashboard

def calculate_net_profit(inventory, sales):
    net_profit = 0.0

    # Create a dictionary from inventory for quick lookup by ID
    inventory_by_id = {item['ID']: float(item['PRECIOCOP']) for item in inventory}

    # Loop through the sales
    for sale in sales:
        sale_id = sale['ID']
        montopagado = float(sale['MONTOPAGADO'])  # Sale revenue
        preciocop =  float(sale['PRECIOCOP']) # Purchase cost from inventory

        # Calculate profit for this sale (sales revenue - purchase cost)
        profit = montopagado - preciocop
        net_profit += profit

    return net_profit


def calculate_total_debt(inventory, sales):
    total_debt = 0.0

    # Calculate debt from sales
    for sale in sales:
        ventacop = float(sale['VENTACOP'])
        montopagado = float(sale['MONTOPAGADO'])

        # Calculate outstanding debt for the sale
        if montopagado < ventacop:
            debt = ventacop - montopagado
            total_debt += debt

    # Add unsold items' purchase cost from inventory
    for item in inventory:
        total_debt += float(item['PRECIOCOP'])  # Each unsold item contributes to the debt

    return total_debt


@app.route('/admin_dashboard', methods=['GET', 'POST'])
@admin_required  # Restricting this route to Admins only
def admin_dashboard():
    inventory = load_inventory()
    sales = load_sales()

    # Filtering Logic for Inventory
    filter_nombreproducto = request.args.get('filter_nombreproducto', '')
    filter_marca = request.args.get('filter_marca', '')
    filter_talla = request.args.get('filter_talla', '')
    filter_color = request.args.get('filter_color', '')
    filter_pieza = request.args.get('filter_pieza', '')
    if filter_marca:
        inventory = [item for item in inventory if filter_marca.lower() in item['MARCA'].lower()]
    if filter_nombreproducto:
        inventory = [item for item in inventory if filter_nombreproducto.lower() in item['NOMBREPRODUCTO'].lower()]
    if filter_talla:
        inventory = [item for item in inventory if item['TALLA'] == filter_talla]
    if filter_color:
        inventory = [item for item in inventory if item['COLOR'] == filter_color]
    if filter_pieza:
        inventory = [item for item in inventory if item['PIEZA'] == filter_pieza]

    # Total Calculations
    total_sales = sum(float(sale['MONTOPAGADO']) for sale in sales)
    #total_debt = sum(float(item['PRECIOCOP']) for item in inventory)
    total_debt = calculate_total_debt(inventory, sales)
    net_profit =  calculate_net_profit(inventory, sales)

    if request.method == 'POST':
        selected_ids = request.form.getlist('sold_items')
        cliente = request.form['cliente']
        metodopago = request.form['metodopago']
        montopagado = request.form['montopagado']
        status = request.form['status']
        
        sold_items = []

        # Processing selected sold items
        for item_id in selected_ids:
            item = next((item for item in inventory if item['ID'] == item_id), None)
            if item:
                sold_items.append({
                    **item,
                    'CLIENTE': cliente,
                    'METODOPAGO': metodopago,
                    'MONTOPAGADO': montopagado,
                    'STATUS': status
                })

        # Save the sold items to the sales record
        save_sales(sold_items)

        # Remove sold items from inventory
        updated_inventory = [item for item in inventory if item['ID'] not in selected_ids]
        save_inventory(updated_inventory)

        flash('Items sold successfully!')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_dashboard.html', 
                           inventory=inventory, 
                           sales=sales, 
                           total_sales=total_sales, 
                           total_debt=total_debt, 
                           net_profit=net_profit)

# Logout route
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    flash('You have been logged out successfully.')
    return redirect(url_for('login'))

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
