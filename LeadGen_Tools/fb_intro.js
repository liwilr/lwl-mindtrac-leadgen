// Step 3 - Facebook page, logged out, one step. Open the page in the browser pane (navigate), then run this whole
// snippet with the browser pane's JavaScript tool. It closes the login dialog, scrolls so the Intro box loads, and
// returns the Intro text plus the WhatsApp button number(s). It never logs in, clicks Like/Message or submits anything.
document.querySelector('[aria-label="Close"]')?.click();
window.scrollTo(0, 600);
await new Promise(r => setTimeout(r, 2500));
document.querySelector('[aria-label="Close"]')?.click();
const t = document.body.innerText;
const label = ['Intro', 'Presentación', 'Detalles', 'Introdução', 'Apresentação'].find(l => t.includes('\n' + l + '\n') || t.startsWith(l + '\n'));
const i = label ? t.indexOf(label) : -1;
const end = i < 0 ? -1 : (() => { const m = t.slice(i).search(/\n(Photos|Fotos)\n/); return m < 0 ? i + 900 : i + m; })();
const htmlText = document.documentElement.innerHTML;
({
  title: document.title,
  // A personal profile shows "Friends"/"Work" tabs instead of an Intro with a page category.
  looks_like_page: i >= 0 && /Page ·|Página ·/.test(t.slice(i, end)),
  intro: i >= 0 ? t.slice(i, end).trim() : null,
  whatsapp_numbers: [...new Set([...htmlText.matchAll(/phone=(\d{9,14})/g)].map(m => m[1]))],
  emails: [...new Set((i >= 0 ? t.slice(i, end) : '').match(/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g) || [])],
  note: i < 0 ? 'Intro not found: reload once and run again; if still missing it is a personal profile or a restricted page.' : null
})
