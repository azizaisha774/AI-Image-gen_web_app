const $ = id => document.getElementById(id);
const prompt_ = $('prompt'), go = $('go'), msg = $('msg'), stage = $('stage');
const preview = $('preview'), dl = $('dl'), caption = $('caption'), gallery = $('gallery');

prompt_.addEventListener('input', () => $('count').textContent = prompt_.value.length);

function say(text, isError) { msg.textContent = text; msg.className = isError ? 'err' : ''; }

function showImage(src, text, downloadUrl) {
  $('placeholder').hidden = true;
  preview.src = src; preview.hidden = false;
  caption.textContent = text;
  dl.href = downloadUrl; dl.hidden = false;
}

function addThumb(d) {
  const empty = $('empty'); if (empty) empty.remove();
  const b = document.createElement('button');
  b.className = 'thumb'; b.dataset.id = d.id; b.dataset.prompt = d.prompt; b.dataset.src = d.url;
  b.innerHTML = '<img alt="">'; b.firstChild.src = d.url; b.firstChild.alt = d.prompt;
  gallery.prepend(b);
}

// click an old image to preview it again
gallery.addEventListener('click', e => {
  const t = e.target.closest('.thumb'); if (!t) return;
  showImage(t.dataset.src, t.dataset.prompt, '/download/' + t.dataset.id);
  window.scrollTo({top: 0, behavior: 'smooth'});
});

go.onclick = async () => {
  const text = prompt_.value.trim();
  if (text.length < 3) { say('Write a few words describing the image first.', true); return; }

  go.disabled = true; stage.classList.add('loading'); dl.hidden = true;
  let secs = 0;
  say('Generating... 0s');
  const timer = setInterval(() => say('Generating... ' + (++secs) + 's'), 1000);

  try {
    const res = await fetch('/api/generate', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: text, style: $('style').value, size: $('size').value})
    });
    const d = await res.json();
    if (!d.ok) { say(d.msg, true); }
    else { showImage(d.url, d.prompt, d.download); addThumb(d); say('Done. Your image is ready.'); }
  } catch (err) {
    say('Something went wrong. Check the PyCharm Run window for the error.', true);
  }
  clearInterval(timer);
  stage.classList.remove('loading'); go.disabled = false;
};
