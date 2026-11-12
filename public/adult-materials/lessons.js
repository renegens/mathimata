const steps = [...document.querySelectorAll('.step')];
const progress = document.getElementById('progress');
function updateProgress() {
  if (progress) progress.textContent = `Ολοκληρώθηκαν ${steps.filter(x => x.checked).length} από ${steps.length}`;
}
steps.forEach(x => x.addEventListener('change', updateProgress));
updateProgress();
document.querySelectorAll('[data-print]').forEach(x => x.addEventListener('click', () => window.print()));

const note = document.getElementById('note');
const noteForm = document.getElementById('note-form');
const appStatus = document.getElementById('app-status');
if (noteForm) {
  try {
    const saved = sessionStorage.getItem('lesson-practice-note');
    if (saved !== null) { note.value = saved; appStatus.textContent = 'Αποθηκεύτηκε σε αυτή την καρτέλα.'; }
  } catch (_) { /* The save action below reports blocked storage. */ }
  note.addEventListener('input', () => { appStatus.textContent = 'Υπάρχουν αλλαγές. Πάτησε «Αποθήκευση».'; });
  noteForm.addEventListener('submit', event => {
    event.preventDefault();
    try {
      sessionStorage.setItem('lesson-practice-note', note.value);
      appStatus.textContent = 'Αποθηκεύτηκε σε αυτή την καρτέλα.';
    } catch (_) {
      appStatus.textContent = 'Η αποθήκευση αποκλείστηκε από το πρόγραμμα περιήγησης.';
    }
  });
}

const attachment = document.getElementById('attachment');
const fileStatus = document.getElementById('file-status');
const result = document.getElementById('result');
let fileReady = false;
let fileCheck = 0;
async function checkFile() {
  const check = ++fileCheck;
  fileReady = false;
  attachment.setCustomValidity('');
  result.textContent = '';
  const file = attachment.files[0];
  if (!file) { fileStatus.textContent = 'Δεν επιλέχθηκε αρχείο.'; return; }
  fileStatus.textContent = 'Έλεγχος αρχείου…';
  let isPdf = false;
  try {
    const bytes = new Uint8Array(await file.slice(0, 5).arrayBuffer());
    isPdf = String.fromCharCode(...bytes) === '%PDF-' && /\.pdf$/i.test(file.name);
  } catch (_) { /* Show the same short retry instruction below. */ }
  if (check !== fileCheck) return;
  if (!isPdf) {
    attachment.setCustomValidity('Διάλεξε ένα αρχείο PDF.');
    fileStatus.textContent = 'Αυτό δεν είναι PDF. Διάλεξε άλλο αρχείο.';
    return;
  }
  fileReady = true;
  fileStatus.textContent = `Επιλέχθηκε: ${file.name}. Το αρχείο δεν στάλθηκε.`;
}
if (attachment) {
  attachment.addEventListener('change', checkFile);
  for (const id of ['practice-form', 'email-form']) {
    const form = document.getElementById(id);
    if (!form) continue;
    form.addEventListener('input', () => { result.textContent = ''; });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      await checkFile();
      if (!fileReady) { attachment.reportValidity(); return; }
      if (id === 'practice-form') {
        const name = document.getElementById('person').value.trim();
        if (!name) { result.textContent = 'Γράψε ένα όνομα.'; return; }
        result.textContent = `Ο έλεγχος ολοκληρώθηκε.\nΌνομα: ${name}\nΗμερομηνία: ${document.getElementById('date').value}\nΤμήμα: ${document.getElementById('team').value}\nPDF: ${attachment.files[0].name}\nΔεν υποβλήθηκε αίτηση.`;
      } else {
        if (!document.getElementById('subject').value.trim() || !document.getElementById('message').value.trim()) {
          result.textContent = 'Συμπλήρωσε θέμα και μήνυμα.'; return;
        }
        result.textContent = `Το μήνυμα έχει παραλήπτη, θέμα, κείμενο και PDF.\nΣυνημμένο: ${attachment.files[0].name}\nΔεν στάλθηκε email.`;
      }
    });
  }
}

const copyButton = document.getElementById('check-copy');
if (copyButton) copyButton.addEventListener('click', () => {
  const source = document.getElementById('copy-source').value;
  const target = document.getElementById('copy-target').value;
  document.getElementById('copy-status').textContent = source === target && source.trim()
    ? 'Σωστά! Το κείμενο αντιγράφηκε.' : 'Τα κείμενα διαφέρουν. Δοκίμασε ξανά.';
});

const draftForm = document.getElementById('draft-form');
if (draftForm) draftForm.addEventListener('submit', event => {
  event.preventDefault();
  const title = document.getElementById('draft-title').value.trim();
  const text = document.getElementById('draft-text').value.trim();
  const status = document.getElementById('draft-status');
  if (!title || !text) { status.textContent = 'Συμπλήρωσε τίτλο και κείμενο.'; return; }
  const file = new Blob(['\uFEFF' + title + '\n\n' + text + '\n'], {type:'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(file);
  const link = document.createElement('a');
  link.href = url;
  link.download = title.replace(/[\\/:*?"<>|]/g, '-').slice(0, 80) + '.txt';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  status.textContent = 'Ζητήθηκε λήψη του κειμένου. Έλεγξε τις «Λήψεις».';
});

document.querySelectorAll('[data-quiz]').forEach(button => button.addEventListener('click', () => {
  document.getElementById('quiz-status').textContent = button.dataset.quiz === 'true'
    ? button.dataset.answer : 'Σκέψου ξανά την περίπτωση και δοκίμασε άλλη επιλογή.';
}));

const calendarForm = document.getElementById('calendar-form');
if (calendarForm) calendarForm.addEventListener('submit', event => {
  event.preventDefault();
  const title = document.getElementById('event-title').value.trim();
  const date = document.getElementById('event-date').value;
  const time = document.getElementById('event-time').value;
  const status = document.getElementById('calendar-status');
  if (!title || !date || !time) { status.textContent = 'Συμπλήρωσε τίτλο, ημερομηνία και ώρα.'; return; }
  const displayDate = new Date(date + 'T12:00:00').toLocaleDateString('el-GR');
  status.textContent = `Έλεγξε: ${title}, ${displayDate}, ώρα ${time}.\nΔεν δημιουργήθηκε συμβάν και δεν στάλθηκε πρόσκληση.`;
});

const stockForm = document.getElementById('stock-form');
if (stockForm) stockForm.addEventListener('submit', event => {
  event.preventDefault();
  const items = [...stockForm.querySelectorAll('[data-price]')];
  const valid = items.every(item => Number.isInteger(Number(item.value)) && Number(item.value) >= 0 && Number(item.value) <= 1000 && item.value !== '');
  const status = document.getElementById('stock-status');
  if (!valid) { status.textContent = 'Βάλε ακέραιες ποσότητες από 0 έως 1000.'; return; }
  const total = items.reduce((sum,item) => sum + Number(item.value)*Number(item.dataset.price), 0);
  status.textContent = 'Συνολικό κόστος: ' + new Intl.NumberFormat('el-GR',{style:'currency',currency:'EUR'}).format(total);
});

/* --- lesson 1 "Ξεκινώ ξανά" button (was an inline script) --- */
const resetButton = document.getElementById('reset');
if (resetButton) resetButton.addEventListener('click', () => {
  steps.forEach(x => { x.checked = false; });
  updateProgress();
  window.scrollTo({top: 0, behavior: 'smooth'});
});
