import csv  # Ensure csv is imported
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file
import os
import pytz

app = Flask(__name__)
app.secret_key = 'fAEZKLASDI1I%%wq$@!'  # Change this to a random secret key

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
                    'password': row['PASSWORD'],  # Store plain password for comparison
                    'sucursal': row['SUCURSAL']  # Include SUCURSAL in the user data
                }
    except FileNotFoundError:
        flash('User data file not found!')
    return users

# Load reports from CSV
def load_reports():
    reports = []
    try:
        with open('reports.csv', mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                reports.append(row)
    except FileNotFoundError:
        with open('reports.csv', mode='w') as file:
            writer = csv.DictWriter(file, fieldnames=['username', 'amount', 'date', 'time', 'SUCURSAL'])
            writer.writeheader()
    return reports

# Save report to CSV
def save_report(username, amount, date, sucursal):
    now = datetime.now(pytz.timezone('America/Bogota'))  # Current time in Bogotá timezone
    time_str = now.strftime("%H:%M:%S")  # Current time for the report
    with open('reports.csv', mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['username', 'amount', 'date', 'time', 'SUCURSAL'])
        writer.writerow({'username': username, 'amount': amount, 'date': date, 'time': time_str, 'SUCURSAL': sucursal})

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    users = load_users()  # Load users from CSV
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users.get(username)
        # Check if user exists and verify password
        if user and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            session['sucursal'] = user['sucursal']  # Store SUCURSAL in the session
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!')

    return render_template('login.html')

from datetime import datetime, timedelta
import pytz

# Adjust this part in `dashboard` to handle the next day view for admin
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    role = session['role']
    reports = load_reports()
    col_time_zone = pytz.timezone('America/Bogota')

    if reports is None:
        return render_template('dashboard.html', error="Failed to load reports.")

    branches = set(report['SUCURSAL'] for report in reports)

    if role == 'Admin':
        grouped_reports = {}
        for report in reports:
            original_date = report['date'].strip()
            report_time = report['time'].strip()
            report_datetime_str = f"{original_date} {report_time}"
            report_datetime = datetime.strptime(report_datetime_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
            report_datetime = report_datetime.astimezone(col_time_zone)

            # Adjust the report's display date based on the time
            display_date = report_datetime.date()
            if report_datetime.time() >= datetime.strptime('18:00:00', '%H:%M:%S').time():
                display_date += timedelta(days=1)  # Move to the next day

            display_date_str = display_date.strftime('%Y-%m-%d')  # Format for display

            # Group reports by the adjusted display date
            if display_date_str not in grouped_reports:
                grouped_reports[display_date_str] = []
            grouped_reports[display_date_str].append(report)

        # Sort the grouped reports by date in descending order
        sorted_grouped_reports = dict(sorted(grouped_reports.items(), key=lambda item: item[0], reverse=True))

        # Pass the sorted grouped reports to the template
        return render_template('AdminMain.html', grouped_reports=sorted_grouped_reports, branches=branches)

    elif role == 'Seller':
        seller_reports = [r for r in reports if r['username'] == session['username']]
        seller_reports.sort(key=lambda r: datetime.strptime(r['date'].strip(), "%Y-%m-%d"), reverse=True)

        return render_template('seller_dashboard.html', reports=seller_reports)

    return redirect(url_for('login'))
# Adjust this part in `report_detail` to show the actual date when viewing details

@app.route('/branch_reports')
def branch_reports():
    branch = request.args.get('branch')
    reports = load_reports()

    # Filter reports by branch
    filtered_reports = [report for report in reports if report['SUCURSAL'] == branch]

    # Group reports by date
    grouped_reports = {}
    for report in filtered_reports:
        original_date = report['date'].strip()
        report_time = report['time'].strip()
        report_datetime_str = f"{original_date} {report_time}"
        report_datetime = datetime.strptime(report_datetime_str, "%Y-%m-%d %H:%M:%S")

        display_date = original_date
        

        if display_date not in grouped_reports:
            grouped_reports[display_date] = []
        grouped_reports[display_date].append(report)

    # Sort the grouped reports by date in descending order
    sorted_grouped_reports = dict(sorted(grouped_reports.items(), key=lambda item: item[0], reverse=True))

    # Optionally, sort reports within each date by time in descending order as well
    for date in sorted_grouped_reports:
        sorted_grouped_reports[date].sort(key=lambda r: datetime.strptime(r['time'], "%H:%M:%S"), reverse=True)

    return render_template('branch_reports.html', grouped_reports=sorted_grouped_reports, branch=branch)
@app.route('/report_detaildate')
def report_detaildate():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))

    date = request.args.get('date').strip()  # Strip whitespace
   
    reports = load_reports()

    # Convert the requested date to a datetime object
    requested_date = datetime.strptime(date, '%Y-%m-%d')

    # Prepare a list to hold filtered reports
    filtered_reports = []

    # Iterate over each report to apply the date adjustment
    for r in reports:
        # Convert the report date and time to a datetime object
        report_date = datetime.strptime(r['date'], '%Y-%m-%d')
        report_time = datetime.strptime(r['time'], '%H:%M:%S')
        
        # Combine report date and time into a single datetime object
        report_datetime = datetime.combine(report_date, report_time.time())
        
        
        adjusted_report_date = report_date  # No adjustment needed

        # If the adjusted report date matches the requested date and branch matches, add to filtered reports
        if adjusted_report_date.date() == requested_date.date() :
            filtered_reports.append(r)

    if not filtered_reports:
        flash(f'No reports found for {date} ')
        return redirect(url_for('dashboard'))

    return render_template('details.html', date=date,  reports=filtered_reports)
@app.route('/report_detail')
def report_detail():
    if 'username' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))

    date = request.args.get('date').strip()  # Strip whitespace
    branch = request.args.get('branch').strip()  # Get the branch from the query parameters
    reports = load_reports()

    # Convert the requested date to a datetime object
    requested_date = datetime.strptime(date, '%Y-%m-%d')

    # Prepare a list to hold filtered reports
    filtered_reports = []

    # Iterate over each report to apply the date adjustment
    for r in reports:
        # Convert the report date and time to a datetime object
        report_date = datetime.strptime(r['date'], '%Y-%m-%d')
        report_time = datetime.strptime(r['time'], '%H:%M:%S')
        
        # Combine report date and time into a single datetime object
        report_datetime = datetime.combine(report_date, report_time.time())
        
        # No adjustment needed in detailed view; show the actual report date
        adjusted_report_date = report_date

        # If the adjusted report date matches the requested date and branch matches, add to filtered reports
        if adjusted_report_date.date() == requested_date.date() and r['SUCURSAL'] == branch:
            filtered_reports.append(r)

    if not filtered_reports:
        flash(f'No reports found for {date} in branch {branch}.')
        return redirect(url_for('dashboard'))

    return render_template('details.html', date=date, branch=branch, reports=filtered_reports)


@app.route('/download_reports')
def download_reports():
    # Check if the user is logged in and is an Admin
    if 'username' not in session or session.get('role') != 'Admin':
        flash('You do not have permission to download the reports.')
        return redirect(url_for('login'))

    # Define the path to the reports.csv file
    report_path = os.path.join(os.getcwd(), 'reports.csv')  # Use the current directory

    if not os.path.exists(report_path):
        return "Report not found!", 404

    return send_file(report_path, mimetype='text/csv', as_attachment=True, download_name='reports.csv')

@app.route('/report', methods=['POST'])
def report():
    if 'username' not in session or session['role'] != 'Seller':
        return redirect(url_for('login'))

    amount = request.form['amount']
    now = datetime.now(pytz.timezone('America/Bogota'))  # Get current time in Bogotá timezone
    current_time = now.time()

    report_date = now.strftime('%Y-%m-%d')

    reports = load_reports()  # Load existing reports

    # Check if a report for this user and date already exists
    existing_report = next((r for r in reports if r['username'] == session['username'] and r['date'] == report_date), None)

    if existing_report:
        flash('You can only submit one report per day.')
        return redirect(url_for('dashboard'))

    # Save report to CSV
    save_report(session['username'], amount, report_date, session['sucursal'])
    flash('Report submitted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('sucursal', None)  # Remove SUCURSAL from session
    flash('Logged out successfully!')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)  # Set to False in production
