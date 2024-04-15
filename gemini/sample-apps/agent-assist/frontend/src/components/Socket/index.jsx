import { io } from "socket.io-client"; // Import the socket.io-client library

const URL =
  process.env.NODE_ENV === "production" ? undefined : "http://127.0.0.1:5000"; // Set the socket URL based on the environment

// Create a socket connection using the socket.io-client library
const socket = io(URL, {
  transports: ["websocket"], // Specify the transport method to use
  upgrade: false, // Disable automatic upgrades to WebSocket
});

// Export the socket object to be used in other components
export default socket;
