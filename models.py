from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    vendor_type = db.Column(db.String(50))  # Wholesale, Grocery, Retail
    location = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    website = db.Column(db.String(200))
    wholesale_relationship = db.Column(db.Boolean, default=False)
    invoices = db.relationship('Invoice', backref='vendor', lazy=True)

    def __repr__(self):
        return f'<Vendor {self.name}>'


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    date_purchased = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')

    @property
    def total(self):
        return sum(item.total for item in self.items)

    def __repr__(self):
        return f'<Invoice {self.id}>'


class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))  # Flower, Hard Good, Labor, Other
    generic_type = db.Column(db.String(200))
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0)
    arrangement_items = db.relationship('ArrangementItem', backref='invoice_item', lazy=True)

    @property
    def total(self):
        return self.quantity * self.unit_price

    @property
    def used_quantity(self):
        return sum(ai.quantity for ai in self.arrangement_items)

    @property
    def remaining_quantity(self):
        return self.quantity - self.used_quantity


class ShopifyCollection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shopify_id = db.Column(db.String(100), unique=True)
    title = db.Column(db.String(200))
    handle = db.Column(db.String(200))


class Arrangement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.Date, default=datetime.utcnow)
    sku = db.Column(db.String(100))
    arrangement_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    collection_id = db.Column(db.Integer, db.ForeignKey('shopify_collection.id'), nullable=True)
    price = db.Column(db.Float, default=0)
    photo_path = db.Column(db.String(500))
    shopify_product_id = db.Column(db.String(100))
    items = db.relationship('ArrangementItem', backref='arrangement', lazy=True, cascade='all, delete-orphan')
    collection = db.relationship('ShopifyCollection', backref='arrangements')

    @property
    def cost(self):
        return sum(item.total for item in self.items)

    @property
    def profit(self):
        return self.price - self.cost

    @property
    def markup(self):
        if self.cost > 0:
            return self.price / self.cost
        return 0


class ArrangementItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    arrangement_id = db.Column(db.Integer, db.ForeignKey('arrangement.id'), nullable=False)
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    generic_type = db.Column(db.String(200))
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0)

    @property
    def total(self):
        return self.quantity * self.unit_price
