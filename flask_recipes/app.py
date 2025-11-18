import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
import json

# last signed 19/11/2025 at 12:07 (Kevin)

app = Flask(__name__)
app.secret_key = 'secret_key'

app.admin_key = 'VascanB'



def get_db_connection():
    conn = sqlite3.connect('DBR.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db_connection()

    # If these 2 lines aren't disabled, the data will reset every session
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


    db.commit()
    db.close()

    print('Initialized database.')
    if not os.path.exists('DBR.db'):
        init_db()
        print('Database created and initialized.')
    else:
        print('Database already exists, skipping initialization.')





# check if someone owns a recipe

def check_recipe_ownership(recipe_id):
    if not session.get('username'):
        return False

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('SELECT author_id FROM recipes WHERE id = ?', (recipe_id,))
    recipe = cursor.fetchone()
    db.close()

    return bool(recipe and recipe['author_id'] == session['username'])

# check if someone has the admin rank

def check_admin():
    """Check if the currently logged-in user is an admin."""
    if not session.get('username'):
        return False

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('SELECT admin FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    db.close()

    return bool(user and user['admin'])

# check if someone is a big boss head admin

def check_head_admin():
    """Check if the currently logged-in user is an admin."""
    if not session.get('username'):
        return False

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('SELECT head_admin FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    db.close()

    return bool(user and user['head_admin'])











# Register, index and login

@app.route('/') # default route is index.html so the starting page is index.html
def index():
    if session.get('username'):
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT admin FROM users WHERE username = ?', (session['username'],))
        db.close()
    return render_template('index.html', admin=check_admin(), headadmin=check_head_admin())




@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login. On GET request, it renders the login page.
    On POST request, it validates the credentials and logs the user in.
    """
    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')


        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('login.html')


        db = get_db_connection()
        cursor = db.cursor()


        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        db.close()  # Always close the database connection after query

        if user is None:
            # If no user is found with the provided email address
            flash('Invalid email or password.', 'error')
            return render_template('login.html')


        stored_password = user['password']
        if password == stored_password:

            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            # If the password is incorrect
            flash('Invalid email or password.', 'error')
            return render_template('login.html')


    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        email = request.form['email'].strip()
        adminkey = request.form.get('AdminKey', '')

        db = get_db_connection()
        cursor = db.cursor()

        # Check if username or email already exists
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        existing_user = cursor.fetchone()
        if existing_user:
            flash('Username or email already exists. Please choose a different one.', 'error')
            db.close()
            return redirect(url_for('register'))

        # Handle profile picture
        picture_ID = request.files['picture']
        if picture_ID and picture_ID.filename != '':
            filename = secure_filename(picture_ID.filename)
            upload_folder = os.path.join(app.root_path, 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            picture_ID.save(os.path.join(upload_folder, filename))
            picture_path = f'/static/uploads/{filename}'
        else:
            picture_path = None

        # Determine if user is admin
        is_admin = 0
        head_admin = 0
        if adminkey == app.admin_key:
            is_admin = 1
            head_admin = 1

        # Insert new user
        cursor.execute(
            'INSERT INTO users (username, password, email, admin, head_admin, picture_ID) VALUES (?, ?, ?, ?, ?, ?)',
            (username, password, email, is_admin, head_admin, picture_path)
        )
        db.commit()
        db.close()

        flash('Registration successful!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')











@app.route('/recipecreator', methods=['GET', 'POST'])
def recipecreator():
    if not session.get('username'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        prep_time = request.form['prep_time']
        cook_time = request.form['cook_time']
        serving_size = request.form['serving_size']
        difficulty = request.form['difficulty']
        video_url = request.form['video_url']
        author_id = session.get('username')


        action = request.form.get('action')
        draft = True if action == 'draft' else False
        approved = False  # admin approval still required


        picture_ID = request.files['picture']
        if picture_ID and picture_ID.filename != '':
            filename = secure_filename(picture_ID.filename)
            upload_folder = os.path.join(app.root_path, 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            picture_ID.save(os.path.join(upload_folder, filename))
            picture_path = f'/static/uploads/{filename}'
        else:
            picture_path = None

        ingredients = request.form.getlist('ingredients[]')
        equipment = request.form.getlist('equipment[]')
        steps = request.form.getlist('steps[]')

        ingredients_text = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(ingredients) if item.strip()])
        equipment_text = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(equipment) if item.strip()])
        steps_text = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(steps) if item.strip()])

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            '''INSERT INTO recipes 
            (title, draft, ingredients, equipment, steps, prep_time, cook_time, serving_size, 
             picture_ID, video_url, author_id, approved, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, draft, ingredients_text, equipment_text, steps_text, prep_time, cook_time,
             serving_size, picture_path, video_url, author_id, approved, difficulty)
        )
        db.commit()
        db.close()

        flash('Recipe saved as draft!' if draft else 'Recipe submitted for approval!', 'success')
        return redirect(url_for('index'))

    return render_template('recipecreator.html')



@app.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if not session.get('username'):
        flash('You must be logged in.', 'error')
        return redirect(url_for('login'))

    username = session.get('username')
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,))
    recipe = cursor.fetchone()

    if not recipe:
        db.close()
        return "Recipe not found", 404

    if recipe['author_id'] != username:
        db.close()
        return "You do not own this recipe.", 403

    if recipe['approved']:
        db.close()
        flash('You cannot edit an approved recipe.', 'error')
        return redirect(url_for('recipetemplate', recipe_id=recipe_id))

    if request.method == 'POST':
        title = request.form['title']
        prep_time = request.form['prep_time']
        cook_time = request.form['cook_time']
        serving_size = request.form['serving_size']
        difficulty = request.form['difficulty']
        video_url = request.form['video_url']

        picture_ID = request.files['picture']
        if picture_ID and picture_ID.filename != '':
            filename = secure_filename(picture_ID.filename)
            upload_folder = os.path.join(app.root_path, 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            picture_ID.save(os.path.join(upload_folder, filename))
            picture_path = f'/static/uploads/{filename}'
        else:
            picture_path = recipe['picture_ID']

        ingredients = request.form.getlist('ingredients[]')
        equipment = request.form.getlist('equipment[]')
        steps = request.form.getlist('steps[]')

        ingredients_text = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(ingredients) if item.strip()])
        equipment_text = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(equipment) if item.strip()])
        steps_text = '\n'.join([f"{i+1}. {item}" for i, item in enumerate(steps) if item.strip()])

        action = request.form.get('action')
        draft = True if action == 'draft' else False

        cursor.execute('''
            UPDATE recipes
            SET title=?, ingredients=?, equipment=?, steps=?, prep_time=?, cook_time=?, 
                serving_size=?, difficulty=?, picture_ID=?, video_url=?, draft=?, approved=0
            WHERE id=? AND author_id=?''',
            (title, ingredients_text, equipment_text, steps_text, prep_time, cook_time,
             serving_size, difficulty, picture_path, video_url, draft, recipe_id, username))

        db.commit()
        db.close()

        flash('Recipe saved as draft!' if draft else 'Recipe published for approval!', 'success')
        return redirect(url_for('recipetemplate', recipe_id=recipe_id))

    db.close()
    return render_template('edit_recipe.html', recipe=recipe)




@app.route('/recipelibrary', methods=['GET', 'POST'])
def recipelibrary():
    if not session.get('username'):
        print("Not logged in!")
        return redirect(url_for('login'))

    db = get_db_connection()
    cursor = db.cursor()

    # Select only approved recipes
    cursor.execute('SELECT * FROM recipes WHERE approved = 1')
    recipes = cursor.fetchall()

    db.close()
    # Pass the recipes to the template
    return render_template('recipelibrary.html', library=recipes, admin=check_admin())




@app.route('/recipetemplate/<int:recipe_id>', methods=['GET'])
def recipetemplate(recipe_id):
    if not session.get('username'):
        print("Not logged in!")
        return redirect(url_for('login'))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,))
    recipe = cursor.fetchone()

    db.close()
    if recipe is None:
        return redirect(url_for('index'))

    return render_template('recipetemplate.html', recipe=recipe, admin=check_admin(), owner=check_recipe_ownership(recipe_id))


















@app.route('/userprofile', defaults={'user_id': None}, methods=['GET'])
@app.route('/userprofile/<user_id>', methods=['GET'])
def userprofile(user_id):
    if not session.get('username'):
        print("Not logged in!")
        return redirect(url_for('login'))

    current_user = session.get('username')
    admincheck = check_admin()

    db = get_db_connection()
    cursor = db.cursor()

    # If no user_id provided, default to current user (you)
    if user_id is None:
        # Fetch current user's ID
        cursor.execute('SELECT rowid, * FROM users WHERE username = ?', (current_user,))
        user_data = cursor.fetchone()
        if not user_data:
            db.close()
            print("User not found!")
            return redirect(url_for('login'))
    else:
        # Fetch the profile being viewed
        cursor.execute('SELECT rowid, * FROM users WHERE username = ? OR rowid = ?', (user_id, user_id))
        user_data = cursor.fetchone()
        if not user_data:
            db.close()
            return "User not found", 404


    is_owner = (user_data['username'] == current_user)

    # Select recipes depending on viewer
    if is_owner or admincheck:
        cursor.execute('SELECT * FROM recipes WHERE author_id = ?', (user_data['username'],))
    else:
        cursor.execute('SELECT * FROM recipes WHERE author_id = ? AND approved = 1', (user_data['username'],))

    recipes = cursor.fetchall()
    db.close()
    # Pass user data & recipes to template
    return render_template(
        'userprofile.html',
        library=recipes,
        user=user_data,
        is_owner=is_owner,
        admin=admincheck
    )




@app.route('/update_pfp', methods=['POST'])
def update_pfp():
    if not session.get('username'):
        flash('You must be logged in to do that.', 'error')
        return redirect(url_for('login'))

    username = session['username']
    picture = request.files['picture']

    if not picture or picture.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('userprofile'))

    filename = secure_filename(picture.filename)
    upload_folder = os.path.join(app.root_path, 'static/uploads')
    os.makedirs(upload_folder, exist_ok=True)
    picture.save(os.path.join(upload_folder, filename))

    picture_path = f'/static/uploads/{filename}'

    # Save new picture path to database
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('UPDATE users SET picture_ID = ? WHERE username = ?', (picture_path, username))
    db.commit()
    db.close()

    flash('Profile picture updated successfully!', 'success')
    return redirect(url_for('userprofile'))

@app.route('/update_description', methods=['POST'])
def update_description():
    if not session.get('username'):
        flash('You must be logged in to do that.', 'error')
        return redirect(url_for('login'))

    username = session['username']
    description = request.form.get('description', '').strip()

    if not description:
        flash('Description cannot be empty.', 'error')
        return redirect(url_for('userprofile'))


    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('UPDATE users SET description = ? WHERE username = ?', (description, username))
    db.commit()
    db.close()

    flash('Profile description updated successfully!', 'success')
    return redirect(url_for('userprofile'))













# admin related

@app.route('/pendingrecipes', methods=['GET', 'POST'])
def pendingrecipes():
    if not session.get('username'):
        print("Not logged in!")
        return redirect(url_for('login'))

    # Block non-admins
    if not check_admin():
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for('index'))

    db = get_db_connection()
    cursor = db.cursor()

    # Select only approved recipes
    cursor.execute('SELECT * FROM recipes WHERE approved = 0')
    recipes = cursor.fetchall()

    db.close()
    # Pass the recipes to the template
    return render_template('pendingrecipes.html', library=recipes)





@app.route('/userlist', methods=['GET', 'POST'])
def userlist():
    if not session.get('username'):
        print("Not logged in!")
        return redirect(url_for('login'))

    # Block non-head admins
    if not check_head_admin():
        flash("You do not have permission to access this page.", "error")
        return redirect(url_for('index'))

    db = get_db_connection()
    cursor = db.cursor()

    # Select all users
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()

    db.close()

    # Pass the users to the template
    return render_template('user_list.html', library=users)







@app.route('/add_admin/<username>', methods=['POST'])
def add_admin(username):
    # Check if user is logged in
    if not session.get('username'):
        flash("You must be logged in.", "error")
        return redirect(url_for('login'))

    # Only head admins can promote
    if not check_head_admin():  # Replace with your headadmin check function
        flash("You do not have permission.", "error")
        return redirect(request.referrer or url_for('index'))

    db = get_db_connection()
    cursor = db.cursor()

    # Promote user to admin (do not change head_admin status)
    cursor.execute('UPDATE users SET admin = 1 WHERE username = ?', (username,))
    db.commit()
    db.close()

    return redirect(request.referrer or url_for('index'))


@app.route('/revoke_admin/<username>', methods=['POST'])
def revoke_admin(username):
    # Check if user is logged in
    if not session.get('username'):
        flash("You must be logged in.", "error")
        return redirect(url_for('login'))

    # Only head admins can revoke
    if not check_head_admin():
        flash("You do not have permission.", "error")
        return redirect(request.referrer or url_for('index'))

    db = get_db_connection()
    cursor = db.cursor()

    # Revoke admin rights (do not touch head_admin)
    cursor.execute('UPDATE users SET admin = 0 WHERE username = ?', (username,))
    db.commit()
    db.close()

    #flash(f"{username} is no longer an Admin.", "success")
    return redirect(request.referrer or url_for('index'))





@app.route('/approve_recipe/<int:recipe_id>', methods=['POST'])
def approve_recipe(recipe_id):
    if not session.get('username'):
        return redirect(url_for('login'))


    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('UPDATE recipes SET approved = 1 WHERE id = ?', (recipe_id,))
    db.commit()
    db.close()


    return redirect(request.referrer or url_for('index'))


@app.route('/delete_recipe/<int:recipe_id>', methods=['POST'])
def delete_recipe(recipe_id):
    if not session.get('username'):
        return {"success": False, "error": "Not logged in"}, 403

    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))
    db.commit()
    db.close()

    return redirect(request.referrer or url_for('index'))











# start

if __name__ == '__main__':
    init_db()

    app.run(port=1951, debug=True)

