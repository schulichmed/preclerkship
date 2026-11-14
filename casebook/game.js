const $ = id => document.getElementById(id);
const storageKey = 'schulich-casebook-v1';
const epoch = Date.UTC(2026,10,13);
const dateParts = new Intl.DateTimeFormat('en-CA',{timeZone:'America/Toronto',year:'numeric',month:'numeric',day:'numeric'})
  .formatToParts(new Date()).filter(p => p.type !== 'literal');
const today = Object.fromEntries(dateParts.map(p => [p.type,Number(p.value)]));
const day = Math.max(0,Math.floor((Date.UTC(today.year,today.month-1,today.day)-epoch)/86400000));
// Keep the published daily lineup for the dates it already covered.
const dailyCase = cases[day < 40 ? day : day % cases.length];
const fresh = () => ({turns:[],status:'playing'});
let saved = {};
try { saved = JSON.parse(localStorage.getItem(storageKey)) || {}; } catch {}
let mode = 'daily';
let practiceCase;
let practiceState;
const practiceCompleted = new Set();
let suggestions = [];
let active = -1;
const input = $('guess');
const norm = value => value.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]/g,'');
const diagnoses = [...cases, ...distractors]
  .sort((a,b) => a.answer.localeCompare(b.answer, 'en-CA'));
const diagnosisIndex = diagnoses.map(entry => ({
  entry,
  name: norm(entry.answer),
  aliases: entry.aliases.map(norm).filter(Boolean)
}));
const getCase = () => mode === 'daily' ? dailyCase : practiceCase;
const getState = () => mode === 'daily' ? (saved[day] ??= fresh()) : practiceState;
const add = (parent,tag,copy,cls) => {
  const el = document.createElement(tag);
  if(copy !== undefined) el.textContent = copy;
  if(cls) el.className = cls;
  parent.append(el);
  return el;
};

function practicePool() {
  const block = $('block').value;
  return cases.filter(entry => !block || entry.note.startsWith(block + '-'));
}

function pickPractice() {
  const remaining = practicePool().filter(entry => !practiceCompleted.has(entry));
  const alternatives = remaining.filter(entry => entry !== practiceCase && entry !== dailyCase);
  const choices = alternatives.length ? alternatives : remaining;
  practiceCase = choices[Math.floor(Math.random() * choices.length)];
  practiceState = fresh();
}

function advancePractice() {
  const pool = practicePool();
  if (pool.every(entry => practiceCompleted.has(entry))) {
    for (const entry of pool) practiceCompleted.delete(entry);
  }
  pickPractice();
  render();
  if (practiceCase) input.focus();
}

$('block').add(new Option('All blocks',''));
for (const [id,[label]] of Object.entries(blocks)) $('block').add(new Option(label,id));

function render(message = '') {
  $('daily').setAttribute('aria-pressed',mode==='daily');
  $('practice').setAttribute('aria-pressed',mode==='practice');
  $('practice-controls').hidden = mode==='daily';
  $('practice-count').hidden = mode==='daily';
  if (mode === 'practice') {
    const pool = practicePool();
    const completed = pool.filter(entry => practiceCompleted.has(entry)).length;
    $('practice-count').textContent = completed + ' completed · ' + (pool.length - completed) + ' left';
    $('next').textContent = completed === pool.length ? 'Restart practice ↻' : 'New case ↻';
  }
  const entry = getCase();
  $('case-sheet').hidden = !entry;
  if (!entry) return;
  const state = getState();
  const done = state.status !== 'playing';
  const [block,course] = blocks[entry.note.split('-')[0]];
  const shown = done ? 6 : state.turns.length+1;
  $('case-meta').textContent = mode === 'daily' ? 'Daily case #'+(day+1) : block;
  $('counter').textContent = done ? (state.status === 'won' ? 'Solved in '+state.turns.length+'/6' : 'Case complete') : 'Clue '+shown+' of 6';
  $('progress').replaceChildren();
  $('clues').replaceChildren();
  entry.clues.forEach((clue,index) => {
    const turn = state.turns[index];
    const current = !done && index===shown-1;
    add($('progress'),'span',undefined,turn ? (turn.hit?'hit':'miss') : (current?'current':''));
    const row = add($('clues'),'li',undefined,index>=shown?'locked':(current?'active':''));
    add(row,'span',String(index+1),'n');
    const copy = add(row,'div',index<shown?clue:'Clue locked','clue-copy');
    if(turn) add(copy,'small',turn.guess ? (turn.hit?'Correct · ':'Guessed · ')+turn.guess : 'Skipped');
  });
  $('guess-form').hidden = done;
  $('feedback').textContent = message;
  $('skip').firstChild.textContent = shown===6 ? 'Reveal diagnosis ' : 'Reveal next clue ';
  input.value = '';
  closeSuggestions();
  const result = $('finish');
  result.hidden = !done;
  result.replaceChildren();
  if (!done) return;
  result.classList.toggle('won',state.status==='won');
  add(result,'div',state.status==='won'?'Correct diagnosis':'Diagnosis revealed','eyebrow');
  add(result,'h3',entry.answer);
  add(result,'p',entry.explanation);
  const source = add(result,'a','Read the Schulich lecture ↗');
  source.href = '../'+course+'/'+entry.note.split('-')[0]+'.html#n-'+entry.note;
  source.target = '_blank';
  source.rel = 'noopener noreferrer';
  const button = add(result,'button',mode==='daily'?'Copy result':$('next').textContent.startsWith('Restart')?'Restart practice':'Next case','utility');
  button.type = 'button';
  button.onclick = mode==='daily' ? async () => {
    const marks = state.turns.map(turn=>turn.hit?'🟩':turn.guess?'🟪':'⬜').join('');
    try {
      await navigator.clipboard.writeText('Schulich Casebook #'+(day+1)+' · '+(state.status==='won'?state.turns.length:'X')+'/6\n'+marks);
      button.textContent = 'Copied!';
    } catch { button.textContent = 'Copy unavailable'; }
  } : advancePractice;
}

function submit(guess) {
  const state = getState();
  if(!getCase() || state.status !== 'playing') return;
  const entry = getCase();
  const query = norm(guess);
  const exactName = diagnosisIndex.find(item => item.name === query);
  const candidates = exactName ? [exactName.entry] : diagnosisIndex
    .filter(item => item.aliases.includes(query)).map(item => item.entry);
  if(guess && !candidates.length) {
    $('feedback').textContent = 'Choose a diagnosis from the suggestions.';
    input.focus();
    return;
  }
  if(candidates.length > 1) {
    $('feedback').textContent = 'That abbreviation matches multiple diagnoses. Choose the full name.';
    input.focus();
    return;
  }
  const hit = candidates.includes(entry);
  const label = candidates[0]?.answer ?? '';
  state.turns.push({guess:label,hit});
  if(hit) state.status='won';
  else if(state.turns.length===6) state.status='lost';
  if(mode==='daily') {
    try { localStorage.setItem(storageKey,JSON.stringify(saved)); } catch {}
  }
  if (mode === 'practice' && state.status !== 'playing') practiceCompleted.add(entry);
  render(guess ? 'Try again with the next clue.' : '');
  if(state.status === 'playing') input.focus();
  else {
    $('finish').tabIndex = -1;
    $('finish').focus();
  }
}

function closeSuggestions() {
  suggestions = [];
  active = -1;
  $('suggestions').hidden = true;
  input.setAttribute('aria-expanded','false');
  input.removeAttribute('aria-activedescendant');
}
function highlight(index) {
  active = index;
  Array.from($('suggestions').children).forEach((item,i)=>item.setAttribute('aria-selected',i===active));
  const selected = $('suggestions').children[active];
  input.setAttribute('aria-activedescendant',selected.id);
  selected.scrollIntoView({block:'nearest'});
}
function selectSuggestion(entry) {
  input.value = entry.answer;
  closeSuggestions();
  input.focus();
}
input.addEventListener('input',()=>{
  closeSuggestions();
  $('feedback').textContent = '';
  const query = norm(input.value);
  if(!query) return;
  const nameMatches = diagnosisIndex.filter(item => item.name.startsWith(query));
  const aliasMatches = diagnosisIndex.filter(item =>
    !item.name.startsWith(query) && item.aliases.some(alias => alias.startsWith(query))
  );
  suggestions = [...nameMatches, ...aliasMatches].map(item => item.entry);
  if(!suggestions.length) return;
  const list = $('suggestions');
  list.replaceChildren();
  suggestions.forEach((entry,index)=>{
    const item = add(list,'li',entry.answer);
    item.id = 'option-'+index;
    item.setAttribute('role','option');
    item.setAttribute('aria-selected','false');
    item.onpointerdown = event => event.preventDefault();
    item.onclick = () => selectSuggestion(entry);
  });
  list.hidden = false;
  input.setAttribute('aria-expanded','true');
});
input.addEventListener('keydown',event=>{
  if(!suggestions.length) return;
  if(event.key==='ArrowDown' || event.key==='ArrowUp') {
    event.preventDefault();
    const offset = event.key==='ArrowDown'?1:-1;
    highlight(active<0 && offset<0?suggestions.length-1:(active+offset+suggestions.length)%suggestions.length);
  } else if(event.key==='Enter' && active>=0) {
    event.preventDefault();
    selectSuggestion(suggestions[active]);
  } else if(event.key==='Escape') closeSuggestions();
});
input.addEventListener('blur',closeSuggestions);
$('guess-form').onsubmit = event => {
  event.preventDefault();
  const value = input.value.trim();
  if(value) submit(value);
  else { $('feedback').textContent = 'Enter a diagnosis first.';input.focus(); }
};
$('skip').onclick = () => submit('');
$('daily').onclick = () => { mode='daily';render(); };
$('practice').onclick = () => { mode='practice';if(!practiceCase) pickPractice();render(); };
$('block').onchange = () => { pickPractice();render(); };
$('next').onclick = advancePractice;

$('help').onclick = () => {
  $('dialog-title').textContent = 'How to play';
  const body = $('dialog-body');
  body.replaceChildren();
  const list = add(body,'ol');
  for(const line of ['Read the opening clue and guess the most likely diagnosis.','A wrong guess or a skip reveals the next clue. You have six turns.','After the case, review the explanation and open the original lecture.']) add(list,'li',line);
  add(body,'p','The daily case resets at midnight Eastern time. Practice lets you draw from any available block.');
  $('dialog').showModal();
};
$('stats').onclick = () => {
  $('dialog-title').textContent = 'Daily stats';
  const complete = Object.values(saved).filter(state=>state.status!=='playing');
  const wins = complete.filter(state=>state.status==='won');
  const body = $('dialog-body');
  body.replaceChildren();
  const grid = add(body,'div',undefined,'stats-grid');
  for(const [label,value] of [['Played',complete.length],['Solved',wins.length],['Win rate',complete.length?Math.round(100*wins.length/complete.length)+'%':'—']]) {
    const cell = add(grid,'div');
    add(cell,'b',String(value));
    add(cell,'span',label);
  }
  add(body,'p','Daily results are saved in this browser.');
  $('dialog').showModal();
};
render();
