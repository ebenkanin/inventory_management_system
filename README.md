# Inventory Management system
This is the backend for an inventory management system, built with python. It runs on flask and has postgres as its database managment system.

# Features
*Register user
  - Users can open an account here that allows them to access the inventory data base.
  - Log in and log out of sessions.
* Product list
  This database mangaement system allows for the entry of a product into it's product list.
   A transaction cannot be logged in the database if the item is not on the product list.
* Log transactions.
  - All transactions typically receiving and discharging of stocks will be logged here.
* Updating of inventory.
  - The inventory is updated automatically one a trasaction is recorded.
# Retrieval of information 
Users can retrieve information about individual items using either their ids or names. 
A get all function that allows a view of all current inventory records is also available.

# Delete information.
Items no longer needed in the warehouse can be deleted.

