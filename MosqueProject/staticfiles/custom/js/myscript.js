/* ─── Sidebar ─── */
function openSb(){document.getElementById('sidebar').classList.add('open');document.getElementById('overlay').classList.add('on')}
function closeSb(){document.getElementById('sidebar').classList.remove('open');document.getElementById('overlay').classList.remove('on')}

/* ─── Submenu (smooth CSS height) ─── */
function toggleSub(link){
  link.classList.toggle('open');
  const sub=link.nextElementSibling;
  sub.classList.toggle('open');
}

/* ─── Nav active ─── */
document.querySelectorAll('.sb-sub-link,.sb-link:not([onclick])').forEach(l=>{
  l.addEventListener('click',function(){
    document.querySelectorAll('.sb-sub-link,.sb-link').forEach(x=>x.classList.remove('active'));
    this.classList.add('active');
  });
});

/* ─── User menu ─── */
function toggleUser(){
  document.getElementById('userDrop').classList.toggle('on');
  document.getElementById('uArrow').classList.toggle('up');
}
document.addEventListener('click',e=>{
  const btn=document.querySelector('.sb-user-btn');
  const dd=document.getElementById('userDrop');
  if(dd&&!btn.contains(e.target)&&!dd.contains(e.target)){
    dd.classList.remove('on');
    document.getElementById('uArrow').classList.remove('up');
  }
});

/* ─── Tab slider ─── */
let curTab=0;
function switchTab(i){
  document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('on'));
  document.querySelectorAll('.tab-nav-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('tp'+i).classList.add('on');
  document.getElementById('tnb'+i).classList.add('active');
  curTab=i;
}
function nextTab(){switchTab((curTab+1)%2)}
function prevTab(){switchTab((curTab+1)%2)}

/* ─── Multi-select ─── */
function toggleMs(boxId,dropId){document.getElementById(dropId).classList.toggle('on')}
function selOpt(el,boxId,dropId){
  el.classList.toggle('sel');
  el.querySelector('.ms-chk').textContent=el.classList.contains('sel')?'✓':'';
  const box=document.getElementById(boxId);
  box.querySelectorAll('.pill').forEach(p=>p.remove());
  document.querySelectorAll('#'+dropId+' .ms-opt.sel').forEach(o=>{
    const p=document.createElement('span');p.className='pill';
    p.innerHTML=o.textContent.trim().replace('✓','').trim()+' <span class="pill-x" onclick="event.stopPropagation()">×</span>';
    box.insertBefore(p,box.querySelector('.ms-ph'));
  });
}
document.addEventListener('click',e=>{
  document.querySelectorAll('.ms-drop').forEach(d=>{
    if(!d.previousElementSibling.contains(e.target)&&!d.contains(e.target))d.classList.remove('on');
  });
});

/* ─── File upload ─── */
function handleFiles(input){
  const list=document.getElementById('fl1');if(!list)return;
  list.innerHTML='';
  Array.from(input.files).forEach(f=>{
    const d=document.createElement('div');d.className='file-item';
    d.innerHTML=`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--p2)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span class="fi-name">${f.name}</span><span class="fi-size">${(f.size/1024).toFixed(0)} KB</span><span class="fi-del" onclick="this.parentElement.remove()"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span>`;
    list.appendChild(d);
  });
}

/* ─── Toast ─── */
const toastIcons={
  success:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
  danger:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
  warning:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
  info:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
};
function showToast(type,title,msg){
  const w=document.getElementById('toastWrap');
  const t=document.createElement('div');t.className=`toast toast-${type}`;
  t.innerHTML=`<span class="toast-icon">${toastIcons[type]}</span><div class="toast-msg"><div>${title}</div><div class="toast-sub">${msg}</div></div><button class="toast-x" onclick="this.parentElement.remove()">×</button>`;
  w.appendChild(t);
  setTimeout(()=>{t.style.transition='all .3s';t.style.opacity='0';t.style.transform='translateY(8px)';setTimeout(()=>t.remove(),300)},4000);
}

/* ─── Bar Chart ─── */
const months=['مهر','آبان','آذر','دی','بهمن','اسفند','فروردین'];
const inc=[42,68,55,80,47,72,85],exp=[28,45,38,52,30,48,55];
document.getElementById('barChart').innerHTML=months.map((m,i)=>`
  <div class="bar-grp">
    <div class="bar-pair">
      <div class="bar bar-g" style="height:${inc[i]}%" title="${inc[i]}٪"></div>
      <div class="bar bar-r" style="height:${exp[i]}%" title="${exp[i]}٪"></div>
    </div>
    <div class="bar-lbl">${m}</div>
  </div>`).join('');

/* ─── Donut Chart ─── */
const doData=[
  {l:'نذورات',p:38,c:'#22c55e'},{l:'خیرات',p:27,c:'#f59e0b'},
  {l:'وقف',p:18,c:'#3b82f6'},{l:'کمک‌ها',p:17,c:'#8b5cf6'}
];
(()=>{
  const svg=document.getElementById('donutSvg');
  const circ=2*Math.PI*38;let off=0,html='';
  doData.forEach(d=>{
    const dash=(d.p/100)*circ,gap=circ-dash;
    html+=`<circle cx="50" cy="50" r="38" fill="none" stroke="${d.c}" stroke-width="12" stroke-dasharray="${dash} ${gap}" stroke-dashoffset="${-off}" transform="rotate(-90 50 50)" opacity=".9"/>`;
    off+=dash;
  });
  svg.innerHTML=html;
  document.getElementById('donutRows').innerHTML=doData.map(d=>`
    <div class="donut-row">
      <div class="dr-dot" style="background:${d.c}"></div>
      <div class="dr-lbl">${d.l}</div>
      <div class="dr-bar-bg"><div class="dr-bar" style="width:${d.p}%;background:${d.c}"></div></div>
      <div class="dr-pct">${d.p}٪</div>
    </div>`).join('');
})();

/* ─── Progress ─── */
const targets=[
  {l:'هدف جمع‌آوری رمضان',v:78,c:'#22c55e'},{l:'بازسازی شبستان',v:45,c:'#f59e0b'},
  {l:'خرید تجهیزات صوتی',v:92,c:'#3b82f6'},{l:'کتابخانه مسجد',v:31,c:'#8b5cf6'}
];
document.getElementById('progList').innerHTML=targets.map(t=>`
  <div class="prog-item">
    <div class="prog-hd"><span class="prog-lbl">${t.l}</span><span class="prog-val" style="color:${t.c}">${t.v}٪</span></div>
    <div class="prog-bg"><div class="prog-bar" style="width:${t.v}%;background:${t.c}"></div></div>
  </div>`).join('');

/* ─── Line Chart ─── */
(()=>{
  const svg=document.getElementById('lineChart');
  const months=['مهر','آبان','آذر','دی','بهمن','اسفند'];
  const ds=[
    {pts:[40,65,50,80,55,75],c:'#22c55e',fill:'rgba(34,197,94,.08)'},
    {pts:[25,40,35,55,30,48],c:'#ef4444',fill:'rgba(239,68,68,.07)'},
    {pts:[30,42,38,56,44,58],c:'#f59e0b',fill:'rgba(245,158,11,.07)'}
  ];
  const W=500,H=140,pad=18,xS=(W-pad*2)/5;
  const py=v=>pad+(1-v/100)*(H-pad*2),px=i=>pad+i*xS;
  let out=`<rect width="${W}" height="${H}" fill="transparent"/>`;
  for(let g=0;g<=4;g++){
    const y=pad+g*(H-pad*2)/4;
    out+=`<line x1="${pad}" y1="${y}" x2="${W-pad}" y2="${y}" stroke="#e2e8f0" stroke-width="1"/>`;
  }
  ds.forEach(d=>{
    const path=d.pts.map((v,i)=>`${i?'L':'M'}${px(i)} ${py(v)}`).join(' ');
    const area=`${path} L${px(5)} ${H-pad} L${px(0)} ${H-pad} Z`;
    out+=`<path d="${area}" fill="${d.fill}"/>`;
    out+=`<path d="${path}" fill="none" stroke="${d.c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
    d.pts.forEach((v,i)=>out+=`<circle cx="${px(i)}" cy="${py(v)}" r="3.5" fill="${d.c}" stroke="#fff" stroke-width="1.5"/>`);
  });
  months.forEach((m,i)=>out+=`<text x="${px(i)}" y="${H-3}" text-anchor="middle" fill="#94a3b8" font-size="9" font-family="Vazirmatn,sans-serif">${m}</text>`);
  svg.innerHTML=out;
})();

/* ─── Receipt thumbs ─── */
const thumbContent={
  t1:'<div style="padding:40px;text-align:center"><svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg><div style="font-size:12px;color:#94a3b8;margin-top:8px">رسید نقدی</div></div>',
  t2:'<div style="padding:40px;text-align:center"><svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg><div style="font-size:12px;color:#94a3b8;margin-top:8px">فاکتور</div></div>',
  t3:'<div style="padding:40px;text-align:center"><svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.2" stroke-linecap="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg><div style="font-size:12px;color:#94a3b8;margin-top:8px">سند بانکی</div></div>',
  t4:'<div style="padding:40px;text-align:center"><svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 7h.01M17 7h.01M7 12h10M7 17h.01M17 17h.01"/></svg><div style="font-size:12px;color:#94a3b8;margin-top:8px">بارکد</div></div>'
};
function selThumb(el,key){
  document.querySelectorAll('.r-thumb').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('rMain').innerHTML=thumbContent[key];
}