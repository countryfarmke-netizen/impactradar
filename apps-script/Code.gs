const HEADERS = ['ID','First seen','Title','Type','Deadline','Fit','Source','Link','Contacts','Owner','Status','Next action','Notes'];
const sheet_ = () => { const ss = SpreadsheetApp.getActiveSpreadsheet(); return ss.getSheetByName('Leads') || ss.insertSheet('Leads'); };
const out_ = o => ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
const fmt_ = d => Utilities.formatDate(new Date(d), 'Africa/Nairobi', 'd MMM yyyy');

function setup() {  // run once; also set Script properties TOKEN (secret) and DIGEST_TO (emails, comma separated)
  const s = sheet_(); if (!s.getLastRow()) s.appendRow(HEADERS);
  s.setFrozenRows(1);
  s.getRange('K2:K1000').setDataValidation(SpreadsheetApp.newDataValidation()
    .requireValueInList(['New','Qualifying','Drafting','Submitted','Won','Lost','Not a fit'], true).build());
}
function doPost(e) {
  const b = JSON.parse(e.postData.contents);
  if (b.token !== PropertiesService.getScriptProperties().getProperty('TOKEN')) return out_({error: 'bad token'});
  const s = sheet_(), have = new Set(s.getRange(2, 1, Math.max(s.getLastRow() - 1, 1), 1).getValues().flat());
  const rows = b.items.filter(i => !have.has(i.id)).map(i =>
    [i.id, i.first_seen, i.title, i.kind, i.deadline, i.score, i.source, i.link, (i.contacts || []).join(', '), '', 'New', '', '']);
  if (rows.length) s.getRange(s.getLastRow() + 1, 1, rows.length, HEADERS.length).setValues(rows);
  return out_({added: rows.length});
}
function weeklyDigest() {  // add a weekly time-driven trigger for this function
  const rows = sheet_().getDataRange().getValues().slice(1), now = new Date(), soon = [], fresh = [];
  rows.forEach(r => {
    if (['Won','Lost','Not a fit','Submitted'].includes(r[10])) return;
    const d = r[4] ? new Date(r[4]) : null;
    if (d && d - now >= 0 && d - now <= 14 * 864e5) soon.push(`${r[2]}: due ${fmt_(d)}, owner ${r[9] || 'UNASSIGNED'}`);
    if (new Date(r[1]) > now - 7 * 864e5) fresh.push(`${r[2]} ${r[7]}`);
  });
  const to = PropertiesService.getScriptProperties().getProperty('DIGEST_TO') || Session.getEffectiveUser().getEmail();
  MailApp.sendEmail(to, 'Impact Radar weekly digest',
    `DUE IN 14 DAYS (${soon.length})\n${soon.join('\n') || 'None'}\n\nNEW THIS WEEK (${fresh.length})\n${fresh.join('\n') || 'None'}`);
}
