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
from sqlalchemy import func, and_
import json
import base64

from app.forms import RegisterForm, LoginForm, ExtractionForm
from app.models import User, Product, Opinion, db, user_product_association
from app.util.ceneo_scraper import scrape_product_reviews
from app.util.analyzer import generate_plots

main_blueprint = Blueprint("main", __name__)


@main_blueprint.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html", user=current_user)
    return render_template("start.html")


@main_blueprint.route("/register", methods=["GET", "POST"])
def register():
    register_form = RegisterForm()

    if register_form.validate_on_submit():
        try:
            email = register_form.email.data
            password = register_form.password.data
            username = register_form.username.data

            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(new_user)
            db.session.commit()

            print(new_user)

            flash("Account successfully created")
            return redirect(url_for("main.login"))

        except Exception:
            flash(Exception)

    return render_template("register.html", form=register_form)


@main_blueprint.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        try:
            user = User.query.filter_by(email=login_form.email.data).first()
            if check_password_hash(user.password_hash, login_form.password.data):
                login_user(user)
                return redirect(url_for("main.index"))
            else:
                flash("Invalid username or password")

        except Exception:
            flash(Exception)

    return render_template("login.html", form=login_form)


@main_blueprint.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@main_blueprint.route("/extraction", methods=["GET", "POST"])
@login_required
def extraction():
    extraction_form = ExtractionForm()
    if extraction_form.validate_on_submit():
        try:
            flash("Extraction in process")
            product_id = extraction_form.code.data
            reviews = scrape_product_reviews(product_id)
            plots = generate_plots(reviews)
            product = Product(
                id=product_id,
                stars_plot=plots["stars"],
                rcmds_plot=plots["recommendations"],
            )
            db.session.merge(product)
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


@main_blueprint.route("/products/<int:code>")
@login_required
def product_page(code):
    product = Product.query.get(code)
    if not product:
        abort(404)
    if (
        db.session.query(user_product_association)
        .filter(
            user_product_association.c.user_id == current_user.id,
            user_product_association.c.product_id == code,
        )
        .count()
        == 0
    ):
        abort(403)
    id_filter = request.args.get("id", "")
    pros_filter = request.args.get("pros", "")
    cons_filter = request.args.get("cons", "")
    rcm_true = request.args.get("rcm_true")
    rcm_false = request.args.get("rcm_false")
    stars_min = request.args.get("stars_min")
    stars_max = request.args.get("stars_max")

    query = product.opinions.filter(Opinion.id.ilike(f"%{id_filter}%"))
    query = query.filter(Opinion.pros.ilike(f"%{pros_filter}%"))
    query = query.filter(Opinion.cons.ilike(f"%{cons_filter}%"))

    if rcm_true and rcm_false:
        pass
    elif rcm_true:
        query = query.filter(Opinion.recommendation == True)
    elif rcm_false:
        query = query.filter(Opinion.recommendation == False)

    if stars_min and stars_max:
        query = query.filter(
            and_(Opinion.stars >= float(stars_min), Opinion.stars <= float(stars_max))
        )
    elif stars_min:
        query = query.filter(Opinion.stars >= float(stars_min))
    elif stars_max:
        query = query.filter(Opinion.stars <= float(stars_max))

    product_reviews = query.all()
    return render_template("product.html", reviews=product_reviews, code=code)


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
        average_stars = product.opinions.with_entities(func.avg(Opinion.stars)).scalar()
        average_stars = round(average_stars, 2)
        pros_count = product.opinions.with_entities(
            func.count(func.nullif(Opinion.pros, ""))
        ).scalar()
        cons_count = product.opinions.with_entities(
            func.count(func.nullif(Opinion.cons, ""))
        ).scalar()

        product_data = {
            "id": product.id,
            "opinion_count": opinion_count,
            "average_stars": average_stars,
            "pros_count": pros_count if pros_count else 0,
            "cons_count": cons_count if cons_count else 0,
        }

        products_data.append(product_data)

    return render_template("product_list.html", data=products_data)


@main_blueprint.route("/products/<int:code>/download")
@login_required
def download_product(code):
    product = Product.query.get(code)

    if not product:
        abort(404)

    if (
        db.session.query(user_product_association)
        .filter(
            user_product_association.c.user_id == current_user.id,
            user_product_association.c.product_id == code,
        )
        .count()
        == 0
    ):
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


@main_blueprint.route("/products/<int:code>/charts")
@login_required
def product_charts(code):
    product = Product.query.get(code)

    if not product:
        abort(404)

    if (
        db.session.query(user_product_association)
        .filter(
            user_product_association.c.user_id == current_user.id,
            user_product_association.c.product_id == code,
        )
        .count()
        == 0
    ):
        abort(403)

    stars_bin = base64.b64encode(product.stars_plot).decode("utf-8")
    rcmds_bin = base64.b64encode(product.rcmds_plot).decode("utf-8")
    return render_template(
        "product_charts.html",
        stars=stars_bin,
        recommendations=rcmds_bin,
        product_id=code,
    )
