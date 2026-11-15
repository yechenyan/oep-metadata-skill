'use strict';
const locale = window.OEP_GUIDE_LOCALE || {language: 'en', labels: {}, flows: []};
const t = value => locale.labels[value] || value;
const flows = window.OEP_WORKFLOWS.map((flow, index) => {
  const translation = locale.flows[index];
  return translation ? {...flow, ...translation, steps: flow.steps.map((step, i) => ({...step, ...translation.steps[i]}))} : flow;
});
function localizeDocument() {
  document.title = t('OEP Metadata — Workflow field guide');
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (node.parentElement.closest('script, style, pre, code')) continue;
    const value = node.textContent.trim();
    if (locale.labels[value]) node.textContent = node.textContent.replace(value, t(value));
  }
  document.querySelectorAll('[aria-label]').forEach(element => {
    const value = element.getAttribute('aria-label');
    if (locale.labels[value]) element.setAttribute('aria-label', t(value));
  });
}
const byId = id => document.getElementById(id);
const escapeHTML = value => String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
let current = 0;
let position = 0;
let timer = null;
const progress = document.querySelector('[role="progressbar"]');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
function stopPlayback() {
  if (timer !== null) clearInterval(timer);
  timer = null;
  byId('play').innerHTML = '<span class="play-icon" aria-hidden="true">▶</span> ' + t('Play steps');
  byId('play').setAttribute('aria-pressed', 'false');
  byId('walkthrough').classList.remove('running');
}
function syncLanguageLinks() {
  document.querySelectorAll('[data-language-link]').forEach(link => {
    link.setAttribute('href', link.dataset.languageLink + location.hash);
  });
}
function updateLocation() {
  const hash = '#' + flows[current].id + '/' + (position + 1);
  try { history.replaceState(null, '', hash); } catch (_) { /* File URLs may restrict history access. */ }
  syncLanguageLinks();
}
const aiExampleMap = {
  generate: {4: 'generate'},
  review: {3: 'review'},
  'generate-review': {1: 'combined-generator', 2: 'combined-reviewer', 4: 'repair', 5: 're-review'}
};
async function copyExample(text, button) {
  try {
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
    else {
      const area = document.createElement('textarea'); area.value = text;
      area.style.cssText = 'position:fixed;left:-9999px;top:0';
      document.body.append(area); area.select();
      const copied = document.execCommand('copy'); area.remove();
      if (!copied) throw new Error('Clipboard unavailable');
    }
    button.textContent = t('Copied ✓');
  } catch (_) { button.textContent = t('Select prompt to copy'); }
}
function renderAIExample() {
  const key = (aiExampleMap[flows[current].id] || {})[position];
  const example = key && (window.OEP_AI_EXAMPLES || {})[key];
  if (!example) {
    byId('stage-content').insertAdjacentHTML('beforeend', `<p class="no-ai">${escapeHTML(t('No AI execution notice'))}</p>`);
    return;
  }
  const translatedPrompt = (window.OEP_AI_PROMPTS_LOCAL || {})[key];
  const view = {...example, promptLocalized: translatedPrompt || example.prompt};
  const injected = ['combined-generator','combined-reviewer','repair'].includes(key);
  const notice = injected ? `<p class="injected">${escapeHTML(t('Injected error notice'))}</p>` : key === 're-review' ? `<p>${escapeHTML(t('Re-review notice'))}</p>` : '';
  const fields = [['prompt','Full original prompt','Input material'],['output','Full AI output','Candidate file']];
  if (translatedPrompt) fields.unshift(['promptLocalized','Full localized prompt','Input material']);
  const blocks = fields.map(([field,title,label]) => `<details class="example-code"><summary>${escapeHTML(t(title))}</summary><div class="example-actions"><span>${escapeHTML(t(label))} · ${view[field].length.toLocaleString(locale.language)} ${escapeHTML(t('Characters'))}</span><button class="copy" type="button" data-example-copy="${field}">${escapeHTML(t('Copy all'))}</button></div><pre tabindex="0" aria-label="${escapeHTML(t(title))}">${escapeHTML(view[field])}</pre></details>`).join('');
  byId('stage-content').insertAdjacentHTML('beforeend', `<section class="ai-example" aria-label="${escapeHTML(t('AI input and output'))}"><h4>${escapeHTML(t('AI input and output'))}</h4><p>${escapeHTML(t('Illustrative fixture notice'))}</p><p>${escapeHTML(t('Example source'))}</p>${notice}<p>${escapeHTML(t('Prompt assembly notice'))}</p>${translatedPrompt ? `<p>${escapeHTML(t('Localized prompt notice'))}</p>` : ''}${blocks}</section>`);
  byId('stage-content').querySelectorAll('[data-example-copy]').forEach(button => button.addEventListener('click', () => copyExample(view[button.dataset.exampleCopy], button)));
  byId('stage-content').querySelectorAll('.example-code').forEach(details => details.addEventListener('toggle', () => { if (details.open) stopPlayback(); }));
}
function renderRoute() {
  const flow = flows[current];
  byId('route-count').textContent = flow.route_count;
  byId('route-note').textContent = flow.route_note;
  byId('route-list').innerHTML = flow.route.map(node => `<li><button type="button" data-route-step="${node.step}" aria-label="${escapeHTML(node.label)}: ${escapeHTML(flow.steps[node.step].title)}"><code>${escapeHTML(node.label)}</code><small>${escapeHTML(node.detail)}</small></button></li>`).join('');
  byId('optional-tools').innerHTML = flow.optional.map(item => `<article><code>${escapeHTML(item.label)}</code><p>${escapeHTML(item.detail)}</p></article>`).join('');
  byId('route-list').querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
    stopPlayback(); position = Number(button.dataset.routeStep); renderStep();
    byId('stage-content').focus({preventScroll: true});
    byId('walkthrough').scrollIntoView({block: 'start', behavior: reducedMotion ? 'auto' : 'smooth'});
  }));
}
function renderStep(announce = true) {
  const flow = flows[current];
  const step = flow.steps[position];
  byId('route-list').querySelectorAll('button').forEach(button => {
    if (Number(button.dataset.routeStep) === position) button.setAttribute('aria-current', 'step');
    else button.removeAttribute('aria-current');
  });
  for (const [index, button] of [...byId('steps').querySelectorAll('button')].entries()) {
    if (index === position) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
    button.parentElement.classList.toggle('done', index < position);
    button.querySelector('.step-number').textContent = index < position ? '✓' : String(index + 1).padStart(2, '0');
  }
  const ai = /AI|KI|Generator|Reviewer|Repair/.test(step.actor);
  byId('stage-content').innerHTML = `<div class="actor-row"><span class="actor ${ai ? 'ai' : ''}">${escapeHTML(step.actor)}</span><span class="step-index">${t('STEP')} ${String(position + 1).padStart(2, '0')}</span></div><h3>${escapeHTML(step.title)}</h3><p class="body-copy">${escapeHTML(step.body)}</p><div class="io"><div><span class="eyebrow">${t('Input / what arrives')}</span><p>${escapeHTML(step.inputs)}</p></div><div><span class="eyebrow">${t('Output / what leaves')}</span><p>${escapeHTML(step.outputs)}</p></div></div><div class="terminal"><div class="terminal-head"><span>${t('ILLUSTRATIVE COMMAND OR ARTIFACT')}</span><span aria-hidden="true">● ● ●</span></div><pre>${escapeHTML(step.example)}</pre></div><p class="gate"><strong>${t('BEFORE YOU CONTINUE')}</strong>${escapeHTML(step.gate)}</p>`;
  const commandNote = String.raw`<details class="example-code"><summary>${escapeHTML(t('Command authorship'))}</summary><div style="padding:14px;font-size:12px"><p>${escapeHTML(t('Command authorship explanation'))}</p><p>${escapeHTML(t('Command example prompt'))}</p><strong>${escapeHTML(t('Command example output'))}</strong><pre>uv run --locked --project skills/oep-metadata/scripts \
  python skills/oep-metadata/scripts/oep_metadata.py collect --intent generate \
  --data examples/capacity.csv \
  --background examples/capacity-source.md \
  --out runs/draft-01</pre></div></details>`;
  byId('stage-content').insertAdjacentHTML('beforeend', commandNote);
  renderAIExample();
  byId('stage-content').classList.remove('enter');
  if (!reducedMotion) { void byId('stage-content').offsetWidth; byId('stage-content').classList.add('enter'); }
  byId('previous').disabled = position === 0;
  byId('next').disabled = position === flow.steps.length - 1;
  byId('counter').textContent = `${String(position + 1).padStart(2, '0')} / ${String(flow.steps.length).padStart(2, '0')}`;
  byId('progress-fill').style.width = `${(position + 1) / flow.steps.length * 100}%`;
  progress.setAttribute('aria-valuenow', position + 1);
  progress.setAttribute('aria-valuemax', flow.steps.length);
  if (announce) byId('announcement').textContent = `${flow.name}. ${t('Step')} ${position + 1} ${t('of')} ${flow.steps.length}: ${step.title}.`;
  updateLocation();
}
function chooseFlow(index, nextPosition = 0, announce = true) {
  stopPlayback();
  current = index;
  position = Math.max(0, Math.min(nextPosition, flows[index].steps.length - 1));
  const flow = flows[index];
  [...byId('nav').querySelectorAll('button')].forEach((button, i) => button.setAttribute('aria-current', String(i === index)));
  byId('workflow-mode').textContent = `${t('Workflow')} ${flow.tag} / ${flow.id}`;
  byId('workflow-title').textContent = flow.name;
  byId('workflow-description').textContent = flow.description;
  byId('prompt-text').textContent = flow.prompt;
  byId('copy').textContent = t('Copy prompt');
  renderRoute();
  byId('steps').innerHTML = flow.steps.map((step, i) => `<li><button type="button" aria-label="${t('Step')} ${i + 1}: ${escapeHTML(step.title)}"><span class="step-number" aria-hidden="true">${i + 1}</span><span class="step-label">${escapeHTML(step.title)}<small>${escapeHTML(step.actor)}</small></span></button></li>`).join('');
  [...byId('steps').querySelectorAll('button')].forEach((button, i) => button.addEventListener('click', () => { stopPlayback(); position = i; renderStep(); }));
  byId('full-steps').innerHTML = flow.steps.map(step => `<li><h3>${escapeHTML(step.title)}</h3><span class="actor">${escapeHTML(step.actor)}</span><p>${escapeHTML(step.body)}</p><p><strong>${t('Inputs:')}</strong> ${escapeHTML(step.inputs)}<br><strong>${t('Outputs:')}</strong> ${escapeHTML(step.outputs)}<br><strong>${t('Gate:')}</strong> ${escapeHTML(step.gate)}</p></li>`).join('');
  renderStep(announce);
}
byId('nav').innerHTML = flows.map(flow => `<button type="button"><span class="num">${flow.tag}</span><span class="name">${escapeHTML(flow.name)}<span class="sub">${escapeHTML(flow.short)}</span></span></button>`).join('');
[...byId('nav').querySelectorAll('button')].forEach((button, i) => button.addEventListener('click', () => chooseFlow(i)));
byId('previous').addEventListener('click', () => { stopPlayback(); if (position > 0) { position--; renderStep(); } });
byId('next').addEventListener('click', () => { stopPlayback(); if (position < flows[current].steps.length - 1) { position++; renderStep(); } });
byId('play').addEventListener('click', () => {
  if (timer !== null) { stopPlayback(); return; }
  if (position === flows[current].steps.length - 1) { position = 0; renderStep(); }
  byId('play').innerHTML = '<span class="play-icon" aria-hidden="true">Ⅱ</span> ' + t('Pause');
  byId('play').setAttribute('aria-pressed', 'true');
  byId('walkthrough').classList.add('running');
  timer = setInterval(() => {
    position++;
    renderStep();
    if (position === flows[current].steps.length - 1) stopPlayback();
  }, 6500);
});
document.addEventListener('visibilitychange', () => { if (document.hidden) stopPlayback(); });
byId('copy').addEventListener('click', async () => {
  const text = flows[current].prompt;
  try {
    if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
    else {
      const area = document.createElement('textarea'); area.value = text; area.setAttribute('aria-label', 'Prompt to copy'); area.style.cssText = 'position:fixed;top:0;left:-9999px'; document.body.append(area); area.select();
      const copied = document.execCommand('copy'); area.remove(); if (!copied) throw new Error('Clipboard unavailable');
    }
    byId('copy').textContent = t('Copied ✓');
  } catch (_) { byId('copy').textContent = t('Select prompt to copy'); }
});
function restoreLocation() {
  const [id, number] = location.hash.slice(1).split('/');
  const index = flows.findIndex(flow => flow.id === id);
  if (index >= 0) chooseFlow(index, Math.max(0, (parseInt(number, 10) || 1) - 1), false);
  else if (!['boundaries', 'guide', 'review-decisions', 'quality-guarantees'].includes(id)) chooseFlow(0, 0, false);
}
window.addEventListener('hashchange', () => { restoreLocation(); syncLanguageLinks(); });
const initialHash = location.hash;
const [initialId, initialNumber] = initialHash.slice(1).split('/');
const initialIndex = flows.findIndex(flow => flow.id === initialId);
chooseFlow(initialIndex >= 0 ? initialIndex : 0, Math.max(0, (parseInt(initialNumber, 10) || 1) - 1), false);
if (['boundaries', 'guide', 'review-decisions', 'quality-guarantees'].includes(initialId)) { location.hash = initialHash; }
localizeDocument();
syncLanguageLinks();
