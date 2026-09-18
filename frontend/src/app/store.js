import { configureStore } from '@reduxjs/toolkit';

import { setupAxiosInterceptors } from '@/lib/axios';
import authReducer from '@/store/slices/authSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
  },
});

setupAxiosInterceptors(store);
