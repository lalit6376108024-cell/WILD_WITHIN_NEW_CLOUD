(() => {
  document.querySelectorAll('[data-open]').forEach(btn => {
    btn.addEventListener('click', () => {
      const dlg = document.getElementById(btn.dataset.open);
      if (dlg) dlg.showModal();
    });
  });
  document.querySelectorAll('[data-close]').forEach(btn => btn.addEventListener('click', () => btn.closest('dialog').close()));
  document.querySelectorAll('dialog').forEach(dlg => {
    dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
  });
  document.querySelectorAll('[data-confirm]').forEach(btn => btn.addEventListener('click', e => {
    if (!confirm(btn.dataset.confirm)) e.preventDefault();
  }));
  // Support the custom duration field without requiring JavaScript for normal presets.
  const expForm = document.querySelector('#addExperiment form');
  if (expForm) expForm.addEventListener('submit', e => {
    const select = expForm.querySelector('[name="duration_days"]');
    const custom = expForm.querySelector('[name="custom_duration"]');
    if (select && select.value === 'custom' && (!custom.value || Number(custom.value) < 1 || Number(custom.value) > 365)) {
      e.preventDefault(); alert('Enter a custom duration between 1 and 365 days.'); custom.focus(); return;
    }
    if (select && select.value === 'custom') select.value = custom.value;
    else if (custom && custom.value) select.value = custom.value;
  });
  const enable = document.getElementById('enableNotifications');
  const status = document.getElementById('notificationStatus');
  let notified = new Set();
  if (enable) {
    if (!('Notification' in window)) {
      enable.disabled = true; status.textContent = 'This browser does not support notifications. Keep the dashboard open to use in-app reminders.';
    } else if (Notification.permission === 'granted') {
      enable.textContent = 'Notifications enabled'; status.textContent = 'Browser notifications are allowed for this site.';
    }
    enable.addEventListener('click', async () => {
      if (!('Notification' in window)) return;
      const permission = await Notification.requestPermission();
      status.textContent = permission === 'granted' ? 'Notifications enabled. Keep this dashboard open for reminder checks.' : 'Permission not granted. You can still view reminder times in each activity.';
      if (permission === 'granted') { enable.textContent = 'Notifications enabled'; checkReminders(); }
    });
  }
  async function checkReminders() {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    try {
      const response = await fetch('/api/reminders', {cache:'no-store'});
      const data = await response.json();
      const now = new Date();
      // Compare local browser clock to each configured reminder. Server timezone should match the user's chosen timezone.
      const hhmm = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
      data.reminders.forEach(r => {
        const key = `${data.date}-${r.id}-${r.time}`;
        if (r.time === hhmm && !notified.has(key)) {
          new Notification(`WILD WITHIN · ${r.name}`, {body:'Your planned time is here. Take one small step.'});
          notified.add(key);
        }
      });
    } catch (e) { /* Reminder checks are optional; app remains usable offline. */ }
  }
  checkReminders();
  setInterval(checkReminders, 30000);
  // Local clock in the header helps make the selected timezone visible.
  const tz = document.querySelector('.timezone');
  if (tz) {
    const clock = document.createElement('span');
    clock.className = 'local-clock';
    tz.appendChild(clock);
    const update = () => { try { clock.textContent = new Intl.DateTimeFormat(undefined,{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'}).format(new Date()); } catch(e) {} };
    update(); setInterval(update, 30000);
  }
})();
