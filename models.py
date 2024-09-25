
import psycopg2
from config import Config
from psycopg2 import OperationalError
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)


def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=Config.DB_PARAMETERS['host'],
            database=Config.DB_PARAMETERS['database'],
            user=Config.DB_PARAMETERS['user'],
            password=Config.DB_PARAMETERS['password'],
            port=Config.DB_PARAMETERS['port']
        )
        if not conn:
            print('Unable to connect to database')
        print('Connected to database successfully')
        return conn
    except OperationalError as e:
        print(f"Unable to connect to Database: {e}")


def create_products_table():
    with app.app_context():
        conn = connect_to_db()
        if not conn:
            return f"failed to connect to database", 400
        cursor = conn.cursor()
        try:
            print('executing command')
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS products(
            product_id SERIAL PRIMARY KEY, 
            product_name VARCHAR(100) NOT NULL,
            packaging VARCHAR(100),
            supplier VARCHAR(100),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
            """)
            conn.commit()

        except OperationalError as e:
            print(f"Error: Unable to complete task due to: {e}"), 400
        finally:
            cursor.close()
            conn.close()


def create_transactions_table():
    with app.app_context():
        conn = connect_to_db()
        if not conn:
            return f"error: Unable to connect to database", 400
        cursor = conn.cursor()

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS 
                    transactions (
                    transaction_id SERIAL PRIMARY KEY,
                    product_id INT,
                    product_name VARCHAR(100),
                    quantity INT,
                    transaction_party VARCHAR(100),
                    entered_by INT,
                    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    transaction_type VARCHAR(20),
                    
                    --Foreign key constraints
                    CONSTRAINT fk_product FOREIGN KEY (product_id) REFERENCES products (product_id) ON DELETE CASCADE,
                    CONSTRAINT fk_entered_by FOREIGN KEY (entered_by) REFERENCES users (user_id) ON DELETE SET NULL,
                    
                    -- Check constraint for transaction_type
                    CONSTRAINT chk_transaction_type CHECK (transaction_type IN ('stock in', 'stock out'))
                );
            """)
            conn.commit()

        except OperationalError as e:
            return f"Unable to complete task due to error:{e}", 400

        finally:
            cursor.close()
            conn.close()


def create_user_table():
    with app.app_context():
        conn = connect_to_db()
        if not conn:
            return f"error: Unable to connect to database", 400
        cursor = conn.cursor()

        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS 
            users(user_id SERIAL PRIMARY KEY,
            user_name VARCHAR(20) NOT NULL,
            account_name VARCHAR(50) NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(255) NOT NULL,
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
            """)

            # Check if the trigger exists
            cursor.execute("""
                   SELECT EXISTS (
                       SELECT 1
                       FROM pg_trigger
                       WHERE tgname = 'trigger_update_updated_at'
                   )
               """)

            trigger_exists = cursor.fetchone()[0]

            if not trigger_exists:

                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                       NEW.updated_at = CURRENT_TIMESTAMP;  -- Automatically update updated_at
                       RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                    
                    -- Create the trigger on the users table
                    CREATE TRIGGER trigger_update_updated_at
                    BEFORE UPDATE ON users
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            
                    """)

                conn.commit()
        except OperationalError as e:
            return f"Error: Unable to complete task{e}", 400

        finally:
            cursor.close()
            conn.close()


def create_inventory_table():
    with app.app_context():
        conn = connect_to_db()
        if not conn:
            return f"error: Unable to connect to database", 400
        cursor = conn.cursor()

        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory(
            product_id INT PRIMARY KEY, 
            product_name VARCHAR(100) NOT NULL,
            packaging VARCHAR(100),
            category VARCHAR(100),
            unit_price DECIMAL(10, 2) NOT NULL,
            quantity_available INT NOT NULL,
            minimum_balance INT,
            supplier VARCHAR(100),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (product_id)
            ON DELETE CASCADE)""")
            conn.commit()
        except OperationalError as e:
            return f"Error: Could not complete task{e}", 400
        finally:
            cursor.close()
            conn.close()


def update_inventory_trigger():
    with app.app_context():

        # connect to the database
        conn = connect_to_db()
        cursor = conn.cursor()
        try:
            # Check if trigger exists before creating it
            cursor.execute("""
                    SELECT EXISTS (
                        SELECT tgname FROM pg_trigger
                        WHERE tgname = 'update_inventory_trigger'
                    );
                    """)
            trigger_exists = cursor.fetchone()[0]
            if not trigger_exists:
                cursor.execute("""
                CREATE OR REPLACE FUNCTION f_update_inventory()
    RETURNS TRIGGER AS 
    $$
    BEGIN
        -- Check if the product and product id are in the products table and they match.
        IF EXISTS(SELECT product_id, product_name 
                  FROM products 
                  WHERE product_id = NEW.product_id 
                    AND product_name = NEW.product_name)
        THEN
            -- If transaction type is 'stock in', increase the quantity
            IF NEW.transaction_type = 'stock in' THEN 
                UPDATE inventory
                SET quantity_available = quantity_available + NEW.quantity, updated_at = NOW()
                WHERE product_id = NEW.product_id;
    
            -- If transaction type is 'stock out', decrease the quantity
            ELSIF NEW.transaction_type = 'stock out' THEN
                -- Check if the subtraction of quantity will result in a negative stock balance
                IF (SELECT quantity_available 
                    FROM inventory 
                    WHERE product_id = NEW.product_id) - NEW.quantity < 0 THEN
                    RAISE EXCEPTION 'Insufficient stock for product ID: %', NEW.product_id;
                ELSE
                    UPDATE inventory
                    SET quantity_available = quantity_available - NEW.quantity, updated_at = NOW()
                    WHERE product_id = NEW.product_id;
                END IF;
            END IF;
    
            -- Return the new row after successful operation
            RETURN NEW;
    
        ELSE
            -- Raise an exception if the product ID or name do not match
            RAISE EXCEPTION 'Product ID: % or Product Name: % does not exist or mismatch.', NEW.product_id, NEW.product_name;
        END IF;
    END;
    $$ LANGUAGE plpgsql;
     
                """)

    # Create the trigger after the function
                cursor.execute("""
                        CREATE TRIGGER update_inventory_trigger
                        AFTER INSERT OR UPDATE ON transactions
                        FOR EACH ROW
                        EXECUTE FUNCTION f_update_inventory();
                        """)
                conn.commit()
                print('Update inventory created successfully')
        except OperationalError as e:
            return f"Error: Unable to complete task:{e}"
        finally:
            cursor.close()
            conn.close()


def log_in():
    with app.app_context():
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
                return jsonify({"message": f"{user_name} Logged in successfully"}), 200
            else:
                return jsonify({"message": "Log in unsuccessful. Check username or password"}), 400
        except Exception as e:
            return jsonify({"message":f"an error occurred str{str(e)}"})


def add_product_to_product_list():
    with app.app_context():
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
            conn.close()


def add_product_to_inventory():
    with app.app_context():
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

        if not all([isinstance(product_name, str), isinstance(packaging, str), isinstance(category, str), isinstance(unit_price, float,),
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


def get_all_records():
    with app.app_context():
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
            conn.close()


def delete_item():
    with app.app_context():
        conn = connect_to_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            product_name = request.args.get('product_name')
            packaging = request.args.get('packaging')
            cursor.execute("""
            SELECT EXISTS(SELECT product_name, package from products where product_name = %s and packaging = %s)
            """,(product_name, packaging))

            data = cursor.fetchone()['data']

            if not data:
                return jsonify({"message": f"No item found for {product_name} with packaging {packaging}"}), 204
            cursor.execute("""
            DELETE FROM products WHERE product_name = %s and packaging = %s""", (product_name, packaging))

            conn.commit()
            return jsonify({"message": f"Product '{product_name}' with packaging '{packaging}' deleted successfully"}), 200
        except Exception as e:
            return jsonify({"message": f"Unable to complete request due to: {str(e)}"})
        finally:
            cursor.close()
            conn.close()

        # check if item exists in the products list


if __name__ == "__main__":
    create_products_table()
    create_user_table()
    create_transactions_table()
    create_inventory_table()
    update_inventory_trigger()




