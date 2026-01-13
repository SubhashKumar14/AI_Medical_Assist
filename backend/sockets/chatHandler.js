const Chat = require('../models/Chat');

module.exports = (io) => {
    const consultationNamespace = io.of('/consultation'); // Re-use existing namespace or separate?
    // Note: If reusing namespace, we need to be careful not to overwrite listeners or use a shared handler.
    // For simplicity, let's attach to the SAME namespace as signaling but dedicated events.

    // Actually, in Socket.io, it's better to modify the existing connection handler or simple use the same `on('connection')` 
    // defined in signalingHandler if they are in the same namespace. 
    // However, to keep files separate, we can export a function that attaches listeners to a specific socket.
    // BUT, `signalingHandler.js` already claims the namespace connection.

    // STRATEGY: We will append this logic to the existing namespace in a modular way.
    // Ideally refactor `signalingHandler.js` to import this, OR just register it separately if io object is passed.
    // Since `io.of('/consultation')` returns the same namespace object, we can add more listeners.

    consultationNamespace.on('connection', (socket) => {
        // Chat Events

        // Load History
        socket.on('join-chat', async (roomId) => {
            try {
                const history = await Chat.find({ roomId }).sort({ timestamp: 1 }).limit(50);
                socket.emit('chat-history', history);
                socket.join(roomId); // Ensure joined (redundant if join-room called, but safe)
            } catch (err) {
                console.error("Error loading chat history:", err);
            }
        });

        // Send Message
        socket.on('send-message', async (payload) => {
            // payload: { roomId, message, senderId, senderName }
            try {
                const newChat = new Chat({
                    roomId: payload.roomId,
                    senderId: payload.senderId,
                    senderName: payload.senderName,
                    message: payload.message
                });
                await newChat.save();

                // Broadcast to everyone in room including sender (for confirmation) 
                // or just others? Usually broadcast to all for sync.
                consultationNamespace.to(payload.roomId).emit('receive-message', newChat);
            } catch (err) {
                console.error("Error saving message:", err);
            }
        });
    });
};
