import { useEffect, useRef, useState } from 'react';
import io from 'socket.io-client';

const STUN_SERVERS = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

export const useWebRTC = (roomId) => {
    const [localStream, setLocalStream] = useState(null);
    const [remoteStream, setRemoteStream] = useState(null);
    const [isCallActive, setIsCallActive] = useState(false);

    const socketRef = useRef();
    const peerRef = useRef();
    const localVideoRef = useRef();
    const remoteVideoRef = useRef();

    useEffect(() => {
        // Init Socket
        socketRef.current = io('http://localhost:5000/consultation');

        // Init Peer Connection
        peerRef.current = new RTCPeerConnection(STUN_SERVERS);

        peerRef.current.onicecandidate = (event) => {
            if (event.candidate) {
                socketRef.current.emit('ice-candidate', { candidate: event.candidate, roomId });
            }
        };

        peerRef.current.ontrack = (event) => {
            console.log("Remote track received");
            setRemoteStream(event.streams[0]);
            if (remoteVideoRef.current) {
                remoteVideoRef.current.srcObject = event.streams[0];
            }
        };

        // Socket Listeners
        socketRef.current.on('user-connected', async (userId) => {
            console.log("User connected, creating offer");
            setIsCallActive(true);
            const offer = await peerRef.current.createOffer();
            await peerRef.current.setLocalDescription(offer);
            socketRef.current.emit('offer', { sdp: offer, roomId });
        });

        socketRef.current.on('offer', async (payload) => {
            console.log("Offer received");
            setIsCallActive(true);
            await peerRef.current.setRemoteDescription(new RTCSessionDescription(payload.sdp));
            const answer = await peerRef.current.createAnswer();
            await peerRef.current.setLocalDescription(answer);
            socketRef.current.emit('answer', { sdp: answer, roomId });
        });

        socketRef.current.on('answer', async (payload) => {
            console.log("Answer received");
            await peerRef.current.setRemoteDescription(new RTCSessionDescription(payload.sdp));
        });

        socketRef.current.on('ice-candidate', async (payload) => {
            if (payload.candidate) {
                await peerRef.current.addIceCandidate(new RTCIceCandidate(payload.candidate));
            }
        });

        // Get Local Media
        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
            .then(stream => {
                setLocalStream(stream);
                if (localVideoRef.current) {
                    localVideoRef.current.srcObject = stream;
                }
                stream.getTracks().forEach(track => peerRef.current.addTrack(track, stream));

                // Join Room after stream ready
                socketRef.current.emit('join-room', roomId);
            })
            .catch(err => console.error("Error accessing media devices:", err));

        return () => {
            socketRef.current.disconnect();
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
            }
        };
    }, [roomId]);

    return { localVideoRef, remoteVideoRef, isCallActive };
};
