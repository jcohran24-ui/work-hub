function openQuickActions(){const m=document.getElementById('quickModal');if(m){m.classList.add('open');m.setAttribute('aria-hidden','false')}}
function closeQuickActions(){const m=document.getElementById('quickModal');if(m){m.classList.remove('open');m.setAttribute('aria-hidden','true')}}
function showToast(message){const t=document.getElementById('toast');if(!t)return;t.textContent=message;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200)}
function showNotConnected(name){showToast(name+' is not connected yet. An administrator can add its URL.')}
function quickLaunch(url,name){closeQuickActions();if(url){window.open(url,'_blank','noopener')}else{showNotConnected(name)}}
document.addEventListener('click',(e)=>{const m=document.getElementById('quickModal');if(e.target===m)closeQuickActions()});
if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/static/service-worker.js').catch(()=>{}))}
