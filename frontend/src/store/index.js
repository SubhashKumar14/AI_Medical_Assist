import { configureStore } from '@reduxjs/toolkit';
import symptomReducer from './symptomSlice';
import authReducer from './authSlice';

export const store = configureStore({
    reducer: {
        symptom: symptomReducer,
        auth: authReducer,
    },
});
