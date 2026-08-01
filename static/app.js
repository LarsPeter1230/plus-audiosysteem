function bindVolumeSSE(eventsUrl, setVolUrl, stepUrl, muteUrl, rcaUrl){
  const sl = document.getElementById('volSlider');
  let dragging=false;
  function apply(d){
    if(!dragging){ sl.value=d.volume; document.getElementById('volBadge').innerText=d.volume+'%'; }
    document.getElementById('muteBadge').innerText=d.mute_status;
    document.getElementById('rcaBadge').innerText='RCA: '+(d.rca_running?'actief':'gestopt');
  }
  sl.addEventListener('input', ()=>{
    const v=Math.max(0,Math.min(100,parseInt(sl.value||'0')));
    document.getElementById('volBadge').innerText=v+'%';
    fetch(setVolUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({volume:v})});
  });
  sl.addEventListener('mousedown', ()=>dragging=true);
  sl.addEventListener('touchstart', ()=>dragging=true);
  window.addEventListener('mouseup', ()=>dragging=false);
  window.addEventListener('touchend', ()=>dragging=false);
  window.step = (d)=>fetch(stepUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delta:d})});
  window.muteToggle = ()=>fetch(muteUrl,{method:'POST'});
  window.rcaToggle  = ()=>fetch(rcaUrl,{method:'POST'});
  (function start(){
    const es=new EventSource(eventsUrl);
    es.onmessage=(e)=>{ try{apply(JSON.parse(e.data));}catch(_){}}; 
    es.onerror=()=>{ es.close(); setTimeout(start,1500); };
  })();
}

window.ttsSpeak = (url)=>{
  const payload = {
    text: document.getElementById('ttsText').value || '',
    voice: document.getElementById('ttsVoice').value || '',
    rate: parseInt(document.getElementById('ttsRate').value || '165',10),
    gain: parseInt(document.getElementById('ttsGain').value || '80',10)
  };
  fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
};

window.bindKeypadUnlock = (postUrl, redirectTo)=>{
  let buf=[]; const MAXLEN=6;
  const codewin=document.getElementById('codewin');
  const err=document.getElementById('err');
  function render(){ codewin.innerText = buf.length ? '•'.repeat(Math.max(4,buf.length)) : '••••'; }
  window.tap=(d)=>{ if(buf.length<MAXLEN){ buf.push(d); render(); } };
  window.clr=()=>{ buf.pop(); render(); };
  window.enter=()=>{
    fetch(postUrl,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:buf.join('')})})
      .then(r=>r.json()).then(j=>{
        if(j.ok){ window.location = redirectTo; }
        else{ err.style.display='block'; buf=[]; render(); setTimeout(()=>err.style.display='none',1200); }
      });
  };
  render();
};
