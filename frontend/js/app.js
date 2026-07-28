let currentUser = null;
let map = null;
let markers = [];
let mapInitialized = false;

function $(id) { return document.getElementById(id); }
function show(id) { document.querySelectorAll('.page').forEach(p => p.classList.remove('active')); const el = $(id); if (el) el.classList.add('active'); }
function modal(id, show) { const el = $(id); if (el) el.classList.toggle('hidden', !show); }

async function checkAuth() {
  try {
    currentUser = await API.getMe();
    if (currentUser.error) { currentUser = null; }
  } catch { currentUser = null; }
  renderNav();
}

function renderNav() {
  const guest = document.getElementById('guest-links');
  const user = document.getElementById('user-links');
  const badge = document.getElementById('user-badge');
  if (currentUser) {
    guest.classList.add('hidden');
    user.classList.remove('hidden');
    badge.textContent = `${currentUser.name} (${currentUser.role})`;
  } else {
    guest.classList.remove('hidden');
    user.classList.add('hidden');
  }
  // Show role-appropriate nav items
  document.querySelectorAll('.role-nav').forEach(el => el.classList.add('hidden'));
  if (currentUser) {
    const roleLinks = document.querySelectorAll(`.role-${currentUser.role}`);
    roleLinks.forEach(el => el.classList.remove('hidden'));
  }
}

async function doLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  try {
    currentUser = await API.login({ email, password });
    modal('login-modal', false);
    renderNav();
    routeAfterLogin();
  } catch (err) {
    alert('Login failed: ' + err.message);
  }
}

async function doSignup(e) {
  e.preventDefault();
  const data = {
    name: document.getElementById('signup-name').value,
    email: document.getElementById('signup-email').value,
    phone: document.getElementById('signup-phone').value,
    password: document.getElementById('signup-password').value,
    role: document.getElementById('signup-role').value,
    vehicle_type: document.getElementById('signup-vehicle').value || null,
  };
  try {
    const r = await API.signup(data);
    currentUser = await API.login({ email: data.email, password: data.password });
    modal('signup-modal', false);
    renderNav();
    routeAfterLogin();
  } catch (err) {
    alert('Signup failed: ' + err.message);
  }
}

async function doLogout() {
  await API.logout();
  currentUser = null;
  renderNav();
  show('page-driver');
  clearMapMarkers();
}

function routeAfterLogin() {
  if (!currentUser) return;
  if (currentUser.role === 'admin') { show('page-admin'); loadAdminDashboard(); }
  else if (currentUser.role === 'operator' || currentUser.role === 'fuel_manager') { show('page-operator'); loadOperatorDashboard(); }
  else { show('page-driver'); initMap(); loadNearbyStations(); }
}

// --- AUTH MODAL HANDLERS ---

document.addEventListener('DOMContentLoaded', async () => {
  await checkAuth();

  document.getElementById('login-form').addEventListener('submit', doLogin);
  document.getElementById('signup-form').addEventListener('submit', doSignup);
  document.getElementById('profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      name: document.getElementById('profile-name').value,
      phone: document.getElementById('profile-phone').value,
      vehicle_type: document.getElementById('profile-vehicle').value || null,
      fuel_preference: document.getElementById('profile-fuel-pref').value || null,
    };
    try {
      await API.updateProfile(data);
      modal('profile-modal', false);
      alert('Profile updated!');
    } catch (err) { alert('Update failed: ' + err.message); }
  });

  // Show signup modal
  document.querySelectorAll('[data-modal]').forEach(btn => {
    btn.addEventListener('click', () => modal(btn.dataset.modal, true));
  });
  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(m => {
    m.addEventListener('click', (e) => { if (e.target === m) m.classList.add('hidden'); });
  });
  // Close on X
  document.querySelectorAll('.modal-close').forEach(b => {
    b.addEventListener('click', () => { b.closest('.modal-overlay').classList.add('hidden'); });
  });

  // Nav profile
  document.getElementById('nav-profile').addEventListener('click', () => {
    if (!currentUser) return;
    document.getElementById('profile-name').value = currentUser.name || '';
    document.getElementById('profile-phone').value = currentUser.phone || '';
    document.getElementById('profile-vehicle').value = currentUser.vehicle_type || '';
    document.getElementById('profile-fuel-pref').value = currentUser.fuel_preference || '';
    modal('profile-modal', true);
  });

  // Initialize driver page
  if (!currentUser || currentUser.role === 'driver') {
    initMap();
  }
});

// --- DRIVER PAGE ---

let userLat = 23.8103;
let userLng = 90.4125;
let driverTab = 'map';

function switchDriverTab(tab) {
  driverTab = tab;
  document.querySelectorAll('.driver-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`dtab-${tab}`).classList.add('active');
  document.querySelectorAll('.driver-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById(`dpanel-${tab}`).classList.remove('hidden');
  if (tab === 'bookings') loadMyBookings();
}

function initMap() {
  if (mapInitialized) return;
  map = L.map('map').setView([userLat, userLng], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);

  // Get user location
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userLat = pos.coords.latitude;
        userLng = pos.coords.longitude;
        map.setView([userLat, userLng], 14);
        L.marker([userLat, userLng], {
          icon: L.divIcon({ className: 'user-marker', html: '<div style="background:#1565c0;width:16px;height:16px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)"></div>', iconSize: [16,16], iconAnchor: [8,8] })
        }).addTo(map).bindPopup('<strong>You are here</strong>');
        loadNearbyStations();
      },
      () => { loadNearbyStations(); },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  } else {
    loadNearbyStations();
  }
  mapInitialized = true;
}

function clearMapMarkers() {
  if (markers.length) { markers.forEach(m => map.removeLayer(m)); markers = []; }
}

async function loadNearbyStations() {
  const radius = document.querySelector('input[name="radius"]:checked')?.value || 5;
  const vehicleType = document.getElementById('filter-vehicle').value;
  const fuelType = document.getElementById('filter-fuel').value;

  const params = { lat: userLat, lng: userLng, radius };
  if (fuelType) params.fuel_type = fuelType;

  try {
    const stations = await API.getNearby(params);
    clearMapMarkers();
    const list = document.getElementById('station-list');
    list.innerHTML = '';
    if (!stations.length) {
      list.innerHTML = '<div class="empty-state"><div class="icon">&#128205;</div><p>No stations found nearby</p></div>';
    }
    stations.forEach(s => {
      const iconColor = s.station_type === 'fuel' ? '#e65100' : '#1565c0';
      const icon = L.divIcon({
        className: '',
        html: `<div style="background:${iconColor};color:#fff;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3)">${s.station_type === 'fuel' ? '⛽' : 'P'}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });
      const marker = L.marker([s.lat, s.lng], { icon }).addTo(map);
      marker.bindPopup(buildPopup(s));
      markers.push(marker);

      // Add to list
      const div = document.createElement('div');
      div.className = 'station-card';
      div.style.cursor = 'pointer';
      div.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:start">
          <div>
            <h3>${s.name}</h3>
            <div style="font-size:13px;color:#78909c">${s.address}</div>
            <div style="font-size:13px;color:#546e7a;margin-top:6px">
              ${s.station_type !== 'fuel' ? `<span><strong>Slots:</strong> ${s.available_slots}/${s.total_capacity}</span> &middot; <span><strong>Rate:</strong> ৳${s.hourly_rate}/hr</span> &middot; ` : ''}
              <span><strong>Dist:</strong> ${s.distance_km}km</span>
            </div>
            ${s.fuel_prices && s.fuel_prices.length ? '<div class="popup-fuel">' + s.fuel_prices.map(f => `<span><strong>${f.fuel_type}:</strong> ৳${f.price_per_liter}/L</span>`).join('') + '</div>' : ''}
          </div>
          <span class="badge ${s.station_type === 'fuel' ? 'badge-orange' : 'badge-blue'}">${s.station_type}</span>
        </div>
      `;
      div.addEventListener('click', () => {
        map.setView([s.lat, s.lng], 16);
        marker.openPopup();
      });
      list.appendChild(div);
    });
  } catch (err) {
    console.error('Failed to load nearby stations:', err);
  }
}

function buildPopup(s) {
  const fuelHtml = s.fuel_prices && s.fuel_prices.length
    ? '<div class="popup-fuel">' + s.fuel_prices.map(f => `<span><strong>${f.fuel_type}:</strong> ৳${f.price_per_liter}/L</span>`).join('') + '</div>'
    : '';
  const dirUrl = `https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lng}`;
  return `
    <h3>${s.name}</h3>
    <div class="popup-address">${s.address}</div>
    ${s.station_type !== 'fuel' ? `<div class="popup-detail"><strong>Available Slots:</strong> ${s.available_slots}/${s.total_capacity}</div>
    <div class="popup-detail"><strong>Hourly Rate:</strong> ৳${s.hourly_rate}</div>` : ''}
    <div class="popup-detail"><strong>Distance:</strong> ${s.distance_km}km</div>
    <div class="popup-detail"><strong>Hours:</strong> ${s.operating_hours}</div>
    ${fuelHtml}
    <div class="popup-actions">
      ${s.station_type !== 'fuel' && s.available_slots > 0 && currentUser ? `<button class="btn btn-primary btn-sm" onclick="openReservation(${s.id},'${s.name}',${s.hourly_rate})">Reserve</button>` : ''}
      <a href="${dirUrl}" target="_blank" class="btn btn-outline btn-sm">Get Directions</a>
    </div>
  `;
}

function openReservation(stationId, name, hourlyRate) {
  if (!currentUser) { alert('Please login first'); return; }
  document.getElementById('reserve-station-name').textContent = name;
  document.getElementById('reserve-station-id').value = stationId;
  document.getElementById('reserve-rate').textContent = hourlyRate;
  // Set default start time to next hour
  const now = new Date();
  now.setHours(now.getHours() + 1, 0, 0, 0);
  document.getElementById('reserve-start').value = now.toISOString().slice(0, 16);
  document.getElementById('reserve-duration').value = 1;
  calcReservationCost();
  modal('reserve-modal', true);
}

function calcReservationCost() {
  const rate = parseFloat(document.getElementById('reserve-rate').textContent) || 0;
  const hours = parseInt(document.getElementById('reserve-duration').value) || 1;
  document.getElementById('reserve-cost').textContent = (rate * hours).toFixed(2);
}

async function confirmReservation() {
  const stationId = parseInt(document.getElementById('reserve-station-id').value);
  const startTime = document.getElementById('reserve-start').value;
  const duration = parseInt(document.getElementById('reserve-duration').value);
  if (!startTime || !duration) { alert('Please fill all fields'); return; }
  try {
    const r = await API.createBooking({
      station_id: stationId,
      start_time: new Date(startTime).toISOString(),
      duration_hours: duration
    });
    modal('reserve-modal', false);
    alert(`Booking confirmed!\nToken: ${r.token}\nCost: ৳${r.cost}\nDuration: ${r.duration_hours}hr`);
    loadNearbyStations();
  } catch (err) { alert('Booking failed: ' + err.message); }
}

async function loadMyBookings() {
  if (!currentUser) { document.getElementById('bookings-list').innerHTML = '<div class="empty-state"><p>Please login to see bookings</p></div>'; return; }
  try {
    const bookings = await API.getMyBookings();
    const list = document.getElementById('bookings-list');
    list.innerHTML = '';
    if (!bookings.length) {
      list.innerHTML = '<div class="empty-state"><div class="icon">&#128203;</div><p>No bookings yet</p></div>';
      return;
    }
    bookings.forEach(b => {
      let statusClass = b.status.toLowerCase();
      if (b.remaining_minutes > 0 && b.remaining_minutes < 15 && b.status === 'Active') statusClass = 'expiring';
      const div = document.createElement('div');
      div.className = `booking-card ${statusClass}`;
      const endTime = new Date(b.start_time);
      endTime.setHours(endTime.getHours() + b.duration_hours);
      div.innerHTML = `
        <div class="b-header">
          <h4>${b.station_name}</h4>
          <span class="badge badge-${b.status === 'Active' ? 'green' : b.status === 'Completed' ? 'blue' : 'red'}">${b.status}</span>
        </div>
        <div class="b-meta">
          <span>Token: <strong>${b.token}</strong></span>
          <span>Start: ${new Date(b.start_time).toLocaleString()}</span>
          <span>Duration: ${b.duration_hours}hr</span>
          <span>Cost: ৳${b.cost}</span>
          ${b.overtime_charge ? `<span style="color:#e65100">Overtime: +${b.overtime_hours}hr (৳${b.overtime_charge})</span>` : ''}
          ${b.is_overtime ? '<span class="badge badge-red" style="margin-left:8px">Overtime!</span>' : ''}
        </div>
        ${b.remaining_minutes > 0 && b.remaining_minutes < 15 && b.status === 'Active' ? '<div class="alert alert-warning" style="margin-top:8px;padding:8px 12px">⚠ Less than 15 minutes remaining!</div>' : ''}
        <div style="margin-top:8px">
          ${b.status === 'Active' ? `<button class="btn btn-danger btn-sm" onclick="cancelMyBooking(${b.id})">Cancel</button>` : ''}
          <a href="https://www.google.com/maps/dir/?api=1&destination=${b.station_lat || ''},${b.station_lng || ''}" target="_blank" class="btn btn-outline btn-sm">Get Directions</a>
        </div>
      `;
      list.appendChild(div);
    });
  } catch (err) { console.error('Failed to load bookings:', err); }
}

async function cancelMyBooking(bookingId) {
  if (!confirm('Cancel this booking?')) return;
  try {
    await API.cancelBooking(bookingId);
    loadMyBookings();
  } catch (err) { alert('Cancel failed: ' + err.message); }
}

// --- OPERATOR PAGE ---

let operatorTab = 'stations';

function switchOperatorTab(tab) {
  operatorTab = tab;
  document.querySelectorAll('.op-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`otab-${tab}`).classList.add('active');
  document.querySelectorAll('.op-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById(`opanel-${tab}`).classList.remove('hidden');
  if (tab === 'stations') loadOperatorStations();
  else if (tab === 'tokens') { /* token lookup ready */ }
}

async function loadOperatorDashboard() {
  loadOperatorStations();
  // Switch to operator page
  show('page-operator');
  document.querySelectorAll('.op-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('otab-stations').classList.add('active');
  document.querySelectorAll('.op-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('opanel-stations').classList.remove('hidden');
}

async function loadOperatorStations() {
  try {
    const stations = await API.getMyStations();
    const list = document.getElementById('op-stations-list');
    list.innerHTML = '';
    if (!stations.length) {
      list.innerHTML = '<div class="empty-state"><div class="icon">&#128205;</div><p>No stations yet. Create one!</p></div>';
    }
    stations.forEach(s => {
      const div = document.createElement('div');
      div.className = 'station-card';
      div.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px">
          <div>
            <h3>${s.name}</h3>
            <div style="font-size:13px;color:#78909c">${s.address}</div>
            <div style="font-size:13px;margin-top:4px">
              <span class="badge ${s.approval_status === 'Approved' ? 'badge-green' : s.approval_status === 'Rejected' ? 'badge-red' : 'badge-yellow'}">${s.approval_status}</span>
              ${!s.is_open ? '<span class="badge badge-red">Closed</span>' : s.available_slots <= 0 ? '<span class="badge badge-gray">Full</span>' : '<span class="badge badge-green">Open</span>'}
            </div>
          </div>
          <div style="text-align:right">
            <div style="font-size:24px;font-weight:700;color:#0d47a1">${s.available_slots} <span style="font-size:13px;font-weight:400;color:#78909c">/ ${s.total_capacity} slots</span></div>
            <div style="font-size:14px;color:#546e7a">৳${s.hourly_rate}/hr</div>
          </div>
        </div>
        <div class="sc-actions">
          <div style="display:flex;align-items:center;gap:8px;margin-right:16px">
            <button class="btn btn-sm btn-outline" onclick="adjustSlot(${s.id},-1)">-</button>
            <span style="font-weight:600;font-size:16px;min-width:30px;text-align:center">${s.available_slots}</span>
            <button class="btn btn-sm btn-outline" onclick="adjustSlot(${s.id},1)">+</button>
          </div>
          <label class="toggle" style="margin-right:16px">
            <input type="checkbox" ${s.is_open ? 'checked' : ''} onchange="toggleStationStatus(${s.id}, this.checked)">
            <span class="slider"></span>
          </label>
          <button class="btn btn-sm btn-primary" onclick="editStation(${s.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteStationConfirm(${s.id})">Delete</button>
          <button class="btn btn-sm btn-warning" onclick="showFuelPrices(${s.id})">Fuel Prices</button>
        </div>
        ${s.fuel_prices && s.fuel_prices.length ? '<div style="margin-top:8px;font-size:12px;color:#546e7a">' + s.fuel_prices.map(f => `<span style="margin-right:12px"><strong>${f.fuel_type}:</strong> ৳${f.price_per_liter}/L</span>`).join('') + '</div>' : ''}
      `;
      list.appendChild(div);
    });
  } catch (err) { console.error('Failed to load stations:', err); }
}

async function adjustSlot(stationId, delta) {
  try {
    await API.updateSlots(stationId, { delta });
    loadOperatorStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function toggleStationStatus(stationId, isOpen) {
  try {
    await API.toggleStatus(stationId, { is_open: isOpen });
  } catch (err) { alert('Failed: ' + err.message); }
}

function showCreateStationForm() {
  document.getElementById('station-form-title').textContent = 'Create Station';
  document.getElementById('station-id').value = '';
  document.getElementById('s-name').value = '';
  document.getElementById('s-address').value = '';
  document.getElementById('s-lat').value = '';
  document.getElementById('s-lng').value = '';
  document.getElementById('s-type').value = 'parking';
  document.getElementById('s-capacity').value = '';
  document.getElementById('s-slots').value = '';
  document.getElementById('s-rate').value = '';
  document.getElementById('s-hours').value = '24/7';
  modal('station-modal', true);
}

async function editStation(id) {
  try {
    const s = await API.getStation(id);
    document.getElementById('station-form-title').textContent = 'Edit Station';
    document.getElementById('station-id').value = s.id;
    document.getElementById('s-name').value = s.name;
    document.getElementById('s-address').value = s.address;
    document.getElementById('s-lat').value = s.lat;
    document.getElementById('s-lng').value = s.lng;
    document.getElementById('s-type').value = s.station_type;
    document.getElementById('s-capacity').value = s.total_capacity;
    document.getElementById('s-slots').value = s.available_slots;
    document.getElementById('s-rate').value = s.hourly_rate;
    document.getElementById('s-hours').value = s.operating_hours;
    modal('station-modal', true);
  } catch (err) { alert('Failed: ' + err.message); }
}

async function saveStation(e) {
  e.preventDefault();
  const id = document.getElementById('station-id').value;
  const data = {
    name: document.getElementById('s-name').value,
    address: document.getElementById('s-address').value,
    lat: parseFloat(document.getElementById('s-lat').value),
    lng: parseFloat(document.getElementById('s-lng').value),
    station_type: document.getElementById('s-type').value,
    total_capacity: parseInt(document.getElementById('s-capacity').value) || 0,
    available_slots: parseInt(document.getElementById('s-slots').value) || 0,
    hourly_rate: parseFloat(document.getElementById('s-rate').value) || 0,
    operating_hours: document.getElementById('s-hours').value,
  };
  try {
    if (id) await API.updateStation(parseInt(id), data);
    else await API.createStation(data);
    modal('station-modal', false);
    loadOperatorStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function deleteStationConfirm(id) {
  if (!confirm('Delete this station permanently?')) return;
  try {
    await API.deleteStation(id);
    loadOperatorStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function showFuelPrices(stationId) {
  document.getElementById('fp-station-id').value = stationId;
  try {
    const prices = await API.getFuelPrices(stationId);
    const list = document.getElementById('fp-list');
    list.innerHTML = '';
    if (!prices.length) {
      list.innerHTML = '<div style="color:#90a4ae;font-size:13px;margin:8px 0">No fuel prices set</div>';
    }
    prices.forEach(p => {
      const row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;gap:8px;margin:6px 0';
      row.innerHTML = `
        <span style="flex:1;font-weight:600">${p.fuel_type}</span>
        <input type="number" step="0.01" value="${p.price_per_liter}" id="fp-val-${p.id}" style="width:100px;padding:6px 10px;border:2px solid #cfd8dc;border-radius:6px">
        <button class="btn btn-sm btn-primary" onclick="updateFuelPrice(${p.id})">Update</button>
        <button class="btn btn-sm btn-danger" onclick="deleteFuelPrice(${p.id})">Delete</button>
      `;
      list.appendChild(row);
    });
    modal('fuel-price-modal', true);
  } catch (err) { alert('Failed: ' + err.message); }
}

async function addFuelPrice() {
  const stationId = document.getElementById('fp-station-id').value;
  const type = document.getElementById('fp-new-type').value;
  const price = parseFloat(document.getElementById('fp-new-price').value);
  if (!type || isNaN(price)) { alert('Fill in all fields'); return; }
  try {
    await API.addFuelPrice(stationId, { fuel_type: type, price_per_liter: price });
    document.getElementById('fp-new-price').value = '';
    showFuelPrices(parseInt(stationId));
    loadOperatorStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function updateFuelPrice(id) {
  const val = parseFloat(document.getElementById(`fp-val-${id}`).value);
  if (isNaN(val)) return;
  try {
    await API.updateFuelPrice(id, { price_per_liter: val });
    alert('Updated!');
  } catch (err) { alert('Failed: ' + err.message); }
}

async function deleteFuelPrice(id) {
  if (!confirm('Delete this fuel price?')) return;
  try {
    await API.deleteFuelPrice(id);
    const stationId = document.getElementById('fp-station-id').value;
    showFuelPrices(parseInt(stationId));
    loadOperatorStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function lookupToken() {
  const token = document.getElementById('token-input').value.trim().toUpperCase();
  if (!token) return;
  try {
    const b = await API.verifyBooking({ token });
    document.getElementById('token-result').classList.remove('hidden');
    document.getElementById('token-info').innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div>
          <div style="font-size:16px;font-weight:600;color:#0d47a1">${b.station_name}</div>
          <div style="font-size:13px;color:#546e7a">Token: <strong>${b.token}</strong></div>
          <div style="font-size:13px;color:#546e7a">Start: ${new Date(b.start_time).toLocaleString()} &middot; Duration: ${b.duration_hours}hr &middot; Cost: ৳${b.cost}</div>
          <div style="font-size:13px">Status: <span class="badge badge-${b.status === 'Active' ? 'green' : b.status === 'Completed' ? 'blue' : 'red'}">${b.status}</span></div>
        </div>
        <div style="display:flex;gap:8px">
          ${b.status === 'Active' ? `<button class="btn btn-sm btn-success" onclick="completeTokenBooking(${b.id})">Complete</button><button class="btn btn-sm btn-danger" onclick="cancelTokenBooking(${b.id})">Cancel</button>` : ''}
        </div>
      </div>
    `;
  } catch (err) {
    document.getElementById('token-result').classList.add('hidden');
    alert('Token not found: ' + err.message);
  }
}

async function completeTokenBooking(id) {
  if (!confirm('Complete this booking?')) return;
  try {
    await API.completeBooking(id);
    lookupToken();
    loadOperatorStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function cancelTokenBooking(id) {
  if (!confirm('Cancel this booking?')) return;
  try {
    await API.cancelBooking(id);
    lookupToken();
    loadOperatorStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

// --- ADMIN PAGE ---

let adminTab = 'approvals';

function switchAdminTab(tab) {
  adminTab = tab;
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  document.getElementById(`atab-${tab}`).classList.add('active');
  document.querySelectorAll('.admin-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById(`apanel-${tab}`).classList.remove('hidden');
  if (tab === 'approvals') loadPendingApprovals();
  else if (tab === 'users') loadAdminUsers();
  else if (tab === 'stations') loadAdminStations();
  else if (tab === 'analytics') loadAnalytics();
}

async function loadAdminDashboard() {
  show('page-admin');
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('atab-analytics').classList.add('active');
  document.querySelectorAll('.admin-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById('apanel-analytics').classList.remove('hidden');
  loadAnalytics();
  loadPendingApprovals();
  loadAdminUsers();
  loadAdminStations();
}

async function loadPendingApprovals() {
  try {
    const stations = await API.getPendingApprovals();
    const list = document.getElementById('approvals-list');
    list.innerHTML = '';
    if (!stations.length) {
      list.innerHTML = '<div class="empty-state"><div class="icon">&#9989;</div><p>No pending approvals</p></div>';
      return;
    }
    stations.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${s.name}</strong></td>
        <td>${s.address}</td>
        <td><span class="badge badge-blue">${s.station_type}</span></td>
        <td>${s.provider_name}<br><small style="color:#90a4ae">${s.provider_email}</small></td>
        <td>${new Date(s.created_at).toLocaleDateString()}</td>
        <td>
          <div class="table-actions">
            <button class="btn btn-sm btn-success" onclick="approveStationReq(${s.id})">Approve</button>
            <button class="btn btn-sm btn-danger" onclick="rejectStationReq(${s.id})">Reject</button>
          </div>
        </td>
      `;
      list.appendChild(tr);
    });
  } catch (err) { console.error('Failed to load approvals:', err); }
}

async function approveStationReq(id) {
  try { await API.approveStation(id); loadPendingApprovals(); } catch (err) { alert('Failed: ' + err.message); }
}
async function rejectStationReq(id) {
  try { await API.rejectStation(id); loadPendingApprovals(); } catch (err) { alert('Failed: ' + err.message); }
}

async function loadAdminUsers() {
  const search = document.getElementById('admin-user-search').value;
  const role = document.getElementById('admin-user-role').value;
  const params = {};
  if (search) params.search = search;
  if (role) params.role = role;
  try {
    const users = await API.getUsers(params);
    const list = document.getElementById('admin-users-list');
    list.innerHTML = '';
    if (!users.length) {
      list.innerHTML = '<tr><td colspan="6" class="text-center" style="color:#90a4ae;padding:40px">No users found</td></tr>';
      return;
    }
    users.forEach(u => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${u.name}</strong></td>
        <td>${u.email}</td>
        <td>${u.phone || '-'}</td>
        <td><span class="badge badge-${u.role === 'admin' ? 'red' : u.role === 'operator' ? 'blue' : u.role === 'fuel_manager' ? 'orange' : 'green'}">${u.role}</span></td>
        <td>${u.vehicle_type || '-'}</td>
        <td>
          <div class="table-actions">
            <button class="btn btn-sm btn-primary" onclick="editAdminUser(${u.id})">Edit</button>
            ${u.role !== 'admin' ? `<button class="btn btn-sm btn-danger" onclick="deleteAdminUser(${u.id})">Delete</button>` : ''}
          </div>
        </td>
      `;
      list.appendChild(tr);
    });
  } catch (err) { console.error('Failed to load users:', err); }
}

async function editAdminUser(id) {
  try {
    const u = await API.getUser(id);
    document.getElementById('au-id').value = u.id;
    document.getElementById('au-name').value = u.name;
    document.getElementById('au-email').value = u.email;
    document.getElementById('au-phone').value = u.phone || '';
    document.getElementById('au-role').value = u.role;
    document.getElementById('au-vehicle').value = u.vehicle_type || '';
    document.getElementById('au-password').value = '';
    modal('admin-user-modal', true);
  } catch (err) { alert('Failed: ' + err.message); }
}

async function saveAdminUser(e) {
  e.preventDefault();
  const id = document.getElementById('au-id').value;
  const data = {
    name: document.getElementById('au-name').value,
    email: document.getElementById('au-email').value,
    phone: document.getElementById('au-phone').value,
    role: document.getElementById('au-role').value,
    vehicle_type: document.getElementById('au-vehicle').value || null,
    password: document.getElementById('au-password').value || '',
  };
  try {
    await API.updateUser(parseInt(id), data);
    modal('admin-user-modal', false);
    loadAdminUsers();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function deleteAdminUser(id) {
  if (!confirm('Delete this user?')) return;
  try { await API.deleteUser(id); loadAdminUsers(); } catch (err) { alert('Failed: ' + err.message); }
}

async function loadAdminStations() {
  try {
    const stations = await API.getAdminStations();
    const list = document.getElementById('admin-stations-list');
    list.innerHTML = '';
    if (!stations.length) {
      list.innerHTML = '<tr><td colspan="7" class="text-center" style="color:#90a4ae;padding:40px">No stations</td></tr>';
      return;
    }
    stations.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${s.name}</strong></td>
        <td>${s.provider_name}</td>
        <td><span class="badge badge-blue">${s.station_type}</span></td>
        <td>${s.available_slots}/${s.total_capacity}</td>
        <td><span class="badge badge-${s.approval_status === 'Approved' ? 'green' : s.approval_status === 'Rejected' ? 'red' : 'yellow'}">${s.approval_status}</span></td>
        <td>${s.is_open ? '<span class="badge badge-green">Open</span>' : '<span class="badge badge-red">Closed</span>'}</td>
        <td>
          <div class="table-actions">
            <button class="btn btn-sm btn-primary" onclick="editAdminStation(${s.id})">Edit</button>
            <button class="btn btn-sm btn-danger" onclick="deleteAdminStation(${s.id})">Delete</button>
          </div>
        </td>
      `;
      list.appendChild(tr);
    });
  } catch (err) { console.error('Failed to load stations:', err); }
}

async function editAdminStation(id) {
  try {
    const s = await API.getStation(id);
    document.getElementById('as-id').value = s.id;
    document.getElementById('as-name').value = s.name;
    document.getElementById('as-address').value = s.address;
    document.getElementById('as-lat').value = s.lat;
    document.getElementById('as-lng').value = s.lng;
    document.getElementById('as-type').value = s.station_type;
    document.getElementById('as-capacity').value = s.total_capacity;
    document.getElementById('as-slots').value = s.available_slots;
    document.getElementById('as-rate').value = s.hourly_rate;
    document.getElementById('as-hours').value = s.operating_hours;
    document.getElementById('as-approval').value = s.approval_status;
    document.getElementById('as-open').checked = s.is_open;
    modal('admin-station-modal', true);
  } catch (err) { alert('Failed: ' + err.message); }
}

async function saveAdminStation(e) {
  e.preventDefault();
  const id = parseInt(document.getElementById('as-id').value);
  const data = {
    name: document.getElementById('as-name').value,
    address: document.getElementById('as-address').value,
    lat: parseFloat(document.getElementById('as-lat').value),
    lng: parseFloat(document.getElementById('as-lng').value),
    station_type: document.getElementById('as-type').value,
    total_capacity: parseInt(document.getElementById('as-capacity').value) || 0,
    available_slots: parseInt(document.getElementById('as-slots').value) || 0,
    hourly_rate: parseFloat(document.getElementById('as-rate').value) || 0,
    operating_hours: document.getElementById('as-hours').value,
  };
  try {
    await API.updateStation(id, data);
    // Also update approval if admin
    const approval = document.getElementById('as-approval').value;
    if (approval === 'Approved') await API.approveStation(id);
    else if (approval === 'Rejected') await API.rejectStation(id);
    // Toggle status
    await API.toggleStatus(id, { is_open: document.getElementById('as-open').checked });
    modal('admin-station-modal', false);
    loadAdminStations();
  } catch (err) { alert('Failed: ' + err.message); }
}

async function deleteAdminStation(id) {
  if (!confirm('Delete this station?')) return;
  try { await API.deleteStation(id); loadAdminStations(); } catch (err) { alert('Failed: ' + err.message); }
}

async function loadAnalytics() {
  try {
    const a = await API.getAnalytics();
    document.getElementById('stat-drivers').textContent = a.total_drivers;
    document.getElementById('stat-operators').textContent = a.total_operators;
    document.getElementById('stat-stations').textContent = a.total_approved_stations;
    document.getElementById('stat-pending').textContent = a.total_pending_stations;
    document.getElementById('stat-active').textContent = a.active_bookings;
    document.getElementById('stat-completed').textContent = a.completed_bookings;
    document.getElementById('stat-canceled').textContent = a.canceled_bookings;
    document.getElementById('stat-revenue').textContent = '৳' + a.total_revenue.toLocaleString();
  } catch (err) { console.error('Failed to load analytics:', err); }
}

// Nav button routing
function goToDriver() { show('page-driver'); initMap(); loadNearbyStations(); }
function goToOperator() { if (currentUser) { show('page-operator'); loadOperatorDashboard(); } else alert('Please login'); }
function goToAdmin() { if (currentUser && currentUser.role === 'admin') { show('page-admin'); loadAdminDashboard(); } else alert('Admin only'); }
