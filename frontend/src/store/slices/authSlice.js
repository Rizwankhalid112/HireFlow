import { createSlice } from '@reduxjs/toolkit';

const ACCESS_TOKEN_KEY = 'accessToken';

function readStoredToken() {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

const initialToken = readStoredToken();

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    accessToken: initialToken,
    isAuthenticated: Boolean(initialToken),
  },
  reducers: {
    setCredentials: (state, action) => {
      const token = action.payload;
      state.accessToken = token;
      state.isAuthenticated = Boolean(token);
      try {
        localStorage.setItem(ACCESS_TOKEN_KEY, token);
      } catch {
        // ignore storage errors
      }
    },
    logout: (state) => {
      state.accessToken = null;
      state.isAuthenticated = false;
      try {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
      } catch {
        // ignore storage errors
      }
    },
  },
});

export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;
