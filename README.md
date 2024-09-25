# Inventory Management system
This is a Flask based application for an inventory management system. It runs on flask and has postgres as its database managment system.
It allows a business manage its inventory in a smooth and efficient manner.

# Features
*Register user
  - Users can open an account here that allows them to access the inventory data base.
  - They can also log in and log out of sessions.
* Product list
  This database mangaement system allows for the logging of a product into it's product list.
   A transaction cannot be logged in the database if the item is not on the product list.
* Log transactions.
  - All transactions, typically receiving and discharging of stock are recorded in the database.
* Updating of inventory.
  - The inventory is updated automatically one a trasaction is recorded.
# Retrieval of information 
Users can retrieve information about individual items using either their ids or names. 
A get all function that allows a view of all current inventory records is also available.

# Delete information.
Items no longer needed in the warehouse can be deleted.

