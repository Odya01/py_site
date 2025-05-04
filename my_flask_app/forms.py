from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError
from models import Brand

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', 
                          validators=[DataRequired(message="Поле обязательно для заполнения"),
                                      Length(min=4, max=20, message="Имя пользователя должно быть от 4 до 20 символов")],
                          render_kw={"placeholder": "Введите имя пользователя"})
    password = PasswordField('Пароль',
                            validators=[DataRequired(message="Поле обязательно для заполнения"),
                                       Length(min=6, message="Пароль должен содержать минимум 6 символов")],
                            render_kw={"placeholder": "Введите пароль"})
    submit = SubmitField('Войти', render_kw={"class": "btn btn-primary"})

class BrandForm(FlaskForm):
    name = StringField('Название бренда',
                      validators=[DataRequired(message="Поле обязательно для заполнения"),
                                 Length(max=100, message="Название не должно превышать 100 символов")],
                      render_kw={"placeholder": "Например: Intel, AMD"})
    submit = SubmitField('Сохранить', render_kw={"class": "btn btn-success"})

    def validate_name(self, field):
        if Brand.query.filter_by(name=field.data).first():
            raise ValidationError('Бренд с таким названием уже существует')

class ProductForm(FlaskForm):
    name = StringField('Название товара',
                      validators=[DataRequired(message="Поле обязательно для заполнения"),
                                 Length(max=100, message="Название не должно превышать 100 символов")],
                      render_kw={"placeholder": "Например: Core i7-12700K"})
    price = FloatField('Цена',
                      validators=[DataRequired(message="Укажите цену"),
                                 NumberRange(min=0.01, message="Цена должна быть больше 0")],
                      render_kw={"placeholder": "Цена в рублях", "step": "0.01"})
    description = TextAreaField('Описание',
                              validators=[Length(max=500, message="Описание не должно превышать 500 символов")],
                              render_kw={"placeholder": "Технические характеристики...", "rows": 4})
    brand = SelectField('Бренд',
                       coerce=int,
                       validators=[DataRequired(message="Выберите бренд")],
                       render_kw={"class": "form-select"})
    submit = SubmitField('Сохранить', render_kw={"class": "btn btn-success"})

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.brand.choices = [(brand.id, brand.name) for brand in Brand.query.order_by(Brand.name).all()]