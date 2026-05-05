// ── Generic Item catalog (loaded once on every form page) ────────────────────
window.genericItems = [];

async function loadGenericItems() {
  try {
    const resp = await fetch('/api/generic-items');
    window.genericItems = await resp.json();
    document.querySelectorAll('.generic-item-select').forEach(function (sel) {
      const cur = sel.value;
      _fillGenericSelect(sel);
      if (cur) sel.value = cur;
    });
  } catch (e) { /* non-fatal */ }
}

function _fillGenericSelect(sel) {
  const cur = sel.getAttribute('data-current') || sel.value || '';
  sel.innerHTML = '<option value="">— Catalog item —</option>' +
    window.genericItems.map(function (it) {
      return `<option value="${it.id}" data-category="${escHtml(it.category)}"
                ${String(it.id) === String(cur) ? 'selected' : ''}>
                ${escHtml(it.label)}
              </option>`;
    }).join('');
}

function onGenericSelectChange(sel) {
  const opt = sel.options[sel.selectedIndex];
  const cat = opt ? (opt.dataset.category || '') : '';
  const row = sel.closest('tr');
  if (!row) return;
  // Update hidden category field
  const catIn = row.querySelector('.row-category');
  if (catIn) catIn.value = cat;
}

// ── Quick-add generic item modal ─────────────────────────────────────────────
let _genericModalCallback = null;

function openGenericModal(callback) {
  _genericModalCallback = callback || null;
  // reset form
  document.getElementById('gm_name').value          = '';
  document.getElementById('gm_category').value      = '';
  document.getElementById('gm_variety').value       = '';
  document.getElementById('gm_color').value         = '';
  document.getElementById('gm_flower_category').value = '';
  toggleModalFlowerFields();
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('genericItemModal'));
  modal.show();
}

function toggleModalFlowerFields() {
  const cat = document.getElementById('gm_category').value;
  const el  = document.getElementById('gm_flowerFields');
  if (el) el.style.display = cat === 'Flower' ? '' : 'none';
}

async function saveGenericModal() {
  const name     = document.getElementById('gm_name').value.trim();
  const category = document.getElementById('gm_category').value;
  if (!name || !category) {
    alert('Name and category are required.');
    return;
  }
  const payload = {
    name,
    category,
    variety:         document.getElementById('gm_variety').value.trim(),
    color:           document.getElementById('gm_color').value.trim(),
    flower_category: document.getElementById('gm_flower_category').value,
  };
  try {
    const resp = await fetch('/api/generic-items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) { alert('Error saving item.'); return; }
    const newItem = await resp.json();
    window.genericItems.push(newItem);
    // Refresh all selects
    document.querySelectorAll('.generic-item-select').forEach(function (sel) {
      const cur = sel.value;
      _fillGenericSelect(sel);
      if (cur) sel.value = cur;
    });
    bootstrap.Modal.getOrCreateInstance(document.getElementById('genericItemModal')).hide();
    if (_genericModalCallback) _genericModalCallback(newItem);
  } catch (e) { alert('Network error: ' + e); }
}

// ── Invoice form ──────────────────────────────────────────────────────────────
let invRowId = 0;

function addInvoiceRow(data) {
  invRowId++;
  const d    = data || {};
  const line = ((d.quantity || 1) * (d.unit_price || 0)).toFixed(2);
  const row  = document.createElement('tr');
  row.id = `inv_row_${invRowId}`;
  row.innerHTML = `
    <td style="min-width:130px">
      <input type="text" name="item_name[]" class="form-control form-control-sm"
             value="${escHtml(d.name || '')}" placeholder="e.g. Red Roses" required>
    </td>
    <td style="min-width:180px">
      <input type="hidden" name="item_category[]" class="row-category"
             value="${escHtml(d.category || '')}">
      <div class="d-flex gap-1">
        <select name="item_generic_item_id[]" class="form-select form-select-sm generic-item-select"
                data-current="${d.generic_item_id || ''}"
                onchange="onGenericSelectChange(this)">
          <option value="">— Catalog item —</option>
        </select>
        <button type="button" class="btn btn-sm btn-outline-success flex-shrink-0"
                title="New catalog item"
                onclick="openGenericModal(function(it){ setRowGeneric(document.getElementById('inv_row_${invRowId}'), it); })">
          <i class="bi bi-plus-lg"></i>
        </button>
      </div>
    </td>
    <td style="min-width:75px">
      <input type="number" name="item_quantity[]" class="form-control form-control-sm inv-qty"
             value="${d.quantity || 1}" step="0.01" min="0.01" oninput="updateInvoiceTotal()">
    </td>
    <td style="min-width:85px">
      <input type="number" name="item_price[]" class="form-control form-control-sm inv-price"
             value="${d.unit_price !== undefined ? d.unit_price : ''}"
             step="0.01" min="0" placeholder="0.00" oninput="updateInvoiceTotal()">
    </td>
    <td class="inv-line-total fw-semibold text-end" style="min-width:70px">$${line}</td>
    <td>
      <button type="button" class="btn btn-sm btn-outline-danger"
              onclick="this.closest('tr').remove(); updateInvoiceTotal();">
        <i class="bi bi-trash"></i>
      </button>
    </td>`;
  document.getElementById('invoiceLineItems').appendChild(row);
  _fillGenericSelect(row.querySelector('.generic-item-select'));
  updateInvoiceTotal();
}

function setRowGeneric(row, item) {
  const sel = row.querySelector('.generic-item-select');
  if (!sel) return;
  _fillGenericSelect(sel);
  sel.value = item.id;
  onGenericSelectChange(sel);
}

function updateInvoiceTotal() {
  let total = 0;
  document.querySelectorAll('#invoiceLineItems tr').forEach(function (row) {
    const qty   = parseFloat(row.querySelector('.inv-qty')?.value)   || 0;
    const price = parseFloat(row.querySelector('.inv-price')?.value) || 0;
    const line  = qty * price;
    total += line;
    const cell = row.querySelector('.inv-line-total');
    if (cell) cell.textContent = '$' + line.toFixed(2);
  });
  const el = document.getElementById('invoiceTotalDisplay');
  if (el) el.textContent = '$' + total.toFixed(2);
}

// ── Arrangement form ──────────────────────────────────────────────────────────
let arrRowId = 0;

function addArrangementRow(data) {
  arrRowId++;
  const d    = data || {};
  const line = ((d.quantity || 1) * (d.unit_price || 0)).toFixed(2);
  const row  = document.createElement('tr');
  row.id = `arr_row_${arrRowId}`;
  row.innerHTML = `
    <td>
      <input type="hidden" name="arr_item_invoice_item_id[]" value="${d.invoice_item_id || ''}">
      <input type="hidden" name="arr_item_category[]" class="row-category" value="${escHtml(d.category || '')}">
      <input type="text" name="arr_item_name[]" class="form-control form-control-sm"
             value="${escHtml(d.name || '')}" placeholder="Item name" required style="min-width:110px">
    </td>
    <td style="min-width:180px">
      <div class="d-flex gap-1">
        <select name="arr_item_generic_item_id[]" class="form-select form-select-sm generic-item-select"
                data-current="${d.generic_item_id || ''}"
                onchange="onGenericSelectChange(this)">
          <option value="">— Catalog item —</option>
        </select>
        <button type="button" class="btn btn-sm btn-outline-success flex-shrink-0"
                title="New catalog item"
                onclick="openGenericModal(function(it){ setRowGeneric(document.getElementById('arr_row_${arrRowId}'), it); })">
          <i class="bi bi-plus-lg"></i>
        </button>
      </div>
    </td>
    <td style="min-width:75px">
      <input type="number" name="arr_item_quantity[]" class="form-control form-control-sm arr-qty"
             value="${d.quantity || 1}" step="0.01" min="0.01" oninput="updateArrangementCost()">
    </td>
    <td style="min-width:85px">
      <input type="number" name="arr_item_price[]" class="form-control form-control-sm arr-price"
             value="${d.unit_price !== undefined ? d.unit_price : ''}"
             step="0.01" min="0" placeholder="0.00" oninput="updateArrangementCost()">
    </td>
    <td class="arr-line-total fw-semibold text-end" style="min-width:65px">$${line}</td>
    <td>
      <button type="button" class="btn btn-sm btn-outline-danger"
              onclick="this.closest('tr').remove(); updateArrangementCost();">
        <i class="bi bi-trash"></i>
      </button>
    </td>`;
  document.getElementById('arrangementItemsBody').appendChild(row);
  _fillGenericSelect(row.querySelector('.generic-item-select'));
  updateArrangementCost();
}

function updateArrangementCost() {
  let cost = 0;
  document.querySelectorAll('#arrangementItemsBody tr').forEach(function (row) {
    const qty   = parseFloat(row.querySelector('.arr-qty')?.value)   || 0;
    const price = parseFloat(row.querySelector('.arr-price')?.value) || 0;
    const line  = qty * price;
    cost += line;
    const cell = row.querySelector('.arr-line-total');
    if (cell) cell.textContent = '$' + line.toFixed(2);
  });

  const salePrice = parseFloat(document.getElementById('priceInput')?.value) || 0;
  const profit    = salePrice - cost;
  const markup    = cost > 0 ? salePrice / cost : 0;

  const costEl   = document.getElementById('costDisplay');
  const profitEl = document.getElementById('profitDisplay');
  const markupEl = document.getElementById('markupDisplay');
  if (costEl)   costEl.textContent   = '$' + cost.toFixed(2);
  if (profitEl) {
    profitEl.textContent = '$' + profit.toFixed(2);
    profitEl.className   = 'value ' + (profit >= 0 ? 'profit-pos' : 'profit-neg');
  }
  if (markupEl) markupEl.textContent = markup.toFixed(2) + 'x';

  // Show/hide empty message
  const msg  = document.getElementById('noItemsMsg');
  const body = document.getElementById('arrangementItemsBody');
  if (msg) msg.style.display = (body && body.children.length) ? 'none' : 'block';
}

function addManualItem() {
  addArrangementRow({ name: '', category: 'Labor', quantity: 1, unit_price: 0 });
}

// ── Invoice item picker (arrangement form) ────────────────────────────────────
const invoiceSelect = document.getElementById('invoicePickerSelect');
if (invoiceSelect) {
  invoiceSelect.addEventListener('change', function () {
    const id        = this.value;
    const container = document.getElementById('invoiceItemsList');
    if (!id) { container.innerHTML = ''; return; }
    container.innerHTML = '<div class="text-center py-3 text-muted"><i class="bi bi-hourglass-split"></i> Loading…</div>';
    fetch(`/api/invoices/${id}/items`)
      .then(function (r) { return r.json(); })
      .then(function (items) {
        if (!items.length) {
          container.innerHTML = '<p class="text-muted text-center py-3">No items on this invoice.</p>';
          return;
        }
        container.innerHTML = items.map(function (item) {
          return `
            <div class="invoice-item-row">
              <div class="item-info">
                <div class="item-name">${escHtml(item.name)}</div>
                <div class="item-meta">
                  ${escHtml(item.category)}
                  ${item.generic_item_label ? '· ' + escHtml(item.generic_item_label) : ''}
                  · $${item.unit_price.toFixed(2)} ea · ${item.remaining.toFixed(2)} avail
                </div>
              </div>
              <input type="number" id="pick_qty_${item.id}" class="form-control form-control-sm qty-input"
                     placeholder="qty" value="1" step="0.01" min="0.01">
              <button type="button" class="btn btn-sm btn-success add-btn ms-2"
                      onclick="addFromInvoice(${item.id}, ${escJs(item.name)}, ${escJs(item.category)}, ${item.unit_price}, ${escJs(String(item.generic_item_id))})">
                <i class="bi bi-plus-lg"></i>
              </button>
            </div>`;
        }).join('');
      })
      .catch(function () {
        container.innerHTML = '<p class="text-danger text-center py-3">Failed to load items.</p>';
      });
  });
}

function addFromInvoice(itemId, name, category, price, genericItemId) {
  const qty = parseFloat(document.getElementById(`pick_qty_${itemId}`)?.value) || 0;
  if (qty <= 0) { alert('Enter a quantity greater than 0.'); return; }
  addArrangementRow({
    invoice_item_id: itemId,
    generic_item_id: genericItemId || '',
    name,
    category,
    quantity:   qty,
    unit_price: price,
  });
}

// ── Shopify collection sync ───────────────────────────────────────────────────
function syncShopifyCollections() {
  const btn = document.getElementById('syncCollectionsBtn');
  if (!btn) return;
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Syncing…';
  fetch('/api/shopify/sync-collections', { method: 'POST' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) { alert('Error: ' + data.error); }
      else { alert(data.message + '\nReload the page to see updated collections.'); }
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-cloud-download"></i> Sync Collections';
    })
    .catch(function () {
      alert('Network error. Check Shopify credentials in .env');
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-cloud-download"></i> Sync Collections';
    });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escJs(s) { return JSON.stringify(String(s || '')); }
