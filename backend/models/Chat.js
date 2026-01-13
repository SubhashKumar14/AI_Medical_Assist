const mongoose = require('mongoose');

const ChatSchema = new mongoose.Schema({
    roomId: {
        type: String,
        required: true,
        index: true
    },
    senderId: {
        type: String, // Can be user ID or socket ID if anon
        required: true
    },
    senderName: {
        type: String,
        default: 'Unknown'
    },
    message: {
        type: String,
        required: true
    },
    timestamp: {
        type: Date,
        default: Date.now
    }
});

module.exports = mongoose.model('Chat', ChatSchema);
