from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import case
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectField, IntegerField, FloatField, FileField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, InputRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Stelle sicher, dass der Upload-Ordner existiert
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bitte melden Sie sich an, um auf den Admin-Bereich zuzugreifen.'
login_manager.login_message_category = 'error'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class MenuCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(50), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    is_drink_category = db.Column(db.Boolean, default=False)
    items = db.relationship('MenuItem', backref='category', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_category.id'), nullable=False)
    image_path = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)
    is_lunch_special = db.Column(db.Boolean, default=False)
    
    # Dietary and characteristic attributes
    vegetarian = db.Column(db.Boolean, default=False)
    vegan = db.Column(db.Boolean, default=False)
    spicy = db.Column(db.Boolean, default=False)
    gluten_free = db.Column(db.Boolean, default=False)
    lactose_free = db.Column(db.Boolean, default=False)
    kid_friendly = db.Column(db.Boolean, default=False)
    alcohol_free = db.Column(db.Boolean, default=False)
    contains_alcohol = db.Column(db.Boolean, default=False)
    homemade = db.Column(db.Boolean, default=False)
    sugar_free = db.Column(db.Boolean, default=False)
    recommended = db.Column(db.Boolean, default=False)

class OpeningHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20), nullable=False)
    open_time_1 = db.Column(db.String(5))
    close_time_1 = db.Column(db.String(5))
    open_time_2 = db.Column(db.String(5))
    close_time_2 = db.Column(db.String(5))
    closed = db.Column(db.Boolean, default=False)
    vacation_start = db.Column(db.String(10))  # Store as string in YYYY-MM-DD format
    vacation_end = db.Column(db.String(10))    # Store as string in YYYY-MM-DD format
    vacation_active = db.Column(db.Boolean, default=False)

class GalleryImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.Column(db.Integer, default=0)

class OpeningHoursForm(FlaskForm):
    monday_hours = StringField('Montag')
    tuesday_hours = StringField('Dienstag')
    wednesday_hours = StringField('Mittwoch')
    thursday_hours = StringField('Donnerstag')
    friday_hours = StringField('Freitag')
    saturday_hours = StringField('Samstag')
    sunday_hours = StringField('Sonntag')

class MenuItemForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    price = FloatField('Preis', validators=[DataRequired()])
    category = SelectField('Kategorie', coerce=int)
    image = FileField('Bild', validators=[FileAllowed(['jpg', 'png'], 'Nur Bilder erlaubt')])
    vegetarian = BooleanField('Vegetarisch')
    vegan = BooleanField('Vegan')
    spicy = BooleanField('Scharf')
    gluten_free = BooleanField('Glutenfrei')
    lactose_free = BooleanField('Laktosefrei')
    kid_friendly = BooleanField('Kinderfreundlich')
    alcohol_free = BooleanField('Alkoholfrei')
    contains_alcohol = BooleanField('Enthält Alkohol')
    homemade = BooleanField('Hausgemacht')
    sugar_free = BooleanField('Zuckerfrei')
    recommended = BooleanField('Empfohlen')

class GalleryImageForm(FlaskForm):
    title = StringField('Titel', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    image = FileField('Bild', validators=[FileAllowed(['jpg', 'png'], 'Nur Bilder erlaubt')])

def init_db():
    db.create_all()
    
    # Initialize opening hours if not exists
    if not OpeningHours.query.first():
        days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        for day in days:
            hours = OpeningHours(
                day=day,
                open_time_1='11:30',
                close_time_1='14:30',
                open_time_2='17:30',
                close_time_2='22:00',
                closed=False,
                vacation_active=False,
                vacation_start=None,
                vacation_end=None
            )
            db.session.add(hours)
        db.session.commit()

    # Initialize admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')  # Change this password!
        db.session.add(admin)
        db.session.commit()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def index():
    image_path = os.path.join(app.static_folder, 'img/awards/Lokal_Des_Jahres_Deutschlansd_2024_Bild-removebg-preview.png')
    print(f"Checking image path: {image_path}")
    print(f"File exists: {os.path.exists(image_path)}")
    try:
        categories = MenuCategory.query.order_by(MenuCategory.order).all()
        menu_items = MenuItem.query.all()
        opening_hours = OpeningHours.query.order_by(
            case(
                (OpeningHours.day == 'Montag', 1),
                (OpeningHours.day == 'Dienstag', 2),
                (OpeningHours.day == 'Mittwoch', 3),
                (OpeningHours.day == 'Donnerstag', 4),
                (OpeningHours.day == 'Freitag', 5),
                (OpeningHours.day == 'Samstag', 6),
                (OpeningHours.day == 'Sonntag', 7)
            )
        ).all()
        return render_template('index.html', categories=categories, menu_items=menu_items, opening_hours=opening_hours)
    except Exception as e:
        print(f"Fehler auf der Homepage: {str(e)}")
        init_db()  # Initialisiere die Datenbank falls sie nicht existiert
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin'))
        else:
            flash('Ungültige Anmeldedaten')
    
    return render_template('admin/login.html')

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('admin/index.html')

@app.route('/admin/menu')
@login_required
def admin_menu():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    menu_items = MenuItem.query.order_by(MenuItem.order).all()
    return render_template('admin/menu.html', categories=categories, menu_items=menu_items)

@app.route('/admin/menu/add', methods=['GET', 'POST'])
@login_required
def admin_menu_add():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category_id = int(request.form.get('category'))
        vegetarian = bool(request.form.get('vegetarian'))
        vegan = bool(request.form.get('vegan'))
        spicy = bool(request.form.get('spicy'))
        gluten_free = bool(request.form.get('gluten_free'))
        lactose_free = bool(request.form.get('lactose_free'))
        kid_friendly = bool(request.form.get('kid_friendly'))
        alcohol_free = bool(request.form.get('alcohol_free'))
        contains_alcohol = bool(request.form.get('contains_alcohol'))
        homemade = bool(request.form.get('homemade'))
        sugar_free = bool(request.form.get('sugar_free'))
        recommended = bool(request.form.get('recommended'))
        
        image = request.files.get('image')
        image_path = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            # Speichere das Bild im uploads Ordner
            image_path = 'uploads/' + filename
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(full_path)
            # Resize and crop the image
            resize_and_crop_image(full_path)
        
        menu_item = MenuItem(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            vegetarian=vegetarian,
            vegan=vegan,
            spicy=spicy,
            gluten_free=gluten_free,
            lactose_free=lactose_free,
            kid_friendly=kid_friendly,
            alcohol_free=alcohol_free,
            contains_alcohol=contains_alcohol,
            homemade=homemade,
            sugar_free=sugar_free,
            recommended=recommended,
            image_path=image_path
        )
        
        db.session.add(menu_item)
        db.session.commit()
        
        flash('Menüpunkt erfolgreich hinzugefügt')
    except Exception as e:
        flash(f'Fehler beim Hinzufügen des Menüpunkts: {str(e)}')
    
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/edit/<int:id>', methods=['GET'])
def admin_menu_edit(id):
    item = MenuItem.query.get_or_404(id)
    return jsonify({
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': item.price,
        'category_id': item.category_id,
        'image_path': item.image_path,
        'vegetarian': item.vegetarian,
        'vegan': item.vegan,
        'spicy': item.spicy,
        'gluten_free': item.gluten_free,
        'lactose_free': item.lactose_free,
        'kid_friendly': item.kid_friendly,
        'alcohol_free': item.alcohol_free,
        'contains_alcohol': item.contains_alcohol,
        'homemade': item.homemade,
        'sugar_free': item.sugar_free,
        'recommended': item.recommended
    })

@app.route('/admin/menu/edit', methods=['POST'])
@login_required
def admin_menu_edit_post():
    item_id = request.form.get('id')
    item = MenuItem.query.get_or_404(item_id)
    
    item.name = request.form['name']
    item.description = request.form['description']
    item.price = float(request.form['price'])
    item.category_id = int(request.form['category'])
    
    # Handle image removal
    remove_image = request.form.get('remove_image') == 'true'
    if remove_image and item.image_path:
        # Delete the existing image file
        try:
            os.remove(os.path.join(app.root_path, 'static', item.image_path))
        except OSError:
            pass  # File might not exist
        item.image_path = None
    
    # Handle new image upload
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            # Delete old image if it exists
            if item.image_path:
                try:
                    os.remove(os.path.join(app.root_path, 'static', item.image_path))
                except OSError:
                    pass  # File might not exist
            
            # Save new image
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(filepath)
            
            # Resize and crop the image
            resize_and_crop_image(filepath)
            
            # Update database with new image path
            item.image_path = os.path.join('uploads', new_filename).replace('\\', '/')
    
    # Update other fields
    item.vegetarian = 'vegetarian' in request.form
    item.vegan = 'vegan' in request.form
    item.spicy = 'spicy' in request.form
    item.gluten_free = 'gluten_free' in request.form
    item.lactose_free = 'lactose_free' in request.form
    item.kid_friendly = 'kid_friendly' in request.form
    item.alcohol_free = 'alcohol_free' in request.form
    item.contains_alcohol = 'contains_alcohol' in request.form
    item.homemade = 'homemade' in request.form
    item.sugar_free = 'sugar_free' in request.form
    item.recommended = 'recommended' in request.form
    
    db.session.commit()
    flash('Menüpunkt wurde erfolgreich aktualisiert!', 'success')
    return redirect(url_for('admin_menu'))

@app.route('/admin/menu/delete/<int:id>')
@login_required
def admin_menu_delete(id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    try:
        menu_item = MenuItem.query.get_or_404(id)
        
        # Bild löschen wenn vorhanden
        if menu_item.image_path:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(menu_item.image_path))
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(menu_item)
        db.session.commit()
        flash('Menüpunkt erfolgreich gelöscht')
    except Exception as e:
        flash(f'Fehler beim Löschen des Menüpunkts: {str(e)}')
    
    return redirect(url_for('admin_menu'))

@app.route('/admin/categories')
@login_required
def admin_categories():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
@login_required
def admin_add_category():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    try:
        name = request.form.get('name').lower()
        display_name = request.form.get('display_name')
        order = int(request.form.get('order'))
        is_drink_category = bool(request.form.get('is_drink_category'))
        
        category = MenuCategory(
            name=name,
            display_name=display_name,
            order=order,
            is_drink_category=is_drink_category
        )
        
        db.session.add(category)
        db.session.commit()
        flash('Kategorie erfolgreich hinzugefügt', 'success')
    except Exception as e:
        flash(f'Fehler beim Hinzufügen der Kategorie: {str(e)}', 'error')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:id>', methods=['POST'])
@login_required
def admin_delete_category(id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    try:
        category = MenuCategory.query.get_or_404(id)
        db.session.delete(category)
        db.session.commit()
        flash('Kategorie erfolgreich gelöscht', 'success')
    except Exception as e:
        flash(f'Fehler beim Löschen der Kategorie: {str(e)}', 'error')
    
    return redirect(url_for('admin_categories'))

@app.route('/admin/hours')
@login_required
def admin_hours():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    opening_hours = OpeningHours.query.order_by(
        case(
            (OpeningHours.day == 'Montag', 1),
            (OpeningHours.day == 'Dienstag', 2),
            (OpeningHours.day == 'Mittwoch', 3),
            (OpeningHours.day == 'Donnerstag', 4),
            (OpeningHours.day == 'Freitag', 5),
            (OpeningHours.day == 'Samstag', 6),
            (OpeningHours.day == 'Sonntag', 7)
        )
    ).all()
    return render_template('admin/hours.html', opening_hours=opening_hours)

@app.route('/admin/hours/save', methods=['POST'])
@login_required
def admin_save_hours():
    try:
        # Handle vacation dates first
        vacation_active = 'vacation_active' in request.form
        vacation_start = request.form.get('vacation_start')
        vacation_end = request.form.get('vacation_end')

        # Update all records with vacation info (we keep it in sync across all days)
        if vacation_active and vacation_start and vacation_end:
            OpeningHours.query.update({
                'vacation_active': True,
                'vacation_start': vacation_start,
                'vacation_end': vacation_end
            })
        else:
            OpeningHours.query.update({
                'vacation_active': False,
                'vacation_start': None,
                'vacation_end': None
            })

        # Handle regular opening hours
        days = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        for day in days:
            hours = OpeningHours.query.filter_by(day=day).first()
            if not hours:
                continue

            closed = day + '_closed' in request.form
            hours.closed = closed

            if not closed:
                hours.open_time_1 = request.form.get(day + '_open_1', '')
                hours.close_time_1 = request.form.get(day + '_close_1', '')
                hours.open_time_2 = request.form.get(day + '_open_2', '')
                hours.close_time_2 = request.form.get(day + '_close_2', '')
            else:
                hours.open_time_1 = ''
                hours.close_time_1 = ''
                hours.open_time_2 = ''
                hours.close_time_2 = ''

        db.session.commit()
        flash('Öffnungszeiten wurden erfolgreich aktualisiert.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Fehler beim Speichern der Öffnungszeiten: ' + str(e), 'error')

    return redirect(url_for('admin_hours'))

@app.route('/menu')
def menu():
    categories = MenuCategory.query.order_by(MenuCategory.order).all()
    menu_items = MenuItem.query.all()
    return render_template('menu.html', categories=categories, menu_items=menu_items)

@app.route('/impressum')
def impressum():
    return render_template('impressum.html')

@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/galerie')
def gallery():
    images = GalleryImage.query.order_by(GalleryImage.order).all()
    return render_template('gallery.html', images=images)

@app.route('/admin/galerie', methods=['GET'])
@login_required
def admin_gallery():
    images = GalleryImage.query.order_by(GalleryImage.order).all()
    return render_template('admin/gallery.html', images=images)

@app.route('/admin/galerie/add', methods=['GET', 'POST'])
@login_required
def admin_gallery_add():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        image = request.files.get('image')
        
        if image:
            # Generate a unique filename using timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(image.filename)
            filename = f"{timestamp}_{original_filename}"
            
            # Ensure the gallery upload directory exists
            gallery_path = os.path.join(app.static_folder, 'uploads', 'gallery')
            os.makedirs(gallery_path, exist_ok=True)
            
            # Save the image
            image_path = os.path.join(gallery_path, filename)
            image.save(image_path)
            
            # Resize and optimize the image
            try:
                resize_and_crop_image(image_path, output_size=(800, 600))
            except Exception as e:
                app.logger.error(f"Error resizing image: {str(e)}")
            
            # Create database entry with relative path
            relative_path = os.path.join('uploads', 'gallery', filename).replace('\\', '/')
            new_image = GalleryImage(
                title=title,
                description=description,
                image_path=relative_path
            )
            
            try:
                db.session.add(new_image)
                db.session.commit()
                flash('Bild wurde erfolgreich hinzugefügt!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Fehler beim Speichern des Bildes: {str(e)}', 'error')
                if os.path.exists(image_path):
                    os.remove(image_path)
            
            return redirect(url_for('admin_gallery'))
        else:
            flash('Bitte wählen Sie ein Bild aus.', 'error')
    
    return render_template('admin/gallery_add.html')

@app.route('/admin/galerie/delete/<int:id>')
@login_required
def admin_gallery_delete(id):
    image = GalleryImage.query.get_or_404(id)
    if image.image_path:
        try:
            os.remove(os.path.join(app.static_folder, image.image_path))
        except:
            pass
    db.session.delete(image)
    db.session.commit()
    flash('Bild wurde erfolgreich gelöscht!', 'success')
    return redirect(url_for('admin_gallery'))

@app.route('/salt-story')
def salt_story():
    return render_template('salt_story.html')

@app.route('/family-story')
def family_story():
    return render_template('family_story.html')

@app.route('/experience-story')
def experience_story():
    return render_template('experience_story.html')

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

def resize_and_crop_image(image_path, output_size=(400, 180)):
    with Image.open(image_path) as img:
        # Convert to RGB if image is in RGBA mode
        if img.mode == 'RGBA':
            img = img.convert('RGB')
            
        # Calculate aspect ratios
        target_ratio = output_size[0] / output_size[1]
        img_ratio = img.width / img.height
        
        if img_ratio > target_ratio:
            # Image is wider than target ratio
            new_width = int(output_size[1] * img_ratio)
            new_height = output_size[1]
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Center crop
            left = (new_width - output_size[0]) // 2
            img = img.crop((left, 0, left + output_size[0], output_size[1]))
        else:
            # Image is taller than target ratio
            new_width = output_size[0]
            new_height = int(output_size[0] / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Center crop
            top = (new_height - output_size[1]) // 2
            img = img.crop((0, top, output_size[0], top + output_size[1]))
        
        # Save with high quality
        img.save(image_path, 'JPEG', quality=95)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, port=5001)
else:
    with app.app_context():
        init_db()
