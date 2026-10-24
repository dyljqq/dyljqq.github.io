(() => {
  const form = document.getElementById('invoice-form');
  if (!form) return;
  const items = document.getElementById('invoice-items');
  const previewItems = document.getElementById('invoice-preview-items');
  const workspace = form.closest('.invoice-workspace');
  const appDialog = document.getElementById('invoice-app-dialog');
  let appPromptPending = false;
  const rowTemplate = items.firstElementChild.cloneNode(true);
  const maxCents = 99999999999;
  const field = id => document.getElementById(id);
  const money = cents => (cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const localDate = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  const today = new Date();
  field('issue-date').value = localDate(today);
  const due = new Date(today);
  due.setDate(due.getDate() + 30);
  field('due-date').value = localDate(due);

  function render() {
    form.querySelectorAll('input, textarea').forEach(input => {
      const target = document.querySelector(`[data-preview="${input.id}"]`);
      if (!target) return;
      let value = input.value.trim();
      if (input.type === 'date' && value) {
        value = new Date(`${value}T00:00:00`).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
      }
      target.textContent = value || ({ 'business-name': 'Your business', 'client-name': 'Your client' }[input.id] || '');
    });
    previewItems.replaceChildren();
    let subtotal = 0, amountTooLarge = false;
    const rows = items.querySelectorAll('[data-item]');
    rows.forEach((row, index) => {
      const description = row.querySelector('[name="description"]').value.trim();
      const quantity = row.querySelector('[name="quantity"]').valueAsNumber;
      const price = row.querySelector('[name="price"]').valueAsNumber;
      const amount = Number.isFinite(quantity) && quantity > 0 && Number.isFinite(price) && price >= 0 ? Math.round((Math.round(quantity * 100) * Math.round(price * 100) / 100) + Number.EPSILON) : 0;
      const validAmount = Number.isSafeInteger(amount) && amount <= maxCents;
      amountTooLarge ||= !validAmount;
      subtotal = Math.min(maxCents + 1, subtotal + (validAmount ? amount : 0));
      const tr = document.createElement('tr');
      [description || 'Your item', Number.isFinite(quantity) ? String(quantity) : '', Number.isFinite(price) && price >= 0 ? money(Math.round(price * 100)) : '—', validAmount ? money(amount) : '—'].forEach(value => {
        const td = document.createElement('td');
        td.textContent = value;
        tr.appendChild(td);
      });
      previewItems.appendChild(tr);
      const remove = row.querySelector('[data-remove-item]');
      remove.disabled = rows.length === 1;
      remove.setAttribute('aria-label', `Remove item ${index + 1}`);
    });
    const rate = field('invoice-tax').valueAsNumber;
    const tax = Number.isFinite(rate) && rate >= 0 && rate <= 100 ? Math.round(subtotal * Math.round(rate * 100) / 10000) : 0;
    amountTooLarge ||= subtotal + tax > maxCents;
    const error = field('invoice-amount-error');
    error.hidden = !amountTooLarge;
    items.querySelector('[name="price"]').setCustomValidity(amountTooLarge ? error.textContent : '');
    field('invoice-subtotal').textContent = amountTooLarge ? '—' : money(subtotal);
    field('invoice-tax-total').textContent = amountTooLarge ? '—' : money(tax);
    field('invoice-total').textContent = amountTooLarge ? '—' : money(subtotal + tax);
    field('invoice-edit-total').textContent = amountTooLarge ? '—' : money(subtotal + tax);
    field('invoice-preview-tax-rate').textContent = Number.isFinite(rate) ? String(rate) : '—';
    document.querySelector('.invoice-payment').hidden = !field('payment-details').value.trim();
    document.querySelector('[data-preview="invoice-notes"]').hidden = !field('invoice-notes').value.trim();
    workspace.dataset.invalid = String(!form.checkValidity());
  }

  field('add-invoice-item').addEventListener('click', () => {
    const row = rowTemplate.cloneNode(true);
    items.appendChild(row);
    render();
    row.querySelector('[name="description"]').focus();
  });
  items.addEventListener('click', event => {
    const remove = event.target.closest('[data-remove-item]');
    if (!remove || items.children.length === 1) return;
    const row = remove.closest('[data-item]');
    const next = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    render();
    next.querySelector('[name="description"]').focus();
  });
  form.addEventListener('input', render);
  form.addEventListener('submit', event => {
    event.preventDefault();
    render();
    if (form.reportValidity()) {
      appPromptPending = true;
      window.print();
    }
  });
  window.addEventListener('beforeprint', render);
  // Closing print preview also fires afterprint; the browser does not report whether a PDF was saved.
  window.addEventListener('afterprint', () => {
    if (!appPromptPending) return;
    appPromptPending = false;
    appDialog.showModal();
  });
  field('invoice-app-close').addEventListener('click', () => appDialog.close());
  field('invoice-app-later').addEventListener('click', () => appDialog.close());
  appDialog.addEventListener('close', () => field('print-invoice').focus());
  render();
  workspace.hidden = false;
  field('print-invoice').disabled = false;
})();
