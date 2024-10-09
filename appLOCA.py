from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask import Flask, send_file, render_template, request
import os
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure key

# Load users from CSV
def load_users():
    users = {}
    try:
        with open('users.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                users[row['USERNAME']] = {
                    'id': row['ID'],
                    'role': row['ROLE'],
                    'password': row['PASSWORD'],
                    'sucursal': row['SUCURSAL']
                }
    except FileNotFoundError:
        flash('User data file not found!')
    return users

# Load reports and calculate Ddate if not present
def load_reports():
    reports = []
    try:
        with open('reports.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                reports.append(row)
    except FileNotFoundError:
        # If the file doesn't exist, create it and write the header
        with open('reports.csv', mode='w') as file:
            writer = csv.DictWriter(file, fieldnames=['username', 'amount', 'date', 'time', 'sucursal', 'Ddate'])
            writer.writeheader()
    
    

    return reports

def update_reports_with_ddate():
    reports = load_reports()  # Load existing reports
    updated_reports = []

    for report in reports:
        # Add Ddate logic based on your requirements
        if report['time'] >= "18:00:00":  # Assuming time is in HH:MM:SS format
            # Adjust Ddate logic according to your needs
            report['Ddate'] = (datetime.strptime(report['date'], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            report['Ddate'] = report['date']

        updated_reports.append(report)

    # Write updated reports back to CSV
    with open('reports.csv', mode='w', newline='') as file:
        fieldnames = ['username', 'amount', 'date', 'time', 'sucursal', 'Ddate']  # Ensure Ddate is included
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_reports)  # Write all updated reports

# Save report to CSV
def save_report(username, amount, date, sucursal, Ddate):
    if 'username' not in session :
        return redirect(url_for('login'))
    now = datetime.now(pytz.timezone('America/Bogota'))
    time_str = now.strftime('%H:%M:%S')

    # Write to the CSV file
    with open('reports.csv', mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['username', 'amount', 'date', 'time', 'sucursal', 'Ddate'])
        writer.writerow({
            'username': username,
            'amount': amount,
            'date': date,
            'time': time_str,
            'sucursal': sucursal,
            'Ddate': Ddate  # Include Ddate in the write
        })

# Seller Dashboard
@app.route('/seller_dashboard', methods=['GET', 'POST'])
def seller_dashboard():
    if 'username' not in session or session['role'] != 'Seller':
        return redirect(url_for('login'))
    update_reports_with_ddate()  # Ensure Ddate is updated
    reports = load_reports()
    # Update reports with Ddate after loading them
    update_reports_with_ddate()  # Ensure Ddate is updated
    user_reports = [report for report in reports if report['username'] == session['username']]

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except ValueError:
            flash('Amount must be a valid number.')
            return redirect(url_for('seller_dashboard'))

        now = datetime.now(pytz.timezone('America/Bogota'))

        # Determine effective report date (Ddate) based on current time
        if now.hour >= 18:  # After 6 PM
            effective_report_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')  # Next day
        else:
            effective_report_date = now.strftime('%Y-%m-%d')

        # Check if there is already a report for the effective report date
        existing_report = next((report for report in user_reports if report['Ddate'] == effective_report_date), None)

        if amount < 0.1:
            flash('Amount must be at least 0.1 USD.')
        elif existing_report:
            flash('Ya subiste un reporte para este día. Contacta al administrador si te equivocaste.')
        else:
            # Save the report with the determined effective report date
            save_report(session['username'], amount, now.strftime('%Y-%m-%d'), session['sucursal'], effective_report_date)
            flash('REPORTE SUBIDO CON ÉXITO')
            return redirect(url_for('seller_dashboard'))

    return render_template('seller_dashboard.html', reports=user_reports)

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
            session['sucursal'] = user['sucursal']  # Store SUCURSAL in the session
            if user['role'] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('seller_dashboard'))
        else:
            flash('Invalid username or password!')

    return render_template('login.html')
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session or session['role'] != 'Admin':
            flash('Access denied. Only admins can access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    # Preserve the original function name
    decorated_function.__name__ = f.__name__
    return decorated_function
# Admin Dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    update_reports_with_ddate()  # Ensure Ddate is updated
    reports = load_reports()  # Load the updated reports

    # Load available branches from reports
    branches = {report['sucursal'] for report in reports}  # Get unique branches

    # Filter by branch if a branch is selected
    selected_branch = request.form.get('branch')
    total_sales_by_date = calculate_total_sales_by_date(reports, selected_branch)

    return render_template('admin_dashboard.html', total_sales=total_sales_by_date, branches=branches, selected_branch=selected_branch)
@admin_required
def calculate_total_sales_by_date(reports, selected_branch=None):
    
    sales_by_date = {}
    for report in reports:
        if selected_branch and report['sucursal'] != selected_branch:
            continue  # Skip reports that don't match the selected branch

        ddate = report['Ddate']
        amount = float(report['amount'])
        if ddate in sales_by_date:
            sales_by_date[ddate] += amount
        else:
            sales_by_date[ddate] = amount
    return sales_by_date

@app.route('/download_report')
@admin_required
def download_report():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    path = "reports.csv"  # Ensure this is the correct path to your CSV file
    if os.path.exists(path):
        return send_file(path, as_attachment=True)  # Send file as attachment
    else:
        return "File not found", 404  # Handle the error if file doesn't exist
@app.route('/details/<string:ddate>', methods=['GET'])
@admin_required
def report_details(ddate):
    selected_branch = request.args.get('branch')  # Get the selected branch from the request args
    reports = load_reports()
    
    # Filter detailed reports by date and selected branch
    detailed_reports = [report for report in reports if report['Ddate'] == ddate]
    
    if selected_branch:
        detailed_reports = [report for report in detailed_reports if report['sucursal'] == selected_branch]

    return render_template('report_details.html', ddate=ddate, reports=detailed_reports)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
