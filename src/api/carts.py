from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import uuid
import re
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "1",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku,
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """
    sql = """SELECT shop_name, description, name, amount, sku, created_at
            FROM potion_ledger
            JOIN potion_inventory ON potion_ledger.potion_id = potion_inventory.id
            WHERE shop_name IS NOT NULL AND shop_name != 'bottler'
                AND (:customer_name = '' OR shop_name ILIKE :customer_name)
                AND (:potion_sku = '' OR sku ILIKE :potion_sku)
            """

    order = "DESC"
    if sort_order == search_sort_order.asc:
        order = "ASC"

    col = "potion_ledger.created_at"
    if sort_col == search_sort_options.line_item_total:
        col = "CAST(SUBSTRING(description FROM POSITION('for:' IN description) + 4) AS INTEGER)"
    elif sort_col == search_sort_options.item_sku:
        col = "potion_inventory.sku"
    elif sort_col == search_sort_options.customer_name:
        col = "potion_ledger.shop_name"

    sql += "ORDER BY " + col + " " + order
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql),
                                    {"customer_name": customer_name, "potion_sku": potion_sku})

    lst = []
    ind = 1
    for row in result:
       lst.append({
           "line_item_id": ind,
           "item_sku": str(row.amount * -1) + " " + row.name + (" potions" if (row.amount * -1) > 1 else " potion"),
           "customer_name": row.shop_name,
           "line_item_total": int(re.search(r'for:\s*(\d+)', row.description).group(1)),
           "timestamp": row.created_at
       })
       ind += 1

    num_res = len(lst)
    results_per_page = 5
    num_pages = (num_res + results_per_page - 1) // results_per_page
    page = int(search_page)
    start_index = (page - 1) * results_per_page
    end_index = page * results_per_page

    return {
        "previous": str(page - 1) if page > 1 else "",
        "next": str(page + 1) if page < num_pages else "",
        "results": lst[start_index : end_index]
    }


class NewCart(BaseModel):
    customer: str

@router.post("/")
def create_cart(new_cart: NewCart):
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("INSERT INTO carts (customer_name) VALUES (:customer_name) RETURNING id"),
            {"customer_name": new_cart.customer}
        )
        cart_id = result.scalar()
    return {"cart_id": cart_id}

@router.get("/{cart_id}")
def get_cart(cart_id: int):
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT * FROM carts WHERE id = :cart_id"),
            {"cart_id": cart_id}
        )
        cart = result.first()
        cart_dict = {
            "id": cart.id,
            "customer_name": cart.customer_name,
            "payment": cart.payment,
        }
    return cart_dict

class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT 1 FROM cart_items WHERE item_sku = :item_sku AND cart_id = :cart_id"),
            {"item_sku": item_sku, "cart_id": cart_id}
        )
        item_exists = bool(result.scalar())
        flag = False
        if item_exists:
            connection.execute(
                sqlalchemy.text("UPDATE cart_items SET quantity = :quantity WHERE item_sku = :item_sku AND cart_id = :cart_id"),
                {"quantity": cart_item.quantity, "item_sku": item_sku, "cart_id": cart_id}
            )
            flag = True
        else:
            connection.execute(
                sqlalchemy.text("INSERT INTO cart_items (cart_id, quantity, item_sku) VALUES (:cart_id, :quantity, :item_sku)"),
                {"cart_id": cart_id, "quantity": cart_item.quantity, "item_sku": item_sku}
            )
            flag = True
    return flag


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    totalBought = 0
    totalPaid = 0
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("UPDATE carts SET payment = :payment WHERE id = :cart_id"),
            {"payment": cart_checkout.payment, "cart_id": cart_id}
        )
        result = connection.execute(
            sqlalchemy.text("SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id"),
            {"cart_id": cart_id}
        )
        for item_sku, quantity in result:
            result = connection.execute(
                sqlalchemy.text("""SELECT amount, price
                                FROM potion_ledger
                                JOIN potion_inventory ON potion_ledger.potion_id = potion_inventory.id
                                WHERE sku = :item_sku
                                ORDER BY potion_ledger.created_at"""),
                {"item_sku": item_sku})

            quantity_pots = 0
            price = 0
            for row in result:
                quantity_pots += row.amount
                price = row.price

            if quantity > quantity_pots:
                raise HTTPException(status_code = 500, detail = f"Not enough potions for purchase")

            totalBought += quantity
            totalPaid += quantity * price

            connection.execute(
                sqlalchemy.text("""INSERT INTO potion_ledger (amount, potion_id, shop_name, description)
                                VALUES (:amount, (SELECT id FROM potion_inventory WHERE sku = :item_sku),
                                (SELECT customer_name
                                FROM cart_items
                                JOIN carts ON carts.id = cart_items.cart_id LIMIT 1), :description)"""),
                {"amount": quantity * -1, "item_sku": item_sku, "shop_name": "",
                 "description": "Sold: " + str(item_sku) + ", for: " + str(price * quantity)}
            )

            connection.execute(
                sqlalchemy.text("""INSERT INTO gold_ledger (amount, shop_name, description)
                                VALUES (:amount, (SELECT customer_name
                                FROM cart_items
                                JOIN carts ON carts.id = cart_items.cart_id LIMIT 1), :description)"""),
                {"amount": quantity * price,
                 "description": "Sold: " + str(item_sku) + ", how many: " + str(quantity)}
            )
    return {"total_potions_bought": totalBought, "total_gold_paid": totalPaid}
