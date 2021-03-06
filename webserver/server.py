#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, flash, session
import random

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = 'some_secret'



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "bw2585"
DB_PASSWORD = "a7TsIwBdEP"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print request.args

  if not session.get('logged_in') or not session.get('user'):
    return render_template('login.html')
  else:
    # return "Hello Boss!  <a href='/logout'>Logout</a>"
    cmd = """
    SELECT O.NO, O.time, F.item_name, F.restaurant_name, D.driver_id, O.food_score, O.driver_score
    FROM Orders O, To_order T, Order_from F, Deliver D
    WHERE O.NO = T.order_NO
    AND O.NO = F.order_NO
    AND O.NO = D.order_NO
    AND T.customer_id = %s
    """
    print session['user']
    cursor = g.conn.execute(cmd, (session['user']))
    names = []
    for result in cursor:
      print result
      names.append(list(result))  # can also be accessed using result[0]
    print names
    cursor.close()
    driver_id = []
    for i in names:
      if i[4] not in driver_id:
        driver_id.append(i[4])
    context = dict(data=names, did=driver_id)
    return render_template('index.html', **context)


@app.route('/gotoregister')
def gotoregister():
  return render_template("register.html")

@app.route('/gotoindex')
def gotoindex():
  return redirect('/')


@app.route('/gotoorder')
def gotoorder():
  cmd = """
With Score AS(
SELECT F.restaurant_name, AVG(O.food_score) rating
FROM Order_from F, Orders O
WHERE F.order_NO = O.NO
GROUP BY F.restaurant_name) 

SELECT R.name, N.state, R.boss, S.rating
FROM Restaurant R, Region N, Locate_in L, Score S
WHERE R.name = L.restaurant_name
AND L.region_id = N.id
AND S.restaurant_name = R.name
Order BY S.rating DESC
  """
  cursor = g.conn.execute(cmd)
  names = []
  for result in cursor:
    print result
    names.append(list(result))  # can also be accessed using result[0]
  for i in range(len(names)):
    names[i][0] = names[i][0].replace(" ", "_")
  print names
  cursor.close()
  context = dict(data=names)
  return render_template("order.html", **context)


@app.route('/filterlocation', methods=['POST'])
def filterlocation():
  st = request.form['state']
  cmd = """
With Score AS(
SELECT F.restaurant_name, AVG(O.food_score) rating
FROM Order_from F, Orders O
WHERE F.order_NO = O.NO
GROUP BY F.restaurant_name) 

SELECT R.name, N.state, R.boss, S.rating
FROM Restaurant R, Region N, Locate_in L, Score S
WHERE R.name = L.restaurant_name
AND L.region_id = N.id
AND S.restaurant_name = R.name
AND N.state = %s
Order BY S.rating DESC
  """
  cursor = g.conn.execute(cmd, (st,))
  names = []
  for result in cursor:
    # print result
    names.append(list(result))  # can also be accessed using result[0]
  for i in range(len(names)):
    names[i][0] = names[i][0].replace(" ", "_")
  print names
  cursor.close()
  context = dict(data=names)
  return render_template("order.html", **context)


@app.route('/searchrestaurant', methods=['POST'])
def searchrestaurant():
  st = request.form['key'].strip()
  print st
  cmd = """
  With Score AS(
  SELECT F.restaurant_name, AVG(O.food_score) rating
  FROM Order_from F, Orders O
  WHERE F.order_NO = O.NO
  GROUP BY F.restaurant_name) 
  
  SELECT R.name, N.state, R.boss, S.rating
  FROM Restaurant R, Region N, Locate_in L, Score S
  WHERE R.name = L.restaurant_name
  AND L.region_id = N.id
  AND S.restaurant_name = R.name
  AND R.name LIKE %s
  Order BY S.rating DESC"""
  print cmd
  cursor = g.conn.execute(cmd, ('%'+st+'%',))
  names = []
  for result in cursor:
    # print result
    names.append(list(result))  # can also be accessed using result[0]
  for i in range(len(names)):
    names[i][0] = names[i][0].replace(" ", "_")
  print names
  cursor.close()
  context = dict(data=names)
  return render_template("order.html", **context)


@app.route('/seedriver', methods=['POST'])
def seedriver():
  st = request.form['driver_id']
  print st
  cmd_driver_info = """
  SELECT D.id, D.name, D.phone, C.name, C.location
  FROM Driver D, Belong_to B, Delivery_company C
  WHERE D.id = %s
  AND D.id = B.driver_id
  AND B.delivery_company_name = C.name
  """
  cursor = g.conn.execute(cmd_driver_info, (st,))
  info = []
  for result in cursor:
    # print result
    info.append(list(result))  # can also be accessed using result[0]
  print info
  cursor.close()
  cmd_deliver = """
  SELECT O.no, O.time Order_time, D.time Deliver_time, driver_score
  FROM orders O, deliver D
  WHERE D.driver_id = %s
  AND O.no = D.order_no
  """
  cursor = g.conn.execute(cmd_deliver, (st,))
  delivers = []
  for result in cursor:
    # print result
    delivers.append(list(result))  # can also be accessed using result[0]
  print delivers
  cursor.close()
  context = dict(data=info, deliver=delivers)
  return render_template("deliver.html", **context)

# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  print name
  cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)';
  g.conn.execute(text(cmd), name1 = name, name2 = name);
  flash("success")
  return redirect('/')

@app.route('/rate', methods=['POST'])
def rate():
  no = request.form['no']
  f_score = float(request.form['food_score'])
  d_score = float(request.form['driver_score'])
  print no, f_score, d_score
  cmd = """
  UPDATE Orders
SET food_score = %s,
 driver_score = %s
WHERE
 Orders.NO = %s
 """
  print cmd
  g.conn.execute(cmd, (f_score, d_score, no,))
  return redirect('/')


@app.route('/pay', methods=['POST'])
def pay():
  r_name = request.form['restaurant name'].replace("_", " ")
  i_name = request.form['item name'].replace("_", " ")
  print r_name
  print i_name
  print session['user']
  cursor = g.conn.execute("SELECT DISTINCT NO FROM orders")
  orderid = []
  for result in cursor:
    print result
    orderid.append(int(result['no']))  # can also be accessed using result[0]
  print max(orderid)
  new_id = max(orderid) + 1
  cursor.close()
  hour = random.randint(0, 23)
  minute = random.randint(0, 40)
  cmd_orders = """
  INSERT INTO orders(no, time) VALUES
  (%s, %s)
  """
  cursor = g.conn.execute(cmd_orders, (str(new_id), str(hour) + ":" + str(minute)))
  cursor.close()
  cmd_to_order = """
  INSERT INTO to_order(customer_id, order_no) VALUES
  (%s, %s) 

  """
  cursor = g.conn.execute(cmd_to_order,(session['user'], str(new_id)))
  cursor.close()
  cmd_order_from = """
  INSERT INTO order_from(order_no, item_name, restaurant_name) VALUES
  (%s, %s, %s)
  """
  cursor = g.conn.execute(cmd_order_from, (str(new_id), i_name, r_name))
  cursor.close()
  cursor = g.conn.execute("SELECT DISTINCT driver_id FROM belong_to")
  driver_ids = []
  for result in cursor:
    print result
    driver_ids.append(result['driver_id'])  # can also be accessed using result[0]
  driver_idx = random.randint(0, len(driver_ids) - 1)
  cmd_deliver = """
  INSERT INTO deliver(order_no, time, driver_id) VALUES
  (%s, %s, %s)
  """
  cursor = g.conn.execute(cmd_deliver, (str(new_id), str(hour) + ":" + str(minute + 15), driver_ids[driver_idx]))
  cursor.close()
  return redirect('/')


@app.route('/torestaurant', methods=['POST'])
def torestaurant():
  name = request.form['name'].replace("_", " ")
  print name
  cmd = """
With Score AS(
SELECT F.restaurant_name, F.item_name, AVG(O.food_score) rating
FROM Orders O, Order_from F
WHERE F.restaurant_name = %s
AND F.order_NO = O.NO
GROUP BY F.restaurant_name, F.item_name
)
SELECT I.restaurant_name, I.name, I.price, S.rating
FROM Item_made_by I, Score S
WHERE I.restaurant_name = %s
AND I.name = S.item_name
ORDER BY S.rating DESC
 """
  cursor = g.conn.execute(cmd, (name, name))
  names = []
  for result in cursor:
    print result
    names.append(list(result))  # can also be accessed using result[0]
  for i in range(len(names)):
    names[i][0] = names[i][0].replace(" ", "_")
    names[i][1] = names[i][1].replace(" ", "_")
  print names
  cursor.close()
  context = dict(data=names)
  return render_template('menu.html', **context)

@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'GET':
    return render_template('login.html')
  else:
    name = request.form['username']
    passw = request.form['password']
# try:
#   name = "kb3467"
#   passw = "Kobe Bryant"
  cmd = "SELECT Count(1) FROM customer WHERE id = %s and password = %s"
  # cursor = g.conn.execute("SELECT NO FROM Orders")
  # print cmd
  cursor = g.conn.execute(cmd, (name, passw))
  # print list(cursor)
  r = False
  for result in cursor:
    if int(result[0]) > 0:
      r = True
  cursor.close()
  if r == True:
    session['logged_in'] = True
    session['user'] = name
  else:
    flash("Log in failure")
  return index()
  # except:
  #   return "except"


@app.route('/register', methods=['GET', 'POST'])
def register():
  if session['logged_in']:
    return render_template('/')
  else:
    _id = request.form['id']
    name = request.form['name']
    passw = request.form['password']
    cmd = """
    INSERT INTO customer VALUES
    (%s, %s, %s)
    """
    try:
      cursor = g.conn.execute(cmd, (_id, name, passw))
      flash("Register Success!")
      return redirect('/')
    except:
      flash("Id already used!")
      return render_template('register.html')


@app.route("/logout")
def logout():
  session['logged_in'] = False
  return index()




if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
