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

carts = {}

class NewCart(BaseModel):
    customer: str

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    rand = uuid.uuid4().int
    carts[rand] = {
        "id": rand,
        "items": {

        }
    }
    print(carts)
    return {"cart_id": rand}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    return carts[cart_id]


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    cart = carts[cart_id]
    if item_sku in cart['items']:
        cart['items'][item_sku] += cart_item.quantity
    else:
        cart['items'][item_sku] = cart_item.quantity
    print(carts)
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    price = 1
    cart = carts[cart_id]
    totalBought = 0
    totalPaid = 0
    for item, quantity in cart['items'].items():
        if item in ('RED_POTION_0', 'GREEN_POTION_0', 'BLUE_POTION_0'):
            colors = ('red', 'green', 'blue')
            index = ('RED_POTION_0', 'GREEN_POTION_0', 'BLUE_POTION_0').index(item)
            color = colors[index]
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text(
                    f"SELECT num_{color}_potions FROM global_inventory")
                )

            inStore = getattr(result.first(), f"num_{color}_potions")
            if quantity > inStore:
                raise HTTPException(status_code = 500, detail = f"Not enough {color} potions for purchase")
            totalBought += quantity
            totalPaid += quantity * price # hard coded value for potion 0's

            with db.engine.begin() as connection:
                result = connection.execute(
                    sqlalchemy.text(
                        f"UPDATE global_inventory SET num_{color}_potions = num_{color}_potions - :toSell, gold = gold + (:toSell * :price)"),
                    {"toSell": quantity, "price": price}
                )

    carts.pop(cart_id)
    return {"total_potions_bought": totalBought, "total_gold_paid": totalPaid}
