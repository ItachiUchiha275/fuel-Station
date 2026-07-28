const API = {
  async request(method, path, body) {
    const opts = { method, credentials: 'same-origin' };
    if (body) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify(body);
    }
    const r = await fetch(path, opts);
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || data.message || 'Request failed');
    return data;
  },
  signup: (d) => API.request('POST', '/api/auth/signup', d),
  login: (d) => API.request('POST', '/api/auth/login', d),
  logout: () => API.request('POST', '/api/auth/logout'),
  getMe: () => API.request('GET', '/api/auth/me'),
  updateProfile: (d) => API.request('PUT', '/api/auth/profile', d),
  createStation: (d) => API.request('POST', '/api/stations', d),
  getMyStations: () => API.request('GET', '/api/stations/mine'),
  getStation: (id) => API.request('GET', `/api/stations/${id}`),
  updateStation: (id, d) => API.request('PUT', `/api/stations/${id}`, d),
  deleteStation: (id) => API.request('DELETE', `/api/stations/${id}`),
  updateSlots: (id, d) => API.request('PUT', `/api/stations/${id}/slots`, d),
  toggleStatus: (id, d) => API.request('PUT', `/api/stations/${id}/status`, d),
  getNearby: (params) => {
    const q = new URLSearchParams(params).toString();
    return API.request('GET', `/api/stations/nearby?${q}`);
  },
  addFuelPrice: (sid, d) => API.request('POST', `/api/stations/${sid}/fuel-prices`, d),
  getFuelPrices: (sid) => API.request('GET', `/api/stations/${sid}/fuel-prices`),
  updateFuelPrice: (pid, d) => API.request('PUT', `/api/fuel-prices/${pid}`, d),
  deleteFuelPrice: (pid) => API.request('DELETE', `/api/fuel-prices/${pid}`),
  createBooking: (d) => API.request('POST', '/api/bookings', d),
  getMyBookings: () => API.request('GET', '/api/bookings/mine'),
  getBooking: (token) => API.request('GET', `/api/bookings/${token}`),
  verifyBooking: (d) => API.request('POST', '/api/bookings/verify', d),
  completeBooking: (id) => API.request('PUT', `/api/bookings/${id}/complete`),
  cancelBooking: (id) => API.request('PUT', `/api/bookings/${id}/cancel`),
  getPendingApprovals: () => API.request('GET', '/api/admin/pending-approvals'),
  approveStation: (id) => API.request('PUT', `/api/admin/stations/${id}/approve`),
  rejectStation: (id) => API.request('PUT', `/api/admin/stations/${id}/reject`),
  getUsers: (params) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return API.request('GET', `/api/admin/users${q}`);
  },
  getUser: (id) => API.request('GET', `/api/admin/users/${id}`),
  updateUser: (id, d) => API.request('PUT', `/api/admin/users/${id}`, d),
  deleteUser: (id) => API.request('DELETE', `/api/admin/users/${id}`),
  getAdminStations: () => API.request('GET', '/api/admin/stations'),
  getAnalytics: () => API.request('GET', '/api/admin/analytics'),
};
