from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__, static_url_path='/static')
app.secret_key = b'\xfdOe\x0c\xc1\x12^o\xc5\x87\x07\xa8u\xc4-\xdcY\x1f+\xc9A\xe8\x92y'

connection = sqlite3.connect('goldvault.db')

cursor = connection.cursor()

# cursor.execute('''DROP TABLE users''')
# cursor.execute('''DROP TABLE comments''')
# cursor.execute('''DROP TABLE friendships''')
# cursor.execute('''DROP TABLE transactions''')

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    nickname TEXT,
                    email TEXT,
                    password TEXT,
                    profile_picture TEXT,
                    money DECIMAL(10, 2)
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS friendships (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    friend_id INTEGER,
                    status TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (friend_id) REFERENCES users(id)
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY,
                    game_id INTEGER,
                    user_id INTEGER,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY,
                    game_name TEXT,
                    rating DECIMAL,
                    description TEXT,
                    price REAL
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    game_id INTEGER,
                    price_paid DECIMAL(10, 2),
                    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (game_id) REFERENCES games(id)
                )''')

connection.commit()
connection.close()

def hash_password(password):
    return generate_password_hash(password)

def check_password(input_password, hashed_password):
    return check_password_hash(hashed_password, input_password)

def create_user(nickname, email, password):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("INSERT INTO users (nickname, email, password, profile_picture, money) VALUES (?, ?, ?, ?, ?)", (nickname, email, password, "static\pictures\default.png", 0.00))
    connection.commit()
    connection.close()
    
def insert_user_money(user_id, money):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE users 
        SET money = ?
        WHERE id = ?
    """, (money, user_id))
    connection.commit()
    connection.close()
    
def get_user_money(user_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("SELECT money FROM users WHERE id = ?", (user_id,))
    money = cursor.fetchone()[0]
    connection.close()
    return money

@app.route('/wallet', methods=['GET', 'POST'])
def add_money():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session.get('id')
    current_money = get_user_money(user_id)

    if request.method == 'POST':
        amount = float(request.form['amount'])
        new_money = round(current_money + amount, 2)
        insert_user_money(user_id, new_money)
        return redirect(url_for('user_profile'))

    return render_template('wallet.html', current_money=current_money)

def insert_user_comment(user_id, game_id, content):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO comments (game_id, user_id, content, timestamp) VALUES (?, ?, ?, ?)", (game_id, user_id, content, timestamp))
    connection.commit()
    connection.close()

@app.route('/add_comment', methods=['GET', 'POST'])
def add_comment():
    if not session.get('game_id'):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        content = request.form['content']
        user_id = session.get('id')
        game_id = session.get('game_id')
        insert_user_comment(user_id, game_id, content)
        return redirect(url_for('game_detail', game_id=game_id))
    else:
        return render_template('add_comment.html')

def get_game_comments(game_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM comments WHERE game_id = ?', (game_id,))
    comments = cursor.fetchall()
    connection.close()
    return comments
    
def update_user_profile(user_id, nickname, profile_picture, password):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()

    query = "UPDATE users SET"
    params = []

    if nickname:
        query += " nickname = ?,"
        params.append(nickname)
    if profile_picture:
        query += " profile_picture = ?,"
        params.append(profile_picture)
    if password:
        query += " password = ?,"
        params.append(password)

    query = query.rstrip(',') + " WHERE id = ?"
    params.append(user_id)
    cursor.execute(query, tuple(params))
    connection.commit()
    connection.close()


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('id')
    user = get_user_details(user_id)

    if request.method == 'POST':
        new_nickname = request.form.get('new_nickname')
        new_profile_picture = request.form.get('new_profile_picture')
        new_password = request.form.get('new_password')
        hashed_password = hash_password(new_password)
        
        update_user_profile(user_id, new_nickname, new_profile_picture, hashed_password)

        return redirect(url_for('user_profile'))

    return render_template('edit_profile.html', user=user) 
    
def authenticate_user(email, password):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    connection.close()
    if user and check_password(password, user[3]):
        return user
    else:
        return None
    
def is_duplicate(nickname, email):
    conn = sqlite3.connect('goldvault.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE nickname = ? OR email = ?', (nickname, email))
    result = cursor.fetchone()
    conn.close()
    return result is not None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nickname = request.form['nickname']
        email = request.form['email']
        password = request.form['password']

        if is_duplicate(nickname, email):
            return "Nickname or email already exists. Please choose a different one."
    
        hashed_password = hash_password(password)
        create_user(nickname, email, hashed_password)

        return render_template('login.html')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = authenticate_user(email, password)

        if user:
            session['logged_in'] = True
            session['id'] = user[0]
            return redirect(url_for("home"))
        else:
            return "Login failed. Please check your email and password."
    return render_template('login.html')

def get_game_details():
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM games')
    games = cursor.fetchall()
    connection.close()
    return games

def get_user_details(user_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    connection.close()
    return user

@app.route('/profile')
def user_profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_id = session.get('id')
    print(user_id)
    user = get_user_details(user_id)
    print(user)
    return render_template('user_profile.html', user=user)

@app.route('/friend_list')
def friend_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session.get('id')
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    
    # Select friends of the current user
    cursor.execute('''
        SELECT u.id, u.nickname 
        FROM users u
        INNER JOIN friendships f ON u.id = f.friend_id
        WHERE f.user_id = ? AND f.status = 'friends'
    ''', (user_id,))
    
    friends = cursor.fetchall()
    
    # Select friends of the other user
    cursor.execute('''
        SELECT u.id, u.nickname 
        FROM users u
        INNER JOIN friendships f ON u.id = f.user_id
        WHERE f.friend_id = ? AND f.status = 'friends'
    ''', (user_id,))
    
    other_friends = cursor.fetchall()
    
    connection.close()
    
    all_friends = friends + other_friends
    
    return render_template('friend_list.html', friends=all_friends)

@app.route('/user_list')
def user_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    
    current_user_id = session.get('id')
    
    # Select users who are not friends and for whom there is no pending request from or to the current user
    cursor.execute("""
        SELECT id, nickname 
        FROM users 
        WHERE id != ? 
        AND id NOT IN (
            SELECT friend_id FROM friendships WHERE user_id = ? AND status = 'friends'
            UNION
            SELECT user_id FROM friendships WHERE friend_id = ? AND status = 'pending'
        ) 
        AND id NOT IN (
            SELECT user_id FROM friendships WHERE friend_id = ? AND status = 'friends'
            UNION
            SELECT friend_id FROM friendships WHERE user_id = ? AND status = 'pending'
        )
    """, (current_user_id, current_user_id, current_user_id, current_user_id, current_user_id))
    
    users = cursor.fetchall()
    
    cursor.execute("SELECT friend_id FROM friendships WHERE user_id = ? AND status = 'pending'", (current_user_id,))
    pending_requests = [row[0] for row in cursor.fetchall()]
    
    connection.close()
    return render_template('user_list.html', users=users, pending_requests=pending_requests)



@app.route('/friend_request', methods=['POST'])
def friend_request():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    friend_id = request.form.get('friend_id')
    
    if friend_id is None:
        return "Friend ID is required.", 400

    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    
    cursor.execute("INSERT INTO friendships (user_id, friend_id, status) VALUES (?, ?, ?)", 
                   (session.get('id'), friend_id, 'pending'))
    
    connection.commit()
    connection.close()
    return redirect(url_for('friend_list'))

@app.route('/requests', methods=['GET', 'POST'])
def choice_request():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_user_id = session.get('id')

        if 'accept_request' in request.form:
            request_id = request.form['accept_request']
            action = 'accept'
        elif 'refuse_request' in request.form:
            request_id = request.form['refuse_request']
            action = 'refuse'

        if action:
            connection = sqlite3.connect('goldvault.db')
            cursor = connection.cursor()

            if action == 'accept':
                cursor.execute("UPDATE friendships SET status = 'friends' WHERE id = ?", (request_id,))
            elif action == 'refuse':
                cursor.execute("DELETE FROM friendships WHERE id = ?", (request_id,))

            connection.commit()
            connection.close()

            return redirect(url_for('friend_list'))

    user_id = session.get('id')
    current_user_nickname = get_user_details(user_id)[0]

    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()

    cursor.execute('''SELECT friendships.id, friendships.status, users.id, users.nickname 
                      FROM friendships 
                      INNER JOIN users ON friendships.user_id = users.id 
                      WHERE (friendships.friend_id = ? AND friendships.status = 'pending')''', (user_id,))
    friend_requests = cursor.fetchall()

    connection.close()

    return render_template('requests.html', friend_requests=friend_requests, current_user_nickname=current_user_nickname)

def get_users_not_friends(user_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("SELECT id, nickname FROM users WHERE id != ? AND id NOT IN (SELECT friend_id FROM friendships WHERE user_id = ?)", (user_id, user_id))
    users = cursor.fetchall()
    connection.close()
    return users

@app.route('/')
def home():
    games = get_game_details()
    return render_template('main.html', games=games)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    if not query:
        return redirect(url_for('home'))
    
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM games WHERE game_name LIKE ?', ('%' + query + '%',))
    search_results = cursor.fetchall()
    connection.close()
    return render_template('search_results.html', query=query, results=search_results)


def update_comment_content(comment_id, new_content):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("UPDATE comments SET content = ? WHERE id = ?", (new_content, comment_id))
    connection.commit()
    connection.close()

def delete_user_comment(comment_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    connection.commit()
    connection.close()

@app.route('/game/<game_id>', methods=['GET', 'POST'])
def game_detail(game_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM games WHERE id = ?', (game_id,))
    game_det = cursor.fetchone()
    cursor.execute('''
        SELECT comments.id, comments.content, users.nickname, comments.timestamp, comments.user_id
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.game_id = ?
    ''', (game_id,))
    comments = cursor.fetchall()
    session['game_id'] = game_id
    connection.close()

    if request.method == 'POST':
        if 'edit_comment' in request.form:
            comment_id = request.form['edit_comment']
            new_content = request.form['new_content']
            update_comment_content(comment_id, new_content)
        elif 'delete_comment' in request.form:
            comment_id = request.form['delete_comment']
            delete_user_comment(comment_id)

        return redirect(url_for('game_detail', game_id=game_id))

    return render_template('game_detail.html', game_det=game_det, comments=comments)

def fetch_game_details(game_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM games WHERE id = ?", (game_id,))
    details = cursor.fetchone()
    connection.close()
    return details

def update_user_balance(user_id, new_balance):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET money = ? WHERE id = ?", (new_balance, user_id))
    connection.commit()
    connection.close()

def record_purchase(user_id, game_id, price_paid):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute("INSERT INTO transactions (user_id, game_id, price_paid) VALUES (?, ?, ?)", (user_id, game_id, price_paid))
    connection.commit()
    connection.close()

@app.route('/confirm_transaction/<game_id>', methods=['GET','POST'])
def confirm_transaction(game_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    game_details = fetch_game_details(game_id)

    if request.method == 'POST':
        user_id = session.get('id')
        user_balance = get_user_details(user_id)[5]
        print(user_balance)
        game_price = game_details[4]
        
        if user_balance < game_price:
            return "Insufficient balance", 403

        new_balance = user_balance - game_price
        update_user_balance(user_id, new_balance)
        
        record_purchase(user_id, game_id, price_paid=game_price)
        return redirect(url_for('library'))
    
    return render_template('confirm_transaction.html', details=game_details)


def fetch_purchased_games(user_id):
    connection = sqlite3.connect('goldvault.db')
    cursor = connection.cursor()
    cursor.execute('''
        SELECT games.game_name
        FROM games
        INNER JOIN transactions ON games.id = transactions.game_id
        WHERE transactions.user_id = ?
    ''', (user_id,))
    purchased_games = cursor.fetchall()
    connection.close()
    
    return purchased_games

@app.route('/library')
def library():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user_id = session.get('id')
    purchased_games = fetch_purchased_games(user_id)
    return render_template('library.html', purchased_games=purchased_games)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
