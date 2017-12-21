from flask import Flask, render_template, json, request, session, url_for
from flaskext.mysql import MySQL
import hashlib , os
from  werkzeug.utils import secure_filename, redirect

#Initalize variables
app = Flask(__name__)
app.secret_key = 'random string'
mysql = MySQL()

#CONSTANTS
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE_DB'] = 'shoppingcart'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#ROOT is implemented for Home Page --If user is logged in then route to this URL after each functionality
@app.route("/")
def root():
    app.logger.info('Entered rot now')
    loggedIn, firstName, noOfItems = getLoginDetails()
    cur = mysql.get_db().cursor()
    cur.execute('SELECT productId, name, price, description, image, stock FROM products')
    itemData = cur.fetchall()
    cur.execute('SELECT categoryId, name FROM categories')
    categoryData = cur.fetchall()
    itemData = parse(itemData)
    return render_template('home.html', itemData=itemData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)


@app.route("/login", methods = ['GET', 'POST'])
def login():
  if request.method == 'GET':
    return render_template('login.html')

  if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if is_valid(email, password):
            session['email'] = email
            return redirect(url_for('root'))
        else:
            error = 'Invalid UserId / Password'
            return render_template('login.html', error=error)

@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')

def parse(data):
    ans = []
    i = 0
    while i < len(data):
        curr = []
        for j in range(7):
            if i >= len(data):
                break
            curr.append(data[i])
            i += 1
        ans.append(curr)
    return ans

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def is_valid(email, password):
    cur =  mysql.get_db().cursor()
    cur.execute("SELECT email, password FROM users where email = '" + email + "'")
    data = cur.fetchall()
    app.logger.info('Data Fetched')
    for row in data:
        app.logger.info('Data Fetched11')
        if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
            app.logger.info('Data Fetched22')
            return True
    return False


def getLoginDetails():
    cur =  mysql.get_db().cursor()
    if 'email' not in session:
        loggedIn = False
        firstName = ''
        noOfItems = 0
    else:
        loggedIn = True
        cur.execute("SELECT userId, firstName FROM users WHERE email = '" + session['email'] + "'")
        userId, firstName = cur.fetchone()
        cur.execute("SELECT count(productId) FROM cart WHERE userId = " + str(userId))
        noOfItems = cur.fetchone()[0]
    cur.close()
    return (loggedIn, firstName, noOfItems)

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('loginForm'))

@app.route("/signup", methods = ['GET','POST'])
def signup():
  if request.method == 'POST':
    firstName = request.form["firstName"]
    lastName = request.form['lastName']
    email = request.form['email']
    password = request.form['password']
    '''address1 = request.form['address1']
    address2 = request.form['address2']
    zipcode = request.form['zipcode']
    city = request.form['city']
    state = request.form['state']
    country = request.form['country']
    phone = request.form['phone']'''
  try:
    cur =  mysql.get_db().cursor()
    cur.execute('INSERT INTO users ( password, email, firstName, lastName) ''VALUES (%s,%s,%s,%s)',
                (hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName))
    msg = "Registered Successfully"
    mysql.get_db().commit()
  except Exception as e:
    app.logger.info('%s Error Occured', e)
    mysql.get_db().rollback()
    msg = "Error occured"

  cur.close()
  return render_template("login.html", error=msg)

#Function related to CART
@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    cur =  mysql.get_db().cursor()
    cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
    userId = cur.fetchone()[0]
    cur.execute("SELECT products.productId, products.name, products.price, products.image FROM products, cart WHERE products.productId = cart.productId AND cart.userId = " + str(userId))
    products = cur.fetchall()
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template("cart.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        cur = mysql.get_db().cursor()
        cur.execute("SELECT userId FROM users WHERE email = '" + session['email'] + "'")
        userId = cur.fetchone()[0]
        app.logger.info('Added to CART with product ID and user %s %s',productId,userId)
        try:
          cur.execute('INSERT INTO cart (userId, productId) ' 'VALUES(%s,%s)', (userId, productId))
          mysql.get_db().commit()
          app.logger.infoI('Inserted to DB successfully')
          msg = "Added successfully"
        except:
            mysql.get_db().rollback()
            msg = "Error occured"

        cur.close()
        return redirect(url_for('root'))

@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    productId = int(request.args.get('productId'))
    cur = mysql.get_db().cursor()
    cur.execute("SELECT userId FROM users WHERE email = '" + email + "'")
    userId = cur.fetchone()[0]
    try:
      cur.execute("DELETE FROM cart WHERE userId = " + str(userId) + " AND productId = " + str(productId))
      mysql.get_db().commit()
      msg = "removed successfully"
    except:
      mysql.get_db().rollback()
      msg = "error occured"

    cur.close()
    return redirect(url_for('root'))

#Product
@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    cur = mysql.get_db().cursor()
    cur.execute('SELECT productId, name, price, description, image, stock FROM products WHERE productId = ' + productId)
    productData = cur.fetchone()
    cur.close()
    return render_template("productDescription.html", data=productData, loggedIn = loggedIn, firstName = firstName, noOfItems = noOfItems)

@app.route("/displayCategory")
def displayCategory():
  loggedIn, firstName, noOfItems = getLoginDetails()
  categoryId = request.args.get("categoryId")
  cur = mysql.get_db().cursor()
  cur.execute("SELECT products.productId, products.name, products.price, products.image, categories.name FROM products, categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = " + categoryId)
  data = cur.fetchall()
  cur.close()
  categoryName = data[0][4]
  data = parse(data)
  return render_template('displayCategory.html', data=data, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)

#Profile

@app.route("/account/profile")
def profileHome():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/edit")
def editProfile():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    cur = mysql.get_db().cursor()
    cur.execute("SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone FROM users WHERE email = '" + session['email'] + "'")
    profileData = cur.fetchone()
    cur.close()
    return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

@app.route("/account/profile/changePassword", methods=["GET", "POST"])
def changePassword():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    if request.method == "POST":
        oldPassword = request.form['oldpassword']
        oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
        newPassword = request.form['newpassword']
        newPassword = hashlib.md5(newPassword.encode()).hexdigest()
        cur = mysql.get_db().cursor()
        cur.execute("SELECT userId, password FROM users WHERE email = '" + session['email'] + "'")
        userId, password = cur.fetchone()
        if password == oldPassword:
            try:
                cur.execute("UPDATE users SET password = ? WHERE userId = ?", (newPassword, userId))
                mysql.get_db().commit()
                msg="Changed successfully"
            except:
                mysql.get_db().rollback()
                msg = "Failed"
            return render_template("changePassword.html", msg=msg)
        else:
            msg = "Wrong password"
        cur.close()
        return render_template("changePassword.html", msg=msg)
    else:
        return render_template("changePassword.html")

@app.route("/updateProfile", methods=["GET", "POST"])
def updateProfile():
    if request.method == 'POST':
        email = request.form['email']
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        address1 = request.form['address1']
        address2 = request.form['address2']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        country = request.form['country']
        phone = request.form['phone']
        cur = mysql.get_db().cursor()
        try:
          cur.execute('UPDATE users SET firstName = ?, lastName = ?, address1 = ?, address2 = ?, zipcode = ?, city = ?, state = ?, country = ?, phone = ? WHERE email = ?', (firstName, lastName, address1, address2, zipcode, city, state, country, phone, email))
          mysql.get_db().commit()
          msg = "Saved Successfully"
        except:
          mysql.get_db().rollback()
          msg = "Error occured"
        cur.close()
        return redirect(url_for('editProfile'))

#Admin Functions
@app.route("/add")
def admin():
    cur = mysql.get_db().cursor()
    cur.execute("SELECT categoryId, name FROM categories")
    categories = cur.fetchall()
    cur.close()
    return render_template('add.html', categories=categories)

@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        categoryId = int(request.form['category'])

        #Uploading image procedure
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        imagename = filename
        cur = mysql.get_db().cursor()
        try:
            cur.execute('''INSERT INTO products (name, price, description, image, stock, categoryId) VALUES (?, ?, ?, ?, ?, ?)''', (name, price, description, imagename, stock, categoryId))
            mysql.get_db().commit()
            msg="added successfully"
        except:
            msg="error occured"
            mysql.get_db().rollback()
        cur.close()
        print(msg)
        return redirect(url_for('root'))

@app.route("/remove")
def remove():
    cur = mysql.get_db().cursor()
    cur.execute('SELECT productId, name, price, description, image, stock FROM products')
    data = cur.fetchall()
    cur.close()
    return render_template('remove.html', data=data)

@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    cur = mysql.get_db().cursor()
    try:
      cur.execute('DELETE FROM products WHERE productID = ' + productId)
      mysql.get_db().cursor().commit()
      msg = "Deleted successsfully"
    except:
      mysql.get_db().rollback()
      msg = "Error occured"
    cur.close()
    print(msg)
    return redirect(url_for('root'))

if __name__ == "__main__":
  app.run()
