from flask import Flask, render_template, request, redirect, flash, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secure_secret_key'
db = SQLAlchemy(app)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Item {self.id}>'


# Helper function for committing database changes with error handling
def commit_to_db(action_description):
    try:
        db.session.commit()
        flash(f"{action_description} successfully!", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database commit failed: {str(e)}")
        flash("An error occurred while processing your request. Please try again.", "danger")


# Input validation function
def validate_item_content(content):
    if not content or not content.strip():
        return False, "Item content cannot be empty."
    if len(content.strip()) > 200:
        return False, "Item content exceeds 200 characters."
    return True, ""


@app.route('/', methods=['POST', 'GET'])
def index():
    search_query = request.args.get('search', '').strip()
    if request.method == 'POST':
        item_content = request.form.get('content', '').strip()

        # Validate input content
        is_valid, error_message = validate_item_content(item_content)
        if not is_valid:
            flash(error_message, "danger")
            return redirect(url_for('index'))

        new_item = Item(content=item_content)
        db.session.add(new_item)
        commit_to_db("Item added")
        return redirect(url_for('index'))

    # Fetch items and apply search filter
    if search_query:
        items = Item.query.filter(Item.content.like(f"%{search_query}%")).order_by(Item.date_created).all()
    else:
        items = Item.query.order_by(Item.date_created).all()

    return render_template("index.html", items=items, search_query=search_query)


@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    item_to_delete = Item.query.get_or_404(id)
    db.session.delete(item_to_delete)
    commit_to_db("Item deleted")
    return redirect(url_for('index'))


@app.route('/update/<int:id>', methods=['POST', 'GET'])
def update(id):
    item_to_update = Item.query.get_or_404(id)

    if request.method == 'POST':
        updated_content = request.form.get('content', '').strip()

        # Check if content is unchanged
        if updated_content == item_to_update.content:
            flash("No changes detected in the content.", "info")
            return redirect(url_for('update', id=id))

        # Validate updated content
        is_valid, error_message = validate_item_content(updated_content)
        if not is_valid:
            flash(error_message, "danger")
            return redirect(url_for('update', id=id))

        item_to_update.content = updated_content
        commit_to_db("Item updated")
        return redirect(url_for('index'))

    return render_template('update.html', item=item_to_update)


# HTTP 404 Error Handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


# Security enhancement: Input sanitization and output encoding
@app.template_filter('sanitize')
def sanitize_input(value):
    # Sanitizes potentially unsafe characters to prevent XSS
    return re.sub(r'[<>"]', '', value)


# Initialize database with data integrity checks
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        app.logger.error(f"Database initialization failed: {str(e)}")
        raise RuntimeError("Critical Error: Unable to initialize the database.")


# Set up logging for monitoring and debugging
if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler("app.log", maxBytes=10240, backupCount=10)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("Application started")


if __name__ == "__main__":
    app.run(debug=True)
