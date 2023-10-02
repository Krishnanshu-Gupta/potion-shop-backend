from fastapi import APIRouter, Depends, Request
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
    cart = carts[cart_id]
    totalBought = 0
    totalPaid = 0
    for item, quantity in cart['items'].items():
        #only get red potions
        if item == "RED_POTION_0":
            with db.engine.begin() as connection:
                result = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory"))
            inStore = result.first().num_red_potions
            #if quantity > inStore:
             #   raise HTTPException(status_code=500, detail="Not enough items for purchase")
            totalBought += quantity
            totalPaid += quantity * 50 # hard coded value for red potion 0

            with db.engine.begin() as connection:
                result = connection.execute(
                    sqlalchemy.text("UPDATE global_inventory SET num_red_potions = num_red_potions - :toSell, gold = gold + (:toSell * :price)"),
                    {"toSell": quantity, "price": 50}
                )
    carts.pop(cart_id)
    return {"total_potions_bought": totalBought, "total_gold_paid": totalPaid}
