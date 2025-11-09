const $ = (q) => document.querySelector(q);
const kMode = $('#kpi-mode');
const kStatus = $('#kpi-status');
const kCycle = $('#kpi-cycle');
const kPayload = $('#kpi-payload');
const lastUpdate = $('#last-update');
const refreshBtn = $('#refresh');
const metricSelect = $('#metric-select');
const loadHistoryBtn = $('#load-history');
const chartCanvas = $('#chart');
const deviceList = $('#device-list');
const jointEls = [
  document.getElementById('joint1'),
  document.getElementById('joint2'),
  document.getElementById('joint3'),
  document.getElementById('joint4'),
];

let latestCache = {};

async function fetchJSON(url){
  const r = await fetch(url, {cache: 'no-cache'});
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

function fmt(v){
  if(v==null) return '--';
  if(typeof v === 'number') return Number.isInteger(v)? v.toString() : v.toFixed(2);
  return String(v);
}

function setKpis(d){
  const op = d.OperationalData || {};
  const tech = d.TechnicalData || {};
  kMode.textContent = fmt(op.WorkingMode);
  const statusText = fmt(op.RobotStatus);
  kStatus.textContent = statusText;
  kStatus.classList.remove('ok','warn','err');
  const s = String(statusText).toLowerCase();
  if(s.includes('estop')||s.includes('fault')||s.includes('error')) kStatus.classList.add('err');
  else if(s.includes('slow')||s.includes('manual')) kStatus.classList.add('warn');
  else kStatus.classList.add('ok');
  kCycle.textContent = fmt(op.CycleTime);
  kPayload.textContent = fmt(tech.PayloadUser);
}

function badge(cls, text){
  return `<span class="tag ${cls}">${text}</span>`;
}

function statusBadge(status){
  const s = String(status || '').toLowerCase();
  if(s.includes('estop') || s.includes('fault') || s.includes('error')) return badge('err','ALERTA');
  if(s.includes('slow') || s.includes('manual')) return badge('warn','ATENÇÃO');
  return badge('ok','OK');
}

function updateJoints(d){
  const op = d.OperationalData || {};
  const joints = [op.JointPosition1, op.JointPosition2, op.JointPosition3, op.JointPosition4];
  joints.forEach((arr, idx)=>{
    const val = Array.isArray(arr)? arr.map(v=>Number(v)||0) : [];
    const avg = val.length? val.reduce((a,b)=>a+b,0)/val.length : 0;
    if(jointEls[idx]) jointEls[idx].querySelector('span').textContent = `${Math.round(avg)}°`;
  });
}

function populateDevices(d){
  const items = Object.keys(d||{});
  deviceList.innerHTML = '';
  for(const name of items){
    const item = document.createElement('div');
    item.className = 'device-item';
    item.innerHTML = `<div class="name">${name}</div><div class="state tag ok">live</div>`;
    deviceList.appendChild(item);
  }
}

async function updateLatest(){
  try{
    const data = await fetchJSON('/api/latest');
    latestCache = data || {};
    setKpis(latestCache);
    updateJoints(latestCache);
    populateDevices(latestCache);
    lastUpdate.textContent = new Date().toLocaleTimeString();
  }catch(e){
    console.error('latest error', e);
  }
}

async function loadPaths(){
  try{
    const data = await fetchJSON('/api/paths');
    const items = (data.paths||[]);
    metricSelect.innerHTML = '';
    for(const it of items){
      const opt = document.createElement('option');
      opt.value = `${it.submodel}|${it.path}`;
      opt.textContent = `${it.submodel} · ${it.path}`;
      metricSelect.appendChild(opt);
    }
  }catch(e){
    console.error('paths error', e);
  }
}

function drawLine(canvas, rows){
  const ctx = canvas.getContext('2d');
  const W = canvas.width = canvas.clientWidth;
  const H = canvas.height = canvas.getAttribute('height');
  ctx.clearRect(0,0,W,H);
  if(!rows.length){
    ctx.fillStyle = '#7a8598';
    ctx.fillText('Sem dados', 10, 20);
    return;
  }
  const values = rows.map(r=>Number(r.v));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = 8;
  ctx.strokeStyle = '#263147';
  ctx.strokeRect(0.5,0.5,W-1,H-1);
  ctx.strokeStyle = '#1b2435';
  // grid lines
  for(let i=1;i<4;i++){
    const y = pad + (H-2*pad) * i/4;
    ctx.beginPath(); ctx.moveTo(pad,y); ctx.lineTo(W-pad,y); ctx.stroke();
  }
  // line
  ctx.strokeStyle = '#16c266'; ctx.lineWidth = 2;
  ctx.beginPath();
  rows.forEach((r, i)=>{
    const x = pad + (W-2*pad) * (i/(rows.length-1||1));
    const y = pad + (H-2*pad) * (1 - (values[i]-min)/((max-min)||1));
    if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();
}

async function loadHistory(){
  const val = metricSelect.value;
  if(!val) return;
  const [submodel, path] = val.split('|');
  const data = await fetchJSON(`/api/timeseries?submodel=${encodeURIComponent(submodel)}&path=${encodeURIComponent(path)}&limit=200`);
  drawLine(chartCanvas, data.rows||[]);
}

refreshBtn.addEventListener('click', updateLatest);
loadHistoryBtn.addEventListener('click', loadHistory);

// boot
updateLatest();
loadPaths();
setInterval(updateLatest, 2000);

// --- Cadastro de Clientes (localStorage CRUD) ---
(function initClientes(){
  const form = document.getElementById('cliente-form');
  const tabela = document.getElementById('clientes-tabela');
  if(!form || !tabela) return; // painel nao esta presente

  const idInput = document.getElementById('cli-id');
  const nomeInput = document.getElementById('cli-nome');
  const emailInput = document.getElementById('cli-email');
  const telInput = document.getElementById('cli-telefone');
  const docInput = document.getElementById('cli-doc');
  const endInput = document.getElementById('cli-endereco');
  const limparBtn = document.getElementById('cli-limpar');

  function loadClientes(){
    try{ return JSON.parse(localStorage.getItem('clientes')||'[]'); }catch{ return []; }
  }
  function saveClientes(arr){
    localStorage.setItem('clientes', JSON.stringify(arr));
  }
  function clearForm(){
    idInput.value = '';
    form.reset();
    nomeInput.focus();
  }
  function fillForm(c){
    idInput.value = c.id || '';
    nomeInput.value = c.nome || '';
    emailInput.value = c.email || '';
    telInput.value = c.telefone || '';
    docInput.value = c.documento || '';
    endInput.value = c.endereco || '';
  }
  function render(){
    const arr = loadClientes();
    const tbody = tabela.querySelector('tbody');
    tbody.innerHTML = '';
    for(const c of arr){
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${c.nome||''}</td>
        <td>${c.email||''}</td>
        <td>${c.telefone||''}</td>
        <td>${c.documento||''}</td>
        <td>
          <button type="button" class="action-btn" data-action="edit" data-id="${c.id}">Editar</button>
          <button type="button" class="action-btn" data-action="del" data-id="${c.id}">Remover</button>
        </td>`;
      tbody.appendChild(tr);
    }
  }

  form.addEventListener('submit', (ev)=>{
    ev.preventDefault();
    const nome = (nomeInput.value||'').trim();
    if(!nome){ nomeInput.focus(); return; }
    const cliente = {
      id: idInput.value || String(Date.now()),
      nome,
      email: (emailInput.value||'').trim(),
      telefone: (telInput.value||'').trim(),
      documento: (docInput.value||'').trim(),
      endereco: (endInput.value||'').trim(),
    };
    const arr = loadClientes();
    const idx = arr.findIndex(x=>x.id===cliente.id);
    if(idx>=0) arr[idx] = cliente; else arr.push(cliente);
    saveClientes(arr);
    clearForm();
    render();
  });

  limparBtn.addEventListener('click', clearForm);

  tabela.addEventListener('click', (ev)=>{
    const btn = ev.target.closest('button[data-action]');
    if(!btn) return;
    const id = btn.getAttribute('data-id');
    if(btn.getAttribute('data-action')==='edit'){
      const c = loadClientes().find(x=>x.id===id);
      if(c) fillForm(c);
    }else if(btn.getAttribute('data-action')==='del'){
      const arr = loadClientes().filter(x=>x.id!==id);
      saveClientes(arr);
      render();
    }
  });

  // primeira renderizacao
  render();
})();
