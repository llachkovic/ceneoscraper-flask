from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    Response,
    request,
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import json

from app.forms import RegisterForm, LoginForm, ExtractionForm
from app.models import User, Product, Opinion, db, user_product_association
from app.util.ceneo_scraper import scrape_product_reviews
from app.util.analyzer import generate_plots
from app.util.utils import is_user_associated_with_product

main_blueprint = Blueprint("main", __name__)


# Home page
@main_blueprint.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html", user=current_user)
    return render_template("start.html")


# User registration
@main_blueprint.route("/register", methods=["GET", "POST"])
def register():
    register_form = RegisterForm()

    if register_form.validate_on_submit():
        try:
            email = register_form.email.data
            password = register_form.password.data
            username = register_form.username.data

            # Create a new user and store it in the database
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(new_user)
            db.session.commit()

            flash("Account successfully created")
            return redirect(url_for("main.login"))

        except Exception as e:
            flash(str(e))

    return render_template("register.html", form=register_form)


# User login
@main_blueprint.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        try:
            user = User.query.filter_by(email=login_form.email.data).first()
            if user and check_password_hash(
                user.password_hash, login_form.password.data
            ):
                login_user(user)
                return redirect(url_for("main.index"))
            else:
                flash("Invalid username or password")

        except Exception as e:
            flash(str(e))

    return render_template("login.html", form=login_form)


# User logout
@main_blueprint.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


# Data extraction page
@main_blueprint.route("/extraction", methods=["GET", "POST"])
@login_required
def extraction():
    extraction_form = ExtractionForm()
    if extraction_form.validate_on_submit():
        try:
            product_id = extraction_form.code.data

            # Scrape product reviews
            reviews = scrape_product_reviews(product_id)

            # Generate plots
            generate_plots(reviews, product_id)

            # Create a new product or update existing product
            product = Product(id=product_id)
            db.session.merge(product)

            # Save scraped reviews to the database
            for review in reviews:
                opinion = Opinion(
                    id=review["id"],
                    product_id=product.id,
                    recommendation=review["recommendation"],
                    stars=review["stars"],
                    pros=review["pros"],
                    cons=review["cons"],
                )
                db.session.merge(opinion)

            # Associate the product with the current user
            association = user_product_association.insert().values(
                user_id=current_user.id, product_id=product_id
            )
            db.session.execute(association)

            db.session.commit()
            return redirect(url_for("main.product_page", code=product_id))

        except Exception as e:
            flash(f"An error occurred: {str(e)}")
            db.session.rollback()

    return render_template("extraction.html", form=extraction_form)


# Product page
@main_blueprint.route("/products/<int:code>")
@login_required
def product_page(code):
    product = Product.query.get(code)
    if not product:
        abort(404)

    # Check if the current user is associated with the product
    if not is_user_associated_with_product(current_user.id, code):
        abort(403)

    # Filter reviews based on query parameters
    filters = {
        "id": request.args.get("id", ""),
        "pros": request.args.get("pros", ""),
        "cons": request.args.get("cons", ""),
    }
    rcm_true = request.args.get("rcm_true")
    rcm_false = request.args.get("rcm_false")
    stars_min = request.args.get("stars_min")
    stars_max = request.args.get("stars_max")

    query = product.opinions.filter(Opinion.id.ilike(f"%{filters['id']}%"))
    query = query.filter(Opinion.pros.ilike(f"%{filters['pros']}%"))
    query = query.filter(Opinion.cons.ilike(f"%{filters['cons']}%"))

    if rcm_true and rcm_false:
        pass
    elif rcm_true:
        query = query.filter(Opinion.recommendation == True)
    elif rcm_false:
        query = query.filter(Opinion.recommendation == False)

    if stars_min:
        query = query.filter(Opinion.stars >= float(stars_min))
    if stars_max:
        query = query.filter(Opinion.stars <= float(stars_max))

    product_reviews = query.all()
    return render_template("product.html", reviews=product_reviews, code=code)


# List of products associated with the current user
@main_blueprint.route("/products")
@login_required
def products():
    products = (
        Product.query.join(user_product_association)
        .join(User)
        .filter(User.id == current_user.id)
        .all()
    )

    products_data = []
    for product in products:
        opinion_count = product.opinions.count()
        average_stars = round(
            product.opinions.with_entities(func.avg(Opinion.stars)).scalar(), 2
        )
        pros_count, cons_count = product.opinions.with_entities(
            func.count(func.nullif(Opinion.pros, "")),
            func.count(func.nullif(Opinion.cons, "")),
        ).first()

        product_data = {
            "id": product.id,
            "opinion_count": opinion_count,
            "average_stars": average_stars,
            "pros_count": pros_count if pros_count else 0,
            "cons_count": cons_count if cons_count else 0,
        }

        products_data.append(product_data)

    return render_template("product_list.html", data=products_data)


# Download product reviews as JSON
@main_blueprint.route("/products/<int:code>/download")
@login_required
def download_product(code):
    product = Product.query.get(code)

    if not product:
        abort(404)

    # Check if the current user is associated with the product
    if not is_user_associated_with_product(current_user.id, code):
        abort(403)

    product_reviews = product.opinions.all()
    reviews_list = []
    for review in product_reviews:
        review_dict = {
            "id": review.id,
            "product_id": review.product_id,
            "recommendation": review.recommendation,
            "stars": review.stars,
            "pros": review.pros,
            "cons": review.cons,
        }
        reviews_list.append(review_dict)

    json_data = json.dumps(reviews_list, indent=4, ensure_ascii=False)

    response = Response(json_data, mimetype="application/json")
    response.headers.set(
        "Content-Disposition", "attachment", filename=f"product_{code}.json"
    )

    return response


# Product charts page
@main_blueprint.route("/products/<int:code>/charts")
@login_required
def product_charts(code):
    product = Product.query.get(code)

    if not product:
        abort(404)

    # Check if the current user is associated with the product
    if not is_user_associated_with_product(current_user.id, code):
        abort(403)

    return render_template("product_charts.html", product_id=code)
