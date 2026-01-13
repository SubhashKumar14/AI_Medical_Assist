module.exports = (io) => {
    const consultationNamespace = io.of('/consultation');

    consultationNamespace.on('connection', (socket) => {
        console.log('New client connected to signaling server:', socket.id);

        // Join a specific consultation room (Use Token ID)
        socket.on('join-room', (roomId) => {
            socket.join(roomId);
            console.log(`Socket ${socket.id} joined room ${roomId}`);

            // Notify others in room
            socket.to(roomId).emit('user-connected', socket.id);
        });

        // WebRTC Signaling: Offer
        socket.on('offer', (payload) => {
            // payload: { target: socketId, sdp: sessionDescription, roomId }
            socket.to(payload.roomId).emit('offer', {
                sdp: payload.sdp,
                callerId: socket.id
            });
        });

        // WebRTC Signaling: Answer
        socket.on('answer', (payload) => {
            // payload: { target: socketId, sdp: sessionDescription, roomId }
            socket.to(payload.roomId).emit('answer', {
                sdp: payload.sdp,
                callerId: socket.id
            });
        });

        // WebRTC Signaling: ICE Candidate
        socket.on('ice-candidate', (payload) => {
            socket.to(payload.roomId).emit('ice-candidate', {
                candidate: payload.candidate,
                senderId: socket.id
            });
        });

        socket.on('disconnect', () => {
            console.log('Client disconnected:', socket.id);
        });
    });
};
