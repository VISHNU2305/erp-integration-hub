"""
Web dashboard for the ERP Integration Hub.

A presentation layer over the already-tested logic in erp_workflow.py,
connectors.py, security_monitor.py, and genai_assistant.py. No business
logic lives here — every action just calls the existing FastAPI
endpoints already defined in api.py.
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ERP Integration Hub</title>
<style>
  :root {
    --bg: #0f1420; --card: #1a2233; --accent: #4f9dff; --accent2: #7c5cff;
    --text: #e8ecf4; --muted: #8892a6; --error: #ff5c5c; --warning: #ffb84f;
    --success: #4fd68c; --medium: #ffb84f; --low: #4f9dff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #0f1420; color: var(--text); min-height: 100vh;
    padding: 32px; position: relative; overflow-x: hidden;
  }
  .bg-anim { position: fixed; top:0; left:0; width:100%; height:100%; z-index:0; overflow:hidden; pointer-events:none; }
  .bg-anim span {
    position: absolute; display: block;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    opacity: 0.1; border-radius: 50%; animation: float 20s linear infinite;
  }
  .bg-anim span:nth-child(1) { left:8%; width:70px; height:70px; animation-duration:24s; }
  .bg-anim span:nth-child(2) { left:22%; width:25px; height:25px; animation-duration:16s; animation-delay:2s; }
  .bg-anim span:nth-child(3) { left:38%; width:50px; height:50px; animation-duration:22s; animation-delay:1s; }
  .bg-anim span:nth-child(4) { left:52%; width:35px; height:35px; animation-duration:18s; animation-delay:4s; }
  .bg-anim span:nth-child(5) { left:65%; width:80px; height:80px; animation-duration:26s; animation-delay:0s; }
  .bg-anim span:nth-child(6) { left:78%; width:20px; height:20px; animation-duration:14s; animation-delay:5s; }
  .bg-anim span:nth-child(7) { left:90%; width:45px; height:45px; animation-duration:20s; animation-delay:3s; }
  @keyframes float {
    0% { transform: translateY(110vh); opacity:0; }
    10% { opacity:0.1; } 90% { opacity:0.1; }
    100% { transform: translateY(-10vh); opacity:0; }
  }
  .content { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; }
  h1 {
    font-size: 26px; margin-bottom: 4px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .subtitle { color: var(--muted); margin-bottom: 28px; }
  .panel {
    background: var(--card); border-radius: 14px; padding: 22px;
    margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.06);
  }
  .panel h2 { margin-top: 0; font-size: 16px; color: var(--accent); }
  .form-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
  input, select {
    background: #10192b; color: var(--text); border: 1px solid rgba(255,255,255,0.1);
    padding: 10px 12px; border-radius: 8px; font-size: 13px; flex: 1; min-width: 140px;
  }
  button {
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border: none; color: white; padding: 10px 18px; border-radius: 8px;
    font-size: 13px; font-weight: 600; cursor: pointer;
  }
  button:hover { opacity: 0.9; }
  button.small { padding: 6px 12px; font-size: 12px; margin-right: 6px; }
  button.secondary { background: #2a3550; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; }
  .badge.DRAFT { background: rgba(136,146,166,0.2); color: var(--muted); }
  .badge.PENDING_APPROVAL { background: rgba(255,184,79,0.15); color: var(--warning); }
  .badge.APPROVED { background: rgba(79,214,140,0.15); color: var(--success); }
  .badge.PROCURED { background: rgba(79,157,255,0.15); color: var(--accent); }
  .badge.REJECTED { background: rgba(255,92,92,0.15); color: var(--error); }
  .badge.HIGH { background: rgba(255,92,92,0.15); color: var(--error); }
  .badge.MEDIUM { background: rgba(255,184,79,0.15); color: var(--warning); }
  .badge.LOW { background: rgba(79,157,255,0.15); color: var(--low); }
  .explanation { color: var(--muted); font-style: italic; font-size: 12px; }
  .briefing-box {
    background: linear-gradient(135deg, rgba(79,157,255,0.1), rgba(124,92,255,0.1));
    border: 1px solid rgba(79,157,255,0.25); border-radius: 12px;
    padding: 16px 20px; white-space: pre-wrap; font-size: 13.5px; line-height: 1.6;
  }
</style>
</head>
<body>
  <div class="bg-anim"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>

  <div class="content">
    <h1>ERP Integration Hub</h1>
    <div class="panel">
  <h2>Step 1: Request Something You Want to Buy</h2>
  <p style="color: var(--muted); font-size: 13px; margin-top: -6px;">
    Fill this out like a purchase request form — who's asking, which department, what you need, and how much it costs.
  </p>
  <div class="form-row">
        <input id="requester" placeholder="Requester (e.g. vishnu)" />
        <input id="department" placeholder="Department (e.g. Engineering)" />
        <input id="item" placeholder="Item description" />
        <input id="quantity" type="number" placeholder="Quantity" />
        <input id="unitCost" type="number" placeholder="Unit cost (JPY)" />
        <button onclick="createRequisition()">Create</button>
      </div>
    </div>

    <div class="panel">
  <h2>Step 2: Track Your Requests</h2>
  <p style="color: var(--muted); font-size: 13px; margin-top: -6px;">
    Every request you make shows up here. Click the button on the right to move it forward — Submit it, then get it Approved, then mark it Procured (purchased).
  </p>
      <table id="reqTable">
        <thead><tr><th>ID</th><th>Item</th><th>Requester</th><th>Total (JPY)</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <div class="panel">
  <h2>Step 3: Pull In Data From Other Systems</h2>
  <p style="color: var(--muted); font-size: 13px; margin-top: -6px;">
    Companies get purchase data from suppliers and expense reports too, not just from requests made here. Click below to pull that data in and check it automatically for anything unusual.
  </p>
  <button onclick="syncPeripheral()">🔄 Bring In Supplier &amp; Expense Data</button>
      <p id="syncResult" style="color: var(--muted); margin-top: 12px;"></p>
    </div>

    <div class="panel">
  <h2>Step 4: Anything Look Unusual?</h2>
  <p style="color: var(--muted); font-size: 13px; margin-top: -6px;">
    The system automatically checks every transaction for red flags — unusually large amounts, duplicate entries, or activity at odd hours. Here's what it found:
  </p>
      <table id="eventsTable">
        <thead><tr><th>Severity</th><th>Type</th><th>Message</th><th>What does this mean?</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>

    <div class="panel">
  <h2>Step 5: Get a Simple Summary</h2>
  <p style="color: var(--muted); font-size: 13px; margin-top: -6px;">
    Instead of reading through everything above, click here to get a short, plain-English summary — like a manager would want.
  </p>
  <button onclick="loadBriefing()">📋 Give Me the Summary</button>
      <div class="briefing-box" id="briefingBox" style="margin-top: 14px;">Click above to generate today's briefing.</div>
    </div>
  </div>

<script>
let requisitions = [];

async function createRequisition() {
  const body = {
    requester: document.getElementById('requester').value,
    department: document.getElementById('department').value,
    item_description: document.getElementById('item').value,
    quantity: parseInt(document.getElementById('quantity').value),
    unit_cost: parseFloat(document.getElementById('unitCost').value),
  };
  const res = await fetch('/requisitions', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  if (res.ok) loadRequisitions();
  else alert('Error creating requisition');
}

async function loadRequisitions() {
  const res = await fetch('/requisitions');
  requisitions = await res.json();
  const tbody = document.querySelector('#reqTable tbody');
  tbody.innerHTML = requisitions.map(r => `
    <tr>
      <td>${r.requisition_id}</td>
      <td>${r.item_description}</td>
      <td>${r.requester}</td>
      <td>${(r.quantity * r.unit_cost).toLocaleString()}</td>
      <td><span class="badge ${r.status}">${friendlyStatus(r.status)}</span></td>
      <td>${actionButtons(r)}</td>
    </tr>`).join('');
}
function friendlyStatus(status) {
  const map = {
    'DRAFT': 'Not Submitted Yet',
    'PENDING_APPROVAL': 'Waiting for Approval',
    'APPROVED': 'Approved - Ready to Buy',
    'PROCURED': 'Purchased ✓',
    'REJECTED': 'Rejected'
  };
  return map[status] || status;
}

function actionButtons(r) {
  if (r.status === 'DRAFT') return `<button class="small" onclick="submitReq('${r.requisition_id}')">Submit</button>`;
  if (r.status === 'PENDING_APPROVAL') return `
    <button class="small" onclick="approveReq('${r.requisition_id}')">Approve</button>
    <button class="small secondary" onclick="rejectReq('${r.requisition_id}')">Reject</button>`;
  if (r.status === 'APPROVED') return `<button class="small" onclick="procureReq('${r.requisition_id}')">Procure</button>`;
  return '-';
}

async function submitReq(id) {
  await fetch(`/requisitions/${id}/submit`, { method: 'POST' });
  loadRequisitions();
}
async function approveReq(id) {
  const approver = prompt('Approver name (cannot be the requester):', 'senior_manager_akira');
  if (!approver) return;
  const res = await fetch(`/requisitions/${id}/approve`, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({approver})
  });
  if (!res.ok) { const err = await res.json(); alert(err.detail); }
  loadRequisitions();
}
async function rejectReq(id) {
  const approver = prompt('Your name:', 'manager');
  if (!approver) return;
  await fetch(`/requisitions/${id}/reject`, {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({approver})
  });
  loadRequisitions();
}
async function procureReq(id) {
  await fetch(`/requisitions/${id}/procure`, { method: 'POST' });
  loadRequisitions();
}

async function syncPeripheral() {
  document.getElementById('syncResult').innerText = 'Syncing...';
  const res = await fetch('/sync-peripheral-systems', { method: 'POST' });
  const data = await res.json();
  document.getElementById('syncResult').innerText =
    `Synced ${data.synced_transactions} transactions, found ${data.security_events_found} security event(s).`;
  loadSecurityEvents();
}

async function loadSecurityEvents() {
  const res = await fetch('/security-events');
  const events = await res.json();
  const tbody = document.querySelector('#eventsTable tbody');
  tbody.innerHTML = events.map(e => `
    <tr>
      <td><span class="badge ${e.severity}">${e.severity}</span></td>
      <td>${e.event_type}</td>
      <td>${e.message}</td>
      <td class="explanation">${explainEvent(e)}</td>
    </tr>`).join('');
}

function explainEvent(e) {
  if (e.event_type === 'UNUSUAL_AMOUNT') return "This amount is way outside the normal range for its department - worth double-checking.";
  if (e.event_type === 'POSSIBLE_DUPLICATE') return "Two very similar transactions happened close together - could be accidental or worth reviewing.";
  if (e.event_type === 'OFF_HOURS_ACTIVITY') return "This happened outside normal business hours - unusual, though not necessarily a problem.";
  return "Flagged by the automated monitoring system for review.";
}

async function loadBriefing() {
  document.getElementById('briefingBox').innerText = 'Generating...';
  const res = await fetch('/briefing');
  const data = await res.json();
  document.getElementById('briefingBox').innerText = data.briefing;
}

loadRequisitions();
loadSecurityEvents();
</script>
</body>
</html>
"""