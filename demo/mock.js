/* Demo-laag: onderschept API-calls en levert voorbeelddata; laat presets +
   Text-to-Speech via de luidsprekers van de bezoeker klinken. Geen backend. */
(function(){
  var COVER="data:image/svg+xml,"+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#222"/><stop offset="1" stop-color="#555"/></linearGradient></defs><rect width="300" height="300" fill="url(#g)"/><circle cx="150" cy="150" r="60" fill="none" stroke="#1ed760" stroke-width="10"/><circle cx="150" cy="150" r="10" fill="#1ed760"/></svg>');
  var NP={name:"Blinding Lights",artist:"The Weeknd",album:"After Hours",cover:COVER,uri:"spotify:track:demo",state:"playing",position_ms:64000,duration_ms:200000,is_explicit:false,played_by:""};
  var PRHIST=[{title:"Midnight Sun",artist:"Demo Artist",cover:COVER,ts:Date.now()/1000-200},{title:"Golden Hour",artist:"Sample Band",cover:COVER,ts:Date.now()/1000-500},{title:"Night Drive",artist:"Demo Crew",cover:COVER,ts:Date.now()/1000-900}];
  var QUEUE=[{uri:"a",name:"Levitating",artist:"Dua Lipa",cover:COVER,added_by:"Demo"},{uri:"b",name:"As It Was",artist:"Harry Styles",cover:COVER,added_by:"Demo"}];
  function J(o){ return Promise.resolve({ok:true,status:200,headers:{get:function(){return "application/json";}},json:function(){return Promise.resolve(o);},text:function(){return Promise.resolve(JSON.stringify(o));}}); }
  function vizBands(){ var b=[],t=Date.now()/380; for(var i=0;i<28;i++){ var s=Math.sin(Math.PI*i/28),n=0.5+0.5*Math.sin(t*1.7+i*0.6)+0.3*Math.sin(t*1.1+i*1.9); b.push(Math.max(0.03,Math.min(1,s*(0.35+0.5*n)))); } return b; }
  var EQ={freqs:[31,63,125,250,500,1000,2000,4000,8000,16000],bands:[50,50,50,50,50,50,50,50,50,50],flat:50};

  // ── Audio: preset-oproep uit de speakers van de bezoeker ──
  function playPresetAudio(n){ try{ var a=new Audio(n+".mp3"); a.play().catch(function(){}); }catch(e){} }
  // ── TTS: spreek de ingevoerde tekst uit in de browser ──
  function speak(text){ try{ if(!window.speechSynthesis||!text) return; window.speechSynthesis.cancel();
      var u=new SpeechSynthesisUtterance(text); u.lang="nl-NL"; u.rate=1;
      var v=(window.speechSynthesis.getVoices()||[]).filter(function(x){return /nl/i.test(x.lang);})[0]; if(v) u.voice=v;
      window.speechSynthesis.speak(u); }catch(e){} }
  function bodyText(opts){ try{ var b=opts&&opts.body; if(!b) return ""; var o=JSON.parse(b); return o.text||o.tekst||""; }catch(e){ return ""; } }

  var _fetch=window.fetch;
  window.fetch=function(url,opts){
    url=''+url; var post=opts&&opts.method&&opts.method.toUpperCase()!=='GET';
    try{
      var mp=url.match(/\/api\/play_preset\/(\d+)/); if(mp){ playPresetAudio(mp[1]); return J({ok:true}); }
      if(url.indexOf('/api/tts/say')>=0||url.indexOf('/api/tts/preview')>=0){ speak(bodyText(opts)); return J({ok:true,token:"demo"}); }
      if(url.indexOf('/api/tts/status/')>=0) return J({status:"done",token:"demo",ready:true});
      if(url.indexOf('/api/viz/rca')>=0) return J({bands:vizBands(),live:true});
      if(url.indexOf('/api/pi/status')>=0) return J({enabled:true,volume:38,host:"demo",control:true,explicit:false,explicit_name:"",commercial_next:false,jam_url:"",nowplaying:NP,history:[]});
      if(url.indexOf('/api/plusradio/commercials')>=0) return J({available:[],buttons:[]});
      if(url.indexOf('/api/plusradio')>=0 && url.indexOf('channel')<0) return J({nowplaying:{title:"Midnight Sun",artist:"Demo Artist",album:"Demo",cover:COVER},title:"Midnight Sun",artist:"Demo Artist",cover:COVER,history:PRHIST,channel:1,playing:true});
      if(url.indexOf('/api/eq/')>=0){ if(post) return J({ok:true,bands:EQ.bands}); return J(EQ); }
      if(url.indexOf('/api/spotify/queue')>=0){ if(post) return J({ok:true}); return J({items:QUEUE}); }
      if(url.indexOf('/api/spotify/search')>=0) return J({tracks:[{uri:"x",name:"Flowers",artist:"Miley Cyrus",album:"Endless Summer",cover:COVER},{uri:"y",name:"Anti-Hero",artist:"Taylor Swift",album:"Midnights",cover:COVER}]});
      if(url.indexOf('/api/system/version')>=0) return J({current:"v7.8.2",latest:"v7.8.2",update_available:false,is_git:true});
      if(url.indexOf('/api/audio/devices')>=0) return J({playback:[{card:0,id:"USB",name:"Speakers (USB Audio)",device:0,hw:"plughw:0,0"},{card:1,id:"HDMI",name:"HDMI Output",device:0,hw:"plughw:1,0"}],capture:[{card:0,id:"USB",name:"Line-in (USB Audio)",device:0,hw:"plughw:0,0"}],have_np:true});
      if(url.indexOf('/api/audio/test-in')>=0) return J({ok:true,rms:0.03,db:-24.5,signal:true});
      if(url.indexOf('/api/audio/test-out')>=0) return J({ok:true});
    }catch(e){}
    return J({ok:true});
  };
  window.EventSource=function(){ return {close:function(){},addEventListener:function(){},onmessage:null,onerror:null}; };

  window.addEventListener('DOMContentLoaded',function(){
    // Login: demo-gegevens vooraf invullen + "Inloggen" → de app
    var u=document.getElementById('username'), p=document.getElementById('password');
    if(u&&p){
      u.value='demo'; p.value='demo1234';
      var f=u.form||document.querySelector('form');
      if(f) f.addEventListener('submit',function(e){ e.preventDefault(); location.href='volume.html'; });
      var hint=document.createElement('div'); hint.textContent='Demo — klik op Inloggen';
      hint.style.cssText='text-align:center;margin-top:10px;color:#4b7a12;font:600 13px sans-serif';
      (f||document.body).appendChild(hint);
    }
    // Demo-badge
    var d=document.createElement('div'); d.textContent='DEMO — voorbeelddata';
    d.style.cssText='position:fixed;left:12px;bottom:12px;z-index:99999;background:#111;color:#fff;font:700 12px/1 sans-serif;padding:8px 12px;border-radius:999px;opacity:.85;box-shadow:0 2px 10px rgba(0,0,0,.3)';
    document.body.appendChild(d);
    // Speech-stemmen vast laden
    if(window.speechSynthesis) window.speechSynthesis.getVoices();
  });
})();
