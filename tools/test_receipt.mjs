import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('./build_tools.py', import.meta.url), 'utf8');
const script = source.match(/RECEIPT_JS = r"""([\s\S]*?)"""/)[1];

function receipt(value) {
  const events = {}, elements = {};
  for (const id of ['rcpt', 'amt', 'amt-cn', 'amount-error', 'print', 'today']) {
    const attributes = {};
    elements[id] = {
      textContent: id === 'amt' ? value : '', hidden: false,
      addEventListener: (name, fn) => { events[id + ':' + name] = fn; },
      setAttribute: (name, value) => { attributes[name] = value; },
      removeAttribute: name => { delete attributes[name]; },
      getAttribute: name => attributes[name],
      focus: () => {},
    };
  }
  let prints = 0;
  runInNewContext(script, {
    document: { getElementById: id => elements[id] },
    window: {
      print: () => { prints++; },
      addEventListener: (name, fn) => { events['window:' + name] = fn; },
    },
  });
  return { elements, events, prints: () => prints };
}

test('decimal money is preserved and both representations agree', () => {
  const r = receipt('123.45');
  assert.equal(r.elements['amt-cn'].textContent, '壹佰貳拾參元肆角伍分');
  r.events['amt:blur']();
  assert.equal(r.elements.amt.textContent, '123.45');
  r.events['print:click']();
  assert.equal(r.prints(), 1);
});

test('integer, fractional and grouped amounts render exactly', () => {
  for (const [value, expected] of [
    ['0', '零元整'], ['0.05', '零元伍分'], ['123.00', '壹佰貳拾參元整'],
    ['123.05', '壹佰貳拾參元零伍分'], ['123.4', '壹佰貳拾參元肆角整'],
    ['10,001.01', '壹萬零壹元零壹分'], ['30,000', '參萬元整'],
  ]) {
    const r = receipt(value);
    assert.equal(r.elements['amt-cn'].textContent, expected, value);
    assert.equal(r.elements['amount-error'].hidden, true, value);
  }
});

test('invalid amounts remain unchanged and cannot print a valid receipt', () => {
  for (const value of ['', '-5', '1.005', '1..2', '12,34', '1e3', 'NT$123', '1000000000000']) {
    const r = receipt(value);
    assert.equal(r.elements.amt.getAttribute('aria-invalid'), 'true', value);
    assert.equal(r.elements['amount-error'].hidden, false, value);
    assert.equal(r.elements.rcpt.getAttribute('data-invalid'), 'true', value);
    r.events['amt:blur']();
    assert.equal(r.elements.amt.textContent, value);
    r.events['print:click']();
    assert.equal(r.prints(), 0, value);
  }
});

test('browser print revalidates the amount and valid edits recover', () => {
  const r = receipt('123');
  r.elements.amt.textContent = '1.005';
  r.events['window:beforeprint']();
  assert.equal(r.elements.rcpt.getAttribute('data-invalid'), 'true');
  r.elements.amt.textContent = '0.05';
  r.events['amt:input']();
  assert.equal(r.elements.rcpt.getAttribute('data-invalid'), undefined);
  assert.equal(r.elements['amount-error'].hidden, true);
  r.events['print:click']();
  assert.equal(r.prints(), 1);
});

test('printing hides the invalid receipt while keeping the error visible', () => {
  assert.ok(/@media print\{\{#rcpt\[data-invalid="true"\]\{\{display:none!important\}/.test(source), 'invalid receipt is hidden in print media');
  assert.ok(/id="amount-error"[^>]*role="alert"/.test(source), 'amount validation is announced');
});
