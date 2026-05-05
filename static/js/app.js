// ── Invoice form ──────────────────────────────────────────────────────────────
let invRowId = 0;

function addInvoiceRow(data) {
  invRowId++;
  const d = data || {};
  const row = document.createElement('tr');
  row.id = `inv_row_${invRowId}`;
  row.innerHTML = `
    <td style="min-width:130px">
      <input type="text" name="item_name[]" class="form-control form-control-sm"
             value="${escHtml(d.name || '')}" placeholder="e.g. Red Roses" required>
    </td>
    <td>
      <select name="item_category[]" class="form-select form-select-sm">
        ${categoryOptions(d.category)}
      </select>
    </td>
    <td style="min-width:110px">
      <input type="text" name="item_generic_type[]" class="form-control form-control-sm"
             value="${escHtml(d.generic_type || '')}" placeholder="e.g. Rose">
    </td>
    <td style="min-width:80px">
      <input type="number" name="item_quantity[]" class="form-control form-control-sm inv-qty"
             value="${d.quantity || 1}" step="0.01" min="0.01" oninput="updateInvoiceTotal()">
    </td>
    <td style="min-width:90px">
      <input type="number" name="item_price[]" class="form-control form-control-sm inv-price"
             value="${d.unit_price !== undefined ? d.unit_price : ''}" step="0.01" min="0"
             placeholder="0.00" oninput="updateInvoiceTotal()">
    </td>
    <td class="inv-line-total fw-semibold text-end" style="min-width:70px">
      $${((d.quantity || 1) * (d.unit_price || 0)).toFixed(2)}
    </td>
    <td>
      <button type="button" class="btn btn-sm btn-outline-danger"
              onclick="this.closest('tr').remove(); updateInvoiceTotal();">
        <i class="bi bi-trash"></i>
      </button>
    </td>`;
  document.getElementById('invoiceLineItems').appendChild(row);
  updateInvoiceTotal();
}

function updateInvoiceTotal() {
  let total = 0;
  document.querySelectorAll('#invoiceLineItems tr').forEach(row => {
    const qty   = parseFloat(row.querySelector('.inv-qty')?.value) || 0;
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
  const d = data || {};
  const row = document.createElement('tr');
  row.id = `arr_row_${arrRowId}`;
  const line = (d.quantity || 1) * (d.unit_price || 0);
  row.innerHTML = `
    <td>
      <input type="hidden" name="arr_item_invoice_item_id[]" value="${d.invoice_item_id || ''}">
      <input type="text" name="arr_item_name[]" class="form-control form-control-sm"
             value="${escHtml(d.name || '')}" placeholder="Item name" required style="min-width:110px">
    </td>
    <td>
      <select name="arr_item_category[]" class="form-select form-select-sm" style="min-width:100px">
        ${categoryOptions(d.category)}
      </select>
    </td>
    <td style="min-width:100px">
      <input type="text" name="arr_item_generic_type[]" class="form-control form-control-sm"
             value="${escHtml(d.generic_type || '')}" placeholder="e.g. Rose">
    </td>
    <td style="min-width:75px">
      <input type="number" name="arr_item_quantity[]" class="form-control form-control-sm arr-qty"
             value="${d.quantity || 1}" step="0.01" min="0.01" oninput="updateArrangementCost()">
    </td>
    <td style="min-width:85px">
      <input type="number" name="arr_item_price[]" class="form-control form-control-sm arr-price"
             value="${d.unit_price !== undefined ? d.unit_price : ''}" step="0.01" min="0"
             placeholder="0.00" oninput="updateArrangementCost()">
    </td>
    <td class="arr-line-total fw-semibold text-end" style="min-width:65px">$${line.toFixed(2)}</td>
    <td>
      <button type="button" class="btn btn-sm btn-outline-danger"
              onclick="this.closest('tr').remove(); updateArrangementCost();">
        <i class="bi bi-trash"></i>
      </button>
    </td>`;
  document.getElementById('arrangementItemsBody').appendChild(row);
  updateArrangementCost();
}

function updateArrangementCost() {
  let cost = 0;
  document.querySelectorAll('#arrangementItemsBody tr').forEach(row => {
    const qty   = parseFloat(row.querySelector('.arr-qty')?.value) || 0;
    const price = parseFloat(row.querySelector('.arr-price')?.value) || 0;
    const line  = qty * price;
    cost += line;
    const cell = row.querySelector('.arr-line-total');
    if (cell) cell.textContent = '$' + line.toFixed(2);
  });

  const salePrice = parseFloat(document.getElementById('priceInput')?.value) || 0;
  const profit = salePrice - cost;
  const markup = cost > 0 ? salePrice / cost : 0;

  const costEl   = document.getElementById('costDisplay');
  const profitEl = document.getElementById('profitDisplay');
  const markupEl = document.getElementById('markupDisplay');

  if (costEl)   costEl.textContent   = '$' + cost.toFixed(2);
  if (profitEl) {
    profitEl.textContent = '$' + profit.toFixed(2);
    profitEl.className   = 'value ' + (profit >= 0 ? 'profit-pos' : 'profit-neg');
  }
  if (markupEl) markupEl.textContent = markup.toFixed(2) + 'x';
}

// ── Invoice item picker ───────────────────────────────────────────────────────
const invoiceSelect = document.getElementById('invoicePickerSelect');
if (invoiceSelect) {
  invoiceSelect.addEventListener('change', function () {
    const id = this.value;
    const container = document.getElementById('invoiceItemsList');
    if (!id) { container.innerHTML = ''; return; }

    container.innerHTML = '<div class="text-center py-3 text-muted"><i class="bi bi-hourglass-split"></i> Loading…</div>';

    fetch(`/api/invoices/${id}/items`)
      .then(r => r.json())
      .then(items => {
        if (!items.length) {
          container.innerHTML = '<p class="text-muted text-center py-3">No items on this invoice.</p>';
          return;
        }
        container.innerHTML = items.map(item => `
          <div class="invoice-item-row">
            <div class="item-info">
              <div class="item-name">${escHtml(item.name)}</div>
              <div class="item-meta">${escHtml(item.category)} · $${item.unit_price.toFixed(2)} ea · ${item.remaining.toFixed(2)} avail</div>
            </div>
            <input type="number" id="pick_qty_${item.id}" class="form-control form-control-sm qty-input"
                   placeholder="qty" value="1" step="0.01" min="0.01">
            <button type="button" class="btn btn-sm btn-success add-btn ms-2"
                    onclick="addFromInvoice(${item.id}, ${escJs(item.name)}, ${escJs(item.category)}, ${escJs(item.generic_type)}, ${item.unit_price})">
              <i class="bi bi-plus-lg"></i>
            </button>
          </div>`).join('');
      })
      .catch(() => {
        container.innerHTML = '<p class="text-danger text-center py-3">Failed to load items.</p>';
      });
  });
}

function addFromInvoice(itemId, name, category, genericType, price) {
  const qty = parseFloat(document.getElementById(`pick_qty_${itemId}`)?.value) || 0;
  if (qty <= 0) { alert('Enter a quantity greater than 0.'); return; }
  addArrangementRow({ invoice_item_id: itemId, name, category, generic_type: genericType, quantity: qty, unit_price: price });
}

function addManualItem() {
  addArrangementRow({ name: '', category: 'Labor', generic_type: '', quantity: 1, unit_price: 0 });
}

// ── Shopify collection sync ───────────────────────────────────────────────────
function syncShopifyCollections() {
  const btn = document.getElementById('syncCollectionsBtn');
  if (!btn) return;
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Syncing…';

  fetch('/api/shopify/sync-collections', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        alert('Error: ' + data.error);
      } else {
        alert(data.message + '\nReload the page to see updated collections.');
      }
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-cloud-download"></i> Sync Collections';
    })
    .catch(() => {
      alert('Network error. Check your Shopify credentials in .env');
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-cloud-download"></i> Sync Collections';
    });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function categoryOptions(selected) {
  const cats = ['Flower', 'Hard Good', 'Labor', 'Other'];
  return cats.map(c => `<option value="${c}" ${c === selected ? 'selected' : ''}>${c}</option>`).join('');
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escJs(s) {
  return JSON.stringify(String(s));
}
