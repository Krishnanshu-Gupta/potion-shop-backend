from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import uuid

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

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
        res = connection.execute(
            sqlalchemy.text("UPDATE carts SET payment = :payment WHERE id = :cart_id"),
            {"payment": cart_checkout.payment, "cart_id": cart_id}
        )
        result = connection.execute(
            sqlalchemy.text("SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id"),
            {"cart_id": cart_id}
        )
        for item_sku, quantity in result:
            potions = connection.execute(
                sqlalchemy.text("SELECT quantity, price FROM potion_inventory WHERE sku = :item_sku"),
                {"item_sku": item_sku}
            )
            quantity_pots, price = potions.first()
            if quantity > quantity_pots:
                raise HTTPException(status_code = 500, detail = f"Not enough potions for purchase")

            totalBought += quantity
            totalPaid += quantity * price

            connection.execute(
                sqlalchemy.text("UPDATE potion_inventory SET quantity = quantity - :quantity WHERE sku = :item_sku"),
                {"quantity": quantity, "item_sku": item_sku}
            )
            connection.execute(
                sqlalchemy.text("UPDATE global_inventory SET gold = gold + :paid"),
                {"paid": (quantity * price)}
            )
        connection.execute(
            sqlalchemy.text(f"DELETE FROM cart_items WHERE cart_id = :cart_id"),
            {"cart_id": cart_id}
        )
        connection.execute(
            sqlalchemy.text(f"DELETE FROM carts WHERE id = :cart_id"),
            {"cart_id": cart_id}
        )
    return {"total_potions_bought": totalBought, "total_gold_paid": totalPaid}
