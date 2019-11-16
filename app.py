from flask import Flask, make_response
from flask_pymongo import PyMongo

from flask import abort, jsonify, redirect, render_template
from flask import request, url_for
from forms import ProductForm
from bson.objectid import ObjectId
from bson.errors import InvalidId

from flask_login import LoginManager, current_user
from flask_login import login_user, logout_user

from forms import LoginForm
from model import User

from flask_login import login_required
import json

app = Flask(__name__)

#### pymongo
app.config['MONGO_DBNAME'] = 'foodb'
#app.config['MONGO_URI'] = 'mongodb://localhost:27017/foodb'
app.config['MONGO_URI'] = 'mongodb+srv://pautib:Mt5113sal@ads-h9hqo.mongodb.net/test?retryWrites=true&w=majority'
mongo = PyMongo(app)
####
app.config['SECRET_KEY'] = 'enydM2ANhdcoKwdVa0jWvEsbPFuQpMjf' # Create your own.
app.config['SESSION_PROTECTION'] = 'strong'

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/')
def index():
  return redirect(url_for('products_list'))



@app.route('/string/')
def return_string():
    dump = dump_request_detail(request)
    return 'Hello, world!'

@app.route('/tuple/<path:resource>')
def return_tuple(resource):
  dump = dump_request_detail(request)
  return 'Hello, world! \n' + dump, 200, {'Content-Type':'text/plain'}

@app.route('/object/')
def return_object():
  dump = dump_request_detail(request)
  headers = {'Content-Type': 'text/plain'}
  return make_response(Response('Hello, world! \n' + dump, status=200,
    headers=headers))

def dump_request_detail(request):
  request_detail = """
## Request INFO ##
request.endpoint: {request.endpoint}
request.method: {request.method}
request.view_args: {request.view_args}
request.args: {request.args}
request.form: {request.form}
request.user_agent: {request.user_agent}
request.files: {request.files}
request.is_xhr: {request.is_xhr}

## request.headers ##
{request.headers}
  """.format(request = request).strip()
  return request_detail

@app.before_request
def callme_before_every_request():
  # Demo only: the before_request hook.
  app.logger.debug(dump_request_detail(request))

@app.after_request
def callme_after_every_response(response):
  # Demo only: the after_request hook.
  app.logger.debug('# After Request #\n' + repr(response))
  return response

## Create a new product
@app.route('/products/create/', methods=['GET', 'POST'])
@login_required
def product_create():
  """Provide HTML form to create a new product."""
  form = ProductForm(request.form)
  if request.method == 'POST' and form.validate():
    mongo.db.products.insert_one(form.data)
    # Success. Send user back to full product list.
    return redirect(url_for('products_list'))
  # Either first load or validation error at this point.
  return render_template('product/edit.html', form=form)

@app.route('/products/<product_id>/')
def product_detail(product_id):
  """Provide HTML page with a given product."""
  # Query: get Product object by ID.
  product = mongo.db.products.find_one({ "_id": ObjectId(product_id) })
  print(product)
  if product is None:
    # Abort with Not Found.
    abort(404)
  return render_template('product/detail.html', product = product)

@app.route('/products/')
def products_list():
  """Provide HTML listing of all Products."""
  # Query: Get all Products objects, sorted by date.
  products = mongo.db.products.find()[:]
  return render_template('product/index.html', products=products)

# @app.route('/products/<int:product_id>/edit/', methods=['GET', 'POST'])
# @login_required
# def product_edit(product_id):
#   product = mongo.db.products.find_one({ "_id": ObjectId(product_id) })
#   print(product)
#   form = ProductForm(request.form)
#
#   if request.method == 'GET':
#     ProductForm.name = product['name']
#     ProductForm.description = product['description']
#     ProductForm.price = product['price']
#     return render_template('product/edit.html', form=form)
#   else:
#     request.method == 'POST' and form.validate():


  #return 'Form to edit product #{}.'.format(product_id)

@app.route('/products/<product_id>/edit/', methods=['GET', 'POST'])
@login_required
def product_edit(product_id):
    form = ProductForm(request.form)
    product = mongo.db.products.find_one({ "_id": ObjectId(product_id) })
    if request.method == 'POST' and form.validate():
        #product['name'] = form.name.data
        #product['description'] = form.description.data
        #product['price'] = form.price.data
        mongo.db.products.update_one({'name': product['name']},
                                     {"$set":{"name": form.name.data,
                                              "description":form.description.data,
                                              "price":form.price.data}})
        # Success. Send user back to full product list.
        return redirect(url_for('products_list'))

    form.name.data = product['name']
    form.description.data = product['description']
    form.price.data = product['price']

    # Either first load or validation error at this point.
    return render_template('product/edit.html', form=form)


@app.route('/products/<product_id>/delete/', methods=['DELETE'])
@login_required
def product_delete(product_id):
  """Delete record using HTTP DELETE, respond with JSON."""
  result = mongo.db.products.delete_one({ "_id": ObjectId(product_id) })
  if result.deleted_count == 0:
    # Abort with Not Found, but with simple JSON response.
    response = jsonify({'status': 'Not Found'})
    response.status = 404
    return response
  return jsonify({'status': 'OK'})

@app.errorhandler(404)
def error_not_found(error):
  return(render_template('error/not_found.html'), 404)

@app.errorhandler(InvalidId)
def error_not_found(error):
  return(render_template('error/not_found.html'), 404)


# Use Flask-Login to track current user in Flask's session.
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
  """Flask-Login hook to load a User instance from ID."""
  u = mongo.db.users.find_one({"username": user_id})
  if not u:
        return None
  return User(u['username'])

## Login view

@app.route('/login/', methods = ['GET', 'POST'])
def login():
  if current_user.is_authenticated:
    return redirect(url_for('products_list'))
  form = LoginForm(request.form)
  error = None
  if request.method == 'POST' and form.validate():
    username = form.username.data.lower().strip()
    password = form.password.data.lower().strip()
    user = mongo.db.users.find_one({"username": form.username.data})
    if user and User.validate_login(user['password'], form.password.data):
      user_obj = User(user['username'])
      login_user(user_obj)
      return redirect(url_for('products_list'))
    else:
      error = 'Incorrect username or password.'
  return render_template('user/login.html',
      form=form, error=error)

@app.route('/logout/')
def logout():
  logout_user()
  return redirect(url_for('products_list'))
