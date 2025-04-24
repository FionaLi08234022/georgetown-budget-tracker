from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import pandas as pd
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # for session management

data_file = "budget_data.csv"
users_file = "users.csv"

# Ensure CSV exists
def init_csv():
    if not os.path.exists(data_file):
        df = pd.DataFrame(columns=["username", "type", "category", "subcategory", "amount", "date"])
        df.to_csv(data_file, index=False)

    if not os.path.exists(users_file):
        users = pd.DataFrame(columns=["username", "password"])
        users.to_csv(users_file, index=False)

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('welcome'))
    return redirect(url_for('index'))

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    init_csv()
    df = pd.read_csv(data_file)
    user_df = df[df['username'] == session['username']].copy()
    user_df['date'] = pd.to_datetime(user_df['date'])
    user_df.sort_values('date', ascending=False, inplace=True)
    user_df.reset_index(inplace=True)

    total_income = user_df[user_df['type'] == 'income']['amount'].sum()
    total_spending = user_df[user_df['type'] == 'spending']['amount'].sum()
    balance = total_income - total_spending

    return render_template('index.html', entries=user_df.to_dict('records'), income=total_income, spending=total_spending, balance=balance)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        entry_type = request.form['type']
        category = request.form['category']

        if category == 'Customize':
            category = request.form.get('custom_category', category)

        subcategory = request.form.get('subcategory', '')
        if subcategory == 'custom':
            subcategory = request.form.get('custom_subcategory', '')

        amount = float(request.form['amount'])
        date = request.form['date']

        df = pd.read_csv(data_file)
        df = pd.concat([df, pd.DataFrame([{
            'username': session['username'],
            'type': entry_type,
            'category': category,
            'subcategory': subcategory,
            'amount': amount,
            'date': date
        }])], ignore_index=True)
        df.to_csv(data_file, index=False)
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/delete/<int:entry_index>', methods=['POST'])
def delete_entry(entry_index):
    if 'username' not in session:
        return redirect(url_for('login'))

    df = pd.read_csv(data_file)
    df = df[df['username'] == session['username']].reset_index(drop=True)

    if 0 <= entry_index < len(df):
        df.drop(index=entry_index, inplace=True)
        df_all = pd.read_csv(data_file)
        df_all = df_all[df_all['username'] != session['username']]
        df_all = pd.concat([df_all, df], ignore_index=True)
        df_all.to_csv(data_file, index=False)

    return redirect(url_for('index'))

@app.route('/visualization', methods=['GET', 'POST'])
def visualization():
    if 'username' not in session:
        return redirect(url_for('login'))

    df = pd.read_csv(data_file)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['username'] == session['username']]

    months_available = sorted(df['date'].dt.strftime('%Y-%m').unique(), reverse=True)
    selected_month = request.form.get('month')
    if selected_month:
        filtered = df[df['date'].dt.strftime('%Y-%m') == selected_month]
    else:
        selected_month = months_available[0] if months_available else None
        filtered = df[df['date'].dt.strftime('%Y-%m') == selected_month] if selected_month else pd.DataFrame()

    spend_df = filtered[filtered['type'] == 'spending']
    grouped = spend_df.groupby('category')['amount'].sum().reset_index()

    return render_template('visualization.html', data=grouped.to_dict('records'), months=months_available, selected_month=selected_month)

@app.route('/register', methods=['GET', 'POST'])
def register():
    init_csv()  # Ensure CSVs exist
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        users = pd.read_csv(users_file)
        if username in users['username'].values:
            return "Username already exists."

        users = pd.concat([users, pd.DataFrame([[username, hashed_password]], columns=['username', 'password'])], ignore_index=True)
        users.to_csv(users_file, index=False)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    init_csv()  # Ensure CSVs exist
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = pd.read_csv(users_file)
        user = users[users['username'] == username]

        if not user.empty and check_password_hash(user.iloc[0]['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
        return "Invalid credentials."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
