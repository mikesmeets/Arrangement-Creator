import os
import base64
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///arrangements.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic', 'pdf'}

from models import db, Vendor, Invoice, InvoiceItem, Arrangement, ArrangementItem, ShopifyCollection, GenericItem, FLOWER_CATEGORIES, ITEM_CATEGORIES, FLOWER_VARIETIES, FLOWER_COLORS

db.init_app(app)

with app.app_context():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Add new columns to existing DBs if upgrading from earlier schema
    from sqlalchemy import text, inspect
    insp = inspect(db.engine)
    for table, col, col_def in [
        ('invoice_item',     'generic_item_id', 'INTEGER REFERENCES generic_item(id)'),
        ('arrangement_item', 'generic_item_id', 'INTEGER REFERENCES generic_item(id)'),
        ('invoice',          'photo_path',       'VARCHAR(500)'),
    ]:
        existing = [c['name'] for c in insp.get_columns(table)]
        if col not in existing:
            db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {col_def}'))
    db.session.commit()


@app.context_processor
def inject_constants():
    return dict(
        FLOWER_VARIETIES=FLOWER_VARIETIES,
        FLOWER_COLORS=FLOWER_COLORS,
        FLOWER_CATEGORIES=FLOWER_CATEGORIES,
        ITEM_CATEGORIES=ITEM_CATEGORIES,
    )


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    recent_arrangements = Arrangement.query.order_by(Arrangement.date_created.desc()).limit(6).all()
    recent_invoices = Invoice.query.order_by(Invoice.date_purchased.desc()).limit(5).all()
    stats = {
        'arrangements': Arrangement.query.count(),
        'invoices': Invoice.query.count(),
        'vendors': Vendor.query.count(),
        'total_value': sum(a.price for a in Arrangement.query.all()),
    }
    return render_template('index.html',
                           recent_arrangements=recent_arrangements,
                           recent_invoices=recent_invoices,
                           stats=stats)


# ─── Catalog (GenericItem) ────────────────────────────────────────────────────

@app.route('/catalog')
def catalog():
    category_filter = request.args.get('category', '')
    q = GenericItem.query
    if category_filter:
        q = q.filter_by(category=category_filter)
    items = q.order_by(GenericItem.category, GenericItem.name).all()
    return render_template('catalog/list.html', items=items,
                           category_filter=category_filter,
                           categories=ITEM_CATEGORIES)


@app.route('/catalog/new', methods=['GET', 'POST'])
def catalog_new():
    if request.method == 'POST':
        item = GenericItem(
            name=request.form['name'],
            category=request.form['category'],
            variety=request.form.get('variety', '') or None,
            color=request.form.get('color', '') or None,
            flower_category=request.form.get('flower_category', '') or None,
        )
        db.session.add(item)
        db.session.commit()
        flash('Item added to catalog!', 'success')
        return redirect(url_for('catalog'))
    return render_template('catalog/form.html', item=None,
                           categories=ITEM_CATEGORIES,
                           flower_categories=FLOWER_CATEGORIES)


@app.route('/catalog/<int:id>/edit', methods=['GET', 'POST'])
def catalog_edit(id):
    item = GenericItem.query.get_or_404(id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.category = request.form['category']
        item.variety = request.form.get('variety', '') or None
        item.color = request.form.get('color', '') or None
        item.flower_category = request.form.get('flower_category', '') or None
        db.session.commit()
        flash('Item updated!', 'success')
        return redirect(url_for('catalog'))
    return render_template('catalog/form.html', item=item,
                           categories=ITEM_CATEGORIES,
                           flower_categories=FLOWER_CATEGORIES)


@app.route('/catalog/<int:id>/delete', methods=['POST'])
def catalog_delete(id):
    item = GenericItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from catalog.', 'info')
    return redirect(url_for('catalog'))


# ─── Vendors ──────────────────────────────────────────────────────────────────

@app.route('/vendors')
def vendors():
    all_vendors = Vendor.query.order_by(Vendor.name).all()
    return render_template('vendors/list.html', vendors=all_vendors)


@app.route('/vendors/new', methods=['GET', 'POST'])
def vendor_new():
    if request.method == 'POST':
        vendor = Vendor(
            name=request.form['name'],
            vendor_type=request.form.get('vendor_type', ''),
            location=request.form.get('location', ''),
            phone=request.form.get('phone', ''),
            website=request.form.get('website', ''),
            wholesale_relationship='wholesale_relationship' in request.form
        )
        db.session.add(vendor)
        db.session.commit()
        flash('Vendor added!', 'success')
        return redirect(url_for('vendors'))
    return render_template('vendors/form.html', vendor=None, title='Add Vendor')


@app.route('/vendors/<int:id>/edit', methods=['GET', 'POST'])
def vendor_edit(id):
    vendor = Vendor.query.get_or_404(id)
    if request.method == 'POST':
        vendor.name = request.form['name']
        vendor.vendor_type = request.form.get('vendor_type', '')
        vendor.location = request.form.get('location', '')
        vendor.phone = request.form.get('phone', '')
        vendor.website = request.form.get('website', '')
        vendor.wholesale_relationship = 'wholesale_relationship' in request.form
        db.session.commit()
        flash('Vendor updated!', 'success')
        return redirect(url_for('vendors'))
    return render_template('vendors/form.html', vendor=vendor, title='Edit Vendor')


@app.route('/vendors/<int:id>/delete', methods=['POST'])
def vendor_delete(id):
    vendor = Vendor.query.get_or_404(id)
    db.session.delete(vendor)
    db.session.commit()
    flash('Vendor deleted.', 'info')
    return redirect(url_for('vendors'))


# ─── Invoices ─────────────────────────────────────────────────────────────────

@app.route('/invoices')
def invoices():
    all_invoices = Invoice.query.order_by(Invoice.date_purchased.desc()).all()
    return render_template('invoices/list.html', invoices=all_invoices)


def _save_invoice_items(invoice_id):
    names           = request.form.getlist('item_name[]')
    categories      = request.form.getlist('item_category[]')
    quantities      = request.form.getlist('item_quantity[]')
    prices          = request.form.getlist('item_price[]')
    generic_ids     = request.form.getlist('item_generic_item_id[]')

    for i in range(len(names)):
        if not names[i].strip():
            continue
        g_id = generic_ids[i] if i < len(generic_ids) and generic_ids[i] else None
        # Auto-fill category from generic item if available
        cat = categories[i] if i < len(categories) and categories[i] else ''
        if g_id and not cat:
            gi = GenericItem.query.get(int(g_id))
            if gi:
                cat = gi.category
        item = InvoiceItem(
            invoice_id=invoice_id,
            generic_item_id=int(g_id) if g_id else None,
            name=names[i].strip(),
            category=cat,
            quantity=float(quantities[i]) if i < len(quantities) and quantities[i] else 1,
            unit_price=float(prices[i]) if i < len(prices) and prices[i] else 0,
        )
        db.session.add(item)


def _handle_invoice_photo(invoice):
    # Pick the first non-empty file across all 'photo' inputs (image or PDF)
    file = next((f for f in request.files.getlist('photo') if f and f.filename), None)
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"inv_{datetime.now().strftime('%Y%m%d%H%M%S')}_{invoice.id}.{ext}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        invoice.photo_path = f'uploads/{filename}'


@app.route('/invoices/new', methods=['GET', 'POST'])
def invoice_new():
    all_vendors = Vendor.query.order_by(Vendor.name).all()
    if request.method == 'POST':
        invoice = Invoice(
            vendor_id=int(request.form['vendor_id']),
            date_purchased=datetime.strptime(request.form['date_purchased'], '%Y-%m-%d').date(),
            notes=request.form.get('notes', ''),
        )
        db.session.add(invoice)
        db.session.flush()
        _handle_invoice_photo(invoice)
        _save_invoice_items(invoice.id)
        db.session.commit()
        flash('Invoice saved!', 'success')
        return redirect(url_for('invoice_detail', id=invoice.id))
    return render_template('invoices/form.html', vendors=all_vendors, invoice=None, items_data=[])


@app.route('/invoices/<int:id>')
def invoice_detail(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoices/detail.html', invoice=invoice)


@app.route('/invoices/<int:id>/edit', methods=['GET', 'POST'])
def invoice_edit(id):
    invoice = Invoice.query.get_or_404(id)
    all_vendors = Vendor.query.order_by(Vendor.name).all()
    if request.method == 'POST':
        invoice.vendor_id = int(request.form['vendor_id'])
        invoice.date_purchased = datetime.strptime(request.form['date_purchased'], '%Y-%m-%d').date()
        invoice.notes = request.form.get('notes', '')
        _handle_invoice_photo(invoice)
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        _save_invoice_items(invoice.id)
        db.session.commit()
        flash('Invoice updated!', 'success')
        return redirect(url_for('invoice_detail', id=invoice.id))
    items_data = [{
        'name': i.name,
        'category': i.category or '',
        'quantity': i.quantity,
        'unit_price': i.unit_price,
        'generic_item_id': i.generic_item_id or '',
    } for i in invoice.items]
    return render_template('invoices/form.html', vendors=all_vendors, invoice=invoice, items_data=items_data)


@app.route('/invoices/<int:id>/delete', methods=['POST'])
def invoice_delete(id):
    invoice = Invoice.query.get_or_404(id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted.', 'info')
    return redirect(url_for('invoices'))


# ─── Arrangements ─────────────────────────────────────────────────────────────

@app.route('/arrangements')
def arrangements():
    all_arrangements = Arrangement.query.order_by(Arrangement.date_created.desc()).all()
    return render_template('arrangements/list.html', arrangements=all_arrangements)


def _save_arrangement_items(arrangement_id):
    names           = request.form.getlist('arr_item_name[]')
    categories      = request.form.getlist('arr_item_category[]')
    quantities      = request.form.getlist('arr_item_quantity[]')
    prices          = request.form.getlist('arr_item_price[]')
    inv_item_ids    = request.form.getlist('arr_item_invoice_item_id[]')
    generic_ids     = request.form.getlist('arr_item_generic_item_id[]')

    for i in range(len(names)):
        if not names[i].strip():
            continue
        inv_id = inv_item_ids[i] if i < len(inv_item_ids) and inv_item_ids[i] else None
        g_id   = generic_ids[i]  if i < len(generic_ids)  and generic_ids[i]  else None
        cat    = categories[i]   if i < len(categories)   and categories[i]   else ''
        if g_id and not cat:
            gi = GenericItem.query.get(int(g_id))
            if gi:
                cat = gi.category
        item = ArrangementItem(
            arrangement_id=arrangement_id,
            invoice_item_id=int(inv_id) if inv_id else None,
            generic_item_id=int(g_id)   if g_id   else None,
            name=names[i].strip(),
            category=cat,
            quantity=float(quantities[i]) if i < len(quantities) and quantities[i] else 1,
            unit_price=float(prices[i])   if i < len(prices)     and prices[i]     else 0,
        )
        db.session.add(item)


def _handle_photo_upload(arrangement):
    if 'photo' not in request.files:
        return
    file = request.files['photo']
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{arrangement.id}.{ext}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        arrangement.photo_path = f'uploads/{filename}'


@app.route('/arrangements/new', methods=['GET', 'POST'])
def arrangement_new():
    all_vendors  = Vendor.query.order_by(Vendor.name).all()
    all_invoices = Invoice.query.order_by(Invoice.date_purchased.desc()).all()
    collections  = ShopifyCollection.query.order_by(ShopifyCollection.title).all()

    if request.method == 'POST':
        arrangement = Arrangement(
            name=request.form['name'],
            date_created=datetime.strptime(request.form['date_created'], '%Y-%m-%d').date(),
            sku=request.form.get('sku', ''),
            arrangement_type=request.form.get('arrangement_type', ''),
            description=request.form.get('description', ''),
            collection_id=request.form.get('collection_id') or None,
            price=float(request.form.get('price', 0) or 0),
        )
        db.session.add(arrangement)
        db.session.flush()
        _handle_photo_upload(arrangement)
        _save_arrangement_items(arrangement.id)
        db.session.commit()
        flash('Arrangement created!', 'success')
        return redirect(url_for('arrangement_detail', id=arrangement.id))

    return render_template('arrangements/form.html',
                           vendors=all_vendors, invoices=all_invoices,
                           collections=collections, arrangement=None, items_data=[])


@app.route('/arrangements/<int:id>')
def arrangement_detail(id):
    arrangement = Arrangement.query.get_or_404(id)
    return render_template('arrangements/detail.html', arrangement=arrangement)


@app.route('/arrangements/<int:id>/edit', methods=['GET', 'POST'])
def arrangement_edit(id):
    arrangement  = Arrangement.query.get_or_404(id)
    all_vendors  = Vendor.query.order_by(Vendor.name).all()
    all_invoices = Invoice.query.order_by(Invoice.date_purchased.desc()).all()
    collections  = ShopifyCollection.query.order_by(ShopifyCollection.title).all()

    if request.method == 'POST':
        arrangement.name = request.form['name']
        arrangement.date_created = datetime.strptime(request.form['date_created'], '%Y-%m-%d').date()
        arrangement.sku = request.form.get('sku', '')
        arrangement.arrangement_type = request.form.get('arrangement_type', '')
        arrangement.description = request.form.get('description', '')
        arrangement.collection_id = request.form.get('collection_id') or None
        arrangement.price = float(request.form.get('price', 0) or 0)
        _handle_photo_upload(arrangement)
        ArrangementItem.query.filter_by(arrangement_id=arrangement.id).delete()
        _save_arrangement_items(arrangement.id)
        db.session.commit()
        flash('Arrangement updated!', 'success')
        return redirect(url_for('arrangement_detail', id=arrangement.id))

    items_data = [{
        'invoice_item_id': i.invoice_item_id or '',
        'generic_item_id': i.generic_item_id or '',
        'name': i.name,
        'category': i.category or '',
        'quantity': i.quantity,
        'unit_price': i.unit_price,
    } for i in arrangement.items]

    return render_template('arrangements/form.html',
                           vendors=all_vendors, invoices=all_invoices,
                           collections=collections, arrangement=arrangement,
                           items_data=items_data)


@app.route('/arrangements/<int:id>/delete', methods=['POST'])
def arrangement_delete(id):
    arrangement = Arrangement.query.get_or_404(id)
    db.session.delete(arrangement)
    db.session.commit()
    flash('Arrangement deleted.', 'info')
    return redirect(url_for('arrangements'))


@app.route('/arrangements/<int:id>/shopify', methods=['POST'])
def push_to_shopify(id):
    arrangement = Arrangement.query.get_or_404(id)
    shop_url     = os.environ.get('SHOPIFY_SHOP_URL', '').strip()
    access_token = os.environ.get('SHOPIFY_ACCESS_TOKEN', '').strip()

    if not shop_url or not access_token:
        flash('Shopify not configured. Add SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN to your .env file.', 'warning')
        return redirect(url_for('arrangement_detail', id=id))

    headers = {'X-Shopify-Access-Token': access_token, 'Content-Type': 'application/json'}
    product_data = {
        'product': {
            'title': arrangement.name,
            'body_html': arrangement.description or '',
            'vendor': 'TreBlooms',
            'product_type': arrangement.arrangement_type or 'Arrangement',
            'variants': [{'price': f'{arrangement.price:.2f}', 'sku': arrangement.sku or ''}],
            'status': 'draft',
        }
    }

    if arrangement.photo_path:
        photo_full = os.path.join('static', arrangement.photo_path)
        if os.path.exists(photo_full):
            with open(photo_full, 'rb') as f:
                product_data['product']['images'] = [{'attachment': base64.b64encode(f.read()).decode()}]

    try:
        if arrangement.shopify_product_id:
            resp = requests.put(
                f'https://{shop_url}/admin/api/2024-01/products/{arrangement.shopify_product_id}.json',
                json=product_data, headers=headers, timeout=15)
        else:
            resp = requests.post(
                f'https://{shop_url}/admin/api/2024-01/products.json',
                json=product_data, headers=headers, timeout=15)

        if resp.status_code in (200, 201):
            product = resp.json()['product']
            arrangement.shopify_product_id = str(product['id'])
            if arrangement.collection and arrangement.collection.shopify_id:
                requests.post(
                    f'https://{shop_url}/admin/api/2024-01/collects.json',
                    json={'collect': {'product_id': product['id'],
                                      'collection_id': int(arrangement.collection.shopify_id)}},
                    headers=headers, timeout=10)
            db.session.commit()
            flash(f'Successfully pushed to Shopify! Product ID: {product["id"]}', 'success')
        else:
            flash(f'Shopify returned {resp.status_code}: {resp.text[:200]}', 'danger')
    except Exception as e:
        flash(f'Error connecting to Shopify: {e}', 'danger')

    return redirect(url_for('arrangement_detail', id=id))


# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/generic-items', methods=['GET'])
def api_generic_items():
    category = request.args.get('category', '')
    q = GenericItem.query
    if category:
        q = q.filter_by(category=category)
    items = q.order_by(GenericItem.category, GenericItem.name).all()
    return jsonify([i.to_dict() for i in items])


@app.route('/api/generic-items', methods=['POST'])
def api_generic_items_create():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('category'):
        return jsonify({'error': 'name and category are required'}), 400
    item = GenericItem(
        name=data['name'],
        category=data['category'],
        variety=data.get('variety') or None,
        color=data.get('color') or None,
        flower_category=data.get('flower_category') or None,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.route('/api/invoices/<int:id>/items')
def api_invoice_items(id):
    items = InvoiceItem.query.filter_by(invoice_id=id).all()
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'category': item.category or '',
        'generic_item_id': item.generic_item_id or '',
        'generic_item_label': item.generic_item.label if item.generic_item else '',
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total': item.total,
        'remaining': item.remaining_quantity,
    } for item in items])


@app.route('/api/shopify/sync-collections', methods=['POST'])
def sync_shopify_collections():
    shop_url     = os.environ.get('SHOPIFY_SHOP_URL', '').strip()
    access_token = os.environ.get('SHOPIFY_ACCESS_TOKEN', '').strip()
    if not shop_url or not access_token:
        return jsonify({'error': 'Shopify credentials not configured'}), 400

    headers   = {'X-Shopify-Access-Token': access_token}
    all_cols  = []
    try:
        for endpoint in ('custom_collections', 'smart_collections'):
            r = requests.get(f'https://{shop_url}/admin/api/2024-01/{endpoint}.json',
                             headers=headers, timeout=10)
            all_cols.extend(r.json().get(endpoint, []))
        for col in all_cols:
            existing = ShopifyCollection.query.filter_by(shopify_id=str(col['id'])).first()
            if existing:
                existing.title = col['title']
                existing.handle = col['handle']
            else:
                db.session.add(ShopifyCollection(shopify_id=str(col['id']),
                                                  title=col['title'], handle=col['handle']))
        db.session.commit()
        return jsonify({'message': f'Synced {len(all_cols)} collections'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
