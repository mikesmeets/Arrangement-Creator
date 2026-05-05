from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

FLOWER_CATEGORIES = ['Focal', 'Secondary', 'Filler', 'Greenery', 'Accent', 'Textural']
ITEM_CATEGORIES   = ['Flower', 'Hard Good', 'Labor', 'Other']


class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    vendor_type = db.Column(db.String(50))
    location = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    website = db.Column(db.String(200))
    wholesale_relationship = db.Column(db.Boolean, default=False)
    invoices = db.relationship('Invoice', backref='vendor', lazy=True)

    def __repr__(self):
        return f'<Vendor {self.name}>'


class GenericItem(db.Model):
    """Reusable item catalog — the abstract 'what it is', not where it was bought."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)       # e.g. "Red Garden Rose"
    category = db.Column(db.String(50), nullable=False)    # Flower / Hard Good / Labor / Other
    # Flower-specific
    variety = db.Column(db.String(200))                    # Rose, Tulip, Lily …
    color = db.Column(db.String(100))                      # Red, White, Blush …
    flower_category = db.Column(db.String(50))             # Focal, Secondary, Filler, Greenery …

    invoice_items    = db.relationship('InvoiceItem',    backref='generic_item', lazy=True)
    arrangement_items = db.relationship('ArrangementItem', backref='generic_item', lazy=True)

    @property
    def label(self):
        """Short display string for dropdowns."""
        parts = [self.name]
        if self.variety:
            parts.append(self.variety)
        if self.color:
            parts.append(self.color)
        if self.flower_category:
            parts.append(self.flower_category)
        return ' · '.join(parts)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'category': self.category,
            'variety': self.variety or '',
            'color': self.color or '',
            'flower_category': self.flower_category or '',
        }

    def __repr__(self):
        return f'<GenericItem {self.name}>'


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
    generic_item_id = db.Column(db.Integer, db.ForeignKey('generic_item.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)       # specific purchase name
    category = db.Column(db.String(50))
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
        return self.price / self.cost if self.cost > 0 else 0


class ArrangementItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    arrangement_id = db.Column(db.Integer, db.ForeignKey('arrangement.id'), nullable=False)
    invoice_item_id = db.Column(db.Integer, db.ForeignKey('invoice_item.id'), nullable=True)
    generic_item_id = db.Column(db.Integer, db.ForeignKey('generic_item.id'), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    quantity = db.Column(db.Float, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0)

    @property
    def total(self):
        return self.quantity * self.unit_price
