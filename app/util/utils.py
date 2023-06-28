from app.models import db, user_product_association


# Check if the current user is associated with the product
def is_user_associated_with_product(user_id, product_id):
    return (
        db.session.query(user_product_association)
        .filter(
            user_product_association.c.user_id == user_id,
            user_product_association.c.product_id == product_id,
        )
        .count()
        > 0
    )
