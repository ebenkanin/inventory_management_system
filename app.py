from flask import Flask, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from models import (connect_to_db)
from config import Config
from dotenv import load_dotenv

load_dotenv('capstone.env')

app = Flask(__name__)
app.config.from_object(Config)
app.app_context()


@app.route("/register-user", methods=['POST'])
def register_user():
    conn = connect_to_db()
    if not conn:
        return jsonify({"Error": "Unable to connect to database"}), 404
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:

        data = request.get_json()

        required_fields = ['username', 'account_name', 'password', 'role', 'email']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({"error": f"missing the following required fields: {', '.join(missing_fields)}"}), 400

        username = data['username']
        account_name = data['account_name']
        password = generate_password_hash(data['password'])
        role = data['role']
        email = data['email']

        if not all([isinstance(username, str), isinstance(account_name, str), isinstance(password, str), isinstance(role, str),
                    isinstance(email, str)]):
            return jsonify({"message": "Check input data types and format"})

            # Check if the user already exists
        cursor.execute("""
           SELECT user_name, account_name FROM users 
           WHERE user_name = %s AND account_name = %s
           """, (username, account_name))

        user = cursor.fetchone()

        if user:
            return jsonify({"message": "This user already exists. Log in to your account"}), 409

        # Insert the new user into the database
        cursor.execute("""
           INSERT INTO users(user_name, account_name, password, role, email) 
           VALUES(%s, %s, %s, %s, %s)
           """, (username, account_name, password, role, email))

        conn.commit()

    except Exception as e:
        return jsonify({"message": f"Unable to register user due to: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"message": f"{username} successfully registered"}), 201


# logging in user
@app.route("/log-in", methods=['POST'])
def log_in():

    conn = connect_to_db()
    if not conn:
        return jsonify({"message": "Unable to connect to database"})
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:

        # retrieving data from request
        data = request.get_json()

        user_name = data['user_name']
        password = data['password']

        cursor.execute("SELECT user_name, password from users where user_name = %s", (user_name,))

        db_results = cursor.fetchone()
        print(db_results)

        cursor.close()

        conn.close()

        if db_results and check_password_hash(db_results['password'], password):
            session['username'] = user_name
            session.permanent = True
            return jsonify({"message": f"{user_name} Logged in successfully"}), 200
        else:
            return jsonify({"message": "Log in unsuccessful. Check username or password"}), 400
    except Exception as e:
        return jsonify({"message": f"an error occurred str{str(e)}"})  # calling the log in function to enable user log in.


@app.route("/logout", methods=['POST'])
def log_out():
    session.clear()
    return jsonify({"message":"Logged out successfully"}), 200


@app.route("/create-product", methods=['POST'])
def add_product_to_product_list():

    conn = connect_to_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        data = request.get_json()
        product_name = data['product_name']
        packaging = data['packaging']
        supplier = data['supplier']

        required_field = ['product_name', 'packaging', 'supplier']
        missing_fields = [field for field in required_field if field not in data]
        if missing_fields:
            return jsonify({"error": f"missing the following required fields: {', '.join(missing_fields)}"}), 400

        if not all([isinstance(product_name, str), isinstance(packaging, str), isinstance(supplier, str)]):
            return jsonify({"message": "Check input data types and format"})

        #  Check if the product exists
        cursor.execute("""
           SELECT product_name, packaging, supplier FROM products WHERE product_name = %s AND packaging = %s AND supplier = %s""",
                       (product_name, packaging, supplier))

        product = cursor.fetchone()

        if product:
            return jsonify({"message": f"Product with name {product_name}, packaging {packaging}, and supplier {supplier} already exists."}), 400

        # Insert the product if it doesn't exist

        cursor.execute("""
        INSERT INTO products(product_name, packaging, supplier) VALUES(%s,%s,%s)
        """, (product_name, packaging, supplier))

        conn.commit()

        if cursor.rowcount > 0:
            return jsonify({"message": f"{product_name} added successfully"}), 201
        else:
            return jsonify({"message": "Unable to add product"}), 400
    except Exception as e:
        return jsonify({"message": f"Unable to complete request due to :{str(e)}"}), 500

    finally:
        cursor.close()
        conn.close()  # log product to product list before it can be added to the inventory


@app.route("/add-product", methods=['POST'])
def add_product_to_inventory():
    conn = connect_to_db()

    if not conn:
        return jsonify({"message": "could connect to database."}), 500

    cursor = conn.cursor(cursor_factory=RealDictCursor)
    # retrieving data from body
    req_fields = ['product_name', 'packaging', 'category', 'unit_price', 'quantity', 'supplier']
    data = request.get_json()

    missing_fields = [field for field in req_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"missing the following required fields {', '.join(missing_fields)}"})

    product_name = data['product_name']
    packaging = data['packaging']
    category = data['category']
    unit_price = data['unit_price']
    quantity = data['quantity']
    minimum_balance = data['minimum_balance']
    supplier = data['supplier']

    if not all([isinstance(product_name, str), isinstance(packaging, str), isinstance(category, str), isinstance(unit_price, float, ),
                isinstance(quantity, int), isinstance(minimum_balance, int), isinstance(supplier, str)]):
        return jsonify({"message": "Check input data types and format"})

    try:
        # Look up product_id based on product_name

        cursor.execute("SELECT product_id, packaging FROM products WHERE product_name = %s and packaging = %s", (product_name, packaging))
        product = cursor.fetchone()

        if not product:
            return jsonify({"message": f"Product with name {product_name} does not exist."}), 404

        product_id = product['product_id']
        packaging = product['packaging']
        # executing the insert statement

        cursor.execute("INSERT INTO Inventory(product_id, product_name, packaging, category, unit_price, quantity_available,minimum_balance,"
                       "supplier)VALUES(%s,"
                       "%s,"
                       "%s,%s,%s,%s,%s,%s)",
                       (product_id, product_name, packaging, category, unit_price, quantity, minimum_balance, supplier))

        if cursor.rowcount == 0:
            return jsonify({"message": f"unable to add {product_name}"})

        conn.commit()

        return jsonify({"message": "product added successfully"}), 201

    except Exception as e:
        return jsonify({"message": f"error: {str(e)}"})
    finally:
        cursor.close()
        conn.close()


@app.route("/get-all-records", methods=['GET'])
def get_all_records():
    conn = connect_to_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM inventory")

        data = cursor.fetchall()
        print(data)
        if not data:
            return jsonify({"message": "No data available"}), 204

        records = []

        for row in data:
            record = {
                "product_id": row['product_id'],
                "product_name": row['product_name'],
                "packaging": row['packaging'],
                "category": row['category'],
                "unit_price": row['unit_price'],
                "quantity_available": row['quantity_available'],
                "minimum_balance": row['minimum_balance'],
                "supplier": row['supplier'],
                "updated_at": row['updated_at']
            }
            records.append(record)
            print(records)

        return jsonify(records), 200

    except Exception as e:
        print(f"Error:{e}")
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()  # calling the get_all_records


@app.route("/get-item", methods=['GET'])
def get_item():

    conn = connect_to_db()
    cursor = conn.cursor()

    search_item = request.args.get('search_item')
    try:

        if not search_item:
            return jsonify({"message": "No search item provided"}), 400

        # Check if the search item is numeric (for product_id) or not (for product_name)
        if search_item.isdigit():
            # Search by product_id if it's a number
            cursor.execute("SELECT product_id, product_name FROM inventory WHERE product_id = %s", (search_item,))
        else:
            # Search by product_name if it's a string
            cursor.execute("SELECT product_id, product_name FROM inventory WHERE product_name ILIKE %s", (f'%{search_item}%',))

        data = cursor.fetchall()

        if not data:
            return jsonify({"message": "Item not found"}), 404

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"message": f"Could not complete request due to:{str(e)}"}), 404
    finally:
        cursor.close()
        conn.close()


@app.route("/update-stock", methods=['POST'])
def update_stock():
    conn = connect_to_db()

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        data = request.get_json()
        # validating all fields

        required_fields = ['product_id', 'product_name', 'quantity', 'transaction_party', 'user_id', 'transaction_type']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"missing the following required fields {', '.join(missing_fields)}"}), 400

        # unpacking data

        product_id = data['product_id']
        product_name = data['product_name']
        quantity = data['quantity']
        transaction_party = data['transaction_party']
        user_id = data['user_id']
        transaction_type = data['transaction_type']

        if not all([isinstance(product_id, int), isinstance(product_name, str),
                    isinstance(quantity, int), isinstance(transaction_party, str), isinstance(user_id, int),
                    isinstance(transaction_type, str)]):

            return f"Error. Check input format and data type"

        cursor.execute("""
        INSERT INTO transactions(product_id, product_name, quantity, transaction_party, entered_by, transaction_type)
        VALUES(%s,%s,%s,%s,%s,%s)
        """, (product_id, product_name, quantity, transaction_party, user_id, transaction_type))

        if cursor.rowcount == 0:
            return jsonify({"error": "Unable to log transaction"}), 400
        conn.commit()

    except Exception as e:
        return jsonify({"error": f"Unable to complete request due to {str(e)}"}), 500

    finally:
        cursor.close()
        conn.close()
        return f"Transaction logged successfully", 201
# calls the update stock function. Sets the trigger that looks up product and if exists, inserts into the
# transactions table and triggers the update_inventory trigger


@app.route("/delete-product", methods=['DELETE'])
def delete_item():

    conn = connect_to_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        product_name = request.args.get('product_name')
        packaging = request.args.get('packaging')
        cursor.execute("""
        SELECT EXISTS(SELECT product_name, package from products where product_name = %s and packaging = %s)
        """, (product_name, packaging))

        data = cursor.fetchone()['data']

        if not data:
            return jsonify({"message": f"No item found for {product_name} with packaging {packaging}"}), 204
        cursor.execute("""
        DELETE FROM products WHERE product_name = %s and packaging = %s""", (product_name, packaging))

        conn.commit()
        return jsonify({"message": f"Product '{product_name}' with packaging '{packaging}' deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": f"Unable to complete request due to: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)
