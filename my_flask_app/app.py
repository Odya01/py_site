from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required, logout_user, current_user
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    FloatField, SelectField, TextAreaField
)
from wtforms.validators import DataRequired, Length, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from sqlalchemy.exc import IntegrityError
from flask_wtf.csrf import CSRFProtect
import os

# Инициализация приложения Flask
app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице'
login_manager.login_message_category = 'warning'

logging.basicConfig(level=logging.INFO)

# Формы
class LoginForm(FlaskForm):
    username = StringField(
        'Имя пользователя',
        validators=[DataRequired(), Length(min=4, max=20)]
    )
    password = PasswordField(
        'Пароль',
        validators=[DataRequired(), Length(min=6)]
    )
    submit = SubmitField('Войти')


class ProductForm(FlaskForm):
    name = StringField(
        'Название',
        validators=[DataRequired(), Length(max=100)]
    )
    price = FloatField(
        'Цена',
        validators=[DataRequired(), NumberRange(min=0.01)]
    )
    brand = SelectField(
        'Бренд',
        coerce=int,
        validators=[DataRequired()]
    )
    description = TextAreaField(
        'Описание',
        validators=[Length(max=255)]
    )
    submit = SubmitField('Сохранить')


class BrandForm(FlaskForm):
    name = StringField(
        'Название бренда',
        validators=[DataRequired(), Length(max=100)]
    )
    submit = SubmitField('Сохранить')


# Модели
class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    products = db.relationship('Product', backref='brand_rel', lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=False)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


# Загрузчик пользователя
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Маршруты аутентификации
@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('welcome'))
        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('home'))


# Маршрут welcome с быстрыми метриками
@app.route('/welcome')
@login_required
def welcome():
    products_count = Product.query.count()
    brands_count = Brand.query.count()
    last_products = Product.query.order_by(Product.id.desc()).limit(5).all()
    return render_template(
        'welcome.html',
        products_count=products_count,
        brands_count=brands_count,
        last_products=last_products
    )


# Фильтр для форматирования цены
@app.template_filter('format_currency')
def format_currency(value):
    try:
        return f"{float(value):,.2f} ₽".replace(",", " ")
    except (ValueError, TypeError):
        return str(value)


# Маршруты для товаров
@app.route('/products')
@login_required
def products():
    products = Product.query.join(Brand).all()
    return render_template('products.html', products=products)


@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not current_user.is_admin:
        abort(403)
    brands = Brand.query.order_by(Brand.name).all()
    if not brands:
        flash('Сначала добавьте хотя бы один бренд!', 'danger')
        return redirect(url_for('list_brands'))

    product = Product(brand_id=brands[0].id) if id == 0 else Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.brand.choices = [(b.id, b.name) for b in brands]

    if form.validate_on_submit():
        try:
            form.populate_obj(product)
            product.brand_id = form.brand.data
            if id == 0:
                db.session.add(product)
            db.session.commit()
            flash('Товар сохранён!', 'success')
            return redirect(url_for('products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении: {e}', 'danger')

    return render_template(
        'edit_product.html',
        form=form,
        product=product,
        is_new=(id == 0)
    )


@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    if not current_user.is_admin:
        abort(403)
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Товар успешно удален', 'success')
    return redirect(url_for('products'))


# Маршруты для брендов
@app.route('/brands')
@login_required
def list_brands():
    if not current_user.is_admin:
        abort(403)
    brands = Brand.query.order_by(Brand.name).all()
    return render_template('brands.html', brands=brands)


@app.route('/add_brand', methods=['GET', 'POST'])
@login_required
def add_brand():
    if not current_user.is_admin:
        abort(403)
    form = BrandForm()
    if form.validate_on_submit():
        try:
            brand = Brand(name=form.name.data)
            db.session.add(brand)
            db.session.commit()
            flash('Бренд успешно добавлен!', 'success')
            return redirect(url_for('list_brands'))
        except IntegrityError:
            db.session.rollback()
            flash('Бренд с таким названием уже существует', 'danger')
    return render_template('add_brand.html', form=form)


@app.route('/edit_brand/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_brand(id):
    if not current_user.is_admin:
        abort(403)
    brand = Brand.query.get_or_404(id)
    form = BrandForm(obj=brand)
    if form.validate_on_submit():
        form.populate_obj(brand)
        db.session.commit()
        flash('Бренд обновлён!', 'success')
        return redirect(url_for('list_brands'))
    return render_template('edit_brand.html', form=form, brand=brand)


class DeleteForm(FlaskForm):
    pass  # для CSRF


@app.route('/delete_brand/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_brand(id):
    if not current_user.is_admin:
        abort(403)
    brand = Brand.query.get_or_404(id)
    product_count = Product.query.filter_by(brand_id=id).count()
    form = DeleteForm()
    if form.validate_on_submit():
        try:
            Product.query.filter_by(brand_id=id).delete()
            db.session.delete(brand)
            db.session.commit()
            flash(f'Удалено: бренд "{brand.name}" и {product_count} товаров', 'success')
            return redirect(url_for('list_brands'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {e}', 'danger')
    return render_template(
        'delete_brand.html',
        brand=brand,
        product_count=product_count,
        form=form
    )


# Инициализация базы данных с расширенными данными
def init_db():
    with app.app_context():
        # Если таблицы ещё не созданы — создаём
        db.create_all()

        # Заполняем тестовыми данными только раз
        if not User.query.first():
            logging.info("Создание тестовых данных...")

            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)

            # Бренды
            brands = [
                Brand(name='Intel'),
                Brand(name='AMD'),
                Brand(name='NVIDIA'),
                Brand(name='Apple'),
                Brand(name='Samsung'),
                Brand(name='Sony')
            ]
            db.session.add_all(brands)
            db.session.flush()

            # Продукты с описаниями
            products = [
                Product(
                    name='Core i7-12700K',
                    price=30000,
                    brand_id=brands[0].id,
                    description='Высокопроизводительный процессор Intel 12-го поколения'
                ),
                Product(
                    name='Ryzen 7 5800X',
                    price=25000,
                    brand_id=brands[1].id,
                    description='8-ядерный CPU AMD для геймеров и профессионалов'
                ),
                Product(
                    name='RTX 3080',
                    price=80000,
                    brand_id=brands[2].id,
                    description='Видеокарта NVIDIA для максимального FPS'
                ),
                Product(
                    name='iPhone 14 Pro',
                    price=90000,
                    brand_id=brands[3].id,
                    description='Смартфон Apple с потрясающей камерой'
                ),
                Product(
                    name='Galaxy S23 Ultra',
                    price=85000,
                    brand_id=brands[4].id,
                    description='Флагман Samsung с большим экраном'
                ),
                Product(
                    name='WH-1000XM4',
                    price=25000,
                    brand_id=brands[5].id,
                    description='Беспроводные наушники Sony с шумоподавлением'
                ),
                Product(
                    name='MacBook Pro 16"',
                    price=220000,
                    brand_id=brands[3].id,
                    description='Ноутбук Apple для профессионального дизайна и видео'
                ),
            ]
            db.session.add_all(products)

            db.session.commit()
            logging.info("Тестовые данные созданы")


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
