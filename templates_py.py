#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
templates_py.py — presentatie-laag (HTML/CSS/Jinja-templates) van het
PLUS Omroepsysteem. Losgekoppeld uit app.py zodat de applicatielogica
overzichtelijk blijft. Bevat UITSLUITEND string-constanten (geen logica,
geen imports uit app.py) — puur code-motion, gedrag ongewijzigd.

BASE_CSS wordt als eerste gedefinieerd; LAYOUT_TPL en LOGIN_TPL bouwen
erop voort (BASE_CSS + body).
"""

BASE_CSS = """
<title>{{ (brand.name if brand is defined and brand else 'PLUS') }} Audiosysteem</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" type="image/png" href="/static/icon.png">
<link rel="apple-touch-icon" href="/static/icon.png">
<link rel="shortcut icon" href="/static/icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&family=DM+Mono:wght@400;500&family=Montserrat:wght@700;800;900&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
<style>
/* "PLUS Radio"-merk-lockup: het volledige PLUS-logo + RADIO in Montserrat.
   Beide erven currentColor → wit op groene tabs, groen/donker op witte vlakken. */
.pr-lockup{display:inline-flex;align-items:center;gap:.42em;white-space:nowrap;vertical-align:-2px}
.pr-lockup svg{height:.8em;width:auto;display:block}
.pr-radio{font-family:'Montserrat','Segoe UI',system-ui,sans-serif;font-weight:800;letter-spacing:.14em;font-size:.82em;line-height:1}
/* ──────────────────────────────────────────────────────────────
   PLUS huisstijl (licht) — gedestilleerd uit de plus.nl styleguide.
   Zelfde class-namen als voorheen, zodat alle pagina's op exact
   dezelfde plek/structuur blijven; alleen de visuele stijl verandert
   van donker-glas naar de lichte PLUS-look.
   Kleuren: Action Green #80bd1d (CTA), Dark Green #115013 (tekst/koppen),
   wit vlak, neutrale grijzen (#333/#6c6c6c/#d8d8d8).
   ────────────────────────────────────────────────────────────── */
:root{
  /* --red* = de primaire actie/CTA-kleur (Action Green). Naam behouden
     voor compatibiliteit met bestaande inline-verwijzingen. */
  --red:#80bd1d;--red-dark:#6aa018;--red-glow:rgba(128,189,29,0.30);
  /* --gold* = merk-accent; op wit vertaald naar PLUS-bosgroen. */
  --gold:#227647;--gold-dim:rgba(34,118,71,0.12);
  --green-dark:#115013;              /* koppen, links, primaire tekst-acties */
  --bg-page:#eef1ea;                 /* paginascherm achter de kaart */
  --bg-card:#ffffff;
  --bg-card-hover:#f5f7f2;
  --bg-soft:#f4f6f1;                 /* subtiele sub-panelen (was rgba zwart) */
  --stroke:#d8d8d8;
  --stroke-light:#e7e9e3;
  --stroke-dark:#c4c8bd;
  --fg:#333333;--fg2:#4a4a4a;--fg3:#6c6c6c;
  --btn:#ffffff;--btnh:#f0f2ec;
  --danger:#fdeceb;--dangerborder:#f1b7b0;--dangertext:#c62828;
  --radius:8px;--radius-sm:8px;
  --btn-radius:24px 24px 24px 4px;   /* kenmerkende PLUS "spraakwolk"-knop */
  --on-primary:#ffffff;              /* tekst/iconen op de gekleurde topbar (thema-afhankelijk) */
  --accent-soft:#eaf4d8;             /* zachte merk-tint (o.a. geselecteerde chip) */
  --shadow:0 1px 3px rgba(0,0,0,.20),0 1px 1px rgba(0,0,0,.14),0 2px 1px -1px rgba(0,0,0,.12);
  --shadow-sm:0 1px 3px rgba(0,0,0,.12);
  --font:"Open Sans","Gotham",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  --serif:"Open Sans","Gotham",system-ui,sans-serif;
  --mono:"DM Mono",ui-monospace,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
/* Touch: verwijder tap-delay + grijze tap-flash; app draait 90% op telefoon/tablet. */
a,button,.btn,.tab,.tabs a,.pill,.k,.preset-tile-icon,input,select,textarea,label,[onclick]{touch-action:manipulation;-webkit-tap-highlight-color:transparent}
html{-webkit-text-size-adjust:100%}
html,body{height:100%;-webkit-font-smoothing:antialiased;overflow-x:hidden}
body{
  font-family:var(--font);color:var(--fg);font-size:15px;line-height:1.55;
  background-color:var(--bg-page);
  min-height:100vh;
}
.wrap{min-height:100vh;display:flex;align-items:flex-start;justify-content:center;padding:clamp(10px,3vw,40px)}
.card{width:min(1060px,96vw);background:var(--bg-card);border:1px solid var(--stroke);border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}
.card-body{padding:clamp(16px,2.8vw,32px)}
/* Kopbalk in Action Green met witte tekst — de PLUS header-look. */
.topbar{
  display:flex;align-items:center;gap:10px;justify-content:space-between;
  padding:0 clamp(14px,2.8vw,30px);
  background:var(--red);
  box-shadow:2px 1px 6px 0 rgba(51,51,51,.20);
  min-height:56px;
}
.topbar-logo{display:flex;align-items:center;gap:13px;white-space:nowrap;padding:10px 0;flex-shrink:0}
.topbar-logo img{height:28px;width:auto;display:block}
/* "Omroepsysteem" als lockup naast het PLUS-woordmerk: scheidingslijn +
   hoofdletters met letterspatiëring, wit — sluit aan bij het logo als één geheel. */
.topbar-logo span{
  color:var(--on-primary);font-weight:800;font-size:12.5px;letter-spacing:.15em;text-transform:uppercase;
  font-family:'Montserrat','Segoe UI',system-ui,sans-serif;line-height:1;
  padding-left:13px;border-left:1.5px solid rgba(255,255,255,.45);
}
.tabs{display:flex;gap:4px;flex-wrap:wrap;padding:8px 0}
.tabs a{
  display:inline-block;padding:7px 15px;border-radius:999px;
  border:1px solid transparent;background:transparent;
  text-decoration:none;color:var(--on-primary);font-weight:600;font-size:13px;
  transition:background .15s,color .15s;
}
.tabs a:hover{background:rgba(255,255,255,.18)}
.tabs a.active{background:#fff;border-color:#fff;color:var(--green-dark);box-shadow:0 2px 6px rgba(0,0,0,.15)}
.topright{display:flex;gap:8px;align-items:center;flex-wrap:wrap;flex-shrink:0}
.pill{
  padding:6px 14px;border-radius:999px;
  border:1px solid rgba(255,255,255,.55);background:rgba(255,255,255,.12);
  text-decoration:none;color:var(--on-primary);font-size:13px;font-weight:600;
  white-space:nowrap;transition:background .15s;
}
.pill:hover{background:rgba(255,255,255,.25)}
.pill-user{background:#fff;border-color:#fff;color:var(--green-dark)}
h1{font-family:var(--serif);font-size:clamp(21px,2.6vw,26px);font-weight:800;margin-bottom:18px;color:var(--green-dark);line-height:1.2}
h1 .gold{color:var(--red-dark)}
h2{font-family:var(--serif);font-size:19px;font-weight:700;margin:20px 0 12px;color:var(--green-dark)}
h3{font-size:15px;font-weight:700;margin:16px 0 10px;color:var(--fg)}
.row{display:flex;flex-wrap:wrap;gap:16px}
.col{flex:1 1 300px}
.label{font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px;color:var(--fg3)}
hr{border:0;border-top:1px solid var(--stroke-light);margin:18px 0}
.help{font-size:13px;color:var(--fg3);line-height:1.5}
.mono{font-family:var(--mono)}
/* Inline Material Symbol-icoon (vervangt emoji's in knoppen/tabs/koppen). */
.material-symbols-outlined{font-variation-settings:'opsz' 24,'wght' 500,'GRAD' 0,'FILL' 0}
.mi{font-family:'Material Symbols Outlined';font-weight:normal;font-style:normal;font-size:18px;line-height:1;letter-spacing:normal;text-transform:none;display:inline-block;white-space:nowrap;word-wrap:normal;direction:ltr;vertical-align:-4px;-webkit-font-feature-settings:'liga';font-feature-settings:'liga';-webkit-font-smoothing:antialiased}
.mi-sm{font-size:16px;vertical-align:-3px}
.btn .mi{margin-right:2px}
.tabs a .mi,.nav-drawer a .mi,.pill .mi{font-size:18px;vertical-align:-4px;margin-right:3px}
/* Touch-vriendelijke checkbox-rij (grotere hitbox, PLUS-groen vinkje). */
.switch-row{display:flex;align-items:center;gap:10px;font-size:15px;color:var(--fg2);cursor:pointer;padding:6px 0;min-height:44px}
.switch-row input[type=checkbox]{width:22px;height:22px;flex-shrink:0;accent-color:var(--red);cursor:pointer}
/* Pill-selectie (stemmen, presets, weergave) — licht thema, touch-vriendelijk. */
.chip{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--stroke);background:#fff;padding:9px 14px;border-radius:999px;font-size:14px;cursor:pointer;color:var(--fg2);min-height:44px}
.chip input{accent-color:var(--red);width:18px;height:18px;flex-shrink:0}
.chip:has(input:checked){border-color:var(--red);background:var(--accent-soft);color:var(--green-dark);font-weight:600}
.chip-wrap{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.radio-card{display:flex;align-items:center;gap:10px;border:1px solid var(--stroke);background:#fff;padding:12px 16px;border-radius:12px;cursor:pointer;font-size:15px;color:var(--fg2);min-height:52px;flex:1 1 200px}
.radio-card input{accent-color:var(--red);width:20px;height:20px;flex-shrink:0}
.radio-card:has(input:checked){border-color:var(--red);background:#eaf4d8;color:var(--green-dark);font-weight:600}
/* Sectiekaart voor formulieren (gebruiker bewerken e.d.) */
.form-card{border:1px solid var(--stroke);border-radius:var(--radius-sm);background:#fff;box-shadow:var(--shadow-sm);padding:18px;margin-bottom:16px}
.form-card h3{margin-top:0;color:var(--green-dark)}
.form-card.dimmed{opacity:.55}
.form-card.dimmed input,.form-card.dimmed .chip,.form-card.dimmed label{pointer-events:none}
/* Herbruikbare sub-tabs (gebruiker bewerken e.d.) */
.subtabs{display:flex;gap:6px;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:6px;margin-bottom:18px;border-bottom:1px solid var(--stroke-light)}
.subtab{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;padding:10px 16px;border:1px solid var(--stroke);background:#fff;border-radius:24px 24px 24px 4px;color:var(--fg2);font-weight:600;font-size:14px;cursor:pointer;min-height:44px;flex-shrink:0}
.subtab .mi{font-size:18px;vertical-align:-4px}
.subtab:hover{background:var(--btnh)}
.subtab.active{background:var(--red);border-color:var(--red);color:#fff}
.subpanel{display:none}
.subpanel.active{display:block}
.input,textarea,select{
  width:100%;padding:12px 14px;border-radius:var(--radius-sm);
  border:1px solid var(--stroke);background:#fff;
  font:inherit;color:var(--fg);transition:border-color .15s,box-shadow .15s;
}
.input::placeholder,textarea::placeholder{color:#999}
.input:focus,textarea:focus,select:focus{outline:none;border-color:var(--green-dark);box-shadow:0 0 0 2px rgba(17,80,19,.12)}
select option{background:#fff;color:var(--fg)}
textarea{min-height:120px;resize:vertical}
.btn{
  display:inline-flex;align-items:center;justify-content:center;gap:7px;
  padding:12px 18px;border-radius:var(--btn-radius);
  border:1px solid var(--green-dark);background:#fff;
  font:inherit;font-weight:700;font-size:14px;cursor:pointer;
  color:var(--green-dark);text-decoration:none;
  transition:background .18s,color .18s,box-shadow .18s;width:100%;
}
.btn:hover{background:var(--btnh)}
.btn-primary{background:var(--red);border-color:var(--red);color:#fff;box-shadow:0 6px 16px var(--red-glow)}
.btn-primary:hover{background:var(--red-dark)!important;border-color:var(--red-dark)}
.btn-stop{background:var(--danger);border-color:var(--dangerborder);color:var(--dangertext)}
.btn-stop:hover{background:#fbdcd8!important}
.btn-danger{background:var(--danger);border-color:var(--dangerborder);color:var(--dangertext)}
.btn-danger:hover{background:#fbdcd8!important}
.btn-sm{padding:8px 13px;font-size:13px;border-radius:16px 16px 16px 4px}
.btn-inline{width:auto}
.btn-gold{background:#fff;border-color:var(--gold);color:var(--gold)}
.btn-gold:hover{background:var(--gold-dim)!important}
.range{-webkit-appearance:none;appearance:none;width:100%;height:14px;background:#e4e7df;border-radius:999px;border:1px solid var(--stroke)}
.range::-webkit-slider-thumb{-webkit-appearance:none;width:26px;height:26px;border-radius:50%;background:var(--red);border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.25)}
.range::-moz-range-thumb{width:24px;height:24px;border-radius:50%;background:var(--red);border:2px solid #fff}
.badge{display:inline-block;padding:5px 12px;border-radius:999px;border:1px solid var(--stroke);background:#f4f6f1;font-weight:700;font-size:14px;color:var(--fg)}
.table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--stroke);border-radius:var(--radius-sm);overflow:hidden}
.table th,.table td{padding:10px 13px;border-bottom:1px solid var(--stroke-light);text-align:left;font-size:14px;color:var(--fg2)}
.table th{background:#f4f6f1;font-weight:700;color:var(--green-dark);text-transform:uppercase;font-size:11px;letter-spacing:.05em}
.table tr:last-child td{border-bottom:none}
.table tr:hover td{background:#f7f9f4}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.card-item{padding:16px;border-radius:var(--radius-sm);border:1px solid var(--stroke);background:#fff;box-shadow:var(--shadow-sm)}
.preset-tile-icon{user-select:none;-webkit-tap-highlight-color:transparent}
.preset-tile-icon:hover{background:#eaf4d8!important;transform:scale(1.03)}
.preset-tile-icon:active{transform:scale(.97)}
.rbadge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700}
.rbadge-admin{background:#fdeceb;color:#c62828;border:1px solid #f1b7b0}
.rbadge-operator{background:var(--gold-dim);color:var(--gold);border:1px solid rgba(34,118,71,.35)}
.rbadge-user{background:#eaf4d8;color:#4b7a12;border:1px solid #cbe3a0}
.rbadge-custom{background:#efe9f7;color:#554DA7;border:1px solid #cdc2e8}
.sbadge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700}
.sbadge-local{background:var(--gold-dim);color:var(--gold)}
.sbadge-sso{background:#efe9f7;color:#554DA7}
.days{display:flex;flex-wrap:wrap;gap:8px}
.days label{display:flex;align-items:center;gap:7px;border:1px solid var(--stroke);background:#fff;padding:7px 12px;border-radius:999px;font-size:14px;cursor:pointer;color:var(--fg2)}
.pad{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;max-width:360px;margin:auto}
.pad .k{padding:16px;border-radius:12px;border:1px solid var(--stroke);background:#fff;font-weight:800;font-size:20px;cursor:pointer;text-align:center;transition:background .12s,transform .1s;user-select:none;color:var(--green-dark);box-shadow:var(--shadow-sm)}
.pad .k:hover{background:var(--btnh);transform:scale(1.04)}
.codewin{letter-spacing:12px;font-size:26px;background:#fff;border:1px solid var(--stroke);border-radius:8px;padding:13px;text-align:center;font-weight:800;user-select:none;color:var(--green-dark)}
.modal-backdrop{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(17,40,20,.55);z-index:9999;padding:20px}
.modal{width:min(760px,94vw);max-height:82vh;overflow-y:auto;background:#fff;color:var(--fg);border:1px solid var(--stroke);border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.30);padding:22px 24px}
.modal .mactions{display:flex;justify-content:flex-end;margin-top:12px}
.md-body{font-size:15px;line-height:1.7;color:var(--fg2)}
.md-body h1,.md-body h2{font-family:var(--serif);color:var(--green-dark);margin:16px 0 8px}
.md-body h1{font-size:22px}.md-body h2{font-size:18px}
.md-body h3{font-size:15px;font-weight:700;color:var(--fg);margin:12px 0 6px}
.md-body p{margin:0 0 10px}
.md-body ul,.md-body ol{padding-left:20px;margin:0 0 10px}
.md-body li{margin-bottom:4px}
.md-body strong{color:var(--green-dark);font-weight:700}
.md-body em{color:var(--gold);font-style:italic}
.md-body code{font-family:var(--mono);font-size:13px;background:#f0f2ec;padding:2px 6px;border-radius:5px;color:var(--gold)}
.md-body pre{background:#f4f6f1;border:1px solid var(--stroke);border-radius:8px;padding:12px;overflow-x:auto;margin:0 0 12px}
.md-body pre code{background:none;padding:0;color:var(--fg2)}
.md-body blockquote{border-left:3px solid var(--red);margin:0 0 10px;padding:6px 14px;background:#f4f6f1;border-radius:0 8px 8px 0;color:var(--fg2)}
.md-body a{color:var(--green-dark);text-decoration:underline}
.md-body hr{border:0;border-top:1px solid var(--stroke-light);margin:14px 0}
.md-body table{width:100%;border-collapse:collapse;margin-bottom:12px;font-size:14px}
.md-body table th,.md-body table td{padding:7px 10px;border:1px solid var(--stroke-light);text-align:left}
.md-body table th{background:#f4f6f1;font-weight:700;color:var(--green-dark)}
.alert{padding:11px 15px;border-radius:var(--radius-sm);margin-bottom:14px;font-size:14px;font-weight:600;border:1px solid}
.alert-ok{background:#eaf4d8;border-color:#cbe3a0;color:#3d6a12}
.alert-err{background:var(--danger);border-color:var(--dangerborder);color:var(--dangertext)}
.alert-warn{background:#fff6e0;border-color:#f2d98a;color:#8a6d00}
.footer{
  padding:10px clamp(14px,2.8vw,30px);border-top:1px solid var(--stroke-light);
  font-size:12px;color:var(--fg3);background:#f7f9f4;
  display:flex;align-items:center;gap:8px;
}
.footer::before{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--red);flex-shrink:0}
.ver-link{color:var(--fg3);text-decoration:underline dotted;text-underline-offset:2px;cursor:pointer;transition:color .15s}
.ver-link:hover{color:var(--green-dark)}
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.login-card{
  width:min(420px,96vw);
  background:#fff;
  border:1px solid var(--stroke);border-radius:var(--radius);box-shadow:0 10px 40px rgba(0,0,0,.18);
  padding:clamp(28px,5vw,44px);
  border-top:4px solid var(--red);
}
.login-logo{font-family:var(--serif);font-size:26px;font-weight:800;color:var(--green-dark);margin-bottom:4px}
.login-logo span{color:var(--red-dark)}
.login-sub{font-size:13px;color:var(--fg3);margin-bottom:28px;font-style:italic}
.divider{display:flex;align-items:center;gap:10px;margin:20px 0;font-size:13px;color:var(--fg3)}
.divider::before,.divider::after{content:'';flex:1;border-top:1px solid var(--stroke-light)}
.oidc-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;width:100%;
  padding:11px 16px;border-radius:var(--radius-sm);
  border:1px solid var(--stroke);background:#fff;
  font:inherit;font-weight:600;font-size:14px;cursor:pointer;text-decoration:none;
  color:var(--green-dark);transition:background .15s;
}
.oidc-btn:hover{background:var(--btnh)}
.section-label{
  font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--gold);margin-bottom:8px;display:block;
}
.table-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:var(--radius-sm)}
.lcbadge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;font-family:var(--mono);white-space:nowrap}
.lc-login   {background:var(--gold-dim);color:var(--gold)}
.lc-logout  {background:#eceee8;color:var(--fg3)}
.lc-preset  {background:#eaf4d8;color:#4b7a12}
.lc-tts     {background:#e4edff;color:#2a5bd7}
.lc-admin   {background:#fdeceb;color:#c62828}
.lc-sso     {background:#efe9f7;color:#554DA7}
.lc-system  {background:#eceee8;color:var(--fg3)}
.lc-schedule{background:#fff1d6;color:#a5730a}
.lc-ha      {background:#d9f3f7;color:#0e7f92}
.lc-rca     {background:#d9f5e4;color:#0e8a4a}
.lc-3cx     {background:#ffe6cc;color:#b5620a}
.lc-volume  {background:#e6e6ff;color:#4a4ad1}
.hamburger{
  display:none;flex-direction:column;gap:5px;cursor:pointer;
  padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,.55);
  background:rgba(255,255,255,.12);flex-shrink:0;
}
.hamburger span{display:block;width:20px;height:2px;background:#fff;border-radius:2px;transition:transform .2s,opacity .2s}
.hamburger.open span:nth-child(1){transform:translateY(7px) rotate(45deg)}
.hamburger.open span:nth-child(2){opacity:0}
.hamburger.open span:nth-child(3){transform:translateY(-7px) rotate(-45deg)}
.nav-drawer{
  display:flex;flex-direction:column;gap:4px;
  padding:0 clamp(14px,2.8vw,30px);
  border-top:0 solid var(--stroke-light);
  background:#f7f9f4;
  max-height:0;opacity:0;overflow:hidden;
  transition:max-height .3s cubic-bezier(.22,1,.36,1),opacity .22s ease,padding .3s ease;
}
.nav-drawer.open{max-height:70vh;opacity:1;padding:12px clamp(14px,2.8vw,30px);border-top-width:1px}
.nav-drawer a{
  display:block;padding:12px 14px;border-radius:var(--radius-sm);
  border:1px solid var(--stroke);background:#fff;
  text-decoration:none;color:var(--fg2);font-weight:600;font-size:15px;min-height:48px;
  transition:background .15s,border-color .15s,transform .12s;
}
.nav-drawer a:active{transform:scale(.99)}
.nav-drawer a.active{background:var(--red);border-color:var(--red);color:#fff}
.log-filters{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;align-items:center}
.log-filter-btn{
  padding:5px 12px;border-radius:999px;border:1px solid var(--stroke);
  background:#fff;color:var(--fg2);font-size:13px;font-weight:600;
  cursor:pointer;transition:background .12s;
}
.log-filter-btn:hover,.log-filter-btn.on{background:var(--red);border-color:var(--red);color:#fff}
/* Echt Spotify-logo in de logs (categorie-badge + filterknop); wit chipje zodat
   het groene logo ook op de groene actieve knop zichtbaar blijft. */
.lc-splogo{height:13px;width:auto;background:#fff;padding:2px 5px;border-radius:4px;vertical-align:-3px;display:inline-block;box-shadow:0 1px 2px rgba(0,0,0,.12)}
.log-search{
  flex:1;min-width:160px;padding:8px 12px;border-radius:999px;
  border:1px solid var(--stroke);background:#fff;
  color:var(--fg);font:inherit;font-size:13px;
}
.log-search::placeholder{color:#999}
.log-search:focus{outline:none;border-color:var(--green-dark)}
.tts-actions-panel{
  border:1px solid #cbe3a0;
  background:#f4f9ea;
  border-radius:12px;
  padding:16px;
  margin-top:4px;
}
@media(max-width:720px){
  .wrap{padding:0}
  .card{border-radius:0;width:100%}
  .card-body{padding:14px}
  .card-grid{grid-template-columns:repeat(2,1fr);gap:12px}   /* 2 kolommen presets in portrait */
  .col{flex:1 1 100%}
  .topbar{flex-wrap:nowrap;min-height:56px;gap:8px}
  .topbar-logo{font-size:15px;padding:10px 0;gap:9px}
  .topbar-logo span{display:inline-block;font-size:10.5px;letter-spacing:.1em;padding-left:9px}
  .tabs{display:none}
  .topright{display:none}
  .hamburger{display:flex;width:44px;height:44px;align-items:center;justify-content:center;gap:5px}
  .table-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:var(--radius-sm)}
  .table{font-size:13px;min-width:480px}
  .table th,.table td{padding:9px 10px}
  .log-filters{gap:6px}
  .log-filter-btn{font-size:13px;padding:7px 12px;min-height:38px}
  .pad{max-width:100%}
  /* Grotere tap-targets in portrait */
  .btn{min-height:50px;font-size:15px}
  .btn-sm{min-height:40px}
  .input,textarea,select{font-size:16px;min-height:50px}   /* 16px voorkomt iOS-zoom bij focus */
  .nav-drawer a{padding:14px 16px;font-size:16px;min-height:50px}
  .days label{min-height:44px;padding:9px 14px}
  .switch-row{min-height:50px;font-size:16px}
  .range{height:22px}
  .range::-webkit-slider-thumb{width:34px;height:34px}
  .range::-moz-range-thumb{width:32px;height:32px}
  h1{font-size:22px}
}
/* Heel smalle telefoons: presets weer 1 grote kolom mag ook — 2 is prima,
   maar bij zeer kleine schermen iets meer ademruimte. */
@media(max-width:360px){
  .card-grid{gap:10px}
}
@media(min-width:721px){
  .hamburger{display:none!important}
  .nav-drawer{display:none!important}
}
/* Tablet / smal desktop: geen hamburger, maar de tabs passen niet op één regel
   naast logo + gebruiker. Zet ze daarom netjes op een eigen, volledige tweede
   rij (links uitgelijnd) i.p.v. verticaal gekneld in het midden. */
@media(min-width:721px) and (max-width:1200px){
  .topbar{flex-wrap:wrap;align-items:center;padding-top:0;padding-bottom:0}
  .topbar-logo{order:1}
  .topright{order:2}
  .tabs{order:3;flex:1 1 100%;justify-content:flex-start;gap:6px;padding:0 0 10px}
}
/* ── App-brede, subtiele bewegingen (clean, niet over-the-top) ── */
/* Bewust GEEN pagina-inlaad-animatie op de hoofdkaart: paginawissels moeten
   (vrijwel) instant voelen. Alleen de losse inlogkaart mag zacht faden. */
@keyframes page-in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.plus-login,.login-card{animation:page-in .24s cubic-bezier(.22,1,.36,1) both}
.btn,.pill,.tab,.tabs a,.subtab,.btab,.chip,.radio-card,.log-filter-btn,.tile-edit-btn{transition:background .16s ease,border-color .16s ease,color .16s ease,box-shadow .16s ease,transform .12s ease}
.btn:active,.pill:active,.subtab:active,.btab:active,.log-filter-btn:active,.chip:active{transform:scale(.975)}
.card-item{transition:box-shadow .18s ease,transform .12s ease,background .16s ease}
.modal-backdrop,.np-backdrop,.ip-backdrop{transition:opacity .2s ease}
a,button{-webkit-tap-highlight-color:transparent}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important;scroll-behavior:auto!important}
}
</style>
"""

LAYOUT_TPL = BASE_CSS + """
{{ branding_style }}
<div class="wrap"><div class="card">
  <div class="topbar">
    <div class="topbar-logo">
      <img src="{{ logo }}" alt="{{ brand.name }}">
      <span>Audiosysteem</span>
    </div>
    <div class="tabs">
      {% if vis.volume  %}<a href="{{ url_for('volume_page')  }}" class="{{ 'active' if tab=='vol'      else '' }}"><span class="mi">music_note</span>Muziek</a>{% endif %}
      {% if vis.presets %}<a href="{{ url_for('presets_page') }}" class="{{ 'active' if tab=='presets'  else '' }}"><span class="mi">queue_music</span>Presets</a>{% endif %}
      {% if vis.tts     %}<a href="{{ url_for('tts_page')     }}" class="{{ 'active' if tab=='tts'      else '' }}"><span class="mi">record_voice_over</span>Text to Speech</a>{% endif %}
      {% if admin %}
      <a href="{{ url_for('beheer_page')      }}" class="{{ 'active' if tab=='beheer'     else '' }}"><span class="mi">settings</span>Beheer</a>
      <a href="{{ url_for('gebruikers_page')  }}" class="{{ 'active' if tab=='gebruikers' else '' }}"><span class="mi">group</span>Gebruikers</a>
      <a href="{{ url_for('oidc_page')        }}" class="{{ 'active' if tab=='oidc'       else '' }}"><span class="mi">key</span>OIDC</a>
      <a href="{{ url_for('logs_page')        }}" class="{{ 'active' if tab=='logs'       else '' }}"><span class="mi">receipt_long</span>Logs</a>
      {% endif %}
    </div>
    <div class="topright">
      {% if logged_in %}
        <span class="pill pill-user" onclick="openUserMenu()" style="cursor:pointer" title="Mijn profiel">{% if my_avatar %}<img src="{{ my_avatar }}" alt="" style="width:20px;height:20px;border-radius:50%;object-fit:cover;vertical-align:-5px;margin-right:6px">{% endif %}{{ display_name }}</span>
        <a class="pill" href="{{ url_for('logout') }}">Uitloggen</a>
      {% else %}
        <a class="pill" href="{{ url_for('login_page') }}">Inloggen</a>
      {% endif %}
    </div>
    <div class="hamburger" id="hambBtn" onclick="toggleNav()">
      <span></span><span></span><span></span>
    </div>
  </div>
  <div class="nav-drawer" id="navDrawer">
    {% if vis.volume  %}<a href="{{ url_for('volume_page')  }}" class="{{ 'active' if tab=='vol'      else '' }}"><span class="mi">music_note</span> Muziek</a>{% endif %}
    {% if vis.presets %}<a href="{{ url_for('presets_page') }}" class="{{ 'active' if tab=='presets'  else '' }}"><span class="mi">queue_music</span> Presets</a>{% endif %}
    {% if vis.tts     %}<a href="{{ url_for('tts_page')     }}" class="{{ 'active' if tab=='tts'      else '' }}"><span class="mi">record_voice_over</span> Text to Speech</a>{% endif %}
    {% if admin %}
    <a href="{{ url_for('beheer_page')     }}" class="{{ 'active' if tab=='beheer'     else '' }}"><span class="mi">settings</span> Beheer</a>
    <a href="{{ url_for('gebruikers_page') }}" class="{{ 'active' if tab=='gebruikers' else '' }}"><span class="mi">group</span> Gebruikers</a>
    <a href="{{ url_for('oidc_page')       }}" class="{{ 'active' if tab=='oidc'       else '' }}"><span class="mi">key</span> OIDC</a>
    <a href="{{ url_for('logs_page')       }}" class="{{ 'active' if tab=='logs'       else '' }}"><span class="mi">receipt_long</span> Logs</a>
    {% endif %}
    {% if logged_in %}
    <a href="{{ url_for('profile_page') }}"><span class="mi">account_circle</span> Mijn profiel</a>
    <a href="{{ url_for('logout') }}" style="border-color:#f1b7b0;color:#c62828"><span class="mi">logout</span> Uitloggen ({{ display_name }})</a>
    {% endif %}
  </div>
  <div class="card-body">
    {{ body|safe }}
  </div>
  <div class="footer"><a href="#" class="ver-link" onclick="openChangelog();return false" title="Bekijk de changelog">{{ settings.version or 'v6' }}</a>{% if display_name %} &middot; {{ display_name }}{% endif %} &middot; {{ brand.name }}{% if settings.location_name %} {{ settings.location_name }}{% endif %} Audiosysteem</div>
</div></div>

<div id="mb" class="modal-backdrop" onclick="mbBackdropClick(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <h3 style="margin:0"><span class="mi">new_releases</span> Changelog</h3>
      <button class="btn btn-inline btn-sm" onclick="closeModal()" style="width:auto;padding:6px 14px" aria-label="Sluiten"><span class="mi">close</span> Sluiten</button>
    </div>
    <div id="modalText" class="md-body"></div>
  </div>
</div>

{% if logged_in %}
<div id="userMenu" class="modal-backdrop" onclick="if(event.target===this)closeUserMenu()">
  <div class="modal" style="max-width:400px;text-align:center">
    <div style="display:flex;flex-direction:column;align-items:center;gap:8px;margin-bottom:18px">
      {% if my_avatar %}<img src="{{ my_avatar }}" alt="" style="width:74px;height:74px;border-radius:50%;object-fit:cover;border:3px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,.2)">{% else %}<div style="width:74px;height:74px;border-radius:50%;background:var(--red);color:#fff;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:800">{{ (display_name or 'U')[:1]|upper }}</div>{% endif %}
      <div style="font-size:18px;font-weight:800;color:var(--green-dark)">{{ display_name }}</div>
      {% if my_email %}<div class="help" style="word-break:break-all">{{ my_email }}</div>{% endif %}
      <div><span class="rbadge rbadge-{{ my_role }}">{{ my_role }}</span> <span class="sbadge sbadge-{{ my_source }}">{{ my_source }}</span></div>
    </div>
    <a class="btn btn-primary" href="{{ url_for('profile_page') }}" style="text-decoration:none"><span class="mi">manage_accounts</span> Profiel bekijken / bewerken</a>
    <div style="height:8px"></div>
    <a class="btn" href="{{ url_for('logout') }}" style="text-decoration:none"><span class="mi">logout</span> Uitloggen</a>
    <div style="margin-top:12px"><button class="btn btn-inline btn-sm" onclick="closeUserMenu()" style="width:auto"><span class="mi">close</span> Sluiten</button></div>
  </div>
</div>
{% endif %}

<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js" crossorigin="anonymous"></script>
<script>
const IS_ADMIN={{ 'true' if admin else 'false' }};
const PRESETS_LOCK={{ 'true' if PRESETS_LOCK else 'false' }},PRESETS_SECS={{ (settings.presets_lock_seconds or 30)|int }};
const TTS_LOCK={{ 'true' if TTS_LOCK else 'false' }},TTS_SECS={{ (settings.tts_lock_seconds or 30)|int }};

function renderMarkdown(text){
  if(typeof marked!=='undefined'){
    marked.setOptions({breaks:true,gfm:true});
    return marked.parse(text);
  }
  return '<pre style="white-space:pre-wrap">'+text.replace(/</g,'&lt;')+'</pre>';
}
// ── Confetti: subtiel & realistisch, bij de changelog-popup op een nieuwe versie.
// Twee lichte golven die onder zwaartekracht vallen en fladderen; bij het sluiten
// van de popup vallen ze versneld naar beneden en vagen ze weg. Respecteert
// prefers-reduced-motion. Zelfstandig (canvas, geen library).
var _confetti=(function(){
  var canvas,ctx,pieces=[],raf=null,running=false,closing=false,W=0,H=0;
  function ensure(){
    if(canvas)return;
    canvas=document.createElement('canvas');
    canvas.style.cssText='position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:10000';
    document.body.appendChild(canvas);ctx=canvas.getContext('2d');resize();
    window.addEventListener('resize',resize);
  }
  function resize(){
    if(!canvas)return;var dpr=Math.min(window.devicePixelRatio||1,2);
    W=window.innerWidth;H=window.innerHeight;
    canvas.width=W*dpr;canvas.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  function palette(){
    var cs=getComputedStyle(document.documentElement);
    function v(n,f){var c=(cs.getPropertyValue(n)||'').trim();return c||f;}
    return [v('--red','#80bd1d'),v('--gold','#227647'),v('--green-dark','#115013'),'#ffd34e','#ffffff','#ff7043'];
  }
  function spawn(n){
    var cols=palette();
    for(var i=0;i<n;i++){pieces.push({
      x:Math.random()*W, y:-20-Math.random()*H*0.35,
      vx:(Math.random()-0.5)*1.2, vy:1.2+Math.random()*1.8,
      w:5+Math.random()*6, h:8+Math.random()*7,
      rot:Math.random()*Math.PI*2, vrot:(Math.random()-0.5)*0.2,
      wob:Math.random()*Math.PI*2, wobs:0.03+Math.random()*0.05,
      color:cols[(Math.random()*cols.length)|0], opacity:1
    });}
  }
  function step(){
    ctx.clearRect(0,0,W,H);
    for(var i=pieces.length-1;i>=0;i--){
      var p=pieces[i];
      p.wob+=p.wobs;
      p.x+=p.vx+Math.sin(p.wob)*0.6;
      p.vy+=closing?0.55:0.05;
      if(!closing&&p.vy>3.0)p.vy=3.0;
      p.y+=p.vy; p.rot+=p.vrot;
      if(closing)p.opacity-=0.03;
      if(p.y>H+30||p.opacity<=0){pieces.splice(i,1);continue;}
      ctx.save();ctx.globalAlpha=Math.max(0,p.opacity);
      ctx.translate(p.x,p.y);ctx.rotate(p.rot);ctx.fillStyle=p.color;
      ctx.fillRect(-p.w/2,-p.h/2,p.w,p.h*(0.55+0.45*Math.abs(Math.cos(p.wob))));
      ctx.restore();
    }
    if(pieces.length){raf=requestAnimationFrame(step);}
    else{running=false;if(raf){cancelAnimationFrame(raf);raf=null;}if(ctx)ctx.clearRect(0,0,W,H);}
  }
  return {
    start:function(){
      if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
      ensure();closing=false;spawn(90);
      setTimeout(function(){if(running&&!closing)spawn(40);},350);
      if(!running){running=true;step();}
    },
    close:function(){closing=true;}
  };
})();
function closeModal(){document.getElementById('mb').style.display='none'; if(window._confetti)_confetti.close();}
function mbBackdropClick(e){if(e.target===document.getElementById('mb')) closeModal();}
function openUserMenu(){var m=document.getElementById('userMenu');if(m)m.style.display='flex';}
function closeUserMenu(){var m=document.getElementById('userMenu');if(m)m.style.display='none';}
document.addEventListener('keydown',function(e){if(e.key==='Escape') closeModal();});

function deadlineKey(s){return"omroep_kiosk_v3_"+s;}
function nowSec(){return Math.floor(Date.now()/1000);}
function getDeadline(s){try{return parseInt(localStorage.getItem(deadlineKey(s))||"0",10);}catch(_){return 0;}}
function setDeadline(s,ts){try{localStorage.setItem(deadlineKey(s),String(ts));}catch(_){}}
function clearDeadline(s){try{localStorage.removeItem(deadlineKey(s));}catch(_){}}
function ensureLock(section){
  if(IS_ADMIN){clearDeadline(section);return;}
  const enabled=(section==="presets")?PRESETS_LOCK:TTS_LOCK;
  const secs=(section==="presets")?PRESETS_SECS:TTS_SECS;
  if(!enabled)return;
  let dl=getDeadline(section);
  if(!dl){setDeadline(section,nowSec()+secs);dl=getDeadline(section);}
  const url=section==="presets"?"{{ url_for('locked_page') }}":"{{ url_for('locked_tts_page') }}";
  const tick=()=>{const d=getDeadline(section);if(d&&nowSec()>=d)window.location.replace(url);};
  tick();setInterval(tick,1000);
  ["click","touchstart","mousemove","keydown"].forEach(ev=>window.addEventListener(ev,()=>{if(!IS_ADMIN)setDeadline(section,nowSec()+secs);},{passive:true}));
}
function toggleNav(){
  const btn=document.getElementById('hambBtn');
  const drawer=document.getElementById('navDrawer');
  if(btn&&drawer){btn.classList.toggle('open');drawer.classList.toggle('open');}
}
function maybeShowAnnouncement(){
  fetch("{{ url_for('api_settings') }}",{cache:'no-store'}).then(r=>r.json()).then(s=>{
    if(!s.announcement_enabled||!s.announcement_text)return;
    // Aan de VERSIE gekoppeld: elke nieuwe versie (fix/update) toont de changelog
    // opnieuw mét confetti. (Voorheen aan announcement_id, dat bleef gelijk.)
    const key='omroep_ann_seen_'+(s.version||s.announcement_id||1);
    try{if(localStorage.getItem(key))return;} catch(_){}
    document.getElementById('modalText').innerHTML=renderMarkdown(s.announcement_text);
    document.getElementById('mb').style.display='flex';
    try{localStorage.setItem(key,'1');}catch(_){}
    if(window._confetti)_confetti.start();   // nieuwe versie → subtiele confetti
  }).catch(()=>{});
}
function openChangelog(){
  fetch("{{ url_for('api_settings') }}",{cache:'no-store'}).then(r=>r.json()).then(s=>{
    var txt=s.announcement_text||'_Nog geen changelog beschikbaar._';
    document.getElementById('modalText').innerHTML=renderMarkdown(txt);
    document.getElementById('mb').style.display='flex';
  }).catch(()=>{});
}
window.addEventListener('load',maybeShowAnnouncement);

// ── Inactiviteit → terug naar de Muziek-pagina (per gebruiker aan/uit) ──
// Reset bij elke interactie, dus tijdens gebruik gebeurt er niets. Alleen actief
// als de gebruiker het aan heeft én we niet al op de Muziek-pagina zijn.
(function(){
  var ON={{ 'true' if idle_redirect else 'false' }};
  var SECS={{ idle_redirect_secs|int }};
  var ONMUSIC={{ 'true' if tab=='vol' else 'false' }};
  if(!ON || ONMUSIC || SECS<10) return;
  var url="{{ url_for('volume_page') }}";
  var t=null, last=0;
  function reset(){
    var now=Date.now();
    if(now-last<400) return;      // lichte throttle voor mousemove
    last=now;
    if(t) clearTimeout(t);
    t=setTimeout(function(){ window.location.href=url; }, SECS*1000);
  }
  ['click','touchstart','pointerdown','keydown','scroll','mousemove'].forEach(function(ev){
    window.addEventListener(ev, reset, {passive:true});
  });
  reset();
})();
</script>
"""

LOGIN_TPL = BASE_CSS + """
{{ branding_style }}
<style>
/* ── inlogpagina (plus.nl-look, thema-afhankelijk) ── */
body{background:#fff!important}
.plus-login{min-height:100vh;width:100%;color:#333;font-family:var(--font);display:flex;flex-direction:column}
.plus-login-header{display:flex;align-items:center;justify-content:center;padding:27px 40px;background:var(--red);box-shadow:2px 1px 6px 0 rgba(51,51,51,.2);position:relative;z-index:6}
.plus-login-header img{height:26px;width:auto;display:block}
.plus-login-wrap{flex:1;margin:auto;width:100%;max-width:570px;padding:32px 16px 90px}
.plus-login-title{color:#333;font-size:22px;font-weight:bold;line-height:30px;margin:0 0 8px}
.plus-login-desc{color:#333;font-size:16px;line-height:24px;margin:0 0 24px}
.plus-field{position:relative;margin-bottom:24px}
.plus-field input{width:100%;height:56px;padding:22px 44px 6px 14px;border:1px solid #999;border-radius:8px;font-size:16px;font-family:var(--font);color:#333;background:#fff;outline:none;transition:border-color .12s,border-width .12s}
.plus-field input:hover{border:2px solid rgba(0,0,0,.87)}
.plus-field input:focus{border:1px solid #333}
.plus-field label{position:absolute;left:11px;top:18px;color:#999;font-size:16px;line-height:1;pointer-events:none;background:#fff;padding:0 4px;transition:top .12s ease,font-size .12s ease,color .12s ease}
.plus-field input:focus ~ label,
.plus-field input:not(:placeholder-shown) ~ label{top:-8px;font-size:12px}
.plus-field input:focus ~ label{color:var(--green-dark)}
.plus-eye{position:absolute;right:8px;top:7px;width:42px;height:42px;border:none;background:none;cursor:pointer;color:#6c6c6c;display:flex;align-items:center;justify-content:center;border-radius:50%;padding:0}
.plus-eye:hover{background:rgba(0,0,0,.06)}
.plus-eye svg{width:24px;height:24px;fill:currentColor}
.plus-btn-primary{display:flex;align-items:center;justify-content:center;width:100%;height:48px;background:var(--red);color:var(--on-primary);border:none;border-radius:var(--btn-radius);font-family:var(--font);font-size:16px;font-weight:400;line-height:20px;cursor:pointer;transition:background .18s}
.plus-btn-primary:hover{background:var(--red-dark)}
#socialButtons{margin-top:20px;display:flex;flex-direction:column;gap:12px}
.plus-btn-sso{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;padding:12px 16px;background:#fff;color:var(--green-dark);border:1px solid var(--green-dark);border-radius:var(--btn-radius);font-family:var(--font);font-size:16px;font-weight:600;text-decoration:none;cursor:pointer;transition:background .15s}
.plus-btn-sso:hover{background:var(--gold-dim)}
.plus-btn-sso svg{width:20px;height:20px;fill:currentColor;flex-shrink:0}
.plus-secure{display:flex;align-items:flex-start;gap:6px;color:#999;font-size:14px;line-height:16px;margin-top:44px}
.plus-secure svg{width:16px;height:16px;fill:#999;flex-shrink:0;margin-top:-1px}
.plus-login .alert{margin-bottom:20px}
@media(max-width:400px){
  .plus-login-header{padding:15px 16px}
  .plus-login-wrap{padding:16px 16px 60px}
}
</style>

<div class="plus-login">
  <header class="plus-login-header">
    <img src="{{ logo }}" alt="{{ brand.name }}">
  </header>
  <div class="plus-login-wrap">
    <div class="plus-login-content">

      <p class="plus-login-title">Inloggen</p>
      <p class="plus-login-desc">Meld je aan om verder te gaan naar het {{ brand.name }}&nbsp;omroepsysteem.</p>

      {% if error %}<div class="alert alert-err">{{ error }}</div>{% endif %}
      {% if warn  %}<div class="alert alert-warn">{{ warn }}</div>{% endif %}

      <form method="post" action="{{ url_for('login_post') }}" autocomplete="on">
        <div class="plus-field">
          <input id="username" name="username" type="text" autocomplete="username"
                 value="{{ prefill }}" placeholder=" " required autofocus>
          <label for="username">Gebruikersnaam</label>
        </div>

        <div class="plus-field">
          <input id="password" name="password" type="password"
                 autocomplete="current-password" placeholder=" " required>
          <label for="password">Wachtwoord</label>
          <button type="button" class="plus-eye" id="pwToggle" title="Wachtwoord tonen"
                  aria-label="Wachtwoord tonen" onclick="togglePw()">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"/></svg>
          </button>
        </div>

        <button type="submit" class="plus-btn-primary">Inloggen</button>
      </form>

      {% if oidc_providers %}
      <div id="socialButtons">
        {% for p in oidc_providers %}
        <a class="plus-btn-sso" href="{{ url_for('sso_popup_start') }}" onclick="return ssoLogin(event,this.href)">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7A2,2 0 0,1 14,9A2,2 0 0,1 12,11A2,2 0 0,1 10,9A2,2 0 0,1 12,7M12,12.5C13.5,12.5 15,13.16 15,14.5V15.25C15,15.66 14.66,16 14.25,16H9.75C9.34,16 9,15.66 9,15.25V14.5C9,13.16 10.5,12.5 12,12.5Z"/></svg>
          Inloggen met {{ p.name }}
        </a>
        {% endfor %}
      </div>
      {% endif %}

      <p class="plus-secure parent_secure_place">
        <svg viewBox="0 0 16 16" aria-hidden="true"><g fill-rule="evenodd"><path d="M12.67 7.333H2.997c-.915 0-1.663.612-1.663 1.362v5.943c0 .75.748 1.362 1.663 1.362h9.675c.915 0 1.662-.612 1.662-1.362V8.695c0-.75-.747-1.362-1.662-1.362zm-9.593.8h9.513c.408 0 .743.275.743.61v5.848c0 .334-.335.609-.743.609H3.077c-.408 0-.744-.275-.744-.61V8.744c0-.335.336-.61.744-.61z" fill-rule="nonzero"/><path d="M7.74.633c2.914 0 4.536 2.219 4.862 6.428l.017.24-.998.065c-.253-3.902-1.546-5.733-3.882-5.733-2.275 0-3.457 1.741-3.545 5.475l-.004.231-1-.011C3.24 2.954 4.755.633 7.74.633z" fill-rule="nonzero"/><path d="M8 9.333a1.333 1.333 0 0 1 .645 2.501.622.622 0 0 1 .022.166v1.333a.667.667 0 1 1-1.334 0V12c0-.058.008-.114.022-.168A1.333 1.333 0 0 1 8 9.333z"/></g></svg>
        Je bevindt je binnen een beveiligde omgeving
      </p>

    </div>
  </div>
</div>

{% if oidc_providers %}
<div id="loginNotice" style="position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(17,40,20,.55);z-index:9999;padding:20px">
  <div style="width:min(430px,94vw);background:#fff;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.30);padding:26px 24px;border-top:5px solid var(--red)">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
      <span class="material-symbols-outlined" style="font-size:30px;color:var(--red)">info</span>
      <div style="font-weight:800;font-size:18px;color:var(--green-dark)">Let op</div>
    </div>
    <p style="color:var(--fg2);line-height:1.55;margin:0 0 10px">De meeste gebruikers loggen in met <strong>SSO</strong>. Deze inlogmethode (gebruikersnaam &amp; wachtwoord) is bedoeld voor <strong>lokale accounts</strong>.</p>
    <p style="color:var(--fg2);line-height:1.55;margin:0 0 20px">Weet je niet zeker welke je moet kiezen? Vraag dit na bij de&nbsp;winkelondernemer.</p>
    <button type="button" onclick="document.getElementById('loginNotice').style.display='none'"
            style="display:block;width:100%;height:48px;background:var(--red);color:#fff;border:none;border-radius:24px 24px 24px 4px;font-weight:700;font-size:15px;cursor:pointer">Begrepen</button>
  </div>
</div>
<script>
(function(){
  var u=document.getElementById('username'); if(!u) return;
  var shown=false;
  u.addEventListener('input',function(){
    if(!shown && (u.value||'').length>=1){ shown=true; document.getElementById('loginNotice').style.display='flex'; }
  });
})();
</script>
{% endif %}

<script>
function togglePw(){
  var i=document.getElementById('password'), b=document.getElementById('pwToggle');
  if(!i)return;
  var show=i.type==='password';
  i.type=show?'text':'password';
  b.setAttribute('aria-label', show?'Wachtwoord verbergen':'Wachtwoord tonen');
  b.title=show?'Wachtwoord verbergen':'Wachtwoord tonen';
}
</script>

<script>
/**
 * SSO-login: navigeert het hele browservenster (window.top) naar de
 * SSO-URL, in plaats van een popup te proberen.
 *
 * Waarom geen popup: iOS Safari blokkeert window.open() structureel
 * vanuit content dat in een cross-origin iframe draait (HA), ook als
 * het synchroon in een click-handler gebeurt — dit geldt niet alleen
 * voor Safari maar inmiddels ook voor Chrome op iOS, dat dezelfde
 * WebKit-restricties gebruikt. Een top-level redirect werkt overal.
 */
function ssoLogin(evt, url) {
  var inIframe = false;
  try { inIframe = window !== window.top; } catch (e) { inIframe = true; }

  if (evt && evt.preventDefault) evt.preventDefault();

  if (inIframe) {
    // Navigeer het volledige browservenster, niet alleen het iframe.
    try {
      window.top.location.href = url;
    } catch (e) {
      // Cross-origin frame-toegang geweigerd — laatste redmiddel.
      window.location.href = url;
    }
  } else {
    window.location.href = url;
  }
  return false;
}
</script>
"""

NO_ACCESS_BODY = """
<h1>Geen toegang</h1>
<div class="card-item" style="max-width:520px">
  <p style="margin-bottom:14px;color:var(--fg2)">
    Je bent ingelogd als <strong>{{ dn }}</strong>, maar je account heeft
    (nog) geen rechten om pagina's in dit omroepsysteem te gebruiken.
  </p>
  <p class="help" style="margin-bottom:18px">
    Vraag een beheerder om jouw account rechten te geven via
    <em>Gebruikers &rarr; Bewerken</em>, of om je aan de juiste
    SSO-groep toe te voegen (bijv. <span class="mono">radio-operator</span>).
  </p>
  <a class="btn btn-inline" href="{{ url_for('logout') }}"><span class="mi">logout</span> Uitloggen</a>
</div>
"""

SSO_DONE_TPL = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Inloggen geslaagd</title>
<style>
  body{font-family:"Open Sans",sans-serif;display:flex;align-items:center;justify-content:center;
       min-height:100vh;margin:0;background:#eef1ea;color:#333;}
  .box{text-align:center;padding:40px;}
  .box h2{color:#115013;}
  .icon{font-size:48px;margin-bottom:16px;}
  p{color:#6c6c6c;font-size:14px;}
</style>
</head>
<body>
<div class="box">
  <div class="icon"><span class="material-symbols-outlined" style="font-size:48px;color:#80bd1d">check_circle</span></div>
  <h2>Inloggen geslaagd</h2>
  <p>Dit venster sluit automatisch…</p>
</div>
<script>
// Probeer de popup te sluiten en het bovenliggende venster te herladen
var dest = {{ dest|tojson }};
try {
  if (window.opener) {
    // We zijn een popup: sluit ons zelf
    window.opener.location.reload();
    window.close();
  } else {
    // Directe navigatie (niet via popup)
    window.location.href = dest;
  }
} catch(e) {
  window.location.href = dest;
}
// Fallback: na 2 seconden toch navigeren als sluiten niet lukt
setTimeout(function(){ window.location.href = dest; }, 2000);
</script>
{% if sip_alert %}
<div id="sipLiveOverlay" style="display:none;position:fixed;inset:0;z-index:2147483000;background:rgba(0,0,0,.58);align-items:center;justify-content:center;padding:20px">
  <div style="background:#fff;border-radius:20px;max-width:440px;width:100%;padding:30px 26px;text-align:center;box-shadow:0 24px 70px rgba(0,0,0,.45);border-top:7px solid #c62828">
    <div style="width:70px;height:70px;border-radius:50%;background:#fdecea;display:flex;align-items:center;justify-content:center;margin:0 auto 16px">
      <span class="mi" style="font-size:38px;color:#c62828;animation:sipLivePulse 1s infinite">campaign</span>
    </div>
    <div style="font-size:13px;letter-spacing:.09em;color:#c62828;font-weight:800">&#9679; LIVE OMROEP BEZIG</div>
    <div style="font-size:23px;font-weight:800;margin:6px 0 2px;color:#1a1a1a">Toestel <span id="sipLiveExt">&mdash;</span></div>
    <div id="sipLiveSince" style="margin:0 0 20px;color:#666;font-size:14px">roept nu om over de speakers</div>
    <button type="button" id="sipLiveStopBtn" onclick="sipLiveStop(this)" style="width:100%;padding:16px;border:0;border-radius:13px;background:#c62828;color:#fff;font-size:17px;font-weight:800;cursor:pointer"><span class="mi" style="vertical-align:middle">stop_circle</span> Omroep stoppen</button>
    <div id="sipLiveMsg" style="margin-top:11px;font-size:13px;color:#c62828;display:none"></div>
  </div>
</div>
<style>@keyframes sipLivePulse{0%,100%{opacity:1}50%{opacity:.3}}</style>
<script>
(function(){
  var ov=document.getElementById('sipLiveOverlay');
  function fmt(s){ s=Math.max(0,Math.floor(s)); var m=Math.floor(s/60), ss=s%60; return m+':'+(ss<10?'0':'')+ss; }
  window.sipLiveStop=function(btn){
    btn.disabled=true;
    var m=document.getElementById('sipLiveMsg'); m.style.display='block'; m.textContent='Stoppen\\u2026';
    fetch('/api/sip/hangup',{method:'POST'}).then(function(r){return r.json();}).then(function(j){
      m.textContent=j.ok?'Gestopt.':(j.error||'Kon niet stoppen'); setTimeout(function(){btn.disabled=false;},1500);
    }).catch(function(){ m.textContent='Kon niet stoppen'; btn.disabled=false; });
  };
  function poll(){
    fetch('/api/sip/live',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
      if(j && j.in_call){
        document.getElementById('sipLiveExt').textContent=j.caller_ext||'?';
        document.getElementById('sipLiveSince').textContent='roept nu om over de speakers'+(j.since_secs?(' \\u00b7 '+fmt(j.since_secs)):'');
        ov.style.display='flex';
      } else {
        ov.style.display='none';
        var m=document.getElementById('sipLiveMsg'); if(m){ m.style.display='none'; }
        var b=document.getElementById('sipLiveStopBtn'); if(b){ b.disabled=false; }
      }
    }).catch(function(){});
  }
  poll(); setInterval(poll, 2000);
})();
</script>
{% endif %}
</body>
</html>"""

VOLUME_BODY = """
<style>
.subtab-brand{display:inline-flex;width:22px;height:22px;border-radius:6px;background:#fff;align-items:center;justify-content:center;padding:2px;vertical-align:-6px;box-shadow:0 1px 2px rgba(0,0,0,.15)}
.subtab-brand img{width:100%;height:100%;object-fit:contain;display:block}
/* Spotify-tab: het volledige woordmerk op een net wit pilletje (i.p.v. het kleine vierkantje) */
.subtab-brand.subtab-spotify{width:auto;height:26px;border-radius:999px;padding:4px 11px;box-shadow:0 1px 3px rgba(0,0,0,.18)}
.subtab-brand.subtab-spotify img{width:auto;height:16px;object-fit:contain}
.vol-card{border:1px solid var(--stroke);border-radius:16px;background:#fff;box-shadow:var(--shadow-sm);padding:clamp(18px,3vw,28px);max-width:560px}
.vol-head{display:flex;align-items:center;gap:14px;margin-bottom:22px}
.vol-numwrap{display:flex;align-items:center;gap:14px;flex-shrink:0;min-width:0}
.vol-ic{font-family:'Material Symbols Outlined';font-size:44px;color:var(--red);line-height:1;font-variation-settings:'wght' 500}
/* min-width houdt de breedte constant of het nu 8%, 68% of 100% is → geen versprong */
.vol-big{font-size:46px;font-weight:800;color:var(--green-dark);line-height:1;font-variant-numeric:tabular-nums;min-width:3.3ch;text-align:left}
.vol-chips{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto;justify-content:flex-end}
.vol-chip{display:inline-flex;align-items:center;gap:4px;padding:5px 11px;border-radius:999px;border:1px solid var(--stroke);background:#f4f6f1;font-size:12px;font-weight:600;color:var(--fg2);white-space:nowrap;transition:background .15s,border-color .15s,color .15s}
.vol-chip.on{background:#eaf4d8;border-color:#cbe3a0;color:#4b7a12}
.vol-chip.play{background:#fff1d6;border-color:#f2d98a;color:#a5730a}
/* Geanimeerde schuifbalk: grijze baan + groene fill die soepel meebeweegt. */
.vslider{position:relative;height:16px;border-radius:999px;background:#e4e7df;margin-bottom:22px}
.vslider-fill{position:absolute;left:0;top:0;height:100%;width:0;border-radius:999px;background:var(--red);pointer-events:none;transition:width .22s cubic-bezier(.22,1,.36,1)}
.vslider.dragging .vslider-fill{transition:none}
.vol-slider{position:absolute;inset:0;-webkit-appearance:none;appearance:none;width:100%;height:100%;margin:0;background:transparent;outline:none;cursor:pointer}
.vol-slider::-webkit-slider-thumb{-webkit-appearance:none;width:32px;height:32px;border-radius:50%;background:#fff;border:3px solid var(--red);box-shadow:0 2px 8px rgba(0,0,0,.28);cursor:pointer;transition:transform .12s ease}
.vol-slider:active::-webkit-slider-thumb{transform:scale(1.14)}
.vol-slider::-moz-range-thumb{width:28px;height:28px;border-radius:50%;background:#fff;border:3px solid var(--red);box-shadow:0 2px 8px rgba(0,0,0,.28);cursor:pointer}
.vol-controls{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
@media(max-width:560px){
  .vol-ic{font-size:34px}
  .vol-big{font-size:34px;min-width:3ch}
  .vol-chip{font-size:11px;padding:4px 9px}
  .vol-head{gap:10px}
}
.vol-controls .btn{width:auto;flex:1 1 120px}
.vol-controls .vol-step{flex:0 0 58px;font-size:22px;font-weight:800;padding:0}
/* Bredere schermen: de volume-inhoud in een gecentreerde kolom i.p.v. links */
@media(min-width:760px){ .vol-wrap{max-width:560px;margin-left:auto;margin-right:auto} }
.hist-more{margin-top:8px;width:100%;padding:8px;border-radius:10px;border:1px solid var(--stroke);background:#f4f6f1;color:var(--green-dark);font-weight:600;font-size:12px;cursor:pointer}
.hist-more:hover{background:#eaf4d8}
</style>

<div class="vol-wrap">
{% set omroep_active = vr.omroep.view %}
<div class="subtabs" id="volTabs">
  {% if vr.omroep.view %}<button type="button" class="subtab active" data-tab="omroep" onclick="volTab('omroep')"><span class="pr-lockup">{{ plus_wordmark|safe }}<span class="pr-radio">RADIO</span></span></button>{% endif %}
  {% if vr.spotify.view %}<button type="button" class="subtab {{ '' if omroep_active else 'active' }}" data-tab="spotify" onclick="volTab('spotify')"><span class="subtab-brand subtab-spotify"><img src="{{ spotify_logo }}" alt="Spotify"></span></button>{% endif %}
  {% if vr.omroep.view or vr.spotify.view %}<button type="button" class="subtab" data-tab="eqviz" onclick="volTab('eqviz')"><span class="mi">graphic_eq</span> EQ &amp; Visualizer</button>{% endif %}
</div>

{% if vr.omroep.view %}
<div class="subpanel active" data-panel="omroep">
  <div class="vol-card">
    <div class="vol-head">
      <div class="vol-numwrap">
        <span class="vol-ic">campaign</span>
        <div class="vol-big" id="volBadge">--%</div>
      </div>
      <div class="vol-chips">
        <span class="vol-chip" id="muteBadge">--</span>
        <span class="vol-chip" id="rcaBadge">RCA: …</span>
        <span class="vol-chip play" id="playBadge" style="display:none"><span class="mi mi-sm">graphic_eq</span> Bezig</span>
      </div>
    </div>
    {% if vr.omroep.volume %}<div class="vslider"><div class="vslider-fill"></div><input id="volSlider" class="vol-slider" type="range" min="{{ vr.omroep.vmin }}" max="{{ vr.omroep.vmax }}"></div>{% endif %}
    <div class="vol-controls">
      {% if vr.omroep.volume %}<button class="btn vol-step" title="Zachter" onclick="step(-1)">−</button>
      <button class="btn vol-step" title="Harder" onclick="step(1)">+</button>{% endif %}
      {% if vr.omroep.mute %}<button class="btn" id="muteBtn" onclick="muteToggle()"><span class="mi">volume_off</span> Mute</button>{% endif %}
      {% if vr.omroep.rca %}<button class="btn" onclick="rcaToggle()"><span class="mi">cable</span> {{ brand.radio_name }} aan/uit</button>{% endif %}
    </div>
  </div>
  {% if vr.omroep.channel %}
  <style>
  .pr-chan{max-width:560px;margin-top:12px;display:flex;gap:8px}
  .pr-chan button{flex:1;padding:11px 12px;border-radius:12px;border:1px solid var(--stroke);background:#fff;color:var(--green-dark);font-weight:700;font-size:14px;cursor:pointer;min-height:44px}
  .pr-chan button.on{background:var(--red);border-color:var(--red);color:#fff}
  .pr-chan button:active{transform:scale(.97)}
  </style>
  <div class="pr-chan" id="prChan">
    <button data-ch="1" onclick="prSetChan(1)"><span class="mi mi-sm">radio</span> Plus Main</button>
    <button data-ch="2" onclick="prSetChan(2)"><span class="mi mi-sm">radio</span> Plus Easy</button>
  </div>
  <div id="chanConfirm" class="modal-backdrop" onclick="if(event.target===this)chanCancel()">
    <div class="modal" style="max-width:430px;text-align:center;border-top:6px solid var(--red)">
      <div style="font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--fg3);margin-bottom:10px">Kanaal wisselen</div>
      <span class="mi" style="font-size:58px;color:var(--red)">radio</span>
      <div style="font-size:22px;font-weight:800;color:var(--green-dark);margin:4px 0 10px" id="chanName">Plus Easy</div>
      <div class="help" style="margin-bottom:20px">De radio faadt de muziek uit en laadt <b id="chanName2">Plus Easy</b> in. Dit kan tot ongeveer <b>30 seconden</b> duren. Na het inladen faadt de muziek weer in.</div>
      <button class="btn btn-primary" onclick="chanConfirm()" style="min-height:52px;font-weight:800"><span class="mi">radio</span> Ja, wisselen</button>
      <div style="height:8px"></div>
      <button class="btn" onclick="chanCancel()"><span class="mi">close</span> Annuleren</button>
    </div>
  </div>
  {% endif %}
  {% if vr.omroep.nowplaying %}
  <style>
  .pr-now{max-width:560px;margin-top:16px;background:#fff;border:1px solid var(--stroke);border-radius:16px;box-shadow:var(--shadow-sm);padding:clamp(16px,2.6vw,22px)}
  .hist-more{margin-top:8px;width:100%;padding:8px;border-radius:10px;border:1px solid var(--stroke);background:#f4f6f1;color:var(--green-dark);font-weight:600;font-size:12px;cursor:pointer}
  .hist-more:hover{background:#eaf4d8}
  .pr-viz{display:block;width:100%;height:64px;border-radius:12px;background:radial-gradient(120% 140% at 50% 100%,#161a15 0%,#0a0c09 100%);margin-bottom:14px;box-shadow:inset 0 1px 3px rgba(0,0,0,.5)}
  .pr-now-head{display:flex;align-items:center;gap:10px;margin-bottom:10px}
  .pr-now-head img{width:22px;height:22px;border-radius:6px;background:#fff;padding:2px;box-shadow:0 1px 2px rgba(0,0,0,.15)}
  .pr-now-head .lbl{font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--fg3)}
  .pr-title{font-weight:800;color:var(--green-dark);font-size:19px;line-height:1.25;word-break:break-word}
  .pr-eq{display:inline-flex;gap:2px;align-items:flex-end;height:14px;margin-right:8px;vertical-align:-2px}
  .pr-eq i{width:3px;height:100%;background:var(--red);border-radius:2px;animation:preq .9s ease-in-out infinite}
  .pr-eq i:nth-child(2){animation-delay:.25s}.pr-eq i:nth-child(3){animation-delay:.5s}
  @keyframes preq{0%,100%{transform:scaleY(.35)}50%{transform:scaleY(1)}}
  .pr-now.pr-empty .pr-eq{visibility:hidden}
  /* Shazam-verrijking: albumcover + artiest */
  .pr-meta{display:flex;align-items:center;gap:12px;margin-top:12px}
  .pr-cover{width:56px;height:56px;border-radius:10px;object-fit:cover;box-shadow:0 2px 8px rgba(0,0,0,.18);flex:0 0 auto}
  .pr-artist{color:var(--fg2);font-size:15px;font-weight:600;line-height:1.3}
  .pr-artist .alb{color:var(--fg3);font-size:12px;font-weight:500;display:block;margin-top:1px}
  .pr-hist-row .tw{display:flex;align-items:center;gap:8px;min-width:0;flex:1 1 auto}
  .pr-hist-row .tt{display:flex;flex-direction:column;min-width:0}
  .pr-hist-row .ar{color:#7a8a6f;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .pr-hist-row .cov{width:30px;height:30px;border-radius:6px;object-fit:cover;flex:0 0 auto;box-shadow:0 1px 3px rgba(0,0,0,.15)}
  .pr-hist{margin-top:14px;border-top:1px solid var(--stroke-light);padding-top:10px}
  .pr-hist-head{font-size:12px;font-weight:700;color:var(--fg3);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
  .pr-hist-row{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-top:1px solid var(--stroke-light)}
  .pr-hist-row:first-child{border-top:none}
  .pr-hist-row .t{color:var(--green-dark);font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .pr-hist-row .a{color:#7a8a6f;font-size:11px;flex:0 0 auto;white-space:nowrap}
  </style>
  <div class="pr-now pr-empty" id="prNow">
    <canvas class="pr-viz" id="prViz"></canvas>
    <div class="pr-now-head"><span class="lbl">Nu op</span> <span class="pr-lockup" style="color:var(--green-dark)">{{ plus_wordmark|safe }}<span class="pr-radio">RADIO</span></span></div>
    <div class="pr-title"><span class="pr-eq"><i></i><i></i><i></i></span><span id="prTitle">—</span></div>
    <div class="pr-meta" id="prMeta" style="display:none">
      <img class="pr-cover" id="prCover" alt="" style="display:none">
      <div class="pr-artist" id="prArtist"></div>
    </div>
    <div class="pr-hist" id="prHistWrap" style="display:none">
      <div class="pr-hist-head">Afgespeelde nummers</div>
      <div id="prHistList"></div>
    </div>
  </div>
  {% endif %}
</div>
{% endif %}

{% if vr.spotify.view %}
<div class="subpanel {{ '' if omroep_active else 'active' }}" data-panel="spotify">
  <style>
  .sp-player{display:flex;flex-direction:column;gap:14px;align-items:stretch;background:#fff;border:1px solid var(--stroke);border-radius:16px;padding:clamp(16px,2.6vw,24px);box-shadow:var(--shadow-sm);max-width:560px;margin-top:20px;margin-bottom:16px}
  .sp-main{display:flex;gap:16px;align-items:center}
  .sp-cover{position:relative;width:clamp(64px,14vw,84px);height:clamp(64px,14vw,84px);flex:0 0 auto;border-radius:12px;overflow:hidden;background:#eef2e6}
  .sp-cover img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:none}
  .sp-cover .sp-ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:34px;color:#9bbf6a}
  .sp-info{flex:1;min-width:0}
  .sp-title{font-weight:800;color:var(--green-dark);font-size:16px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-artist{color:#5b6b52;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}
  .sp-progress{margin-top:10px}
  .sp-bar{height:6px;border-radius:6px;background:#e7ecdd;overflow:hidden}
  .sp-fill{height:100%;width:0;background:linear-gradient(90deg,#80bd1d,#5a9216);border-radius:6px;transition:width .5s linear}
  .sp-times{display:flex;justify-content:space-between;font-size:11px;color:#7a8a6f;margin-top:4px;font-variant-numeric:tabular-nums}
  .sp-status{display:flex;align-items:center;gap:8px;margin-top:6px;font-size:12px;color:#7a8a6f}
  .sp-caster{display:none;align-items:center;gap:5px;color:#5b6b52;font-size:12px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-caster.on{display:flex}
  .sp-caster .mi{font-size:15px;color:#80bd1d;flex:0 0 auto}
  .sp-eq{display:inline-flex;gap:2px;align-items:flex-end;height:12px}
  .sp-eq i{width:3px;height:100%;background:#80bd1d;border-radius:2px;transform-origin:bottom;animation:speq .9s ease-in-out infinite}
  .sp-eq i:nth-child(2){animation-delay:.25s}
  .sp-eq i:nth-child(3){animation-delay:.5s}
  @keyframes speq{0%,100%{transform:scaleY(.35)}50%{transform:scaleY(1)}}
  .sp-player[data-state="empty"] .sp-progress,.sp-player[data-state="empty"] .sp-eq{visibility:hidden}
  .sp-player:not([data-state="playing"]) .sp-eq i{animation-play-state:paused;opacity:.4}
  /* Transportknoppen + seek — alleen zichtbaar in go-librespot-modus (data-control=1) */
  .sp-barwrap{padding:7px 0;cursor:default}
  .sp-knob{position:absolute;top:50%;left:0;width:14px;height:14px;border-radius:50%;background:#fff;border:2px solid #5a9216;box-shadow:0 1px 4px rgba(0,0,0,.3);transform:translate(-50%,-50%);opacity:0;transition:opacity .15s}
  .sp-bar{position:relative}
  .sp-controls{display:none;justify-content:center;align-items:center;gap:20px}
  .sp-player[data-control="1"] .sp-controls{display:flex}
  .sp-player[data-control="1"][data-state="empty"] .sp-controls{opacity:.4;pointer-events:none}
  .sp-player[data-control="1"] .sp-barwrap{cursor:pointer}
  .sp-player[data-control="1"] .sp-barwrap:hover .sp-knob,.sp-barwrap.sp-seeking .sp-knob{opacity:1}
  .sp-btn{width:44px;height:44px;border-radius:50%;border:1px solid var(--stroke);background:#fff;color:var(--green-dark);display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:var(--shadow-sm);padding:0}
  .sp-btn .mi{font-size:24px}
  .sp-btn.sp-play{width:56px;height:56px;background:#80bd1d;border-color:#5a9216;color:#fff}
  .sp-btn.sp-play .mi{font-size:30px}
  .sp-btn:active{transform:scale(.93)}
  .sp-player[data-control="1"] .sp-fill{transition:none}
  /* Explicit-waarschuwing boven de player */
  .sp-explicit{display:none;align-items:center;gap:10px;background:#fdecec;border:1px solid #f3b6b6;color:#a01818;border-radius:14px;padding:12px 16px;margin-top:20px;margin-bottom:14px;font-weight:600;font-size:14px;max-width:560px}
  .sp-explicit.on{display:flex;animation:spexpuls 1.4s ease-in-out infinite}
  .sp-explicit .mi{font-size:24px;color:#c62828;flex:0 0 auto}
  @keyframes spexpuls{0%,100%{border-color:#f3b6b6}50%{border-color:#d33}}
  .vol-card.sp-locked{opacity:.5;pointer-events:none}
  .sp-jam{display:none;align-items:center;justify-content:center;gap:8px;margin-top:14px;padding:12px 18px;border-radius:999px;background:#1db954;color:#fff;font-weight:800;font-size:15px;text-decoration:none;border:none;cursor:pointer;box-shadow:var(--shadow-sm);width:100%}
  .sp-jam.on{display:flex}
  .sp-jam:active{transform:scale(.97)}
  .sp-jam .mi{font-size:22px}
  .sp-jambox{display:none;flex-direction:column;align-items:center;gap:12px;margin-top:12px;padding:18px;border:1px solid var(--stroke);border-radius:16px;background:#fafdf6}
  .sp-jambox.on{display:flex}
  .sp-jambox .jam-cap{font-size:13px;color:#5b6b52;text-align:center;font-weight:600;line-height:1.4}
  .sp-jambox img{width:min(280px,80%);height:auto;border-radius:10px;display:block}
  .sp-jam-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
  .sp-jam-actions a,.sp-jam-actions button{display:inline-flex;align-items:center;gap:6px;padding:10px 16px;border-radius:999px;border:1px solid var(--stroke);background:#fff;color:var(--green-dark);font-weight:700;font-size:13px;text-decoration:none;cursor:pointer}
  .sp-jam-actions .mi{font-size:18px}
  </style>
  <style>
  /* ===== V7: Spotify-tab in app-stijl (donker, album-art) ===== */
  [data-panel="spotify"]{--spg:#1ed760;--spg2:#1db954}
  [data-panel="spotify"] .sp-brandbar{max-width:560px;display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin:20px 0 12px}
  [data-panel="spotify"] .sp-brandbar img{height:38px;width:auto;display:block;filter:drop-shadow(0 2px 7px rgba(0,0,0,.22))}
  [data-panel="spotify"] .sp-brandbar .sp-tag{font-size:12px;color:#6b7a60;font-weight:700;text-align:right;line-height:1.35}
  [data-panel="spotify"] .sp-brandbar .sp-tag b{color:var(--green-dark);font-size:13px}
  /* player → donkere hero met vervaagde albumhoes op de achtergrond */
  [data-panel="spotify"] .sp-player{position:relative;overflow:hidden;background:linear-gradient(165deg,#3a3a40,#161616 72%);border:1px solid rgba(255,255,255,.08);color:#fff;box-shadow:0 16px 40px rgba(0,0,0,.34);margin-top:0;gap:18px}
  [data-panel="spotify"] .sp-viz{display:block;width:100%;height:52px;position:relative;z-index:1;margin-bottom:2px}
  [data-panel="spotify"] .sp-backdrop{position:absolute;inset:-10%;background-size:cover;background-position:center;filter:blur(42px) saturate(1.6) brightness(.6);opacity:0;transition:opacity .7s ease;z-index:0}
  [data-panel="spotify"] .sp-player:not([data-state="empty"]) .sp-backdrop{opacity:.92}
  [data-panel="spotify"] .sp-player::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,10,10,.28),rgba(10,10,10,.72));z-index:0}
  [data-panel="spotify"] .sp-player>*{position:relative;z-index:1}
  [data-panel="spotify"] .sp-main{gap:18px}
  [data-panel="spotify"] .sp-cover{width:clamp(92px,22vw,124px);height:clamp(92px,22vw,124px);border-radius:10px;box-shadow:0 10px 26px rgba(0,0,0,.55);background:#2a2a2a}
  [data-panel="spotify"] .sp-cover .sp-ph{color:#54545a}
  [data-panel="spotify"] .sp-title{color:#fff;font-size:clamp(18px,3vw,22px);font-weight:800;letter-spacing:-.02em}
  [data-panel="spotify"] .sp-artist{color:#dcdcdc;font-size:14px;margin-top:3px}
  [data-panel="spotify"] .sp-bar{height:6px;background:rgba(255,255,255,.26)}
  [data-panel="spotify"] .sp-fill{background:#fff;transition:width .5s linear}
  [data-panel="spotify"] .sp-player:hover .sp-fill{background:var(--spg)}
  [data-panel="spotify"] .sp-times{color:#e2e2e2;margin-top:6px}
  [data-panel="spotify"] .sp-status{color:#cecece;margin-top:8px}
  [data-panel="spotify"] .sp-eq i{background:var(--spg)}
  [data-panel="spotify"] .sp-caster{color:#e8e8e8}
  [data-panel="spotify"] .sp-caster .mi{color:var(--spg)}
  [data-panel="spotify"] .sp-comnext{display:none;align-items:center;gap:5px;margin-top:5px;font-size:11.5px;font-weight:600;color:#e6c766}
  [data-panel="spotify"] .sp-comnext.on{display:inline-flex}
  [data-panel="spotify"] .sp-comnext .mi{font-size:15px;color:#e6c766}
  [data-panel="spotify"] .sp-knob{background:#fff;border-color:var(--spg)}
  /* transport-knoppen: witte ronde play zoals Spotify */
  [data-panel="spotify"] .sp-controls{gap:24px}
  [data-panel="spotify"] .sp-btn{background:transparent;border:none;color:#d4d4d4;box-shadow:none;width:50px;height:50px}
  [data-panel="spotify"] .sp-btn:hover{color:#fff}
  [data-panel="spotify"] .sp-btn .mi{font-size:32px}
  [data-panel="spotify"] .sp-btn.sp-play{background:#fff;border:none;color:#000;width:62px;height:62px;box-shadow:0 8px 20px rgba(0,0,0,.45)}
  [data-panel="spotify"] .sp-btn.sp-play:hover{transform:scale(1.06);background:var(--spg);color:#000}
  [data-panel="spotify"] .sp-btn.sp-play .mi{font-size:36px}
  /* volume-kaart → compacte donkere strip */
  [data-panel="spotify"] .vol-card{max-width:560px;margin-top:14px;background:#181818;border:1px solid rgba(255,255,255,.08);color:#fff;box-shadow:0 8px 22px rgba(0,0,0,.24)}
  [data-panel="spotify"] .vol-card .vol-big,[data-panel="spotify"] .vol-card .vol-ic{color:#fff}
  [data-panel="spotify"] .vol-card .vol-chip{background:#2a2a2a;color:#d0d0d0;border-color:rgba(255,255,255,.12)}
  [data-panel="spotify"] .vol-card .btn{background:#2a2a2a;color:#fff;border-color:rgba(255,255,255,.14)}
  [data-panel="spotify"] .vol-card .btn:hover{background:#333;color:#fff}
  [data-panel="spotify"] .vol-card .btn-gold{background:var(--spg);border-color:var(--spg);color:#000}
  [data-panel="spotify"] .vol-card .vslider{background:rgba(255,255,255,.18)}
  [data-panel="spotify"] .vol-card .vslider-fill{background:var(--spg)}
  /* zoeken, wachtrij, geschiedenis → donkere kaarten */
  [data-panel="spotify"] .sp-search,[data-panel="spotify"] .sp-queue,[data-panel="spotify"] .sp-history{background:#181818;border:1px solid rgba(255,255,255,.08);color:#fff;box-shadow:0 8px 22px rgba(0,0,0,.24)}
  [data-panel="spotify"] .sp-search-head,[data-panel="spotify"] .sp-queue-head,[data-panel="spotify"] .sp-hist-head{color:#fff}
  [data-panel="spotify"] .sp-search-head .mi,[data-panel="spotify"] .sp-queue-head .mi,[data-panel="spotify"] .sp-hist-head .mi{color:var(--spg)}
  [data-panel="spotify"] .sp-search-box input{background:#2a2a2a;border-color:rgba(255,255,255,.14);color:#fff}
  [data-panel="spotify"] .sp-search-box input::placeholder{color:#8f8f8f}
  [data-panel="spotify"] .sp-search-box input:focus{border-color:var(--spg);outline:none}
  [data-panel="spotify"] .sp-search-box button{background:var(--spg);border-color:var(--spg);color:#000}
  [data-panel="spotify"] .sp-res-row{cursor:pointer;border-radius:8px;padding-left:8px;padding-right:8px;border-top-color:rgba(255,255,255,.07)}
  [data-panel="spotify"] .sp-res-row:hover{background:rgba(255,255,255,.06)}
  [data-panel="spotify"] .sp-queue-row,[data-panel="spotify"] .sp-hist-row{border-top-color:rgba(255,255,255,.07)}
  [data-panel="spotify"] .sp-res-title,[data-panel="spotify"] .sp-queue-title,[data-panel="spotify"] .sp-hist-title{color:#fff}
  [data-panel="spotify"] .sp-res-sub,[data-panel="spotify"] .sp-queue-sub,[data-panel="spotify"] .sp-hist-sub{color:#b3b3b3}
  [data-panel="spotify"] .sp-res-cover,[data-panel="spotify"] .sp-queue-cover,[data-panel="spotify"] .sp-hist-cover{background:#2a2a2a}
  [data-panel="spotify"] .sp-res-actions button{background:transparent;border-color:rgba(255,255,255,.2);color:#fff}
  [data-panel="spotify"] .sp-res-actions button.play{background:var(--spg);border-color:var(--spg);color:#000}
  [data-panel="spotify"] .sp-queue-tag{color:var(--spg)}
  [data-panel="spotify"] .sp-queue-row.nu .sp-queue-title{color:var(--spg)}
  [data-panel="spotify"] .sp-hist-meta{color:#9a9a9a}
  [data-panel="spotify"] .sp-hist-caster .mi{color:var(--spg)}
  [data-panel="spotify"] .hist-more{color:#e0e0e0;background:transparent;border-color:rgba(255,255,255,.16)}
  [data-panel="spotify"] .sp-webmsg{color:#d0d0d0}
  /* ── ALLE kaarten gelijk: zelfde kleur, rand, hoeken en tussenruimte ── */
  [data-panel="spotify"] .vol-card,
  [data-panel="spotify"] .sp-player,
  [data-panel="spotify"] .sp-search,
  [data-panel="spotify"] .sp-queue,
  [data-panel="spotify"] .sp-history{
    max-width:560px;width:100%;box-sizing:border-box;
    background:#181818;border:1px solid rgba(255,255,255,.08);border-radius:16px;
    margin:0 0 14px 0;box-shadow:0 8px 22px rgba(0,0,0,.26)}
  /* de speler houdt de vervaagde albumhoes, maar dezelfde basiskleur */
  [data-panel="spotify"] .sp-player{background:#181818}
  [data-panel="spotify"] .sp-player::after{background:linear-gradient(180deg,rgba(15,15,15,.35),rgba(15,15,15,.78))}
  [data-panel="spotify"] .sp-brandbar{margin:20px 0 14px}
  /* wachtrij-bediening */
  [data-panel="spotify"] .sp-queue-head{display:flex;align-items:center;gap:8px}
  [data-panel="spotify"] .sp-qbtn{display:inline-flex;align-items:center;gap:5px;background:#2a2a2a;border:1px solid rgba(255,255,255,.14);color:#fff;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:700;cursor:pointer}
  [data-panel="spotify"] .sp-qbtn:hover{background:#3a3a3a}
  [data-panel="spotify"] .sp-qbtn .mi{font-size:16px}
  [data-panel="spotify"] .sp-queue-sec{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#9a9a9a;margin:10px 0 2px}
  [data-panel="spotify"] .sp-queue-sec:first-child{margin-top:2px}
  [data-panel="spotify"] .sp-queue-empty{color:#9a9a9a;font-size:13px;padding:8px 0}
  [data-panel="spotify"] .sp-q-ctrl{display:flex;align-items:center;gap:2px;flex:0 0 auto}
  [data-panel="spotify"] .sp-q-ctrl button{width:32px;height:32px;display:inline-flex;align-items:center;justify-content:center;background:transparent;border:none;color:#cfcfcf;border-radius:50%;cursor:pointer;padding:0}
  [data-panel="spotify"] .sp-q-ctrl button:hover{background:rgba(255,255,255,.1);color:#fff}
  [data-panel="spotify"] .sp-q-ctrl button:disabled{opacity:.3;cursor:default}
  [data-panel="spotify"] .sp-q-ctrl button.rm:hover{color:#ff6b6b}
  [data-panel="spotify"] .sp-q-ctrl .mi{font-size:20px}
  [data-panel="spotify"] .sp-queue-row.nu .sp-queue-cover{box-shadow:0 0 0 2px var(--spg)}
  /* overgeslagen (expliciet) nummer in de geschiedenis */
  [data-panel="spotify"] .sp-hist-row.skipped .sp-hist-title{color:#c9c9c9;text-decoration:line-through;text-decoration-color:rgba(255,107,107,.7)}
  [data-panel="spotify"] .sp-hist-row.skipped .sp-hist-cover{opacity:.6}
  [data-panel="spotify"] .sp-hist-skip{display:inline-flex;align-items:center;gap:4px;margin-top:4px;font-size:11px;font-weight:800;color:#ff6b6b;background:rgba(255,107,107,.12);border:1px solid rgba(255,107,107,.35);padding:2px 8px;border-radius:999px}
  [data-panel="spotify"] .sp-hist-skip .mi{font-size:14px}
  [data-panel="spotify"] .sp-queue-by{display:flex;align-items:center;gap:3px;font-size:11px;color:#9a9a9a;margin-top:2px}
  [data-panel="spotify"] .sp-queue-by .mi{font-size:13px;color:var(--spg)}
  </style>
  <div class="sp-brandbar"><img src="{{ spotify_logo }}" alt="Spotify"><div class="sp-tag">speelt op<br><b>{{ settings.spotify_device_name or brand.name }}</b></div></div>
  {% if admin and vr.spotify.transport %}
  <style>
    #spSrcCard .sp-src-head{font-size:13px;font-weight:600;opacity:.85;display:flex;align-items:center;gap:6px;margin-bottom:8px}
    #spSrcCard .sp-src-btns{display:flex;gap:8px}
    #spSrcCard .sp-src{flex:1;justify-content:center;opacity:.6}
    #spSrcCard .sp-src.active{opacity:1;outline:2px solid var(--spg,#1db954);outline-offset:-2px}
    #spGuiTransport{display:none;align-items:center;gap:10px;margin-top:10px}
    #spGuiTransport .sp-gui-status{font-size:12px;opacity:.7;margin-left:auto}
  </style>
  <div class="vol-card" id="spSrcCard">
    <div class="sp-src-head"><span class="mi">tune</span> Spotify-bron</div>
    <div class="sp-src-btns">
      <button type="button" class="btn sp-src" data-src="omroepweb" onclick="spSetSource('omroepweb')">omroepweb</button>
      <button type="button" class="btn sp-src" data-src="gui" onclick="spSetSource('gui')"><span class="mi" style="font-size:16px">graphic_eq</span>&nbsp;Automix (desktop)</button>
    </div>
    <div id="spGuiTransport">
      <button class="sp-btn" title="Vorige" onclick="spGui('prev')"><span class="mi">skip_previous</span></button>
      <button class="sp-btn sp-play" title="Play / pauze" onclick="spGui('playpause')"><span class="mi">play_arrow</span></button>
      <button class="sp-btn" title="Volgende" onclick="spGui('next')"><span class="mi">skip_next</span></button>
      <span class="sp-gui-status" id="spGuiStatus"></span>
    </div>
    <div id="spSrcHint" style="font-size:12px;opacity:.7;margin-top:8px"></div>
  </div>
  <script>
    function spRenderSource(src, guistatus){
      document.querySelectorAll('#spSrcCard .sp-src').forEach(function(b){ b.classList.toggle('active', b.dataset.src===src); });
      var t=document.getElementById('spGuiTransport'); if(t) t.style.display=(src==='gui')?'flex':'none';
      var h=document.getElementById('spSrcHint'); if(h) h.textContent=(src==='gui')
        ? 'De desktop-app (Automix) speelt in de winkel — bedien via RDP of de knoppen hierboven.'
        : 'De door omroepweb beheerde Spotify speelt in de winkel.';
      var gs=document.getElementById('spGuiStatus'); if(gs) gs.textContent=guistatus? ('desktop: '+guistatus):'';
    }
    function spLoadSource(){ fetch('/api/spotify/source').then(function(r){return r.json();}).then(function(d){ spRenderSource(d.source,d.gui_status); }).catch(function(){}); }
    function spSetSource(src){ fetch('/api/spotify/source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:src})}).then(function(r){return r.json();}).then(function(d){ spRenderSource(d.source,d.gui_status); }).catch(function(){}); }
    function spGui(cmd){ fetch('/api/spotify/gui/'+cmd,{method:'POST'}).then(function(r){return r.json();}).then(function(d){ var gs=document.getElementById('spGuiStatus'); if(gs&&d.gui_status) gs.textContent='desktop: '+d.gui_status; }).catch(function(){}); }
    document.addEventListener('DOMContentLoaded', spLoadSource);
  </script>
  {% endif %}
  <div class="vol-card">
    <div class="vol-head">
      <div class="vol-numwrap">
        <span class="vol-ic">music_note</span>
        <div class="vol-big" id="piVolNum">--%</div>
      </div>
      <div class="vol-chips"><span class="vol-chip" id="piVolBadge">vol: …</span></div>
    </div>
    {% if vr.spotify.volume %}<div class="vslider"><div class="vslider-fill"></div><input class="vol-slider" type="range" min="{{ vr.spotify.vmin }}" max="{{ vr.spotify.vmax }}" id="piVolSlider"></div>{% endif %}
    <div class="vol-controls">
      {% if vr.spotify.volume %}<button class="btn vol-step" title="Zachter" onclick="piStep(-1)">−</button>
      <button class="btn vol-step" title="Harder" onclick="piStep(1)">+</button>{% endif %}
      {% if admin %}<button class="btn btn-gold" onclick="spFixOpen()"><span class="mi">healing</span> Spotify fixen</button>
      {% elif vr.spotify.restart %}<button class="btn btn-gold" onclick="piRestart()"><span class="mi">restart_alt</span> Spotify herstarten</button>{% endif %}
    </div>
    <div id="piMsg" style="margin-top:6px;font-size:13px;display:none"></div>
  </div>
  {% if admin %}
  <div id="spFixBd" class="spfix-bd" onclick="if(event.target===this)spFixClose()">
    <div class="spfix">
      <div class="spfix-head">
        <img src="{{ spotify_logo }}" alt="Spotify" class="spfix-logo">
        <div class="spfix-htxt"><div class="spfix-title">Spotify fixen</div><div class="spfix-sub" id="spFixSub">Automatische reparatie</div></div>
        <button class="spfix-x" onclick="spFixClose()" aria-label="Sluiten"><span class="mi">close</span></button>
      </div>
      <div class="spfix-log" id="spFixLog"></div>
      <div class="spfix-ask" id="spFixAsk" style="display:none">
        <div class="spfix-q" id="spFixQ"></div>
        <div class="spfix-btns" id="spFixBtns"></div>
      </div>
    </div>
  </div>
  <style>
    .spfix-bd{position:fixed;inset:0;z-index:2147483200;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.72);padding:18px}
    .spfix-bd.on{display:flex}
    .spfix{width:min(560px,96vw);max-height:86vh;display:flex;flex-direction:column;background:#121212;color:#fff;border:1px solid #2a2a2a;border-radius:16px;box-shadow:0 24px 80px rgba(0,0,0,.6);overflow:hidden}
    .spfix-head{display:flex;align-items:center;gap:12px;padding:16px 18px;background:linear-gradient(180deg,#1a1a1a,#121212);border-bottom:1px solid #262626}
    .spfix-logo{height:26px;width:auto}
    .spfix-htxt{flex:1;min-width:0}
    .spfix-title{font-size:18px;font-weight:800;letter-spacing:.2px}
    .spfix-sub{font-size:12px;color:#1ed760;font-weight:700;display:flex;align-items:center;gap:7px}
    .spfix-sub.busy::before{content:"";width:9px;height:9px;border-radius:50%;background:#1ed760;animation:spfixPulse 1s infinite}
    .spfix-x{background:none;border:0;color:#b3b3b3;cursor:pointer;padding:6px;border-radius:8px;line-height:0}
    .spfix-x:hover{background:#242424;color:#fff}
    .spfix-log{flex:1;overflow-y:auto;padding:14px 16px;background:#0a0a0a;font-family:ui-monospace,'SF Mono',Menlo,Consolas,monospace;font-size:13px;line-height:1.5;min-height:130px}
    .spfix-line{display:flex;gap:8px;padding:2px 0;white-space:pre-wrap;word-break:break-word}
    .spfix-line .ic{flex:none;font-size:15px;line-height:1.4}
    .spfix-line.info{color:#b3b3b3}
    .spfix-line.ok{color:#1ed760}
    .spfix-line.warn{color:#f0c14b}
    .spfix-line.err{color:#ff5c5c}
    .spfix-ask{padding:14px 16px;border-top:1px solid #262626;background:#161616}
    .spfix-q{font-size:14px;font-weight:700;margin-bottom:12px;color:#fff}
    .spfix-btns{display:flex;gap:10px;flex-wrap:wrap}
    .spfix-btn{flex:1;min-width:120px;padding:13px 16px;border:0;border-radius:999px;font-size:15px;font-weight:800;cursor:pointer}
    .spfix-btn.yes{background:#1ed760;color:#000}
    .spfix-btn.yes:hover{background:#1fdf64}
    .spfix-btn.no{background:#2a2a2a;color:#fff}
    .spfix-btn.no:hover{background:#383838}
    .spfix-btn.alt{background:#333;color:#fff;border:1px solid #555}
    @keyframes spfixPulse{0%,100%{opacity:1}50%{opacity:.25}}
  </style>
  <script>
  (function(){
    var es=null, curStep=null;
    var bd=document.getElementById('spFixBd');
    function el(id){return document.getElementById(id);}
    function busy(txt){ var s=el('spFixSub'); s.textContent=txt||'Bezig\\u2026'; s.classList.add('busy'); }
    function idle(txt){ var s=el('spFixSub'); s.textContent=txt||''; s.classList.remove('busy'); }
    function ics(lvl){ return {info:'chevron_right',ok:'check_circle',warn:'warning',err:'error'}[lvl]||'chevron_right'; }
    function addLine(lvl,msg){
      var box=el('spFixLog');
      var d=document.createElement('div'); d.className='spfix-line '+(lvl||'info');
      var i=document.createElement('span'); i.className='ic mi'; i.textContent=ics(lvl);
      var t=document.createElement('span'); t.textContent=msg;
      d.appendChild(i); d.appendChild(t); box.appendChild(d); box.scrollTop=box.scrollHeight;
    }
    function clearAsk(){ el('spFixAsk').style.display='none'; el('spFixBtns').innerHTML=''; el('spFixQ').textContent=''; }
    function stopEs(){ if(es){ try{es.close();}catch(e){} es=null; } }
    function showButtons(q,btns){
      el('spFixQ').textContent=q||''; var wrap=el('spFixBtns'); wrap.innerHTML='';
      btns.forEach(function(b){ var x=document.createElement('button'); x.className='spfix-btn '+(b.cls||'no'); x.textContent=b.label; x.onclick=b.fn; wrap.appendChild(x); });
      el('spFixAsk').style.display='block';
    }
    function run(step){
      curStep=step; clearAsk(); stopEs();
      busy(step==='deep'?'Diepere diagnose\\u2026':(step==='rollback'?'Terugdraaien\\u2026':'Herstarten\\u2026'));
      es=new EventSource('/api/spotify/fix?step='+encodeURIComponent(step));
      es.onmessage=function(ev){
        var d; try{d=JSON.parse(ev.data);}catch(e){return;}
        if(d.t==='log'){ addLine(d.lvl,d.msg); }
        else if(d.t==='end'){ stopEs(); onEnd(d); }
      };
      es.onerror=function(){ stopEs(); idle(''); addLine('err','Verbinding met de server verbroken.'); showButtons('',[{label:'Sluiten',cls:'no',fn:spFixClose}]); };
    }
    function onEnd(d){
      if(d.result==='ask'){
        idle('Wacht op je antwoord');
        showButtons(d.msg,[
          {label:'Ja, het werkt',cls:'yes',fn:success},
          {label:'Nee, nog niet',cls:'no',fn:nextAfterNo}
        ]);
      } else if(d.result==='fail'){
        idle('Reparatie afgerond');
        var btns=[{label:'Sluiten',cls:'no',fn:spFixClose}];
        if(d.can_rollback){ btns.unshift({label:'Vorige versie terugzetten',cls:'alt',fn:function(){ run('rollback'); }}); }
        showButtons(d.msg,btns);
      } else { idle(''); showButtons(d.msg||'Klaar.',[{label:'Sluiten',cls:'no',fn:spFixClose}]); }
    }
    function nextAfterNo(){
      clearAsk();
      if(curStep==='restart'){ addLine('info','\\u2500\\u2500 Diepere diagnose starten \\u2500\\u2500'); run('deep'); }
      else if(curStep==='deep'){ addLine('info','\\u2500\\u2500 Automatische stappen uitgeput \\u2500\\u2500'); showButtons('De automatische reparatie hielp niet. Wil je terugdraaien naar de vorige go-librespot-versie?',[
          {label:'Ja, terugdraaien',cls:'alt',fn:function(){ run('rollback'); }},
          {label:'Sluiten',cls:'no',fn:spFixClose}
        ]); }
      else { showButtons('Ook dit hielp niet. Bekijk de logs of neem contact op.',[{label:'Sluiten',cls:'no',fn:spFixClose}]); }
    }
    function success(){ idle('Opgelost'); clearAsk(); addLine('ok','Top! Spotify Connect werkt weer.'); showButtons('',[{label:'Sluiten',cls:'yes',fn:spFixClose}]); }
    window.spFixOpen=function(){ el('spFixLog').innerHTML=''; clearAsk(); bd.classList.add('on'); addLine('info','Spotify-reparatie gestart\\u2026'); run('restart'); };
    window.spFixClose=function(){ stopEs(); bd.classList.remove('on'); idle(''); };
    document.addEventListener('keydown',function(e){ if(e.key==='Escape' && bd.classList.contains('on')) spFixClose(); });
  })();
  </script>
  {% endif %}
  <div class="sp-explicit" id="spExplicit"><span class="mi">explicit</span><span id="spExplicitTxt">Expliciet nummer — Spotify is gedempt. Sla het over op je telefoon.</span></div>
  <div class="sp-player" id="spPlayer" data-state="empty" data-control="0">
    <div class="sp-backdrop" id="spBackdrop"></div>
    <canvas class="sp-viz" id="spViz"></canvas>
    <div class="sp-main">
      <div class="sp-cover"><img id="spCover" alt=""><span class="sp-ph mi">music_note</span></div>
      <div class="sp-info">
        <div class="sp-title" id="spTitle">Er speelt niets</div>
        <div class="sp-artist" id="spArtist"></div>
        <div class="sp-progress">
          <div class="sp-barwrap" id="spBarWrap"><div class="sp-bar"><div class="sp-fill" id="spFill"></div><span class="sp-knob" id="spKnob"></span></div></div>
          <div class="sp-times"><span id="spCur">0:00</span><span id="spDur">0:00</span></div>
        </div>
        <div class="sp-status"><span class="sp-eq"><i></i><i></i><i></i></span> <span id="spStatusText">—</span></div>
        <div class="sp-caster" id="spCaster"><span class="mi">person</span><span id="spCasterName"></span></div>
        <div class="sp-comnext" id="spComNext"><span class="mi">campaign</span> Na dit nummer volgt een reclame</div>
      </div>
    </div>
    {% if vr.spotify.transport %}<div class="sp-controls" id="spControls">
      <button class="sp-btn" title="Vorige" onclick="spPrev()"><span class="mi">skip_previous</span></button>
      <button class="sp-btn sp-play" id="spPlayBtn" title="Afspelen / pauze" onclick="spPlayPause()"><span class="mi">play_arrow</span></button>
      <button class="sp-btn" title="Volgende" onclick="spNext()"><span class="mi">skip_next</span></button>
    </div>{% endif %}
    {% if vr.spotify.jam %}<button type="button" class="sp-jam" id="spJam" onclick="spJamToggle()"><span class="mi">group_add</span> Jam meedoen</button>
    <div class="sp-jambox" id="spJamBox">
      <div class="jam-cap">Open in de Spotify-app <b>Zoeken</b> → tik op het <b>camera-icoon</b> en scan deze code om mee te doen aan de Jam.</div>
      <img id="spJamScan" alt="Spotify Jam-code">
      <div class="sp-jam-actions">
        <a id="spJamOpen" href="#"><span class="mi">open_in_new</span> Open in Spotify</a>
        <button type="button" onclick="spJamCopy()"><span class="mi">content_copy</span> Kopieer link</button>
      </div>
    </div>{% endif %}
  </div>
  {% if vr.spotify.transport %}
  <style>
  .sp-search{max-width:560px;margin-top:16px;background:#fff;border:1px solid var(--stroke);border-radius:16px;padding:14px 16px;box-shadow:var(--shadow-sm)}
  .sp-search-head{display:flex;align-items:center;gap:8px;font-weight:800;color:var(--green-dark);font-size:14px;margin-bottom:10px}
  .sp-search-head .mi{font-size:20px}
  .sp-search-box{display:flex;gap:8px}
  .sp-search-box input{flex:1;min-width:0;border:1px solid var(--stroke);border-radius:10px;padding:10px 12px;font-size:14px;font-family:inherit;color:var(--green-dark)}
  .sp-search-box button{flex:0 0 auto;border:1px solid var(--red-dark);background:var(--red);color:var(--on-primary);border-radius:10px;padding:0 14px;font-weight:700;cursor:pointer}
  .sp-search-box button .mi{font-size:20px}
  .sp-res{margin-top:10px;display:flex;flex-direction:column}
  .sp-res-row{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--stroke-light)}
  .sp-res-row:first-child{border-top:none}
  .sp-res-cover{width:44px;height:44px;border-radius:8px;object-fit:cover;flex:0 0 auto;background:#eef2e6}
  .sp-res-info{flex:1;min-width:0}
  .sp-res-title{font-weight:700;color:var(--green-dark);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-res-sub{color:#5b6b52;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-res-actions{display:flex;gap:6px;flex:0 0 auto}
  .sp-res-actions button{display:inline-flex;align-items:center;gap:4px;padding:7px 10px;border-radius:999px;border:1px solid var(--stroke);background:#fff;color:var(--green-dark);font-weight:700;font-size:12px;cursor:pointer}
  .sp-res-actions button.play{background:var(--red);border-color:var(--red-dark);color:var(--on-primary)}
  .sp-res-actions .mi{font-size:16px}
  .sp-webmsg{margin-top:8px;font-size:13px;display:none}
  .sp-queue{max-width:560px;margin-top:12px;background:#fff;border:1px solid var(--stroke);border-radius:16px;padding:14px 16px;box-shadow:var(--shadow-sm)}
  .sp-queue-head{display:flex;align-items:center;gap:8px;font-weight:800;color:var(--green-dark);font-size:14px;margin-bottom:8px}
  .sp-queue-head .mi{font-size:20px}
  .sp-queue-row{display:flex;align-items:center;gap:10px;padding:6px 0;border-top:1px solid var(--stroke-light)}
  .sp-queue-row:first-child{border-top:none}
  .sp-queue-cover{width:34px;height:34px;border-radius:6px;object-fit:cover;flex:0 0 auto;background:#eef2e6}
  .sp-queue-info{flex:1;min-width:0}
  .sp-queue-title{font-weight:700;color:var(--green-dark);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-queue-sub{color:#5b6b52;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-queue-tag{flex:0 0 auto;font-size:11px;color:var(--red);font-weight:700}
  </style>
  <style>
  [data-panel="spotify"] .sp-search-box{position:relative}
  [data-panel="spotify"] .sp-search-box .sp-sic{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:#8f8f8f;font-size:22px;pointer-events:none}
  [data-panel="spotify"] .sp-search-box input{padding-left:42px;border-radius:999px;height:46px}
  [data-panel="spotify"] .sp-search-box .sp-clear{position:absolute;right:8px;top:50%;transform:translateY(-50%);width:34px;height:34px;padding:0;border-radius:50%;background:transparent;border:none;color:#b3b3b3;display:none}
  [data-panel="spotify"] .sp-search-box .sp-clear.on{display:inline-flex;align-items:center;justify-content:center}
  [data-panel="spotify"] .sp-browse{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
  [data-panel="spotify"] .sp-chip{border:1px solid rgba(255,255,255,.16);background:#2a2a2a;color:#fff;border-radius:999px;padding:7px 14px;font-size:13px;font-weight:700;cursor:pointer;transition:background .15s}
  [data-panel="spotify"] .sp-chip:hover{background:#3a3a3a}
  [data-panel="spotify"] .sp-chip.on{background:var(--spg);border-color:var(--spg);color:#000}
  [data-panel="spotify"] .sp-browse-lbl{font-size:12px;color:#9a9a9a;font-weight:700;margin:12px 0 2px;text-transform:uppercase;letter-spacing:.04em}
  </style>
  <div class="sp-search">
    <div class="sp-search-head"><span class="mi">search</span> Zoeken &amp; bladeren <img src="{{ spotify_logo }}" alt="Spotify" style="height:19px;margin-left:auto"></div>
    <div class="sp-search-box">
      <span class="mi sp-sic">search</span>
      <input id="spSearchInput" type="text" placeholder="Waar wil je naar luisteren?" autocomplete="off" oninput="spSearchLive()" onkeydown="if(event.key==='Enter'){event.preventDefault();spSearch();}">
      <button type="button" class="sp-clear" id="spClear" title="Wissen" onclick="spClearSearch()"><span class="mi">close</span></button>
    </div>
    <div class="sp-browse-lbl" id="spBrowseLbl">Bladeren</div>
    <div class="sp-browse" id="spBrowse"></div>
    <div class="sp-res" id="spSearchRes"></div>
    <div class="sp-webmsg" id="spWebMsg"></div>
  </div>
  <div class="sp-queue" id="spQueueBox" style="display:none">
    <div class="sp-queue-head"><span class="mi">queue_music</span> Wachtrij
      <button class="sp-qbtn" id="spQClearBtn" style="margin-left:auto;display:none" onclick="spQClear()"><span class="mi">delete_sweep</span> Leegmaken</button>
      <button class="sp-qbtn" onclick="spQueueRefresh()"><span class="mi">refresh</span></button>
    </div>
    <div class="sp-queue-list" id="spQueueList"></div>
  </div>
  {% endif %}
  {% if vr.spotify.history %}
  <style>
  .sp-history{padding:14px 16px}
  .sp-hist-head{display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px;margin-bottom:8px}
  .sp-hist-head .mi{font-size:20px}
  .sp-hist-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-top:1px solid var(--stroke-light)}
  .sp-hist-row:first-child{border-top:none}
  .sp-hist-cover{width:38px;height:38px;border-radius:7px;object-fit:cover;flex:0 0 auto;background:#eef2e6}
  .sp-hist-info{flex:1;min-width:0}
  .sp-hist-title{font-weight:700;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-hist-sub{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-hist-meta{flex:0 0 auto;text-align:right;font-size:11px;max-width:44%}
  .sp-hist-caster{display:flex;align-items:center;gap:3px;justify-content:flex-end;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .sp-hist-caster .mi{font-size:13px;flex:0 0 auto}
  </style>
  <div class="sp-history" id="spHistory" style="display:none">
    <div class="sp-hist-head"><span class="mi">history</span> Afgespeelde nummers</div>
    <div class="sp-hist-list" id="spHistList"></div>
  </div>
  {% endif %}
</div>
{% endif %}

{% if vr.omroep.view or vr.spotify.view %}
<div class="subpanel" data-panel="eqviz">
  <div class="eqviz-wrap">
    {% if vr.omroep.view %}<div class="eqviz" data-source="rca" data-eq="bg" data-edit="{{ '1' if vr.omroep.channel else '0' }}" data-title="{{ brand.radio_name }}" data-note="PLUS Radio &rarr; versterker"></div>{% endif %}
    {% if vr.spotify.view %}<div class="eqviz eqviz-dark" data-source="spot" data-eq="spot" data-edit="{{ '1' if vr.spotify.transport else '0' }}" data-title="Spotify" data-logo="{{ spotify_logo }}" data-note="Spotify &rarr; versterker"></div>{% endif %}
  </div>
</div>
{% endif %}
</div>

<script>
const EV="{{ url_for('events') }}";
const CAN_TRANSPORT={{ 'true' if vr.spotify.transport else 'false' }};
const SPOTIFY_LOGO="{{ spotify_logo }}";
function spOpenUrl(uri){ return (uri||'').indexOf('spotify:track:')===0 ? ('https://open.spotify.com/track/'+uri.split(':')[2]) : ''; }
let dragging=false, piSliderActive=false;
function clampv(x){ x=parseInt(x||0); return x<0?0:(x>100?100:x); }
function paintSlider(sl){
  if(!sl) return;
  var v=clampv(sl.value);
  var f=sl.parentElement && sl.parentElement.querySelector('.vslider-fill');
  if(f) f.style.width=v+'%';
}
function volDrag(sl,on){ if(sl&&sl.parentElement) sl.parentElement.classList.toggle('dragging',!!on); }
function setMuteBtn(muted){
  var b=document.getElementById('muteBtn');
  if(b) b.innerHTML='<span class="mi">'+(muted?'volume_up':'volume_off')+'</span> '+(muted?'Unmute':'Mute');
}
function sendVol(v){
  fetch("{{ url_for('api_set_volume') }}",{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({volume:v})});
}
function attachSlider(){
  const sl=document.getElementById('volSlider');
  if(!sl) return;
  // Tijdens slepen: alleen live UI bijwerken (geen server-call → geen log-spam).
  sl.addEventListener('input',function(){
    dragging=true; volDrag(sl,true);
    var v=clampv(sl.value);
    document.getElementById('volBadge').innerText=v+'%';
    paintSlider(sl);
  });
  // Bij loslaten: pas dan de waarde versturen (en dus loggen).
  sl.addEventListener('change',function(){
    var v=clampv(sl.value);
    dragging=false; volDrag(sl,false);
    setMuteBtn(false);
    sendVol(v);
  });
  sl.addEventListener('mousedown',()=>{dragging=true;volDrag(sl,true);});sl.addEventListener('touchstart',()=>{dragging=true;volDrag(sl,true);});
}
function attachPiSlider(){
  const sl=document.getElementById('piVolSlider');
  if(!sl) return;
  sl.addEventListener('input',function(){
    piSliderActive=true; volDrag(sl,true);
    document.getElementById('piVolNum').textContent=sl.value+'%';
    paintSlider(sl);
  });
  sl.addEventListener('change',function(){
    piSliderActive=false; volDrag(sl,false);
    fetch('/api/pi/volume',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({volume:parseInt(sl.value)})})
      .then(r=>r.json()).then(j=>piMsg(j.ok?'Volume ingesteld':'Fout',j.ok));
  });
}
function applyState(d){
  var badge=document.getElementById('volBadge');
  if(!badge) return;                 // PLUS Radio-tab niet zichtbaar voor deze gebruiker
  if(!dragging){
    var vol = d.muted ? ((typeof d.bg_before!=='undefined')?d.bg_before:d.volume) : d.volume;
    const s=document.getElementById('volSlider');
    badge.innerText=vol+'%';
    if(s){ s.value=vol; paintSlider(s); }
  }
  var mb=document.getElementById('muteBadge');
  if(mb){ mb.innerText=d.muted?'Gemutet':'Actief'; mb.classList.toggle('on',!d.muted); }
  var rb=document.getElementById('rcaBadge');
  if(rb){ rb.innerText='RCA: '+(d.rca_running?'actief':'gestopt'); rb.classList.toggle('on',!!d.rca_running); }
  var pb=document.getElementById('playBadge');
  if(pb) pb.style.display=d.playing?'inline-flex':'none';
  setMuteBtn(d.muted);
  // PLUS Radio now-playing (titel via de Lisa) — snel via SSE (1s)
  var pt=document.getElementById('prTitle');
  if(pt && typeof d.plusradio_title!=='undefined'){
    var box=document.getElementById('prNow');
    var prt=d.plusradio_title;
    if(prt){ pt.textContent=(prt.toLowerCase()==='commercial'?'Reclame':prt); if(box) box.classList.remove('pr-empty'); }
    else { pt.textContent='—'; if(box) box.classList.add('pr-empty'); }
    if(box) box.classList.toggle('pr-ad', (prt||'').toLowerCase()==='commercial');
    if(!prt || (prt||'').toLowerCase()==='commercial') applyPrMeta('','','','');
    else applyPrMeta(d.plusradio_cover, d.plusradio_artist, d.plusradio_full_title, d.plusradio_album);
  }
  if(typeof d.plusradio_channel!=='undefined') prMarkChan(d.plusradio_channel);
}
function applyPrMeta(cover, artist, fullTitle, album){
  var meta=document.getElementById('prMeta'), img=document.getElementById('prCover'),
      ar=document.getElementById('prArtist'), pt=document.getElementById('prTitle');
  if(fullTitle && pt) pt.textContent=fullTitle;   // volledige, niet-afgekapte titel
  if(!meta) return;
  if(cover || artist){
    if(img){ if(cover){ img.src=cover; img.style.display=''; } else img.style.display='none'; }
    if(ar) ar.innerHTML=_hEsc(artist||'')+(album?'<span class="alb">'+_hEsc(album)+'</span>':'');
    meta.style.display='flex';
  } else {
    if(img){ img.style.display='none'; img.removeAttribute('src'); }
    if(ar) ar.textContent='';
    meta.style.display='none';
  }
}
var _prExpanded=false, _prLast=[];
function prMarkChan(ch){
  document.querySelectorAll('#prChan button').forEach(function(b){ b.classList.toggle('on', parseInt(b.dataset.ch)===ch); });
}
var _pendingChan=null;
function prSetChan(n){
  _pendingChan=n;
  var naam=(n==2?'Plus Easy':'Plus Main');
  var e1=document.getElementById('chanName'), e2=document.getElementById('chanName2');
  if(e1) e1.textContent=naam; if(e2) e2.textContent=naam;
  var m=document.getElementById('chanConfirm'); if(m) m.style.display='flex';
}
function chanCancel(){ var m=document.getElementById('chanConfirm'); if(m) m.style.display='none'; _pendingChan=null; }
function chanConfirm(){
  var n=_pendingChan; chanCancel(); if(!n) return;
  fetch('/api/plusradio/channel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({channel:n})})
    .then(r=>r.json()).then(function(j){ if(j.channel) prMarkChan(j.channel); setTimeout(prRefresh,1000); }).catch(function(){});
}
function prToggleHist(){ _prExpanded=!_prExpanded; renderPrHist(); }
function renderPrHist(){
  var wrap=document.getElementById('prHistWrap'); if(!wrap) return;
  if(!_prLast.length){ wrap.style.display='none'; return; }
  wrap.style.display='block';
  var show=_prExpanded?_prLast:_prLast.slice(0,5);
  var html=show.map(function(t){
    var cov=t.cover?'<img class="cov" src="'+encodeURI(t.cover)+'" alt="">':'';
    var ttl=_hEsc(t.full_title||t.title);
    var art=t.artist?'<span class="ar">'+_hEsc(t.artist)+'</span>':'';
    return '<div class="pr-hist-row"><span class="tw">'+cov+'<span class="tt"><span class="t">'+ttl+'</span>'+art+'</span></span><span class="a">'+_hWhen(t.played_at)+'</span></div>';
  }).join('');
  if(_prLast.length>5){ html+='<button class="hist-more" onclick="prToggleHist()">'+(_prExpanded?'Minder tonen':('Toon alle '+_prLast.length))+'</button>'; }
  var el=document.getElementById('prHistList'); if(el) el.innerHTML=html;
}
function prRefresh(){
  if(!document.getElementById('prNow') && !document.getElementById('prChan')) return;
  fetch('/api/plusradio',{cache:'no-store'}).then(r=>r.json()).then(function(j){
    var pt=document.getElementById('prTitle'), box=document.getElementById('prNow');
    if(pt && j.title){ pt.textContent=(j.title.toLowerCase()==='commercial'?'Reclame':j.title); if(box) box.classList.remove('pr-empty'); }
    if(!j.title || (j.title||'').toLowerCase()==='commercial') applyPrMeta('','','','');
    else applyPrMeta(j.plusradio_cover, j.plusradio_artist, j.plusradio_full_title, j.plusradio_album);
    if(typeof j.channel!=='undefined') prMarkChan(j.channel);
    _prLast=j.history||[]; renderPrHist();
  }).catch(function(){});
}
function piMsg(txt,ok){
  const el=document.getElementById('piMsg');
  el.style.display='block';el.style.color=ok?'#4b7a12':'#c62828';el.textContent=txt;
  setTimeout(()=>el.style.display='none',3000);
}
// ── Spotify now-playing player ──
let NP={state:'empty',pos:0,dur:0,recv:0,cover:''};
let spSeeking=false;
let _explicitLock=false;
let _jamUrl='';
function _jamToken(){ return (( _jamUrl.split('/socialsession/')[1]||'').split('?')[0]); }
function spJamToggle(){
  var box=document.getElementById('spJamBox'); if(!box||!_jamUrl) return;
  var open=!box.classList.contains('on'); box.classList.toggle('on',open);
  if(open){ var t=_jamToken();
    document.getElementById('spJamScan').src='https://scannables.scdn.co/uri/plain/png/1DB954/white/640/spotify:socialsession:'+t;
    document.getElementById('spJamOpen').href='spotify:socialsession:'+t;
  }
}
function spJamCopy(){
  if(!_jamUrl) return;
  navigator.clipboard.writeText(_jamUrl).then(function(){piMsg('Link gekopieerd',true);})
    .catch(function(){piMsg('Kopiëren mislukt — selecteer de link handmatig',false);});
}
function npFmt(ms){ms=Math.max(0,ms|0);var s=Math.floor(ms/1000),m=Math.floor(s/60);s=s%60;return m+':'+(s<10?'0':'')+s;}
function npCurPos(){
  if(NP.state==='playing'){var v=NP.pos+(performance.now()-NP.recv);return NP.dur>0?Math.min(v,NP.dur):v;}
  return NP.pos;
}
function npRender(){
  var p=document.getElementById('spPlayer');if(!p)return;
  var stt=document.getElementById('spStatusText');
  var pb=document.getElementById('spPlayBtn');
  if(pb) pb.querySelector('.mi').textContent=(NP.state==='playing'?'pause':'play_arrow');
  if(p.dataset.state==='empty'){
    if(!spSeeking){document.getElementById('spFill').style.width='0%';document.getElementById('spKnob').style.left='0%';}
    document.getElementById('spCur').textContent='0:00';
    document.getElementById('spDur').textContent='0:00';
    stt.textContent='Er speelt niets op Spotify';return;
  }
  var pos=npCurPos(),dur=NP.dur;
  var pct=(dur>0?Math.min(100,pos/dur*100):0);
  if(!spSeeking){
    document.getElementById('spFill').style.width=pct+'%';
    document.getElementById('spKnob').style.left=pct+'%';
    document.getElementById('spCur').textContent=npFmt(pos);
  }
  document.getElementById('spDur').textContent=dur>0?npFmt(dur):'—';
  stt.textContent=NP.state==='playing'?'Aan het afspelen':(NP.state==='paused'?'Gepauzeerd':'Gestopt');
}
function applyNowPlaying(np){
  var p=document.getElementById('spPlayer');if(!p)return;
  var bd=document.getElementById('spBackdrop');
  if(!np||!np.name){p.dataset.state='empty';NP.state='empty';
    document.getElementById('spTitle').textContent='Er speelt niets';
    document.getElementById('spArtist').textContent='';
    document.getElementById('spCover').style.display='none';
    document.getElementById('spCaster').classList.remove('on');
    NP.cover=''; if(bd) bd.style.backgroundImage='';
    npRender();return;}
  NP.state=np.state||'stopped';NP.pos=np.position_ms||0;NP.dur=np.duration_ms||0;NP.recv=performance.now();
  if((np.cover||'')!==NP.cover){NP.cover=np.cover||'';var img=document.getElementById('spCover');
    if(NP.cover){img.src=NP.cover;img.style.display='block';img.onerror=function(){img.style.display='none';};}
    else{img.style.display='none';}
    if(bd) bd.style.backgroundImage=NP.cover?('url("'+NP.cover+'")'):'';}
  document.getElementById('spTitle').textContent=np.name+(np.is_explicit?'  🅴':'');
  document.getElementById('spArtist').textContent=[np.artist,np.album].filter(Boolean).join(' — ');
  var cel=document.getElementById('spCaster');
  if(np.played_by){document.getElementById('spCasterName').textContent='Gecast door '+np.played_by;cel.classList.add('on');}
  else{cel.classList.remove('on');}
  p.dataset.state=NP.state;
  npRender();
}
// ── Afgespeelde nummers (geschiedenis) ──
function _hEsc(s){ return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
function _hAgo(sec){
  var s=Math.floor(Date.now()/1000)-(sec||0);
  if(s<60) return 'net';
  if(s<3600) return Math.floor(s/60)+' min';
  if(s<86400) return Math.floor(s/3600)+' u';
  return Math.floor(s/86400)+' d';
}
function _hClock(sec){
  var d=new Date((sec||0)*1000);
  return ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2);
}
function _hSameDay(sec){
  var d=new Date((sec||0)*1000), n=new Date();
  return d.getFullYear()===n.getFullYear()&&d.getMonth()===n.getMonth()&&d.getDate()===n.getDate();
}
function _hDate(sec){
  var d=new Date((sec||0)*1000);
  return ('0'+d.getDate()).slice(-2)+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+d.getFullYear();
}
// Kloktijd + "hoelang geleden"; na langer dan 59 min alleen de kloktijd.
// Andere dag dan vandaag → datum ervoor.
function _hWhen(sec){
  var s=Math.floor(Date.now()/1000)-(sec||0);
  var clock=_hClock(sec);
  if(!_hSameDay(sec)) return _hDate(sec)+' &middot; '+clock;
  if(s<60)   return clock+' &middot; net';
  if(s<3600) return clock+' &middot; '+Math.floor(s/60)+' min geleden';
  return clock;
}
var _spExpanded=false, _spLast=[];
function spToggleHist(){ _spExpanded=!_spExpanded; renderHistory(_spLast); }
function renderHistory(list){
  var box=document.getElementById('spHistory'); if(!box) return;
  _spLast=list||_spLast;
  if(!_spLast.length){ box.style.display='none'; return; }
  box.style.display='block';
  var show=_spExpanded?_spLast:_spLast.slice(0,5);
  var html=show.map(function(t){
    var cov=t.cover?'<img class="sp-hist-cover" src="'+_hEsc(t.cover)+'" alt="">':'<span class="sp-hist-cover"></span>';
    var caster=t.played_by?'<div class="sp-hist-caster"><span class="mi">person</span>'+_hEsc(t.played_by)+'</div>':'';
    var reason=t.skip_reason==='explicit'?'expliciet nummer':(t.skip_reason||'');
    var skip=t.skipped?'<div class="sp-hist-skip"><span class="mi">block</span>Overgeslagen'+(reason?(' — '+_hEsc(reason)):'')+'</div>':'';
    return '<div class="sp-hist-row'+(t.skipped?' skipped':'')+'">'+cov+
      '<div class="sp-hist-info"><div class="sp-hist-title">'+_hEsc(t.name)+(t.explicit?' 🅴':'')+'</div>'+
      '<div class="sp-hist-sub">'+_hEsc(t.artist)+'</div>'+skip+'</div>'+
      '<div class="sp-hist-meta">'+_hWhen(t.played_at)+caster+'</div></div>';
  }).join('');
  if(_spLast.length>5){ html+='<button class="hist-more" onclick="spToggleHist()">'+(_spExpanded?'Minder tonen':('Toon alle '+_spLast.length))+'</button>'; }
  var el=document.getElementById('spHistList'); if(el) el.innerHTML=html;
}
// ── Transportbesturing (alleen actief in go-librespot-modus) ──
function spCmd(path){return fetch('/api/pi/spotify/'+path,{method:'POST'}).then(r=>r.json()).catch(()=>({}));}
// ── Spotify Web API: zoeken, afspelen, wachtrij ──
var _spWebRes=[];
var _spDeb=null;
function spWebMsg(txt,ok){
  var el=document.getElementById('spWebMsg'); if(!el) return;
  el.style.display='block'; el.style.color=ok?'#1ed760':'#ff6b6b'; el.textContent=txt;
  setTimeout(function(){el.style.display='none';},3500);
}
// Bladeren: snelle categorie-zoekopdrachten (betrouwbaar, zonder verouderde browse-API).
var SP_BROWSE=[
  {l:'Nederlandstalig',q:'nederlandstalig'},{l:'Top hits NL',q:'top 40 nederland'},
  {l:'Pop',q:'pop hits'},{l:'Rock',q:'rock classics'},{l:'Dance',q:'dance hits'},
  {l:'80s',q:'80s hits'},{l:'90s',q:'90s hits'},{l:'Feest',q:'feest'},
  {l:'Rustig',q:'rustige muziek'},{l:'Kerst',q:'kerst'}
];
function spRenderBrowse(){
  var b=document.getElementById('spBrowse'); if(!b) return;
  b.innerHTML=SP_BROWSE.map(function(c,i){return '<button type="button" class="sp-chip" onclick="spChip('+i+')">'+_hEsc(c.l)+'</button>';}).join('');
}
function spChip(i){
  var c=SP_BROWSE[i]; if(!c) return;
  var inp=document.getElementById('spSearchInput'); if(inp){ inp.value=c.q; }
  spToggleClear(); spSearch();
}
function spToggleClear(){
  var inp=document.getElementById('spSearchInput'), cl=document.getElementById('spClear');
  if(cl) cl.classList.toggle('on', !!(inp && inp.value.trim()));
}
function spSetBrowse(show){
  var b=document.getElementById('spBrowse'), l=document.getElementById('spBrowseLbl');
  if(b) b.style.display=show?'flex':'none';
  if(l) l.style.display=show?'block':'none';
}
function spClearSearch(){
  var inp=document.getElementById('spSearchInput'); if(inp){ inp.value=''; inp.focus(); }
  document.getElementById('spSearchRes').innerHTML='';
  spSetBrowse(true); spToggleClear();
}
function spSearchLive(){
  spToggleClear();
  clearTimeout(_spDeb);
  var q=(document.getElementById('spSearchInput').value||'').trim();
  if(!q){ document.getElementById('spSearchRes').innerHTML=''; spSetBrowse(true); return; }
  _spDeb=setTimeout(spSearch,300);
}
function spResRow(t,i){
  var cov=t.cover?'<img class="sp-res-cover" src="'+_hEsc(t.cover)+'" alt="">':'<span class="sp-res-cover"></span>';
  return '<div class="sp-res-row" onclick="spPlayIdx('+i+')" title="Afspelen">'+cov+
    '<div class="sp-res-info"><div class="sp-res-title">'+_hEsc(t.name)+(t.explicit?' 🅴':'')+'</div>'+
    '<div class="sp-res-sub">'+_hEsc(t.artist)+'</div></div>'+
    '<div class="sp-res-actions" onclick="event.stopPropagation()">'+
    '<button class="play" title="Afspelen" onclick="spPlayIdx('+i+')"><span class="mi">play_arrow</span></button>'+
    '<button title="In wachtrij" onclick="spQueueIdx('+i+')"><span class="mi">add</span></button>'+
    '<a href="'+spOpenUrl(t.uri)+'" target="_blank" rel="noopener" title="Open in Spotify" style="display:inline-flex;align-items:center"><img src="'+SPOTIFY_LOGO+'" alt="Open in Spotify" style="height:20px"></a>'+
    '</div></div>';
}
function spSearch(){
  var inp=document.getElementById('spSearchInput'); if(!inp) return;
  var q=(inp.value||'').trim(); if(!q){ spSetBrowse(true); return; }
  spSetBrowse(false);
  var box=document.getElementById('spSearchRes');
  box.innerHTML='<div class="sp-res-row" style="color:#9a9a9a;font-size:13px;cursor:default">Zoeken&hellip;</div>';
  fetch('/api/spotify/search?q='+encodeURIComponent(q),{cache:'no-store'})
    .then(function(r){return r.json();})
    .then(function(j){
      _spWebRes=(j.results||[]);
      if(j.error){ box.innerHTML=''; spWebMsg('Spotify nog niet gekoppeld of niet bereikbaar (Beheer → Spotify)',false); return; }
      if(!_spWebRes.length){ box.innerHTML='<div class="sp-res-row" style="color:#9a9a9a;font-size:13px;cursor:default">Geen resultaten</div>'; return; }
      box.innerHTML=_spWebRes.map(spResRow).join('');
    })
    .catch(function(){ box.innerHTML=''; spWebMsg('Zoeken mislukt',false); });
}
function spPlayIdx(i){
  var t=_spWebRes[i]; if(!t) return;
  spWebMsg('Afspelen&hellip;',true);
  fetch('/api/spotify/play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uri:t.uri})})
    .then(function(r){return r.json();})
    .then(function(j){
      if(j.blocked){ spWebMsg('Geblokkeerd: er speelt een expliciet nummer',false); return; }
      spWebMsg(j.ok?('Speelt: '+t.name):'Afspelen mislukt',j.ok);
      setTimeout(piRefresh,700); setTimeout(spQueueRefresh,900);
    })
    .catch(function(){ spWebMsg('Afspelen mislukt',false); });
}
function spQueueIdx(i){
  var t=_spWebRes[i]; if(!t) return;
  fetch('/api/spotify/queue',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({uri:t.uri,name:t.name,artist:t.artist,cover:t.cover,explicit:!!t.explicit})})
    .then(function(r){return r.json();})
    .then(function(j){ spWebMsg('In wachtrij: '+t.name,true); spRenderQueue(j.queue); })
    .catch(function(){ spWebMsg('Toevoegen mislukt',false); });
}
var _spQ=[];
function _spMi(n){ return '<span class="mi">'+n+'</span>'; }
function spQueueRefresh(){
  var box=document.getElementById('spQueueBox'); if(!box) return;
  fetch('/api/spotify/queue',{cache:'no-store'})
    .then(function(r){return r.json();})
    .then(function(j){ _spQCur=j.current||null; spRenderQueue(j.next||[]); })
    .catch(function(){});
}
var _spQCur=null;
function _spQRow(t,i,now){
  var cov=t.cover?'<img class="sp-queue-cover" src="'+_hEsc(t.cover)+'" alt="">':'<span class="sp-queue-cover"></span>';
  var right = now ? '<span class="sp-queue-tag">nu</span>'
    : '<div class="sp-q-ctrl">'+
      '<button title="Omhoog" onclick="spQMove('+i+',-1)"'+(i===0?' disabled':'')+'>'+_spMi('keyboard_arrow_up')+'</button>'+
      '<button title="Omlaag" onclick="spQMove('+i+',1)"'+(i===_spQ.length-1?' disabled':'')+'>'+_spMi('keyboard_arrow_down')+'</button>'+
      '<button title="Verwijderen" class="rm" onclick="spQRemove('+i+')">'+_spMi('close')+'</button>'+
      '</div>';
  var by=(!now&&t.added_by)?'<div class="sp-queue-by"><span class="mi">person</span>'+_hEsc(t.added_by)+'</div>':'';
  return '<div class="sp-queue-row'+(now?' nu':'')+'">'+cov+
    '<div class="sp-queue-info"><div class="sp-queue-title">'+_hEsc(t.name)+(t.explicit?' 🅴':'')+'</div>'+
    '<div class="sp-queue-sub">'+_hEsc(t.artist)+'</div>'+by+'</div>'+right+'</div>';
}
function spRenderQueue(next){
  var box=document.getElementById('spQueueBox'); if(!box) return;
  _spQ=next||[]; box.style.display='block';
  var clr=document.getElementById('spQClearBtn'); if(clr) clr.style.display=_spQ.length?'inline-flex':'none';
  var html='';
  if(_spQCur&&_spQCur.name){ html+='<div class="sp-queue-sec">Speelt nu</div>'+_spQRow(_spQCur,-1,true); }
  html+='<div class="sp-queue-sec">Hierna'+(_spQ.length?(' &middot; '+_spQ.length):'')+'</div>';
  if(!_spQ.length){
    html+='<div class="sp-queue-empty">Nog niets. Zet een nummer erin met&nbsp;<span class="mi" style="font-size:15px;vertical-align:-3px">add</span>&nbsp;bij de zoekresultaten.</div>';
  } else {
    html+=_spQ.map(function(t,i){return _spQRow(t,i,false);}).join('');
  }
  document.getElementById('spQueueList').innerHTML=html;
}
function spQMove(i,dir){
  var j=i+dir; if(j<0||j>=_spQ.length) return;
  var a=_spQ.slice(); var tmp=a[i]; a[i]=a[j]; a[j]=tmp;
  fetch('/api/spotify/queue/reorder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order:a.map(function(t){return t.uri;})})})
    .then(function(r){return r.json();}).then(function(j){ spRenderQueue(j.queue); }).catch(function(){});
}
function spQRemove(i){
  var t=_spQ[i]; if(!t) return;
  fetch('/api/spotify/queue/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({uri:t.uri})})
    .then(function(r){return r.json();}).then(function(j){ spRenderQueue(j.queue); }).catch(function(){});
}
function spQClear(){
  fetch('/api/spotify/queue/clear',{method:'POST'})
    .then(function(r){return r.json();}).then(function(j){ spRenderQueue(j.queue); }).catch(function(){});
}
function spPlayPause(){
  var cur=npCurPos(); NP.pos=cur; NP.recv=performance.now();
  NP.state=(NP.state==='playing'?'paused':'playing');
  var p=document.getElementById('spPlayer'); if(p.dataset.state!=='empty') p.dataset.state=NP.state;
  npRender();
  spCmd('playpause').then(function(){setTimeout(piRefresh,500);});
}
function spNext(){ spCmd('next').then(function(){setTimeout(piRefresh,600);setTimeout(spQueueRefresh,900);}); }
function spPrev(){ spCmd('prev').then(function(){setTimeout(piRefresh,600);}); }
function spSeekFrac(clientX){
  var bar=document.getElementById('spBarWrap').querySelector('.sp-bar');
  var r=bar.getBoundingClientRect(); var f=(clientX-r.left)/r.width;
  return Math.max(0,Math.min(1,f));
}
function spBarStart(e){
  if(!CAN_TRANSPORT) return;
  var p=document.getElementById('spPlayer');
  if(!p||p.dataset.control!=='1'||NP.dur<=0) return;
  spSeeking=true; document.getElementById('spBarWrap').classList.add('sp-seeking');
  spBarMove(e); if(e.cancelable)e.preventDefault();
}
function spBarMove(e){
  if(!spSeeking) return;
  var x=(e.touches&&e.touches[0])?e.touches[0].clientX:e.clientX;
  var f=spSeekFrac(x),pct=f*100;
  document.getElementById('spFill').style.width=pct+'%';
  document.getElementById('spKnob').style.left=pct+'%';
  document.getElementById('spCur').textContent=npFmt(f*NP.dur);
  if(e.cancelable)e.preventDefault();
}
function spBarEnd(e){
  if(!spSeeking) return;
  var x=(e.changedTouches&&e.changedTouches[0])?e.changedTouches[0].clientX:e.clientX;
  var posms=Math.round(spSeekFrac(x)*NP.dur);
  spSeeking=false; document.getElementById('spBarWrap').classList.remove('sp-seeking');
  NP.pos=posms; NP.recv=performance.now();
  fetch('/api/pi/spotify/seek',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position_ms:posms})})
    .then(function(){setTimeout(piRefresh,500);});
}
function attachSeek(){
  var bw=document.getElementById('spBarWrap'); if(!bw) return;
  bw.addEventListener('mousedown',spBarStart);
  document.addEventListener('mousemove',spBarMove);
  document.addEventListener('mouseup',spBarEnd);
  bw.addEventListener('touchstart',spBarStart,{passive:false});
  document.addEventListener('touchmove',spBarMove,{passive:false});
  document.addEventListener('touchend',spBarEnd);
}
function piRefresh(){
  fetch('/api/pi/status',{cache:'no-store'}).then(r=>r.json()).then(j=>{
    var piBadge=document.getElementById('piVolBadge');
    if(!piBadge) return;               // Spotify-tab niet zichtbaar voor deze gebruiker
    piBadge.textContent='vol: '+(j.volume>=0?j.volume+'%':'n/b');
    var pl=document.getElementById('spPlayer'); if(pl) pl.dataset.control=j.control?'1':'0';
    var exp=!!j.explicit; _explicitLock=exp;
    var eb=document.getElementById('spExplicit');
    if(eb){ eb.classList.toggle('on',exp);
      if(exp) document.getElementById('spExplicitTxt').textContent='Expliciet nummer'+(j.explicit_name?(' “'+j.explicit_name+'”'):'')+' — Spotify is gedempt en het volume is geblokkeerd. Sla het nummer over op je telefoon.'; }
    var vc=document.querySelector('[data-panel="spotify"] .vol-card'); if(vc) vc.classList.toggle('sp-locked',exp);
    var ps=document.getElementById('piVolSlider'); if(ps) ps.disabled=exp;
    var cn=document.getElementById('spComNext'); if(cn) cn.classList.toggle('on',!!j.commercial_next);
    var jam=document.getElementById('spJam');
    if(jam){ if(j.jam_url){_jamUrl=j.jam_url;jam.classList.add('on');} else {_jamUrl='';jam.classList.remove('on');var jb=document.getElementById('spJamBox');if(jb)jb.classList.remove('on');} }
    applyNowPlaying(j.nowplaying);
    renderHistory(j.history);
    if(!piSliderActive){
      const s=document.getElementById('piVolSlider');
      var pn=document.getElementById('piVolNum');
      if(pn) pn.textContent=(j.volume>=0?j.volume:'-')+'%';
      if(s){ s.value=j.volume>=0?j.volume:50; paintSlider(s); }
    }
  }).catch(()=>{});
}
let _piMuted=false;
function piMuteToggle(){
  if(_explicitLock){piMsg('Geblokkeerd: er speelt een expliciet nummer',false);return;}
  const url=_piMuted?'/api/pi/unmute':'/api/pi/mute';
  fetch(url,{method:'POST'}).then(r=>r.json()).then(j=>{
    if(j.ok){
      _piMuted=!_piMuted;
      document.getElementById('piMuteBtn').innerHTML='<span class="mi">'+(_piMuted?'volume_up':'volume_off')+'</span> '+(_piMuted?'Spotify unmute':'Spotify mute');
      piMsg(_piMuted?'Gemutet':'Ongemutet',true);
    } else { piMsg('Fout',false); }
  });
}
function startSSE(){const es=new EventSource(EV);es.onmessage=e=>{try{applyState(JSON.parse(e.data));}catch(_){}};es.onerror=()=>{es.close();setTimeout(startSSE,1500);};}
// +/- : direct in de UI tonen (geen wachttijd) en meteen naar de server.
function step(d){
  const s=document.getElementById('volSlider');
  if(!s) return;
  var nv=clampv(parseInt(s.value||0)+d);
  s.value=nv; nv=parseInt(s.value);   // range-attributen klemmen op toegestaan bereik
  document.getElementById('volBadge').innerText=nv+'%'; paintSlider(s); setMuteBtn(false);
  dragging=true; setTimeout(function(){dragging=false;},700);
  fetch("{{ url_for('api_step') }}",{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delta:d})});
}
function piStep(d){
  if(_explicitLock){piMsg('Geblokkeerd: er speelt een expliciet nummer',false);return;}
  const s=document.getElementById('piVolSlider');
  if(!s) return;
  var nv=clampv(parseInt(s.value||0)+d);
  s.value=nv; nv=parseInt(s.value);   // range-attributen klemmen op toegestaan bereik
  document.getElementById('piVolNum').textContent=nv+'%'; paintSlider(s);
  piSliderActive=true; setTimeout(function(){piSliderActive=false;},1200);
  fetch('/api/pi/volume',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({volume:nv})})
    .then(r=>r.json()).then(j=>piMsg(j.ok?'Volume ingesteld':'Fout',j.ok));
}
function muteToggle(){
  fetch("{{ url_for('api_mute_toggle') }}",{method:'POST'}).then(r=>r.json())
    .then(j=>{ if(j&&typeof j.muted!=='undefined') setMuteBtn(j.muted); }).catch(()=>{});
}
function rcaToggle(){fetch("{{ url_for('api_rca_toggle') }}",{method:'POST'});}
function stopPlayback(){fetch("{{ url_for('api_stop') }}",{method:'POST'});}
function piRestart(){
  piMsg('Herstarten…',true);
  fetch('/api/pi/restart_raspotify',{method:'POST'}).then(r=>r.json()).then(j=>piMsg(j.ok?'Spotify-speler herstart':'Mislukt',j.ok));
}
function volTab(name){
  document.querySelectorAll('#volTabs .subtab').forEach(function(b){b.classList.toggle('active',b.dataset.tab===name);});
  document.querySelectorAll('.subpanel').forEach(function(p){p.classList.toggle('active',p.dataset.panel===name);});
  try{localStorage.setItem('vol_tab',name);}catch(_){}
  paintSlider(document.getElementById('volSlider'));
  paintSlider(document.getElementById('piVolSlider'));
}
window.onload=()=>{
  var first=document.querySelector('#volTabs .subtab');
  var t=''; try{t=localStorage.getItem('vol_tab')||'';}catch(_){}
  if(!t||!document.querySelector('.subtab[data-tab="'+t+'"]')) t=first?first.dataset.tab:'';
  if(t) volTab(t);
  attachSlider();attachPiSlider();attachSeek();startSSE();piRefresh();setInterval(piRefresh,5000);setInterval(npRender,500);
  prRefresh();setInterval(prRefresh,8000);
  if(CAN_TRANSPORT){ spRenderBrowse(); spQueueRefresh(); setInterval(spQueueRefresh,15000); }
  paintSlider(document.getElementById('volSlider'));
  paintSlider(document.getElementById('piVolSlider'));
};
</script>

<style>
[data-panel="eqviz"]{padding-top:6px}
.eqviz-wrap{display:flex;flex-wrap:wrap;gap:18px;align-items:flex-start;margin-top:8px}
.eqviz{flex:1 1 360px;max-width:560px;background:#fff;border:1px solid var(--stroke);border-radius:18px;padding:18px 20px;box-shadow:var(--shadow-sm)}
.eqviz-dark{background:linear-gradient(165deg,#2b2b30,#141414);border-color:rgba(255,255,255,.08);color:#fff}
.eqviz-head{display:flex;align-items:center;gap:9px;font-weight:800;font-size:16px;margin-bottom:14px;color:var(--green-dark)}
.eqviz-dark .eqviz-head{color:#fff}
.eqviz-head .mi{font-size:22px}
.eqviz-head .hlogo{height:22px;width:auto;display:block}
.eqviz-head .st{margin-left:auto;font-size:11px;font-weight:700;color:var(--fg3);display:inline-flex;align-items:center;gap:6px;text-transform:uppercase;letter-spacing:.03em}
.eqviz-dark .eqviz-head .st{color:#9a9a9a}
.eqviz-head .st .dot{width:9px;height:9px;border-radius:50%;background:#c0392b;transition:background .3s}
.eqviz-head .st.live .dot{background:#39c46e;box-shadow:0 0 8px #39c46e}
.viz-wrap{position:relative;border-radius:12px;overflow:hidden}
.viz-canvas{display:block;width:100%;height:120px;background:#0c0e0b}
.eqviz-dark .viz-canvas{background:#000}
.viz-hint{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:8px;background:rgba(0,0,0,.55);color:#fff;font-size:13px;font-weight:700;cursor:pointer}
.viz-hint .mi{font-size:26px}
.viz-hint.hide{display:none}
.eq-presets{display:flex;flex-wrap:wrap;gap:6px;margin-top:16px}
.eq-preset-btn{border:1px solid var(--stroke);background:#f6f7f4;color:var(--green-dark);border-radius:999px;padding:6px 13px;font-size:12px;font-weight:700;cursor:pointer}
.eq-preset-btn:hover{background:#eaf4d8}
.eq-preset-btn.on{background:var(--red);border-color:var(--red);color:#fff}
.eqviz-dark .eq-preset-btn{background:#2f2f35;border-color:rgba(255,255,255,.14);color:#e6e6e6}
.eqviz-dark .eq-preset-btn:hover{background:#3a3a42}
.eqviz-dark .eq-preset-btn.on{background:#1ed760;border-color:#1ed760;color:#000}
.eq-grid{display:flex;justify-content:space-between;gap:5px;margin-top:16px}
.eq-band{display:flex;flex-direction:column;align-items:center;gap:5px;flex:1}
.eq-band .val{font-size:10px;font-weight:800;color:var(--green-dark);min-height:13px}
.eqviz-dark .eq-band .val{color:#1ed760}
.eq-band input[type=range]{writing-mode:vertical-lr;direction:rtl;width:22px;height:104px;accent-color:var(--red);cursor:pointer}
.eqviz-dark .eq-band input[type=range]{accent-color:#1ed760}
.eq-band input[type=range]:disabled{opacity:.5;cursor:default}
.eq-band .fl{font-size:9px;color:var(--fg3);font-weight:700}
.eqviz-dark .eq-band .fl{color:#9a9a9a}
.eq-scale{display:flex;justify-content:space-between;font-size:9px;color:var(--fg3);margin-top:2px;padding:0 2px}
.eq-foot{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:14px}
.eq-foot .help{margin:0;font-size:11px}
.eqviz-dark .eq-foot .help{color:#9a9a9a}
</style>
<script>
(function(){
  var FREQ_LBL=['31','63','125','250','500','1k','2k','4k','8k','16k'];
  var BARS=48;
  var PRESETS=[['Vlak',[0,0,0,0,0,0,0,0,0,0]],['Bas',[7,6,4,2,0,0,0,0,0,0]],['Warm',[4,3,2,1,0,-1,-2,-2,-1,0]],['Helder',[0,0,0,0,1,2,3,4,5,6]],['Spraak',[-4,-3,-1,1,3,4,3,1,-1,-3]],['Loudness',[6,4,2,0,-1,0,1,3,5,6]]];
  function dbOf(v){ return Math.round((v-50)/50*12); }
  function fdb(v){ var d=dbOf(v); return d>0?('+'+d):(''+d); }
  function valOfDb(db){ return Math.max(0,Math.min(100,Math.round(50+db/12*50))); }
  function jpost(which,body){ return fetch('/api/eq/'+which,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); }
  var vizzes=[];
  function setBand(v,i,val){ v.sliders[i].value=val; v.vals[i].textContent=fdb(val); }
  function markPreset(v){ var cur=v.sliders.map(function(s){return dbOf(parseInt(s.value,10));}); v.presetBtns.forEach(function(b,idx){ var p=PRESETS[idx][1],same=true; for(var k=0;k<10;k++){ if(p[k]!==cur[k]){ same=false; break; } } b.classList.toggle('on',same); }); }
  function applyPreset(v,arr){ var bands=arr.map(valOfDb); for(var i=0;i<10;i++) setBand(v,i,bands[i]); markPreset(v); if(v.edit) jpost(v.which,{bands:bands}); }
  function build(v){
    var el=v.el, logo=el.dataset.logo;
    var head='<div class="eqviz-head">'+(logo?'<img class="hlogo" src="'+logo+'">':'<span class="mi">graphic_eq</span>')+'<span class="htxt">'+v.title+'</span><span class="st"><span class="dot"></span><span class="lbl">&mdash;</span></span></div>';
    var viz='<div class="viz-wrap"><canvas class="viz-canvas"></canvas><div class="viz-hint"><span class="mi">play_circle</span> Tik om de visualizer te starten</div></div>';
    var grid='<div class="eq-grid"></div><div class="eq-scale"><span>+12 dB</span><span>0</span><span>&minus;12 dB</span></div>';
    var foot='<div class="eq-foot"><span class="help">'+(el.dataset.note||'')+(v.edit?'':' &middot; alleen-lezen')+'</span>'+(v.edit?'<button class="btn btn-sm eq-reset"><span class="mi mi-sm">restart_alt</span> Vlak</button>':'')+'</div>';
    el.innerHTML=head+viz+'<div class="eq-presets"></div>'+grid+foot;
    v.canvas=el.querySelector('.viz-canvas'); v.ctx=v.canvas.getContext('2d');
    v.hint=el.querySelector('.viz-hint'); v.stEl=el.querySelector('.st'); v.stLbl=el.querySelector('.st .lbl');
    var pw=el.querySelector('.eq-presets'); v.presetBtns=[];
    PRESETS.forEach(function(p){ var b=document.createElement('button'); b.className='eq-preset-btn'; b.textContent=p[0]; if(!v.edit) b.disabled=true; b.addEventListener('click',function(){ applyPreset(v,p[1]); }); pw.appendChild(b); v.presetBtns.push(b); });
    var gr=el.querySelector('.eq-grid'); v.sliders=[]; v.vals=[];
    for(var i=0;i<10;i++){
      var col=document.createElement('div'); col.className='eq-band';
      var val=document.createElement('div'); val.className='val'; val.textContent='0';
      var inp=document.createElement('input'); inp.type='range'; inp.min=0; inp.max=100; inp.value=50; inp.dataset.i=i; inp.disabled=!v.edit;
      var fl=document.createElement('div'); fl.className='fl'; fl.textContent=FREQ_LBL[i];
      col.appendChild(val); col.appendChild(inp); col.appendChild(fl); gr.appendChild(col);
      v.sliders.push(inp); v.vals.push(val);
      if(v.edit){ (function(inp,val){ var t=null; inp.addEventListener('input',function(){ val.textContent=fdb(inp.value); markPreset(v); clearTimeout(t); t=setTimeout(function(){ jpost(v.which,{index:parseInt(inp.dataset.i,10),value:parseInt(inp.value,10)}); },170); }); })(inp,val); }
    }
    var rs=el.querySelector('.eq-reset'); if(rs) rs.addEventListener('click',function(){ applyPreset(v,PRESETS[0][1]); });
    fetch('/api/eq/'+v.which).then(function(r){return r.json();}).then(function(j){ if(j.bands){ for(var i=0;i<10;i++) setBand(v,i,j.bands[i]); markPreset(v); } }).catch(function(){});
    v.hint.classList.add('hide');   // server-side visualizer: geen gebruikersgebaar nodig
  }
  function sizeCanvas(v){ var r=v.canvas.getBoundingClientRect(); if(!r.width) return false; var dpr=window.devicePixelRatio||1; v.canvas.width=Math.round(r.width*dpr); v.canvas.height=Math.round((r.height||120)*dpr); return true; }
  function rcaPoll(v){ fetch('/api/viz/rca',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){ v.tband=j.bands||[]; v.rlive=!!j.live; }).catch(function(){ v.rlive=false; }); }
  function rcaLevels(v){ var tb=v.tband; if(!tb||!tb.length){ for(var i=0;i<v.out.length;i++) v.out[i]*=0.86; return !!v.rlive; } if(v.out.length!==tb.length) v.out=new Array(tb.length).fill(0); for(var i=0;i<tb.length;i++){ var t=tb[i]; v.out[i]= t>v.out[i] ? (v.out[i]*0.35+t*0.65) : (v.out[i]*0.78+t*0.22); } return !!v.rlive; }
  function spSync(v){ fetch('/api/pi/status',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){ var np=j.nowplaying||{}; v.spPlaying=(np.state==='playing'); }).catch(function(){ v.spPlaying=false; }); }
  function spLevels(v){ if(!v.spPlaying){ for(var i=0;i<BARS;i++) v.out[i]*=0.9; return false; } v.phase+=0.06; var beat=0.5+0.5*Math.sin(v.phase*3.0); var env=0.55+0.35*Math.sin(v.phase*0.7); for(var i=0;i<BARS;i++){ var x=i/BARS; var shape=Math.sin(Math.PI*Math.pow(x,0.6))*0.8+0.2; var w=0.5+0.5*Math.sin(v.phase*2.1+i*0.6)+0.35*Math.sin(v.phase*1.3+i*1.7); var tgt=Math.max(0,Math.min(1, shape*env*(0.4+0.5*w)+beat*shape*0.25)); v.out[i]=v.out[i]*0.6+tgt*0.4; } return true; }
  function roundBar(ctx,x,y,w,h,r){ if(r>w/2)r=w/2; if(r>h)r=h; ctx.beginPath(); ctx.moveTo(x,y+h); ctx.lineTo(x,y+r); ctx.arcTo(x,y,x+r,y,r); ctx.lineTo(x+w-r,y); ctx.arcTo(x+w,y,x+w,y+r,r); ctx.lineTo(x+w,y+h); ctx.closePath(); ctx.fill(); }
  function draw(v){
    var c=v.canvas,ctx=v.ctx; if(!c.width) return; var W=c.width,H=c.height,n=v.out.length; if(!n) return;
    var slot=W/n, bw=Math.max(2, slot*0.66), pad=(slot-bw)/2;
    ctx.clearRect(0,0,W,H);
    if(!v.peaks||v.peaks.length!==n){ v.peaks=new Array(n).fill(0); }
    var grad=ctx.createLinearGradient(0,H,0,0);
    grad.addColorStop(0,v.c1); grad.addColorStop(0.55,v.c2); grad.addColorStop(1,v.c3||v.c2);
    for(var i=0;i<n;i++){
      var lv=v.out[i];
      v.peaks[i] = lv>v.peaks[i] ? lv : Math.max(lv, v.peaks[i]-0.018);
      var bh=Math.max(H*0.02, lv*H*0.9), x=i*slot+pad, y=H-bh;
      ctx.fillStyle=grad; roundBar(ctx,x,y,bw,bh,Math.min(bw/2,4));
      var py=H-Math.max(H*0.02, v.peaks[i]*H*0.9);
      ctx.fillStyle='rgba(255,255,255,.5)'; ctx.fillRect(x, Math.max(1,py-2), bw, 2);
    }
  }
  function setStat(v,live){ if(!v.stEl) return; v.stEl.classList.toggle('live',!!live); v.stLbl.textContent=live?'live':(v.source==='spot'?'stil':'geen signaal'); }
  function loop(){
    var vis=document.visibilityState!=='hidden';
    for(var i=0;i<vizzes.length;i++){
      var v=vizzes[i]; var panel=v.el.closest('.subpanel'); var active=vis&&(!panel||panel.classList.contains('active'));
      if(active){
        if(!v.sized) v.sized=sizeCanvas(v);
        var live;
        if(v.source==='rca'){ if(!v.rTimer){ rcaPoll(v); v.rTimer=setInterval((function(vv){return function(){rcaPoll(vv);};})(v),100); } live=rcaLevels(v); }
        else { if(!v.spTimer){ spSync(v); v.spTimer=setInterval((function(vv){return function(){spSync(vv);};})(v),2500); } live=spLevels(v); }
        draw(v); setStat(v,live);
      } else {
        if(v.rTimer){ clearInterval(v.rTimer); v.rTimer=null; v.rlive=false; }
        if(v.spTimer){ clearInterval(v.spTimer); v.spTimer=null; v.spPlaying=false; }
        v.sized=false;
      }
    }
    requestAnimationFrame(loop);
  }
  function _shade(hex,amt){ hex=(hex||'').trim().replace('#',''); if(hex.length===3) hex=hex.split('').map(function(c){return c+c;}).join(''); if(hex.length<6) return hex||'#80bd1d'; var r=parseInt(hex.substr(0,2),16),g=parseInt(hex.substr(2,2),16),b=parseInt(hex.substr(4,2),16); function f(x){ return Math.max(0,Math.min(255,Math.round(amt<0? x*(1+amt): x+(255-x)*amt))); } return 'rgb('+f(r)+','+f(g)+','+f(b)+')'; }
  function brandCols(){ var s=getComputedStyle(document.documentElement); var p=(s.getPropertyValue('--red')||'#80bd1d').trim(); var d=(s.getPropertyValue('--green-dark')||'#115013').trim(); return {c1:_shade(d,-0.15), c2:p, c3:_shade(p,0.45)}; }
  function applyRcaCols(v){ var c=brandCols(); v.c1=c.c1; v.c2=c.c2; v.c3=c.c3; }
  function initAll(){
    [].forEach.call(document.querySelectorAll('.eqviz'),function(el){ var v={el:el, source:el.dataset.source, which:el.dataset.eq, edit:el.dataset.edit==='1', title:el.dataset.title||'', out:new Array(BARS).fill(0), phase:Math.random()*6}; if(v.source==='rca'){ applyRcaCols(v); } else { v.c1='#0c7a33'; v.c2='#17c257'; v.c3='#4dff8f'; } build(v); vizzes.push(v); });
    var pv=document.getElementById('prViz');
    if(pv){ var pvv={el:pv, canvas:pv, ctx:pv.getContext('2d'), source:'rca', out:new Array(BARS).fill(0)}; applyRcaCols(pvv); vizzes.push(pvv); }
    var sv=document.getElementById('spViz');
    if(sv){ vizzes.push({el:sv, canvas:sv, ctx:sv.getContext('2d'), source:'spot', out:new Array(BARS).fill(0), phase:Math.random()*6, c1:'#0c7a33', c2:'#17c257', c3:'#4dff8f'}); }
    // Huisstijl-wissel: rca-kleuren mee laten kleuren
    var bp=window.brandPick; window.brandPick=function(n){ if(bp) try{bp(n);}catch(e){} setTimeout(function(){ vizzes.forEach(function(v){ if(v.source==='rca') applyRcaCols(v); }); },50); };
    if(!vizzes.length) return;
    window.addEventListener('resize',function(){ vizzes.forEach(function(v){ v.sized=false; }); });
    requestAnimationFrame(loop);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',initAll); else initAll();
})();
</script>

"""

ONBOARDING_BODY = """
<style>
.ob-wrap{max-width:640px;margin:0 auto;padding:8px 4px 40px}
.ob-head{text-align:center;margin-bottom:18px}
.ob-head h1{margin:0 0 4px;color:var(--green-dark);font-size:26px}
.ob-head p{margin:0;color:var(--fg3)}
.ob-dots{display:flex;justify-content:center;gap:8px;margin:16px 0 22px}
.ob-dots span{width:10px;height:10px;border-radius:50%;background:var(--stroke)}
.ob-dots span.on{background:var(--green);transform:scale(1.15)}
.ob-dots span.done{background:var(--green-dark)}
.ob-card{background:#fff;border:1px solid var(--stroke);border-radius:16px;padding:22px 24px;box-shadow:var(--shadow-sm)}
.ob-card h2{margin:0 0 4px;font-size:20px;color:var(--green-dark);display:flex;align-items:center;gap:8px}
.ob-card .sub{color:var(--fg3);font-size:13px;margin:0 0 16px}
.ob-step{display:none}.ob-step.on{display:block}
.ob-field{margin-bottom:14px}
.ob-field .label{font-weight:700;font-size:13px;color:var(--green-dark);margin-bottom:5px}
.ob-nav{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:18px}
.ob-msg{font-size:13px;margin-top:10px;display:none}
.ob-dev{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ob-meter{height:12px;border-radius:6px;background:#e4e7df;overflow:hidden;flex:1;min-width:120px}
.ob-meter > i{display:block;height:100%;width:0;background:linear-gradient(90deg,#39c46e,#f5c542,#e05c4a);transition:width .15s}
.ob-brandopt{display:flex;gap:10px;flex-wrap:wrap}
.ob-brandopt label{border:1px solid var(--stroke);border-radius:12px;padding:10px 16px;cursor:pointer;font-weight:700;color:var(--green-dark)}
.ob-brandopt input{margin-right:6px}
.ob-brandopt label:has(input:checked){border-color:var(--green);background:#eaf4d8}
.ob-skip{background:none;border:none;color:var(--fg3);text-decoration:underline;cursor:pointer;font-size:13px}
</style>
<div class="ob-wrap">
  <div class="ob-head"><h1>Welkom 👋</h1><p>Laten we dit audiosysteem in een paar stappen instellen.</p></div>
  <div class="ob-dots" id="obDots"></div>

  {% if not has_admin %}
  <div class="ob-step" data-step="admin">
    <div class="ob-card">
      <h2><span class="mi">admin_panel_settings</span> Beheerder</h2>
      <p class="sub">Maak de eerste beheerder aan om in te loggen.</p>
      <div class="ob-field"><div class="label">Naam (weergave)</div><input class="input" id="obDisp" placeholder="bijv. Beheer"></div>
      <div class="ob-field"><div class="label">Gebruikersnaam</div><input class="input" id="obUser" autocomplete="username" placeholder="bijv. admin"></div>
      <div class="ob-field"><div class="label">Wachtwoord (min. 6 tekens)</div><input class="input" type="password" id="obPw" autocomplete="new-password"></div>
      <div class="ob-msg" id="obAdminMsg"></div>
    </div>
  </div>
  {% endif %}

  <div class="ob-step" data-step="brand">
    <div class="ob-card">
      <h2><span class="mi">palette</span> Huisstijl &amp; locatie</h2>
      <p class="sub">Kies de winkelketen en (optioneel) de filiaalnaam.</p>
      <div class="ob-field"><div class="label">Huisstijl</div>
        <div class="ob-brandopt" id="obBrand">
          {% for b in brands %}<label><input type="radio" name="obbrand" value="{{ b.key }}" {{ 'checked' if b.key=='plus' else '' }}>{{ b.name }}</label>{% endfor %}
        </div>
      </div>
      <div class="ob-field"><div class="label">Locatie / filiaal (optioneel)</div><input class="input" id="obLoc" placeholder="bijv. Centrum"></div>
    </div>
  </div>

  <div class="ob-step" data-step="audio">
    <div class="ob-card">
      <h2><span class="mi">graphic_eq</span> Audio</h2>
      <p class="sub">Kies en test de geluidsuitgang (versterker/speakers) en, indien aanwezig, de line-in (winkelmuziek).</p>
      <label class="switch-row" style="margin-bottom:14px"><input type="checkbox" id="obDemo" onchange="obDemoToggle()"> <span><b>Demo / test op deze computer</b> &mdash; audio komt uit dit apparaat (laptop), geen winkelhardware nodig.</span></label>
      <div class="ob-field"><div class="label">Uitgang (naar versterker/speakers)</div>
        <div class="ob-dev"><select class="input" id="obOut" style="flex:1"></select>
          <button type="button" class="btn btn-sm btn-inline" style="width:auto" onclick="obTestOut()"><span class="mi">volume_up</span> Test toon</button></div>
        <div class="ob-msg" id="obOutMsg"></div>
      </div>
      <div class="ob-field" id="obInWrap"><div class="label">Line-in (winkelmuziek / PLUS Radio) &mdash; optioneel</div>
        <div class="ob-dev"><select class="input" id="obIn" style="flex:1"></select>
          <button type="button" class="btn btn-sm btn-inline" style="width:auto" onclick="obTestIn()"><span class="mi">mic</span> Meet niveau</button></div>
        <div class="ob-dev" style="margin-top:8px"><div class="ob-meter"><i id="obMeter"></i></div><span id="obInMsg" class="help" style="margin:0">&mdash;</span></div>
      </div>
      <div class="ob-msg" id="obApplyMsg"></div>
    </div>
  </div>

  <div class="ob-step" data-step="plusradio">
    <div class="ob-card">
      <h2><span class="mi">radio</span> PLUS Radio (winkelmuziek)</h2>
      <p class="sub">Heb je een Streamit Lisa-streamer? Vul dan het IP in. Anders overslaan.</p>
      <label class="switch-row" style="margin-bottom:12px"><input type="checkbox" id="obLisaOn" checked> <span>Winkelmuziek van een Streamit Lisa-streamer uitlezen</span></label>
      <div class="ob-field"><div class="label">IP-adres streamer</div><input class="input" id="obLisaHost" placeholder="bijv. 10.0.0.50"></div>
    </div>
  </div>

  <div class="ob-step" data-step="spotify">
    <div class="ob-card">
      <h2><span class="mi">login</span> Spotify &amp; inloggen</h2>
      <p class="sub">Deze kun je nu overslaan en later instellen onder <b>Beheer</b>.</p>
      <ul class="help" style="margin:0;padding-left:18px;line-height:1.9">
        <li><b>Spotify</b>: koppel later het huis-account onder Beheer &rarr; Spotify.</li>
        <li><b>SSO / OIDC</b>: optioneel; standaard log je lokaal in met de beheerder die je net maakte.</li>
        <li>Alles is later aanpasbaar in <b>Beheer</b>.</li>
      </ul>
    </div>
  </div>

  <div class="ob-step" data-step="done">
    <div class="ob-card" style="text-align:center">
      <h2 style="justify-content:center"><span class="mi" style="color:var(--green)">check_circle</span> Klaar!</h2>
      <p class="sub">Het systeem is ingesteld. Je kunt nu inloggen en aan de slag.</p>
    </div>
  </div>

  <div class="ob-nav">
    <button type="button" class="btn btn-inline" style="width:auto" id="obPrev" onclick="obGo(-1)"><span class="mi">arrow_back</span> Vorige</button>
    <button type="button" class="ob-skip" id="obSkip" onclick="obGo(1,true)">Overslaan</button>
    <button type="button" class="btn btn-primary btn-inline" style="width:auto" id="obNext" onclick="obGo(1)">Volgende <span class="mi">arrow_forward</span></button>
  </div>
</div>
<script>
(function(){
  var steps=[].slice.call(document.querySelectorAll('.ob-step')).map(function(s){return s.dataset.step;});
  var i=0, devicesLoaded=false;
  var dots=document.getElementById('obDots');
  steps.forEach(function(){ var s=document.createElement('span'); dots.appendChild(s); });
  function show(){
    document.querySelectorAll('.ob-step').forEach(function(s){ s.classList.toggle('on',s.dataset.step===steps[i]); });
    [].forEach.call(dots.children,function(d,k){ d.className=(k<i?'done':(k===i?'on':'')); });
    document.getElementById('obPrev').style.visibility=i>0?'visible':'hidden';
    var last=i===steps.length-1;
    document.getElementById('obNext').innerHTML=last?'Voltooien <span class="mi">check</span>':'Volgende <span class="mi">arrow_forward</span>';
    var st=steps[i];
    document.getElementById('obSkip').style.display=(st==='audio'||st==='plusradio'||st==='spotify')?'inline':'none';
    if(st==='audio' && !devicesLoaded) obLoadDevices();
  }
  function msg(id,txt,ok){ var e=document.getElementById(id); if(!e)return; e.style.display='block'; e.style.color=ok?'#4b7a12':'#c62828'; e.textContent=txt; }
  window.obDemoToggle=function(){ var demo=document.getElementById('obDemo').checked; document.getElementById('obInWrap').style.opacity=demo?'.5':'1'; };
  window.obLoadDevices=function(){
    fetch('/api/audio/devices').then(function(r){return r.json();}).then(function(j){
      devicesLoaded=true;
      var out=document.getElementById('obOut'), inp=document.getElementById('obIn');
      out.innerHTML=''; inp.innerHTML='<option value="">— geen —</option>';
      (j.playback||[]).forEach(function(d){ var o=document.createElement('option'); o.value=d.hw; o.textContent=d.name+' (card '+d.card+')'; out.appendChild(o); });
      (j.capture||[]).forEach(function(d){ var o=document.createElement('option'); o.value=d.hw; o.textContent=d.name+' (card '+d.card+')'; inp.appendChild(o); });
      if(!(j.playback||[]).length){ var o=document.createElement('option'); o.value='default'; o.textContent='Standaard-uitgang'; out.appendChild(o); }
    }).catch(function(){ msg('obApplyMsg','Kon apparaten niet laden.',false); });
  };
  window.obTestOut=function(){
    var dev=document.getElementById('obOut').value||'default';
    msg('obOutMsg','Toon speelt\\u2026',true);
    fetch('/api/audio/test-out',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:dev})})
      .then(function(r){return r.json();}).then(function(j){ msg('obOutMsg',j.ok?'Toon afgespeeld \\u2014 hoorde je iets? Zo niet, kies een andere uitgang.':('Mislukt: '+(j.error||'')),j.ok); });
  };
  window.obTestIn=function(){
    var dev=document.getElementById('obIn').value; if(!dev){ msg('obInMsg','Kies eerst een line-in.',false); return; }
    document.getElementById('obInMsg').textContent='Meten (2s)\\u2026';
    fetch('/api/audio/test-in',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:dev})})
      .then(function(r){return r.json();}).then(function(j){
        if(!j.ok){ document.getElementById('obInMsg').textContent='Mislukt: '+(j.error||''); return; }
        var pct=Math.max(2,Math.min(100,Math.round((j.db+60)/60*100)));
        document.getElementById('obMeter').style.width=pct+'%';
        document.getElementById('obInMsg').textContent=(j.signal?'Signaal ok ':'Weinig/geen signaal ')+'('+j.db+' dB)';
      });
  };
  function cardOf(hw){ var m=(hw||'').match(/:(\\d+),/); return m?parseInt(m[1],10):0; }
  function saveAudio(){
    var demo=document.getElementById('obDemo').checked;
    var out=document.getElementById('obOut').value||'default';
    var inp=demo?'':document.getElementById('obIn').value;
    var pc=cardOf(out), cc=inp?cardOf(inp):pc;
    return fetch('/api/onboarding/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({demo_mode:demo})})
      .then(function(){ return fetch('/api/audio/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({play_card:pc,cap_card:cc})}); })
      .then(function(r){return r.json();}).then(function(j){ if(!j.ok && !j.staged) msg('obApplyMsg','Let op: audio-config niet toegepast ('+(j.error||'')+'). Je kunt dit later in Beheer regelen.',false); return true; })
      .catch(function(){ return true; });
  }
  function saveAdmin(){
    var u=document.getElementById('obUser'), p=document.getElementById('obPw');
    if(!u||!p) return Promise.resolve(true);
    if((u.value||'').length<1||(p.value||'').length<6){ msg('obAdminMsg','Vul een gebruikersnaam en wachtwoord (min. 6 tekens) in.',false); return Promise.resolve(false); }
    return fetch('/api/onboarding/admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value,display_name:document.getElementById('obDisp').value})})
      .then(function(r){return r.json();}).then(function(j){ if(!j.ok){ msg('obAdminMsg',j.error||'Mislukt.',false); return false; } return true; });
  }
  function saveBrand(){
    var b=(document.querySelector('input[name=obbrand]:checked')||{}).value||'plus';
    return fetch('/api/onboarding/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brand_theme:b,location_name:document.getElementById('obLoc').value})}).then(function(){return true;});
  }
  function savePlusradio(){
    var on=document.getElementById('obLisaOn').checked;
    return fetch('/api/onboarding/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lisa_enabled:on,lisa_host:document.getElementById('obLisaHost').value})}).then(function(){return true;});
  }
  window.obGo=function(dir,skip){
    if(dir>0 && !skip){
      var st=steps[i]; var chain=Promise.resolve(true);
      if(st==='admin') chain=saveAdmin();
      else if(st==='brand') chain=saveBrand();
      else if(st==='audio') chain=saveAudio();
      else if(st==='plusradio') chain=savePlusradio();
      chain.then(function(ok){ if(ok!==false) advance(dir); });
      return;
    }
    advance(dir);
  };
  function advance(dir){
    if(i===steps.length-1 && dir>0){
      fetch('/api/onboarding/finish',{method:'POST'}).then(function(){ location.href='/login'; });
      return;
    }
    i=Math.max(0,Math.min(steps.length-1,i+dir)); show();
  }
  show();
})();
</script>
"""

PRESETS_BODY = """
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
<style>
#editToggleBtn.active{background:var(--red);border-color:var(--red-dark);color:#fff}
/* Potlood-knop op tegel (alleen zichtbaar in bewerkmodus) → eigen bewerkpagina */
.card-item{position:relative}
.tile-edit-btn{position:absolute;top:8px;right:8px;width:40px;height:40px;display:none;align-items:center;justify-content:center;border-radius:50%;border:1px solid var(--stroke);background:#fff;color:var(--green-dark);text-decoration:none;box-shadow:var(--shadow-sm);z-index:2}
.tile-edit-btn:hover{background:#eaf4d8}
.tile-edit-btn .mi{font-size:20px;margin:0;vertical-align:-4px}
.edit-mode .tile-edit-btn{display:flex}
.new-preset-card{display:none!important}
.edit-mode .new-preset-card{display:block!important}
/* 'Nu aan het afspelen'-popup */
.np-backdrop{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(17,40,20,.60);z-index:10000;padding:20px}
.np-backdrop.show{display:flex}
.np-card{width:min(440px,94vw);background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.35);padding:28px 24px;text-align:center;border-top:6px solid var(--red)}
.np-label{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--fg3);margin-bottom:12px}
.np-icon .material-symbols-outlined{font-size:76px;color:var(--red)}
.np-name{font-size:24px;font-weight:800;color:var(--green-dark);margin:6px 0 22px;word-break:break-word;line-height:1.2}
.np-stop{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;min-height:66px;font-size:20px;font-weight:800;background:#c62828;color:#fff;border:none;border-radius:24px 24px 24px 4px;cursor:pointer;-webkit-tap-highlight-color:transparent}
.np-stop:active{background:#a51f1f}
.np-stop .mi{font-size:28px;vertical-align:-7px}
.np-hint{margin-top:14px;font-size:13px;color:var(--fg3)}
</style>
<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:18px">
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    <h1 style="margin:0">Presets</h1>
    <button class="btn btn-stop btn-inline btn-sm" onclick="stopPlayback()" style="width:auto"><span class="mi">stop_circle</span> Stop preset</button>
  </div>
  {% if admin %}
  <button id="editToggleBtn" class="btn btn-inline btn-sm"
          onclick="toggleEdit()" style="width:auto;gap:6px">
    <span class="mi">edit</span> Bewerken
  </button>
  {% endif %}
</div>
<div class="card-grid" id="presetGrid">{{ cards|safe }}</div>

<!-- Icon picker modal -->
<div id="iconPickerBackdrop" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.70);z-index:9998;align-items:center;justify-content:center;padding:20px">
  <div style="width:min(700px,96vw);max-height:85vh;display:flex;flex-direction:column;background:#fff;border:1px solid var(--stroke);border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.30);overflow:hidden">
    <div style="padding:16px 20px;border-bottom:1px solid var(--stroke-light);display:flex;gap:10px;align-items:center">
      <input id="iconSearch" class="input" placeholder="Zoek icon… (bijv. campaign, mic, warning)" style="flex:1"
             oninput="filterIcons(this.value)">
      <button class="btn btn-inline btn-sm" onclick="closeIconPicker()" style="width:auto;flex-shrink:0"><span class="mi">close</span> Sluiten</button>
    </div>
    <div id="iconGrid" style="overflow-y:auto;padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(80px,1fr));gap:8px"></div>
  </div>
</div>

<div id="nowPlaying" class="np-backdrop">
  <div class="np-card">
    <div class="np-label">Nu aan het afspelen</div>
    <div id="npIcon" class="np-icon"><span class="material-symbols-outlined">campaign</span></div>
    <div id="npName" class="np-name">Preset</div>
    <button class="np-stop" onclick="stopPlayback()"><span class="mi">stop_circle</span> Stop preset</button>
    <div class="np-hint">Verkeerde gekozen? Tik op stop.</div>
  </div>
</div>

<script>
const PRESET_META = {{ preset_meta|safe }};
const SHOW_PLAYING_POPUP = {{ 'true' if show_popup else 'false' }};
let _npActive=false, _npHideTimer=null, _npEs=null, _npSeen=false, _npShownAt=0, _npPoll=null;
const NP_MAX_WAIT_MS=8000;   // popup nooit langer laten staan als er nóóit geluid kwam

function showNowPlaying(n){
  const m=PRESET_META[n]||{name:'Preset '+n,icon:''};
  document.getElementById('npName').textContent=m.name;
  document.getElementById('npIcon').innerHTML='<span class="material-symbols-outlined">'+(m.icon||'campaign')+'</span>';
  document.getElementById('nowPlaying').classList.add('show');
  _npActive=true; _npSeen=false; _npShownAt=Date.now();
  if(_npHideTimer){clearTimeout(_npHideTimer);_npHideTimer=null;}
  npWatch();
  // Vangnet: pol de status ook los van de SSE-stream, zodat een weggevallen
  // stream de popup niet kan laten hangen na afloop van de preset.
  if(_npPoll){clearInterval(_npPoll);}
  _npPoll=setInterval(npPollStatus,1500);
}
function hideNowPlaying(){
  _npActive=false;
  if(_npHideTimer){clearTimeout(_npHideTimer);_npHideTimer=null;}
  if(_npPoll){clearInterval(_npPoll);_npPoll=null;}
  document.getElementById('nowPlaying').classList.remove('show');
}
function npApplyState(d){
  if(!_npActive) return;
  if(d && d.playing){
    _npSeen=true;                                   // preset speelt écht
    if(_npHideTimer){clearTimeout(_npHideTimer);_npHideTimer=null;}
    return;
  }
  // Er speelt (even) niets. Pas verbergen nadat we geluid hebben gezien —
  // presets bestaan uit preroll+preset+outro met korte gaten; 2s debounce
  // voorkomt flikkeren tussen de segmenten door.
  if(_npSeen){
    if(!_npHideTimer){
      _npHideTimer=setTimeout(function(){ if(_npActive) hideNowPlaying(); }, 2000);
    }
  } else if(Date.now()-_npShownAt > NP_MAX_WAIT_MS){
    hideNowPlaying();                               // nooit geluid gedetecteerd → toch sluiten
  }
}
function npPollStatus(){
  if(!_npActive) return;
  fetch("{{ url_for('api_status') }}",{cache:'no-store'}).then(r=>r.json()).then(npApplyState).catch(()=>{});
}
function npWatch(){
  if(_npEs) return;
  _npEs=new EventSource("{{ url_for('events') }}");
  _npEs.onmessage=function(e){ try{ npApplyState(JSON.parse(e.data)); }catch(_){} };
  _npEs.onerror=function(){ try{_npEs.close();}catch(_){} _npEs=null; if(_npActive) setTimeout(npWatch,1500); };
}
function playPreset(n){
  fetch("{{ url_for('api_play_preset',preset_id=0) }}".replace('/0','/'+n),{method:'POST'}).catch(()=>{});
  if(SHOW_PLAYING_POPUP) showNowPlaying(n);
}
function stopPlayback(){
  fetch("{{ url_for('api_stop') }}",{method:'POST'}).catch(()=>{});
  hideNowPlaying();
}
window.addEventListener('load',()=>{if(typeof ensureLock==="function")ensureLock('presets');});

// ── Bewerken toggle ──
let _editMode = false;
function toggleEdit(){
  _editMode = !_editMode;
  const grid = document.getElementById('presetGrid');
  const btn  = document.getElementById('editToggleBtn');
  if(_editMode){
    grid.classList.add('edit-mode');
    btn.classList.add('active');
    btn.innerHTML = '<span class="mi">edit_off</span> Bewerken uit';
    try{ localStorage.setItem('omroep_edit_mode','1'); }catch(_){}
  } else {
    grid.classList.remove('edit-mode');
    btn.classList.remove('active');
    btn.innerHTML = '<span class="mi">edit</span> Bewerken';
    try{ localStorage.removeItem('omroep_edit_mode'); }catch(_){}
  }
}
// Herstel vorige staat na pagina-reload
window.addEventListener('load', function(){
  try{ if(localStorage.getItem('omroep_edit_mode')==='1') toggleEdit(); }catch(_){}
});

// ── Icon picker ──
const ICONS=[
  "campaign","mic","volume_up","record_voice_over","speaker","queue_music","music_note","headphones",
  "alarm","schedule","timer","event","today","calendar_month","notifications","notification_important",
  "warning","error","info","help","priority_high","report","new_releases","flag",
  "person","group","people","badge","supervisor_account","engineering","support_agent","manage_accounts",
  "store","local_grocery_store","shopping_cart","shopping_basket","storefront","local_mall","point_of_sale",
  "local_bar","liquor","wine_bar","sports_bar","local_cafe","coffee","bakery_dining","restaurant",
  "recycling","delete","cleaning_services","build","handyman","construction","home_repair_service",
  "directions_car","local_shipping","delivery_dining","two_wheeler","electric_car","agriculture",
  "lock","lock_open","security","verified","shield","key","vpn_key","fingerprint",
  "phone","phone_in_talk","call","contact_phone","headset_mic","support",
  "bolt","power","electrical_services","outlet","settings","tune","device_hub",
  "star","thumb_up","celebration","cake","favorite","emoji_events","workspace_premium",
  "close","check","done","add","remove","search","refresh","sync","autorenew",
  "arrow_forward","arrow_back","arrow_upward","arrow_downward","open_in_new","link",
  "bread","local_pizza","fastfood","lunch_dining","dinner_dining","brunch_dining",
  "freezing","thermostat","ac_unit","water_drop","opacity","light_mode","dark_mode",
  "monetization_on","euro","attach_money","payments","receipt","savings","account_balance",
  "inventory","inventory_2","warehouse","shelves","category","label","sell","price_tag",
  "trolley","forklift","pallet","conveyor_belt","factory","precision_manufacturing"
];
let _pickerPresetId = null;

function openIconPicker(pid){
  _pickerPresetId = pid;
  document.getElementById('iconSearch').value='';
  renderIconGrid(ICONS);
  const bd=document.getElementById('iconPickerBackdrop');
  bd.style.display='flex';
  document.getElementById('iconSearch').focus();
}
function closeIconPicker(){
  document.getElementById('iconPickerBackdrop').style.display='none';
  _pickerPresetId=null;
}
function filterIcons(q){
  q=(q||'').toLowerCase().trim();
  renderIconGrid(q?ICONS.filter(ic=>ic.includes(q)):ICONS);
}
function renderIconGrid(list){
  const g=document.getElementById('iconGrid');
  g.innerHTML='';
  list.forEach(ic=>{
    const d=document.createElement('div');
    d.style.cssText='display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 6px;border-radius:10px;border:1px solid var(--stroke-light);background:#f4f6f1;cursor:pointer;transition:background .12s';
    d.onmouseenter=()=>d.style.background='#eaf4d8';
    d.onmouseleave=()=>d.style.background='#f4f6f1';
    d.innerHTML='<span class="material-symbols-outlined" style="font-size:30px;color:#80bd1d">'+ic+'</span>'
      +'<span style="font-size:10px;color:var(--fg3);text-align:center;word-break:break-all;line-height:1.2">'+ic+'</span>';
    d.onclick=()=>selectIcon(ic);
    g.appendChild(d);
  });
  if(!list.length){g.innerHTML='<div style="color:var(--fg3);grid-column:1/-1;text-align:center;padding:30px">Geen resultaten</div>';}
}
function selectIcon(ic){
  if(_pickerPresetId===null)return;
  const inp=document.getElementById('icon_input_'+_pickerPresetId);
  const prv=document.getElementById('icon_preview_'+_pickerPresetId);
  const hid=document.getElementById('icon_hidden_'+_pickerPresetId);
  if(inp)inp.value=ic;
  if(prv)prv.textContent=ic;
  if(hid)hid.value=ic;
  closeIconPicker();
}
document.getElementById('iconPickerBackdrop').addEventListener('click',function(e){
  if(e.target===this)closeIconPicker();
});
document.addEventListener('keydown',function(e){
  if(e.key==='Escape')closeIconPicker();
});
</script>
"""

PRESET_EDIT_BODY = """
<style>
.pe-preview{display:flex;align-items:center;gap:16px}
.pe-preview .material-symbols-outlined{font-size:60px;color:var(--red)}
.ip-backdrop{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(17,40,20,.55);z-index:9998;padding:16px}
.ip-backdrop.show{display:flex}
.ip-modal{width:min(680px,96vw);max-height:82vh;display:flex;flex-direction:column;background:#fff;border:1px solid var(--stroke);border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.30);overflow:hidden}
.ip-grid{overflow-y:auto;padding:14px;display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:8px}
.ip-cell{display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 6px;border-radius:10px;border:1px solid var(--stroke-light);background:#f4f6f1;cursor:pointer}
.ip-cell:hover{background:#eaf4d8}
.ip-cell .material-symbols-outlined{font-size:30px;color:#80bd1d}
.ip-cell small{font-size:10px;color:var(--fg3);text-align:center;word-break:break-all;line-height:1.2}
</style>

<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px">
  <a class="btn btn-inline btn-sm" href="{{ url_for('presets_page') }}" style="width:auto"><span class="mi">arrow_back</span> Terug naar presets</a>
  <h1 style="margin:0">Preset bewerken</h1>
</div>

{% if ok %}<div class="alert alert-ok"><span class="mi mi-sm">check</span> Wijzigingen opgeslagen.</div>{% endif %}

<div style="max-width:620px">

  <div class="form-card">
    <div class="pe-preview">
      <span class="material-symbols-outlined" id="pePreview">{{ icon or 'campaign' }}</span>
      <div>
        <div class="label" style="margin:0">Preset #{{ pid }}</div>
        <div id="peName" style="font-size:20px;font-weight:800;color:var(--green-dark)">{{ nm }}</div>
      </div>
    </div>
  </div>

  <form method="post" action="{{ url_for('save_preset_all', preset_id=pid) }}">
    <div class="form-card">
      <h3>Algemeen</h3>
      <div class="label">Naam</div>
      <input class="input" name="name" id="peNameInput" value="{{ nm }}" oninput="document.getElementById('peName').textContent=this.value||'Preset {{ pid }}'" style="margin-bottom:14px">

      <div class="label">Icoon</div>
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:14px">
        <span class="material-symbols-outlined" id="peIconPrev" style="font-size:34px;color:#80bd1d;min-width:40px;text-align:center">{{ icon }}</span>
        <input class="input" name="icon" id="peIconInput" placeholder="bijv. campaign" value="{{ icon }}"
               oninput="peIconChanged(this.value)" style="flex:1">
        <button class="btn btn-sm" type="button" onclick="peOpenPicker()" style="width:auto"><span class="mi">search</span> Zoeken</button>
      </div>

      <div class="label">Gain % (0&ndash;200)</div>
      <input class="input" type="number" name="gain" min="0" max="200" value="{{ gain }}" style="max-width:160px">
    </div>

    <div class="form-card">
      <h3>Opties</h3>
      <label class="switch-row"><input type="checkbox" name="admin_only" value="1" {{ 'checked' if admin_only }}> <span>Alleen zichtbaar voor admin</span></label>
      <label class="switch-row"><input type="checkbox" name="preroll_enabled" value="1" {{ 'checked' if preroll_on }}> <span>Preroll (intro) afspelen</span></label>
      <label class="switch-row"><input type="checkbox" name="outro_enabled" value="1" {{ 'checked' if outro_on }}> <span>Outro afspelen</span></label>
    </div>

    <button class="btn btn-primary btn-inline" type="submit" style="min-width:180px"><span class="mi">save</span> Wijzigingen opslaan</button>
  </form>

  <div class="form-card" style="margin-top:16px">
    <h3>Audiobestand vervangen</h3>
    <form method="post" action="{{ url_for('upload_preset', preset_id=pid) }}" enctype="multipart/form-data">
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <input class="input" type="file" name="file" accept=".wav,.mp3,.m4a" required style="flex:1;min-width:200px">
        <button class="btn btn-inline" type="submit" style="width:auto"><span class="mi">upload</span> Vervangen</button>
      </div>
    </form>
  </div>

  <div class="form-card">
    <h3 style="color:#c62828">Verwijderen</h3>
    <p class="help" style="margin-bottom:10px">Dit verwijdert de preset en het audiobestand definitief.</p>
    <form method="post" action="{{ url_for('delete_preset', preset_id=pid) }}" onsubmit="return confirm('Preset {{ pid }} definitief verwijderen?')">
      <button class="btn btn-danger btn-inline" type="submit" style="width:auto"><span class="mi">delete</span> Preset verwijderen</button>
    </form>
  </div>
</div>

<div id="peIconPicker" class="ip-backdrop" onclick="if(event.target===this)peClosePicker()">
  <div class="ip-modal">
    <div style="padding:14px 18px;border-bottom:1px solid var(--stroke-light);display:flex;gap:10px;align-items:center">
      <input id="peIconSearch" class="input" placeholder="Zoek icoon… (bijv. campaign, store, warning)" oninput="peRenderIcons(this.value)" style="flex:1">
      <button class="btn btn-inline btn-sm" type="button" onclick="peClosePicker()" style="width:auto"><span class="mi">close</span> Sluiten</button>
    </div>
    <div id="peIconGrid" class="ip-grid"></div>
  </div>
</div>

<script>
const PE_ICONS = {{ icons_json|safe }};
function peIconChanged(v){ document.getElementById('peIconPrev').textContent=v; document.getElementById('pePreview').textContent=v||'campaign'; }
function peOpenPicker(){ document.getElementById('peIconSearch').value=''; peRenderIcons(''); document.getElementById('peIconPicker').classList.add('show'); document.getElementById('peIconSearch').focus(); }
function peClosePicker(){ document.getElementById('peIconPicker').classList.remove('show'); }
function peRenderIcons(q){
  q=(q||'').toLowerCase().trim();
  const list=q?PE_ICONS.filter(function(ic){return ic.includes(q);}):PE_ICONS;
  const g=document.getElementById('peIconGrid'); g.innerHTML='';
  list.forEach(function(ic){
    const d=document.createElement('div'); d.className='ip-cell';
    d.innerHTML='<span class="material-symbols-outlined">'+ic+'</span><small>'+ic+'</small>';
    d.onclick=function(){ document.getElementById('peIconInput').value=ic; peIconChanged(ic); peClosePicker(); };
    g.appendChild(d);
  });
  if(!list.length){ g.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--fg3)">Geen resultaten</div>'; }
}
document.addEventListener('keydown',function(e){ if(e.key==='Escape') peClosePicker(); });
</script>
"""

TTS_BODY = """
<style>
.tts-pop-backdrop{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(17,40,20,.60);z-index:10000;padding:20px}
.tts-pop-backdrop.show{display:flex}
.tts-pop{width:min(460px,94vw);background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.35);padding:26px 24px;text-align:center;border-top:6px solid var(--red)}
.tts-pop.warn{border-top-color:#c62828}
.tts-pop-label{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--fg3);margin-bottom:14px}
.tts-pop .mi-big{font-family:'Material Symbols Outlined';font-size:64px;color:var(--red)}
.tts-pop.warn .mi-big{color:#c62828}
.tts-pop-text{font-size:17px;font-weight:600;color:var(--green-dark);margin:6px 0 20px;max-height:190px;overflow:auto;line-height:1.45;word-break:break-word;text-align:left;background:#f4f6f1;border-radius:10px;padding:12px 14px}
.tts-pop-stop{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;min-height:64px;font-size:20px;font-weight:800;background:#c62828;color:#fff;border:none;border-radius:24px 24px 24px 4px;cursor:pointer}
.tts-pop-stop:active{background:#a51f1f}
.tts-pop-stop .mi{font-size:26px;vertical-align:-6px}
.tts-pop-word{display:inline-block;background:#fdeceb;color:#c62828;border:1px solid #f1b7b0;border-radius:8px;padding:5px 14px;font-weight:800;margin:6px 0 18px;font-size:18px}
.tts-pop-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:52px;padding:0 26px;font-size:16px;font-weight:700;background:var(--red);color:#fff;border:none;border-radius:24px 24px 24px 4px;cursor:pointer}
#btnSpeak:disabled,#btnGen:disabled{opacity:.45;cursor:not-allowed;box-shadow:none}
</style>

<div id="ttsNow" class="tts-pop-backdrop">
  <div class="tts-pop">
    <div class="tts-pop-label">Nu aan het afspelen</div>
    <div class="tts-pop-text" id="ttsNowText"></div>
    <button class="tts-pop-stop" onclick="stopPlayback()"><span class="mi">stop_circle</span> Stop omroep</button>
    <div style="margin-top:12px;font-size:13px;color:var(--fg3)">Verkeerd? Tik op stop.</div>
  </div>
</div>
<div id="ttsBlock" class="tts-pop-backdrop">
  <div class="tts-pop warn">
    <div class="tts-pop-label">Niet toegestaan</div>
    <span class="mi-big">block</span>
    <div style="margin:10px 0 4px;color:var(--fg2)">Dit woord mag niet omgeroepen worden:</div>
    <div class="tts-pop-word" id="ttsBlockWord">—</div>
    <div><button class="tts-pop-btn" onclick="ttsBlockClose()"><span class="mi">check</span> Begrepen</button></div>
  </div>
</div>

<h1>Text to Speech</h1>
<div class="row"><div class="col" style="max-width:680px">
  <div class="label">Tekst</div>
  <textarea class="input" id="ttsText" placeholder="Typ de omroeptekst hier..." oninput="checkBlocked()">{{ tts_prefill }}</textarea>
  {% if quick_words %}
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;align-items:center">
    <span class="help" style="margin-right:2px">Snel invoegen:</span>
    {% for w in quick_words %}<button type="button" class="btn btn-sm btn-inline" style="width:auto" onclick="ttsInsert('{{ w }}')"><span class="mi mi-sm">add</span> {{ w }}</button>{% endfor %}
  </div>
  {% endif %}
  <div id="ttsBlockedBanner" class="alert alert-err" style="display:none;margin-top:10px"></div>
  <div style="height:10px"></div>

  <div style="margin-bottom:10px">
    <div class="label">Stem</div>
    <select class="input" id="ttsVoice">{{ opts|safe }}</select>
  </div>
  <input type="hidden" id="ttsRate" value="165">

  <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:14px">
    <input type="checkbox" id="ttsPreroll" {% if settings.tts_preroll_enabled %}checked{% endif %}>
    Preroll afspelen
  </label>
  <label style="display:flex;align-items:center;gap:8px;margin-bottom:16px;font-size:14px">
    <input type="checkbox" id="ttsOutro" {% if settings.tts_outro_enabled %}checked{% endif %} {% if not outro_exists %}disabled{% endif %}>
    Outro afspelen{% if not outro_exists %} <span class="help">(geen outro geüpload)</span>{% endif %}
  </label>

  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px">
    <button class="btn btn-primary btn-inline" id="btnSpeak" onclick="ttsSpeak()"><span class="mi">play_arrow</span> Spreek af</button>
    {% if can_generate %}
    <button class="btn btn-gold btn-inline" id="btnGen" onclick="ttsGenerate()" title="Genereer audio zonder af te spelen"><span class="mi">download</span> Genereren</button>
    {% endif %}
    <button class="btn btn-stop btn-inline" style="width:auto;padding:11px 20px" onclick="stopPlayback()"><span class="mi">stop_circle</span> Stop</button>
  </div>

  <div id="ttsStatus" style="display:none;margin-bottom:12px">
    <div class="alert alert-warn" id="ttsStatusMsg">Text to Speech wordt gegenereerd…</div>
  </div>

  <div id="ttsActionsPanel" style="display:none" class="tts-actions-panel">
    <div class="label" style="color:var(--gold);margin-bottom:12px"><span class="mi">check_circle</span> Opname gereed</div>

    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
      <a id="dlWav" class="btn btn-inline btn-sm" style="width:auto;text-decoration:none" download="tts_opname.wav"><span class="mi">download</span> WAV</a>
      <a id="dlMp3" class="btn btn-inline btn-sm" style="width:auto;text-decoration:none" download="tts_opname.mp3"><span class="mi">download</span> MP3</a>
    </div>

    {% if can_save_preset %}
    <hr style="margin:10px 0 14px">
    <div class="label" style="margin-bottom:8px">Opslaan als preset</div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <input class="input" id="presetName" placeholder="Naam voor de preset" style="flex:1;min-width:160px">
      <button class="btn btn-inline btn-sm" style="width:auto" onclick="savePreset()"><span class="mi">save</span> Opslaan als preset</button>
    </div>
    <div id="presetMsg" style="display:none;margin-top:10px;font-size:13px"></div>
    {% endif %}
  </div>

</div></div>

<script>
const TTS_BLOCKED = {{ blocked_json|safe }};
const TTS_SHOW_POPUP = {{ 'true' if show_popup else 'false' }};
let _ttsToken=null,_pollTimer=null,_wasBlocked=false;
let _ttsNpActive=false,_ttsNpSeen=false,_ttsNpTimer=null,_ttsEs=null;
function _norm(t){
  t=(''+t).toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
  var L={'0':'o','1':'i','3':'e','4':'a','5':'s','6':'g','7':'t','8':'b','9':'g','@':'a','$':'s','!':'i','|':'l','(':'c'};
  var o=''; for(var i=0;i<t.length;i++){o+=(L[t[i]]||t[i]);}
  return o.replace(/[^a-z]/g,'').replace(/(.)\\1+/g,'$1');
}
function blockedHit(text){
  var toks=(''+text).split(/[^0-9A-Za-zÀ-ÿ]+/);
  var NB=[]; for(var i=0;i<TTS_BLOCKED.length;i++){var b=_norm(TTS_BLOCKED[i]); if(b)NB.push([TTS_BLOCKED[i],b]);}
  for(var j=0;j<toks.length;j++){
    var nt=_norm(toks[j]); if(!nt)continue;
    for(var k=0;k<NB.length;k++){
      if(nt===NB[k][1]) return NB[k][0];
      if(NB[k][1].length>=5 && nt.indexOf(NB[k][1])>=0) return NB[k][0];
    }
  }
  return null;
}
function ttsInsert(w){
  var ta=document.getElementById('ttsText');
  var s=(ta.selectionStart!=null)?ta.selectionStart:ta.value.length;
  var e=(ta.selectionEnd!=null)?ta.selectionEnd:ta.value.length;
  var ins=w+' ';
  ta.value=ta.value.slice(0,s)+ins+ta.value.slice(e);
  var pos=s+ins.length;
  ta.focus(); try{ta.setSelectionRange(pos,pos);}catch(_){}
  checkBlocked();
}
function ttsShowBlock(word){ document.getElementById('ttsBlockWord').textContent=word||'ongepast woord'; document.getElementById('ttsBlock').classList.add('show'); }
function ttsBlockClose(){ document.getElementById('ttsBlock').classList.remove('show'); }
function checkBlocked(){
  var hit=blockedHit(document.getElementById('ttsText').value||'');
  var banner=document.getElementById('ttsBlockedBanner');
  var speak=document.getElementById('btnSpeak'), gen=document.getElementById('btnGen');
  if(hit){
    if(banner){banner.style.display='block'; banner.innerHTML='<span class="mi mi-sm">block</span> Geblokkeerd woord: \\''+hit+'\\' — pas de tekst aan om te kunnen omroepen.';}
    if(speak)speak.disabled=true; if(gen)gen.disabled=true;
    if(!_wasBlocked) ttsShowBlock(hit);
    _wasBlocked=true;
  } else {
    if(banner)banner.style.display='none';
    if(speak)speak.disabled=false; if(gen)gen.disabled=false;
    _wasBlocked=false;
  }
}
function ttsShowNow(text){
  if(!TTS_SHOW_POPUP) return;
  document.getElementById('ttsNowText').textContent=text;
  document.getElementById('ttsNow').classList.add('show');
  _ttsNpActive=true;_ttsNpSeen=false; ttsNpWatch();
}
function ttsHideNow(){ _ttsNpActive=false; document.getElementById('ttsNow').classList.remove('show'); if(_ttsNpTimer){clearTimeout(_ttsNpTimer);_ttsNpTimer=null;} }
function ttsNpWatch(){
  if(_ttsEs) return;
  _ttsEs=new EventSource("{{ url_for('events') }}");
  _ttsEs.onmessage=function(e){
    if(!_ttsNpActive) return;
    try{ var d=JSON.parse(e.data);
      if(d.playing){ _ttsNpSeen=true; if(_ttsNpTimer){clearTimeout(_ttsNpTimer);_ttsNpTimer=null;} }
      else if(_ttsNpSeen && !_ttsNpTimer){ _ttsNpTimer=setTimeout(function(){ if(_ttsNpActive) ttsHideNow(); },1500); }
    }catch(_){}
  };
  _ttsEs.onerror=function(){ try{_ttsEs.close();}catch(_){} _ttsEs=null; if(_ttsNpActive) setTimeout(ttsNpWatch,1500); };
}
function ttsGetPayload(){
  const text=(document.getElementById('ttsText').value||'').trim();
  if(!text){alert('Voer eerst een tekst in.');return null;}
  const outroEl=document.getElementById('ttsOutro');
  return{text,voice:document.getElementById('ttsVoice').value||'',
    rate:parseInt(document.getElementById('ttsRate').value||'165',10),
    preroll:document.getElementById('ttsPreroll').checked,
    outro:outroEl?outroEl.checked:false};
}
function ttsSetStatus(msg,show){
  document.getElementById('ttsStatus').style.display=show?'block':'none';
  if(msg)document.getElementById('ttsStatusMsg').textContent=msg;
}
function ttsHideActions(){
  _ttsToken=null;if(_pollTimer){clearInterval(_pollTimer);_pollTimer=null;}
  document.getElementById('ttsActionsPanel').style.display='none';
  const pm=document.getElementById('presetMsg');if(pm)pm.style.display='none';
}
function ttsShowActions(token){
  _ttsToken=token;
  document.getElementById('dlWav').href='/api/tts/download/'+token+'/wav';
  document.getElementById('dlMp3').href='/api/tts/download/'+token+'/mp3';
  document.getElementById('ttsActionsPanel').style.display='block';
  const ni=document.getElementById('presetName');
  if(ni&&!ni.value)ni.value=(document.getElementById('ttsText').value||'').substring(0,50);
}
function ttsPollReady(token,onReady){
  if(_pollTimer)clearInterval(_pollTimer);
  _pollTimer=setInterval(()=>{
    fetch('/api/tts/status/'+token,{cache:'no-store'}).then(r=>r.json()).then(j=>{
      if(j.ready){clearInterval(_pollTimer);_pollTimer=null;onReady();}
    }).catch(()=>{});
  },700);
}
function ttsSpeak(){
  ttsHideActions();const payload=ttsGetPayload();if(!payload)return;
  var hit=blockedHit(payload.text);
  if(hit){ ttsShowBlock(hit); return; }
  fetch("{{ url_for('api_tts_say') }}",{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
    .then(function(r){return r.json().catch(function(){return {};});})
    .then(function(j){ if(j && j.blocked){ ttsShowBlock(j.word||''); } else { ttsShowNow(payload.text); } })
    .catch(function(){ ttsShowNow(payload.text); });
}
function ttsGenerate(){
  ttsHideActions();const payload=ttsGetPayload();if(!payload)return;
  var hit=blockedHit(payload.text);
  if(hit){ ttsShowBlock(hit); return; }
  ttsSetStatus('Text to Speech wordt gegenereerd…',true);
  fetch("{{ url_for('api_tts_preview') }}",{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
    .then(r=>r.json()).then(j=>{
      if(j.blocked){ttsSetStatus('',false);ttsShowBlock(j.word||'');return;}
      if(j.token){ttsPollReady(j.token,()=>{ttsSetStatus('',false);ttsShowActions(j.token);});}
      else{ttsSetStatus('Genereren mislukt.',true);setTimeout(()=>ttsSetStatus('',false),3000);}
    }).catch(()=>{ttsSetStatus('',false);});
}
function stopPlayback(){fetch("{{ url_for('api_stop') }}",{method:'POST'}); ttsHideNow();}
function savePreset(){
  if(!_ttsToken){alert('Genereer eerst een opname.');return;}
  const name=(document.getElementById('presetName').value||'').trim();
  const pm=document.getElementById('presetMsg');pm.style.display='none';
  fetch('/api/tts/save_preset/'+_ttsToken,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})})
    .then(r=>r.json()).then(j=>{
      pm.style.display='block';
      pm.style.color=j.ok?'#7dffaa':'#ffaaaa';
      pm.textContent=j.ok?'Opgeslagen als preset '+j.preset_id+' — "'+j.name+'"':''+(j.error||'Onbekende fout');
    }).catch(()=>{pm.style.display='block';pm.style.color='#ffaaaa';pm.textContent='Verbindingsfout';});
}
window.addEventListener('load',()=>{if(typeof ensureLock==="function")ensureLock('tts'); checkBlocked();});
</script>
"""

GEBRUIKERS_BODY = """
<style>
.user-search-wrap{position:relative;max-width:420px;margin-bottom:16px}
.user-search-wrap .mi{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--fg3)}
#userSearch{width:100%;padding:12px 14px 12px 40px;border:1px solid var(--stroke);border-radius:999px;font:inherit;font-size:15px;background:#fff;color:var(--fg)}
#userSearch:focus{outline:none;border-color:var(--green-dark);box-shadow:0 0 0 2px rgba(17,80,19,.12)}
.user-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.user-card{border:1px solid var(--stroke);border-radius:var(--radius-sm);background:#fff;box-shadow:var(--shadow-sm);padding:16px;display:flex;flex-direction:column;gap:10px}
.uc-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.uc-name{font-weight:800;color:var(--green-dark);font-size:16px;word-break:break-word}
.uc-user{font-size:12px;color:var(--fg3);word-break:break-all}
.uc-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.ugroup{display:inline-block;padding:2px 9px;border-radius:999px;background:#eaf4d8;color:#4b7a12;border:1px solid #cbe3a0;font-size:11px;font-weight:600}
.uc-rights{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:var(--fg2);padding:8px 0;border-top:1px solid var(--stroke-light);border-bottom:1px solid var(--stroke-light)}
.uc-foot{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.uc-actions{display:flex;gap:6px}
#userNoResults{display:none;color:var(--fg3);padding:20px 4px}
</style>
<h1>Gebruikers &amp; Rechten</h1>
<p class="help" style="margin-bottom:14px">Lokale gebruikers worden hier aangemaakt. SSO-gebruikers worden automatisch toegevoegd bij de eerste login (alleen <span class="mono">radio-</span>groepen tellen mee).</p>
<div class="user-search-wrap">
  <span class="mi">search</span>
  <input id="userSearch" type="search" placeholder="Zoek op naam, gebruikersnaam of groep…" oninput="filterUsers()">
</div>
<div class="user-grid" id="userGrid">{{ rows|safe }}</div>
<div id="userNoResults">Geen gebruikers gevonden.</div>
<script>
function filterUsers(){
  var q=(document.getElementById('userSearch').value||'').toLowerCase().trim();
  var n=0;
  document.querySelectorAll('#userGrid .user-card').forEach(function(c){
    var show=!q||(c.dataset.search||'').indexOf(q)>=0;
    c.style.display=show?'':'none'; if(show)n++;
  });
  document.getElementById('userNoResults').style.display=n?'none':'block';
}
</script>

<h2>Nieuwe lokale gebruiker aanmaken</h2>
<div class="card-item" style="max-width:540px">
  <form method="post" action="{{ url_for('create_user') }}">
    {% if create_err %}<div class="alert alert-err">{{ create_err }}</div>{% endif %}
    {% if create_ok  %}<div class="alert alert-ok">Gebruiker aangemaakt.</div>{% endif %}
    <div class="row">
      <div class="col">
        <div class="label">Gebruikersnaam</div>
        <input class="input" name="username" required placeholder="gebruikersnaam" autocomplete="off">
      </div>
      <div class="col">
        <div class="label">Weergavenaam</div>
        <input class="input" name="display_name" placeholder="Volledige naam">
      </div>
    </div>
    <div style="height:10px"></div>
    <div class="row">
      <div class="col">
        <div class="label">Wachtwoord</div>
        <input class="input" name="password" type="password" required placeholder="min. 6 tekens">
      </div>
      <div class="col">
        <div class="label">Rol</div>
        <select class="input" name="role">
          <option value="admin">Admin</option>
          <option value="operator">Operator</option>
          <option value="user" selected>Gebruiker</option>
        </select>
      </div>
    </div>
    <div style="height:12px"></div>
    <button class="btn btn-inline" type="submit">Aanmaken</button>
  </form>
</div>
"""

OIDC_BODY = """
<h1>OpenID Connect configuratie</h1>
<p class="help" style="margin-bottom:16px">Configureer hier een externe identity provider (bijv. Authentik, Keycloak, Azure AD).</p>

{% if saved %}<div class="alert alert-ok">Instellingen opgeslagen.</div>{% endif %}
{% if test_result %}<div class="alert {{ 'alert-ok' if test_ok else 'alert-err' }}">{{ test_result }}</div>{% endif %}

<div style="max-width:680px">
<form method="post" action="{{ url_for('save_oidc') }}">
  <div class="card-item" style="margin-bottom:16px">
    <h3 style="margin-top:0">Provider</h3>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:14px;font-weight:600">
      <input type="checkbox" name="oidc_enabled" value="1" {% if cfg.enabled %}checked{% endif %}>
      OIDC inschakelen
    </label>
    <div class="label">Naam (weergave op loginpagina)</div>
    <input class="input" name="provider_name" value="{{ cfg.provider_name }}" placeholder="Authentik" style="margin-bottom:10px">
    <div class="label">Discovery URL</div>
    <input class="input" name="discovery_url" value="{{ cfg.discovery_url }}"
           placeholder="https://auth.voorbeeld.nl/application/o/mijn-app/.well-known/openid-configuration"
           style="margin-bottom:6px">
  </div>

  <div class="card-item" style="margin-bottom:16px">
    <h3 style="margin-top:0">Client credentials</h3>
    <div class="row">
      <div class="col">
        <div class="label">Client ID</div>
        <input class="input" name="client_id" value="{{ cfg.client_id }}" placeholder="client-id">
      </div>
      <div class="col">
        <div class="label">Client Secret</div>
        <input class="input" name="client_secret" type="password" value="{{ cfg.client_secret }}" placeholder="geheim">
      </div>
    </div>
    <div style="height:10px"></div>
    <div class="label">Redirect URI</div>
    <input class="input" name="redirect_uri" value="{{ cfg.redirect_uri or redirect_uri_default }}"
           placeholder="{{ redirect_uri_default }}">
    <div style="height:10px"></div>
    <div class="label">Scopes</div>
    <input class="input" name="scope" value="{{ cfg.scope }}" placeholder="openid email profile groups">
  </div>

  <div class="card-item" style="margin-bottom:16px">
    <h3 style="margin-top:0">Groepen → Rollen</h3>
    <div class="row">
      <div class="col">
        <div class="label">Groepsclaim</div>
        <input class="input" name="group_claim" value="{{ cfg.group_claim }}" placeholder="groups">
      </div>
    </div>
    <div style="height:10px"></div>
    <div class="row">
      <div class="col"><div class="label">Admin-groep</div><input class="input" name="group_admin" value="{{ cfg.group_admin }}"></div>
      <div class="col"><div class="label">Operator-groep</div><input class="input" name="group_operator" value="{{ cfg.group_operator }}"></div>
      <div class="col"><div class="label">Gebruiker-groep</div><input class="input" name="group_user" value="{{ cfg.group_user }}"></div>
    </div>
  </div>

  <div style="display:flex;gap:10px">
    <button class="btn btn-inline" type="submit">Opslaan</button>
    <button class="btn btn-inline" type="submit" name="test" value="1" formaction="{{ url_for('test_oidc') }}">Discovery testen</button>
  </div>
</form>

{% if meta %}
<hr>
<h3>Discovery metadata</h3>
<table class="table">
  <tbody>
    {% for k,v in meta.items() %}{% if not k.startswith('_') %}
    <tr><td class="mono" style="font-size:12px;width:220px">{{ k }}</td><td style="font-size:12px;word-break:break-all">{{ v }}</td></tr>
    {% endif %}{% endfor %}
  </tbody>
</table>
{% endif %}
</div>
"""

BEHEER_BODY = """
<style>
.beheer-tabs{display:flex;gap:6px;overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:6px;margin-bottom:20px;border-bottom:1px solid var(--stroke-light)}
.btab{display:inline-flex;align-items:center;gap:7px;white-space:nowrap;padding:10px 16px;border:1px solid var(--stroke);background:#fff;border-radius:24px 24px 24px 4px;color:var(--fg2);font-weight:600;font-size:14px;cursor:pointer;min-height:44px;flex-shrink:0}
.btab .mi{font-size:18px;vertical-align:-4px}
.btab:hover{background:var(--btnh)}
.btab.active{background:var(--red);border-color:var(--red);color:#fff}
.bpanel{display:none}
.bpanel.active{display:block}
.beheer-save{position:sticky;bottom:0;background:#fff;padding:14px 0 4px;border-top:1px solid var(--stroke-light);margin-top:18px}
.beheer-card{border:1px solid var(--stroke);border-radius:var(--radius-sm);background:#fff;box-shadow:var(--shadow-sm);padding:18px;margin-bottom:16px}
.beheer-card h3{margin-top:0}
</style>

<h1>Beheer</h1>

<div class="beheer-tabs" id="beheerTabs">
  <button type="button" class="btab active" data-tab="algemeen" onclick="beheerTab('algemeen')"><span class="mi">tune</span> Algemeen</button>
  <button type="button" class="btab" data-tab="huisstijl" onclick="beheerTab('huisstijl')"><span class="mi">palette</span> Huisstijl</button>
  <button type="button" class="btab" data-tab="tts" onclick="beheerTab('tts')"><span class="mi">record_voice_over</span> Text to Speech</button>
  <button type="button" class="btab" data-tab="mededeling" onclick="beheerTab('mededeling')"><span class="mi">new_releases</span> Changelog</button>
  <button type="button" class="btab" data-tab="audio" onclick="beheerTab('audio')"><span class="mi">graphic_eq</span> Audio</button>
  <button type="button" class="btab" data-tab="spotifybeheer" onclick="beheerTab('spotifybeheer')"><img src="{{ spotify_logo }}" alt="Spotify" style="height:17px;vertical-align:middle;display:inline-block"></button>
  <button type="button" class="btab" data-tab="plusradio" onclick="beheerTab('plusradio')"><span class="pr-lockup">{{ plus_wordmark|safe }}<span class="pr-radio">RADIO</span></span></button>
  <button type="button" class="btab" data-tab="sip" onclick="beheerTab('sip')"><span class="mi">campaign</span> Live omroep</button>
  <button type="button" class="btab" data-tab="ip" onclick="beheerTab('ip')"><span class="mi">verified_user</span> Toegang</button>
  <button type="button" class="btab" data-tab="woorden" onclick="beheerTab('woorden')"><span class="mi">block</span> Woordfilter</button>
  <button type="button" class="btab" data-tab="snel" onclick="beheerTab('snel')"><span class="mi">bolt</span> Snel invoegen</button>
  <button type="button" class="btab" data-tab="schema" onclick="beheerTab('schema')"><span class="mi">smart_toy</span> Automatiseringen</button>
</div>

<form method="post" action="{{ url_for('save_settings') }}">

  <!-- ALGEMEEN -->
  <div class="bpanel active" data-panel="algemeen">
    <div class="beheer-card" style="border-left:4px solid var(--green)">
      <h3 style="display:flex;align-items:center;gap:8px"><span class="mi">system_update</span> Systeem &amp; updates</h3>
      <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
        <div>
          <div class="label" style="margin:0">Huidige versie</div>
          <div id="sysCurVer" style="font-size:20px;font-weight:800;color:var(--green-dark)">{{ settings.version }}</div>
        </div>
        <div id="sysUpdInfo" class="help" style="margin:0;flex:1;min-width:180px">Klik op &laquo;Controleren&raquo; om te kijken of er een nieuwe versie is.</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button type="button" class="btn btn-sm btn-inline" style="width:auto" onclick="sysCheck()"><span class="mi">refresh</span> Controleren</button>
          <button type="button" class="btn btn-sm btn-primary btn-inline" style="width:auto;display:none" id="sysUpdBtn" onclick="sysUpdate()"><span class="mi">download</span> Nu bijwerken</button>
        </div>
      </div>
      <div id="sysUpdMsg" style="margin-top:10px;font-size:13px;display:none"></div>
      <div class="help" style="margin-top:8px">Haalt de laatste versie van GitHub. Na een update herstart de app automatisch &mdash; je hoeft hiervoor niet in de console.</div>
    </div>
    <script>
    function sysCheck(){
      var info=document.getElementById('sysUpdInfo'); info.textContent='Controleren\\u2026';
      fetch('/api/system/version').then(function(r){return r.json();}).then(function(j){
        document.getElementById('sysCurVer').textContent=j.current||'?';
        var btn=document.getElementById('sysUpdBtn');
        if(!j.is_git){ info.textContent='Deze installatie is niet via GitHub ge\\u00efnstalleerd (updaten via de console).'; btn.style.display='none'; return; }
        if(j.update_available){ info.innerHTML='Nieuwe versie beschikbaar: <b>'+(j.latest||'nieuwer')+'</b>'; btn.style.display='inline-flex'; }
        else { info.textContent='Je hebt de laatste versie ('+(j.latest||j.current)+').'; btn.style.display='none'; }
      }).catch(function(){ info.textContent='Kon niet controleren.'; });
    }
    function sysUpdate(){
      if(!confirm('Nu bijwerken naar de laatste versie? De app herstart heel even.')) return;
      var m=document.getElementById('sysUpdMsg'); m.style.display='block'; m.style.color='var(--green-dark)';
      m.innerHTML='<span class="mi mi-sm" style="vertical-align:middle">autorenew</span> Bijwerken\\u2026 de app herstart zo. Deze pagina laadt daarna vanzelf opnieuw.';
      document.getElementById('sysUpdBtn').disabled=true;
      fetch('/api/system/update',{method:'POST'}).then(function(r){return r.json();}).then(function(j){
        if(!j.ok){ m.style.color='#c62828'; m.textContent=j.error||'Bijwerken mislukt.'; document.getElementById('sysUpdBtn').disabled=false; return; }
        var t=setInterval(function(){ fetch('/api/system/version',{cache:'no-store'}).then(function(r){return r.json();}).then(function(v){ if(v && !v.update_available){ clearInterval(t); location.reload(); } }).catch(function(){}); },4000);
      }).catch(function(){ m.style.color='#c62828'; m.textContent='Bijwerken mislukt.'; document.getElementById('sysUpdBtn').disabled=false; });
    }
    </script>
    <div class="row">
      <div class="col">
        <div class="beheer-card">
          <h3>Locatie &amp; weergave</h3>
          <div class="label">Locatie / filiaal</div>
          <input class="input" type="text" name="location_name" value="{{ settings.location_name or '' }}"
                 placeholder="bijv. Centrum (leeg = alleen &quot;PLUS&quot;)" style="margin-bottom:4px">
          <div class="help" style="margin-bottom:12px">Wordt getoond als &laquo;PLUS [locatie] Audiosysteem&raquo;. Laat leeg voor een generieke installatie.</div>
          <label class="switch-row">
            <input type="checkbox" name="show_playing_popup" value="1" {% if settings.show_playing_popup %}checked{% endif %}>
            <span>Toon &laquo;nu aan het afspelen&raquo;-popup bij presets</span>
          </label>
          <div class="help" style="margin-bottom:12px">Groot venster met presetnaam, icoon en Stop-knop &mdash; handig aan de servicebalie om een verkeerd gekozen omroep meteen te stoppen.</div>
          <div class="label">Versie</div>
          <input class="input" type="text" name="version" value="{{ settings.version }}">
        </div>
      </div>
      <div class="col">
        <div class="beheer-card">
          <h3>Pagina's zichtbaar</h3>
          <label class="switch-row"><input type="checkbox" name="page_volume"  value="1" {% if settings.pages.volume  %}checked{% endif %}> <span>Muziek</span></label>
          <label class="switch-row"><input type="checkbox" name="page_presets" value="1" {% if settings.pages.presets %}checked{% endif %}> <span>Presets</span></label>
          <label class="switch-row"><input type="checkbox" name="page_tts"     value="1" {% if settings.pages.tts     %}checked{% endif %}> <span>Text to Speech</span></label>
        </div>
        <div class="beheer-card">
          <h3>Kiosk-sloten (pincode)</h3>
          <label class="switch-row"><input type="checkbox" name="presets_lock_enabled" value="1" {% if settings.presets_lock_enabled %}checked{% endif %}> <span>Presets-slot</span></label>
          <div class="label" style="margin-top:8px">Presets: vergrendel na (seconden)</div>
          <input class="input" type="number" min="5" max="3600" name="presets_lock_seconds" value="{{ settings.presets_lock_seconds }}" style="margin-bottom:12px">
          <label class="switch-row"><input type="checkbox" name="tts_lock_enabled" value="1" {% if settings.tts_lock_enabled %}checked{% endif %}> <span>Text to Speech-slot</span></label>
          <div class="label" style="margin-top:8px">Text to Speech: vergrendel na (seconden)</div>
          <input class="input" type="number" min="5" max="3600" name="tts_lock_seconds" value="{{ settings.tts_lock_seconds }}">
        </div>
      </div>
    </div>
  </div>

  <!-- TTS -->
  <div class="bpanel" data-panel="tts">
    <div class="row">
      <div class="col">
        <div class="beheer-card">
          <h3>Text to Speech-engine &amp; stem</h3>
          <div class="label">Engine</div>
          <select class="input" name="tts_engine" style="margin-bottom:10px">
            <option value="edge"   {% if settings.tts_engine=='edge'   %}selected{% endif %}>Edge Text to Speech (Microsoft)</option>
            <option value="piper"  {% if settings.tts_engine=='piper'  %}selected{% endif %}>Piper (offline)</option>
            <option value="espeak" {% if settings.tts_engine=='espeak' %}selected{% endif %}>eSpeak (fallback)</option>
          </select>
          <div class="label">Edge Text to Speech stem</div>
          <select class="input" name="tts_edge_voice">
            <option value="nl-NL-MaartenNeural" {% if settings.tts_edge_voice=='nl-NL-MaartenNeural' %}selected{% endif %}>Maarten (man, NL)</option>
            <option value="nl-NL-ColetteNeural" {% if settings.tts_edge_voice=='nl-NL-ColetteNeural' %}selected{% endif %}>Colette (vrouw, NL)</option>
            <option value="nl-BE-ArnaudNeural"  {% if settings.tts_edge_voice=='nl-BE-ArnaudNeural'  %}selected{% endif %}>Arnaud (man, BE)</option>
            <option value="nl-BE-DenaNeural"    {% if settings.tts_edge_voice=='nl-BE-DenaNeural'    %}selected{% endif %}>Dena (vrouw, BE)</option>
          </select>
        </div>
      </div>
      <div class="col">
        <div class="beheer-card">
          <h3>Geluid</h3>
          <div class="label">Text to Speech gain % (0&ndash;200)</div>
          <input class="input" type="number" name="tts_gain" min="0" max="200" value="{{ settings.tts_gain or 100 }}" style="margin-bottom:10px">
          <label class="switch-row"><input type="checkbox" name="tts_preroll_enabled" value="1" {% if settings.tts_preroll_enabled %}checked{% endif %}> <span>Preroll (intro) standaard aan</span></label>
          <label class="switch-row"><input type="checkbox" name="tts_outro_enabled" value="1" {% if settings.tts_outro_enabled %}checked{% endif %}> <span>Outro standaard aan</span></label>
        </div>
      </div>
    </div>
  </div>

  <!-- MEDEDELING -->
  <div class="bpanel" data-panel="mededeling">
    <div class="beheer-card">
      <h3>Changelog</h3>
      <textarea class="input" name="announcement_text" style="min-height:220px">{{ settings.announcement_text }}</textarea>
      <label class="switch-row" style="margin-top:8px">
        <input type="checkbox" name="announcement_enabled" value="1" {% if settings.announcement_enabled %}checked{% endif %}>
        <span>Automatisch tonen bij een update</span>
      </label>
      <div class="help">Ondersteunt Markdown. Wordt eenmalig getoond aan gebruikers tot je de tekst wijzigt.</div>
    </div>
  </div>

  <div class="beheer-save" id="beheerSave">
    <button class="btn btn-primary btn-inline" type="submit" style="min-width:160px"><span class="mi">save</span> Instellingen opslaan</button>
  </div>
</form>

<!-- HUISSTIJL / BRANDING -->
<div class="bpanel" data-panel="huisstijl">
  <style>
    .brand-grid{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:6px}
    .brand-card{flex:1 1 220px;border:2px solid var(--stroke);border-radius:12px;background:#fff;overflow:hidden;cursor:pointer;transition:border-color .15s,box-shadow .15s;position:relative}
    .brand-card:has(input:checked){border-color:var(--red);box-shadow:0 4px 14px rgba(0,0,0,.10)}
    .brand-card input{position:absolute;opacity:0;pointer-events:none}
    .brand-head{display:flex;align-items:center;gap:12px;padding:16px;color:#fff}
    .brand-head img{height:30px;width:auto}
    .brand-head img.boxed{background:#fff;border-radius:6px;padding:3px;box-sizing:content-box}
    .brand-head .bn{font-weight:800;font-size:16px}
    .brand-body{padding:12px 16px}
    .brand-swatches{display:flex;gap:6px;margin-bottom:8px}
    .brand-swatch{width:26px;height:26px;border-radius:6px;border:1px solid rgba(0,0,0,.08)}
    .brand-check{position:absolute;top:10px;right:10px;color:#fff;opacity:0;transition:opacity .15s}
    .brand-card:has(input:checked) .brand-check{opacity:1}
    .brand-radio-name{font-size:13px;color:var(--fg3)}
  </style>
  <div class="row">
    <div class="col">
      <div class="beheer-card">
        <h3><span class="mi">palette</span> Huisstijl kiezen</h3>
        <div class="help" style="margin-bottom:14px">Kies de winkelhuisstijl. Dit past kleuren, logo en naam van het hele omroepsysteem aan &mdash; inlogpagina, koppen, knoppen en de footer. Nieuwe ketens (bijv. Jumbo) kunnen later worden toegevoegd.</div>
        <form method="post" action="{{ url_for('save_branding') }}" enctype="multipart/form-data" id="brandForm">
          <div class="brand-grid">
            {% for t in brand_themes %}
            <label class="brand-card">
              <input type="radio" name="brand_theme" value="{{ t.key }}" {{ 'checked' if active_theme==t.key else '' }} onchange="brandPick('{{ t.name }}')">
              <span class="brand-check" style="color:{{ t.on_primary }}"><span class="mi">check_circle</span></span>
              <div class="brand-head" style="background:{{ t.primary }};color:{{ t.on_primary }}">
                <img src="{{ t.logo }}" alt="{{ t.name }}" class="{{ 'boxed' if t.logo_boxed else '' }}">
                <span class="bn">{{ t.name }}</span>
              </div>
              <div class="brand-body">
                <div class="brand-swatches">
                  <span class="brand-swatch" style="background:{{ t.primary }}" title="Primair"></span>
                  <span class="brand-swatch" style="background:{{ t.heading }}" title="Koppen"></span>
                  <span class="brand-swatch" style="background:{{ t.accent }}" title="Accent"></span>
                </div>
                <div class="brand-radio-name">Radio: {{ t.radio_name }}{% if t.has_override %} &middot; eigen logo{% endif %}</div>
              </div>
            </label>
            {% endfor %}
          </div>
          <div class="beheer-card" style="margin-top:14px;background:var(--bg-soft)">
            <h3 style="margin-top:0"><span class="mi">image</span> Eigen logo voor <span id="brandLogoFor">{% for t in brand_themes %}{% if t.key==active_theme %}{{ t.name }}{% endif %}{% endfor %}</span></h3>
            <div class="help" style="margin-bottom:10px">Optioneel eigen logo voor het <b>geselecteerde</b> thema (SVG/PNG, max&nbsp;512&nbsp;kB). Vervangt het standaardlogo op de topbar en inlogpagina. Kies eerst het thema hierboven en sla daarna op.</div>
            <div class="label">Logo uploaden</div>
            <input class="input" type="file" name="brand_logo_file" accept=".svg,.png,.jpg,.jpeg,.webp,.gif" style="margin-bottom:12px">
            <div class="label">of logo-URL</div>
            <input class="input" type="text" name="brand_logo_url" placeholder="https://…  of  data:image/svg+xml;base64,…" style="margin-bottom:12px">
            <label class="switch-row"><input type="checkbox" name="brand_logo_clear" value="1"> <span>Eigen logo verwijderen (terug naar standaard)</span></label>
          </div>
          <div style="height:12px"></div>
          <button class="btn btn-primary btn-inline" type="submit"><span class="mi">save</span> Huisstijl opslaan</button>
        </form>
      </div>
    </div>
  </div>
  <script>
  function brandPick(name){ var e=document.getElementById('brandLogoFor'); if(e) e.textContent=name; }
  </script>
</div>

<!-- AUDIO & PI -->
<div class="bpanel" data-panel="audio">
  <div class="row">
    <div class="col">
      <div class="beheer-card">
        <h3>Preroll (intro)</h3>
        <form method="post" action="{{ url_for('upload_intro') }}" enctype="multipart/form-data">
          <input class="input" type="file" name="file" accept=".wav,.mp3,.m4a" required style="margin-bottom:8px">
          <button class="btn btn-inline" type="submit"><span class="mi">upload</span> Upload / Vervang</button>
        </form>
        <div style="height:10px"></div>
        {% if intro_exists %}
          <div style="margin-bottom:8px"><span class="mi mi-sm" style="color:#4b7a12">check</span> Preroll aanwezig</div>
          <form method="post" action="{{ url_for('delete_intro') }}" onsubmit="return confirm('Verwijderen?')">
            <button class="btn btn-sm btn-danger btn-inline" type="submit"><span class="mi">delete</span> Verwijderen</button>
          </form>
        {% else %}<div class="help">Geen preroll ingesteld.</div>{% endif %}
      </div>
    </div>
    <div class="col">
      <div class="beheer-card">
        <h3>Outro</h3>
        <p class="help" style="margin-bottom:12px">Wordt (indien ingeschakeld) ná de preset of Text to Speech afgespeeld, vóórdat het achtergrondvolume terugkomt. Per preset via Presets &rarr; Bewerken; voor Text to Speech via de checkbox op de Text to Speech-pagina.</p>
        <form method="post" action="{{ url_for('upload_outro') }}" enctype="multipart/form-data">
          <input class="input" type="file" name="file" accept=".wav,.mp3,.m4a" required style="margin-bottom:8px">
          <button class="btn btn-inline" type="submit"><span class="mi">upload</span> Upload / Vervang</button>
        </form>
        <div style="height:10px"></div>
        {% if outro_exists %}
          <div style="margin-bottom:8px"><span class="mi mi-sm" style="color:#4b7a12">check</span> Outro aanwezig</div>
          <form method="post" action="{{ url_for('delete_outro') }}" onsubmit="return confirm('Verwijderen?')">
            <button class="btn btn-sm btn-danger btn-inline" type="submit"><span class="mi">delete</span> Verwijderen</button>
          </form>
        {% else %}<div class="help">Geen outro ingesteld.</div>{% endif %}
      </div>
    </div>
  </div>

  <div class="row">
    <div class="col">
      <div class="beheer-card">
        <h3>Achtergrond tijdens omroep</h3>
        <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px">
          <input class="range" type="range" min="0" max="80" id="piDuckSlider"
                 value="{{ settings.pi_duck_level | default(0) }}"
                 oninput="document.getElementById('piDuckNum').textContent=this.value+'%'">
          <span id="piDuckNum" style="min-width:42px;text-align:right;font-weight:700">{{ settings.pi_duck_level | default(0) }}%</span>
        </div>
        <button class="btn btn-sm btn-inline" onclick="piSaveDuck()"><span class="mi">save</span> Opslaan niveau</button>
        <div id="duckMsg" style="margin-top:8px;font-size:13px;display:none"></div>
        <div class="help" style="margin-top:8px">Naar welk niveau <b>zowel Spotify als RCA PlusRadio</b> gaan tijdens elke preset of Text to Speech. <b>0% = volledig stil</b> (aanbevolen). Daarna gaat de achtergrond automatisch terug naar het originele niveau.</div>
      </div>
    </div>
    <div class="col"></div>
  </div>
</div>

<!-- SPOTIFY -->
<div class="bpanel" data-panel="spotifybeheer">
  <div class="row">
    <div class="col">
      <div class="beheer-card">
        <h3 style="display:flex;align-items:center;gap:8px"><img src="{{ spotify_logo }}" alt="Spotify" style="height:20px"> Bediening</h3>
        <label style="display:flex;align-items:center;gap:10px;cursor:pointer">
          <input type="checkbox" id="spCtrlToggle" {{ 'checked' if settings.spotify_control else '' }} onchange="spSaveMode()">
          <span>Transportknoppen + slepen inschakelen</span>
        </label>
        <div class="help" style="margin-top:8px">Zet dit aan om onder <b>Muziek &rarr; Spotify</b> te kunnen afspelen, pauzeren, doorspoelen en de wachtrij te slepen. Uit = alleen weergave (nu-speelt).</div>
        <div id="spCtrlMsg" style="margin-top:8px;font-size:13px;display:none"></div>
        <div style="height:14px"></div>
        <button class="btn btn-sm btn-gold btn-inline" onclick="spRestart()"><span class="mi">restart_alt</span> Spotify-speler herstarten</button>
        <div class="help" style="margin-top:6px">Herstart de lokale go-librespot op de VM (bij haperende Connect/afspelen).</div>
        <div id="spRestartMsg" style="margin-top:8px;font-size:13px;display:none"></div>
      </div>
    </div>
    <div class="col">
      <div class="beheer-card">
        <h3 style="display:flex;align-items:center;gap:8px"><img src="{{ spotify_logo }}" alt="Spotify" style="height:20px"> Web API &mdash; zoeken &amp; wachtrij</h3>
        <div class="help" style="margin-bottom:10px">Koppel het <b>huis-Spotify-account (Premium)</b> zodat je onder <b>Muziek &rarr; Spotify</b> kunt zoeken, afspelen en in de wachtrij zetten. Gegevens uit je Spotify-app (developer.spotify.com). Redirect-URI in die app: <code>{{ (settings.public_base_url or 'https://JOUW-DOMEIN') }}/spotify/callback</code>.</div>
        <div class="row">
          <div class="col"><div class="label">Client ID</div><input class="input" id="spCidInput" autocomplete="off"></div>
          <div class="col"><div class="label">Client secret</div><input class="input" type="password" id="spSecInput" placeholder="leeg = ongewijzigd laten" autocomplete="off"></div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
          <button class="btn btn-inline" style="width:auto" onclick="spAdminSave()"><span class="mi">save</span> Opslaan</button>
          <a class="btn btn-primary btn-inline" style="width:auto" id="spConnectBtn" href="/spotify/auth" target="_blank"><span class="mi">link</span> Koppelen met Spotify</a>
        </div>
        <div id="spAdminStatus" class="help" style="margin-top:10px">&nbsp;</div>
      </div>
    </div>
  </div>
  <div class="beheer-card">
    <h3 style="display:flex;align-items:center;gap:8px"><img src="{{ spotify_logo }}" alt="Spotify" style="height:20px"> Reclame over Spotify</h3>
    <label class="switch-row"><input type="checkbox" id="commDuckToggle" {{ 'checked' if settings.commercial_duck_spotify else '' }} onchange="spCommToggle('commercial_duck_spotify',this)"> <span>Spotify automatisch dempen tijdens een reclame</span></label>
    <label class="switch-row"><input type="checkbox" id="commReplayToggle" {{ 'checked' if settings.commercial_replay else '' }} onchange="spCommToggle('commercial_replay',this)"> <span>Reclame <b>tussen de nummers</b> over Spotify afspelen <span style="color:#b37e00;font-weight:700">(experimenteel)</span><br><span class="help">Neemt de reclame compleet op en speelt 'm af bij de e&eacute;rstvolgende nummerovergang &mdash; nooit midden in een nummer. Test op een rustig moment.</span></span></label>
    <div id="commToggleMsg" style="margin-top:6px;font-size:13px;display:none"></div>
    <div style="margin-top:10px;padding:10px 12px;background:var(--bg2, #f6f7f4);border-radius:10px">
      <div class="label" style="margin:0 0 6px"><span class="mi mi-sm" style="vertical-align:middle">download</span> Laatst opgenomen reclames</div>
      <div id="recComList" class="help" style="margin:0">Laden…</div>
    </div>
  </div>
  <script>
  function spCommToggle(key,el){
    fetch('/api/spotify/comm_toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key,on:el.checked})})
      .then(function(r){return r.json();}).then(function(j){
        var m=document.getElementById('commToggleMsg'); if(!m) return;
        m.style.display='block';m.style.color=j.ok?'#4b7a12':'#c62828';m.textContent=j.ok?'Opgeslagen':'Fout';
        setTimeout(function(){m.style.display='none';},2500);
      }).catch(function(){});
  }
  function loadRecCom(){
    var el=document.getElementById('recComList'); if(!el) return;
    fetch('/api/commercials/recorded',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
      var it=(j&&j.items)||[];
      if(!it.length){ el.textContent='Nog geen opnames. Zodra een reclame over Spotify heeft gespeeld verschijnt \\'ie hier.'; return; }
      el.innerHTML=it.map(function(x){
        return '<div style="display:flex;align-items:center;gap:8px;padding:4px 0"><a class="btn btn-sm btn-inline" style="width:auto" href="'+x.url+'"><span class="mi">download</span> mp3</a><span style="color:var(--fg3)">'+x.when+' &middot; '+x.size_kb+' kB</span></div>';
      }).join('');
    }).catch(function(){ el.textContent='Kon opnames niet laden.'; });
  }
  loadRecCom(); setInterval(loadRecCom, 30000);
  function spAdminLoad(){
    fetch('/api/spotify/admin/status').then(function(r){return r.json();}).then(function(j){
      var c=document.getElementById('spCidInput'); if(c&&!c.value) c.value=j.client_id||'';
      var b=document.getElementById('spConnectBtn'); if(b) b.href=j.auth_url||'/spotify/auth';
      var s=j.connected?(j.token_ok?('Gekoppeld ✔ — apparaat: '+(j.device_id?'gevonden':'nog niet gevonden (zorg dat Spotify actief is op de VM)')):'Gekoppeld, maar token vernieuwen faalt — controleer client secret'):'Nog niet gekoppeld';
      var el=document.getElementById('spAdminStatus'); if(el) el.textContent=s;
    }).catch(function(){});
  }
  function spAdminSave(){
    var body={client_id:document.getElementById('spCidInput').value,client_secret:document.getElementById('spSecInput').value};
    fetch('/api/spotify/admin/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
      .then(function(r){return r.json();}).then(function(){ document.getElementById('spSecInput').value=''; spAdminLoad(); });
  }
  spAdminLoad();
  </script>
</div>

<!-- PLUS RADIO -->
<div class="bpanel" data-panel="plusradio">
  <div class="row">
    <div class="col">
      <div class="beheer-card">
        <h3>{{ brand.radio_name }}-streamer</h3>
        <div class="help" style="margin-bottom:12px">Instellingen van de Streamit-streamer en de online stream. Handig bij uitrol in een <b>andere winkel</b>: pas hier het IP en de Icecast-gegevens aan.</div>
        <form method="post" action="{{ url_for('save_streamer') }}">
          <label class="switch-row"><input type="checkbox" name="lisa_enabled" value="1" {{ 'checked' if settings.lisa_enabled else '' }}> <span>Huidig nummer uitlezen van de streamer</span></label>
          <div class="row">
            <div class="col"><div class="label">IP-adres streamer</div><input class="input" name="lisa_host" value="{{ settings.lisa_host or '' }}" placeholder="bijv. 10.0.0.50"></div>
            <div class="col"><div class="label">Telnet-poort</div><input class="input" name="lisa_port" value="{{ settings.lisa_port | default(23) }}"></div>
          </div>
          <label class="switch-row" style="margin-top:12px"><input type="checkbox" name="shazam_enabled" value="1" {{ 'checked' if settings.shazam_enabled else '' }}> <span>Nummer herkennen (Shazam) &rarr; volledige titel, artiest &amp; albumcover</span></label>
          <div class="help" style="margin-top:6px">De reclame-over-Spotify-instellingen staan nu onder het <b>Spotify</b>-tabblad.</div>
          <div class="label" style="margin-top:12px">Commercial-volume op de online stream</div>
          <div style="display:flex;align-items:center;gap:10px">
            <button type="button" class="btn vol-step" style="width:46px;flex:0 0 auto;font-size:20px;font-weight:800" onclick="streamPct(-5)">−</button>
            <span id="streamPctVal" style="min-width:64px;text-align:center;font-weight:800;font-size:18px;color:var(--green-dark)">{{ settings.commercial_stream_pct | default(50) }}%</span>
            <button type="button" class="btn vol-step" style="width:46px;flex:0 0 auto;font-size:20px;font-weight:800" onclick="streamPct(5)">+</button>
            <span class="help" style="margin:0">van normaal, tijdens een reclame</span>
          </div>
          <script>
          function streamPct(d){
            fetch('/api/stream/commercial_pct',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delta:d})})
              .then(function(r){return r.json();}).then(function(j){ if(j.ok){var e=document.getElementById('streamPctVal'); if(e) e.textContent=j.pct+'%';} }).catch(function(){});
          }
          </script>
          <div class="label" style="margin-top:16px;border-top:1px solid var(--stroke-light);padding-top:12px">Online stream (Icecast-metadata)</div>
          <label class="switch-row"><input type="checkbox" name="icecast_meta_enabled" value="1" {{ 'checked' if settings.icecast_meta_enabled else '' }}> <span>Titel meesturen naar de stream</span></label>
          <div class="row">
            <div class="col"><div class="label">Admin-URL</div><input class="input" name="icecast_admin_url" value="{{ settings.icecast_admin_url | default('') }}"></div>
            <div class="col"><div class="label">Mount</div><input class="input" name="icecast_mount" value="{{ settings.icecast_mount | default('/rca') }}"></div>
          </div>
          <div class="row">
            <div class="col"><div class="label">Admin-gebruiker</div><input class="input" name="icecast_admin_user" value="{{ settings.icecast_admin_user | default('admin') }}"></div>
            <div class="col"><div class="label">Admin-wachtwoord</div><input class="input" type="password" name="icecast_admin_pass" placeholder="leeg = ongewijzigd laten"></div>
          </div>
          <div class="label" style="margin-top:16px;border-top:1px solid var(--stroke-light);padding-top:12px">TuneIn (nu speelt doorgeven)</div>
          <label class="switch-row"><input type="checkbox" name="tunein_enabled" value="1" {{ 'checked' if settings.tunein_enabled else '' }}> <span>Huidige titel/artiest naar TuneIn pushen</span></label>
          <div class="help" style="margin-bottom:8px">Vereist TuneIn-broadcaster-gegevens (partnerId + partnerKey via TuneIn). StationId staat in je TuneIn-URL (bijv. <code>s359456</code>).</div>
          <div class="row">
            <div class="col"><div class="label">Partner ID</div><input class="input" name="tunein_partner_id" value="{{ settings.tunein_partner_id | default('') }}"></div>
            <div class="col"><div class="label">Station ID</div><input class="input" name="tunein_station_id" value="{{ settings.tunein_station_id | default('s359456') }}"></div>
          </div>
          <div class="label">Partner Key</div>
          <input class="input" type="password" name="tunein_partner_key" placeholder="leeg = ongewijzigd laten">
          <div style="height:14px"></div>
          <button class="btn btn-primary btn-inline" type="submit"><span class="mi">save</span> Opslaan</button>
        </form>
      </div>
    </div>
    <div class="col">
      <div class="beheer-card">
        <h3>Streamer-console</h3>
        <div class="help" style="margin-bottom:10px">Commando's naar de streamer. Bv. <code>getinfo title</code>, <code>getinfo playerstat</code>, <code>channel</code>, <code>pp 1</code> (Plus Main), <code>pp 2</code> (Plus Easy), <code>isp</code>, <code>ver</code>. Reset-/log-commando's zijn geblokkeerd.</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">
          <button class="btn btn-sm btn-inline" onclick="lisaCmd('getinfo title')">Titel</button>
          <button class="btn btn-sm btn-inline" onclick="lisaCmd('getinfo playerstat')">Status</button>
          <button class="btn btn-sm btn-inline" onclick="lisaCmd('channel')">Kanalen</button>
          <button class="btn btn-sm btn-inline" onclick="lisaCmd('isp')">Netwerk</button>
          <button class="btn btn-sm btn-inline" onclick="lisaCmd('ver')">Versie</button>
        </div>
        <div style="display:flex;gap:8px;margin-bottom:10px">
          <input class="input" id="lisaCmdInput" placeholder="commando… (bv. getinfo title)" onkeydown="if(event.key==='Enter'){event.preventDefault();lisaCmd();}">
          <button class="btn btn-sm btn-inline" style="width:auto;flex:0 0 auto" onclick="lisaCmd()"><span class="mi">send</span> Stuur</button>
        </div>
        <pre id="lisaOut" style="background:#0d1a0d;color:#c8e6a0;border-radius:10px;padding:12px;font-size:12px;line-height:1.5;max-height:300px;overflow:auto;white-space:pre-wrap;word-break:break-word;margin:0">Stuur een commando naar de streamer…</pre>
      </div>
    </div>
  </div>
  <div class="beheer-card" style="margin-top:16px">
    <h3>Streamer herstarten</h3>
    <div class="help" style="margin-bottom:10px">Herstart de Streamit-streamer. De <b>muziek valt ~30&ndash;60 seconden weg</b> en de <b>playlist begint opnieuw vanaf het begin</b>. Gebruik dit alleen als de streamer hapert.</div>
    <button class="btn btn-gold btn-inline" style="width:auto" onclick="prRestartAsk()"><span class="mi">restart_alt</span> Streamer herstarten</button>
    <span id="prRestartMsg" style="font-size:13px;margin-left:8px"></span>
  </div>
  <div id="prRestartModal" class="modal-backdrop" onclick="if(event.target===this)prRestartClose()">
    <div class="modal" style="max-width:440px;text-align:center;border-top:6px solid #e0a400">
      <span class="mi" style="font-size:52px;color:#e0a400">warning</span>
      <div style="font-size:13px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#b37e00;margin:6px 0">Let op</div>
      <div style="font-size:17px;font-weight:800;color:var(--green-dark);margin-bottom:8px">Streamer herstarten?</div>
      <div class="help" style="margin-bottom:18px">De streamer start opnieuw op. De <b>muziek valt ongeveer 30&ndash;60 seconden weg</b> en de <b>playlist begint weer vanaf het begin</b>.</div>
      <button class="btn btn-primary" onclick="prRestartDo()" style="min-height:50px;font-weight:800"><span class="mi">restart_alt</span> Ja, herstarten</button>
      <div style="height:8px"></div>
      <button class="btn" onclick="prRestartClose()"><span class="mi">close</span> Annuleren</button>
    </div>
  </div>
  <script>
  function prRestartAsk(){ var m=document.getElementById('prRestartModal'); if(m) m.style.display='flex'; }
  function prRestartClose(){ var m=document.getElementById('prRestartModal'); if(m) m.style.display='none'; }
  function prRestartDo(){
    prRestartClose();
    var s=document.getElementById('prRestartMsg'); if(s){s.style.color='#4b7a12';s.textContent='Herstarten… (kan ~1 min duren)';}
    fetch('/api/plusradio/restart',{method:'POST'}).then(function(r){return r.json();}).then(function(j){
      if(s){ s.textContent=j.ok?'Streamer wordt opnieuw opgestart.':'Herstarten mislukt.'; setTimeout(function(){s.textContent='';},8000); }
    }).catch(function(){ if(s){ s.style.color='#c62828'; s.textContent='Herstarten mislukt.'; } });
  }
  </script>
  <script>
  function lisaCmd(cmd){
    var inp=document.getElementById('lisaCmdInput');
    var fromInput=(cmd===undefined);
    cmd=cmd||(inp?inp.value.trim():'');
    if(!cmd) return;
    fetch('/api/lisa/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd:cmd})})
      .then(function(r){return r.json();}).then(function(j){
        var out=document.getElementById('lisaOut');
        var hist=j.history||[];
        out.textContent=hist.map(function(h){return '> '+h.cmd+'\\n'+(h.resp||'');}).join('\\n\\n')||(j.resp||'(geen respons)');
        out.scrollTop=out.scrollHeight;
        if(fromInput&&inp) inp.value='';
      }).catch(function(){});
  }
  </script>
</div>

<!-- IP-REGELS -->
<!-- LIVE OMROEP (SIP) -->
<div class="bpanel" data-panel="sip">
  <div class="beheer-card" style="border-left:4px solid var(--green)">
    <h3 style="display:flex;align-items:center;gap:8px"><span class="mi">campaign</span> Live omroep via de telefoon (3CX / SIP)</h3>
    <div class="help" style="margin-bottom:12px">Bel vanaf een 3CX-toestel het ingestelde extensienummer om <b>live over de winkelspeakers</b> om te roepen. Bij het opnemen speelt eerst de <b>intro</b>, daarna hoort de winkel jouw stem, en na het ophangen de <b>outro</b> &mdash; de muziek (Spotify / {{ brand.radio_name }} / reclame) wordt automatisch gedempt en daarna hersteld.</div>
    <div id="sipStatus" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 12px;background:var(--bg2,#f6f7f4);border-radius:10px;margin-bottom:16px">
      <span class="mi" id="sipDot" style="color:#9aa0a6;font-size:14px">circle</span>
      <span id="sipStatusTxt" style="font-weight:600">Status laden&hellip;</span>
    </div>

    <label class="switch-row"><input type="checkbox" id="sipEnabled" {{ 'checked' if settings.sip_enabled else '' }}> <span>Live omroep inschakelen <span class="help">(registreert als toestel bij de SBC en neemt inkomende gesprekken aan)</span></span></label>
    <div style="height:12px"></div>
    <div class="row">
      <div class="col"><div class="label">Extensienummer</div>
        <input class="input" id="sipExt" placeholder="bijv. 321" autocomplete="off" value="{{ settings.sip_extension or '' }}"></div>
      <div class="col"><div class="label">Authentication ID</div>
        <input class="input" id="sipAuthId" autocomplete="off" value="{{ settings.sip_auth_id or '' }}"></div>
    </div>
    <div class="row">
      <div class="col"><div class="label">Authentication password</div>
        <input class="input" type="password" id="sipAuthPass" placeholder="{{ '••••••••  (leeg = ongewijzigd)' if settings.sip_auth_pass else 'wachtwoord' }}" autocomplete="new-password"></div>
      <div class="col"><div class="label">Registrar hostname of IP</div>
        <input class="input" id="sipReg" placeholder="bijv. pluskoelhuis.my3cx.nl" autocomplete="off" value="{{ settings.sip_registrar_host or '' }}"></div>
    </div>
    <div class="row">
      <div class="col"><div class="label">Registrar SIP-poort</div>
        <input class="input" type="number" id="sipRegPort" value="{{ settings.sip_registrar_port or 5060 }}"></div>
      <div class="col"><div class="label">Outbound Proxy (SBC) adres</div>
        <input class="input" id="sipSbc" placeholder="bijv. 10.0.13.254" autocomplete="off" value="{{ settings.sip_sbc_host or '' }}"></div>
    </div>
    <div class="row">
      <div class="col"><div class="label">Outbound Proxy (SBC) poort</div>
        <input class="input" type="number" id="sipSbcPort" value="{{ settings.sip_sbc_port or 5060 }}"></div>
      <div class="col"><div class="label">Max. omroepduur (seconden)</div>
        <input class="input" type="number" id="sipMax" value="{{ settings.sip_max_secs or 300 }}">
        <div class="help">Veiligheid tegen een &laquo;open microfoon&raquo;: het gesprek stopt automatisch na deze tijd.</div></div>
    </div>
    <div class="row">
      <div class="col">
        <div class="label">Volume van de beller over de speakers: <b><span id="sipGainVal">{{ settings.sip_gain or 100 }}</span>%</b></div>
        <input type="range" id="sipGain" min="0" max="200" step="5" value="{{ settings.sip_gain or 100 }}" oninput="document.getElementById('sipGainVal').textContent=this.value" style="width:100%;accent-color:var(--green)">
        <div class="help">100% = normaal. Klinkt de omroeper te zacht? Zet hoger (bijv. 130&ndash;160%). Te hard/vervormd? Lager. Werkt bij het eerstvolgende telefoontje.</div>
      </div>
    </div>
    <div style="height:6px"></div>
    <label class="switch-row"><input type="checkbox" id="sipIntro" {{ 'checked' if settings.sip_intro else '' }}> <span>Intro afspelen vóór de omroep</span></label>
    <label class="switch-row"><input type="checkbox" id="sipOutro" {{ 'checked' if settings.sip_outro else '' }}> <span>Outro afspelen ná de omroep</span></label>
    <div class="help" style="margin:6px 0 14px">Gebruikt dezelfde intro/outro als je presets en TTS (uploadbaar onder <b>Audio</b>).</div>

    <div class="label">Toegestane extensies</div>
    <input class="input" id="sipAllowed" placeholder="bijv. 301-309, 101, 103-105  (leeg = alle interne toestellen)" autocomplete="off" value="{{ (settings.sip_allowed_exts or [])|join(', ') }}">
    <div class="help" style="margin:4px 0 16px">Alleen deze toestellen mogen omroepen &mdash; losse nummers én <b>bereiken</b> (bijv. <code>301-309</code> = 301 t/m 309), gescheiden door komma&#39;s. <b>Leeg = alle interne toestellen.</b> Een <b>buitenlijn wordt altijd geweigerd</b> (alles met meer dan 3 cijfers), ook als 'ie hier zou staan.</div>

    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
      <button type="button" class="btn btn-primary btn-inline" style="width:auto" onclick="sipSave()"><span class="mi">save</span> Opslaan</button>
      <span id="sipSaveMsg" style="font-size:13px;display:none"></span>
    </div>
  </div>

  <div class="beheer-card">
    <h3 style="display:flex;align-items:center;gap:8px"><span class="mi">wifi_find</span> Verbinding &amp; registratie testen</h3>
    <div class="help" style="margin-bottom:10px">Controleert of de VM de <b>SBC</b> bereikt en of extensie <b>{{ settings.sip_extension or '(nog leeg)' }}</b> zich kan <b>registreren</b>. Werkt ook als de functie nog uit staat. Zegt precies wát er misgaat: SBC onbereikbaar, geweigerd, of gelukt.</div>
    <button type="button" class="btn btn-inline" style="width:auto" onclick="sipTestConn()"><span class="mi">wifi_find</span> Verbinding testen</button>
    <div id="sipConnRes" style="margin-top:12px;font-size:13px;display:none;padding:10px 12px;border-radius:10px;line-height:1.5"></div>
  </div>

  <div class="beheer-card">
    <h3 style="display:flex;align-items:center;gap:8px"><span class="mi">volume_up</span> Testen</h3>
    <div class="help" style="margin-bottom:10px">Speel een <b>testomroep</b> af over de winkelspeakers (dempen &rarr; intro &rarr; testboodschap &rarr; outro), precies zoals een echt telefoontje klinkt. Werkt ook <b>zonder</b> dat de SBC-registratie al rond is &mdash; handig om de speakers, intro/outro en het dempen te controleren.</div>
    <button type="button" class="btn btn-gold btn-inline" style="width:auto" onclick="sipTest()"><span class="mi">campaign</span> Testomroep afspelen</button>
    <span id="sipTestMsg" style="font-size:13px;display:none;margin-left:10px"></span>
    <div class="help" style="margin-top:12px"><b>Echte test:</b> staat de status hierboven op <span style="color:#2e7d32;font-weight:700">groen (geregistreerd)</span>, bel dan vanaf een 3CX-toestel <b>{{ settings.sip_extension or 'de extensie' }}</b> en spreek na het verbinden je omroep in. Ophangen = klaar.</div>
  </div>
  <script>
  (function(){
    function el(id){return document.getElementById(id);}
    window.sipStatusPoll=function(){
      fetch('/api/sip/status',{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
        var dot=el('sipDot'), txt=el('sipStatusTxt'), col, msg;
        if(!j.enabled){ col='#9aa0a6'; msg='Uitgeschakeld.'; }
        else if(j.in_call){ col='#1769aa'; msg='Bezig met een live omroep' + (j.caller_ext?(' — toestel '+j.caller_ext):'') + '…'; }
        else if(j.registered){ col='#2e7d32'; msg='Geregistreerd bij de SBC — bel '+(j.extension||'de extensie')+' om om te roepen.'; }
        else if(j.running){ col='#f9a825'; msg='Verbinden met de SBC… (nog niet geregistreerd — controleer firewall/3CX)'; }
        else if(!j.configured){ col='#9aa0a6'; msg='Nog niet volledig ingevuld.'; }
        else { col='#c62828'; msg='Niet verbonden.'; }
        dot.style.color=col; txt.textContent=msg;
      }).catch(function(){});
    };
    window.sipSave=function(){
      var body={
        sip_enabled:el('sipEnabled').checked,
        sip_extension:el('sipExt').value,
        sip_auth_id:el('sipAuthId').value,
        sip_auth_pass:el('sipAuthPass').value,
        sip_registrar_host:el('sipReg').value,
        sip_registrar_port:el('sipRegPort').value,
        sip_sbc_host:el('sipSbc').value,
        sip_sbc_port:el('sipSbcPort').value,
        sip_max_secs:el('sipMax').value,
        sip_gain:el('sipGain').value,
        sip_allowed_exts:el('sipAllowed').value,
        sip_intro:el('sipIntro').checked,
        sip_outro:el('sipOutro').checked
      };
      var m=el('sipSaveMsg'); m.style.display='inline'; m.style.color='#4b7a12'; m.textContent='Opslaan…';
      fetch('/admin/sip/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
        .then(function(r){return r.json();}).then(function(j){
          el('sipAuthPass').value='';
          m.textContent=j.ok?'Opgeslagen ✔':'Fout'; m.style.color=j.ok?'#4b7a12':'#c62828';
          setTimeout(function(){m.style.display='none';},3000);
          setTimeout(sipStatusPoll,1500);
        }).catch(function(){ m.textContent='Fout'; m.style.color='#c62828'; });
    };
    window.sipTestConn=function(){
      var box=el('sipConnRes'); box.style.display='block'; box.style.background='#fff8e1'; box.style.color='#7a5c00';
      box.innerHTML='<span class="mi mi-sm" style="vertical-align:middle">autorenew</span> Testen… (max ~10 sec)';
      fetch('/admin/sip/test_connection',{method:'POST'}).then(function(r){return r.json();}).then(function(j){
        var ok=j.ok, reg=j.registered;
        box.style.background = ok ? '#e8f5e9' : (reg===false ? '#fdecea' : '#fff8e1');
        box.style.color      = ok ? '#1b5e20' : (reg===false ? '#b71c1c' : '#7a5c00');
        var icon = ok ? 'check_circle' : (reg===false ? 'error' : 'warning');
        box.innerHTML='<span class="mi mi-sm" style="vertical-align:middle">'+icon+'</span> '+(j.msg||'Onbekend resultaat')+(j.dns?('<br><span style="opacity:.7">Registrar DNS: '+j.dns+'</span>'):'');
      }).catch(function(){ box.style.background='#fdecea'; box.style.color='#b71c1c'; box.textContent='Test mislukt.'; });
    };
    window.sipTest=function(){
      if(!confirm('Nu een testomroep over de winkelspeakers afspelen?')) return;
      var m=el('sipTestMsg'); m.style.display='inline'; m.style.color='#4b7a12';
      m.textContent='Speelt af… (dempen → intro → test → outro)';
      fetch('/admin/sip/test',{method:'POST'}).then(function(r){return r.json();}).then(function(j){
        m.textContent=j.ok?'Testomroep gestart ✔':(j.error||'Fout'); m.style.color=j.ok?'#4b7a12':'#c62828';
        setTimeout(function(){m.style.display='none';},6000);
      }).catch(function(){ m.textContent='Fout'; m.style.color='#c62828'; });
    };
    sipStatusPoll(); setInterval(sipStatusPoll,5000);
  })();
  </script>
</div>

<div class="bpanel" data-panel="ip">
  <style>
  .ip-row{border:1px solid var(--stroke);border-radius:12px;background:#fff;padding:14px;margin-bottom:12px}
  .ip-row-top{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap}
  .ip-row-top .ip-type{max-width:160px;flex:0 0 auto}
  .ip-row-top .ip-target{flex:1;min-width:180px}
  .ip-sub{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--fg3);margin:0 0 6px}
  .ip-toggles{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
  .ip-empty{color:var(--fg3);padding:8px 0 14px}
  </style>
  <div class="beheer-card">
    <h3>Toegangsregels</h3>
    <p class="help" style="margin-bottom:14px">Bepaal per <strong>apparaat (IP-adres)</strong> of per <strong>gebruiker</strong> welke pagina's zichtbaar zijn en of er een pincode-slot geldt. Zonder regel gelden de standaardinstellingen. Bij overlap wint de gebruiker-regel. <em>Geldt niet voor admins.</em></p>
    <form method="post" action="{{ url_for('save_ip_rules') }}" onsubmit="return ipSerialize()">
      <div id="ipRows"></div>
      <datalist id="userDatalist"></datalist>
      <div id="ipEmpty" class="ip-empty" style="display:none">Nog geen regels. Voeg er een toe met de knop hieronder.</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
        <button type="button" class="btn btn-sm btn-inline" onclick="ipAddRow('ip')" style="width:auto"><span class="mi">add</span> Apparaat (IP)</button>
        <button type="button" class="btn btn-sm btn-inline" onclick="ipAddRow('user')" style="width:auto"><span class="mi">add</span> Gebruiker</button>
      </div>
      <hr>
      <button class="btn btn-primary btn-inline" type="submit" style="min-width:150px"><span class="mi">save</span> Toegangsregels opslaan</button>
      <textarea name="ip_rules_json" id="ipJson" style="display:none"></textarea>
      <textarea name="user_rules_json" id="userJson" style="display:none"></textarea>
    </form>
    <details style="margin-top:16px">
      <summary class="help" style="cursor:pointer">Geavanceerd: ruwe JSON bekijken</summary>
      <div class="help" style="margin-top:8px">Apparaten (IP):</div>
      <pre class="mono" style="background:#f4f6f1;border:1px solid var(--stroke);border-radius:8px;padding:12px;overflow-x:auto;font-size:12px">{{ ip_rules_json }}</pre>
      <div class="help">Gebruikers:</div>
      <pre class="mono" style="background:#f4f6f1;border:1px solid var(--stroke);border-radius:8px;padding:12px;overflow-x:auto;font-size:12px">{{ user_rules_json }}</pre>
    </details>
  </div>

  <script>
  const IP_RULES = {{ ip_rules_json|safe }};
  const USER_RULES = {{ user_rules_json|safe }};
  const USERS_LIST = {{ users_list|safe }};
  function ipFillDatalist(){
    var dl=document.getElementById('userDatalist'); if(!dl) return;
    dl.innerHTML=USERS_LIST.map(function(x){ return '<option value="'+x.u+'">'+x.n+'</option>'; }).join('');
  }
  function ipRowHtml(kind, target, r){
    r = r || {}; var p = r.pages||{}, l = r.locks||{};
    function cb(k, on, lbl){ return '<label class="chip"><input type="checkbox" data-k="'+k+'"'+(on?' checked':'')+'> '+lbl+'</label>'; }
    var isUser = (kind==='user');
    return '<div class="ip-row" data-kind="'+kind+'">'
      + '<div class="ip-row-top">'
      +   '<select class="input ip-type" onchange="ipTypeChanged(this)">'
      +     '<option value="ip"'+(isUser?'':' selected')+'>Apparaat (IP)</option>'
      +     '<option value="user"'+(isUser?' selected':'')+'>Gebruiker</option>'
      +   '</select>'
      +   '<input class="input ip-target ip-ip" placeholder="IP-adres, bijv. 192.168.1.50" value="'+(isUser?'':(target||''))+'"'+(isUser?' style="display:none"':'')+'>'
      +   '<input class="input ip-target ip-user" list="userDatalist" placeholder="Typ gebruikersnaam of naam…" value="'+(isUser?(target||''):'')+'"'+(isUser?'':' style="display:none"')+'>'
      +   '<button type="button" class="btn btn-sm btn-danger" title="Regel verwijderen" style="width:auto" onclick="this.closest(\\'.ip-row\\').remove();ipCheckEmpty()"><span class="mi">delete</span></button>'
      + '</div>'
      + '<div class="ip-sub">Zichtbare pagina\\'s</div>'
      + '<div class="ip-toggles">'
      +   cb('vol', p.volume!==false, 'Volume') + cb('pre', p.presets!==false, 'Presets') + cb('tts', p.tts!==false, 'Text to Speech')
      + '</div>'
      + '<div class="ip-sub">Pincode-slot</div>'
      + '<div class="ip-toggles">'
      +   cb('lpre', !!l.presets, 'Presets-slot') + cb('ltts', !!l.tts, 'Text to Speech-slot')
      + '</div>'
      + '</div>';
  }
  function ipTypeChanged(sel){
    var row=sel.closest('.ip-row');
    var isUser=sel.value==='user';
    row.querySelector('.ip-ip').style.display=isUser?'none':'';
    row.querySelector('.ip-user').style.display=isUser?'':'none';
  }
  function ipAddRow(kind, target, r){
    document.getElementById('ipRows').insertAdjacentHTML('beforeend', ipRowHtml(kind||'ip', target, r));
    ipCheckEmpty();
    if(!target){ var rows=document.querySelectorAll('#ipRows .ip-row'); var last=rows[rows.length-1];
      var f=last.querySelector((kind==='user')?'.ip-user':'.ip-ip'); if(f) f.focus(); }
  }
  function ipCheckEmpty(){
    document.getElementById('ipEmpty').style.display =
      document.querySelectorAll('#ipRows .ip-row').length ? 'none' : 'block';
  }
  function ipSerialize(){
    var ipObj={}, userObj={};
    document.querySelectorAll('#ipRows .ip-row').forEach(function(row){
      var kind=row.querySelector('.ip-type').value;
      var target=(kind==='user') ? (row.querySelector('.ip-user').value||'').trim()
                                  : (row.querySelector('.ip-ip').value||'').trim();
      if(!target) return;
      function v(k){ var el=row.querySelector('[data-k="'+k+'"]'); return el?el.checked:false; }
      var rule={pages:{volume:v('vol'),presets:v('pre'),tts:v('tts')},locks:{presets:v('lpre'),tts:v('ltts')}};
      if(kind==='user') userObj[target]=rule; else ipObj[target]=rule;
    });
    document.getElementById('ipJson').value=JSON.stringify(ipObj);
    document.getElementById('userJson').value=JSON.stringify(userObj);
    return true;
  }
  (function(){
    ipFillDatalist();
    Object.keys(IP_RULES||{}).forEach(function(ip){ ipAddRow('ip', ip, IP_RULES[ip]); });
    Object.keys(USER_RULES||{}).forEach(function(u){ ipAddRow('user', u, USER_RULES[u]); });
    ipCheckEmpty();
  })();
  </script>
</div>

<!-- WOORDFILTER -->
<div class="bpanel" data-panel="woorden">
  <style>
  .wf-chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 6px;max-height:360px;overflow:auto;border:1px solid var(--stroke-light);border-radius:10px;padding:12px;background:#fafbf8}
  .wf-search{position:relative;max-width:360px;margin-top:14px}
  .wf-search input{width:100%;padding:10px 12px 10px 38px;border:1px solid var(--stroke);border-radius:999px;font:inherit;background:#fff}
  .wf-search input:focus{outline:none;border-color:var(--green-dark)}
  .wf-search .mi{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--fg3)}
  .wf-chip{display:inline-flex;align-items:center;gap:6px;background:#fdeceb;color:#c62828;border:1px solid #f1b7b0;border-radius:999px;padding:6px 8px 6px 12px;font-size:14px;font-weight:600}
  .wf-chip button{border:none;background:rgba(198,40,40,.12);color:#c62828;width:22px;height:22px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;line-height:1;padding:0}
  .wf-chip button:hover{background:rgba(198,40,40,.22)}
  .wf-add{display:flex;gap:8px;flex-wrap:wrap;align-items:center;max-width:420px}
  </style>
  <div class="beheer-card">
    <h3>Woordfilter</h3>
    <p class="help" style="margin-bottom:12px">Deze woorden worden geblokkeerd bij Text to Speech-omroepen: het afspelen/genereren wordt geweigerd en de gebruiker krijgt een melding. Hoofdletter-ongevoelig, op hele woorden.</p>
    <form method="post" action="{{ url_for('save_blocked_words') }}" onsubmit="return wfSerialize()">
      <div class="wf-add">
        <input class="input" id="wfInput" placeholder="Woord toevoegen…" onkeydown="if(event.key==='Enter'){event.preventDefault();wfAdd();}">
        <button type="button" class="btn btn-inline" style="width:auto" onclick="wfAdd()"><span class="mi">add</span> Toevoegen</button>
      </div>
      <div class="wf-search"><span class="mi">search</span><input id="wfSearch" placeholder="Zoek een woord…" oninput="wfRender()"></div>
      <div class="wf-chips" id="wfChips"></div>
      <div id="wfCount" class="help" style="margin-bottom:12px"></div>
      <input type="hidden" name="blocked_words_json" id="wfJson">
      <button class="btn btn-primary btn-inline" type="submit" style="min-width:150px"><span class="mi">save</span> Woordfilter opslaan</button>
    </form>
  </div>
  <script>
  var WF_WORDS = {{ blocked_words_json|safe }};
  function wfRender(){
    var c=document.getElementById('wfChips'); c.innerHTML='';
    var q=((document.getElementById('wfSearch')||{}).value||'').toLowerCase().trim();
    var shown=0;
    WF_WORDS.slice().sort().forEach(function(w){
      if(q && (''+w).toLowerCase().indexOf(q)<0) return;
      shown++;
      var el=document.createElement('span'); el.className='wf-chip';
      el.appendChild(document.createTextNode(w));
      var b=document.createElement('button'); b.type='button'; b.title='Verwijderen'; b.textContent='×';
      b.onclick=function(){ var i=WF_WORDS.indexOf(w); if(i>=0)WF_WORDS.splice(i,1); wfRender(); };
      el.appendChild(b); c.appendChild(el);
    });
    document.getElementById('wfCount').textContent = q ? (shown+' van '+WF_WORDS.length+' woorden') : (WF_WORDS.length+' woorden');
  }
  function wfAdd(){
    var inp=document.getElementById('wfInput');
    var v=(inp.value||'').trim().toLowerCase();
    if(v && WF_WORDS.indexOf(v)<0){ WF_WORDS.push(v); wfRender(); }
    inp.value=''; inp.focus();
  }
  function wfSerialize(){ document.getElementById('wfJson').value=JSON.stringify(WF_WORDS); return true; }
  wfRender();
  </script>
</div>

<!-- SNEL INVOEGEN -->
<div class="bpanel" data-panel="snel">
  <style>
  .sw-chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 16px}
  .sw-chip{display:inline-flex;align-items:center;gap:6px;background:#eaf4d8;color:#4b7a12;border:1px solid #cbe3a0;border-radius:999px;padding:6px 8px 6px 12px;font-size:14px;font-weight:600}
  .sw-chip button{border:none;background:rgba(75,122,18,.14);color:#4b7a12;width:22px;height:22px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;line-height:1;padding:0}
  .sw-chip button:hover{background:rgba(75,122,18,.26)}
  </style>
  <div class="beheer-card">
    <h3>Snel invoegen (Text to Speech)</h3>
    <p class="help" style="margin-bottom:14px">Deze knoppen verschijnen op de Text to Speech-pagina om veelgebruikte woorden met één tik in te voegen.</p>
    <form method="post" action="{{ url_for('save_quick_words') }}" onsubmit="return swSerialize()">
      <div class="label">Standaard begintekst</div>
      <input class="input" name="tts_prefill" value="{{ tts_prefill_val }}" placeholder="bijv. Attentie, " style="max-width:360px;margin-bottom:4px">
      <div class="help" style="margin-bottom:16px">Staat automatisch al in het tekstvak. Laat leeg voor een leeg vak.</div>
      <div class="label">Snelknoppen</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;max-width:420px">
        <input class="input" id="swInput" placeholder="Woord toevoegen…" onkeydown="if(event.key==='Enter'){event.preventDefault();swAdd();}">
        <button type="button" class="btn btn-inline" style="width:auto" onclick="swAdd()"><span class="mi">add</span> Toevoegen</button>
      </div>
      <div class="sw-chips" id="swChips"></div>
      <input type="hidden" name="quick_words_json" id="swJson">
      <button class="btn btn-primary btn-inline" type="submit" style="min-width:150px"><span class="mi">save</span> Snelknoppen opslaan</button>
    </form>
  </div>
  <script>
  var SW_WORDS = {{ quick_words_json|safe }};
  function swRender(){
    var c=document.getElementById('swChips'); c.innerHTML='';
    SW_WORDS.forEach(function(w){
      var el=document.createElement('span'); el.className='sw-chip';
      el.appendChild(document.createTextNode(w));
      var b=document.createElement('button'); b.type='button'; b.title='Verwijderen'; b.textContent='×';
      b.onclick=function(){ var i=SW_WORDS.indexOf(w); if(i>=0)SW_WORDS.splice(i,1); swRender(); };
      el.appendChild(b); c.appendChild(el);
    });
  }
  function swAdd(){
    var inp=document.getElementById('swInput'); var v=(inp.value||'').trim();
    var lc=SW_WORDS.map(function(x){return (''+x).toLowerCase();});
    if(v && lc.indexOf(v.toLowerCase())<0){ SW_WORDS.push(v); swRender(); }
    inp.value=''; inp.focus();
  }
  function swSerialize(){ document.getElementById('swJson').value=JSON.stringify(SW_WORDS); return true; }
  swRender();
  </script>
</div>

<!-- SCHEMA'S -->
<div class="bpanel" data-panel="schema">
  <style>
  .am-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;flex-wrap:wrap}
  .am-list{display:flex;flex-direction:column;gap:10px}
  .am-row{display:flex;align-items:center;gap:14px;background:#fff;border:1px solid var(--stroke);border-radius:14px;box-shadow:var(--shadow-sm);padding:14px 16px}
  .am-row.off{opacity:.6}
  .am-ic{width:40px;height:40px;border-radius:10px;background:var(--accent-soft);color:var(--green-dark);display:flex;align-items:center;justify-content:center;flex:0 0 auto}
  .am-ic .mi{font-size:22px}
  .am-info{flex:1;min-width:0}
  .am-name{font-weight:800;color:var(--green-dark);font-size:15px}
  .am-sub{font-size:12px;color:var(--fg3);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .am-acts{display:flex;align-items:center;gap:6px;flex:0 0 auto}
  .am-sw{position:relative;width:44px;height:26px;flex:0 0 auto;cursor:pointer}
  .am-sw input{opacity:0;width:0;height:0;position:absolute}
  .am-sw .tr{position:absolute;inset:0;background:#c9cec2;border-radius:999px;transition:.15s}
  .am-sw .kn{position:absolute;top:3px;left:3px;width:20px;height:20px;background:#fff;border-radius:50%;transition:.15s;box-shadow:0 1px 3px rgba(0,0,0,.3)}
  .am-sw input:checked + .tr{background:var(--red)}
  .am-sw input:checked + .tr + .kn{transform:translateX(18px)}
  .am-iconbtn{width:38px;height:38px;border-radius:10px;border:1px solid var(--stroke);background:#fff;color:var(--fg2);cursor:pointer;display:flex;align-items:center;justify-content:center}
  .am-iconbtn:hover{background:var(--btnh)}
  .am-iconbtn.danger{color:var(--dangertext);border-color:var(--dangerborder)}
  .am-empty{color:var(--fg3);padding:24px;text-align:center}
  .am-sec-h{font-size:18px;font-weight:800;color:var(--green-dark);margin:20px 0 4px}
  .am-sec-sub{font-size:13px;color:var(--fg3);margin-bottom:10px}
  .am-erow{display:flex;gap:12px;align-items:flex-start;margin-bottom:10px;background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:12px 14px;box-shadow:var(--shadow-sm)}
  .am-arow{background:#fff;border:1px solid var(--stroke);border-radius:12px;margin-bottom:10px;box-shadow:var(--shadow-sm);overflow:hidden}
  .am-arow.open{border-color:var(--red)}
  .am-arow-head{display:flex;gap:12px;align-items:center;padding:12px 14px;cursor:pointer}
  .am-arow-head:hover{background:var(--bg-soft)}
  .am-arow-body{padding:0 14px 14px;display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start;border-top:1px solid var(--stroke-light)}
  .am-arow-body>*{margin-top:12px}
  .am-rowic{width:38px;height:38px;border-radius:10px;background:var(--accent-soft);color:var(--green-dark);display:flex;align-items:center;justify-content:center;flex:0 0 auto}
  .am-rowic .mi{font-size:22px}
  .am-rowbody{flex:1;min-width:0;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .am-addbtn{border:none;background:var(--red);color:var(--on-primary);border-radius:999px;padding:10px 18px;font-weight:700;font-size:14px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;margin:2px 0 8px}
  .am-addbtn:hover{background:var(--red-dark)}
  .am-daychips{display:flex;gap:4px;flex-wrap:wrap}
  .am-day{padding:5px 9px;border:1px solid var(--stroke);border-radius:999px;font-size:12px;cursor:pointer;background:#fff;color:var(--fg2);user-select:none}
  .am-day.on{background:var(--accent-soft);border-color:var(--red);color:var(--green-dark);font-weight:700}
  .am-afields{display:flex;gap:8px;flex-wrap:wrap;align-items:center;flex:1;min-width:0}
  .am-mb .modal{max-width:640px}
  .am-picker{flex:1;min-width:240px}
  .am-search{margin-bottom:6px}
  .am-checklist{max-height:170px;overflow:auto;border:1px solid var(--stroke);border-radius:8px;background:#fff;padding:4px}
  .am-prow{display:flex;align-items:center;gap:8px;padding:6px 7px;border-radius:6px;cursor:pointer;font-size:13px;color:var(--fg2)}
  .am-prow:hover{background:var(--bg-soft)}
  .am-prow input{width:18px;height:18px;flex:0 0 auto;accent-color:var(--red)}
  .am-order{margin-top:8px}
  .am-chip{display:flex;align-items:center;justify-content:space-between;gap:8px;background:var(--accent-soft);color:var(--green-dark);border-radius:8px;padding:7px 12px;font-size:13px;font-weight:700;margin:0 0 5px 0;width:100%}
  .am-chip .x{cursor:pointer;font-weight:800;color:var(--dangertext);font-size:16px;flex:0 0 auto}
  .am-picktype{display:flex;align-items:center;gap:12px;padding:12px;border:1px solid var(--stroke);border-radius:12px;margin-bottom:8px;cursor:pointer;background:#fff}
  .am-picktype:hover{background:var(--bg-soft);border-color:var(--red)}
  </style>
  <div class="am-top">
    <div><h1 style="margin:0">Automatiseringen</h1><div class="help">Triggers op tijd/dag &rarr; acties (presets, RCA, volume, kanaal, TTS). Vervangt HA-automatiseringen.</div></div>
    <button class="btn btn-primary btn-inline" style="width:auto;flex:0 0 auto" onclick="amNew()"><span class="mi">add</span> Nieuwe automatisering</button>
  </div>
  <div class="am-list" id="amList"><div class="am-empty">Laden&hellip;</div></div>
</div>

<!-- Editor-modal voor automatiseringen -->
<div id="amModal" class="modal-backdrop am-mb" onclick="if(event.target===this)amClose()">
  <div class="modal">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <h3 style="margin:0" id="amTitle">Automatisering</h3>
      <button class="btn btn-inline btn-sm" style="width:auto;padding:6px 12px" onclick="amClose()"><span class="mi">close</span></button>
    </div>
    <div class="label">Naam</div>
    <input class="input" id="amName" placeholder="bijv. Avond omroep sluit" style="margin-bottom:8px">
    <div class="am-sec-h">Wanneer</div>
    <div class="am-sec-sub">Op welke tijd(en)/dag(en) &mdash; of via een webhook &mdash; moet deze automatisering starten.</div>
    <div id="amTriggers"></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="am-addbtn" onclick="amAddTrigger()"><span class="mi">schedule</span> Tijd-trigger</button>
      <button class="am-addbtn" onclick="amAddWebhookTrigger()"><span class="mi">webhook</span> Webhook-trigger</button>
    </div>
    <div class="am-sec-h">Voorwaarden <span class="help" style="font-weight:400">(optioneel)</span></div>
    <div class="am-sec-sub">De acties draaien alleen als <select id="amCondMode" class="input" style="width:auto;display:inline-block;padding:2px 8px;min-height:auto" onchange="_amEdit.condition_mode=this.value"><option value="all">alle</option><option value="any">&eacute;&eacute;n</option></select> van deze voorwaarden klopt.</div>
    <div id="amConditions"></div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="am-addbtn" onclick="amAddCond('rca')"><span class="mi">cable</span> RCA</button>
      <button class="am-addbtn" onclick="amAddCond('spotify')"><span class="mi">music_note</span> Spotify</button>
      <button class="am-addbtn" onclick="amAddCond('time_between')"><span class="mi">schedule</span> Tussen tijden</button>
      <button class="am-addbtn" onclick="amAddCond('day')"><span class="mi">event</span> Dag</button>
    </div>
    <div class="am-sec-h">Doe dan</div>
    <div class="am-sec-sub">De acties worden in deze volgorde uitgevoerd.</div>
    <div id="amActions"></div>
    <button class="am-addbtn" onclick="amOpenPick()"><span class="mi">add</span> Actie toevoegen</button>
    <hr>
    <label class="switch-row" style="margin-bottom:12px"><input type="checkbox" id="amEnabled" checked> <span>Ingeschakeld</span></label>
    <div style="display:flex;gap:8px">
      <button class="btn btn-primary btn-inline" style="width:auto" onclick="amSave()"><span class="mi">save</span> Opslaan</button>
      <button class="btn btn-inline" style="width:auto" onclick="amClose()">Annuleren</button>
    </div>
  </div>
</div>

<!-- Actietype-kiezer (zoals HA 'Actie toevoegen') -->
<div id="amPick" class="modal-backdrop am-mb" style="z-index:10001" onclick="if(event.target===this)amClosePick()">
  <div class="modal" style="max-width:520px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
      <h3 style="margin:0">Actie toevoegen</h3>
      <button class="btn btn-inline btn-sm" style="width:auto;padding:6px 12px" onclick="amClosePick()"><span class="mi">close</span></button>
    </div>
    <input class="input am-search" id="amPickQ" placeholder="Zoeken&hellip;" oninput="amPickFilter(this.value)" style="margin-bottom:10px">
    <div id="amPickList"></div>
  </div>
</div>

<script>
var AM_PRESETS = {{ am_presets|safe }};
var AM_DAYS = [['Mon','Ma'],['Tue','Di'],['Wed','Wo'],['Thu','Do'],['Fri','Vr'],['Sat','Za'],['Sun','Zo']];
var _amEdit = null;   // automation in bewerking
var _amOpenAction = null;   // welke actie-regel is uitgeklapt (accordion)
function amEsc(s){ return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function amPresetName(id){ var p=AM_PRESETS.find(function(x){return x.id==id;}); return p?(p.id+'. '+p.name):('Preset '+id); }
function amDaysShort(days){
  if(!days||!days.length) return 'elke dag';
  return AM_DAYS.filter(function(d){return days.indexOf(d[0])>=0;}).map(function(d){return d[1];}).join(' ');
}
function amTrigSummary(a){
  var s=(a.triggers||[]).map(function(t){ return t.type==='webhook'?'webhook':(t.time+' ('+amDaysShort(t.days)+')'); }).join(' · ')||'geen trigger';
  var nc=(a.conditions||[]).length; if(nc) s+=' · '+nc+' voorwaarde'+(nc>1?'n':'');
  return s;
}
function amActSummary(a){
  return (a.actions||[]).map(function(ac){
    if(ac.type==='preset_sequence') return 'Preset '+(ac.presets||[]).join('→');
    if(ac.type==='rca') return 'RCA '+(ac.state==='off'?'uit':'aan');
    if(ac.type==='rca_auto') return 'RCA-automatiek '+(ac.state==='off'?'uit':'aan');
    if(ac.type==='volume') return 'Volume '+ac.value+'%';
    if(ac.type==='channel') return 'Kanaal '+(ac.channel==2?'Plus Easy':'Plus Main');
    if(ac.type==='tts') return 'TTS';
    if(ac.type==='spotify') return 'Spotify: '+(ac.command==='source'?('bron '+((ac.source==='gui')?'Automix':'omroepweb')):(ac.command||''));
    if(ac.type==='webhook') return 'Webhook';
    if(ac.type==='wait') return 'Wacht '+ac.seconds+'s';
    return ac.type;
  }).join(' · ')||'geen acties';
}
function amAgo(ts){ if(!ts) return 'nooit'; var d=new Date(ts*1000); return d.toLocaleDateString('nl-NL',{day:'numeric',month:'short'})+' '+('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2); }
function amLoad(){
  fetch("{{ url_for('api_automations') }}",{cache:'no-store'}).then(function(r){return r.json();}).then(function(j){
    var list=j.automations||[]; var el=document.getElementById('amList');
    if(!list.length){ el.innerHTML='<div class="am-empty">Nog geen automatiseringen. Klik op &laquo;Nieuwe automatisering&raquo;.</div>'; return; }
    el.innerHTML=list.map(function(a){
      return '<div class="am-row'+(a.enabled?'':' off')+'">'+
        '<div class="am-ic"><span class="mi">bolt</span></div>'+
        '<div class="am-info"><div class="am-name">'+amEsc(a.name)+'</div>'+
        '<div class="am-sub">'+amEsc(amTrigSummary(a))+' &nbsp;•&nbsp; '+amEsc(amActSummary(a))+'</div>'+
        '<div class="am-sub" style="color:var(--fg3)">Laatst: '+amAgo(a.last_run)+'</div></div>'+
        '<div class="am-acts">'+
          '<label class="am-sw" title="Aan/uit"><input type="checkbox" '+(a.enabled?'checked':'')+' onchange="amToggle('+a.id+')"><span class="tr"></span><span class="kn"></span></label>'+
          '<button class="am-iconbtn" title="Nu testen" onclick="amTest('+a.id+')"><span class="mi">play_arrow</span></button>'+
          '<button class="am-iconbtn" title="Bewerken" onclick="amEditId('+a.id+')"><span class="mi">edit</span></button>'+
          '<button class="am-iconbtn danger" title="Verwijderen" onclick="amDel('+a.id+')"><span class="mi">delete</span></button>'+
        '</div></div>';
    }).join('');
    window._amCache=list;
  }).catch(function(){});
}
function amToggle(id){ fetch("/admin/automation/toggle/"+id,{method:'POST'}).then(function(){amLoad();}); }
function amDel(id){ if(!confirm('Automatisering verwijderen?'))return; fetch("/admin/automation/delete/"+id,{method:'POST'}).then(function(){amLoad();}); }
function amTest(id){ fetch("/admin/automation/run/"+id,{method:'POST'}).then(function(){}); }
function amClose(){ document.getElementById('amModal').style.display='none'; }
function amNew(){ _amEdit={id:null,name:'',enabled:true,triggers:[],conditions:[],condition_mode:'all',actions:[]}; amFill(); }
function amEditId(id){ var a=(window._amCache||[]).find(function(x){return x.id==id;}); if(a){ _amEdit=JSON.parse(JSON.stringify(a)); amFill(); } }
function amFill(){
  _amOpenAction=null;   // alles ingeklapt bij openen (compact)
  document.getElementById('amTitle').textContent=_amEdit.id?'Automatisering bewerken':'Nieuwe automatisering';
  document.getElementById('amName').value=_amEdit.name||'';
  document.getElementById('amEnabled').checked=_amEdit.enabled!==false;
  if(!_amEdit.conditions) _amEdit.conditions=[];
  if(!_amEdit.condition_mode) _amEdit.condition_mode='all';
  var cm=document.getElementById('amCondMode'); if(cm) cm.value=_amEdit.condition_mode;
  amRenderTriggers(); amRenderConditions(); amRenderActions();
  document.getElementById('amModal').style.display='flex';
}
var AM_CTYPES={rca:['cable','PLUS Radio (RCA)'],spotify:['music_note','Spotify'],time_between:['schedule','Tussen tijden'],day:['event','Op dag(en)']};
function amNewCond(t){
  if(t==='rca') return {type:t,state:'on'};
  if(t==='spotify') return {type:t,state:'playing'};
  if(t==='time_between') return {type:t,after:'21:00',before:'23:59'};
  if(t==='day') return {type:t,days:['Mon','Tue','Wed','Thu','Fri','Sat']};
  return {type:t};
}
function amAddCond(t){ _amEdit.conditions.push(amNewCond(t)); amRenderConditions(); }
function amCondFields(c,i){
  if(c.type==='rca') return '<select class="input" style="max-width:150px" onchange="_amEdit.conditions['+i+'].state=this.value"><option value="on" '+(c.state!=='off'?'selected':'')+'>staat AAN</option><option value="off" '+(c.state==='off'?'selected':'')+'>staat UIT</option></select>';
  if(c.type==='spotify') return '<select class="input" style="max-width:150px" onchange="_amEdit.conditions['+i+'].state=this.value"><option value="playing" '+(c.state!=='stopped'?'selected':'')+'>speelt</option><option value="stopped" '+(c.state==='stopped'?'selected':'')+'>speelt niet</option></select>';
  if(c.type==='time_between') return '<span class="help">tussen</span> <input class="input" type="time" style="max-width:115px" value="'+(c.after||'')+'" onchange="_amEdit.conditions['+i+'].after=this.value"> <span class="help">en</span> <input class="input" type="time" style="max-width:115px" value="'+(c.before||'')+'" onchange="_amEdit.conditions['+i+'].before=this.value">';
  if(c.type==='day') return '<div class="am-daychips" data-ci="'+i+'">'+amDayChips(c.days||[])+'</div>';
  return '';
}
function amRenderConditions(){
  var w=document.getElementById('amConditions'); if(!w) return;
  w.innerHTML=(_amEdit.conditions||[]).map(function(c,i){
    var t=AM_CTYPES[c.type]||['rule',c.type];
    return '<div class="am-erow"><div class="am-rowic"><span class="mi">'+t[0]+'</span></div><div class="am-rowbody" style="align-items:center;flex-wrap:wrap;gap:6px">'+
      '<span style="font-weight:700;color:var(--green-dark);margin-right:2px">'+t[1]+'</span>'+amCondFields(c,i)+
      '</div><button class="am-iconbtn danger" onclick="_amEdit.conditions.splice('+i+',1);amRenderConditions()"><span class="mi">close</span></button></div>';
  }).join('');
  w.querySelectorAll('.am-daychips').forEach(function(box){
    var ci=+box.dataset.ci;
    box.querySelectorAll('.am-day').forEach(function(ch){
      ch.onclick=function(){ var d=ch.dataset.d; var arr=_amEdit.conditions[ci].days=_amEdit.conditions[ci].days||[];
        var k=arr.indexOf(d); if(k>=0)arr.splice(k,1); else arr.push(d); ch.classList.toggle('on'); };
    });
  });
}
function amDayChips(days, cb){
  return AM_DAYS.map(function(d){
    return '<span class="am-day'+(days.indexOf(d[0])>=0?' on':'')+'" data-d="'+d[0]+'">'+d[1]+'</span>';
  }).join('');
}
function amRenderTriggers(){
  var w=document.getElementById('amTriggers');
  w.innerHTML=(_amEdit.triggers||[]).map(function(t,i){
    if(t.type==='webhook'){
      var inner=t.token
        ? '<code style="font-size:11px;background:var(--btnh);padding:4px 8px;border-radius:6px;word-break:break-all">'+location.origin+'/hook/automation/'+t.token+'</code><button class="am-addbtn" onclick="amCopyHook('+i+')"><span class="mi">content_copy</span> Kopieer</button>'
        : '<span class="help">De webhook-URL verschijnt zodra je opslaat.</span>';
      return '<div class="am-erow"><div class="am-rowic"><span class="mi">webhook</span></div><div class="am-rowbody" style="align-items:center;flex-wrap:wrap;gap:6px">'+inner+
        '</div><button class="am-iconbtn danger" onclick="_amEdit.triggers.splice('+i+',1);amRenderTriggers()"><span class="mi">close</span></button></div>';
    }
    return '<div class="am-erow"><div class="am-rowic"><span class="mi">schedule</span></div><div class="am-rowbody">'+
      '<input class="input" type="time" style="max-width:120px" value="'+(t.time||'')+'" onchange="_amEdit.triggers['+i+'].time=this.value">'+
      '<div class="am-daychips" data-ti="'+i+'">'+amDayChips(t.days||[])+'</div>'+
      '</div><button class="am-iconbtn danger" onclick="_amEdit.triggers.splice('+i+',1);amRenderTriggers()"><span class="mi">close</span></button></div>';
  }).join('');
  w.querySelectorAll('.am-daychips').forEach(function(box){
    var ti=+box.dataset.ti;
    box.querySelectorAll('.am-day').forEach(function(ch){
      ch.onclick=function(){ var d=ch.dataset.d; var arr=_amEdit.triggers[ti].days=_amEdit.triggers[ti].days||[];
        var k=arr.indexOf(d); if(k>=0)arr.splice(k,1); else arr.push(d); ch.classList.toggle('on'); };
    });
  });
}
function amCopyHook(i){ var t=_amEdit.triggers[i]; if(!t||!t.token)return; navigator.clipboard.writeText(location.origin+'/hook/automation/'+t.token).then(function(){alert('Webhook-URL gekopieerd');}).catch(function(){}); }
function amAddTrigger(){ _amEdit.triggers.push({time:'12:00',days:['Mon','Tue','Wed','Thu','Fri','Sat']}); amRenderTriggers(); }
function amAddWebhookTrigger(){ _amEdit.triggers.push({type:'webhook',token:''}); amRenderTriggers(); }
var AM_ATYPES=[
  ['preset_sequence','Preset(s) afspelen','queue_music','Speel één of meer presets in volgorde af (intro vóór de eerste, outro ná de laatste).'],
  ['rca','PLUS Radio aan/uit','cable','Zet de winkelmuziek (RCA) aan of uit.'],
  ['rca_auto','RCA-automatiek aan/uit','sync','Zet "RCA wijkt automatisch voor Spotify" aan of uit. UIT houdt RCA uit bij een gesloten winkel.'],
  ['volume','Volume zetten','volume_up','Zet het PLUS Radio-volume op een vaste waarde.'],
  ['channel','Kanaal wisselen','radio','Wissel tussen Plus Main en Plus Easy.'],
  ['tts','TTS uitspreken','record_voice_over','Laat een tekst omroepen (tekst-naar-spraak).'],
  ['spotify','Spotify bedienen','play_circle','Pauzeer/hervat, volgende/vorige, stop of zet het Spotify-volume.'],
  ['webhook','Webhook aanroepen','webhook','Roep een externe URL aan (bijv. Home Assistant).'],
  ['wait','Wachten','timer','Pauzeer een aantal seconden voor de volgende actie.']
];
function amAT(t){ return AM_ATYPES.find(function(x){return x[0]===t;})||['','','bolt','']; }
function amNewAction(t){
  if(t==='preset_sequence') return {type:t,presets:[],intro:true,outro:true};
  if(t==='rca') return {type:t,state:'on'};
  if(t==='rca_auto') return {type:t,state:'off'};
  if(t==='volume') return {type:t,value:65};
  if(t==='channel') return {type:t,channel:1};
  if(t==='tts') return {type:t,text:'',gain:100,intro:true,outro:false};
  if(t==='spotify') return {type:t,command:'pause',value:50};
  if(t==='webhook') return {type:t,url:'',method:'POST',body:''};
  if(t==='wait') return {type:t,seconds:5};
  return {type:t};
}
// Actietype-kiezer (zoals HA)
function amOpenPick(){ amPickRender(''); document.getElementById('amPick').style.display='flex'; var q=document.getElementById('amPickQ'); if(q){q.value='';q.focus();} }
function amClosePick(){ document.getElementById('amPick').style.display='none'; }
function amPickRender(f){
  f=(f||'').toLowerCase().trim();
  document.getElementById('amPickList').innerHTML=AM_ATYPES.filter(function(t){
    return !f || t[1].toLowerCase().indexOf(f)>=0 || t[3].toLowerCase().indexOf(f)>=0;
  }).map(function(t){
    return '<div class="am-picktype" onclick="amPickChoose(\\''+t[0]+'\\')"><div class="am-rowic"><span class="mi">'+t[2]+'</span></div>'+
      '<div style="min-width:0"><div style="font-weight:700;color:var(--green-dark)">'+t[1]+'</div><div class="help">'+t[3]+'</div></div></div>';
  }).join('')||'<div class="help" style="padding:10px">Geen resultaten.</div>';
}
function amPickFilter(v){ amPickRender(v); }
function amPickChoose(t){ _amEdit.actions.push(amNewAction(t)); _amOpenAction=_amEdit.actions.length-1; amClosePick(); amRenderActions(); }
function amPresetOrderHtml(i){
  var ids=(_amEdit.actions[i].presets||[]);
  if(!ids.length) return '<span class="help">Nog geen preset gekozen &mdash; vink hierboven aan. De <b>volgorde</b> is de aanvinkvolgorde.</span>';
  return '<div class="help" style="margin-bottom:4px">Speelt in deze volgorde:</div>'+ids.map(function(id,k){
    return '<span class="am-chip">'+(k+1)+'. '+amEsc(amPresetName(id))+'<span class="x" onclick="amPresetToggle('+i+','+id+',false)">&times;</span></span>';
  }).join('');
}
function amPresetToggle(i,id,on){
  var arr=_amEdit.actions[i].presets=_amEdit.actions[i].presets||[];
  var k=arr.indexOf(id);
  if(on && k<0) arr.push(id);
  if(!on && k>=0) arr.splice(k,1);
  var ord=document.getElementById('amord'+i); if(ord) ord.innerHTML=amPresetOrderHtml(i);
  var list=document.getElementById('amlist'+i);
  if(list){ var cb=list.querySelector('.am-prow[data-id="'+id+'"] input'); if(cb) cb.checked=arr.indexOf(id)>=0; }
}
function amPresetFilter(i,q){
  q=(q||'').toLowerCase().trim();
  var list=document.getElementById('amlist'+i); if(!list) return;
  list.querySelectorAll('.am-prow').forEach(function(r){
    var hit=!q || r.dataset.name.indexOf(q)>=0 || r.dataset.id.indexOf(q)===0;
    r.style.display=hit?'':'none';
  });
}
function amActFields(ac,i){
  if(ac.type==='preset_sequence'){
    var rows=AM_PRESETS.map(function(p){
      var on=(ac.presets||[]).indexOf(p.id)>=0;
      return '<label class="am-prow" data-id="'+p.id+'" data-name="'+amEsc((p.name||'').toLowerCase())+'"><input type="checkbox" '+(on?'checked':'')+' onchange="amPresetToggle('+i+','+p.id+',this.checked)"><span>'+amEsc(p.id+'. '+p.name)+'</span></label>';
    }).join('');
    return '<div class="am-picker">'+
        '<input class="input am-search" placeholder="Zoek preset op naam of nummer&hellip;" oninput="amPresetFilter('+i+',this.value)">'+
        '<div class="am-checklist" id="amlist'+i+'">'+rows+'</div>'+
        '<div class="am-order" id="amord'+i+'">'+amPresetOrderHtml(i)+'</div>'+
      '</div>'+
      '<div style="display:flex;flex-direction:column;gap:2px">'+
        '<label class="switch-row" style="min-height:auto"><input type="checkbox" '+(ac.intro!==false?'checked':'')+' onchange="_amEdit.actions['+i+'].intro=this.checked"> <span>intro</span></label>'+
        '<label class="switch-row" style="min-height:auto"><input type="checkbox" '+(ac.outro!==false?'checked':'')+' onchange="_amEdit.actions['+i+'].outro=this.checked"> <span>outro</span></label>'+
      '</div>';
  }
  if(ac.type==='rca') return '<select class="input" style="max-width:130px" onchange="_amEdit.actions['+i+'].state=this.value"><option value="on" '+(ac.state!=='off'?'selected':'')+'>Aan</option><option value="off" '+(ac.state==='off'?'selected':'')+'>Uit</option></select>';
  if(ac.type==='rca_auto') return '<select class="input" style="max-width:130px" onchange="_amEdit.actions['+i+'].state=this.value"><option value="on" '+(ac.state!=='off'?'selected':'')+'>Aan</option><option value="off" '+(ac.state==='off'?'selected':'')+'>Uit</option></select>';
  if(ac.type==='volume') return '<input class="input" type="number" min="0" max="100" style="max-width:110px" value="'+(ac.value!=null?ac.value:65)+'" onchange="_amEdit.actions['+i+'].value=+this.value"><span class="help">%</span>';
  if(ac.type==='channel') return '<select class="input" style="max-width:160px" onchange="_amEdit.actions['+i+'].channel=+this.value"><option value="1" '+(ac.channel!=2?'selected':'')+'>Plus Main</option><option value="2" '+(ac.channel==2?'selected':'')+'>Plus Easy</option></select>';
  if(ac.type==='tts') return '<div style="display:flex;flex-direction:column;gap:6px;flex:1;min-width:200px">'+
    '<input class="input" placeholder="tekst om uit te spreken" value="'+amEsc(ac.text||'')+'" onchange="_amEdit.actions['+i+'].text=this.value">'+
    '<div style="display:flex;gap:16px">'+
      '<label class="switch-row" style="min-height:auto"><input type="checkbox" '+(ac.intro!==false?'checked':'')+' onchange="_amEdit.actions['+i+'].intro=this.checked"> <span>intro (bel vooraf)</span></label>'+
      '<label class="switch-row" style="min-height:auto"><input type="checkbox" '+(ac.outro?'checked':'')+' onchange="_amEdit.actions['+i+'].outro=this.checked"> <span>outro (bel na)</span></label>'+
    '</div></div>';
  if(ac.type==='spotify'){
    var cmds=[['pause','Pauzeren'],['resume','Hervatten'],['playpause','Play/Pauze'],['next','Volgende'],['prev','Vorige'],['stop','Stoppen'],['volume','Volume zetten'],['source','Bron kiezen']];
    var s='<select class="input" style="max-width:170px" onchange="_amEdit.actions['+i+'].command=this.value;amRenderActions()">'+cmds.map(function(c){return '<option value="'+c[0]+'" '+(ac.command===c[0]?'selected':'')+'>'+c[1]+'</option>';}).join('')+'</select>';
    if(ac.command==='volume') s+=' <input class="input" type="number" min="0" max="100" style="max-width:100px" value="'+(ac.value!=null?ac.value:50)+'" onchange="_amEdit.actions['+i+'].value=+this.value"><span class="help">%</span>';
    if(ac.command==='source'){ var srcs=[['omroepweb','omroepweb'],['gui','Automix (desktop)']]; s+=' <select class="input" style="max-width:180px" onchange="_amEdit.actions['+i+'].source=this.value">'+srcs.map(function(c){return '<option value="'+c[0]+'" '+((ac.source||'omroepweb')===c[0]?'selected':'')+'>'+c[1]+'</option>';}).join('')+'</select>'; }
    return s;
  }
  if(ac.type==='webhook'){
    return '<div style="display:flex;flex-direction:column;gap:6px;flex:1;min-width:220px">'+
      '<input class="input" placeholder="https://… URL" value="'+amEsc(ac.url||'')+'" onchange="_amEdit.actions['+i+'].url=this.value">'+
      '<div style="display:flex;gap:6px;align-items:center">'+
        '<select class="input" style="max-width:100px" onchange="_amEdit.actions['+i+'].method=this.value"><option value="POST" '+(ac.method!=='GET'?'selected':'')+'>POST</option><option value="GET" '+(ac.method==='GET'?'selected':'')+'>GET</option></select>'+
        '<input class="input" style="flex:1" placeholder="body (JSON, optioneel)" value="'+amEsc(ac.body||'')+'" onchange="_amEdit.actions['+i+'].body=this.value">'+
      '</div></div>';
  }
  if(ac.type==='wait') return '<input class="input" type="number" min="0" max="600" style="max-width:110px" value="'+(ac.seconds!=null?ac.seconds:5)+'" onchange="_amEdit.actions['+i+'].seconds=+this.value"><span class="help">sec</span>';
  return '';
}
function amActSummaryOne(ac){
  if(ac.type==='preset_sequence'){ var p=(ac.presets||[]); return p.length? ('Preset '+p.join(' → ')) : 'nog geen preset gekozen'; }
  if(ac.type==='rca') return ac.state==='off'?'Uit':'Aan';
  if(ac.type==='rca_auto') return 'automatiek '+(ac.state==='off'?'uit':'aan');
  if(ac.type==='volume') return (ac.value!=null?ac.value:65)+'%';
  if(ac.type==='channel') return ac.channel==2?'Plus Easy':'Plus Main';
  if(ac.type==='tts'){ var t=(ac.text||'').trim(); return t? (t.length>40?t.slice(0,40)+'…':t) : '(nog geen tekst)'; }
  if(ac.type==='spotify'){ if(ac.command==='source') return 'Bron → '+((ac.source==='gui')?'Automix (desktop)':'omroepweb'); var m={pause:'Pauzeren',resume:'Hervatten',playpause:'Play/Pauze',next:'Volgende',prev:'Vorige',stop:'Stoppen',volume:'Volume '+(ac.value!=null?ac.value:50)+'%'}; return m[ac.command]||ac.command||''; }
  if(ac.type==='webhook'){ return ac.url? ((ac.method||'POST')+' '+ac.url.replace('https://','').replace('http://','').slice(0,32)) : '(geen URL)'; }
  if(ac.type==='wait') return (ac.seconds!=null?ac.seconds:5)+' sec';
  return '';
}
function amToggleAction(i){ _amOpenAction=(_amOpenAction===i?null:i); amRenderActions(); }
function amRenderActions(){
  var w=document.getElementById('amActions');
  w.innerHTML=(_amEdit.actions||[]).map(function(ac,i){
    var at=amAT(ac.type), open=(_amOpenAction===i);
    return '<div class="am-arow'+(open?' open':'')+'">'+
      '<div class="am-arow-head" onclick="amToggleAction('+i+')">'+
        '<div class="am-rowic"><span class="mi">'+at[2]+'</span></div>'+
        '<div style="flex:1;min-width:0"><div style="font-weight:700;color:var(--green-dark)">'+at[1]+'</div>'+
          '<div class="am-sub">'+amEsc(amActSummaryOne(ac))+'</div></div>'+
        '<span class="mi" style="color:var(--fg3)">'+(open?'expand_less':'expand_more')+'</span>'+
        '<button class="am-iconbtn danger" onclick="event.stopPropagation();_amEdit.actions.splice('+i+',1);_amOpenAction=null;amRenderActions()"><span class="mi">close</span></button>'+
      '</div>'+
      (open?('<div class="am-arow-body">'+amActFields(ac,i)+'</div>'):'')+
    '</div>';
  }).join('')||'<div class="help" style="margin-bottom:8px">Nog geen acties &mdash; klik op &laquo;Actie toevoegen&raquo;.</div>';
}
function amSave(){
  _amEdit.name=document.getElementById('amName').value.trim();
  _amEdit.enabled=document.getElementById('amEnabled').checked;
  fetch("{{ url_for('automation_save') }}",{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(_amEdit)})
    .then(function(r){return r.json();}).then(function(j){ if(j.ok){ amClose(); amLoad(); } else alert('Opslaan mislukt'); }).catch(function(){alert('Opslaan mislukt');});
}
document.addEventListener('DOMContentLoaded',function(){ if(document.getElementById('amList')) amLoad(); });
</script>

<script>
function beheerTab(name){
  document.querySelectorAll('#beheerTabs .btab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.bpanel').forEach(p=>p.classList.toggle('active',p.dataset.panel===name));
  var settingsTabs=['algemeen','tts','mededeling'];
  var save=document.getElementById('beheerSave');
  if(save) save.style.display = settingsTabs.indexOf(name)>=0 ? 'block' : 'none';
  try{localStorage.setItem('beheer_tab',name);}catch(_){}
}
function addTime(){const w=document.getElementById('timesWrap');const i=document.createElement('input');i.className='input';i.type='time';i.name='times_hm';i.style.marginBottom='6px';w.appendChild(i);}
(function(){
  var t='algemeen';
  try{t=localStorage.getItem('beheer_tab')||'algemeen';}catch(_){}
  if(!document.querySelector('.btab[data-tab="'+t+'"]'))t='algemeen';
  beheerTab(t);
  function toast(id,txt,ok){
    var el=document.getElementById(id); if(!el) return;
    el.style.display='block';el.style.color=ok?'#4b7a12':'#c62828';el.textContent=txt;
    setTimeout(function(){el.style.display='none';},3000);
  }
  window.piSaveDuck=function(){
    const v=parseInt(document.getElementById('piDuckSlider').value);
    fetch('/api/pi/save_duck',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({duck_level:v})})
      .then(r=>r.json()).then(j=>toast('duckMsg',j.ok?'Niveau opgeslagen':'Fout',j.ok));
  };
  window.spRestart=function(){
    toast('spRestartMsg','Herstarten…',true);
    fetch('/api/pi/restart_raspotify',{method:'POST'}).then(r=>r.json()).then(j=>toast('spRestartMsg',j.ok?'Spotify-speler herstart':'Mislukt',j.ok));
  };
  window.spSaveMode=function(){
    const on=document.getElementById('spCtrlToggle').checked;
    fetch('/api/pi/spotify/set_mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({control:on})})
      .then(r=>r.json()).then(function(j){toast('spCtrlMsg',j.ok?('Bediening '+(on?'aan':'uit')):'Fout',j.ok);});
  };
})();
</script>
"""

PROFILE_BODY = """
<style>
.pf-hero{display:flex;align-items:center;gap:18px;margin-bottom:18px;flex-wrap:wrap}
.pf-av{width:84px;height:84px;border-radius:50%;object-fit:cover;border:3px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,.2);background:var(--red);color:#fff;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:800;flex-shrink:0}
.pf-name{font-size:22px;font-weight:800;color:var(--green-dark);line-height:1.2;word-break:break-word}
.pf-sub{color:var(--fg3);font-size:14px;word-break:break-all}
.pf-right{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--stroke-light);flex-wrap:wrap}
.pf-right:last-child{border-bottom:0}
.pf-yes{color:#4b7a12;font-weight:700;display:inline-flex;align-items:center;gap:5px}
.pf-no{color:#c0392b;font-weight:700;display:inline-flex;align-items:center;gap:5px}
</style>

<h1 style="margin:0 0 16px">Mijn profiel</h1>
{% if ok %}<div class="alert alert-ok"><span class="mi mi-sm">check</span> {{ ok }}</div>{% endif %}
{% if err %}<div class="alert alert-err"><span class="mi mi-sm">error</span> {{ err }}</div>{% endif %}

<div style="max-width:720px">
  <div class="pf-hero">
    {% if avatar_url %}<img class="pf-av" src="{{ avatar_url }}" alt="">{% else %}<div class="pf-av">{{ (display_name or uname)[:1]|upper }}</div>{% endif %}
    <div style="min-width:0">
      <div class="pf-name">{{ display_name }}</div>
      <div class="pf-sub">{{ uname }}{% if email and email != uname %} &middot; {{ email }}{% endif %}</div>
      <div style="margin-top:8px"><span class="rbadge rbadge-{{ role }}">{{ role }}</span> <span class="sbadge sbadge-{{ acc_source }}">{{ acc_source }}</span></div>
    </div>
  </div>

  <div class="subtabs" id="pfTabs">
    <button type="button" class="subtab active" data-tab="profiel" onclick="pfTab('profiel')"><span class="mi">person</span> Profiel</button>
    <button type="button" class="subtab" data-tab="rechten" onclick="pfTab('rechten')"><span class="mi">verified_user</span> Rechten</button>
    <button type="button" class="subtab" data-tab="logs" onclick="pfTab('logs')"><span class="mi">receipt_long</span> Mijn logboek</button>
  </div>

  <div class="subpanel active" data-panel="profiel">
    <div class="form-card">
      <h3>Profielfoto</h3>
      <p class="help" style="margin-bottom:10px">Kies een afbeelding (png/jpg/webp/gif). Deze verschijnt bij je naam.</p>
      <form method="post" action="{{ url_for('profile_photo_upload') }}" enctype="multipart/form-data">
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <input class="input" type="file" name="file" accept="image/*" required style="flex:1;min-width:200px">
          <button class="btn btn-inline" type="submit" style="width:auto"><span class="mi">upload</span> Uploaden</button>
        </div>
      </form>
    </div>

    {% if acc_source == 'local' %}
    <div class="form-card">
      <h3>Wachtwoord wijzigen</h3>
      <form method="post" action="{{ url_for('profile_password') }}">
        <div class="label">Huidig wachtwoord</div>
        <input class="input" type="password" name="current" autocomplete="current-password" required style="margin-bottom:10px;max-width:360px">
        <div class="row">
          <div class="col"><div class="label">Nieuw wachtwoord (min. 6)</div><input class="input" type="password" name="password" autocomplete="new-password" required></div>
          <div class="col"><div class="label">Bevestiging</div><input class="input" type="password" name="password2" autocomplete="new-password" required></div>
        </div>
        <div style="height:10px"></div>
        <button class="btn btn-primary btn-inline" type="submit" style="width:auto"><span class="mi">key</span> Wachtwoord wijzigen</button>
      </form>
    </div>
    {% else %}
    <div class="form-card"><div class="help"><span class="mi mi-sm">info</span> Je logt in via SSO &mdash; je wachtwoord beheer je bij de identity provider.</div></div>
    {% endif %}
  </div>

  <div class="subpanel" data-panel="rechten">
    {% macro yn(v) %}{% if v %}<span class="pf-yes"><span class="mi mi-sm">check</span> Ja</span>{% else %}<span class="pf-no"><span class="mi mi-sm">close</span> Nee</span>{% endif %}{% endmacro %}
    <div class="form-card">
      <h3>Mijn rechten</h3>
      <div class="pf-right"><span>Rol</span><span class="rbadge rbadge-{{ role }}">{{ role }}</span></div>
      <div class="pf-right"><span>Volume aanpassen</span>{{ yn(can_volume) }}</div>
      <div class="pf-right"><span>Text to Speech gebruiken</span>{{ yn(can_tts) }}</div>
      <div class="pf-right"><span>Text to Speech genereren (download)</span>{{ yn(can_tts_generate) }}</div>
      <div class="pf-right"><span>Toegestane presets</span><strong>{% if presets_all %}Alle{% elif preset_list %}{{ preset_list|join(', ') }}{% else %}Geen{% endif %}</strong></div>
      <div class="pf-right"><span>Zichtbare pagina's</span><strong>{% set ps=[] %}{% if pages.volume %}{% set _=ps.append('Volume') %}{% endif %}{% if pages.presets %}{% set _=ps.append('Presets') %}{% endif %}{% if pages.tts %}{% set _=ps.append('Text to Speech') %}{% endif %}{{ ps|join(' · ') or '—' }}</strong></div>
      {% if groups %}<div class="pf-right"><span>Groepen</span><span>{% for g in groups %}<span class="ugroup">{{ g }}</span> {% endfor %}</span></div>{% endif %}
    </div>
  </div>

  <div class="subpanel" data-panel="logs">
    <div class="form-card">
      <h3>Mijn laatste acties</h3>
      {% if log_rows %}
      <div class="table-wrap"><table class="table" style="margin-bottom:0">
        <thead><tr><th style="width:140px">Tijdstip</th><th style="width:120px">Categorie</th><th>Actie</th><th style="width:120px">IP</th></tr></thead>
        <tbody>
        {% for it in log_rows %}
        <tr><td class="mono" style="font-size:12px;white-space:nowrap;color:var(--fg3)">{{ it.time }}</td>
        <td>{% if it.cat in cat_logos %}<img src="{{ cat_logos[it.cat] }}" alt="{{ it.label }}" class="lc-splogo">{% else %}<span class="lcbadge lc-{{ it.cat }}">{{ it.label }}</span>{% endif %}</td>
        <td style="font-size:13px;word-break:break-word;max-width:420px">{{ it.action }}</td>
        <td class="mono" style="font-size:11px;color:var(--fg3);white-space:nowrap">{{ it.ip }}</td></tr>
        {% endfor %}
        </tbody>
      </table></div>
      {% else %}<div class="help">Nog geen acties geregistreerd voor jouw account.</div>{% endif %}
    </div>
  </div>
</div>

<script>
function pfTab(name){
  document.querySelectorAll('#pfTabs .subtab').forEach(function(b){b.classList.toggle('active',b.dataset.tab===name);});
  document.querySelectorAll('.subpanel').forEach(function(p){p.classList.toggle('active',p.dataset.panel===name);});
}
</script>
"""

LOGS_BODY = """
<h1>Logboek</h1>
<div class="row" style="margin-bottom:18px;gap:10px">
  {% for stat in stats %}
  <div style="padding:10px 16px;border-radius:8px;border:1px solid var(--stroke);background:#f4f6f1;min-width:100px;text-align:center">
    <div style="font-size:22px;font-weight:900;color:{% if stat.cat=='login' %}var(--gold){% elif stat.cat=='preset' %}#4b7a12{% elif stat.cat == 'admin' or stat.cat == 'logout' %}#c62828{% else %}var(--green-dark){% endif %}">{{ stat.count }}</div>
    <div class="label" style="margin:0">{{ stat.label }}</div>
  </div>
  {% endfor %}
</div>

<div class="log-filters">
  <button class="log-filter-btn on" data-cat="all" onclick="filterCat(this,'all')">Alles</button>
  {% for cat,label in cats %}
  <button class="log-filter-btn" data-cat="{{ cat }}" onclick="filterCat(this,'{{ cat }}')">{% if cat in cat_logos %}<img src="{{ cat_logos[cat] }}" alt="{{ label }}" class="lc-splogo">{% else %}{{ label }}{% endif %}</button>
  {% endfor %}
  <input class="log-search" id="logSearch" type="search" placeholder="Zoeken in logs…" oninput="filterSearch()">
</div>

<div class="table-wrap">
<table class="table" id="logTable">
  <thead>
    <tr>
      <th style="width:140px">Tijdstip</th>
      <th style="width:90px">Categorie</th>
      <th style="width:130px">Gebruiker</th>
      <th>Actie</th>
      <th style="width:120px">IP-adres</th>
    </tr>
  </thead>
  <tbody>
    {% for it in rows %}
    <tr data-cat="{{ it.cat }}">
      <td class="mono" style="font-size:12px;white-space:nowrap;color:var(--fg3)">{{ it.time }}</td>
      <td>{% if it.cat in cat_logos %}<img src="{{ cat_logos[it.cat] }}" alt="{{ it.label }}" class="lc-splogo">{% else %}<span class="lcbadge lc-{{ it.cat }}">{{ it.label }}</span>{% endif %}</td>
      <td style="font-size:13px;white-space:nowrap;font-weight:600">{{ it.user }}</td>
      <td style="font-size:13px;word-break:break-word;max-width:420px">{{ it.action }}</td>
      <td class="mono" style="font-size:11px;color:var(--fg3);white-space:nowrap">{{ it.ip }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
</div>

<div style="height:12px"></div>
<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
  <span class="help" id="logCount">{{ rows|length }} vermeldingen getoond</span>
  <form method="post" action="{{ url_for('clear_logs') }}" onsubmit="return confirm('Alle logs wissen?')" style="margin:0">
    <button class="btn btn-sm btn-danger btn-inline" type="submit"><span class="mi">delete</span> Logs wissen</button>
  </form>
</div>

<script>
let activeCat='all';
function filterCat(btn,cat){
  activeCat=cat;
  document.querySelectorAll('.log-filter-btn').forEach(b=>b.classList.toggle('on',b===btn));
  applyFilter();
}
function filterSearch(){applyFilter();}
function applyFilter(){
  const q=(document.getElementById('logSearch').value||'').toLowerCase();
  let vis=0;
  document.querySelectorAll('#logTable tbody tr').forEach(row=>{
    const catOk=activeCat==='all'||row.dataset.cat===activeCat;
    const textOk=!q||row.textContent.toLowerCase().includes(q);
    const show=catOk&&textOk;
    row.style.display=show?'':'none';
    if(show)vis++;
  });
  document.getElementById('logCount').textContent=vis+' vermeldingen getoond';
}
</script>
"""

LOCKED_BODY = """
<h1>{{ title }}</h1>
<div class="row"><div class="col" style="max-width:380px;margin:auto">
  <div id="err" class="alert alert-err" style="display:none">Onjuiste code</div>
  <div class="codewin" id="codewin">****</div>
  <div style="height:14px"></div>
  <div class="pad">
    {% for n in ['1','2','3','4','5','6','7','8','9','Del','0','OK'] %}
    <div class="k" onclick="tap('{{ n }}')">{{ n }}</div>
    {% endfor %}
  </div>
</div></div>
<script>
let buf=[]; const MAXLEN=6;
function render(){document.getElementById('codewin').innerText=buf.length?'*'.repeat(Math.max(4,buf.length)):'****';}
function tap(d){
  if(d==='Del'){buf.pop();render();return;}
  if(d==='OK'){enter();return;}
  if(buf.length>=MAXLEN)return;
  buf.push(d);render();
}
function enter(){
  fetch("{{ unlock_url }}",{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:buf.join('')})})
    .then(r=>r.json()).then(j=>{
      if(j.ok){
        try{localStorage.removeItem("omroep_kiosk_v3_{{ section }}");}catch(_){}
        window.location="{{ dest_url }}";
      } else {
        document.getElementById('err').style.display='block';
        buf=[];render();
        setTimeout(()=>document.getElementById('err').style.display='none',1500);
      }
    }).catch(()=>{});
}
render();
history.pushState(null,'',location.href);
window.addEventListener('popstate',()=>history.pushState(null,'',location.href));
</script>
"""
