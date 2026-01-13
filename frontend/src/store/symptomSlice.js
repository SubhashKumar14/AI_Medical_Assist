import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    sessionId: null,
    questionsAsked: [],
    currentQuestion: null,
    answers: {},
    triageSummary: null,
    redFlags: [],
    isLoading: false,
    error: null,
};

const symptomSlice = createSlice({
    name: 'symptom',
    initialState,
    reducers: {
        startTriage: (state, action) => {
            // action.payload: { sessionId, firstQuestion }
            state.sessionId = action.payload.sessionId;
            state.currentQuestion = action.payload.firstQuestion;
            state.questionsAsked = [];
            state.answers = {};
            state.triageSummary = null;
            state.redFlags = [];
        },
        answerQuestion: (state, action) => {
            // action.payload: { question, answer }
            const { question, answer } = action.payload;
            state.answers[question] = answer;
            state.questionsAsked.push({ question, answer });
        },
        setNextStep: (state, action) => {
            // action.payload: { nextQuestion, triageSummary, redFlags }
            if (action.payload.triageSummary) {
                state.triageSummary = action.payload.triageSummary;
                state.currentQuestion = null; // Finished
            } else {
                state.currentQuestion = action.payload.nextQuestion;
            }
            state.redFlags = action.payload.redFlags || [];
        },
        setLoading: (state, action) => {
            state.isLoading = action.payload;
        },
        resetTriage: (state) => {
            return initialState;
        }
    },
});

export const { startTriage, answerQuestion, setNextStep, setLoading, resetTriage } = symptomSlice.actions;
export default symptomSlice.reducer;
